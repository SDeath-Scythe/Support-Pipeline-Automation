# baseline on fixes_30

Fixes on: none · backend `cli` · 2026-10-20T11:53:34 · compared with `baseline`

| Metric | baseline |
|---|---|
| Subcategory correct | 29/30 |
| Outcome matches gold | 29/30 |
| Draft given iff it should be | 29/30 |
| Priority correct | 24/30 |
| Amount correct | 30/30 |
| Fee correct (fee tickets) | 0/4 |
| Escalated | 2 |
| Flagged | 0 |
| Drafted (ready) | 28 |
| Drafts judged | 28 |
| Bad drafts (judge) | 2 |
| Bad drafts marked ready | 2 |
| Mean draft score (1-5) | 4.5 |
| Model calls (pipeline) | 63 |
| Judge: understood | 28/28 |
| Judge: grounded | 27/28 |
| Judge: no_promise | 26/28 |
| Judge: asks_right | 23/28 |
| Judge: safe | 28/28 |
| Judge: tone | 28/28 |
| Judge: clean | 28/28 |

## Every ticket

| Ticket | Gold | Got | Outcome | Priority | Flags | Draft score | Judge notes |
|---|---|---|---|---|---|---|---|
| f01 | rejected_or_pending | ✓ | drafted | P2 ✗ (P3) |  | 5 |  |
| f02 | forgot_pin | ✓ | drafted | P2 ✗ (P3) |  | 5 |  |
| f03 | app_bug | ✓ | drafted | P2 ✗ (P3) |  | 5 |  |
| f04 | sim_change | ✓ | drafted | P1 ✗ (P2) |  | 5 |  |
| f05 | fees_limits_question | ✓ | drafted | P2 ✗ (P3) |  | 4 | The closing 'إن شاء الله ما يتأخرون عليك' loosely hints at a quick reply with no listed response time and could be softened. |
| f06 | not_received | ✓ | drafted | P1 |  | 4 | Minor: the draft assumes the currency is dinar and says 'حتى نسرّع الفحص', which slightly implies faster handling. |
| f07 | unclear | ✓ | drafted | P3 |  | 5 |  |
| f08 | unclear | ✓ | drafted | P3 |  | 5 |  |
| f09 | unclear | ✓ | drafted | P3 |  | 3 ⚠ | The draft assumes a Basra branch exists and promises to send its address, which is not in Known facts; it also asks for the customer's area although nothing is needed. |
| f10 | unclear | ✓ | drafted | P3 |  | 4 | The phrase "نوصل لك للجواب" is a bit awkward and reads better as "نوصلك للجواب". |
| f11 | wrong_recipient | ✓ | drafted | P2 |  | 5 |  |
| f12 | blocked_account | ✓ | drafted | P2 |  | 5 |  |
| f13 | rejected_or_pending | ✓ | drafted | P3 |  | 4 | The limit question is only vaguely deferred; the agent might tighten the last sentence. |
| f14 | fees_limits_question | ✗ not_received | escalated ✗ (drafted) | P2 ✗ (P3) | missing:reference, recheck_disagreed | — |  |
| f15 | topup_failed | ✓ | drafted | P3 |  | 5 |  |
| f16 | card_payment_failed | ✓ | drafted | P3 |  | 4 | Minor wording fix: 'دفعت بي' reads better as 'دفعت بيه', and the draft adds 'دينار' to the customer's amount without the ticket stating it. |
| f17 | overcharged_fee | ✓ | drafted | P3 |  | 5 |  |
| f18 | fees_limits_question | ✓ | drafted | P3 |  | 4 | The draft adds 'دينار' to the amounts, which the customer didn't say, though it is a reasonable assumption. |
| f19 | overcharged_fee | ✓ | drafted | P3 |  | 5 |  |
| f20 | wrong_recipient | ✓ | drafted | P2 |  | 5 |  |
| f21 | topup_failed | ✓ | drafted | P3 |  | 5 |  |
| f22 | login_otp | ✓ | drafted | P2 |  | 5 |  |
| f23 | card_payment_failed | ✓ | drafted | P3 |  | 3 ⚠ | The draft asks for the store name although the ticket already says Amazon, and saying the department will confirm the refund date implies a refund is coming. |
| f24 | complaint | ✓ | drafted | P3 |  | 4 | The draft does not acknowledge the compensation demand or say the team will review the complaint, which would reassure an angry repeat complainant. |
| f25 | not_received | ✓ | drafted | P2 |  | 4 | The draft does not ask for the approximate time of the transfer; the ticket only says 'yesterday'. |
| f26 | suspected_scam | ✓ | escalated | P1 | fraud | — |  |
| f27 | delivery_or_activation | ✓ | drafted | P3 |  | 4 | Asks for the exact error message even though no information is needed for this issue; the optional ask could be dropped. |
| f28 | bill_not_reflected | ✓ | drafted | P3 |  | 4 | The draft asks for the bill type, but the customer already said it is the internet bill, so the closing question should be removed. |
| f29 | merchant_payment | ✓ | drafted | P3 |  | 5 |  |
| f30 | cash_out_refused | ✓ | drafted | P3 |  | 5 |  |
