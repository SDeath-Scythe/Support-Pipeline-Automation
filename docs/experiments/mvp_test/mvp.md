# mvp on mvp_test

Fixes on: ask_if_missing, draft_check, duplicate_payment_hint, fee_followup, fraud_secondary_cleanup, handoff_note, no_specific_followup, no_urgency_words, recheck_cross_team, reference_when_needed, team_summary, usd_large_amount, warqa_usd · backend `api` · 2026-10-29T22:00:04 · compared with `mvp`

| Metric | mvp |
|---|---|
| Subcategory correct (first model) | 73/78 |
| Subcategory used correct | 77/78 |
| Secondary subcategory correct | 77/78 |
| Secondary correct (fraud tickets) | 6/6 |
| Wrong type, not escalated | 1 |
| Outcome matches gold | 69/78 |
| Draft given iff it should be | 78/78 |
| Priority correct | 77/78 |
| Amount correct | 77/78 |
| Fee correct (fee tickets) | — |
| Escalated | 6 |
| Flagged | 15 |
| Drafted (ready) | 57 |
| Drafts judged | 72 |
| Bad drafts (judge) | 4 |
| Bad drafts marked ready | 3 |
| Mean draft score (1-5) | 4.49 |
| Model calls (pipeline) | 174 |
| Judge: understood | 72/72 |
| Judge: grounded | 70/72 |
| Judge: no_promise | 72/72 |
| Judge: asks_right | 61/72 |
| Judge: safe | 72/72 |
| Judge: tone | 72/72 |
| Judge: clean | 70/72 |

## Every ticket

| Ticket | Gold | Got | Outcome | Priority | Flags | Draft score | Judge notes |
|---|---|---|---|---|---|---|---|
| mvp-0001 | forgot_pin | ✓ | drafted | P3 |  | 5 |  |
| mvp-0002 | unclear | ✓ | drafted | P3 |  | 5 |  |
| mvp-0003 | login_otp | ✓ | drafted | P2 |  | 4 | The draft mostly repeats the customer's own story back to them and offers little guidance, so it could be trimmed. |
| mvp-0004 | suspected_scam | ✓ | escalated | P1 | fraud | — |  |
| mvp-0005 | wrong_recipient | ✓ | drafted | P2 |  | 5 |  |
| mvp-0006 | unclear | ✓ | drafted | P3 |  | 5 |  |
| mvp-0007 | app_bug | ✓ | drafted | P3 |  | 5 |  |
| mvp-0008 | cash_in_not_credited | ✓ | flagged | P2 | missing:amount | 4 | The draft asks for the amount and the agent's name and location but not the approximate time of the transaction; the customer only said it was yesterday. |
| mvp-0009 | fees_limits_question | ✗ not_received | flagged ✗ (drafted) | P3 | recheck_used_second | 4 | The draft spends too long restating the ticket, and 'ولم تشوف' mixes formal Arabic into dialect; 'وما شفت' would read more naturally. |
| mvp-0010 | not_received | ✓ | flagged | P2 | missing:amount | 4 | The draft asks for the amount but not the exact date and time of the transfer; the customer only said 'two days ago'. |
| mvp-0011 | limit_upgrade | ✓ | drafted | P3 |  | 5 |  |
| mvp-0012 | fees_limits_question | ✗ not_received | flagged ✗ (drafted) | P3 | recheck_used_second | 4 | The draft treats this as a transfer investigation rather than a fee question, and its last sentence is a bit awkward and could be smoother. |
| mvp-0013 | forgot_pin | ✓ | flagged ✗ (drafted) | P3 | draft:asks_secret | 5 |  |
| mvp-0014 | suspected_scam | ✓ | escalated | P1 | fraud | — |  |
| mvp-0015 | card_payment_failed | ✓ | drafted | P3 |  | 5 |  |
| mvp-0016 | suspected_scam | ✓ | escalated | P1 | fraud | — |  |
| mvp-0017 | complaint | ✓ | drafted | P3 |  | 5 |  |
| mvp-0018 | blocked_account | ✓ | drafted | P2 |  | 5 |  |
| mvp-0019 | app_bug | ✓ | drafted | P3 |  | 4 | The phrase 'گاعد أفهم' is slightly unnatural and would read better as 'أفهم'. |
| mvp-0020 | wrong_recipient | ✓ | flagged | P2 | missing:reference | 4 | The hint about finding the reference in the app's transfer history is a small unlisted procedure detail that the agent may want to check. |
| mvp-0021 | rejected_or_pending | ✓ | drafted | P3 |  | 4 | Slightly awkward phrasing ('انزعاجك من صارلك', 'نحن' instead of 'إحنا') could use a light touch-up. |
| mvp-0022 | bill_not_reflected | ✓ | drafted | P3 |  | 4 | The draft asks for the bill type, but the customer already said it was the internet bill. |
| mvp-0023 | unauthorized_charge | ✓ | escalated | P1 | fraud | — |  |
| mvp-0024 | topup_failed | ✓ | drafted | P3 |  | 5 |  |
| mvp-0025 | not_received | ✓ | drafted | P2 |  | 5 |  |
| mvp-0026 | rejected_or_pending | ✓ | drafted | P3 |  | 4 ⚠ | The draft says the team will contact the customer if photos are missing, a procedure detail not in Known facts; it should only say the verification team will check the request. |
| mvp-0027 | reversal_request | ✓ | drafted | P2 |  | 4 | The draft assumes the recipient is the customer's brother and adds 'دينار', and its 'تقصد' restatement reads like a question that is never posed, so it needs a small edit. |
| mvp-0028 | not_received | ✓ | drafted | P2 |  | 4 | The draft does not ask for the approximate time of yesterday's transfer, which the ticket does not include. |
| mvp-0029 | limit_upgrade | ✓ | drafted | P3 |  | 4 | The line 'ما أكدر أعطيك تفاصيل الخطوات هسه' sounds a bit blunt and could be softened. |
| mvp-0030 | delivery_or_activation | ✓ | drafted | P3 |  | 5 |  |
| mvp-0031 | merchant_payment | ✓ | drafted | P3 |  | 4 | Minor wording slip ('فهمت إن دفعت' should be 'فهمت إنك دفعت'); otherwise correct and asks only for the missing restaurant name. |
| mvp-0032 | merchant_payment | ✗ not_received | flagged ✗ (drafted) | P3 | recheck_used_second | 5 |  |
| mvp-0033 | wrong_recipient | ✓ | flagged | P2 | missing:amount | 5 |  |
| mvp-0034 | overcharged_fee | ✓ | drafted | P3 |  | 4 | The line 'بعدك ما حددنا منو الغلطان' sounds a bit awkward and could be smoothed. |
| mvp-0035 | wrong_recipient | ✓ | drafted | P2 |  | 5 |  |
| mvp-0036 | topup_failed | ✓ | drafted | P3 |  | 5 |  |
| mvp-0037 | bill_not_reflected | ✓ | drafted | P3 |  | 4 | The draft asks for the bill type even though the customer already said it is an internet bill and gave the amount. |
| mvp-0038 | rejected_or_pending | ✓ | drafted | P3 |  | 5 |  |
| mvp-0039 | blocked_account | ✓ | drafted | P2 |  | 4 | The closing line 'ما تحتاج تسوي شي حالياً' is an unsupported reassurance and may need softening. |
| mvp-0040 | forgot_pin | ✓ | drafted | P3 |  | 4 | Phrasing like 'وماكو قدرة تفتح الحساب' and the trailing 'بعد' sound slightly awkward and need a small polish. |
| mvp-0041 | not_received | ✓ | drafted | P2 |  | 3 ⚠ | The draft reads the slang 'ورقتين' as exactly 200 dollars, but the currency and amount are not confirmed, so it should ask for the amount instead of stating it. |
| mvp-0042 | cash_in_not_credited | ✓ | drafted | P2 |  | 5 |  |
| mvp-0043 | reversal_request | ✓ | flagged | P2 | missing:amount | 5 |  |
| mvp-0044 | blocked_account | ✓ | drafted | P2 |  | 5 |  |
| mvp-0045 | unauthorized_charge | ✓ | escalated | P1 | fraud | — |  |
| mvp-0046 | sim_change | ✓ | flagged ✗ (drafted) | P3 ✗ (P2) | recheck_used_second | 4 | The last sentence about the SIM change repeats the previous point and should be removed, and the draft mixes 'we' and 'I' in its apology. |
| mvp-0047 | overcharged_fee | ✓ | drafted | P3 |  | 4 | The draft asks for the agent's name and location but not for the amount withdrawn, which the ticket does not give. |
| mvp-0048 | not_received | ✓ | drafted | P2 |  | 4 | The draft does not ask for the approximate time of yesterday's transfer, which is still missing from the ticket. |
| mvp-0049 | complaint | ✓ | drafted | P3 |  | 5 |  |
| mvp-0050 | unauthorized_charge | ✓ | escalated | P1 | fraud | — |  |
| mvp-0051 | reversal_request | ✓ | drafted | P2 |  | 5 |  |
| mvp-0052 | reversal_request | ✓ | drafted | P2 |  | 5 |  |
| mvp-0053 | fees_limits_question | ✗ not_received | flagged ✗ (drafted) | P3 | recheck_used_second | 4 | The phrase 'ذو المرجع' is stiff formal Arabic and could be made more natural Iraqi. |
| mvp-0054 | not_received | ✓ | drafted | P1 |  | 4 | The draft does not ask for the approximate time of the transfer; the ticket gives only the day, so the time is still needed. |
| mvp-0056 | cash_in_not_credited | ✓ | flagged | P2 | missing:amount | 4 | The draft could also ask for the approximate time of the transaction, since the ticket only says 'this morning'. |
| mvp-0057 | not_received | ✓ | drafted | P1 |  | 4 | The draft adds 'دينار' to the amount although the customer only wrote '٢ مليون', which is a small assumption worth removing. |
| mvp-0058 | merchant_payment | ✓ | drafted | P3 |  | 5 |  |
| mvp-0059 | delivery_or_activation | ✓ | drafted | P3 |  | 5 |  |
| mvp-0061 | not_received | ✓ | drafted | P1 |  | 4 | The draft adds 'دينار' and assumes 7549422 is the transaction number, but the ticket states neither. |
| mvp-0062 | limit_upgrade | ✓ | drafted | P3 |  | 5 |  |
| mvp-0063 | delivery_or_activation | ✓ | drafted | P3 |  | 5 |  |
| mvp-0064 | sim_change | ✓ | drafted | P2 |  | 5 |  |
| mvp-0065 | login_otp | ✓ | drafted | P2 |  | 5 |  |
| mvp-0066 | overcharged_fee | ✓ | flagged ✗ (drafted) | P3 | missing:amount | 3 | The draft asks for the withdrawn amount but not the agent's name (only the area, Karrada, was given), and 'گصتك واضحة' reads awkwardly. |
| mvp-0067 | cash_in_not_credited | ✓ | drafted | P2 |  | 5 |  |
| mvp-0068 | complaint | ✗ fees_limits_question | flagged ✗ (drafted) | P3 | recheck_used_second | 4 ⚠ | The word "وياناً" has a stray tanween and should read "ويانا"; otherwise the draft is good. |
| mvp-0069 | cash_out_refused | ✓ | drafted | P3 |  | 4 | The customer visited two agents, but the draft asks for only one agent's name and location; it should ask for both. |
| mvp-0070 | not_received | ✓ | drafted | P1 |  | 4 | The draft does not ask for the exact date and time of the transfer (the ticket only says 'three days ago'), and it assumes the currency is dinar. |
| mvp-0071 | unclear | ✓ | flagged ✗ (drafted) | P3 | draft:unknown_number | 3 | The draft suggests a specialist team will look into gold prices; it should instead say this is outside the company's services and ask whether the customer needs help with their account. |
| mvp-0072 | login_otp | ✓ | drafted | P2 |  | 5 |  |
| mvp-0073 | wrong_recipient | ✓ | drafted | P2 |  | 5 |  |
| mvp-0074 | wrong_recipient | ✓ | drafted | P2 |  | 4 ⚠ | The word 'إلە' ends in a stray Kurdish letter (ە) instead of Arabic 'إله' and needs a one-character fix. |
| mvp-0075 | card_payment_failed | ✓ | drafted | P3 |  | 5 |  |
| mvp-0076 | cash_out_refused | ✓ | drafted | P3 |  | 5 |  |
| mvp-0077 | cash_out_refused | ✓ | drafted | P3 |  | 5 |  |
| mvp-0078 | topup_failed | ✓ | drafted | P3 |  | 4 | The first sentence is a long, clunky restatement (e.g. 'أكيد نفهم إزعاجك') that could be smoothed. |
| mvp-0079 | card_payment_failed | ✓ | drafted | P3 |  | 5 |  |
| mvp-0080 | app_bug | ✓ | drafted | P3 |  | 5 |  |
