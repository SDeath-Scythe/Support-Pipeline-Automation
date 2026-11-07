"""Stage 6: draft a reply for the agent to review (drafter role, Sonnet).

The drafter only gets facts from config/policy.yaml. Missing facts are simply not
given to it, so it cannot state them.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from . import fixes
from .clean import neutralise_tags, secret_kinds
from .config import load_yaml, taxonomy
from .draft_check import amount_written
from .llm import call
from .requirements import reference_needed
from .schemas import Extraction

_PROMPTS = Path(__file__).parent / "prompts"

FIELD_AR = {
    "reference": "رقم العملية",
    "amount": "المبلغ",
    "date": "تاريخ ووقت العملية",
    "recipient_number": "رقم المستلم",
    "agent_location": "اسم الوكيل ومكانه",
    "merchant": "اسم المتجر",
    "bill_type": "نوع الفاتورة",
    "phone_number": "الرقم اللي انشحن",
    "screenshot": "صورة من الشاشة",
}


@lru_cache(maxsize=2)
def _read(name: str) -> str:
    return (_PROMPTS / name).read_text(encoding="utf-8")


def system_prompt() -> str:
    """The drafter's instructions (the draft_rules_ut version since 7 Nov); the draft_rules_r2 flag swaps in the version
    under test."""
    return _read("draft_system.draft_rules_r2.md" if fixes.enabled("draft_rules_r2") else "draft_system.md")


# The amount as the customer wrote it, when it is not a number in the ticket («عشر ورقات»).
# A run of number words with a money word in it; «ورقة» (a 100 USD note) is how the classifier reads it, not
# something the customer wrote, so the draft quotes the words instead of the converted number.
_NUM_WORD = (r"(?:و|ب|وب)?(?:واحد|وحدة|ثنين|اثنين|ثنتين|ثلاث|ثلاثة|تلاث|تلاثة|اربع|أربع|اربعة|أربعة|خمس|خمسة|ست|ستة|"
             r"سبع|سبعة|ثمان|ثمانية|ثمن|ثمنية|تسع|تسعة|عشر|عشرة|احدعش|اثنعش|ثلطعش|ربعطعش|خمسطعش|عشرين|ثلاثين|تلاثين|"
             r"اربعين|أربعين|خمسين|ستين|سبعين|ثمانين|تسعين|مية|ميه|مئة|ميت|ميتين|\w+مي[ةه]|ربع|نص|نصف|الف|ألف|الفين|"
             r"ألفين|آلاف|الاف|مليون|ملايين|\d+)")
_MONEY_WORD = r"(?:ورق[ةه]|ورقات|اوراق|أوراق|دولار|دينار|الف|ألف|آلاف|الاف|مليون|ملايين)"
# Second round of role-played test sessions (drafter_inputs_r2, adopted 7 Nov): «1.5 مليون» is one number, a lone «و» goes
# on with the amount («2 مليون و 500 الف»), and «مئتي» is 200 («ألف ومئتي دولار» was given to the drafter as «ألف»).
_NUM_WORD_R2 = _NUM_WORD.replace(r"|\d+)", r"|مئتي|ميتي|مائتي|مائتين|\d+(?:[.٫]\d+)?)")
_TOKEN_R2 = rf"(?:{_NUM_WORD_R2}|(?:و|ب|وب)?{_MONEY_WORD}|و(?=\s))"
_OWN_WORDS_R2 = re.compile(rf"(?<!\w){_TOKEN_R2}(?:\s+{_TOKEN_R2})*(?<=\w)(?!\w)")


def own_words(text: str) -> str | None:
    """The longest run of number words in the ticket that names money («عشر ورقات», «بستين الف»), or None."""
    runs = [m.group().strip() for m in _OWN_WORDS_R2.finditer(text)
            if re.search(rf"(?<!\w)(?:و|ب|وب)?{_MONEY_WORD}(?!\w)", m.group())]
    return max(runs, key=lambda r: len(r.split()), default=None)


def amount_line(cleaned_text: str, ex: Extraction) -> str | None:
    """The drafter's amount line. An amount the ticket doesn't write as a number is given as the customer's
    own words to quote (or, if they can't be found, as an instruction to use them): amount_own_words, 7 Nov."""
    if ex.amount_iqd is not None:
        n, currency, line = ex.amount_iqd, "iqd", f"Amount: {ex.amount_iqd:,} IQD"
    elif ex.amount_usd is not None:
        n, currency, line = ex.amount_usd, "usd", f"Amount: {ex.amount_usd} USD"
    else:
        return None
    if amount_written(cleaned_text, n, currency) or _written_r2(cleaned_text, n, currency):
        return line
    words = own_words(cleaned_text)
    if words:
        return (f"Amount: the customer wrote «{words}». If you mention the amount, use those words as they are, "
                "without quotation marks, and write no number for it.")
    return ("Amount: the customer did not write it as a number. If you mention it, use their own words from the "
            "ticket and write no number for it.")


def _written_r2(text: str, n, currency: str) -> bool:
    """The amount written as a decimal of a million («1.5 مليون», which the drafter was told as «5 مليون») or as «2 مليون و
    500 الف» (told as «2 مليون»): second round of role-played test sessions."""
    if currency != "iqd" or not n or n < 1_000_000:
        return False
    m, k = divmod(int(n), 1_000_000)
    tries = []
    if k and k % 1000 == 0:
        tries.append(rf"(?<![\d.,٫٬]){m}\s*(?:مليون|ملايين)\s*و\s*{k // 1000}\s*(?:ألف|الف|آلاف|الاف|ألاف)")
    dec = f"{n / 1_000_000:g}"
    if "." in dec and len(dec.split(".")[1]) <= 2:
        tries.append(rf"(?<![\d.,٫٬]){dec.replace('.', '[.٫]')}\s*(?:مليون|ملايين)")
    return any(re.search(t, text) for t in tries)


_CHECKED = {"reference", "amount", "date", "recipient_number", "phone_number"}   # fields _have() can see


def _have(ex: Extraction, field: str) -> bool:
    return {
        "reference": ex.reference,
        "amount": ex.amount_iqd if ex.amount_iqd is not None else ex.amount_usd,
        "date": ex.date,
        "recipient_number": ex.recipient_phone,
        "phone_number": ex.recipient_phone,
    }.get(field) not in (None, "")


# No shop to name at a cash machine or when a card fails everywhere (drafter_inputs_r2, adopted 7 Nov). (A time for what happens «هسه» was
# tried and dropped: «الوكيل كال تنزل هسه» is the agent's words, and the deposit's time is still needed.)
_NO_SHOP = re.compile(r"صراف|(?<![A-Za-z])ATM(?![A-Za-z])|مكين[ةه]\s+(?:ال)?سحب|(?:بكل|كل)\s+(?:ال)?(?:مكان|محلات|مواقع|مكائن)|وين\s+ما",
                      re.IGNORECASE)


def ask_for(ex: Extraction, text: str | None = None) -> list[str]:
    """Fields the policy says the customer should send that the ticket doesn't contain. Given the ticket's text, a shop is
    not asked at a cash machine or «بكل مكان»."""
    sub = load_yaml("policy.yaml")["subcategories"].get(ex.subcategory) or {}
    wanted = sub.get("customer_should_send", [])
    if not reference_needed(ex):   # the team can find the transaction without it (author's rule)
        wanted = [f for f in wanted if f != "reference"]
    if text and _NO_SHOP.search(text):
        wanted = [f for f in wanted if f != "merchant"]
    return [f for f in wanted if not _have(ex, f)]


def policy_facts(subcategory: str | None) -> list[str]:
    """The policy facts the drafter is told for one kind of issue (support hours, the expected
    response time). They are the only place a draft may take a time from: draft_check allows a
    «خلال ...» found here, never one from the ticket. None (no known issue type) gives the company
    facts alone."""
    facts_src = load_yaml("policy.yaml")
    facts = []
    if facts_src["company"].get("support_hours_ar"):
        facts.append(f"Support hours: {facts_src['company']['support_hours_ar']}")
    rt = (facts_src["subcategories"].get(subcategory) or {}).get("response_time_ar")
    if rt:
        facts.append(f"Expected response time for this issue: {rt}")
    return facts


def known_facts(ex: Extraction) -> list[str]:
    """The policy facts for this ticket's issue type, as the drafter's prompt lists them."""
    return policy_facts(ex.subcategory)


def facts_text(subcategory: str | None) -> str:
    """The policy facts as draft_check reads them (its facts_text argument): one per line. The
    pipeline checks every draft with this, and so does the viewer when an agent edits one, so both
    allow exactly the same times."""
    return "\n".join(policy_facts(subcategory))


def user_prompt(cleaned_text: str, ex: Extraction, team_key: str) -> str:
    tax = taxonomy()
    sub = tax.get(ex.subcategory)
    facts = known_facts(ex)
    lines = [
        f"<ticket>\n{neutralise_tags(cleaned_text)}\n</ticket>",
        "",
        f"Issue: {tax.categories[sub.category]} / {sub.label}",
        f"Handled by: {tax.teams[team_key]['label_ar']}",
    ]
    if ex.secondary_subcategory and ex.secondary_subcategory in tax.subcategories:
        lines.append(f"Second question in the ticket: {tax.get(ex.secondary_subcategory).label}")
    if ex.reference:
        lines.append(f"Reference given: {ex.reference}")
    amount = amount_line(cleaned_text, ex)
    if amount:
        lines.append(amount)
    if ex.fee_iqd is not None:
        lines.append(f"Disputed fee: {ex.fee_iqd:,} IQD")
    if fixes.enabled("draft_rules_r2"):
        said = security_line(cleaned_text)
        if said:
            lines.append(said)
    missing = ask_for(ex, cleaned_text)
    # The classifier can't see a shop name, agent location or bill type, so those are only asked for
    # when the ticket doesn't already give them.
    sure = [f for f in missing if f in _CHECKED]
    maybe = [f for f in missing if f not in _CHECKED]
    lines.append("Ask the customer for: " + (", ".join(FIELD_AR.get(f, f) for f in sure) if sure else "nothing"))
    if maybe:
        lines.append("Also ask for these, but only if the ticket does not already give them: "
                     + ", ".join(FIELD_AR.get(f, f) for f in maybe))
    lines.append("Known facts: " + ("; ".join(facts) if facts else "none (do not state any timeline, fee or limit)"))
    return "\n".join(lines)


_SECURITY = {"card": ("a card number", "stop the card"), "cvv": ("the card's security code", "stop the card"),
             "pin": ("their PIN", "change their PIN"), "otp": ("a one-time code", "never share a code with anyone, us included")}


def security_line(cleaned_text: str) -> str | None:
    """draft_rules_r2: the drafter's line when the customer wrote a card number, a PIN or a code (clean.secret_kinds)."""
    kinds = [k for k in secret_kinds(cleaned_text) if k in _SECURITY]
    if not kinds:
        return None
    what = ", ".join(_SECURITY[k][0] for k in kinds)
    advice = " and ".join(dict.fromkeys(_SECURITY[k][1] for k in kinds))
    return f"Security: the customer wrote {what} in the ticket. Never repeat it. Advise them to {advice}."


def draft(cleaned_text: str, ex: Extraction, team_key: str) -> str:
    return call("drafter", system_prompt(), user_prompt(cleaned_text, ex, team_key)).strip()
