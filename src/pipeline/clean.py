"""Light, rule-based cleaning before the model sees a ticket."""

from __future__ import annotations

import re

# Arabic-Indic (٠-٩) and Persian (۰-۹) digits -> ASCII, so references and
# amounts compare the same way however the customer typed them.
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_TATWEEL = "ـ"
_WS = re.compile(r"\s+")


def clean(text: str) -> str:
    text = text.translate(_DIGITS).replace(_TATWEEL, "")
    return _WS.sub(" ", text).strip()


# Seven or more digits, in any script, optionally split by single spaces ("9776 593217",
# "0770 123 4567", "+964..."): phone, card, account and transaction numbers. A number with
# thousands commas ("1,000,000") is an amount and is left alone.
_LONG_NUMBER = re.compile(r"(?<!\d)(?<!\d[.,])\+?\d(?: ?\d){6,}(?!\d|[.,]\d)")


def _hide(m: re.Match) -> str:
    s = m.group()
    digits = [i for i, c in enumerate(s) if c.isdigit()]
    keep = set(digits[:2] + digits[-2:])
    return "".join("*" if c.isdigit() and i not in keep else c for i, c in enumerate(s))


def mask_for_logs(text: str) -> str:
    """Hide long numbers (phone, card, account, transaction) before saving, keeping the first
    and last two digits so a person can still tell two numbers apart. Names are not masked."""
    return _LONG_NUMBER.sub(_hide, text)


def mask_run(value):
    """mask_for_logs applied to every string in a saved run (ticket text, prompts, model
    replies, drafts, notes); numbers, keys and structure are kept."""
    if isinstance(value, str):
        return mask_for_logs(value)
    if isinstance(value, list):
        return [mask_run(v) for v in value]
    if isinstance(value, dict):
        return {k: mask_run(v) for k, v in value.items()}
    return value
