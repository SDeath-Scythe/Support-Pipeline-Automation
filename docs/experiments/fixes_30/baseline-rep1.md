# baseline-rep1 on fixes_30

Fixes on: none · backend `cli` · 2026-10-20T11:53:34 · compared with `baseline`

| Metric | baseline | baseline-rep1 | Change |
|---|---|---|---|
| Subcategory correct | 29/30 | 29/30 |  |
| Outcome matches gold | 29/30 | 29/30 |  |
| Draft given iff it should be | 29/30 | 29/30 |  |
| Priority correct | 24/30 | 24/30 |  |
| Amount correct | 30/30 | 29/30 | -1 worse |
| Fee correct (fee tickets) | 0/4 | 0/4 |  |
| Escalated | 2 | 2 |  |
| Flagged | 0 | 0 |  |
| Drafted (ready) | 28 | 28 |  |
| Drafts judged | 28 | 28 |  |
| Bad drafts (judge) | 2 | 0 | -2 better |
| Bad drafts marked ready | 2 | 0 | -2 better |
| Mean draft score (1-5) | 4.5 | 4.64 | +0.14 better |
| Model calls (pipeline) | 63 | 64 | +1 worse |
| Judge: understood | 28/28 | 28/28 |  |
| Judge: grounded | 27/28 | 28/28 | +1 better |
| Judge: no_promise | 26/28 | 28/28 | +2 better |
| Judge: asks_right | 23/28 | 25/28 | +2 better |
| Judge: safe | 28/28 | 28/28 |  |
| Judge: tone | 28/28 | 28/28 |  |
| Judge: clean | 28/28 | 28/28 |  |

## Tickets that changed (28)

| Ticket | Targets | What changed |
|---|---|---|
| f01 | F7 | draft changed (score 5 → 5) |
| f02 | F7 | draft changed (score 5 → 5) |
| f03 | F7 | draft changed (score 5 → 5) |
| f04 | F7 | draft changed (score 5 → 5) |
| f05 | F7,F2 | draft changed (score 4 → 4) |
| f06 | F7 | draft changed (score 4 → 5) |
| f07 | F8 | draft changed (score 5 → 5) |
| f08 | F8 | draft changed (score 5 → 5) |
| f09 | F8 | draft changed (score 3 → 5) |
| f10 | F8 | draft changed (score 4 → 5) |
| f11 | F3 | draft changed (score 5 → 5) |
| f12 | F3 | draft changed (score 5 → 5) |
| f13 | F3 | draft changed (score 4 → 5) |
| f15 | F3 | draft changed (score 5 → 5) |
| f16 | F3 | draft changed (score 4 → 5) |
| f17 | F6 | draft changed (score 5 → 4) |
| f18 | F6 | draft changed (score 4 → 4) |
| f19 | F6 | draft changed (score 5 → 5) |
| f20 | F2 | draft changed (score 5 → 4) |
| f21 | F2 | draft changed (score 5 → 5) |
| f22 | F2 | draft changed (score 5 → 5) |
| f23 | F2 | draft changed (score 3 → 4) |
| f24 | F2 | draft changed (score 4 → 4) |
| f25 | control | draft changed (score 4 → 4) |
| f27 | control | draft changed (score 4 → 4) |
| f28 | control | draft changed (score 4 → 3) |
| f29 | control | draft changed (score 5 → 5) |
| f30 | control | draft changed (score 5 → 5) |

## Every ticket

| Ticket | Gold | Got | Outcome | Priority | Flags | Draft score | Judge notes |
|---|---|---|---|---|---|---|---|
| f01 | rejected_or_pending | ✓ | drafted | P2 ✗ (P3) |  | 5 |  |
| f02 | forgot_pin | ✓ | drafted | P2 ✗ (P3) |  | 5 |  |
| f03 | app_bug | ✓ | drafted | P2 ✗ (P3) |  | 5 |  |
| f04 | sim_change | ✓ | drafted | P1 ✗ (P2) |  | 5 |  |
| f05 | fees_limits_question | ✓ | drafted | P2 ✗ (P3) |  | 4 | Saying the team will confirm the 'exact correct number' sounds like a promised result, so it should be softened to a general next step. |
| f06 | not_received | ✓ | drafted | P1 |  | 5 |  |
| f07 | unclear | ✓ | drafted | P3 |  | 5 |  |
| f08 | unclear | ✓ | drafted | P3 |  | 5 |  |
| f09 | unclear | ✓ | drafted | P3 |  | 5 |  |
| f10 | unclear | ✓ | drafted | P3 |  | 5 |  |
| f11 | wrong_recipient | ✓ | drafted | P2 |  | 5 |  |
| f12 | blocked_account | ✓ | drafted | P2 |  | 5 |  |
| f13 | rejected_or_pending | ✓ | drafted | P3 |  | 5 |  |
| f14 | fees_limits_question | ✗ not_received | escalated ✗ (drafted) | P2 ✗ (P3) | missing:reference, recheck_disagreed | — |  |
| f15 | topup_failed | ✓ | drafted | P3 |  | 5 |  |
| f16 | card_payment_failed | ✓ | drafted | P3 |  | 5 |  |
| f17 | overcharged_fee | ✓ | drafted | P3 |  | 4 | The draft asks for the agent's location even though the customer already said Mansour, though asking for the exact spot is a reasonable refinement. |
| f18 | fees_limits_question | ✓ | drafted | P3 |  | 4 | The draft adds the currency 'دينار', which the ticket doesn't state, and slightly over-commits by saying the team will explain the reason 'بالتفصيل'. |
| f19 | overcharged_fee | ✓ | drafted | P3 |  | 5 |  |
| f20 | wrong_recipient | ✓ | drafted | P2 |  | 4 | "شفنا" implies the team already verified the transaction, which is better phrased as restating what the customer said. |
| f21 | topup_failed | ✓ | drafted | P3 |  | 5 |  |
| f22 | login_otp | ✓ | drafted | P2 |  | 5 |  |
| f23 | card_payment_failed | ✓ | drafted | P3 |  | 4 | The draft asks for the store name even though the customer already said Amazon. |
| f24 | complaint | ✓ | drafted | P3 |  | 4 | The draft doesn't acknowledge the compensation demand or say the complaint will be passed to the team for follow-up. |
| f25 | not_received | ✓ | drafted | P2 |  | 4 | The draft does not ask for the approximate time of the transfer; the ticket gives only 'yesterday'. |
| f26 | suspected_scam | ✓ | escalated | P1 | fraud | — |  |
| f27 | delivery_or_activation | ✓ | drafted | P3 |  | 4 | Typo: 'ما تنفعل' should be 'ما تتفعل' (activate), as currently written it reads like 'doesn't get excited'. |
| f28 | bill_not_reflected | ✓ | drafted | P3 |  | 3 | The draft asks for the bill type even though the customer already said it was the internet bill. |
| f29 | merchant_payment | ✓ | drafted | P3 |  | 5 |  |
| f30 | cash_out_refused | ✓ | drafted | P3 |  | 5 |  |
