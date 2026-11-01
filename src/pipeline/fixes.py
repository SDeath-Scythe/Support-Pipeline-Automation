"""Feature flags for candidate fixes under test. All are off unless named in PIPELINE_FIXES.

    PIPELINE_FIXES=some_fix python scripts/run_batch.py ...

A new idea is added here as a flag, measured with and without it (scripts/experiment.py), and then
either made the normal code path or deleted. On 30 Oct the 13 adopted fixes (F2, F3c, F6b, F11,
F12, F14b, F15, F16, F17, F18, F19, F20, F21) became the normal code and every dropped one was
deleted; their history is in docs/experiments/LOG.md and git.

Open since 1 Nov (security review), off until measured with and without on dev:
hold_reason, sensitive_number (draft rules in draft_check.py) and escalate_account_risk (gate.py).
"""

from __future__ import annotations

import os

FIXES: dict[str, str] = {
    # Iraq AML/CFT Law 39/2015 forbids telling a customer about a report or investigation (tipping-off).
    "hold_reason": "draft rule: flag a draft that mentions an investigation, suspicion, a report or "
                   "money laundering (draft:hold_reason)",
    "sensitive_number": "draft rule: flag a draft that repeats a card number or a code back to the "
                        "customer (draft:sensitive_number)",
    "escalate_account_risk": "gate: a blocked account or a SIM change always goes to a person with no "
                             "draft (flag account_risk); both are common account-takeover steps",
}


def active() -> frozenset[str]:
    names = {n.strip() for n in os.getenv("PIPELINE_FIXES", "").split(",") if n.strip()}
    unknown = names - FIXES.keys()
    if unknown:
        raise ValueError(f"Unknown fix(es) in PIPELINE_FIXES: {', '.join(sorted(unknown))}")
    return frozenset(names)


def enabled(name: str) -> bool:
    if name not in FIXES:
        raise KeyError(name)
    return name in active()
