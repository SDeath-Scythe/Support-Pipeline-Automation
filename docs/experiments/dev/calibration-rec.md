# Gate calibration: rec on dev

240 tickets, run on `api` with fixes: ask_if_missing, draft_check, fee_followup, fraud_secondary_cleanup, handoff_note, no_specific_followup, no_urgency_words, recheck_cross_team, reference_when_needed, usd_large_amount. The re-check model's answer is known for every ticket (`calibrate.py recheck-all`), so each threshold pair below is a replay of the gate with no new model calls. Draft-check flags are left out.

**Gold labels are model-written and not yet checked by a person**: a wrong label looks like a model error.

## Classifier confidence vs correct (first model)

| Confidence | Tickets | Correct | Re-check model correct |
|---|---|---|---|
| 0.95–1.00 | 54 | 54/54 | 54/54 |
| 0.90–0.95 | 121 | 121/121 | 121/121 |
| 0.85–0.90 | 35 | 34/35 | 34/35 |
| 0.80–0.85 | 16 | 15/16 | 15/16 |
| 0.75–0.80 | 8 | 6/8 | 8/8 |
| 0.60–0.75 | 6 | 5/6 | 5/6 |

## Threshold grid

Review rate = flagged + escalated (anything that needs more than a quick approve). Wrong → draft = wrong type that still gets a draft (flagged or ready); wrong → ready = of those, marked ready with no flag. Fraud → draft must be 0.

| pass_above | recheck_from | Ready | Flagged | Escalated | Review rate | Wrong → draft | Wrong → ready | Fraud → draft | Type used correct | Outcome = gold | Re-checks |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.70 | 0.50 | 197 | 25 | 18 | 18% | 4 | 2 | 0 | 235/240 | 231/240 | 41 |
| 0.70 | 0.55 | 197 | 25 | 18 | 18% | 4 | 2 | 0 | 235/240 | 231/240 | 41 |
| 0.70 | 0.60 | 197 | 25 | 18 | 18% | 4 | 2 | 0 | 235/240 | 231/240 | 41 |
| 0.70 | 0.65 | 197 | 23 | 20 | 18% | 3 | 2 | 0 | 236/240 | 230/240 | 40 |
| 0.70 | 0.70 | 197 | 23 | 20 | 18% | 5 | 2 | 0 | 234/240 | 230/240 | 18 |
| 0.75 | 0.50 | 197 | 25 | 18 | 18% | 4 | 2 | 0 | 235/240 | 231/240 | 42 |
| 0.75 | 0.55 | 197 | 25 | 18 | 18% | 4 | 2 | 0 | 235/240 | 231/240 | 42 |
| 0.75 **(now)** | 0.60 | 197 | 25 | 18 | 18% | 4 | 2 | 0 | 235/240 | 231/240 | 42 |
| 0.75 | 0.65 | 197 | 23 | 20 | 18% | 3 | 2 | 0 | 236/240 | 230/240 | 41 |
| 0.75 | 0.70 | 197 | 23 | 20 | 18% | 3 | 2 | 0 | 236/240 | 230/240 | 41 |
| 0.80 | 0.50 | 197 | 25 | 18 | 18% | 4 | 2 | 0 | 235/240 | 231/240 | 46 |
| 0.80 | 0.55 | 197 | 25 | 18 | 18% | 4 | 2 | 0 | 235/240 | 231/240 | 46 |
| 0.80 | 0.60 | 197 | 25 | 18 | 18% | 4 | 2 | 0 | 235/240 | 231/240 | 46 |
| 0.80 | 0.65 | 197 | 23 | 20 | 18% | 3 | 2 | 0 | 236/240 | 230/240 | 45 |
| 0.80 | 0.70 | 197 | 23 | 20 | 18% | 3 | 2 | 0 | 236/240 | 230/240 | 45 |
| 0.85 | 0.50 | 197 | 25 | 18 | 18% | 4 | 2 | 0 | 235/240 | 231/240 | 56 |
| 0.85 | 0.55 | 197 | 25 | 18 | 18% | 4 | 2 | 0 | 235/240 | 231/240 | 56 |
| 0.85 | 0.60 | 197 | 25 | 18 | 18% | 4 | 2 | 0 | 235/240 | 231/240 | 56 |
| 0.85 | 0.65 | 197 | 23 | 20 | 18% | 3 | 2 | 0 | 236/240 | 230/240 | 55 |
| 0.85 | 0.70 | 197 | 23 | 20 | 18% | 3 | 2 | 0 | 236/240 | 230/240 | 55 |
| 0.90 | 0.50 | 196 | 26 | 18 | 18% | 3 | 1 | 0 | 236/240 | 230/240 | 83 |
| 0.90 | 0.55 | 196 | 26 | 18 | 18% | 3 | 1 | 0 | 236/240 | 230/240 | 83 |
| 0.90 | 0.60 | 196 | 26 | 18 | 18% | 3 | 1 | 0 | 236/240 | 230/240 | 83 |
| 0.90 | 0.65 | 196 | 24 | 20 | 18% | 2 | 1 | 0 | 237/240 | 229/240 | 82 |
| 0.90 | 0.70 | 196 | 24 | 20 | 18% | 2 | 1 | 0 | 237/240 | 229/240 | 82 |
| 0.95 | 0.50 | 196 | 26 | 18 | 18% | 3 | 1 | 0 | 236/240 | 230/240 | 179 |
| 0.95 | 0.55 | 196 | 26 | 18 | 18% | 3 | 1 | 0 | 236/240 | 230/240 | 179 |
| 0.95 | 0.60 | 196 | 26 | 18 | 18% | 3 | 1 | 0 | 236/240 | 230/240 | 179 |
| 0.95 | 0.65 | 196 | 24 | 20 | 18% | 2 | 1 | 0 | 237/240 | 229/240 | 178 |
| 0.95 | 0.70 | 196 | 24 | 20 | 18% | 2 | 1 | 0 | 237/240 | 229/240 | 178 |

Self-check: replaying 0.75 / 0.60 gives the run's own outcome on 240/240 tickets.
