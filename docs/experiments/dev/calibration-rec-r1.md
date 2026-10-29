# Gate calibration: rec-r1 on dev

233 tickets, run on `api` with fixes: ask_if_missing, draft_check, fee_followup, fraud_secondary_cleanup, handoff_note, no_specific_followup, no_urgency_words, recheck_cross_team, reference_when_needed, usd_large_amount. The re-check model's answer is known for every ticket (`calibrate.py recheck-all`), so each threshold pair below is a replay of the gate with no new model calls. Draft-check flags are left out.

**Gold labels are model-written and not yet checked by a person**: a wrong label looks like a model error.

## Classifier confidence vs correct (first model)

| Confidence | Tickets | Correct | Re-check model correct |
|---|---|---|---|
| 0.95–1.00 | 61 | 61/61 | 61/61 |
| 0.90–0.95 | 116 | 116/116 | 116/116 |
| 0.85–0.90 | 35 | 34/35 | 33/35 |
| 0.80–0.85 | 7 | 6/7 | 7/7 |
| 0.75–0.80 | 6 | 6/6 | 6/6 |
| 0.60–0.75 | 8 | 5/8 | 7/8 |

## Threshold grid

Review rate = flagged + escalated (anything that needs more than a quick approve). Wrong → draft = wrong type that still gets a draft (flagged or ready); wrong → ready = of those, marked ready with no flag. Fraud → draft must be 0.

| pass_above | recheck_from | Ready | Flagged | Escalated | Review rate | Wrong → draft | Wrong → ready | Fraud → draft | Type used correct | Outcome = gold | Re-checks |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.70 | 0.50 | 194 | 21 | 18 | 17% | 4 | 2 | 0 | 228/233 | 227/233 | 36 |
| 0.70 | 0.55 | 194 | 21 | 18 | 17% | 4 | 2 | 0 | 228/233 | 227/233 | 36 |
| 0.70 | 0.60 | 194 | 21 | 18 | 17% | 4 | 2 | 0 | 228/233 | 227/233 | 36 |
| 0.70 | 0.65 | 193 | 19 | 21 | 17% | 2 | 2 | 0 | 230/233 | 226/233 | 34 |
| 0.70 | 0.70 | 193 | 19 | 21 | 17% | 4 | 2 | 0 | 228/233 | 226/233 | 15 |
| 0.75 | 0.50 | 193 | 22 | 18 | 17% | 3 | 1 | 0 | 229/233 | 226/233 | 40 |
| 0.75 | 0.55 | 193 | 22 | 18 | 17% | 3 | 1 | 0 | 229/233 | 226/233 | 40 |
| 0.75 **(now)** | 0.60 | 193 | 22 | 18 | 17% | 3 | 1 | 0 | 229/233 | 226/233 | 40 |
| 0.75 | 0.65 | 192 | 20 | 21 | 18% | 1 | 1 | 0 | 231/233 | 225/233 | 38 |
| 0.75 | 0.70 | 192 | 20 | 21 | 18% | 1 | 1 | 0 | 231/233 | 225/233 | 38 |
| 0.80 | 0.50 | 193 | 22 | 18 | 17% | 3 | 1 | 0 | 229/233 | 226/233 | 45 |
| 0.80 | 0.55 | 193 | 22 | 18 | 17% | 3 | 1 | 0 | 229/233 | 226/233 | 45 |
| 0.80 | 0.60 | 193 | 22 | 18 | 17% | 3 | 1 | 0 | 229/233 | 226/233 | 45 |
| 0.80 | 0.65 | 192 | 20 | 21 | 18% | 1 | 1 | 0 | 231/233 | 225/233 | 43 |
| 0.80 | 0.70 | 192 | 20 | 21 | 18% | 1 | 1 | 0 | 231/233 | 225/233 | 43 |
| 0.85 | 0.50 | 193 | 22 | 18 | 17% | 3 | 1 | 0 | 229/233 | 226/233 | 49 |
| 0.85 | 0.55 | 193 | 22 | 18 | 17% | 3 | 1 | 0 | 229/233 | 226/233 | 49 |
| 0.85 | 0.60 | 193 | 22 | 18 | 17% | 3 | 1 | 0 | 229/233 | 226/233 | 49 |
| 0.85 | 0.65 | 192 | 20 | 21 | 18% | 1 | 1 | 0 | 231/233 | 225/233 | 47 |
| 0.85 | 0.70 | 192 | 20 | 21 | 18% | 1 | 1 | 0 | 231/233 | 225/233 | 47 |
| 0.90 | 0.50 | 193 | 22 | 18 | 17% | 3 | 1 | 0 | 229/233 | 226/233 | 75 |
| 0.90 | 0.55 | 193 | 22 | 18 | 17% | 3 | 1 | 0 | 229/233 | 226/233 | 75 |
| 0.90 | 0.60 | 193 | 22 | 18 | 17% | 3 | 1 | 0 | 229/233 | 226/233 | 75 |
| 0.90 | 0.65 | 192 | 20 | 21 | 18% | 1 | 1 | 0 | 231/233 | 225/233 | 73 |
| 0.90 | 0.70 | 192 | 20 | 21 | 18% | 1 | 1 | 0 | 231/233 | 225/233 | 73 |
| 0.95 | 0.50 | 193 | 22 | 18 | 17% | 3 | 1 | 0 | 229/233 | 226/233 | 165 |
| 0.95 | 0.55 | 193 | 22 | 18 | 17% | 3 | 1 | 0 | 229/233 | 226/233 | 165 |
| 0.95 | 0.60 | 193 | 22 | 18 | 17% | 3 | 1 | 0 | 229/233 | 226/233 | 165 |
| 0.95 | 0.65 | 192 | 20 | 21 | 18% | 1 | 1 | 0 | 231/233 | 225/233 | 163 |
| 0.95 | 0.70 | 192 | 20 | 21 | 18% | 1 | 1 | 0 | 231/233 | 225/233 | 163 |

Self-check: replaying 0.75 / 0.60 gives the run's own outcome on 233/233 tickets.
