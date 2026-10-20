# baseline-d1 on holdout_30

Fixes on: none · backend `cli` · 2026-10-20T14:08:48 · compared with `baseline`

| Metric | baseline | baseline-d1 | Change |
|---|---|---|---|
| Subcategory correct (first model) | 28/30 | 28/30 |  |
| Subcategory used correct | 28/30 | 28/30 |  |
| Wrong type, not escalated | 1 | 1 |  |
| Outcome matches gold | 29/30 | 29/30 |  |
| Draft given iff it should be | 29/30 | 29/30 |  |
| Priority correct | 28/30 | 28/30 |  |
| Amount correct | 30/30 | 30/30 |  |
| Fee correct (fee tickets) | 0/2 | 0/2 |  |
| Escalated | 3 | 3 |  |
| Flagged | 0 | 0 |  |
| Drafted (ready) | 27 | 27 |  |
| Drafts judged | 27 | 27 |  |
| Bad drafts (judge) | 1 | 3 | +2 worse |
| Bad drafts marked ready | 1 | 3 | +2 worse |
| Mean draft score (1-5) | 4.41 | 4.48 | +0.07 better |
| Model calls (pipeline) | 63 | 63 |  |
| Judge: understood | 27/27 | 27/27 |  |
| Judge: grounded | 27/27 | 26/27 | -1 worse |
| Judge: no_promise | 27/27 | 27/27 |  |
| Judge: asks_right | 21/27 | 21/27 |  |
| Judge: safe | 27/27 | 27/27 |  |
| Judge: tone | 27/27 | 27/27 |  |
| Judge: clean | 26/27 | 25/27 | -1 worse |

## Tickets that changed (26)

| Ticket | Targets | What changed |
|---|---|---|
| h01 | confusable | draft changed (score 4 → 5) |
| h02 | confusable | draft changed (score 4 → 5) |
| h03 | confusable | draft changed (score 5 → 5) |
| h04 | confusable | draft changed (score 5 → 4) |
| h05 | confusable | draft changed (score 4 → 4) |
| h06 | confusable | draft changed (score 5 → 5) |
| h07 | confusable | draft changed (score 5 → 5) |
| h08 | confusable | draft changed (score 5 → 5) |
| h09 | confusable | draft changed (score 4 → 4) |
| h10 | confusable | draft changed (score 4 → 4) |
| h11 | info_given | draft changed (score 3 → 4) |
| h12 | info_given | draft changed (score 3 → 3) |
| h13 | info_given | draft changed (score 3 → 4) |
| h14 | info_given | draft changed (score 4 → 5) |
| h15 | info_given | draft changed (score 4 → 4) |
| h16 | promise_bait | draft changed (score 5 → 5) |
| h18 | promise_bait | draft changed (score 5 → 5) |
| h19 | promise_bait | draft changed (score 5 → 4) |
| h20 | now | draft changed (score 5 → 5) |
| h21 | urgent | draft changed (score 5 → 5) |
| h22 | unclear | draft changed (score 5 → 5) |
| h26 | arabizi | draft changed (score 5 → 5) |
| h27 | mixed_english | draft changed (score 4 → 3) |
| h28 | control | draft changed (score 4 → 5) |
| h29 | control | draft changed (score 4 → 4) |
| h30 | control | draft changed (score 5 → 4) |

## Every ticket

| Ticket | Gold | Got | Outcome | Priority | Flags | Draft score | Judge notes |
|---|---|---|---|---|---|---|---|
| h01 | fees_limits_question | ✓ | drafted | P3 |  | 5 |  |
| h02 | topup_failed | ✓ | drafted | P3 |  | 5 |  |
| h03 | card_payment_failed | ✓ | drafted | P3 |  | 5 |  |
| h04 | forgot_pin | ✓ | drafted | P3 |  | 4 | The phrase 'وإلى ذلك الوقت' is slightly awkward and could be smoothed, but the draft is otherwise ready. |
| h05 | blocked_account | ✓ | drafted | P2 |  | 4 | The last sentence starts with a stray, ungrammatical 'وياكم' and should be smoothed (e.g. 'ونرجع نوافيك بالتفاصيل'). |
| h06 | wrong_recipient | ✓ | drafted | P2 |  | 5 |  |
| h07 | merchant_payment | ✓ | drafted | P3 |  | 5 |  |
| h08 | cash_in_not_credited | ✓ | drafted | P2 |  | 5 |  |
| h09 | bill_not_reflected | ✓ | drafted | P3 |  | 4 | The draft asks for the bill type, but the customer already said it is the monthly mobile bill. |
| h10 | not_received | ✓ | drafted | P2 |  | 4 | The draft says the case was already escalated, which the agent must confirm, and it could ask for the exact time of the transfer since the ticket only says 'this morning'. |
| h11 | card_payment_failed | ✓ | drafted | P3 |  | 4 | The draft asks for the store name, but the customer already said it was Noon, so that question should be removed. |
| h12 | overcharged_fee | ✓ | drafted | P3 |  | 3 | The draft asks for the agent's name and location, but the customer already gave both (الشرقاوي, شارع الربيعي). |
| h13 | bill_not_reflected | ✓ | drafted | P3 |  | 4 | The draft asks for the bill type, but the customer already said it was the water bill, and the amount is also given, so no question is needed. |
| h14 | topup_failed | ✓ | drafted | P3 |  | 5 |  |
| h15 | cash_out_refused | ✓ | drafted | P3 |  | 4 | The draft asks for the agent's location again even though the customer said it is near Al-Rahman mosque in Mansour; it should only ask for the agent's name. |
| h16 | delivery_or_activation | ✓ | drafted | P3 |  | 5 |  |
| h17 | wrong_recipient | ✗ reversal_request | escalated ✗ (drafted) | P2 | recheck_disagreed | — |  |
| h18 | fees_limits_question | ✓ | drafted | P3 |  | 5 |  |
| h19 | limit_upgrade | ✗ fees_limits_question | drafted | P3 |  | 4 | Saying the team will explain 'everything exactly' slightly over-commits and could be softened. |
| h20 | app_bug | ✓ | drafted | P2 ✗ (P3) |  | 5 |  |
| h21 | topup_failed | ✓ | drafted | P2 |  | 5 |  |
| h22 | unclear | ✓ | drafted | P3 |  | 5 |  |
| h23 | unclear | ✓ | drafted | P3 |  | 5 |  |
| h24 | suspected_scam | ✓ | escalated | P1 | fraud | — |  |
| h25 | unauthorized_charge | ✓ | escalated | P1 | fraud | — |  |
| h26 | rejected_or_pending | ✓ | drafted | P3 |  | 5 |  |
| h27 | sim_change | ✓ | drafted | P1 ✗ (P2) |  | 3 ⚠ | The draft asks where the code fails to arrive though nothing is needed for this issue, and uses the English word 'SIM' in 'شريحة الـ SIM' instead of just 'الشريحة'. |
| h28 | complaint | ✓ | drafted | P3 |  | 5 |  |
| h29 | not_received | ✓ | drafted | P1 |  | 4 ⚠ | The draft adds 'دينار', but the customer only said 'مليونين' without a currency; otherwise it asks only for the missing date and time. |
| h30 | delivery_or_activation | ✓ | drafted | P3 |  | 4 ⚠ | Typo 'رحتم نحول' should be 'راح نحول'. |
