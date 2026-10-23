# free-groq on holdout_30

Fixes on: ask_if_missing, draft_check, fee_followup, fraud_secondary_cleanup, no_now_urgency, no_specific_followup, recheck_cross_team · backend `cli` · 2026-10-23T18:58:16 · compared with `F2+F3c+F6b+F7+F11+F12+F14b`

| Metric | F2+F3c+F6b+F7+F11+F12+F14b | free-groq | Change |
|---|---|---|---|
| Subcategory correct (first model) | 28/30 | 25/30 | -3 worse |
| Subcategory used correct | 29/30 | 26/30 | -3 worse |
| Secondary subcategory correct | 30/30 | 30/30 |  |
| Secondary correct (fraud tickets) | 2/2 | 2/2 |  |
| Wrong type, not escalated | 1 | 4 | +3 worse |
| Outcome matches gold | 29/30 | 24/30 | -5 worse |
| Draft given iff it should be | 30/30 | 30/30 |  |
| Priority correct | 30/30 | 27/30 | -3 worse |
| Amount correct | 30/30 | 30/30 |  |
| Fee correct (fee tickets) | 2/2 | 1/2 | -1 worse |
| Escalated | 2 | 2 |  |
| Flagged | 1 | 6 | +5 |
| Drafted (ready) | 27 | 22 | -5 |
| Drafts judged | 28 | 28 |  |
| Bad drafts (judge) | 1 | 8 | +7 worse |
| Bad drafts marked ready | 1 | 7 | +6 worse |
| Mean draft score (1-5) | 4.64 | 4.21 | -0.43 worse |
| Model calls (pipeline) | 68 | 64 | -4 better |
| Judge: understood | 28/28 | 28/28 |  |
| Judge: grounded | 28/28 | 25/28 | -3 worse |
| Judge: no_promise | 28/28 | 24/28 | -4 worse |
| Judge: asks_right | 25/28 | 24/28 | -1 worse |
| Judge: safe | 28/28 | 28/28 |  |
| Judge: tone | 28/28 | 28/28 |  |
| Judge: clean | 27/28 | 26/28 | -1 worse |

## Tickets that changed (28)

| Ticket | Targets | What changed |
|---|---|---|
| h01 | confusable | subcategory fees_limits_question → not_received; outcome drafted → flagged; priority P3 → P2; flags [] → ['missing:reference', 'draft:unknown_number']; draft changed (score 4 → 3) |
| h02 | confusable | subcategory topup_failed → cash_in_not_credited; priority P3 → P2; draft changed (score 5 → 3) |
| h03 | confusable | draft changed (score 5 → 5) |
| h04 | confusable | draft changed (score 5 → 5) |
| h05 | confusable | draft changed (score 5 → 4) |
| h06 | confusable | subcategory wrong_recipient → reversal_request; outcome drafted → flagged; flags [] → ['recheck_used_second']; draft changed (score 5 → 4) |
| h07 | confusable | draft changed (score 5 → 5) |
| h08 | confusable | outcome drafted → flagged; flags [] → ['draft:unknown_number']; draft changed (score 4 → 5) |
| h09 | confusable | draft changed (score 4 → 4) |
| h10 | confusable | outcome drafted → flagged; flags [] → ['draft:unknown_number']; draft changed (score 4 → 4) |
| h11 | info_given | outcome drafted → flagged; flags [] → ['draft:unknown_number']; draft changed (score 4 → 5) |
| h12 | info_given | draft changed (score 5 → 5) |
| h13 | info_given | draft changed (score 5 → 4) |
| h14 | info_given | draft changed (score 5 → 5) |
| h15 | info_given | draft changed (score 5 → 4) |
| h16 | promise_bait | draft changed (score 5 → 4) |
| h17 | promise_bait | outcome flagged → drafted; flags ['recheck_used_second'] → []; draft changed (score 5 → 3) |
| h18 | promise_bait | draft changed (score 5 → 4) |
| h19 | promise_bait | subcategory fees_limits_question → limit_upgrade; draft changed (score 4 → 4) |
| h20 | now | draft changed (score 5 → 4) |
| h21 | urgent | outcome drafted → flagged; flags [] → ['draft:unknown_number']; draft changed (score 5 → 4) |
| h22 | unclear | draft changed (score 5 → 4) |
| h23 | unclear | draft changed (score 5 → 5) |
| h26 | arabizi | subcategory rejected_or_pending → blocked_account; priority P3 → P2; draft changed (score 4 → 4) |
| h27 | mixed_english | draft changed (score 4 → 4) |
| h28 | control | draft changed (score 5 → 4) |
| h29 | control | draft changed (score 4 → 4) |
| h30 | control | draft changed (score 4 → 5) |

## Every ticket

| Ticket | Gold | Got | Outcome | Priority | Flags | Draft score | Judge notes |
|---|---|---|---|---|---|---|---|
| h01 | fees_limits_question | ✗ not_received | flagged ✗ (drafted) | P2 ✗ (P3) | missing:reference, draft:unknown_number | 3 | The draft asks for a transaction number, date and time even though nothing is needed for this fees question, and it treats the question as a complaint to investigate. |
| h02 | topup_failed | ✗ cash_in_not_credited | drafted | P2 ✗ (P3) |  | 3 | The draft never asks for the phone number that was topped up, which is the key missing information, and instead asks for date, time and agent details that aren't required. |
| h03 | card_payment_failed | ✓ | drafted | P3 |  | 5 |  |
| h04 | forgot_pin | ✓ | drafted | P3 |  | 5 |  |
| h05 | blocked_account | ✓ | drafted | P2 |  | 4 | Small dialect edit: 'رح' is Levantine and should be 'راح' for Iraqi Arabic. |
| h06 | wrong_recipient | ✗ reversal_request | flagged ✗ (drafted) | P2 | recheck_used_second | 4 ⚠ | The draft writes the amount as "75,000 IQD", adding an English currency code the ticket did not use, and "للغلط" is slightly awkward phrasing. |
| h07 | merchant_payment | ✓ | drafted | P3 |  | 5 |  |
| h08 | cash_in_not_credited | ✓ | flagged ✗ (drafted) | P2 | draft:unknown_number | 5 |  |
| h09 | bill_not_reflected | ✓ | drafted | P3 |  | 4 | The phrase 'وما وصلها لشركة الاتصالات' is slightly awkward and would read better as 'وما وصلت لشركة الاتصالات'. |
| h10 | not_received | ✓ | flagged ✗ (drafted) | P2 | draft:unknown_number | 4 | The draft does not ask for the date and exact time of the transfer (the ticket only says 'since the morning'), and it assumes the currency is dinar. |
| h11 | card_payment_failed | ✓ | flagged ✗ (drafted) | P3 | draft:unknown_number | 5 |  |
| h12 | overcharged_fee | ✓ | drafted | P3 |  | 5 |  |
| h13 | bill_not_reflected | ✓ | drafted | P3 |  | 4 ⚠ | The draft claims 'استلمنا سدادك' (we received your payment), which is not a known fact and should only acknowledge the customer's report. |
| h14 | topup_failed | ✓ | drafted | P3 |  | 5 |  |
| h15 | cash_out_refused | ✓ | drafted | P3 |  | 4 | The phrase 'والكاش جهازه عاطل' is garbled; it should say the agent told the customer his device was broken. |
| h16 | delivery_or_activation | ✓ | drafted | P3 |  | 4 ⚠ | The draft promises an update 'soon' (قريباً), a timing commitment not in Known facts, so that word should be removed. |
| h17 | wrong_recipient | ✗ reversal_request | drafted | P2 |  | 3 ⚠ | The draft does not ask for the recipient's number, which is needed, and 'ويكّده' is a malformed word; it also does not tell the customer that no timeline can be given yet. |
| h18 | fees_limits_question | ✓ | drafted | P3 |  | 4 | The draft names the internal queue 'الطابور العام' to the customer, which should be replaced with a general phrase like 'الفريق المختص'. |
| h19 | limit_upgrade | ✓ | drafted | P3 |  | 4 | The draft does not directly acknowledge the customer's specific questions about how long it takes and which documents are needed; a small edit would make it feel more responsive. |
| h20 | app_bug | ✓ | drafted | P3 |  | 4 ⚠ | The phrase 'يجاوبك قريباً' promises a reply 'soon', a time not given in Known facts, and 'إنّو' sounds more Levantine than Iraqi. |
| h21 | topup_failed | ✓ | flagged ✗ (drafted) | P2 | draft:unknown_number | 4 | The phrase 'خصم 30 000 عراقي' is awkward and should be 'انخصم منك 30 ألف دينار'; a short apology for the repeat issue would also help. |
| h22 | unclear | ✓ | drafted | P3 |  | 4 | The second sentence about the team reviewing and replying 'as soon as possible' is premature before the customer has stated an issue and could be trimmed. |
| h23 | unclear | ✓ | drafted | P3 |  | 5 |  |
| h24 | suspected_scam | ✓ | escalated | P1 | fraud | — |  |
| h25 | unauthorized_charge | ✓ | escalated | P1 | fraud | — |  |
| h26 | rejected_or_pending | ✗ blocked_account | drafted | P2 ✗ (P3) |  | 4 ⚠ | The draft promises an update 'soon' (قريبًا), which is a timeline not in Known facts and should be removed. |
| h27 | sim_change | ✓ | drafted | P2 |  | 4 ⚠ | The draft promises an update 'قريباً' (soon), a timing commitment that is not in Known facts and should be removed. |
| h28 | complaint | ✓ | drafted | P3 |  | 4 | Naming the internal queue 'الطابور العام' to the customer sounds odd and should probably be rephrased as 'الفريق المختص'. |
| h29 | not_received | ✓ | drafted | P1 |  | 4 ⚠ | The draft adds 'دينار' as the currency, but the customer only said 'مليونين' without naming one. |
| h30 | delivery_or_activation | ✓ | drafted | P3 |  | 5 |  |
