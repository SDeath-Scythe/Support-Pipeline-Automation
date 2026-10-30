"""Routing and priority: plain rules a reviewer can read."""

from __future__ import annotations

from .config import taxonomy, thresholds
from .schemas import Extraction

_ORDER = ["P1", "P2", "P3"]


def _raise_one(priority: str) -> str:
    return _ORDER[max(0, _ORDER.index(priority) - 1)]


def route(extraction: Extraction, cleaned_text: str) -> tuple[str, str]:
    """Return (team_key, priority).

    Priority is the subcategory's default, raised one level for a large amount: at least
    1,000,000 IQD, or at least $750 (dollars are compared, never converted). From the project
    author: no word in a ticket (not هسه, ضروري, عاجل or any other) changes priority.
    """
    sub = taxonomy().get(extraction.subcategory)
    priority = sub.default_priority
    limits = thresholds()["priority"]
    large_iqd = extraction.amount_iqd is not None and extraction.amount_iqd >= limits["large_amount_iqd"]
    large_usd = extraction.amount_usd is not None and extraction.amount_usd >= limits["large_amount_usd"]
    if large_iqd or large_usd:
        priority = _raise_one(priority)
    return sub.team, priority
