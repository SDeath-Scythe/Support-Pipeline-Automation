"""Stage 6: draft a reply for the agent to review (drafter role, Sonnet).

The drafter only gets facts from config/policy.yaml. Missing facts are simply not
given to it, so it cannot state them.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from .config import load_yaml, taxonomy
from .fixes import enabled
from .llm import call
from .requirements import reference_needed
from .schemas import Extraction

_PROMPT = Path(__file__).parent / "prompts" / "draft_system.md"

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


def policy() -> dict:
    """The grounding facts. F5 (policy_facts) swaps in the filled-in experiment file."""
    return load_yaml("experiments/policy_filled.yaml" if enabled("policy_facts") else "policy.yaml")


# F12 (no_specific_followup): the judge's worst drafts promised to send a specific answer
# (a branch address, a refund date) the team may not have.
# v2: v1 ended "...will check and follow up", and the drafter's follow-up phrase kept coming out
# broken ("wياك", "يتابعونويا"); v2 drops that wording.
_NO_SPECIFIC = (
    "- Do not say the team will send, confirm or tell the customer a specific answer (an address, a date, "
    "a fee, how long something takes, a refund). It is enough to say the relevant team will check it.\n"
)


def system_prompt() -> str:
    return _system_prompt(enabled("no_specific_followup"))


@lru_cache(maxsize=2)
def _system_prompt(no_specific: bool) -> str:
    prompt = _PROMPT.read_text(encoding="utf-8")
    if no_specific:
        anchor = "- Never promise a refund, a reversal, a time, or an outcome. You can say the team will check.\n"
        prompt = prompt.replace(anchor, anchor + _NO_SPECIFIC)
    return prompt


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
    sub = policy()["subcategories"].get(ex.subcategory) or {}
    wanted = sub.get("customer_should_send", [])
    if not reference_needed(ex):   # F18: the team can find the transaction without it
        wanted = [f for f in wanted if f != "reference"]
    return [f for f in wanted if not _have(ex, f)]


def user_prompt(cleaned_text: str, ex: Extraction, team_key: str) -> str:
    facts_src = policy()
    tax = taxonomy()
    sub = tax.get(ex.subcategory)
    facts = []
    if facts_src["company"].get("support_hours_ar"):
        facts.append(f"Support hours: {facts_src['company']['support_hours_ar']}")
    rt = (facts_src["subcategories"].get(ex.subcategory) or {}).get("response_time_ar")
    if rt:
        facts.append(f"Expected response time for this issue: {rt}")
    lines = [
        f"<ticket>\n{cleaned_text}\n</ticket>",
        "",
        f"Issue: {tax.categories[sub.category]} / {sub.label}",
        f"Handled by: {tax.teams[team_key]['label_ar']}",
    ]
    if ex.secondary_subcategory and ex.secondary_subcategory in tax.subcategories:
        lines.append(f"Second question in the ticket: {tax.get(ex.secondary_subcategory).label}")
    if ex.reference:
        lines.append(f"Reference given: {ex.reference}")
    if ex.amount_iqd is not None:
        lines.append(f"Amount: {ex.amount_iqd:,} IQD")
    elif ex.amount_usd is not None:
        lines.append(f"Amount: {ex.amount_usd} USD")
    if ex.fee_iqd is not None:
        lines.append(f"Disputed fee: {ex.fee_iqd:,} IQD")
    missing = ask_for(ex)
    if enabled("ask_if_missing"):
        # F11: the classifier can't see a shop name, agent location or bill type, so those are only
        # asked for when the ticket doesn't already give them.
        sure = [f for f in missing if f in _CHECKED]
        maybe = [f for f in missing if f not in _CHECKED]
        lines.append("Ask the customer for: " + (", ".join(FIELD_AR.get(f, f) for f in sure) if sure else "nothing"))
        if maybe:
            # F11b (ask_if_unnamed), from the author's round-2 review (dev-0199): "بالمطعم" (at the restaurant)
            # was taken as the shop's name, so the drafter didn't ask for it.
            unnamed = (" (the kind of place alone, like the restaurant or the agent, does not count: ask for its name)"
                       if enabled("ask_if_unnamed") else "")
            lines.append("Also ask for these, but only if the ticket does not already give them" + unnamed + ": "
                         + ", ".join(FIELD_AR.get(f, f) for f in maybe))
    else:
        lines.append("Ask the customer for: " + (", ".join(FIELD_AR.get(f, f) for f in missing) if missing else "nothing"))
    lines.append("Known facts: " + ("; ".join(facts) if facts else "none (do not state any timeline, fee or limit)"))
    return "\n".join(lines)


def draft(cleaned_text: str, ex: Extraction, team_key: str) -> str:
    return call("drafter", system_prompt(), user_prompt(cleaned_text, ex, team_key)).strip()
