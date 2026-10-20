# baseline on synthetic_20

Fixes on: none · backend `cli` · 2026-10-20T12:04:42 · compared with `baseline`

| Metric | baseline |
|---|---|
| Subcategory correct | 20/20 |
| Outcome matches gold | 19/20 |
| Draft given iff it should be | 19/20 |
| Priority correct | 20/20 |
| Amount correct | 19/20 |
| Fee correct (fee tickets) | — |
| Escalated | 3 |
| Flagged | 1 |
| Drafted (ready) | 16 |
| Drafts judged | 17 |
| Bad drafts (judge) | 1 |
| Bad drafts marked ready | 1 |
| Mean draft score (1-5) | 4.53 |
| Model calls (pipeline) | 43 |
| Judge: understood | 17/17 |
| Judge: grounded | 17/17 |
| Judge: no_promise | 17/17 |
| Judge: asks_right | 15/17 |
| Judge: safe | 17/17 |
| Judge: tone | 17/17 |
| Judge: clean | 16/17 |

## Every ticket

| Ticket | Gold | Got | Outcome | Priority | Flags | Draft score | Judge notes |
|---|---|---|---|---|---|---|---|
| s01 | wrong_recipient | ✓ | drafted | P2 |  | 5 |  |
| s02 | login_otp | ✓ | drafted | P2 |  | 4 | The first sentence restating the issue is clunky and needs a small rephrase. |
| s03 | blocked_account | ✓ | drafted | P2 |  | 4 | Saying the accounts team will explain the reason slightly overcommits; softening it to a general follow-up would be safer. |
| s04 | sim_change | ✓ | drafted | P2 |  | 5 |  |
| s05 | limit_upgrade | ✓ | drafted | P3 |  | 4 | The optional request for extra details about the customer's work or needed limit isn't required and could be trimmed. |
| s06 | cash_in_not_credited | ✓ | drafted | P1 |  | 4 | The draft asks for the agent's location again even though the ticket gives it (Palestine Street), and it does not ask for the exact date and time of the transaction. |
| s07 | overcharged_fee | ✓ | drafted | P3 |  | 5 |  |
| s08 | cash_out_refused | ✓ | drafted | P3 |  | 5 |  |
| s09 | delivery_or_activation | ✓ | drafted | P3 |  | 5 |  |
| s10 | bill_not_reflected | ✓ | drafted | P3 |  | 4 | The draft asks for the bill type, but the customer already said it is the electricity bill, and the amount is also given, so nothing further needs to be asked. |
| s11 | merchant_payment | ✓ | drafted | P3 |  | 5 |  |
| s12 | app_bug | ✓ | drafted | P3 |  | 5 |  |
| s13 | not_received | ✓ | flagged | P2 | missing:reference, missing:amount | 5 |  |
| s14 | unauthorized_charge | ✓ | escalated | P1 | fraud | — |  |
| s15 | topup_failed | ✓ | drafted | P3 |  | 5 |  |
| s16 | fees_limits_question | ✓ | drafted | P3 |  | 4 | The restating sentence is a bit robotic, and 'نسبة الرسوم بالضبط' implies a percentage-based fee and an exact answer, so it should be softened. |
| s17 | unclear | ✓ | drafted | P3 |  | 4 | Saying the team will reply about the dollar rate slightly implies a rate answer is coming; it could be softened. |
| s18 | reversal_request | ✓ | escalated ✗ (drafted) | P1 | recheck_disagreed | — |  |
| s19 | suspected_scam | ✓ | escalated | P1 | fraud | — |  |
| s20 | complaint | ✓ | drafted | P2 |  | 4 ⚠ | Typo 'وياانا' should be 'ويانا'; otherwise fine. |
