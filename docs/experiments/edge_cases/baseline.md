# baseline on edge_cases

Fixes on: none · backend `cli` · 2026-10-20T12:04:43 · compared with `baseline`

| Metric | baseline |
|---|---|
| Subcategory correct | 15/15 |
| Outcome matches gold | 15/15 |
| Draft given iff it should be | 15/15 |
| Priority correct | 15/15 |
| Amount correct | 15/15 |
| Fee correct (fee tickets) | — |
| Escalated | 3 |
| Flagged | 3 |
| Drafted (ready) | 9 |
| Drafts judged | 12 |
| Bad drafts (judge) | 1 |
| Bad drafts marked ready | 1 |
| Mean draft score (1-5) | 4.42 |
| Model calls (pipeline) | 31 |
| Judge: understood | 12/12 |
| Judge: grounded | 11/12 |
| Judge: no_promise | 12/12 |
| Judge: asks_right | 8/12 |
| Judge: safe | 12/12 |
| Judge: tone | 12/12 |
| Judge: clean | 12/12 |

## Every ticket

| Ticket | Gold | Got | Outcome | Priority | Flags | Draft score | Judge notes |
|---|---|---|---|---|---|---|---|
| e01 | not_received | ✓ | drafted | P2 |  | 3 ⚠ | The draft turns the customer's 'خمسين' into '50,000 دينار', an amount the ticket never states, and it asks for nothing when it should confirm the amount and get the exact time of last night's transfer. |
| e02 | suspected_scam | ✓ | escalated | P1 | fraud | — |  |
| e03 | topup_failed | ✓ | flagged | P3 | missing:amount | 5 |  |
| e04 | wrong_recipient | ✓ | flagged | P2 | missing:reference | 5 |  |
| e05 | not_received | ✓ | drafted | P1 |  | 3 | The draft doesn't ask for the date and time of the transfer, and the phrasing 'حالياً نفهم' and 'رحنا نحول' is awkward. |
| e06 | app_bug | ✓ | drafted | P3 |  | 5 |  |
| e07 | unauthorized_charge | ✓ | escalated | P1 | fraud | — |  |
| e08 | cash_in_not_credited | ✓ | drafted | P2 |  | 4 | The draft asks for the agent's name and location but not the time of the transaction; the ticket gives only the day (Thursday). |
| e09 | fees_limits_question | ✓ | drafted | P3 |  | 4 | The phrase "مكتوب بي" reads awkwardly and should be "مكتوب بيه" or "مكتوب بيه مجاني". |
| e10 | delivery_or_activation | ✓ | drafted | P3 |  | 5 |  |
| e11 | sim_change | ✓ | drafted | P1 |  | 5 |  |
| e12 | unclear | ✓ | drafted | P3 |  | 5 |  |
| e13 | suspected_scam | ✓ | escalated | P1 | fraud | — |  |
| e14 | reversal_request | ✓ | flagged | P1 | missing:reference | 5 |  |
| e15 | bill_not_reflected | ✓ | drafted | P3 |  | 4 | The draft asks for the bill type even though the customer already said it is the electricity bill. |
