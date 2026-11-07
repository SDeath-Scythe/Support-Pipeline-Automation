"""Feature flags for candidate fixes under test. All are off unless named in PIPELINE_FIXES.

    PIPELINE_FIXES=some_fix python scripts/run_batch.py ...

A new idea is added here as a flag, measured with and without it (scripts/experiment.py), and then
either made the normal code path or deleted. On 30 Oct the 13 adopted fixes (F2, F3c, F6b, F11,
F12, F14b, F15, F16, F17, F18, F19, F20, F21) became the normal code and every dropped one was
deleted; their history is in docs/experiments/LOG.md and git.

On 5 Nov the three flags opened by the 1 Nov security review became the normal code (the author's
decision, for a regulated financial institution): hold_reason and sensitive_number are draft rules
that always run and block an approval (draft_check.py), and escalate_account_risk was changed into
the account_risk flag (run.py), which keeps the draft.

On 7 Nov four draft warnings found by the user tests were opened as flags, then six pipeline rules from
the same tests (fraud_secondary to instructions_in_ticket) and three prompt changes (draft_rules_ut,
amount_own_words, summary_qualifiers). The same day, after measuring them with and without, all but
summary_qualifiers became the normal code (ADOPTED below; the numbers are in docs/experiments/LOG.md).
summary_qualifiers stays a flag: its summaries still had an English word in 1 of 54 lines.
"""

from __future__ import annotations

import os

# Prompt change from the 7 Nov role-played test sessions (run.py; the prompt file is side by side in prompts/).
FIXES: dict[str, str] = {
    "summary_qualifiers": "team-note summary prompt summary_system.summary_qualifiers.md: keep the customer's own "
                          "qualifiers and denials, third person, about 15 words, Arabic only",
}

# Flags that became the normal code. Naming one in PIPELINE_FIXES is refused with what happened to it,
# so an old command line can't look as if it switched something on or off.
ADOPTED: dict[str, str] = {
    "hold_reason": "adopted on 5 Nov 2026: the draft rule always runs and blocks an approval",
    "sensitive_number": "adopted on 5 Nov 2026: the draft rule always runs and blocks an approval",
    "escalate_account_risk": "changed and adopted on 5 Nov 2026: a blocked account or a SIM change keeps "
                             "its draft and always gets the account_risk flag (no escalation)",
    # 7 Nov 2026: the draft warnings always run and warn (draft_check.KINDS); none blocks an approval.
    "claims_done": "adopted on 7 Nov 2026: the draft warning always runs (a refund, change or complaint said to be done)",
    "repeated_text": "adopted on 7 Nov 2026: the draft warning always runs (a second greeting or a repeated sentence)",
    "ask_missing": "adopted on 7 Nov 2026: the draft warning always runs and names the fields the draft never asks for",
    "dialect_words": "adopted on 7 Nov 2026: the draft warning always runs (a word from another dialect or stiff MSA)",
    # 7 Nov 2026: the code rules on the customer's text always run (run.py, ticket_rules.py).
    "fraud_secondary": "adopted on 7 Nov 2026: a fraud second type, from either model, always escalates as fraud",
    "secret_in_ticket": "adopted on 7 Nov 2026: a card number or code in the ticket always gets the flag and secret_spans",
    "strip_format_chars": "adopted on 7 Nov 2026: clean always drops invisible format characters; bidi_controls and "
                          "amount_disagreed always apply",
    "device_lost": "adopted on 7 Nov 2026: a lost phone with the wallet open always escalates to fraud, P1; "
                   "other_phone always applies",
    "complaint_risk": "adopted on 7 Nov 2026: a regulator threat or repeat contact always gets the flag",
    "instructions_in_ticket": "adopted on 7 Nov 2026: text aimed at the system always gets the quiet flag",
    # 7 Nov 2026: the prompt changes; the version under test replaced the prompt file.
    "draft_rules_ut": "adopted on 7 Nov 2026: its revised drafter prompt is now draft_system.md",
    "amount_own_words": "adopted on 7 Nov 2026: the drafter always gets the customer's own amount words, and the "
                        "amount_not_in_ticket warning always runs",
    # 7 Nov 2026, the second round of role-played test sessions: the code rules, measured cache-only.
    "secret_forms": "adopted on 7 Nov 2026 (second round): a code after «..», a card in groups of four with mixed "
                    "separators or one the customer calls their card, the card's code in words; «AG-2290» is an id; "
                    "the advice names the kind",
    "complaint_reasons": "adopted on 7 Nov 2026 (second round): complaint_risk reads a repeat contact said other ways, "
                         "needs a threat verb near the regulator words, and says which reason",
    "device_lost_negation": "adopted on 7 Nov 2026 (second round): a wallet said not to be open is not device_lost",
    "second_request_flag": "adopted on 7 Nov 2026 (second round): a drafted ticket with a second type is flagged "
                           "second_request",
}


def active() -> frozenset[str]:
    names = {n.strip() for n in os.getenv("PIPELINE_FIXES", "").split(",") if n.strip()}
    adopted = sorted(names & ADOPTED.keys())
    if adopted:
        raise ValueError("PIPELINE_FIXES names a fix that is now the normal code: "
                         + "; ".join(f"{n} ({ADOPTED[n]})" for n in adopted)
                         + ". Remove it from PIPELINE_FIXES.")
    unknown = names - FIXES.keys()
    if unknown:
        raise ValueError(f"Unknown fix(es) in PIPELINE_FIXES: {', '.join(sorted(unknown))}")
    return frozenset(names)


def enabled(name: str) -> bool:
    if name not in FIXES:
        raise KeyError(name)
    return name in active()
