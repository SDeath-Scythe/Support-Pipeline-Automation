"""Routing and priority: plain rules a reviewer can read."""

from __future__ import annotations

import re

from .config import taxonomy, thresholds
from .fixes import enabled
from .schemas import Extraction

_ORDER = ["P1", "P2", "P3"]

# Starting list; extended from dev-set failures.
URGENT_WORDS = ["ضروري", "عاجل", "بسرعة", "هسه", "صارلي يومين", "صارلي اسبوع", "تاني مرة", "ثاني مرة"]

# F7 (no_now_urgency): "هسه" means "now" and is everyday wording ("هسه شلون ارجعه؟"),
# so on its own it is not a sign of urgency.
NOW_WORDS = ["هسه"]


def urgent_words() -> list[str]:
    # F15 (no_urgency_words), from the project author (a native speaker): no word marks real
    # urgency reliably, so with F15 no word changes priority. It supersedes F7.
    if enabled("no_urgency_words"):
        return []
    if enabled("no_now_urgency"):
        return [w for w in URGENT_WORDS if w not in NOW_WORDS]
    return URGENT_WORDS


def _raise_one(priority: str) -> str:
    return _ORDER[max(0, _ORDER.index(priority) - 1)]


def route(extraction: Extraction, cleaned_text: str) -> tuple[str, str]:
    """Return (team_key, priority)."""
    sub = taxonomy().get(extraction.subcategory)
    priority = sub.default_priority

    large = thresholds()["priority"]["large_amount_iqd"]
    # F19 (usd_large_amount), from the project author: dollar amounts count too. $750 is about
    # 1,000,000 IQD. The amount itself is never converted; only the threshold is per currency.
    large_usd = thresholds()["priority"].get("large_amount_usd")
    usd_large = (enabled("usd_large_amount") and large_usd is not None and extraction.amount_usd is not None
                 and extraction.amount_usd >= large_usd)
    if (extraction.amount_iqd is not None and extraction.amount_iqd >= large) or usd_large:
        priority = _raise_one(priority)
    elif any(re.search(w, cleaned_text) for w in urgent_words()):
        priority = _raise_one(priority)

    return sub.team, priority
