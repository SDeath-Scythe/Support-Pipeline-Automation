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


_LONG_NUMBER = re.compile(r"\d{8,}")


def mask_for_logs(text: str) -> str:
    """Hide long digit runs (phone, card, account numbers) before logging."""
    return _LONG_NUMBER.sub(lambda m: m.group()[:2] + "*" * (len(m.group()) - 4) + m.group()[-2:], text)
