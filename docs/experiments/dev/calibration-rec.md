# Gate calibration: rec on dev

233 tickets, run on `api` with fixes: ask_if_missing, draft_check, fee_followup, fraud_secondary_cleanup, handoff_note, no_specific_followup, no_urgency_words, recheck_cross_team, reference_when_needed, usd_large_amount. The re-check model's answer is known for every ticket (`calibrate.py recheck-all`), so each threshold pair below is a replay of the gate with no new model calls. Draft-check flags are left out.

**Gold labels are model-written and not yet checked by a person**: a wrong label looks like a model error.

## Classifier confidence vs correct (first model)

| Confidence | Tickets | Correct | Re-check model correct |
|---|---|---|---|
| 0.95–1.00 | 54 | 54/54 | 54/54 |
| 0.90–0.95 | 118 | 118/118 | 118/118 |
| 0.85–0.90 | 34 | 33/34 | 33/34 |
| 0.80–0.85 | 15 | 14/15 | 14/15 |
| 0.75–0.80 | 8 | 6/8 | 8/8 |
| 0.60–0.75 | 4 | 3/4 | 3/4 |

## Threshold grid

Review rate = flagged + escalated (anything that needs more than a quick approve). Wrong → draft = wrong type that still gets a draft (flagged or ready); wrong → ready = of those, marked ready with no flag. Fraud → draft must be 0.

| pass_above | recheck_from | Ready | Flagged | Escalated | Review rate | Wrong → draft | Wrong → ready | Fraud → draft | Type used correct | Outcome = gold | Re-checks |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.70 | 0.50 | 192 | 23 | 18 | 18% | 4 | 2 | 0 | 228/233 | 225/233 | 37 |
| 0.70 | 0.55 | 192 | 23 | 18 | 18% | 4 | 2 | 0 | 228/233 | 225/233 | 37 |
| 0.70 | 0.60 | 192 | 23 | 18 | 18% | 4 | 2 | 0 | 228/233 | 225/233 | 37 |
| 0.70 | 0.65 | 192 | 22 | 19 | 18% | 3 | 2 | 0 | 229/233 | 225/233 | 37 |
| 0.70 | 0.70 | 192 | 22 | 19 | 18% | 5 | 2 | 0 | 227/233 | 225/233 | 16 |
| 0.75 | 0.50 | 192 | 23 | 18 | 18% | 4 | 2 | 0 | 228/233 | 225/233 | 38 |
| 0.75 | 0.55 | 192 | 23 | 18 | 18% | 4 | 2 | 0 | 228/233 | 225/233 | 38 |
| 0.75 **(now)** | 0.60 | 192 | 23 | 18 | 18% | 4 | 2 | 0 | 228/233 | 225/233 | 38 |
| 0.75 | 0.65 | 192 | 22 | 19 | 18% | 3 | 2 | 0 | 229/233 | 225/233 | 38 |
| 0.75 | 0.70 | 192 | 22 | 19 | 18% | 3 | 2 | 0 | 229/233 | 225/233 | 38 |
| 0.80 | 0.50 | 192 | 23 | 18 | 18% | 4 | 2 | 0 | 228/233 | 225/233 | 42 |
| 0.80 | 0.55 | 192 | 23 | 18 | 18% | 4 | 2 | 0 | 228/233 | 225/233 | 42 |
| 0.80 | 0.60 | 192 | 23 | 18 | 18% | 4 | 2 | 0 | 228/233 | 225/233 | 42 |
| 0.80 | 0.65 | 192 | 22 | 19 | 18% | 3 | 2 | 0 | 229/233 | 225/233 | 42 |
| 0.80 | 0.70 | 192 | 22 | 19 | 18% | 3 | 2 | 0 | 229/233 | 225/233 | 42 |
| 0.85 | 0.50 | 192 | 23 | 18 | 18% | 4 | 2 | 0 | 228/233 | 225/233 | 51 |
| 0.85 | 0.55 | 192 | 23 | 18 | 18% | 4 | 2 | 0 | 228/233 | 225/233 | 51 |
| 0.85 | 0.60 | 192 | 23 | 18 | 18% | 4 | 2 | 0 | 228/233 | 225/233 | 51 |
| 0.85 | 0.65 | 192 | 22 | 19 | 18% | 3 | 2 | 0 | 229/233 | 225/233 | 51 |
| 0.85 | 0.70 | 192 | 22 | 19 | 18% | 3 | 2 | 0 | 229/233 | 225/233 | 51 |
| 0.90 | 0.50 | 191 | 24 | 18 | 18% | 3 | 1 | 0 | 229/233 | 224/233 | 78 |
| 0.90 | 0.55 | 191 | 24 | 18 | 18% | 3 | 1 | 0 | 229/233 | 224/233 | 78 |
| 0.90 | 0.60 | 191 | 24 | 18 | 18% | 3 | 1 | 0 | 229/233 | 224/233 | 78 |
| 0.90 | 0.65 | 191 | 23 | 19 | 18% | 2 | 1 | 0 | 230/233 | 224/233 | 78 |
| 0.90 | 0.70 | 191 | 23 | 19 | 18% | 2 | 1 | 0 | 230/233 | 224/233 | 78 |
| 0.95 | 0.50 | 191 | 24 | 18 | 18% | 3 | 1 | 0 | 229/233 | 224/233 | 172 |
| 0.95 | 0.55 | 191 | 24 | 18 | 18% | 3 | 1 | 0 | 229/233 | 224/233 | 172 |
| 0.95 | 0.60 | 191 | 24 | 18 | 18% | 3 | 1 | 0 | 229/233 | 224/233 | 172 |
| 0.95 | 0.65 | 191 | 23 | 19 | 18% | 2 | 1 | 0 | 230/233 | 224/233 | 172 |
| 0.95 | 0.70 | 191 | 23 | 19 | 18% | 2 | 1 | 0 | 230/233 | 224/233 | 172 |

Self-check: replaying 0.75 / 0.60 gives the run's own outcome on 233/233 tickets.
