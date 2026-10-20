# rec-d1 on holdout_30

Fixes on: ask_if_missing, draft_check, fee_followup, no_now_urgency, no_specific_followup, recheck_cross_team · backend `cli` · 2026-10-20T14:10:20 · compared with `baseline`

| Metric | baseline | rec-d1 | Change |
|---|---|---|---|
| Subcategory correct (first model) | 28/30 | 28/30 |  |
| Subcategory used correct | 28/30 | 29/30 | +1 better |
| Wrong type, not escalated | 1 | 1 |  |
| Outcome matches gold | 29/30 | 29/30 |  |
| Draft given iff it should be | 29/30 | 30/30 | +1 better |
| Priority correct | 28/30 | 30/30 | +2 better |
| Amount correct | 30/30 | 30/30 |  |
| Fee correct (fee tickets) | 0/2 | 2/2 | +2 better |
| Escalated | 3 | 2 | -1 |
| Flagged | 0 | 1 | +1 |
| Drafted (ready) | 27 | 27 |  |
| Drafts judged | 27 | 28 | +1 |
| Bad drafts (judge) | 1 | 2 | +1 worse |
| Bad drafts marked ready | 1 | 2 | +1 worse |
| Mean draft score (1-5) | 4.41 | 4.61 | +0.2 better |
| Model calls (pipeline) | 63 | 68 | +5 worse |
| Judge: understood | 27/27 | 28/28 | +1 better |
| Judge: grounded | 27/27 | 28/28 | +1 better |
| Judge: no_promise | 27/27 | 28/28 | +1 better |
| Judge: asks_right | 21/27 | 25/28 | +4 better |
| Judge: safe | 27/27 | 28/28 | +1 better |
| Judge: tone | 27/27 | 28/28 | +1 better |
| Judge: clean | 26/27 | 26/28 |  |

## Tickets that changed (28)

| Ticket | Targets | What changed |
|---|---|---|
| h01 | confusable | draft changed (score 4 → 5) |
| h02 | confusable | draft changed (score 4 → 4) |
| h03 | confusable | draft changed (score 5 → 5) |
| h04 | confusable | draft changed (score 5 → 5) |
| h05 | confusable | draft changed (score 4 → 4) |
| h06 | confusable | draft changed (score 5 → 5) |
| h07 | confusable | draft changed (score 5 → 5) |
| h08 | confusable | draft changed (score 5 → 4) |
| h09 | confusable | draft changed (score 4 → 4) |
| h10 | confusable | draft changed (score 4 → 4) |
| h11 | info_given | draft changed (score 3 → 4) |
| h12 | info_given | draft changed (score 3 → 5) |
| h13 | info_given | draft changed (score 3 → 5) |
| h14 | info_given | draft changed (score 4 → 5) |
| h15 | info_given | draft changed (score 4 → 5) |
| h16 | promise_bait | draft changed (score 5 → 5) |
| h17 | promise_bait | outcome escalated → flagged; flags ['recheck_disagreed'] → ['recheck_used_second']; draft changed (score — → 5) |
| h18 | promise_bait | draft changed (score 5 → 4) |
| h19 | promise_bait | draft changed (score 5 → 5) |
| h20 | now | priority P2 → P3; draft changed (score 5 → 4) |
| h21 | urgent | draft changed (score 5 → 4) |
| h22 | unclear | draft changed (score 5 → 5) |
| h23 | unclear | draft changed (score 5 → 5) |
| h26 | arabizi | draft changed (score 5 → 5) |
| h27 | mixed_english | priority P1 → P2; draft changed (score 4 → 4) |
| h28 | control | draft changed (score 4 → 5) |
| h29 | control | draft changed (score 4 → 4) |
| h30 | control | draft changed (score 5 → 5) |

## Every ticket

| Ticket | Gold | Got | Outcome | Priority | Flags | Draft score | Judge notes |
|---|---|---|---|---|---|---|---|
| h01 | fees_limits_question | ✓ | drafted | P3 |  | 5 |  |
| h02 | topup_failed | ✓ | drafted | P3 |  | 4 | The draft says the money was 'withdrawn' (انسحبت), but the customer paid the agent in cash; this needs a small wording fix. |
| h03 | card_payment_failed | ✓ | drafted | P3 |  | 5 |  |
| h04 | forgot_pin | ✓ | drafted | P3 |  | 5 |  |
| h05 | blocked_account | ✓ | drafted | P2 |  | 4 ⚠ | Missing space in 'نتواصلويّاك' (should be 'نتواصل وياك'). |
| h06 | wrong_recipient | ✓ | drafted | P2 |  | 5 |  |
| h07 | merchant_payment | ✓ | drafted | P3 |  | 5 |  |
| h08 | cash_in_not_credited | ✓ | drafted | P2 |  | 4 | The opening 'أكو مشكلة بالنسبة لمبلغ' reads awkwardly, as if confirming a fault, and should be rephrased to acknowledge the customer's report. |
| h09 | bill_not_reflected | ✓ | drafted | P3 |  | 4 | The draft asks for the bill type, but the ticket already says it is a monthly mobile bill, so nothing more needed to be asked. |
| h10 | not_received | ✓ | drafted | P2 |  | 4 | The draft asks for nothing, but it should ask for the exact time of the transfer since the ticket only says 'from the morning'. |
| h11 | card_payment_failed | ✓ | drafted | P3 |  | 4 | The draft asks for the store name, but the customer already said the payment was on Noon. |
| h12 | overcharged_fee | ✓ | drafted | P3 |  | 5 |  |
| h13 | bill_not_reflected | ✓ | drafted | P3 |  | 5 |  |
| h14 | topup_failed | ✓ | drafted | P3 |  | 5 |  |
| h15 | cash_out_refused | ✓ | drafted | P3 |  | 5 |  |
| h16 | delivery_or_activation | ✓ | drafted | P3 |  | 5 |  |
| h17 | wrong_recipient | ✗ reversal_request | flagged ✗ (drafted) | P2 | recheck_used_second | 5 |  |
| h18 | fees_limits_question | ✓ | drafted | P3 |  | 4 | The phrase saying it cannot give any number or information sounds a bit blunt and could be softened. |
| h19 | limit_upgrade | ✗ fees_limits_question | drafted | P3 |  | 5 |  |
| h20 | app_bug | ✓ | drafted | P3 |  | 4 | Naming the internal queue 'الطابور العام' to the customer is awkward and should be replaced with a generic 'الفريق المختص'. |
| h21 | topup_failed | ✓ | drafted | P2 |  | 4 | The phrasing 'أدري انخصم منك' sounds slightly off; 'أفهم إنه انخصم منك' would read more naturally. |
| h22 | unclear | ✓ | drafted | P3 |  | 5 |  |
| h23 | unclear | ✓ | drafted | P3 |  | 5 |  |
| h24 | suspected_scam | ✓ | escalated | P1 | fraud | — |  |
| h25 | unauthorized_charge | ✓ | escalated | P1 | fraud | — |  |
| h26 | rejected_or_pending | ✓ | drafted | P3 |  | 5 |  |
| h27 | sim_change | ✓ | drafted | P2 |  | 4 ⚠ | The draft uses the English word 'SIM' (الـ SIM), which should be replaced with Arabic 'الشريحة'. |
| h28 | complaint | ✓ | drafted | P3 |  | 5 |  |
| h29 | not_received | ✓ | drafted | P1 |  | 4 | The draft adds 'دينار', a currency the customer did not state; otherwise it is ready to send. |
| h30 | delivery_or_activation | ✓ | drafted | P3 |  | 5 |  |
