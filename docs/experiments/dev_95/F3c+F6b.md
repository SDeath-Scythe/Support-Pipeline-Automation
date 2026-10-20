# F3c+F6b on dev_95

Fixes on: fee_followup, recheck_cross_team · backend `cli` · 2026-10-20T13:57:32 · compared with `baseline`

| Metric | baseline | F3c+F6b | Change |
|---|---|---|---|
| Subcategory correct (first model) | 90/95 | 90/95 |  |
| Subcategory used correct | 90/95 | 95/95 | +5 better |
| Wrong type, not escalated | 0 | 0 |  |
| Outcome matches gold | 90/95 | 90/95 |  |
| Draft given iff it should be | 90/95 | 95/95 | +5 better |
| Priority correct | 86/95 | 90/95 | +4 better |
| Amount correct | 77/79 | 77/79 |  |
| Fee correct (fee tickets) | 0/4 | 4/4 | +4 better |
| Escalated | 13 | 8 | -5 |
| Flagged | 6 | 11 | +5 |
| Drafted (ready) | 76 | 76 |  |
| Drafts judged | 82 | 87 | +5 |
| Bad drafts (judge) | 6 | 7 | +1 worse |
| Bad drafts marked ready | 6 | 7 | +1 worse |
| Mean draft score (1-5) | 4.52 | 4.54 | +0.02 better |
| Model calls (pipeline) | 199 | 215 | +16 worse |
| Judge: understood | 82/82 | 87/87 | +5 better |
| Judge: grounded | 79/82 | 83/87 | +4 better |
| Judge: no_promise | 79/82 | 84/87 | +5 better |
| Judge: asks_right | 68/82 | 73/87 | +5 better |
| Judge: safe | 82/82 | 87/87 | +5 better |
| Judge: tone | 81/82 | 86/87 | +5 better |
| Judge: clean | 81/82 | 86/87 | +5 better |

## Interaction with the single fixes

Expected = baseline + the change each fix made on its own. A non-zero difference means the fixes affect each other.

| Metric | Expected if independent | Observed | Difference |
|---|---|---|---|
| Subcategory used correct | 95 | 95 | +0 |
| Draft given iff it should be | 95 | 95 | +0 |
| Priority correct | 90 | 90 | +0 |
| Fee correct (fee tickets) | 3 | 4 | +1 |
| Escalated | 8 | 8 | +0 |
| Flagged | 11 | 11 | +0 |
| Drafts judged | 87 | 87 | +0 |
| Bad drafts (judge) | 7 | 7 | +0 |
| Bad drafts marked ready | 7 | 7 | +0 |
| Mean draft score (1-5) | 4.56 | 4.54 | -0.02 |
| Model calls (pipeline) | 213 | 215 | +2 |
| Judge: understood | 87 | 87 | +0 |
| Judge: grounded | 83 | 83 | +0 |
| Judge: no_promise | 84 | 84 | +0 |
| Judge: asks_right | 73 | 73 | +0 |
| Judge: safe | 87 | 87 | +0 |
| Judge: tone | 86 | 86 | +0 |
| Judge: clean | 86 | 86 | +0 |

## Tickets that changed (12)

| Ticket | Targets | What changed |
|---|---|---|
| f14 | F3,F6 | outcome escalated → flagged; priority P2 → P3; flags ['missing:reference', 'recheck_disagreed'] → ['recheck_used_second']; draft changed (score — → 4) |
| f17 | F6 | draft changed (score 5 → 5) |
| f18 | F6 | draft changed (score 4 → 5) |
| f19 | F6 | draft changed (score 5 → 5) |
| s07 |  | draft changed (score 5 → 5) |
| s16 |  | draft changed (score 4 → 4) |
| s18 |  | outcome escalated → flagged; flags ['recheck_disagreed'] → ['recheck_used_second']; draft changed (score — → 4) |
| m02 |  | outcome escalated → flagged; priority P2 → P3; flags ['recheck_disagreed'] → ['recheck_used_second']; draft changed (score — → 5) |
| m09 |  | outcome escalated → flagged; priority P2 → P3; flags ['missing:reference', 'recheck_disagreed'] → ['recheck_used_second']; draft changed (score — → 5) |
| m12 |  | draft changed (score 5 → 5) |
| m23 |  | outcome escalated → flagged; priority P2 → P3; flags ['missing:reference', 'recheck_disagreed'] → ['recheck_used_second']; draft changed (score — → 4) |
| e09 |  | draft changed (score 4 → 5) |

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
| f14 | fees_limits_question | ✗ not_received | flagged ✗ (drafted) | P3 | recheck_used_second | 4 | Phrase 'ويوافيك بالتفاصيل' leans slightly toward promising an explanation and the reply is a bit formal, but it is acceptable as a general next step. |
| f15 | topup_failed | ✓ | drafted | P3 |  | 5 |  |
| f16 | card_payment_failed | ✓ | drafted | P3 |  | 4 | Minor wording fix: 'دفعت بي' reads better as 'دفعت بيه', and the draft adds 'دينار' to the customer's amount without the ticket stating it. |
| f17 | overcharged_fee | ✓ | drafted | P3 |  | 5 |  |
| f18 | fees_limits_question | ✓ | drafted | P3 |  | 5 |  |
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
| s16 | fees_limits_question | ✓ | drafted | P3 |  | 4 ⚠ | The phrase 'نسبة الرسوم' implies the fee is a percentage, which is not in Known facts, so it should be reworded to just 'الرسوم'. |
| s17 | unclear | ✓ | drafted | P3 |  | 4 | Saying the team will reply about the dollar rate slightly implies a rate answer is coming; it could be softened. |
| s18 | wrong_recipient | ✗ reversal_request | flagged ✗ (drafted) | P1 | recheck_used_second | 4 | The draft adds 'دينار' to the amount although the customer never named a currency; this is minor but worth softening. |
| s19 | suspected_scam | ✓ | escalated | P1 | fraud | — |  |
| s20 | complaint | ✓ | drafted | P2 |  | 4 ⚠ | Typo 'وياانا' should be 'ويانا'; otherwise fine. |
| m01 | not_received | ✓ | drafted | P2 |  | 5 |  |
| m02 | forgot_pin | ✗ login_otp | flagged ✗ (drafted) | P3 | recheck_used_second | 5 |  |
| m03 | card_payment_failed | ✓ | drafted | P3 |  | 5 |  |
| m04 | topup_failed | ✓ | drafted | P3 |  | 5 |  |
| m05 | rejected_or_pending | ✓ | drafted | P3 |  | 5 |  |
| m06 | cash_out_refused | ✓ | drafted | P3 |  | 5 |  |
| m07 | app_bug | ✓ | drafted | P3 |  | 5 |  |
| m08 | limit_upgrade | ✓ | drafted | P3 |  | 4 | The word "للحين" in the last sentence reads awkwardly and should be removed or rephrased. |
| m09 | merchant_payment | ✗ not_received | flagged ✗ (drafted) | P3 | recheck_used_second | 5 |  |
| m10 | blocked_account | ✓ | drafted | P2 |  | 5 |  |
| m11 | wrong_recipient | ✓ | drafted | P2 |  | 5 |  |
| m12 | overcharged_fee | ✓ | drafted | P3 |  | 5 |  |
| m13 | bill_not_reflected | ✓ | drafted | P3 |  | 4 | The draft asks for the bill type, but the customer already said it was the internet bill, and both needed details are already in the ticket. |
| m14 | login_otp | ✓ | drafted | P2 |  | 5 |  |
| m15 | delivery_or_activation | ✓ | drafted | P3 |  | 5 |  |
| m16 | fees_limits_question | ✓ | drafted | P3 |  | 5 |  |
| m17 | complaint | ✓ | drafted | P3 |  | 5 |  |
| m18 | cash_in_not_credited | ✓ | drafted | P1 |  | 4 | The draft could also ask for the approximate time of the deposit, since the ticket only says 'the morning'. |
| m19 | reversal_request | ✓ | drafted | P2 |  | 4 | The phrase 'اللي ألغيتوا البيعة' reads awkwardly and could be smoothed to 'واللي ألغيتوا بيها البيعة'. |
| m20 | not_received | ✓ | flagged | P1 | missing:reference | 4 | The draft asks only for the transaction number and should also ask for the exact date and time of the transfer, since the ticket only says it has been about two days. |
| m21 | unauthorized_charge | ✓ | escalated | P1 | fraud | — |  |
| m22 | sim_change | ✓ | drafted | P2 |  | 4 | The phrase 'ما تنطيك العافية على الخط المسروق' is awkward and can read as negative; it should be removed or replaced with a normal sympathy line. |
| m23 | fees_limits_question | ✗ not_received | flagged ✗ (drafted) | P3 | recheck_used_second | 4 | Minor wording issue ("وواصل" reads awkwardly), and the draft adds "دينار" although the ticket gives no currency. |
| m24 | wrong_recipient | ✓ | flagged | P1 | missing:reference | 5 |  |
| m25 | card_payment_failed | ✓ | drafted | P3 |  | 4 ⚠ | The phrase 'ويأكدلك الإمكانية' implies the card limit can be raised, so it should become something neutral like 'يوضحلك إذا ممكن'. |
| m26 | not_received | ✓ | drafted | P2 |  | 3 ⚠ | The draft misstates the amount as 100,000 when the customer wrote 200,000, and it does not ask for the time of the transfer. |
| m27 | cash_in_not_credited | ✓ | drafted | P1 |  | 4 | "وللحين" is Gulf dialect, not Iraqi; "لهسه" would sound more natural. |
| m28 | unclear | ✓ | drafted | P3 |  | 5 |  |
| m29 | unclear | ✓ | drafted | P3 |  | 5 |  |
| m30 | suspected_scam | ✓ | escalated | P1 | fraud | — |  |
| e01 | not_received | ✓ | drafted | P2 |  | 3 ⚠ | The draft turns the customer's 'خمسين' into '50,000 دينار', an amount the ticket never states, and it asks for nothing when it should confirm the amount and get the exact time of last night's transfer. |
| e02 | suspected_scam | ✓ | escalated | P1 | fraud | — |  |
| e03 | topup_failed | ✓ | flagged | P3 | missing:amount | 5 |  |
| e04 | wrong_recipient | ✓ | flagged | P2 | missing:reference | 5 |  |
| e05 | not_received | ✓ | drafted | P1 |  | 3 | The draft doesn't ask for the date and time of the transfer, and the phrasing 'حالياً نفهم' and 'رحنا نحول' is awkward. |
| e06 | app_bug | ✓ | drafted | P3 |  | 5 |  |
| e07 | unauthorized_charge | ✓ | escalated | P1 | fraud | — |  |
| e08 | cash_in_not_credited | ✓ | drafted | P2 |  | 4 | The draft asks for the agent's name and location but not the time of the transaction; the ticket gives only the day (Thursday). |
| e09 | fees_limits_question | ✓ | drafted | P3 |  | 5 |  |
| e10 | delivery_or_activation | ✓ | drafted | P3 |  | 5 |  |
| e11 | sim_change | ✓ | drafted | P1 |  | 5 |  |
| e12 | unclear | ✓ | drafted | P3 |  | 5 |  |
| e13 | suspected_scam | ✓ | escalated | P1 | fraud | — |  |
| e14 | reversal_request | ✓ | flagged | P1 | missing:reference | 5 |  |
| e15 | bill_not_reflected | ✓ | drafted | P3 |  | 4 | The draft asks for the bill type even though the customer already said it is the electricity bill. |
