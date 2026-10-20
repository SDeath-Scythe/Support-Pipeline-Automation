# F6-rep1 on fixes_30

Fixes on: fee_amount · backend `cli` · 2026-10-20T12:04:43 · compared with `baseline`

| Metric | baseline | F6-rep1 | Change |
|---|---|---|---|
| Subcategory correct | 29/30 | 28/30 | -1 worse |
| Outcome matches gold | 29/30 | 28/30 | -1 worse |
| Draft given iff it should be | 29/30 | 28/30 | -1 worse |
| Priority correct | 24/30 | 23/30 | -1 worse |
| Amount correct | 30/30 | 30/30 |  |
| Fee correct (fee tickets) | 0/4 | 4/4 | +4 better |
| Escalated | 2 | 3 | +1 |
| Flagged | 0 | 0 |  |
| Drafted (ready) | 28 | 27 | -1 |
| Drafts judged | 28 | 27 | -1 |
| Bad drafts (judge) | 2 | 0 | -2 better |
| Bad drafts marked ready | 2 | 0 | -2 better |
| Mean draft score (1-5) | 4.5 | 4.63 | +0.13 better |
| Model calls (pipeline) | 63 | 61 | -2 better |
| Judge: understood | 28/28 | 27/27 | -1 worse |
| Judge: grounded | 27/28 | 27/27 |  |
| Judge: no_promise | 26/28 | 27/27 | +1 better |
| Judge: asks_right | 23/28 | 24/27 | +1 better |
| Judge: safe | 28/28 | 27/27 | -1 worse |
| Judge: tone | 28/28 | 27/27 | -1 worse |
| Judge: clean | 28/28 | 27/27 | -1 worse |

## Tickets that changed (28)

| Ticket | Targets | What changed |
|---|---|---|
| f01 | F7 | draft changed (score 5 → 5) |
| f02 | F7 | draft changed (score 5 → 5) |
| f03 | F7 | draft changed (score 5 → 5) |
| f04 | F7 | draft changed (score 5 → 5) |
| f05 | F7,F2 | draft changed (score 4 → 4) |
| f06 | F7 | draft changed (score 4 → 4) |
| f07 | F8 | draft changed (score 5 → 5) |
| f08 | F8 | draft changed (score 5 → 5) |
| f09 | F8 | draft changed (score 3 → 4) |
| f10 | F8 | draft changed (score 4 → 5) |
| f11 | F3 | draft changed (score 5 → 5) |
| f12 | F3 | draft changed (score 5 → 5) |
| f13 | F3 | draft changed (score 4 → 5) |
| f15 | F3 | subcategory topup_failed → cash_in_not_credited; outcome drafted → escalated; priority P3 → P2; flags [] → ['recheck_disagreed']; draft changed (score 5 → —) |
| f16 | F3 | draft changed (score 4 → 4) |
| f17 | F6 | draft changed (score 5 → 5) |
| f18 | F6 | draft changed (score 4 → 5) |
| f19 | F6 | draft changed (score 5 → 5) |
| f20 | F2 | draft changed (score 5 → 4) |
| f21 | F2 | draft changed (score 5 → 5) |
| f22 | F2 | draft changed (score 5 → 5) |
| f23 | F2 | draft changed (score 3 → 4) |
| f24 | F2 | draft changed (score 4 → 4) |
| f25 | control | draft changed (score 4 → 4) |
| f27 | control | draft changed (score 4 → 5) |
| f28 | control | draft changed (score 4 → 4) |
| f29 | control | draft changed (score 5 → 4) |
| f30 | control | draft changed (score 5 → 5) |

## Every ticket

| Ticket | Gold | Got | Outcome | Priority | Flags | Draft score | Judge notes |
|---|---|---|---|---|---|---|---|
| f01 | rejected_or_pending | ✓ | drafted | P2 ✗ (P3) |  | 5 |  |
| f02 | forgot_pin | ✓ | drafted | P2 ✗ (P3) |  | 5 |  |
| f03 | app_bug | ✓ | drafted | P2 ✗ (P3) |  | 5 |  |
| f04 | sim_change | ✓ | drafted | P1 ✗ (P2) |  | 5 |  |
| f05 | fees_limits_question | ✓ | drafted | P2 ✗ (P3) |  | 4 | The draft switches between first-person singular and plural (نتفهم vs ما أگدر/حولت), a minor fix. |
| f06 | not_received | ✓ | drafted | P1 |  | 4 | The first sentence states 'not received' as fact instead of as the customer's report and does not acknowledge the urgency; one small edit would fix it. |
| f07 | unclear | ✓ | drafted | P3 |  | 5 |  |
| f08 | unclear | ✓ | drafted | P3 |  | 5 |  |
| f09 | unclear | ✓ | drafted | P3 |  | 4 | The draft states the team will reply with the branch information, which could be softened to a general 'the team will check' since it isn't confirmed they can provide it. |
| f10 | unclear | ✓ | drafted | P3 |  | 5 |  |
| f11 | wrong_recipient | ✓ | drafted | P2 |  | 5 |  |
| f12 | blocked_account | ✓ | drafted | P2 |  | 5 |  |
| f13 | rejected_or_pending | ✓ | drafted | P3 |  | 5 |  |
| f14 | fees_limits_question | ✗ not_received | escalated ✗ (drafted) | P2 ✗ (P3) | missing:reference, recheck_disagreed | — |  |
| f15 | topup_failed | ✗ cash_in_not_credited | escalated ✗ (drafted) | P2 ✗ (P3) | recheck_disagreed | — |  |
| f16 | card_payment_failed | ✓ | drafted | P3 |  | 4 | Minor wording slip: 'دفعت بي' should be 'دفعت بيه'. |
| f17 | overcharged_fee | ✓ | drafted | P3 |  | 5 |  |
| f18 | fees_limits_question | ✓ | drafted | P3 |  | 5 |  |
| f19 | overcharged_fee | ✓ | drafted | P3 |  | 5 |  |
| f20 | wrong_recipient | ✓ | drafted | P2 |  | 4 | The draft doesn't respond to the customer's demand for an exact date, and it adds the currency 'دينار', which the ticket never stated. |
| f21 | topup_failed | ✓ | drafted | P3 |  | 5 |  |
| f22 | login_otp | ✓ | drafted | P2 |  | 5 |  |
| f23 | card_payment_failed | ✓ | drafted | P3 |  | 4 | The draft asks for the store name, but the customer already said it was Amazon. |
| f24 | complaint | ✓ | drafted | P3 |  | 4 | The apology accepts the customer's unverified claim that earlier complaints went unanswered; consider softening it. |
| f25 | not_received | ✓ | drafted | P2 |  | 4 | The draft doesn't ask for the approximate time of the transfer; the ticket only says 'since yesterday'. |
| f26 | suspected_scam | ✓ | escalated | P1 | fraud | — |  |
| f27 | delivery_or_activation | ✓ | drafted | P3 |  | 5 |  |
| f28 | bill_not_reflected | ✓ | drafted | P3 |  | 4 | The draft asks for the bill type, but the ticket already says it is the internet bill. |
| f29 | merchant_payment | ✓ | drafted | P3 |  | 4 | Minor grammar slip: 'وصلنا إن دفعت' should be 'وصلنا إنك دفعت'. |
| f30 | cash_out_refused | ✓ | drafted | P3 |  | 5 |  |
