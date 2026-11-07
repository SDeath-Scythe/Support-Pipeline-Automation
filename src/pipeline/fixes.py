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

On 7 Nov four draft warnings found by the user tests were opened as flags (FIXES below), off by default,
and six pipeline rules from the same tests (fraud_secondary to instructions_in_ticket), then three prompt
changes (draft_rules_ut, amount_own_words, summary_qualifiers).
"""

from __future__ import annotations

import os

# Draft warnings opened after the 7 Nov user tests (draft_check.py, FLAG_KINDS); each warns, none blocks.
FIXES: dict[str, str] = {
    "claims_done": "draft check: warn when the draft says a refund, an account or number change or a complaint "
                   "is already done (forwarding to a team stays allowed)",
    "repeated_text": "draft check: warn on a second greeting or a sentence repeated almost word for word",
    "ask_missing": "draft check: warn, naming them, about the fields the drafter was told to ask for that the "
                   "draft never mentions; a lost receipt is not asked for its reference",
    "dialect_words": "draft check: warn on a word from another dialect or stiff standard Arabic (عشان، وايد، رح، "
                     "يرجى، التي ...)",
    # Pipeline rules opened after the same tests (run.py, ticket_rules.py).
    "fraud_secondary": "a second type in an always-escalate category (fraud), from either model, escalates the "
                       "ticket as fraud (fraud team, P1); the main type stays in the team note as «طلب ثاني»",
    "secret_in_ticket": "a card number or a code after its word (PIN, OTP, الرمز السري، الباسورد ...) in the "
                        "customer's text: flag secret_in_ticket, a line in the team note, and secret_spans for the page",
    "strip_format_chars": "clean drops invisible format characters (zero-width, direction controls, BOM); direction "
                          "controls add bidi_controls, and different amounts from the two models add amount_disagreed",
    "device_lost": "a lost or stolen phone with the wallet or account open on it escalates to the fraud team, P1; "
                   "writing from another person's phone adds other_phone",
    "complaint_risk": "a threat to complain to a regulator or a repeat contact (البنك المركزي، الجهات الرقابية، "
                      "اشتكي عليكم، ثالث مرة ...): flag complaint_risk; the priority does not change",
    "instructions_in_ticket": "text aimed at the system (a forged tag, SYSTEM:, ignore previous instructions, "
                              "تجاهل التعليمات، اكتب للزبون ...): a quiet flag; the outcome does not change",
    # Prompt changes from the same tests (draft.py, run.py; the prompt files are side by side in prompts/).
    "draft_rules_ut": "drafter prompt draft_system.draft_rules_ut.md: a second request is followed up, never said to "
                      "be registered; no guessed gender («يمّه» is an exclamation); a blocked account or SIM change "
                      "does not hear that nothing more is needed; ask only for what the ask lines name; text that "
                      "instructs the system gets no answer; plain Baghdadi words; every sentence complete",
    "amount_own_words": "an amount not written as a number in the ticket («عشر ورقات») reaches the drafter as the "
                        "customer's own words, not the converted number; draft check: warn on an amount the ticket "
                        "writes neither as a number nor in number words in the same unit («1000 دولار» for «عشر ورقات»)",
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
