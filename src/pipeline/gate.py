"""Confidence gate: decides continue / re-check / escalate.

The model's own score is never trusted alone. Rule checks can lower it, and
high-risk subcategories are always re-checked by a second model.
"""

from __future__ import annotations

import re

from .clean import clean
from .config import taxonomy, thresholds
from .requirements import missing_required
from .schemas import Extraction, GateResult


_ALNUM = re.compile(r"[^0-9A-Za-z]")
# A reference as customers type it: chunks of letters/digits joined by - space / _ .
_REF_RUN = re.compile(r"[0-9A-Za-z]+(?:[\s\-/_.]+[0-9A-Za-z]+)*")


def _key(s: str) -> str:
    return _ALNUM.sub("", clean(s)).lower()


def reference_in_text(reference: str, cleaned_text: str) -> bool:
    """True if the reference appears in the ticket, ignoring separators and digit script.

    "44719032" matches "4471-٩٠٣٢" and "4471 9032"; an invented number does not.
    """
    if reference in cleaned_text:
        return True
    key = _key(reference)
    if not key:
        return False
    return any(key in _key(run) for run in _REF_RUN.findall(clean(cleaned_text)))


def check(extraction: Extraction, cleaned_text: str) -> GateResult:
    tax = taxonomy()
    t = thresholds()["confidence"]
    score = extraction.confidence
    flags: list[str] = []
    reasons: list[str] = []

    sub = tax.subcategories.get(extraction.subcategory)
    if sub is None or sub.category != extraction.category:
        return GateResult(
            confidence=0.0, needs_recheck=False, escalate=True,
            flags=["invalid_category"], reasons=["Category and subcategory do not match the taxonomy"],
        )

    if sub.always_escalate:
        return GateResult(
            confidence=score, needs_recheck=False, escalate=True,
            flags=["fraud"], reasons=["Fraud and security tickets are always handled by a person"],
        )

    # A reference the model "found" must actually appear in the ticket text.
    if extraction.reference and not reference_in_text(extraction.reference, cleaned_text):
        flags.append("ref_not_in_text")
        reasons.append("Extracted reference does not appear in the ticket")
        score = min(score, t["missing_field_cap"])

    # No reference is needed when the team can find the transaction another way (requirements.py).
    for field in missing_required(extraction, sub.required_fields):
        flags.append(f"missing:{field}")
        score = min(score, t["missing_field_cap"])

    if score < t["recheck_from"]:
        reasons.append(f"Low confidence ({score:.2f})")
        return GateResult(confidence=score, needs_recheck=False, escalate=True, flags=flags, reasons=reasons)

    needs_recheck = score < t["pass_above"] or sub.high_risk
    return GateResult(confidence=score, needs_recheck=needs_recheck, escalate=False, flags=flags, reasons=reasons)
