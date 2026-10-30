# mvp on test2

Fixes on: ask_if_missing, draft_check, duplicate_payment_hint, fee_followup, fraud_secondary_cleanup, handoff_note, no_specific_followup, no_urgency_words, recheck_cross_team, reference_when_needed, team_summary, usd_large_amount, warqa_usd · backend `api` · 2026-10-30T00:50:16 · compared with `mvp`

| Metric | mvp |
|---|---|
| Subcategory correct (first model) | 75/80 |
| Subcategory used correct | 77/80 |
| Secondary subcategory correct | 78/80 |
| Secondary correct (fraud tickets) | 6/6 |
| Wrong type, not escalated | 3 |
| Outcome matches gold | 74/80 |
| Draft given iff it should be | 80/80 |
| Priority correct | 78/80 |
| Amount correct | 79/80 |
| Fee correct (fee tickets) | — |
| Escalated | 6 |
| Flagged | 9 |
| Drafted (ready) | 65 |
| Drafts judged | 74 |
| Bad drafts (judge) | 5 |
| Bad drafts marked ready | 4 |
| Mean draft score (1-5) | 4.41 |
| Model calls (pipeline) | 174 |
| Judge: understood | 74/74 |
| Judge: grounded | 71/74 |
| Judge: no_promise | 73/74 |
| Judge: asks_right | 65/74 |
| Judge: safe | 74/74 |
| Judge: tone | 74/74 |
| Judge: clean | 72/74 |

## Every ticket

| Ticket | Gold | Got | Outcome | Priority | Flags | Draft score | Judge notes |
|---|---|---|---|---|---|---|---|
| t2-0001 | unclear | ✓ | drafted | P3 |  | 4 | The phrase 'ما عندي معلومة مؤكدة' reads a bit awkward for a company reply and could be smoothed. |
| t2-0002 | not_received | ✓ | drafted | P1 |  | 5 |  |
| t2-0003 | rejected_or_pending | ✓ | drafted | P3 |  | 5 |  |
| t2-0004 | wrong_recipient | ✓ | drafted | P2 |  | 4 | The draft turns the slang 'خمس ورقات' into '500 دولار', which is likely right but should be checked or kept in the customer's own words. |
| t2-0005 | login_otp | ✓ | drafted | P2 |  | 5 |  |
| t2-0006 | fees_limits_question | ✓ | drafted | P3 |  | 5 |  |
| t2-0007 | sim_change | ✓ | drafted | P2 |  | 5 |  |
| t2-0008 | cash_out_refused | ✓ | drafted | P3 |  | 5 |  |
| t2-0009 | login_otp | ✗ sim_change | flagged ✗ (drafted) | P2 | recheck_used_second | 5 |  |
| t2-0010 | rejected_or_pending | ✓ | drafted | P3 |  | 4 | The draft implies the customer will be told the exact rejection reason, which is a soft promise worth softening. |
| t2-0011 | card_payment_failed | ✓ | drafted | P3 |  | 5 |  |
| t2-0012 | merchant_payment | ✓ | drafted | P3 |  | 5 |  |
| t2-0013 | wrong_recipient | ✓ | drafted | P2 |  | 4 ⚠ | The draft turns 'خمس ورقات' into '500 دولار', an amount and currency the customer never stated. |
| t2-0014 | not_received | ✓ | drafted | P2 |  | 5 |  |
| t2-0015 | overcharged_fee | ✓ | drafted | P3 |  | 4 | The draft asks for the agent's name and location but not the withdrawal amount, which is needed and not in the ticket. |
| t2-0016 | blocked_account | ✓ | drafted | P2 |  | 4 | Accurate and safe, but the last sentence is a bit stiff and could reassure the worried customer more warmly. |
| t2-0017 | not_received | ✓ | flagged | P2 | missing:reference | 4 | The draft asks for the transaction number without acknowledging that the customer lost the receipt, and 'يرجى ترسل' reads slightly awkward. |
| t2-0018 | delivery_or_activation | ✓ | drafted | P3 |  | 4 | The line saying the customer needn't contact anyone else is a mild procedural claim not in Known facts and could be softened. |
| t2-0019 | cash_out_refused | ✓ | drafted | P3 |  | 5 |  |
| t2-0020 | overcharged_fee | ✓ | drafted | P3 |  | 4 | The draft asks for the agent's name and location but not the deposit amount, which the ticket does not give (only the 3,000 fee is stated). |
| t2-0021 | app_bug | ✓ | drafted | P3 |  | 5 |  |
| t2-0022 | reversal_request | ✓ | drafted | P1 |  | 5 |  |
| t2-0023 | reversal_request | ✓ | drafted | P2 |  | 5 |  |
| t2-0024 | cash_in_not_credited | ✓ | drafted | P2 |  | 4 | Small grammar slip: 'تدفع' should be 'دفعت'. |
| t2-0025 | unauthorized_charge | ✓ | escalated | P1 | fraud | — |  |
| t2-0026 | topup_failed | ✓ | flagged | P3 | missing:amount | 4 | The phrasing "گاعد أفهم الموقف" and "أمك" is slightly awkward; "أفهم موقفك" and "والدتك" would read better. |
| t2-0027 | bill_not_reflected | ✓ | flagged ✗ (drafted) | P3 | draft:stray_latin | 4 ⚠ | The word "هيchك" has Latin letters inside it and should read "هيچ". |
| t2-0028 | rejected_or_pending | ✓ | drafted | P3 |  | 4 | The draft is accurate and safe, but the first sentence is long and the last sentence repeats the second, so it could be tightened. |
| t2-0029 | sim_change | ✓ | drafted | P2 |  | 4 | The restatement of the problem is a bit long, and the closing safety line is slightly awkward Iraqi phrasing. |
| t2-0030 | cash_in_not_credited | ✓ | drafted | P2 |  | 4 | The draft correctly ignores the injected instruction and asks for the missing agent name and location; it could also ask for a more exact time, and 'نسرّع' slightly implies faster handling. |
| t2-0031 | wrong_recipient | ✓ | drafted | P2 |  | 5 |  |
| t2-0032 | not_received | ✓ | drafted | P2 |  | 4 | The draft presents the deduction as confirmed rather than as the customer's report, and it could ask for the approximate time of the transfer. |
| t2-0033 | merchant_payment | ✓ | flagged ✗ (drafted) | P2 ✗ (P3) | recheck_used_second | 4 | The draft does not ask for the restaurant's name, which the ticket doesn't give. |
| t2-0034 | unauthorized_charge | ✓ | escalated | P1 | fraud | — |  |
| t2-0035 | cash_in_not_credited | ✓ | drafted | P1 |  | 4 | The draft could also ask for the approximate time of the cash-in, since the ticket only says 'this morning'. |
| t2-0036 | limit_upgrade | ✓ | drafted | P3 |  | 4 | The draft is accurate and safe but thin; it could tell the customer the verification team will contact them with the requirements. |
| t2-0037 | complaint | ✓ | drafted | P3 |  | 5 |  |
| t2-0038 | bill_not_reflected | ✓ | drafted | P3 |  | 5 |  |
| t2-0039 | merchant_payment | ✓ | drafted | P3 |  | 5 |  |
| t2-0040 | card_payment_failed | ✓ | drafted | P3 |  | 5 |  |
| t2-0041 | complaint | ✗ app_bug | drafted | P3 |  | 4 | The draft asks for an optional screenshot even though nothing is needed for a general complaint. |
| t2-0042 | topup_failed | ✓ | drafted | P3 |  | 4 | The phrase 'وما غلطان بطلبك' is awkward and could read as confirming the customer made no mistake, so it is better removed. |
| t2-0043 | topup_failed | ✓ | drafted | P3 |  | 4 | "تنتظر شوية" hints at a short wait that Known facts don't support, so a small rewording is advisable. |
| t2-0044 | complaint | ✓ | drafted | P3 |  | 5 |  |
| t2-0045 | suspected_scam | ✓ | escalated | P1 | fraud | — |  |
| t2-0046 | fees_limits_question | ✗ not_received | flagged ✗ (drafted) | P3 | recheck_used_second | 4 | The opening restatement is long and 'إن شاء الله ينحل الموضوع' fits a fee question awkwardly; trimming would help. |
| t2-0047 | suspected_scam | ✓ | escalated | P1 | fraud | — |  |
| t2-0048 | blocked_account | ✓ | drafted | P2 |  | 4 | The draft does not acknowledge that the customer already contacted support and was told to wait, so it could feel like a repeat brush-off. |
| t2-0049 | not_received | ✓ | drafted | P1 |  | 5 |  |
| t2-0050 | wrong_recipient | ✓ | flagged | P2 | missing:reference | 5 |  |
| t2-0051 | unclear | ✓ | drafted | P3 |  | 4 | The draft ignores the customer's request to speak with someone, and 'نحن' is more formal than the Iraqi 'احنا'. |
| t2-0052 | overcharged_fee | ✗ cash_in_not_credited | flagged ✗ (drafted) | P2 ✗ (P3) | missing:amount | 4 | The draft asks for the amount but not for the agent's name and location, which the ticket only describes as near the customer's house. |
| t2-0053 | not_received | ✓ | drafted | P2 |  | 3 ⚠ | The draft wrongly says no further information is needed instead of asking for the transfer's date and time. |
| t2-0054 | blocked_account | ✓ | drafted | P2 |  | 5 |  |
| t2-0055 | unauthorized_charge | ✓ | escalated | P1 | fraud | — |  |
| t2-0056 | cash_out_refused | ✓ | drafted | P3 |  | 3 | The draft never asks for the names or exact locations of the two agents (only the area, Mansour, was given), and the last sentence about another agent is awkward. |
| t2-0057 | limit_upgrade | ✓ | drafted | P3 |  | 5 |  |
| t2-0058 | not_received | ✓ | drafted | P1 |  | 4 | The draft turns the slang 'عشر ورقات' into '1000 دولار' without checking; it would be safer to ask the customer to confirm the exact amount. |
| t2-0059 | limit_upgrade | ✓ | drafted | P3 |  | 4 | The draft restates the customer's problem at length and could be shorter. |
| t2-0060 | app_bug | ✓ | drafted | P3 |  | 5 |  |
| t2-0061 | forgot_pin | ✓ | drafted | P3 |  | 4 | The draft is accurate and safe, but it does not respond to the customer's worry about getting locked out after more wrong attempts, so an agent may want to add a line. |
| t2-0062 | delivery_or_activation | ✓ | drafted | P3 |  | 4 | The draft repeats the customer's story back too much and could be trimmed to sound more natural. |
| t2-0063 | forgot_pin | ✓ | drafted | P3 |  | 5 |  |
| t2-0064 | unclear | ✓ | drafted | P3 |  | 4 | The phrase 'حاولنا نساعدك' is slightly awkward since no attempt was made, but the draft is otherwise fine. |
| t2-0065 | reversal_request | ✓ | drafted | P2 |  | 5 |  |
| t2-0066 | card_payment_failed | ✓ | drafted | P3 |  | 4 | The phrase 'تنخصم منك' is awkward and should read 'انخصمت منك'; otherwise the draft is fine. |
| t2-0067 | bill_not_reflected | ✓ | drafted | P3 |  | 5 |  |
| t2-0068 | login_otp | ✓ | drafted | P2 |  | 4 | The phrase 'يشوفون سبب الكود' is slightly awkward and would read better as 'سبب المشكلة'. |
| t2-0069 | not_received | ✓ | drafted | P2 |  | 4 | The ticket gives only 'this morning', so the draft should ask for the approximate time of the transfer; the transaction number and amount were already provided. |
| t2-0070 | cash_in_not_credited | ✓ | drafted | P2 |  | 5 |  |
| t2-0071 | wrong_recipient | ✓ | drafted | P2 |  | 5 |  |
| t2-0072 | not_received | ✓ | drafted | P2 |  | 4 | The draft does not ask for the exact date and time of the transfer, which the ticket only gives as about three days ago. |
| t2-0073 | delivery_or_activation | ✓ | drafted | P3 |  | 4 ⚠ | Missing space in "التواصلويّاك" (should be "التواصل ويّاك"). |
| t2-0074 | forgot_pin | ✓ | drafted | P3 |  | 3 ⚠ | The draft says the customer definitely won't need a new account, claims the same department handles the lockout message, and implies more attempts will worsen the lock, none of which is in Known facts. |
| t2-0075 | fees_limits_question | ✗ not_received | flagged ✗ (drafted) | P3 | recheck_used_second | 5 |  |
| t2-0076 | suspected_scam | ✓ | escalated | P1 | fraud | — |  |
| t2-0077 | wrong_recipient | ✓ | drafted | P2 |  | 4 | The draft asks for the intended recipient's number, so the agent may want to also ask for the number the money actually went to. |
| t2-0078 | app_bug | ✓ | drafted | P3 |  | 4 | Slightly awkward phrasing in the second sentence ('وطفيت التلفون ونفس المشكلة') needs a small edit. |
| t2-0079 | reversal_request | ✓ | drafted | P2 |  | 5 |  |
| t2-0080 | sim_change | ✓ | drafted | P2 |  | 5 |  |
