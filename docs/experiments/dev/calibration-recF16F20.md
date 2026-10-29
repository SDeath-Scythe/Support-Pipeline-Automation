# Gate calibration: recF16F20 on dev

233 tickets, run on `api` with fixes: ask_if_missing, draft_check, duplicate_payment_hint, fee_followup, fraud_secondary_cleanup, handoff_note, no_specific_followup, no_urgency_words, recheck_cross_team, reference_when_needed, usd_large_amount, warqa_usd. The re-check model's answer is known for every ticket (`calibrate.py recheck-all`), so each threshold pair below is a replay of the gate with no new model calls. Draft-check flags are left out.

**Gold labels are model-written and not yet checked by a person**: a wrong label looks like a model error.

## Classifier confidence vs correct (first model)

| Confidence | Tickets | Correct | Re-check model correct |
|---|---|---|---|
| 0.95–1.00 | 58 | 58/58 | 58/58 |
| 0.90–0.95 | 126 | 126/126 | 126/126 |
| 0.85–0.90 | 29 | 29/29 | 29/29 |
| 0.80–0.85 | 12 | 10/12 | 12/12 |
| 0.75–0.80 | 3 | 3/3 | 2/3 |
| 0.60–0.75 | 5 | 3/5 | 5/5 |

## Threshold grid

Review rate = flagged + escalated (anything that needs more than a quick approve). Wrong → draft = wrong type that still gets a draft (flagged or ready); wrong → ready = of those, marked ready with no flag. Fraud → draft must be 0.

| pass_above | recheck_from | Ready | Flagged | Escalated | Review rate | Wrong → draft | Wrong → ready | Fraud → draft | Type used correct | Outcome = gold | Re-checks |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.70 | 0.50 | 194 | 21 | 18 | 17% | 1 | 1 | 0 | 231/233 | 227/233 | 38 |
| 0.70 | 0.55 | 194 | 21 | 18 | 17% | 1 | 1 | 0 | 231/233 | 227/233 | 38 |
| 0.70 | 0.60 | 194 | 21 | 18 | 17% | 1 | 1 | 0 | 231/233 | 227/233 | 38 |
| 0.70 | 0.65 | 194 | 21 | 18 | 17% | 1 | 1 | 0 | 231/233 | 227/233 | 38 |
| 0.70 | 0.70 | 194 | 21 | 18 | 17% | 3 | 1 | 0 | 229/233 | 227/233 | 17 |
| 0.75 | 0.50 | 194 | 21 | 18 | 17% | 1 | 1 | 0 | 231/233 | 227/233 | 40 |
| 0.75 | 0.55 | 194 | 21 | 18 | 17% | 1 | 1 | 0 | 231/233 | 227/233 | 40 |
| 0.75 **(now)** | 0.60 | 194 | 21 | 18 | 17% | 1 | 1 | 0 | 231/233 | 227/233 | 40 |
| 0.75 | 0.65 | 194 | 21 | 18 | 17% | 1 | 1 | 0 | 231/233 | 227/233 | 40 |
| 0.75 | 0.70 | 194 | 21 | 18 | 17% | 1 | 1 | 0 | 231/233 | 227/233 | 40 |
| 0.80 | 0.50 | 193 | 22 | 18 | 17% | 2 | 1 | 0 | 230/233 | 226/233 | 42 |
| 0.80 | 0.55 | 193 | 22 | 18 | 17% | 2 | 1 | 0 | 230/233 | 226/233 | 42 |
| 0.80 | 0.60 | 193 | 22 | 18 | 17% | 2 | 1 | 0 | 230/233 | 226/233 | 42 |
| 0.80 | 0.65 | 193 | 21 | 19 | 17% | 1 | 1 | 0 | 231/233 | 226/233 | 42 |
| 0.80 | 0.70 | 193 | 21 | 19 | 17% | 1 | 1 | 0 | 231/233 | 226/233 | 42 |
| 0.85 | 0.50 | 192 | 23 | 18 | 18% | 1 | 0 | 0 | 231/233 | 225/233 | 50 |
| 0.85 | 0.55 | 192 | 23 | 18 | 18% | 1 | 0 | 0 | 231/233 | 225/233 | 50 |
| 0.85 | 0.60 | 192 | 23 | 18 | 18% | 1 | 0 | 0 | 231/233 | 225/233 | 50 |
| 0.85 | 0.65 | 192 | 22 | 19 | 18% | 0 | 0 | 0 | 232/233 | 225/233 | 50 |
| 0.85 | 0.70 | 192 | 22 | 19 | 18% | 0 | 0 | 0 | 232/233 | 225/233 | 50 |
| 0.90 | 0.50 | 192 | 23 | 18 | 18% | 1 | 0 | 0 | 231/233 | 225/233 | 74 |
| 0.90 | 0.55 | 192 | 23 | 18 | 18% | 1 | 0 | 0 | 231/233 | 225/233 | 74 |
| 0.90 | 0.60 | 192 | 23 | 18 | 18% | 1 | 0 | 0 | 231/233 | 225/233 | 74 |
| 0.90 | 0.65 | 192 | 22 | 19 | 18% | 0 | 0 | 0 | 232/233 | 225/233 | 74 |
| 0.90 | 0.70 | 192 | 22 | 19 | 18% | 0 | 0 | 0 | 232/233 | 225/233 | 74 |
| 0.95 | 0.50 | 192 | 23 | 18 | 18% | 1 | 0 | 0 | 231/233 | 225/233 | 172 |
| 0.95 | 0.55 | 192 | 23 | 18 | 18% | 1 | 0 | 0 | 231/233 | 225/233 | 172 |
| 0.95 | 0.60 | 192 | 23 | 18 | 18% | 1 | 0 | 0 | 231/233 | 225/233 | 172 |
| 0.95 | 0.65 | 192 | 22 | 19 | 18% | 0 | 0 | 0 | 232/233 | 225/233 | 172 |
| 0.95 | 0.70 | 192 | 22 | 19 | 18% | 0 | 0 | 0 | 232/233 | 225/233 | 172 |

Self-check: replaying 0.75 / 0.60 gives the run's own outcome on 233/233 tickets.
