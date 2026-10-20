# all5-rep1 on fixes_30

Fixes on: draft_check, fee_amount, no_now_urgency, recheck_same_team, unclear_template · backend `cli` · 2026-10-20T12:12:53 · compared with `baseline`

| Metric | baseline | all5-rep1 | Change |
|---|---|---|---|
| Subcategory correct | 29/30 | 29/30 |  |
| Outcome matches gold | 29/30 | 29/30 |  |
| Draft given iff it should be | 29/30 | 29/30 |  |
| Priority correct | 24/30 | 29/30 | +5 better |
| Amount correct | 30/30 | 30/30 |  |
| Fee correct (fee tickets) | 0/4 | 4/4 | +4 better |
| Escalated | 2 | 2 |  |
| Flagged | 0 | 0 |  |
| Drafted (ready) | 28 | 28 |  |
| Drafts judged | 28 | 28 |  |
| Bad drafts (judge) | 2 | 2 |  |
| Bad drafts marked ready | 2 | 2 |  |
| Mean draft score (1-5) | 4.5 | 4.46 | -0.04 worse |
| Model calls (pipeline) | 63 | 59 | -4 better |
| Judge: understood | 28/28 | 27/28 | -1 worse |
| Judge: grounded | 27/28 | 28/28 | +1 better |
| Judge: no_promise | 26/28 | 28/28 | +2 better |
| Judge: asks_right | 23/28 | 24/28 | +1 better |
| Judge: safe | 28/28 | 28/28 |  |
| Judge: tone | 28/28 | 28/28 |  |
| Judge: clean | 28/28 | 27/28 | -1 worse |

## Tickets that changed (28)

| Ticket | Targets | What changed |
|---|---|---|
| f01 | F7 | priority P2 → P3; draft changed (score 5 → 5) |
| f02 | F7 | priority P2 → P3; draft changed (score 5 → 5) |
| f03 | F7 | priority P2 → P3; draft changed (score 5 → 5) |
| f04 | F7 | priority P1 → P2; draft changed (score 5 → 5) |
| f05 | F7,F2 | priority P2 → P3; draft changed (score 4 → 5) |
| f06 | F7 | draft changed (score 4 → 5) |
| f07 | F8 | draft changed (score 5 → 4) |
| f08 | F8 | draft changed (score 5 → 4) |
| f09 | F8 | draft changed (score 3 → 3) |
| f10 | F8 | draft changed (score 4 → 4) |
| f11 | F3 | draft changed (score 5 → 5) |
| f12 | F3 | draft changed (score 5 → 4) |
| f13 | F3 | draft changed (score 4 → 5) |
| f15 | F3 | draft changed (score 5 → 4) |
| f16 | F3 | draft changed (score 4 → 5) |
| f17 | F6 | draft changed (score 5 → 5) |
| f18 | F6 | draft changed (score 4 → 4) |
| f19 | F6 | draft changed (score 5 → 4) |
| f20 | F2 | draft changed (score 5 → 4) |
| f21 | F2 | draft changed (score 5 → 5) |
| f22 | F2 | draft changed (score 5 → 5) |
| f23 | F2 | draft changed (score 3 → 4) |
| f24 | F2 | draft changed (score 4 → 4) |
| f25 | control | draft changed (score 4 → 4) |
| f27 | control | draft changed (score 4 → 4) |
| f28 | control | draft changed (score 4 → 4) |
| f29 | control | draft changed (score 5 → 5) |
| f30 | control | draft changed (score 5 → 5) |

## Every ticket

| Ticket | Gold | Got | Outcome | Priority | Flags | Draft score | Judge notes |
|---|---|---|---|---|---|---|---|
| f01 | rejected_or_pending | ✓ | drafted | P3 |  | 5 |  |
| f02 | forgot_pin | ✓ | drafted | P3 |  | 5 |  |
| f03 | app_bug | ✓ | drafted | P3 |  | 5 |  |
| f04 | sim_change | ✓ | drafted | P2 |  | 5 |  |
| f05 | fees_limits_question | ✓ | drafted | P3 |  | 5 |  |
| f06 | not_received | ✓ | drafted | P1 |  | 5 |  |
| f07 | unclear | ✓ | drafted | P3 |  | 4 | The line about a general question is awkward because the customer only sent a greeting; it should simply ask what they need help with. |
| f08 | unclear | ✓ | drafted | P3 |  | 4 | The 'general question' sentence doesn't fit a customer who said they have a problem and could be cut, leaving the request to explain what happened. |
| f09 | unclear | ✓ | drafted | P3 |  | 3 ⚠ | The draft is a generic template that ignores the customer's clear question about the nearest branch in Basra and asks for transaction details that are not needed. |
| f10 | unclear | ✓ | drafted | P3 |  | 4 | The customer hasn't stated their question yet, so the draft should simply ask them to write it instead of saying the team will review it. |
| f11 | wrong_recipient | ✓ | drafted | P2 |  | 5 |  |
| f12 | blocked_account | ✓ | drafted | P2 |  | 4 | Saying the accounts team will explain the reason ('ويوضحون لك السبب') is a mild commitment that could be softened to 'the team will check'. |
| f13 | rejected_or_pending | ✓ | drafted | P3 |  | 5 |  |
| f14 | fees_limits_question | ✗ not_received | escalated ✗ (drafted) | P2 ✗ (P3) | missing:reference, recheck_disagreed | — |  |
| f15 | topup_failed | ✓ | drafted | P3 |  | 4 | The phrase 'وصلت إنك' is awkward and should read 'فهمت إنك' or 'وصلني إنك', and 'بسرعة' hints at speed, which is better dropped. |
| f16 | card_payment_failed | ✓ | drafted | P3 |  | 5 |  |
| f17 | overcharged_fee | ✓ | drafted | P3 |  | 5 |  |
| f18 | fees_limits_question | ✓ | drafted | P3 |  | 4 | The draft adds 'دينار' to the amounts although the ticket gave no currency, so this small assumption may be worth removing. |
| f19 | overcharged_fee | ✓ | drafted | P3 |  | 4 | The phrasing 'أكو قسم الوكلاء راح يراجع' is slightly awkward and could be smoothed to 'قسم الوكلاء راح يراجع'. |
| f20 | wrong_recipient | ✓ | drafted | P2 |  | 4 | The draft does not respond to the customer's direct question about when the money will be returned, so the agent may want to add one line saying no exact date can be given yet. |
| f21 | topup_failed | ✓ | drafted | P3 |  | 5 |  |
| f22 | login_otp | ✓ | drafted | P2 |  | 5 |  |
| f23 | card_payment_failed | ✓ | drafted | P3 |  | 4 | The draft asks for the store name, but the customer already said Amazon, so nothing needs to be asked. |
| f24 | complaint | ✓ | drafted | P3 |  | 4 ⚠ | The words يتواصل and ويّاك are glued together without a space; otherwise the reply is calm, grounded and makes no promise of compensation. |
| f25 | not_received | ✓ | drafted | P2 |  | 4 | The draft does not ask for the time of the transfer; the ticket gives only 'since yesterday' as the date and no time. |
| f26 | suspected_scam | ✓ | escalated | P1 | fraud | — |  |
| f27 | delivery_or_activation | ✓ | drafted | P3 |  | 4 | The phrase 'شكلها وصلتك' sounds hesitant about something the customer already confirmed, and 'رحنوصّل' should be split as 'رح نوصّل'. |
| f28 | bill_not_reflected | ✓ | drafted | P3 |  | 4 | The draft asks for the bill type, but the customer already said it was the internet bill. |
| f29 | merchant_payment | ✓ | drafted | P3 |  | 5 |  |
| f30 | cash_out_refused | ✓ | drafted | P3 |  | 5 |  |
