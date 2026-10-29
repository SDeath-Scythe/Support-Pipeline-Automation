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
    "recheck_use_second": "F3b: a same-team re-check disagreement is drafted from the re-check's answer, flagged",
    "recheck_cross_team": "F3c: any non-fraud re-check disagreement is drafted from the re-check's answer, flagged",
    "confusable_recheck": "F9: re-check when the answer is in a known look-alike pair and confidence < 0.90",
    "runner_up": "F10: the classifier names a runner-up; re-check when it has one and confidence < 0.90",
    "lookalike_hints": "F13: sharper classifier hints for the look-alike subcategories",
    "fraud_secondary_rule": "F14: rule 1 defers to rule 5, so a consequence of the fraud is not a secondary issue",
    "fraud_secondary_cleanup": "F14b: rule, not prompt: a fraud ticket's secondary is cleared when it is only a consequence (account access or another fraud type)",
    "reference_when_needed": "F18: a transaction number is required only when the team can't find the transaction without it (recipient's number is enough; reversals never need it)",
    "usd_large_amount": "F19: dollar amounts >= large_amount_usd ($750) raise priority like >= 1,000,000 IQD",
    "handoff_note": "F17: escalated tickets get a short Arabic note for the receiving team, built from the extracted fields (no model call)",
    "ask_if_missing": "F11: the drafter asks for unverifiable details only if the ticket does not give them",
    "no_specific_followup": "F12: the drafter must not promise to send a specific answer, date or result",
    "fee_amount": "F6: the classifier extracts the disputed fee separately (fee_iqd)",
    "fee_followup": "F6b: a small extra call extracts the fee, only for fee tickets; the classifier prompt is unchanged",
    "no_now_urgency": "F7: 'هسه' (now) no longer raises priority (superseded by F15)",
    "no_urgency_words": "F15: no word raises priority; only the subcategory default and the large-amount rule",
    "warqa_usd": "F16: classifier prompt: 'ورقة' is a 100 USD note ('خمسين ورقة' = 5,000 USD), not 1,000 IQD",
    "unclear_template": "F8: unclear tickets get a fixed reply instead of a drafter call",
    "ask_if_unnamed": "F11b: with F11, the kind of place alone (the restaurant, the agent) does not count as its name, so the draft still asks for it",
    "team_summary": "F21: escalated tickets get a one-line Arabic summary of what happened in the team note (a small extra call; dropped if it has a number not in the ticket)",
    "duplicate_payment_hint": "F20: classifier hint: the same payment sent twice by mistake is a reversal request, not a wrong recipient or a shop payment",
}


# The configuration locked for the MVP runs on 29 Oct, after the API runs on dev and the author's two
# reviews (docs/experiments/LOG.md). PIPELINE_FIXES=mvp turns these on; flags stay off by default.
PRESETS = {
    "mvp": ("draft_check", "recheck_cross_team", "fee_followup", "ask_if_missing", "no_specific_followup",
            "fraud_secondary_cleanup", "no_urgency_words", "warqa_usd", "handoff_note", "reference_when_needed",
            "usd_large_amount", "duplicate_payment_hint", "team_summary"),
}


def active() -> frozenset[str]:
    names = {n.strip() for n in os.getenv("PIPELINE_FIXES", "").split(",") if n.strip()}
    for preset in names & PRESETS.keys():
        names = (names - {preset}) | set(PRESETS[preset])
    unknown = names - FIXES.keys()
    if unknown:
        raise ValueError(f"Unknown fix(es) in PIPELINE_FIXES: {', '.join(sorted(unknown))}")
    return frozenset(names)


def enabled(name: str) -> bool:
    if name not in FIXES:
        raise KeyError(name)
    return name in active()
