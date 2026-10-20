"""Feature flags for candidate fixes under test. All are off unless named in PIPELINE_FIXES.

    PIPELINE_FIXES=draft_check,recheck_same_team python scripts/run_batch.py ...

Each fix is measured with and without it (scripts/experiment.py) before it becomes the
default. When a fix is adopted, its flag is removed and the code path made permanent.
See docs/experiments/README.md.
"""

from __future__ import annotations

import os

FIXES = {
    "draft_check": "F2: rule checks on every draft; a failing draft is flagged with the reason",
    "recheck_same_team": "F3: re-check disagreement within one team (not fraud) is flagged with a draft, not escalated",
    "policy_facts": "F5: the drafter gets filled-in policy facts (config/experiments/policy_filled.yaml)",
    "fee_amount": "F6: the classifier extracts the disputed fee separately (fee_iqd)",
    "no_now_urgency": "F7: 'هسه' (now) no longer raises priority",
    "unclear_template": "F8: unclear tickets get a fixed reply instead of a drafter call",
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
