# baseline-rep2 on fixes_30

Fixes on: none · backend `cli` · 2026-10-20T11:53:34 · compared with `baseline`

| Metric | baseline | baseline-rep2 | Change |
|---|---|---|---|
| Subcategory correct | 29/30 | 27/30 | -2 worse |
| Outcome matches gold | 29/30 | 27/30 | -2 worse |
| Draft given iff it should be | 29/30 | 27/30 | -2 worse |
| Priority correct | 24/30 | 22/30 | -2 worse |
| Amount correct | 30/30 | 30/30 |  |
| Fee correct (fee tickets) | 0/4 | 0/4 |  |
| Escalated | 2 | 4 | +2 |
| Flagged | 0 | 0 |  |
| Drafted (ready) | 28 | 26 | -2 |
| Drafts judged | 28 | 26 | -2 |
| Bad drafts (judge) | 2 | 0 | -2 better |
| Bad drafts marked ready | 2 | 0 | -2 better |
| Mean draft score (1-5) | 4.5 | 4.65 | +0.15 better |
| Model calls (pipeline) | 63 | 60 | -3 better |
| Judge: understood | 28/28 | 26/26 | -2 worse |
| Judge: grounded | 27/28 | 26/26 | -1 worse |
| Judge: no_promise | 26/28 | 26/26 |  |
| Judge: asks_right | 23/28 | 22/26 | -1 worse |
| Judge: safe | 28/28 | 26/26 | -2 worse |
| Judge: tone | 28/28 | 26/26 | -2 worse |
| Judge: clean | 28/28 | 26/26 | -2 worse |

## Tickets that changed (28)

| Ticket | Targets | What changed |
|---|---|---|
| f01 | F7 | draft changed (score 5 → 5) |
| f02 | F7 | draft changed (score 5 → 5) |
| f03 | F7 | draft changed (score 5 → 5) |
| f04 | F7 | draft changed (score 5 → 4) |
| f05 | F7,F2 | draft changed (score 4 → 5) |
| f06 | F7 | draft changed (score 4 → 5) |
| f07 | F8 | draft changed (score 5 → 5) |
| f08 | F8 | draft changed (score 5 → 5) |
| f09 | F8 | draft changed (score 3 → 4) |
| f10 | F8 | draft changed (score 4 → 5) |
| f11 | F3 | draft changed (score 5 → 5) |
| f12 | F3 | draft changed (score 5 → 4) |
| f13 | F3 | draft changed (score 4 → 5) |
| f15 | F3 | subcategory topup_failed → cash_in_not_credited; outcome drafted → escalated; priority P3 → P2; flags [] → ['recheck_disagreed']; draft changed (score 5 → —) |
| f16 | F3 | draft changed (score 4 → 5) |
| f17 | F6 | draft changed (score 5 → 5) |
| f18 | F6 | draft changed (score 4 → 5) |
| f19 | F6 | draft changed (score 5 → 5) |
| f20 | F2 | draft changed (score 5 → 4) |
| f21 | F2 | draft changed (score 5 → 5) |
| f22 | F2 | subcategory login_otp → suspected_scam; outcome drafted → escalated; priority P2 → P1; flags [] → ['fraud']; draft changed (score 5 → —) |
| f23 | F2 | draft changed (score 3 → 3) |
| f24 | F2 | draft changed (score 4 → 5) |
| f25 | control | draft changed (score 4 → 4) |
| f27 | control | draft changed (score 4 → 4) |
| f28 | control | draft changed (score 4 → 4) |
| f29 | control | draft changed (score 5 → 5) |
| f30 | control | draft changed (score 5 → 5) |

## Every ticket

| Ticket | Gold | Got | Outcome | Priority | Flags | Draft score | Judge notes |
|---|---|---|---|---|---|---|---|
| f01 | rejected_or_pending | ✓ | drafted | P2 ✗ (P3) |  | 5 |  |
| f02 | forgot_pin | ✓ | drafted | P2 ✗ (P3) |  | 5 |  |
| f03 | app_bug | ✓ | drafted | P2 ✗ (P3) |  | 5 |  |
| f04 | sim_change | ✓ | drafted | P1 ✗ (P2) |  | 4 | The phrase 'وسلامتك من الضياع' is awkward and should be removed or replaced. |
| f05 | fees_limits_question | ✓ | drafted | P2 ✗ (P3) |  | 5 |  |
| f06 | not_received | ✓ | drafted | P1 |  | 5 |  |
| f07 | unclear | ✓ | drafted | P3 |  | 5 |  |
| f08 | unclear | ✓ | drafted | P3 |  | 5 |  |
| f09 | unclear | ✓ | drafted | P3 |  | 4 | Saying the team will confirm the address and send it implies a Basra branch exists, which Known facts do not confirm, so it could be softened. |
| f10 | unclear | ✓ | drafted | P3 |  | 5 |  |
| f11 | wrong_recipient | ✓ | drafted | P2 |  | 5 |  |
| f12 | blocked_account | ✓ | drafted | P2 |  | 4 | The opening restates the customer's problem back to them a bit awkwardly, but otherwise the draft is fine. |
| f13 | rejected_or_pending | ✓ | drafted | P3 |  | 5 |  |
| f14 | fees_limits_question | ✗ not_received | escalated ✗ (drafted) | P2 ✗ (P3) | missing:reference, recheck_disagreed | — |  |
| f15 | topup_failed | ✗ cash_in_not_credited | escalated ✗ (drafted) | P2 ✗ (P3) | recheck_disagreed | — |  |
| f16 | card_payment_failed | ✓ | drafted | P3 |  | 5 |  |
| f17 | overcharged_fee | ✓ | drafted | P3 |  | 5 |  |
| f18 | fees_limits_question | ✓ | drafted | P3 |  | 5 |  |
| f19 | overcharged_fee | ✓ | drafted | P3 |  | 5 |  |
| f20 | wrong_recipient | ✓ | drafted | P2 |  | 4 | The draft avoids a timeline but never tells the customer, who asked for an exact day, that it can't give one yet. |
| f21 | topup_failed | ✓ | drafted | P3 |  | 5 |  |
| f22 | login_otp | ✗ suspected_scam | escalated ✗ (drafted) | P1 ✗ (P2) | fraud | — |  |
| f23 | card_payment_failed | ✓ | drafted | P3 |  | 3 | The draft asks for the store name even though the ticket already says Amazon, and it doesn't address the refund question; the phrasing 'أكو عندك' is also slightly awkward. |
| f24 | complaint | ✓ | drafted | P3 |  | 5 |  |
| f25 | not_received | ✓ | drafted | P2 |  | 4 | The draft does not ask for the approximate time of the transfer; the ticket only says 'yesterday'. |
| f26 | suspected_scam | ✓ | escalated | P1 | fraud | — |  |
| f27 | delivery_or_activation | ✓ | drafted | P3 |  | 4 | The draft asks for the error message text even though no information is required for this issue. |
| f28 | bill_not_reflected | ✓ | drafted | P3 |  | 4 | The draft asks for the bill type, but the customer already said it is the internet bill. |
| f29 | merchant_payment | ✓ | drafted | P3 |  | 5 |  |
| f30 | cash_out_refused | ✓ | drafted | P3 |  | 5 |  |
