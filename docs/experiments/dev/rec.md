# rec on dev

Fixes on: ask_if_missing, draft_check, fee_followup, fraud_secondary_cleanup, handoff_note, no_specific_followup, no_urgency_words, recheck_cross_team, reference_when_needed, usd_large_amount · backend `api` · 2026-10-29T12:07:17 · compared with `baseline`

| Metric | baseline | rec | Change |
|---|---|---|---|
| Subcategory correct (first model) | 233/240 | 233/240 |  |
| Subcategory used correct | 233/240 | 233/240 |  |
| Secondary subcategory correct | 231/240 | 233/240 | +2 better |
| Secondary correct (fraud tickets) | 17/17 | 17/17 |  |
| Wrong type, not escalated | 4 | 6 | +2 worse |
| Outcome matches gold | 220/240 | 227/240 | +7 better |
| Draft given iff it should be | 235/240 | 239/240 | +4 better |
| Priority correct | 193/240 | 234/240 | +41 better |
| Amount correct | 233/240 | 233/240 |  |
| Fee correct (fee tickets) | — | — |  |
| Escalated | 22 | 18 | -4 |
| Flagged | 30 | 27 | -3 |
| Drafted (ready) | 188 | 195 | +7 |
| Drafts judged | 218 | 222 | +4 |
| Bad drafts (judge) | 22 | 25 | +3 worse |
| Bad drafts marked ready | 20 | 21 | +1 worse |
| Mean draft score (1-5) | 4.45 | 4.45 |  |
| Model calls (pipeline) | 505 | 525 | +20 worse |
| Judge: understood | 218/218 | 222/222 | +4 better |
| Judge: grounded | 211/218 | 213/222 | +2 better |
| Judge: no_promise | 217/218 | 222/222 | +5 better |
| Judge: asks_right | 185/218 | 180/222 | -5 worse |
| Judge: safe | 218/218 | 222/222 | +4 better |
| Judge: tone | 215/218 | 220/222 | +5 better |
| Judge: clean | 204/218 | 206/222 | +2 better |

## Tickets that changed (222)

| Ticket | Targets | What changed |
|---|---|---|
| dev-0001 |  | draft changed (score 5 → 5) |
| dev-0002 |  | outcome flagged → drafted; priority P1 → P2; flags ['missing:reference'] → []; draft changed (score 5 → 3) |
| dev-0003 |  | priority P2 → P3; draft changed (score 4 → 5) |
| dev-0004 |  | priority P2 → P3; draft changed (score 4 → 5) |
| dev-0005 |  | priority P2 → P3; draft changed (score 4 → 4) |
| dev-0006 |  | draft changed (score 5 → 5) |
| dev-0007 |  | priority P2 → P3; draft changed (score 5 → 5) |
| dev-0008 |  | draft changed (score 4 → 3) |
| dev-0009 |  | draft changed (score 5 → 4) |
| dev-0010 |  | draft changed (score 5 → 4) |
| dev-0011 |  | draft changed (score 4 → 3) |
| dev-0012 |  | draft changed (score 5 → 5) |
| dev-0013 |  | draft changed (score 4 → 4) |
| dev-0014 |  | draft changed (score 5 → 5) |
| dev-0015 |  | draft changed (score 4 → 4) |
| dev-0016 |  | draft changed (score 4 → 5) |
| dev-0017 |  | priority P1 → P2; draft changed (score 4 → 4) |
| dev-0018 |  | draft changed (score 4 → 4) |
| dev-0019 |  | draft changed (score 4 → 5) |
| dev-0020 |  | draft changed (score 4 → 4) |
| dev-0021 |  | priority P1 → P2; draft changed (score 4 → 5) |
| dev-0022 |  | priority P1 → P2; draft changed (score 5 → 4) |
| dev-0023 |  | draft changed (score 5 → 4) |
| dev-0024 |  | draft changed (score 5 → 5) |
| dev-0025 |  | priority P2 → P3; draft changed (score 5 → 5) |
| dev-0026 |  | draft changed (score 5 → 5) |
| dev-0027 |  | draft changed (score 4 → 5) |
| dev-0028 |  | outcome escalated → flagged; priority P1 → P3; flags ['missing:reference', 'missing:amount', 'recheck_disagreed'] → ['recheck_used_second']; draft changed (score — → 5) |
| dev-0029 |  | draft changed (score 5 → 5) |
| dev-0030 |  | draft changed (score 3 → 4) |
| dev-0031 |  | draft changed (score 4 → 5) |
| dev-0032 |  | draft changed (score 5 → 4) |
| dev-0033 |  | draft changed (score 5 → 5) |
| dev-0034 |  | draft changed (score 4 → 5) |
| dev-0035 |  | draft changed (score 4 → 4) |
| dev-0036 |  | draft changed (score 4 → 4) |
| dev-0037 |  | draft changed (score 4 → 4) |
| dev-0038 |  | draft changed (score 5 → 4) |
| dev-0039 |  | flags ['missing:amount'] → ['missing:amount', 'draft:stray_latin']; draft changed (score 4 → 3) |
| dev-0040 |  | outcome flagged → drafted; flags ['missing:reference'] → []; draft changed (score 4 → 5) |
| dev-0041 |  | draft changed (score 3 → 4) |
| dev-0042 |  | priority P2 → P3; draft changed (score 4 → 5) |
| dev-0043 |  | outcome flagged → drafted; flags ['missing:reference'] → []; draft changed (score 4 → 4) |
| dev-0044 |  | draft changed (score 5 → 5) |
| dev-0045 |  | priority P1 → P2; draft changed (score 5 → 4) |
| dev-0047 |  | draft changed (score 4 → 4) |
| dev-0048 |  | draft changed (score 4 → 4) |
| dev-0049 |  | draft changed (score 4 → 3) |
| dev-0050 |  | priority P2 → P3; draft changed (score 5 → 5) |
| dev-0051 |  | draft changed (score 4 → 4) |
| dev-0052 |  | draft changed (score 5 → 4) |
| dev-0053 |  | priority P1 → P2; draft changed (score 4 → 4) |
| dev-0054 |  | draft changed (score 4 → 4) |
| dev-0055 |  | draft changed (score 5 → 5) |
| dev-0056 |  | draft changed (score 5 → 5) |
| dev-0057 |  | outcome flagged → drafted; flags ['missing:reference'] → []; draft changed (score 4 → 4) |
| dev-0058 |  | priority P2 → P3; draft changed (score 5 → 5) |
| dev-0059 |  | priority P1 → P2; draft changed (score 5 → 5) |
| dev-0060 |  | outcome flagged → drafted; flags ['missing:reference'] → []; draft changed (score 4 → 4) |
| dev-0061 |  | draft changed (score 5 → 5) |
| dev-0062 |  | draft changed (score 4 → 5) |
| dev-0064 |  | draft changed (score 5 → 5) |
| dev-0065 |  | draft changed (score 5 → 5) |
| dev-0066 |  | draft changed (score 5 → 5) |
| dev-0067 |  | draft changed (score 5 → 4) |
| dev-0068 |  | draft changed (score 5 → 5) |
| dev-0070 |  | draft changed (score 4 → 5) |
| dev-0071 |  | draft changed (score 5 → 4) |
| dev-0072 |  | draft changed (score 5 → 5) |
| dev-0073 |  | priority P2 → P3; draft changed (score 4 → 5) |
| dev-0074 |  | draft changed (score 3 → 3) |
| dev-0075 |  | priority P2 → P3; draft changed (score 4 → 4) |
| dev-0076 |  | draft changed (score 5 → 5) |
| dev-0077 |  | draft changed (score 4 → 4) |
| dev-0078 |  | draft changed (score 5 → 4) |
| dev-0079 |  | priority P1 → P2; draft changed (score 4 → 4) |
| dev-0080 |  | draft changed (score 5 → 4) |
| dev-0081 |  | draft changed (score 5 → 4) |
| dev-0082 |  | draft changed (score 5 → 5) |
| dev-0084 |  | draft changed (score 4 → 3) |
| dev-0085 |  | draft changed (score 5 → 5) |
| dev-0086 |  | draft changed (score 4 → 4) |
| dev-0087 |  | priority P2 → P3; draft changed (score 4 → 5) |
| dev-0088 |  | draft changed (score 5 → 5) |
| dev-0089 |  | draft changed (score 5 → 5) |
| dev-0091 |  | draft changed (score 4 → 4) |
| dev-0092 |  | draft changed (score 4 → 4) |
| dev-0093 |  | draft changed (score 4 → 5) |
| dev-0094 |  | draft changed (score 3 → 3) |
| dev-0096 |  | draft changed (score 4 → 5) |
| dev-0097 |  | priority P2 → P3; draft changed (score 4 → 4) |
| dev-0098 |  | draft changed (score 5 → 5) |
| dev-0099 |  | draft changed (score 5 → 5) |
| dev-0100 |  | draft changed (score 5 → 5) |
| dev-0101 |  | draft changed (score 4 → 4) |
| dev-0102 |  | draft changed (score 4 → 4) |
| dev-0103 |  | draft changed (score 4 → 4) |
| dev-0104 |  | draft changed (score 4 → 4) |
| dev-0105 |  | draft changed (score 4 → 4) |
| dev-0106 |  | draft changed (score 5 → 5) |
| dev-0107 |  | draft changed (score 4 → 5) |
| dev-0108 |  | draft changed (score 5 → 5) |
| dev-0109 |  | priority P2 → P3; draft changed (score 4 → 3) |
| dev-0110 |  | draft changed (score 5 → 5) |
| dev-0111 |  | draft changed (score 5 → 4) |
| dev-0112 |  | priority P2 → P3; draft changed (score 5 → 4) |
| dev-0113 |  | priority P2 → P3; draft changed (score 5 → 5) |
| dev-0114 |  | draft changed (score 4 → 4) |
| dev-0115 |  | draft changed (score 4 → 5) |
| dev-0116 |  | draft changed (score 5 → 5) |
| dev-0118 |  | draft changed (score 5 → 4) |
| dev-0119 |  | draft changed (score 5 → 5) |
| dev-0120 |  | draft changed (score 4 → 5) |
| dev-0121 |  | outcome escalated → flagged; priority P2 → P3; flags ['missing:reference', 'missing:amount', 'recheck_disagreed'] → ['recheck_used_second']; draft changed (score — → 4) |
| dev-0122 |  | draft changed (score 4 → 4) |
| dev-0123 |  | priority P1 → P2; draft changed (score 4 → 5) |
| dev-0124 |  | draft changed (score 4 → 5) |
| dev-0125 |  | priority P2 → P3; draft changed (score 4 → 5) |
| dev-0126 |  | draft changed (score 5 → 4) |
| dev-0128 |  | draft changed (score 4 → 5) |
| dev-0130 |  | draft changed (score 4 → 5) |
| dev-0131 |  | priority P2 → P3; draft changed (score 5 → 4) |
| dev-0132 |  | draft changed (score 4 → 4) |
| dev-0134 |  | draft changed (score 5 → 4) |
| dev-0135 |  | outcome drafted → flagged; flags [] → ['draft:stray_latin']; draft changed (score 5 → 3) |
| dev-0136 |  | draft changed (score 5 → 5) |
| dev-0137 |  | draft changed (score 5 → 5) |
| dev-0138 |  | outcome escalated → flagged; flags ['recheck_disagreed'] → ['recheck_used_second']; draft changed (score — → 4) |
| dev-0139 |  | draft changed (score 5 → 4) |
| dev-0140 |  | draft changed (score 3 → 4) |
| dev-0141 |  | draft changed (score 5 → 5) |
| dev-0142 |  | priority P1 → P2; draft changed (score 5 → 5) |
| dev-0143 |  | draft changed (score 4 → 5) |
| dev-0144 |  | priority P2 → P3; draft changed (score 5 → 4) |
| dev-0145 |  | draft changed (score 4 → 4) |
| dev-0147 |  | priority P2 → P3; draft changed (score 4 → 5) |
| dev-0148 |  | priority P2 → P3; draft changed (score 5 → 5) |
| dev-0149 |  | draft changed (score 4 → 4) |
| dev-0150 |  | draft changed (score 4 → 5) |
| dev-0151 |  | draft changed (score 5 → 5) |
| dev-0152 |  | draft changed (score 4 → 3) |
| dev-0153 |  | priority P2 → P3; draft changed (score 4 → 5) |
| dev-0154 |  | draft changed (score 5 → 4) |
| dev-0155 |  | draft changed (score 4 → 5) |
| dev-0156 |  | draft changed (score 4 → 5) |
| dev-0157 |  | draft changed (score 4 → 5) |
| dev-0158 |  | draft changed (score 5 → 5) |
| dev-0159 |  | draft changed (score 5 → 5) |
| dev-0160 |  | draft changed (score 5 → 4) |
| dev-0161 |  | draft changed (score 4 → 5) |
| dev-0162 |  | draft changed (score 4 → 4) |
| dev-0163 |  | outcome flagged → drafted; flags ['missing:reference'] → []; draft changed (score 4 → 3) |
| dev-0165 |  | draft changed (score 4 → 4) |
| dev-0166 |  | outcome flagged → drafted; flags ['missing:reference'] → []; draft changed (score 4 → 3) |
| dev-0167 |  | draft changed (score 5 → 5) |
| dev-0168 |  | outcome flagged → drafted; flags ['missing:reference'] → []; draft changed (score 5 → 4) |
| dev-0170 |  | draft changed (score 5 → 5) |
| dev-0171 |  | priority P2 → P3; draft changed (score 4 → 4) |
| dev-0172 |  | draft changed (score 5 → 5) |
| dev-0173 |  | outcome flagged → drafted; flags ['missing:reference'] → []; draft changed (score 4 → 3) |
| dev-0174 |  | priority P2 → P3; draft changed (score 5 → 5) |
| dev-0175 |  | draft changed (score 4 → 5) |
| dev-0176 |  | draft changed (score 5 → 4) |
| dev-0177 |  | draft changed (score 5 → 4) |
| dev-0178 |  | draft changed (score 4 → 4) |
| dev-0179 |  | draft changed (score 5 → 5) |
| dev-0180 |  | draft changed (score 5 → 5) |
| dev-0181 |  | draft changed (score 4 → 4) |
| dev-0182 |  | draft changed (score 5 → 4) |
| dev-0183 |  | draft changed (score 5 → 5) |
| dev-0184 |  | draft changed (score 4 → 4) |
| dev-0185 |  | draft changed (score 4 → 4) |
| dev-0186 |  | draft changed (score 5 → 5) |
| dev-0187 |  | priority P1 → P2; draft changed (score 4 → 5) |
| dev-0188 |  | priority P1 → P2; draft changed (score 4 → 4) |
| dev-0189 |  | draft changed (score 4 → 5) |
| dev-0190 |  | outcome escalated → flagged; flags ['recheck_disagreed'] → ['recheck_used_second']; draft changed (score — → 4) |
| dev-0191 |  | draft changed (score 5 → 5) |
| dev-0193 |  | draft changed (score 4 → 5) |
| dev-0194 |  | draft changed (score 5 → 5) |
| dev-0195 |  | draft changed (score 5 → 4) |
| dev-0196 |  | draft changed (score 4 → 5) |
| dev-0198 |  | draft changed (score 4 → 5) |
| dev-0199 |  | draft changed (score 4 → 3) |
| dev-0200 |  | draft changed (score 4 → 5) |
| dev-0201 |  | draft changed (score 5 → 5) |
| dev-0202 |  | draft changed (score 4 → 4) |
| dev-0203 |  | draft changed (score 5 → 4) |
| dev-0204 |  | draft changed (score 5 → 5) |
| dev-0205 |  | outcome drafted → flagged; flags [] → ['draft:unknown_number']; draft changed (score 5 → 4) |
| dev-0206 |  | draft changed (score 5 → 5) |
| dev-0207 |  | draft changed (score 4 → 5) |
| dev-0208 |  | draft changed (score 4 → 3) |
| dev-0209 |  | draft changed (score 4 → 5) |
| dev-0210 |  | draft changed (score 5 → 4) |
| dev-0211 |  | priority P2 → P3; draft changed (score 4 → 4) |
| dev-0212 |  | priority P1 → P2; draft changed (score 4 → 4) |
| dev-0213 |  | draft changed (score 5 → 4) |
| dev-0214 |  | draft changed (score 5 → 5) |
| dev-0215 |  | draft changed (score 5 → 5) |
| dev-0216 |  | draft changed (score 5 → 5) |
| dev-0217 |  | draft changed (score 5 → 5) |
| dev-0218 |  | draft changed (score 4 → 4) |
| dev-0220 |  | priority P1 → P2; draft changed (score 5 → 5) |
| dev-0221 |  | draft changed (score 4 → 5) |
| dev-0222 |  | draft changed (score 4 → 5) |
| dev-0223 |  | priority P2 → P3; draft changed (score 4 → 5) |
| dev-0224 |  | draft changed (score 4 → 5) |
| dev-0225 |  | draft changed (score 5 → 4) |
| dev-0226 |  | draft changed (score 4 → 5) |
| dev-0227 |  | draft changed (score 5 → 5) |
| dev-0228 |  | draft changed (score 5 → 5) |
| dev-0230 |  | draft changed (score 5 → 5) |
| dev-0231 |  | priority P1 → P2; draft changed (score 4 → 4) |
| dev-0232 |  | draft changed (score 4 → 5) |
| dev-0233 |  | draft changed (score 4 → 4) |
| dev-0234 |  | draft changed (score 5 → 5) |
| dev-0235 |  | draft changed (score 4 → 4) |
| dev-0236 |  | draft changed (score 5 → 4) |
| dev-0237 |  | draft changed (score 5 → 5) |
| dev-0238 |  | draft changed (score 4 → 5) |
| dev-0240 |  | priority P2 → P3; draft changed (score 4 → 4) |

## Every ticket

| Ticket | Gold | Got | Outcome | Priority | Flags | Draft score | Judge notes |
|---|---|---|---|---|---|---|---|
| dev-0001 | topup_failed | ✓ | drafted | P3 |  | 5 |  |
| dev-0002 | wrong_recipient | ✓ | drafted | P2 |  | 3 | The draft does not ask for the transaction number, which is still missing because the customer gave the recipient's phone number instead. |
| dev-0003 | complaint | ✓ | drafted | P3 |  | 5 |  |
| dev-0004 | bill_not_reflected | ✓ | flagged | P3 | missing:amount | 5 |  |
| dev-0005 | app_bug | ✓ | drafted | P3 |  | 4 ⚠ | The English word 'restart' should be in Arabic (e.g. 'إعادة تشغيل'), and the line about the team confirming the account issue 'before any step' is a slightly loose commitment. |
| dev-0006 | delivery_or_activation | ✓ | drafted | P3 |  | 5 |  |
| dev-0007 | limit_upgrade | ✓ | drafted | P3 |  | 5 |  |
| dev-0008 | delivery_or_activation | ✓ | drafted | P3 |  | 3 ⚠ | The draft uses the English word 'error' twice and asks for the error text even though no information is needed. |
| dev-0009 | card_payment_failed | ✓ | drafted | P3 |  | 4 | Typo 'انقصم' should be 'انقص' (or 'نقص'); otherwise correct, asks only for the missing store name. |
| dev-0010 | rejected_or_pending | ✓ | drafted | P3 |  | 4 | The line saying the customer needs to do nothing until then is a slight overreach, and the phrasing could sound more natural in Iraqi dialect. |
| dev-0011 | wrong_recipient | ✓ | drafted | P2 ✗ (P1) |  | 3 ⚠ | The draft turns the customer's '10 ورقة' into '10,000 دينار', an amount the ticket never states, so the agent must fix the amount before sending. |
| dev-0012 | login_otp | ✓ | drafted | P2 |  | 5 |  |
| dev-0013 | not_received | ✓ | drafted | P2 |  | 4 | The draft does not ask for the exact date and time of the transfer; the ticket only says 'two days ago'. |
| dev-0014 | forgot_pin | ✓ | drafted | P3 |  | 5 |  |
| dev-0015 | sim_change | ✓ | drafted | P2 |  | 4 | Minor: 'we recorded the transaction number' asserts an action the agent should confirm, and the reply mixes singular 'وصلتني' with plural 'سجلنا'. |
| dev-0016 | cash_in_not_credited | ✓ | drafted | P1 |  | 5 |  |
| dev-0017 | not_received | ✓ | flagged ✗ (drafted) | P2 | missing:amount | 4 | The draft asks for the amount, which the customer already gave ('3 ورقة'), and doesn't ask for the approximate time of the transfer. |
| dev-0018 | card_payment_failed | ✓ | drafted | P3 |  | 4 | The draft does not ask for the restaurant's name, which is needed and not in the ticket. |
| dev-0019 | wrong_recipient | ✓ | flagged | P2 | missing:reference | 5 |  |
| dev-0020 | delivery_or_activation | ✓ | drafted | P3 |  | 4 | The last sentence is clunky and doesn't tell the customer how or when they'll get an update, so a small rewording would help. |
| dev-0021 | cash_in_not_credited | ✓ | drafted | P2 |  | 5 |  |
| dev-0022 | sim_change | ✓ | drafted | P2 |  | 4 | The third sentence is awkwardly phrased ('الفريق راح يتحقق منه هم') and repeats the previous sentence, so it should be smoothed or merged. |
| dev-0023 | blocked_account | ✓ | drafted | P2 |  | 4 | Slightly repetitive wording (إزعاج/انزعاج, and the last sentence repeats that the case will be checked). |
| dev-0024 | blocked_account | ✓ | drafted | P2 |  | 5 |  |
| dev-0025 | merchant_payment | ✓ | drafted | P3 |  | 5 |  |
| dev-0026 | wrong_recipient | ✓ | drafted | P2 |  | 5 |  |
| dev-0027 | wrong_recipient | ✓ | flagged | P2 | missing:amount | 5 |  |
| dev-0028 | fees_limits_question | ✗ not_received | flagged ✗ (drafted) | P3 | recheck_used_second | 5 |  |
| dev-0029 | not_received | ✓ | drafted | P2 |  | 5 |  |
| dev-0030 | not_received | ✓ | drafted | P2 |  | 4 | The draft does not ask for the exact date and time of the transfer; the ticket only says 'three days ago'. |
| dev-0031 | not_received | ✓ | drafted | P2 |  | 5 |  |
| dev-0032 | cash_out_refused | ✓ | drafted | P3 |  | 4 ⚠ | The draft uses the English word 'error'; replace it with an Arabic word such as 'خلل'. |
| dev-0033 | card_payment_failed | ✓ | drafted | P3 |  | 5 |  |
| dev-0034 | blocked_account | ✓ | drafted | P2 |  | 5 |  |
| dev-0035 | cash_out_refused | ✓ | drafted | P3 |  | 4 | Minor wording slip: 'إذا يحق للوكيل يرفض وين تگدر' is missing 'و' between the two questions. |
| dev-0036 | not_received | ✓ | drafted | P2 |  | 4 | The draft does not ask for the exact date and time of the transfer; the ticket only says 'two days ago'. |
| dev-0037 | not_received | ✓ | drafted | P2 |  | 4 | The draft calls it a 'delay' (سبب التأخير), which assumes the money will arrive; 'سبب المشكلة' would be safer. |
| dev-0038 | delivery_or_activation | ✓ | drafted | P3 |  | 4 | The phrase 'تجربها بي' is awkward and should simply be 'تجربها'; otherwise the draft is fine. |
| dev-0039 | cash_in_not_credited | ✓ | flagged | P2 | missing:amount, draft:stray_latin | 3 ⚠ | The draft doesn't ask for the exact date and time of the transaction, and it uses English words stuck to Arabic ('الـtop up', 'بالwallet') where Arabic terms would work. |
| dev-0040 | not_received | ✓ | drafted | P2 |  | 5 |  |
| dev-0041 | bill_not_reflected | ✓ | drafted | P3 |  | 4 | Small grammar slip: 'فهمت إن دفعت' should be 'فهمت إنك دفعت'. |
| dev-0042 | cash_out_refused | ✓ | drafted | P3 |  | 5 |  |
| dev-0043 | reversal_request | ✓ | drafted | P2 |  | 4 | The draft never asks for the transaction number, which is needed and not in the ticket. |
| dev-0044 | topup_failed | ✓ | drafted | P3 |  | 5 |  |
| dev-0045 | login_otp | ✓ | drafted | P2 |  | 4 | The draft switches between plural and singular voice ('نعتذر' then 'فهمت') and could warn the customer not to share the OTP. |
| dev-0046 | suspected_scam | ✓ | escalated | P1 | fraud | — |  |
| dev-0047 | cash_in_not_credited | ✓ | drafted | P2 |  | 4 | The draft asks for the agent's name and location but not the approximate time of the transaction (the ticket gives only 'day before yesterday'). |
| dev-0048 | forgot_pin | ✓ | drafted | P3 |  | 4 ⚠ | The draft uses the English words 'PIN' and 'reset' instead of Arabic (e.g. الرمز السري, إعادة التعيين); otherwise it is fine. |
| dev-0049 | not_received | ✓ | flagged | P2 | missing:reference | 3 ⚠ | The draft doesn't ask for the transfer time, offers no other way forward even though the customer said the reference is lost, and names app locations (confirmation message, transaction history) that aren't in Known facts. |
| dev-0050 | rejected_or_pending | ✓ | drafted | P3 |  | 5 |  |
| dev-0051 | wrong_recipient | ✓ | drafted | P2 |  | 4 | The closing phrase 'ونتمنى تبقى على تواصل وياه' is awkward and unclear, and the draft does not acknowledge the customer's claim that the app changed the number. |
| dev-0052 | card_payment_failed | ✓ | drafted | P3 |  | 4 | The draft never asks for the restaurant's name, which is needed and not in the ticket. |
| dev-0053 | wrong_recipient | ✓ | flagged | P2 | missing:reference | 4 ⚠ | The draft says the transaction number can be found in the app's transaction history, which is a procedure detail not in Known facts, and 'ارسللنا' reads like a typo. |
| dev-0054 | cash_in_not_credited | ✓ | drafted | P2 |  | 4 | The phrasing 'إنت إدخلت ... واكو وكيل كلك نزلت' is awkward and should read more naturally, e.g. 'انطيت الوكيل 200,000 دينار وكلك نزلت'. |
| dev-0055 | login_otp | ✓ | drafted | P2 |  | 5 |  |
| dev-0056 | not_received | ✓ | drafted | P2 |  | 5 |  |
| dev-0057 | not_received | ✓ | drafted | P2 |  | 4 | The draft asks for nothing, but it should ask for the exact date and time of the transfer, since the ticket only says 'two days ago' and has no transaction number. |
| dev-0058 | overcharged_fee | ✓ | flagged | P3 | missing:amount | 5 |  |
| dev-0059 | login_otp | ✓ | drafted | P2 |  | 5 |  |
| dev-0060 | reversal_request | ✓ | drafted | P1 |  | 4 | The draft never asks for the transaction number (or help locating it in the app history), which is the one missing piece of information; the amount is already given. |
| dev-0061 | wrong_recipient | ✓ | drafted | P2 |  | 5 |  |
| dev-0062 | bill_not_reflected | ✓ | flagged | P3 | missing:amount | 5 |  |
| dev-0063 | unauthorized_charge | ✓ | escalated | P1 | fraud | — |  |
| dev-0064 | sim_change | ✓ | drafted | P2 |  | 5 |  |
| dev-0065 | topup_failed | ✓ | drafted | P3 |  | 5 |  |
| dev-0066 | blocked_account | ✓ | drafted | P2 |  | 5 |  |
| dev-0067 | overcharged_fee | ✓ | flagged ✗ (drafted) | P3 | missing:amount | 4 | The opening 'آني أفهم كلامك، وإنت تشتكي إن...' reads a bit robotic and could be smoothed. |
| dev-0068 | unclear | ✓ | drafted | P3 |  | 5 |  |
| dev-0069 | suspected_scam | ✓ | escalated | P1 | fraud | — |  |
| dev-0070 | complaint | ✓ | drafted | P3 |  | 5 |  |
| dev-0071 | reversal_request | ✓ | drafted | P2 |  | 4 | "أخوي الكريم" assumes the customer's gender, and the closing "إن شاء الله نوصل لحل" hints at a resolution, so a small edit is worth considering. |
| dev-0072 | not_received | ✓ | drafted | P1 |  | 5 |  |
| dev-0073 | merchant_payment | ✓ | drafted | P3 |  | 5 |  |
| dev-0074 | cash_in_not_credited | ✓ | drafted | P2 ✗ (P1) |  | 3 ⚠ | The draft reads 'ten notes' as 10,000 dinar, an amount the customer never gave, and it doesn't ask for the exact amount or the date and time of the deposit. |
| dev-0075 | forgot_pin | ✓ | drafted | P3 |  | 4 ⚠ | The draft uses the English word 'PIN' (written الـPIN) twice, which should be replaced with an Arabic term like الرمز السري. |
| dev-0076 | wrong_recipient | ✓ | drafted | P1 |  | 5 |  |
| dev-0077 | card_payment_failed | ✓ | drafted | P3 |  | 4 ⚠ | The draft uses the English word 'declined', which should be replaced with Arabic (e.g. 'انرفضت'). |
| dev-0078 | topup_failed | ✓ | drafted | P3 |  | 4 | The clause 'اللي انقطعت فلوسه' wrongly says the money was deducted from the phone number rather than the customer's wallet and should be reworded. |
| dev-0079 | sim_change | ✓ | drafted | P2 |  | 4 | The phrase 'أكيد نگدر نساعدك' leans toward an assurance of resolution and should be softened. |
| dev-0080 | unclear | ✓ | drafted | P3 |  | 4 | The phrase 'مو من اختصاص الحساب' is awkward and should say it is outside the company's scope, ideally offering help with any account issue. |
| dev-0081 | app_bug | ✓ | drafted | P3 |  | 4 | The phrase 'وأكيد أكو مشكلة تعطلك' reads awkwardly and should be reworded to acknowledge the inconvenience more naturally. |
| dev-0082 | complaint | ✓ | drafted | P3 |  | 5 |  |
| dev-0083 | unauthorized_charge | ✓ | escalated | P1 | fraud | — |  |
| dev-0084 | overcharged_fee | ✓ | drafted | P3 |  | 3 | The draft asks for the agent's name and location but not the withdrawal amount, and it misstates the ticket by saying 10,000 was taken extra when the agent called 10,000 his whole commission. |
| dev-0085 | reversal_request | ✓ | drafted | P2 |  | 5 |  |
| dev-0086 | fees_limits_question | ✓ | drafted | P3 |  | 4 | The line saying the agent can't state fees 'from my side' to avoid giving inaccurate info sounds awkward for a support reply and could be smoothed. |
| dev-0087 | merchant_payment | ✓ | drafted | P3 |  | 5 |  |
| dev-0088 | app_bug | ✓ | drafted | P3 |  | 5 |  |
| dev-0089 | topup_failed | ✓ | drafted | P3 |  | 5 |  |
| dev-0090 | suspected_scam | ✓ | escalated | P1 | fraud | — |  |
| dev-0091 | topup_failed | ✓ | drafted | P3 |  | 4 | The first sentence is a little awkward ('شحنة الرصيد بمبلغ... انخصم المبلغ') and could be smoothed. |
| dev-0092 | overcharged_fee | ✓ | drafted | P3 |  | 4 | The draft asks for the agent's name and location but not the withdrawal amount, which the ticket does not give. |
| dev-0093 | bill_not_reflected | ✓ | drafted | P3 |  | 5 |  |
| dev-0094 | fees_limits_question | ✗ not_received | flagged ✗ (drafted) | P2 ✗ (P3) | missing:reference, missing:amount | 3 | The draft asks for the transaction number, amount and date/time even though nothing is needed for a fees question, and 'وكلك' is a typo for 'وگالك'. |
| dev-0095 | unauthorized_charge | ✓ | escalated | P1 | fraud | — |  |
| dev-0096 | forgot_pin | ✓ | drafted | P3 |  | 5 |  |
| dev-0097 | rejected_or_pending | ✓ | drafted | P3 |  | 4 | The draft uses non-Iraqi 'لسه' (Iraqi would say 'بعده') and mixes 'أدري' with 'نعتذر'; both are minor wording fixes. |
| dev-0098 | topup_failed | ✓ | drafted | P3 |  | 5 |  |
| dev-0099 | forgot_pin | ✓ | drafted | P3 |  | 5 |  |
| dev-0100 | login_otp | ✓ | drafted | P2 |  | 5 |  |
| dev-0101 | overcharged_fee | ✓ | flagged ✗ (drafted) | P3 | missing:amount | 4 | The draft asks for the withdrawal amount but not the agent's name and location, which the team needs. |
| dev-0102 | merchant_payment | ✓ | drafted | P3 |  | 4 | The advice not to pay again is unsupported guidance that could leave the customer stuck with the restaurant, so the agent may want to soften or remove it. |
| dev-0103 | delivery_or_activation | ✓ | drafted | P3 |  | 4 | The draft restates the ticket at length and mixes plural 'نعتذر' with singular 'فهمت'; it could be trimmed. |
| dev-0104 | rejected_or_pending | ✓ | drafted | P3 |  | 4 | Minor typo 'وياانا' should be 'ويانا', and the English words 'pending' and 'selfie' could be put in Arabic. |
| dev-0105 | wrong_recipient | ✓ | drafted | P2 |  | 4 | Minor spelling slip 'إلية' should be 'إله' or 'إليه', and 'أخي الكريم' assumes the customer's gender. |
| dev-0106 | not_received | ✓ | drafted | P2 |  | 5 |  |
| dev-0107 | reversal_request | ✓ | drafted | P1 |  | 5 |  |
| dev-0108 | wrong_recipient | ✓ | flagged | P2 | missing:reference | 5 |  |
| dev-0109 | reversal_request | ✗ merchant_payment | drafted | P3 ✗ (P2) |  | 3 | The draft asks for the shop name instead of the transaction reference number; it also has a typo ('گتلي' should be 'گلتلي') and an awkward last phrase. |
| dev-0110 | cash_out_refused | ✓ | drafted | P3 |  | 5 |  |
| dev-0111 | topup_failed | ✓ | drafted | P3 |  | 4 | The connector 'إذ' reads stiff and formal for an Iraqi chat reply, so the first sentence needs a small edit. |
| dev-0112 | delivery_or_activation | ✓ | drafted | P3 |  | 4 ⚠ | The words 'تواصل ويّاك' are glued together as 'تواصلويّاك', and 'وللحين' reads Gulf rather than Iraqi ('لهسه' would fit better). |
| dev-0113 | cash_out_refused | ✓ | drafted | P3 |  | 5 |  |
| dev-0114 | not_received | ✓ | drafted | P2 ✗ (P1) |  | 4 ⚠ | The draft turns the slang '20 ورقة' into '20,000 دينار' and assumes 95120323 is the transaction reference, but the ticket confirms neither. |
| dev-0115 | wrong_recipient | ✓ | drafted | P2 |  | 5 |  |
| dev-0116 | limit_upgrade | ✓ | drafted | P3 |  | 5 |  |
| dev-0117 | unauthorized_charge | ✓ | escalated | P1 | fraud | — |  |
| dev-0118 | sim_change | ✓ | drafted | P2 |  | 4 | The phrase 'سلامة التلفون' is awkward and should be 'سلامتك'; the draft also claims the request was already transferred and the reference logged, which the agent should confirm before sending. |
| dev-0119 | wrong_recipient | ✓ | flagged | P2 | missing:amount | 5 |  |
| dev-0120 | delivery_or_activation | ✓ | drafted | P3 |  | 5 |  |
| dev-0121 | fees_limits_question | ✗ not_received | flagged ✗ (drafted) | P3 | recheck_used_second | 4 | The draft asks for the sent and received amounts even though nothing is needed for this fees question; drop the last sentence. |
| dev-0122 | rejected_or_pending | ✓ | drafted | P3 |  | 4 | The quoted English word "pending" could be replaced with "قيد المراجعة", and the draft could briefly say the customer will be contacted once the team checks. |
| dev-0123 | wrong_recipient | ✓ | drafted | P2 |  | 5 |  |
| dev-0124 | fees_limits_question | ✓ | drafted | P3 |  | 5 |  |
| dev-0125 | rejected_or_pending | ✓ | drafted | P3 |  | 5 |  |
| dev-0126 | limit_upgrade | ✓ | drafted | P3 |  | 4 | The second sentence is awkward and only vaguely answers what the customer must provide; it should say clearly that قسم التوثيق will tell them the requirements. |
| dev-0127 | suspected_scam | ✓ | escalated | P1 | fraud | — |  |
| dev-0128 | blocked_account | ✓ | drafted | P2 |  | 5 |  |
| dev-0129 | unauthorized_charge | ✓ | escalated | P1 | fraud | — |  |
| dev-0130 | cash_in_not_credited | ✓ | drafted | P2 |  | 5 |  |
| dev-0131 | merchant_payment | ✓ | drafted | P3 |  | 4 | The opening 'گاعد افهم كلامك' is awkward, and calling the merchant payment a 'حوالة' is slightly inaccurate. |
| dev-0132 | bill_not_reflected | ✓ | drafted | P3 |  | 4 | The opening 'گاعد افهم گدّ شنو' is awkward Iraqi phrasing (better 'أفهم شگد'), and 'ما تعيد الدفع مرتين' is redundant. |
| dev-0133 | unauthorized_charge | ✓ | escalated | P1 | fraud | — |  |
| dev-0134 | overcharged_fee | ✓ | drafted | P3 |  | 4 | The draft asks for the agent's name and location but not the withdrawal amount; the ticket gives only the fee. |
| dev-0135 | card_payment_failed | ✓ | flagged ✗ (drafted) | P3 | draft:stray_latin | 3 ⚠ | The draft never asks for the restaurant's name, and it has Latin letters inside an Arabic word ('هيchك'). |
| dev-0136 | login_otp | ✓ | drafted | P2 |  | 5 |  |
| dev-0137 | not_received | ✓ | drafted | P1 |  | 5 |  |
| dev-0138 | reversal_request | ✓ | flagged ✗ (drafted) | P2 | recheck_used_second | 4 | Asks for the recipient's number, which is not among the needed information, while the reference and amount were already given, so nothing needed to be asked. |
| dev-0139 | rejected_or_pending | ✓ | drafted | P3 |  | 4 | The phrase 'ومثل ما سألت عن المشكلة بالضبط' is clunky, and the long recap of the ticket could be trimmed. |
| dev-0140 | not_received | ✓ | drafted | P2 |  | 4 ⚠ | The draft turns the slang 'ثلاث ورقات' into '3,000 دينار', an amount the customer never stated, so it should use the customer's own words or ask them to confirm the exact amount. |
| dev-0141 | app_bug | ✓ | drafted | P3 |  | 5 |  |
| dev-0142 | reversal_request | ✓ | drafted | P2 |  | 5 |  |
| dev-0143 | unclear | ✓ | drafted | P3 |  | 5 |  |
| dev-0144 | app_bug | ✓ | drafted | P3 |  | 4 | The recap of the ticket is long and switches from plural (نتفهم) to singular (فهمت), so it needs a small trim and one consistent voice. |
| dev-0145 | limit_upgrade | ✗ fees_limits_question | drafted | P3 |  | 4 | The draft rightly ignores the injected instruction, but the line saying it can't give details sounds a little blunt and could be softened. |
| dev-0146 | unauthorized_charge | ✓ | escalated | P1 | fraud | — |  |
| dev-0147 | merchant_payment | ✓ | drafted | P3 |  | 5 |  |
| dev-0148 | topup_failed | ✓ | drafted | P3 |  | 5 |  |
| dev-0149 | bill_not_reflected | ✓ | drafted | P3 |  | 4 | The final sentence ('if you don't get an answer, the matter is in the specialist team's hands') is awkward and sounds dismissive, so it should be reworded or removed. |
| dev-0150 | unclear | ✓ | drafted | P3 |  | 5 |  |
| dev-0151 | login_otp | ✓ | drafted | P2 |  | 5 |  |
| dev-0152 | cash_out_refused | ✗ overcharged_fee | flagged ✗ (drafted) | P3 | missing:amount | 3 | The draft asks for the withdrawn and deducted amounts but never asks for the needed agents' names and locations. |
| dev-0153 | overcharged_fee | ✓ | drafted | P3 |  | 5 |  |
| dev-0154 | overcharged_fee | ✓ | flagged | P3 | missing:amount | 4 | The draft never acknowledges the customer's direct question about whether the agent is allowed to charge that much, and 'وأيضاً' reads slightly formal. |
| dev-0155 | login_otp | ✓ | drafted | P2 |  | 5 |  |
| dev-0156 | not_received | ✓ | flagged ✗ (drafted) | P2 | missing:amount | 5 |  |
| dev-0157 | forgot_pin | ✓ | drafted | P3 |  | 5 |  |
| dev-0158 | card_payment_failed | ✓ | drafted | P3 |  | 5 |  |
| dev-0159 | topup_failed | ✓ | drafted | P3 |  | 5 |  |
| dev-0160 | limit_upgrade | ✓ | drafted | P3 |  | 4 | The restatement of the problem is long, and the closing line deferring documents and timing to the department sounds a bit curt; it could be softened. |
| dev-0161 | overcharged_fee | ✓ | drafted | P3 |  | 5 |  |
| dev-0162 | not_received | ✓ | drafted | P2 |  | 4 | The ticket gives the date only as 'yesterday', so the draft should ask for the approximate time of the transfer. |
| dev-0163 | reversal_request | ✓ | drafted | P2 |  | 3 ⚠ | The draft only asks for the transaction number if it turns up later instead of asking for it now, uses the English word 'screenshot', and adds 'دينار', which the ticket never stated. |
| dev-0164 | login_otp | ✗ suspected_scam | escalated ✗ (drafted) | P1 ✗ (P2) | fraud | — |  |
| dev-0165 | cash_in_not_credited | ✓ | drafted | P2 |  | 4 | The draft asks for the agent's name and location but not the date and time of the transaction; the ticket only vaguely mentions yesterday. |
| dev-0166 | reversal_request | ✓ | drafted | P2 |  | 3 ⚠ | The draft wrongly says the transaction number isn't needed and the team can proceed without it, a claim not in Known facts, and it fails to ask for the missing transaction number. |
| dev-0167 | delivery_or_activation | ✓ | drafted | P3 |  | 5 |  |
| dev-0168 | not_received | ✓ | drafted | P2 |  | 4 | The number in the ticket is the brother's phone number, not a transaction reference, so the draft should also ask for the transaction number, not only the date and time. |
| dev-0169 | suspected_scam | ✓ | escalated | P1 | fraud | — |  |
| dev-0170 | not_received | ✓ | drafted | P1 |  | 5 |  |
| dev-0171 | limit_upgrade | ✓ | drafted | P3 |  | 4 | The closing line about tomorrow's payments is a bit awkward and could be read as implying it will be handled in time, so it may need a light rewording. |
| dev-0172 | wrong_recipient | ✓ | flagged | P2 | missing:reference | 5 |  |
| dev-0173 | not_received | ✓ | drafted | P1 |  | 3 | The customer sent the recipient's phone number, not the transaction number, but the draft never asks for the transaction number or the exact time of the transfer. |
| dev-0174 | app_bug | ✓ | drafted | P3 |  | 5 |  |
| dev-0175 | bill_not_reflected | ✓ | drafted | P3 |  | 5 |  |
| dev-0176 | cash_in_not_credited | ✓ | drafted | P1 |  | 4 | The draft asks for the date and time but not the agent's name, which the ticket does not give (only the location near سوگ الخضرة). |
| dev-0177 | cash_in_not_credited | ✓ | flagged | P2 | missing:amount | 4 | The draft asks for the amount but not the agent's name; the ticket gives only the area (Mansour). |
| dev-0178 | not_received | ✓ | drafted | P1 |  | 4 | The draft does not ask for the exact time of the transfer; the ticket only says 'this morning'. |
| dev-0179 | not_received | ✓ | drafted | P2 |  | 5 |  |
| dev-0180 | forgot_pin | ✓ | drafted | P3 |  | 5 |  |
| dev-0181 | not_received | ✓ | drafted | P1 |  | 4 ⚠ | The draft assumes the currency is Iraqi dinar (2,000,000 د.ع), but the customer only wrote 'مليونين'. |
| dev-0182 | delivery_or_activation | ✓ | drafted | P3 |  | 4 ⚠ | The words 'تواصل' and 'ويّاك' are joined without a space ('تواصلويّاك') and need separating. |
| dev-0183 | not_received | ✓ | drafted | P2 |  | 5 |  |
| dev-0184 | overcharged_fee | ✓ | drafted | P3 |  | 4 | The draft asks for the agent's name and location but not the withdrawal amount, which the ticket does not give. |
| dev-0185 | not_received | ✓ | drafted | P2 |  | 4 | The draft does not ask for the exact date and time of the transfer; the ticket only says 'two days ago'. |
| dev-0186 | card_payment_failed | ✓ | drafted | P3 |  | 5 |  |
| dev-0187 | wrong_recipient | ✓ | drafted | P2 |  | 5 |  |
| dev-0188 | login_otp | ✓ | drafted | P2 |  | 4 ⚠ | The advice not to retry until the check is done is a procedure instruction that is not in Known facts; otherwise the draft is good. |
| dev-0189 | fees_limits_question | ✓ | drafted | P3 |  | 5 |  |
| dev-0190 | reversal_request | ✓ | flagged ✗ (drafted) | P2 | recheck_used_second | 4 | The draft asks for the recipient's number, which isn't required, while the reference and amount are already in the ticket, so that request should be removed. |
| dev-0191 | reversal_request | ✓ | drafted | P2 |  | 5 |  |
| dev-0192 | suspected_scam | ✓ | escalated | P1 | fraud | — |  |
| dev-0193 | blocked_account | ✓ | drafted | P2 |  | 5 |  |
| dev-0194 | topup_failed | ✓ | drafted | P3 |  | 5 |  |
| dev-0195 | blocked_account | ✓ | drafted | P2 |  | 4 | The last sentence is a bit awkward and repetitive; it could be smoothed into a clearer next-step statement. |
| dev-0196 | cash_out_refused | ✓ | drafted | P3 |  | 5 |  |
| dev-0197 | suspected_scam | ✓ | escalated | P1 | fraud | — |  |
| dev-0198 | cash_out_refused | ✓ | drafted | P3 |  | 5 |  |
| dev-0199 | merchant_payment | ✓ | drafted | P3 |  | 3 ⚠ | The draft never asks for the restaurant's name, which is needed and missing from the ticket, and it uses the English word 'error' instead of Arabic. |
| dev-0200 | rejected_or_pending | ✓ | drafted | P3 |  | 5 |  |
| dev-0201 | app_bug | ✓ | drafted | P3 |  | 5 |  |
| dev-0202 | overcharged_fee | ✓ | drafted | P3 |  | 4 | The phrase 'يرجى ترسل' is slightly awkward and should be smoothed (e.g. 'ممكن ترسل لنا'); otherwise the draft is accurate and complete. |
| dev-0203 | limit_upgrade | ✓ | drafted | P3 |  | 4 | The last sentence about the department confirming the upgrade steps is awkward and unhelpful, and could be smoothed or dropped. |
| dev-0204 | topup_failed | ✓ | drafted | P3 |  | 5 |  |
| dev-0205 | overcharged_fee | ✓ | flagged ✗ (drafted) | P3 | draft:unknown_number | 4 | Minor phrasing: 'يرجى تكتبلنا' mixes formal and dialect, and 'حتى تنتبه الجهة المختصة للحالة' reads a bit awkwardly. |
| dev-0206 | not_received | ✓ | drafted | P2 |  | 5 |  |
| dev-0207 | bill_not_reflected | ✓ | drafted | P3 |  | 5 |  |
| dev-0208 | forgot_pin | ✓ | drafted | P3 |  | 3 ⚠ | The last sentence is awkward and sounds like it is passing responsibility to the team, the draft uses the English word 'app' (التطبيق would be better), and it should warn the customer not to share their PIN. |
| dev-0209 | bill_not_reflected | ✓ | drafted | P3 |  | 5 |  |
| dev-0210 | forgot_pin | ✓ | drafted | P3 |  | 4 ⚠ | The draft has small typos to fix: 'وياعيك' is garbled, 'وياناً' has a stray tanween, and 'تغيرت الموبايل' should be 'غيرت الموبايل'. |
| dev-0211 | cash_out_refused | ✓ | drafted | P3 |  | 4 | Minor awkward phrasing ('محاولة السحب الكاش فشلت' should be plural/smoother, and 'نتفهم' then 'فهمت' mixes voice), otherwise ready to send. |
| dev-0212 | wrong_recipient | ✓ | drafted | P2 |  | 4 | Minor typo 'وأفتهم' should be 'وأتفهم'; otherwise the draft is correct, grounded and asks only for the missing recipient number. |
| dev-0213 | topup_failed | ✓ | drafted | P3 |  | 4 ⚠ | The draft repeats the English words 'top up', 'app' and 'wallet' from the ticket instead of using Arabic, and the closing request is slightly awkward. |
| dev-0214 | sim_change | ✓ | drafted | P2 |  | 5 |  |
| dev-0215 | not_received | ✓ | drafted | P2 |  | 5 |  |
| dev-0216 | rejected_or_pending | ✓ | drafted | P3 |  | 5 |  |
| dev-0217 | delivery_or_activation | ✓ | drafted | P3 |  | 5 |  |
| dev-0218 | not_received | ✓ | flagged | P2 | missing:amount | 4 | The draft asks for the amount but not the approximate time of the transfer; the customer only said 'yesterday'. |
| dev-0219 | unauthorized_charge | ✓ | escalated | P1 | fraud | — |  |
| dev-0220 | login_otp | ✓ | drafted | P2 |  | 5 |  |
| dev-0221 | card_payment_failed | ✓ | drafted | P3 |  | 5 |  |
| dev-0222 | fees_limits_question | ✓ | drafted | P3 |  | 5 |  |
| dev-0223 | complaint | ✓ | drafted | P3 |  | 5 |  |
| dev-0224 | wrong_recipient | ✓ | drafted | P2 |  | 5 |  |
| dev-0225 | unclear | ✓ | drafted | P3 |  | 4 | The opening line sounds like the company has checked and confirmed the account is fine, though it only echoes the customer; rephrasing it would be safer. |
| dev-0226 | login_otp | ✓ | drafted | P2 |  | 5 |  |
| dev-0227 | sim_change | ✓ | drafted | P2 |  | 5 |  |
| dev-0228 | overcharged_fee | ✓ | drafted | P3 |  | 5 |  |
| dev-0229 | suspected_scam | ✓ | escalated | P1 | fraud | — |  |
| dev-0230 | cash_in_not_credited | ✓ | drafted | P2 |  | 5 |  |
| dev-0231 | not_received | ✓ | flagged | P2 | missing:reference, missing:amount | 4 | Draft asks for the reference number and amount but not the transaction time (the ticket only says Thursday). |
| dev-0232 | rejected_or_pending | ✓ | drafted | P3 |  | 5 |  |
| dev-0233 | cash_in_not_credited | ✓ | drafted | P2 |  | 4 | The draft asks for the agent's name and location but not the approximate time of the transaction (only the day, Thursday, was given). |
| dev-0234 | cash_in_not_credited | ✓ | drafted | P2 |  | 5 |  |
| dev-0235 | cash_in_not_credited | ✓ | drafted | P2 |  | 4 | The draft asks for the agent's name and location but not the approximate time of the transaction (only 'yesterday' was given). |
| dev-0236 | complaint | ✓ | drafted | P3 |  | 4 ⚠ | The English word 'chat' should be in Arabic (e.g. المحادثة); otherwise the draft is good. |
| dev-0237 | limit_upgrade | ✓ | drafted | P3 |  | 5 |  |
| dev-0238 | login_otp | ✓ | drafted | P2 |  | 5 |  |
| dev-0239 | unauthorized_charge | ✓ | escalated | P1 | fraud | — |  |
| dev-0240 | limit_upgrade | ✓ | drafted | P3 |  | 4 | The first sentence is long and restates the customer's request almost word for word, so it could be trimmed. |
