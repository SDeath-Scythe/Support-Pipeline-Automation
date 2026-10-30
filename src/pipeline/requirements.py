"""What a ticket must contain before the team can act on it.

Base rule: taxonomy.yaml `required_fields` (transfers need a reference and an amount, and so on).

From the project author: ask for a transaction number only when the team can't find the
transaction without it.
- not_received / wrong_recipient: the recipient's phone number identifies the transfer just as well.
- reversal_request: a duplicate or cancelled payment is found in the history by amount and recipient,
  so the reference is never required.
"""

from __future__ import annotations

from .schemas import Extraction

# Fields that can stand in for a reference.
REFERENCE_ALTERNATIVES = {
    "not_received": ("recipient_phone",),
    "wrong_recipient": ("recipient_phone",),
}
REFERENCE_NOT_NEEDED = {"reversal_request"}


def has_field(ex: Extraction, field: str) -> bool:
    value = {
        "reference": ex.reference,
        "amount": ex.amount_iqd if ex.amount_iqd is not None else ex.amount_usd,
        "recipient_phone": ex.recipient_phone,
    }.get(field)
    return value not in (None, "")


def reference_needed(ex: Extraction) -> bool:
    """False when the team can find the transaction without a reference."""
    if ex.subcategory in REFERENCE_NOT_NEEDED:
        return False
    return not any(has_field(ex, alt) for alt in REFERENCE_ALTERNATIVES.get(ex.subcategory, ()))


def missing_required(ex: Extraction, required_fields: tuple[str, ...] | list[str]) -> list[str]:
    """Required fields the ticket doesn't give, after the reference exceptions above."""
    out = []
    for field in required_fields:
        if field == "reference" and not reference_needed(ex):
            continue
        if not has_field(ex, field):
            out.append(field)
    return out
