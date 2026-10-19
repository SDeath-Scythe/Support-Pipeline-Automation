"""Data shapes passed between pipeline stages."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Outcome(str, Enum):
    DRAFTED = "drafted"      # ready for a human to approve
    FLAGGED = "flagged"      # drafted, but one field needs checking
    ESCALATED = "escalated"  # no draft; a human takes it, with a note why


class Ticket(BaseModel):
    id: str
    text: str


class Extraction(BaseModel):
    """What the classifier model returns (validated against this schema)."""

    category: str
    subcategory: str
    secondary_subcategory: str | None = None
    reference: str | None = None
    amount_iqd: int | None = None
    date: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = ""


class GateResult(BaseModel):
    confidence: float          # after rule caps
    needs_recheck: bool
    escalate: bool
    flags: list[str] = []      # e.g. "missing:amount", "ref_not_in_text"
    reasons: list[str] = []    # human-readable, shown in the escalation note


class TicketResult(BaseModel):
    ticket: Ticket
    extraction: Extraction | None = None
    team: str | None = None
    priority: str | None = None
    outcome: Outcome
    draft_ar: str | None = None
    notes: list[str] = []
