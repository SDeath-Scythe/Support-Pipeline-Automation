"""Stage 6: draft a reply for the agent to review (drafter role, Sonnet).

The drafter only gets facts from config/policy.yaml. Missing facts are simply not
given to it, so it cannot state them.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from . import fixes
from .clean import neutralise_tags
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
    """The drafter's instructions; the draft_rules_ut flag (fixes.py) swaps in the version under test."""
    return _read("draft_system.draft_rules_ut.md" if fixes.enabled("draft_rules_ut") else "draft_system.md")


# amount_own_words: the amount as the customer wrote it, when it is not a number in the ticket («عشر ورقات»).
# A run of number words with a money word in it; «ورقة» (a 100 USD note) is how the classifier reads it, not
# something the customer wrote, so the draft quotes the words instead of the converted number.
_NUM_WORD = (r"و?(?:واحد|وحدة|ثنين|اثنين|ثنتين|ثلاث|ثلاثة|تلاث|تلاثة|اربع|أربع|اربعة|أربعة|خمس|خمسة|ست|ستة|سبع|سبعة|"
             r"ثمان|ثمانية|ثمن|ثمنية|تسع|تسعة|عشر|عشرة|احدعش|اثنعش|ثلطعش|ربعطعش|خمسطعش|عشرين|ثلاثين|تلاثين|اربعين|"
             r"أربعين|خمسين|ستين|سبعين|ثمانين|تسعين|مية|ميه|مئة|ميتين|ربع|نص|نصف|الف|ألف|الفين|ألفين|آلاف|الاف|"
             r"مليون|ملايين|\d+)")
_MONEY_WORD = r"(?:ورق[ةه]|ورقات|اوراق|أوراق|دولار|دينار|الف|ألف|آلاف|الاف|مليون|ملايين)"
_TOKEN = rf"(?:{_NUM_WORD}|و?{_MONEY_WORD})"
_OWN_WORDS = re.compile(rf"(?<!\w){_TOKEN}(?:\s+{_TOKEN})*(?<=\w)(?!\w)")


def own_words(text: str) -> str | None:
    """The first run of number words in the ticket that names money («عشر ورقات», «مليون ونص»), or None."""
    for m in _OWN_WORDS.finditer(text):
        if re.search(rf"(?<!\w)و?{_MONEY_WORD}(?!\w)", m.group()):
            return m.group()
    return None


def amount_line(cleaned_text: str, ex: Extraction) -> str | None:
    """The drafter's amount line. With amount_own_words on, an amount the ticket doesn't write as a number
    is given as the customer's own words to quote (or, if they can't be found, as an instruction to use them)."""
    if ex.amount_iqd is not None:
        n, currency, line = ex.amount_iqd, "iqd", f"Amount: {ex.amount_iqd:,} IQD"
    elif ex.amount_usd is not None:
        n, currency, line = ex.amount_usd, "usd", f"Amount: {ex.amount_usd} USD"
    else:
        return None
    if not fixes.enabled("amount_own_words") or amount_written(cleaned_text, n, currency):
        return line
    words = own_words(cleaned_text)
    return ("Amount: the customer wrote it in words, not as a number. If you mention it, quote their words"
            + (f" «{words}»" if words else "") + " and write no number for it.")


_CHECKED = {"reference", "amount", "date", "recipient_number", "phone_number"}   # fields _have() can see


def _have(ex: Extraction, field: str) -> bool:
    return {
        "reference": ex.reference,
        "amount": ex.amount_iqd if ex.amount_iqd is not None else ex.amount_usd,
        "date": ex.date,
        "recipient_number": ex.recipient_phone,
        "phone_number": ex.recipient_phone,
    }.get(field) not in (None, "")


def ask_for(ex: Extraction) -> list[str]:
    """Fields the policy says the customer should send that the ticket doesn't contain."""
    sub = load_yaml("policy.yaml")["subcategories"].get(ex.subcategory) or {}
    wanted = sub.get("customer_should_send", [])
    if not reference_needed(ex):   # the team can find the transaction without it (author's rule)
        wanted = [f for f in wanted if f != "reference"]
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
    missing = ask_for(ex)
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


def draft(cleaned_text: str, ex: Extraction, team_key: str) -> str:
    return call("drafter", system_prompt(), user_prompt(cleaned_text, ex, team_key)).strip()
