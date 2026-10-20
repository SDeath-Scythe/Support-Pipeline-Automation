# recnoF6-c1 on dev_95

Fixes on: ask_if_missing, draft_check, no_now_urgency, no_specific_followup, recheck_cross_team · backend `cli` · 2026-10-20T13:55:47 · compared with `baseline`

| Metric | baseline | recnoF6-c1 | Change |
|---|---|---|---|
| Subcategory correct (first model) | 90/95 | 88/95 | -2 worse |
| Subcategory used correct | 90/95 | 95/95 | +5 better |
| Wrong type, not escalated | 0 | 0 |  |
| Outcome matches gold | 90/95 | 88/95 | -2 worse |
| Draft given iff it should be | 90/95 | 95/95 | +5 better |
| Priority correct | 86/95 | 93/95 | +7 better |
| Amount correct | 77/79 | 78/79 | +1 better |
| Fee correct (fee tickets) | 0/4 | 0/4 |  |
| Escalated | 13 | 8 | -5 |
| Flagged | 6 | 13 | +7 |
| Drafted (ready) | 76 | 74 | -2 |
| Drafts judged | 82 | 87 | +5 |
| Bad drafts (judge) | 6 | 1 | -5 better |
| Bad drafts marked ready | 6 | 1 | -5 better |
| Mean draft score (1-5) | 4.52 | 4.67 | +0.15 better |
| Model calls (pipeline) | 199 | 203 | +4 worse |
| Judge: understood | 82/82 | 87/87 | +5 better |
| Judge: grounded | 79/82 | 86/87 | +7 better |
| Judge: no_promise | 79/82 | 87/87 | +8 better |
| Judge: asks_right | 68/82 | 80/87 | +12 better |
| Judge: safe | 82/82 | 87/87 | +5 better |
| Judge: tone | 81/82 | 87/87 | +6 better |
| Judge: clean | 81/82 | 87/87 | +6 better |

## Tickets that changed (87)

| Ticket | Targets | What changed |
|---|---|---|
| f01 | F7 | priority P2 → P3; draft changed (score 5 → 5) |
| f02 | F7 | priority P2 → P3; draft changed (score 5 → 5) |
| f03 | F7 | priority P2 → P3; draft changed (score 5 → 4) |
| f04 | F7 | priority P1 → P2; draft changed (score 5 → 4) |
| f05 | F7,F2 | priority P2 → P3; draft changed (score 4 → 3) |
| f06 | F7 | draft changed (score 4 → 5) |
| f07 | F8 | draft changed (score 5 → 5) |
| f08 | F8 | draft changed (score 5 → 5) |
| f09 | F8 | draft changed (score 3 → 4) |
| f10 | F8 | draft changed (score 4 → 4) |
| f11 | F3 | draft changed (score 5 → 5) |
| f12 | F3 | draft changed (score 5 → 4) |
| f13 | F3 | draft changed (score 4 → 4) |
| f14 | F3,F6 | outcome escalated → flagged; priority P2 → P3; flags ['missing:reference', 'recheck_disagreed'] → ['recheck_used_second']; draft changed (score — → 5) |
| f15 | F3 | subcategory topup_failed → cash_in_not_credited; outcome drafted → flagged; flags [] → ['recheck_used_second']; draft changed (score 5 → 4) |
| f16 | F3 | draft changed (score 4 → 5) |
| f17 | F6 | draft changed (score 5 → 5) |
| f18 | F6 | draft changed (score 4 → 5) |
| f19 | F6 | draft changed (score 5 → 5) |
| f20 | F2 | draft changed (score 5 → 5) |
| f21 | F2 | draft changed (score 5 → 4) |
| f22 | F2 | draft changed (score 5 → 5) |
| f23 | F2 | draft changed (score 3 → 5) |
| f24 | F2 | draft changed (score 4 → 5) |
| f25 | control | draft changed (score 4 → 4) |
| f27 | control | draft changed (score 4 → 5) |
| f28 | control | draft changed (score 4 → 5) |
| f29 | control | draft changed (score 5 → 5) |
| f30 | control | draft changed (score 5 → 4) |
| s01 |  | draft changed (score 5 → 5) |
| s02 |  | draft changed (score 4 → 5) |
| s03 |  | draft changed (score 4 → 4) |
| s04 |  | draft changed (score 5 → 5) |
| s05 |  | draft changed (score 4 → 5) |
| s06 |  | draft changed (score 4 → 4) |
| s07 |  | draft changed (score 5 → 5) |
| s08 |  | draft changed (score 5 → 4) |
| s09 |  | draft changed (score 5 → 5) |
| s10 |  | draft changed (score 4 → 5) |
| s11 |  | draft changed (score 5 → 5) |
| s12 |  | draft changed (score 5 → 5) |
| s13 |  | draft changed (score 5 → 5) |
| s15 |  | draft changed (score 5 → 5) |
| s16 |  | draft changed (score 4 → 5) |
| s17 |  | draft changed (score 4 → 4) |
| s18 |  | outcome escalated → flagged; flags ['recheck_disagreed'] → ['recheck_used_second']; draft changed (score — → 4) |
| s20 |  | draft changed (score 4 → 5) |
| m01 |  | draft changed (score 5 → 5) |
| m02 |  | outcome escalated → flagged; priority P2 → P3; flags ['recheck_disagreed'] → ['recheck_used_second']; draft changed (score — → 5) |
| m03 |  | draft changed (score 5 → 5) |
| m04 |  | draft changed (score 5 → 5) |
| m05 |  | draft changed (score 5 → 5) |
| m06 |  | draft changed (score 5 → 5) |
| m07 |  | draft changed (score 5 → 5) |
| m08 |  | draft changed (score 4 → 5) |
| m09 |  | outcome escalated → flagged; priority P2 → P3; flags ['missing:reference', 'recheck_disagreed'] → ['recheck_used_second']; draft changed (score — → 5) |
| m10 |  | draft changed (score 5 → 4) |
| m11 |  | draft changed (score 5 → 5) |
| m12 |  | draft changed (score 5 → 5) |
| m13 |  | draft changed (score 4 → 5) |
| m14 |  | draft changed (score 5 → 4) |
| m15 |  | draft changed (score 5 → 5) |
| m16 |  | draft changed (score 5 → 5) |
| m17 |  | draft changed (score 5 → 5) |
| m18 |  | draft changed (score 4 → 4) |
| m19 |  | draft changed (score 4 → 5) |
| m20 |  | draft changed (score 4 → 4) |
| m22 |  | draft changed (score 4 → 5) |
| m23 |  | outcome escalated → flagged; priority P2 → P3; flags ['missing:reference', 'recheck_disagreed'] → ['recheck_used_second']; draft changed (score — → 5) |
| m24 |  | draft changed (score 5 → 5) |
| m25 |  | draft changed (score 4 → 5) |
| m26 |  | draft changed (score 3 → 4) |
| m27 |  | priority P1 → P2; draft changed (score 4 → 5) |
| m28 |  | draft changed (score 5 → 5) |
| m29 |  | draft changed (score 5 → 4) |
| e01 |  | draft changed (score 3 → 3) |
| e03 |  | draft changed (score 5 → 5) |
| e04 |  | draft changed (score 5 → 4) |
| e05 |  | draft changed (score 3 → 4) |
| e06 |  | subcategory app_bug → unclear; outcome drafted → flagged; flags [] → ['recheck_used_second']; draft changed (score 5 → 5) |
| e08 |  | draft changed (score 4 → 4) |
| e09 |  | draft changed (score 4 → 4) |
| e10 |  | draft changed (score 5 → 5) |
| e11 |  | priority P1 → P2; draft changed (score 5 → 5) |
| e12 |  | draft changed (score 5 → 5) |
| e14 |  | draft changed (score 5 → 5) |
| e15 |  | draft changed (score 4 → 5) |

## Every ticket

| Ticket | Gold | Got | Outcome | Priority | Flags | Draft score | Judge notes |
|---|---|---|---|---|---|---|---|
| f01 | rejected_or_pending | ✓ | drafted | P3 |  | 5 |  |
| f02 | forgot_pin | ✓ | drafted | P3 |  | 5 |  |
| f03 | app_bug | ✓ | drafted | P3 |  | 4 | The draft names the internal queue ('فريق الطابور العام') to the customer, which reads awkwardly and should just say 'the team'. |
| f04 | sim_change | ✓ | drafted | P2 |  | 4 | The phrase 'ومن هسه' reads awkwardly and should be 'وهسه'; otherwise the draft is fine. |
| f05 | fees_limits_question | ✓ | drafted | P3 |  | 3 | Saying the company has no confirmed information about its own limit sounds unprofessional, and the phrase 'نتمنى تبقى وياهم' is awkward, so both need rewording. |
| f06 | not_received | ✓ | drafted | P1 |  | 5 |  |
| f07 | unclear | ✓ | drafted | P3 |  | 5 |  |
| f08 | unclear | ✓ | drafted | P3 |  | 5 |  |
| f09 | unclear | ✓ | drafted | P3 |  | 4 | Saying the team will 'review and verify your request' is awkward for a simple branch-location question and could be reworded. |
| f10 | unclear | ✓ | drafted | P3 |  | 4 | The phrase 'تفضل اسأل وياك أي شي' is awkward and should be smoothed, e.g. 'تفضل اسأل عن أي شي تحتاجه'. |
| f11 | wrong_recipient | ✓ | drafted | P2 |  | 5 |  |
| f12 | blocked_account | ✓ | drafted | P2 |  | 4 | The first sentence awkwardly states the customer's problem back to them, and 'you don't need to do anything now' is a mild unsupported assurance. |
| f13 | rejected_or_pending | ✓ | drafted | P3 |  | 4 | The draft acknowledges the limit-upgrade need but does not link the next step to it, and 'ويشوف الموضوع' is vague, so a small edit would help. |
| f14 | fees_limits_question | ✗ not_received | flagged ✗ (drafted) | P3 | recheck_used_second | 5 |  |
| f15 | topup_failed | ✗ cash_in_not_credited | flagged ✗ (drafted) | P3 | recheck_used_second | 4 | The opening 'وصلتني مشكلتك وياك' is awkward and should be smoothed. |
| f16 | card_payment_failed | ✓ | drafted | P3 |  | 5 |  |
| f17 | overcharged_fee | ✓ | drafted | P3 |  | 5 |  |
| f18 | fees_limits_question | ✓ | drafted | P3 |  | 5 |  |
| f19 | overcharged_fee | ✓ | drafted | P3 |  | 5 |  |
| f20 | wrong_recipient | ✓ | drafted | P2 |  | 5 |  |
| f21 | topup_failed | ✓ | drafted | P3 |  | 4 | The line saying it cannot set a time or guarantee a result sounds a bit defensive and could be softened. |
| f22 | login_otp | ✓ | drafted | P2 |  | 5 |  |
| f23 | card_payment_failed | ✓ | drafted | P3 |  | 5 |  |
| f24 | complaint | ✓ | drafted | P3 |  | 5 |  |
| f25 | not_received | ✓ | drafted | P2 |  | 4 | The draft does not ask for the approximate time of the transfer; the ticket only says 'yesterday'. |
| f26 | suspected_scam | ✓ | escalated | P1 | fraud | — |  |
| f27 | delivery_or_activation | ✓ | drafted | P3 |  | 5 |  |
| f28 | bill_not_reflected | ✓ | drafted | P3 |  | 5 |  |
| f29 | merchant_payment | ✓ | drafted | P3 |  | 5 |  |
| f30 | cash_out_refused | ✓ | drafted | P3 |  | 4 | The ticket already names Karrada, so the request for the location could ask only for the exact spot, and the opening phrasing is a little stiff. |
| s01 | wrong_recipient | ✓ | drafted | P2 |  | 5 |  |
| s02 | login_otp | ✓ | drafted | P2 |  | 5 |  |
| s03 | blocked_account | ✓ | drafted | P2 |  | 4 | The closing line 'ولا تحتاج تسوي شي هسه' slightly asserts a procedure detail not given in Known facts, so the agent may want to soften it. |
| s04 | sim_change | ✓ | drafted | P2 |  | 5 |  |
| s05 | limit_upgrade | ✓ | drafted | P3 |  | 5 |  |
| s06 | cash_in_not_credited | ✓ | drafted | P1 |  | 4 | The draft asks for the agent's name and location but not the date and time of the cash-in, which the ticket only gives as roughly two days ago. |
| s07 | overcharged_fee | ✓ | drafted | P3 |  | 5 |  |
| s08 | cash_out_refused | ✓ | drafted | P3 |  | 4 | The draft mixes plural 'نعتذر' with singular 'فهمت', a small inconsistency worth smoothing. |
| s09 | delivery_or_activation | ✓ | drafted | P3 |  | 5 |  |
| s10 | bill_not_reflected | ✓ | drafted | P3 |  | 5 |  |
| s11 | merchant_payment | ✓ | drafted | P3 |  | 5 |  |
| s12 | app_bug | ✓ | drafted | P3 |  | 5 |  |
| s13 | not_received | ✓ | flagged | P2 | missing:reference, missing:amount | 5 |  |
| s14 | unauthorized_charge | ✓ | escalated | P1 | fraud | — |  |
| s15 | topup_failed | ✓ | drafted | P3 |  | 5 |  |
| s16 | fees_limits_question | ✓ | drafted | P3 |  | 5 |  |
| s17 | unclear | ✓ | drafted | P3 |  | 4 | The claim that exchange-rate questions are not handled here is not in Known facts, and 'حبيبي' is a bit too familiar; a small edit would fix both. |
| s18 | wrong_recipient | ✗ reversal_request | flagged ✗ (drafted) | P1 | recheck_used_second | 4 | The draft adds the currency 'دينار', which the customer never stated; otherwise it correctly asks only for the recipient number and leaves the daily limit to the team. |
| s19 | suspected_scam | ✓ | escalated | P1 | fraud | — |  |
| s20 | complaint | ✓ | drafted | P2 |  | 5 |  |
| m01 | not_received | ✓ | drafted | P2 |  | 5 |  |
| m02 | forgot_pin | ✗ login_otp | flagged ✗ (drafted) | P3 | recheck_used_second | 5 |  |
| m03 | card_payment_failed | ✓ | drafted | P3 |  | 5 |  |
| m04 | topup_failed | ✓ | drafted | P3 |  | 5 |  |
| m05 | rejected_or_pending | ✓ | drafted | P3 |  | 5 |  |
| m06 | cash_out_refused | ✓ | drafted | P3 |  | 5 |  |
| m07 | app_bug | ✓ | drafted | P3 |  | 5 |  |
| m08 | limit_upgrade | ✓ | drafted | P3 |  | 5 |  |
| m09 | merchant_payment | ✗ not_received | flagged ✗ (drafted) | P3 | recheck_used_second | 5 |  |
| m10 | blocked_account | ✓ | drafted | P2 |  | 4 | The phrase 'أكيد أكو مشكلة بحسابك' sounds awkward, as if confirming a fault, and should be reworded to something like 'نفهم إن حسابك انقفل'. |
| m11 | wrong_recipient | ✓ | drafted | P2 |  | 5 |  |
| m12 | overcharged_fee | ✓ | drafted | P3 |  | 5 |  |
| m13 | bill_not_reflected | ✓ | drafted | P3 |  | 5 |  |
| m14 | login_otp | ✓ | drafted | P2 |  | 4 | The repeated apology in the last sentence is redundant and could be trimmed. |
| m15 | delivery_or_activation | ✓ | drafted | P3 |  | 5 |  |
| m16 | fees_limits_question | ✓ | drafted | P3 |  | 5 |  |
| m17 | complaint | ✓ | drafted | P3 |  | 5 |  |
| m18 | cash_in_not_credited | ✓ | drafted | P1 |  | 4 | The draft could also ask for the approximate time of the deposit (the ticket only says 'morning'), and 'ولم تنزل' reads slightly formal instead of the Iraqi 'وما نزلت'. |
| m19 | reversal_request | ✓ | drafted | P2 |  | 5 |  |
| m20 | not_received | ✓ | flagged | P1 | missing:reference | 4 | The draft asks only for the transaction number and should also ask for the exact date and time of the transfer, since the ticket only says 'two days'. |
| m21 | unauthorized_charge | ✓ | escalated | P1 | fraud | — |  |
| m22 | sim_change | ✓ | drafted | P2 |  | 5 |  |
| m23 | fees_limits_question | ✗ not_received | flagged ✗ (drafted) | P3 | recheck_used_second | 5 |  |
| m24 | wrong_recipient | ✓ | flagged | P1 | missing:reference | 5 |  |
| m25 | card_payment_failed | ✓ | drafted | P3 |  | 5 |  |
| m26 | not_received | ✓ | drafted | P2 |  | 4 | The draft does not ask for the approximate time of the transfer; the ticket gives only the day, as 'yesterday'. |
| m27 | cash_in_not_credited | ✓ | drafted | P2 ✗ (P1) |  | 5 |  |
| m28 | unclear | ✓ | drafted | P3 |  | 5 |  |
| m29 | unclear | ✓ | drafted | P3 |  | 4 | The draft never says that phone repair shops are outside the company's services, so it reads as if it ignored the question. |
| m30 | suspected_scam | ✓ | escalated | P1 | fraud | — |  |
| e01 | not_received | ✓ | drafted | P2 |  | 3 ⚠ | The draft turns 'خمسين' into '50,000 دينار', which the ticket does not say, and it does not ask for the exact time of the transfer or for the exact amount. |
| e02 | suspected_scam | ✓ | escalated | P1 | fraud | — |  |
| e03 | topup_failed | ✓ | flagged | P3 | missing:amount | 5 |  |
| e04 | wrong_recipient | ✓ | flagged | P2 | missing:reference | 4 | The phrase 'وأكيد تدري هذا الشي يزعج' reads awkwardly and should become a plain apology; adding 'دينار' is a mild assumption not in the ticket. |
| e05 | not_received | ✓ | drafted | P1 |  | 4 | The draft does not ask for the exact date and time of the transfer; the ticket only says 'two days ago'. |
| e06 | app_bug | ✗ unclear | flagged ✗ (drafted) | P3 | recheck_used_second | 5 |  |
| e07 | unauthorized_charge | ✓ | escalated | P1 | fraud | — |  |
| e08 | cash_in_not_credited | ✓ | drafted | P2 |  | 4 | The draft asks for the agent's name and location but not the approximate time of the transaction; the ticket gives only the day. |
| e09 | fees_limits_question | ✓ | drafted | P3 |  | 4 | The closing line offers help 'about the transfer' even though the customer said the transfer was fine, so it would read better as a general offer of help. |
| e10 | delivery_or_activation | ✓ | drafted | P3 |  | 5 |  |
| e11 | sim_change | ✓ | drafted | P2 ✗ (P1) |  | 5 |  |
| e12 | unclear | ✓ | drafted | P3 |  | 5 |  |
| e13 | suspected_scam | ✓ | escalated | P1 | fraud | — |  |
| e14 | reversal_request | ✓ | flagged | P1 | missing:reference | 5 |  |
| e15 | bill_not_reflected | ✓ | drafted | P3 |  | 5 |  |
