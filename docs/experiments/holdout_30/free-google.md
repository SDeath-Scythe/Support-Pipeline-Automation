# free-google on holdout_30

Fixes on: ask_if_missing, draft_check, fee_followup, fraud_secondary_cleanup, no_now_urgency, no_specific_followup, recheck_cross_team · backend `cli` · 2026-10-23T19:04:56 · compared with `F2+F3c+F6b+F7+F11+F12+F14b`

| Metric | F2+F3c+F6b+F7+F11+F12+F14b | free-google | Change |
|---|---|---|---|
| Subcategory correct (first model) | 28/30 | 27/30 | -1 worse |
| Subcategory used correct | 29/30 | 27/30 | -2 worse |
| Secondary subcategory correct | 30/30 | 30/30 |  |
| Secondary correct (fraud tickets) | 2/2 | 2/2 |  |
| Wrong type, not escalated | 1 | 1 |  |
| Outcome matches gold | 29/30 | 19/30 | -10 worse |
| Draft given iff it should be | 30/30 | 20/30 | -10 worse |
| Priority correct | 30/30 | 27/30 | -3 worse |
| Amount correct | 30/30 | 30/30 |  |
| Fee correct (fee tickets) | 2/2 | 0/2 | -2 worse |
| Escalated | 2 | 12 | +10 |
| Flagged | 1 | 1 |  |
| Drafted (ready) | 27 | 17 | -10 |
| Drafts judged | 28 | 18 | -10 |
| Bad drafts (judge) | 1 | 1 |  |
| Bad drafts marked ready | 1 | 0 | -1 better |
| Mean draft score (1-5) | 4.64 | 4.56 | -0.08 worse |
| Model calls (pipeline) | 68 | 47 | -21 better |
| Judge: understood | 28/28 | 18/18 | -10 worse |
| Judge: grounded | 28/28 | 18/18 | -10 worse |
| Judge: no_promise | 28/28 | 18/18 | -10 worse |
| Judge: asks_right | 25/28 | 14/18 | -11 worse |
| Judge: safe | 28/28 | 18/18 | -10 worse |
| Judge: tone | 28/28 | 18/18 | -10 worse |
| Judge: clean | 27/28 | 17/18 | -10 worse |

## Tickets that changed (28)

| Ticket | Targets | What changed |
|---|---|---|
| h01 | confusable | draft changed (score 4 → 4) |
| h02 | confusable | draft changed (score 5 → 5) |
| h03 | confusable | draft changed (score 5 → 5) |
| h04 | confusable | subcategory forgot_pin → None; outcome drafted → escalated; priority P3 → None; flags [] → ['model_error']; draft changed (score 5 → —) |
| h05 | confusable | draft changed (score 5 → 5) |
| h06 | confusable | draft changed (score 5 → 5) |
| h07 | confusable | outcome drafted → flagged; flags [] → ['draft:stray_latin']; draft changed (score 5 → 4) |
| h08 | confusable | draft changed (score 4 → 5) |
| h09 | confusable | draft changed (score 4 → 4) |
| h10 | confusable | draft changed (score 4 → 4) |
| h11 | info_given | draft changed (score 4 → 5) |
| h12 | info_given | draft changed (score 5 → 5) |
| h13 | info_given | draft changed (score 5 → 5) |
| h14 | info_given | draft changed (score 5 → 5) |
| h15 | info_given | draft changed (score 5 → 3) |
| h16 | promise_bait | draft changed (score 5 → 4) |
| h17 | promise_bait | outcome flagged → drafted; flags ['recheck_used_second'] → []; draft changed (score 5 → 4) |
| h18 | promise_bait | draft changed (score 5 → 5) |
| h19 | promise_bait | subcategory fees_limits_question → limit_upgrade; outcome drafted → escalated; flags [] → ['model_error']; draft changed (score 4 → —) |
| h20 | now | subcategory app_bug → None; outcome drafted → escalated; priority P3 → None; flags [] → ['model_error']; draft changed (score 5 → —) |
| h21 | urgent | outcome drafted → escalated; flags [] → ['model_error']; draft changed (score 5 → —) |
| h22 | unclear | outcome drafted → escalated; flags [] → ['model_error']; draft changed (score 5 → —) |
| h23 | unclear | draft changed (score 5 → 5) |
| h26 | arabizi | outcome drafted → escalated; flags [] → ['model_error']; draft changed (score 4 → —) |
| h27 | mixed_english | outcome drafted → escalated; priority P2 → None; flags [] → ['model_error']; draft changed (score 4 → —) |
| h28 | control | outcome drafted → escalated; flags [] → ['model_error']; draft changed (score 5 → —) |
| h29 | control | outcome drafted → escalated; flags [] → ['model_error']; draft changed (score 4 → —) |
| h30 | control | outcome drafted → escalated; flags [] → ['model_error']; draft changed (score 4 → —) |

## Every ticket

| Ticket | Gold | Got | Outcome | Priority | Flags | Draft score | Judge notes |
|---|---|---|---|---|---|---|---|
| h01 | fees_limits_question | ✓ | drafted | P3 |  | 4 | The wording is a bit stiff ('افتهمت مشكلتك') and could use a softer, more natural phrasing. |
| h02 | topup_failed | ✓ | drafted | P3 |  | 5 |  |
| h03 | card_payment_failed | ✓ | drafted | P3 |  | 5 |  |
| h04 | forgot_pin | ✗ None | escalated ✗ (drafted) | None ✗ (P3) | model_error | — |  |
| h05 | blocked_account | ✓ | drafted | P2 |  | 5 |  |
| h06 | wrong_recipient | ✓ | drafted | P2 |  | 5 |  |
| h07 | merchant_payment | ✓ | flagged ✗ (drafted) | P3 | draft:stray_latin | 4 ⚠ | The draft writes 'الـQR' in Latin letters attached to an Arabic prefix, but the customer wrote 'الكيو ار', so it should be in Arabic script. |
| h08 | cash_in_not_credited | ✓ | drafted | P2 |  | 5 |  |
| h09 | bill_not_reflected | ✓ | drafted | P3 |  | 4 | The draft asks for the bill type, but the customer already said it is the monthly mobile bill. |
| h10 | not_received | ✓ | drafted | P2 |  | 4 | The draft does not ask for the exact time of the transfer; the ticket only says 'from the morning'. |
| h11 | card_payment_failed | ✓ | drafted | P3 |  | 5 |  |
| h12 | overcharged_fee | ✓ | drafted | P3 |  | 5 |  |
| h13 | bill_not_reflected | ✓ | drafted | P3 |  | 5 |  |
| h14 | topup_failed | ✓ | drafted | P3 |  | 5 |  |
| h15 | cash_out_refused | ✓ | drafted | P3 |  | 3 | The draft never asks for the agent's name, which is needed and missing from the ticket, and it calls the agent a 'branch' (فرع). |
| h16 | delivery_or_activation | ✓ | drafted | P3 |  | 4 | Draft doesn't tell the customer that no exact date can be given yet, which they explicitly asked for; a short line on that would help. |
| h17 | wrong_recipient | ✗ reversal_request | drafted | P2 |  | 4 | The draft never asks for the recipient's number, which the company needs and the ticket does not give. |
| h18 | fees_limits_question | ✓ | drafted | P3 |  | 5 |  |
| h19 | limit_upgrade | ✓ | escalated ✗ (drafted) | P3 | model_error | — |  |
| h20 | app_bug | ✗ None | escalated ✗ (drafted) | None ✗ (P3) | model_error | — |  |
| h21 | topup_failed | ✓ | escalated ✗ (drafted) | P2 | model_error | — |  |
| h22 | unclear | ✓ | escalated ✗ (drafted) | P3 | model_error | — |  |
| h23 | unclear | ✓ | drafted | P3 |  | 5 |  |
| h24 | suspected_scam | ✓ | escalated | P1 | fraud | — |  |
| h25 | unauthorized_charge | ✓ | escalated | P1 | fraud | — |  |
| h26 | rejected_or_pending | ✓ | escalated ✗ (drafted) | P3 | model_error | — |  |
| h27 | sim_change | ✓ | escalated ✗ (drafted) | None ✗ (P2) | model_error | — |  |
| h28 | complaint | ✓ | escalated ✗ (drafted) | P3 | model_error | — |  |
| h29 | not_received | ✓ | escalated ✗ (drafted) | P1 | model_error | — |  |
| h30 | delivery_or_activation | ✓ | escalated ✗ (drafted) | P3 | model_error | — |  |
