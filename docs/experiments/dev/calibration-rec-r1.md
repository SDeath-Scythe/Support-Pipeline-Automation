# Gate calibration: rec-r1 on dev

240 tickets, run on `api` with fixes: ask_if_missing, draft_check, fee_followup, fraud_secondary_cleanup, handoff_note, no_specific_followup, no_urgency_words, recheck_cross_team, reference_when_needed, usd_large_amount. The re-check model's answer is known for every ticket (`calibrate.py recheck-all`), so each threshold pair below is a replay of the gate with no new model calls. Draft-check flags are left out.

**Gold labels are model-written and not yet checked by a person**: a wrong label looks like a model error.

## Classifier confidence vs correct (first model)

| Confidence | Tickets | Correct | Re-check model correct |
|---|---|---|---|
| 0.95–1.00 | 61 | 61/61 | 61/61 |
| 0.90–0.95 | 119 | 119/119 | 119/119 |
| 0.85–0.90 | 36 | 34/36 | 33/36 |
| 0.80–0.85 | 9 | 8/9 | 9/9 |
| 0.75–0.80 | 6 | 6/6 | 6/6 |
| 0.60–0.75 | 9 | 5/9 | 7/9 |

## Threshold grid

Review rate = flagged + escalated (anything that needs more than a quick approve). Wrong → draft = wrong type that still gets a draft (flagged or ready); wrong → ready = of those, marked ready with no flag. Fraud → draft must be 0.

| pass_above | recheck_from | Ready | Flagged | Escalated | Review rate | Wrong → draft | Wrong → ready | Fraud → draft | Type used correct | Outcome = gold | Re-checks |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.70 | 0.50 | 200 | 22 | 18 | 17% | 6 | 2 | 0 | 233/240 | 232/240 | 39 |
| 0.70 | 0.55 | 200 | 22 | 18 | 17% | 6 | 2 | 0 | 233/240 | 232/240 | 39 |
| 0.70 | 0.60 | 200 | 22 | 18 | 17% | 6 | 2 | 0 | 233/240 | 232/240 | 39 |
| 0.70 | 0.65 | 199 | 19 | 22 | 17% | 3 | 2 | 0 | 235/240 | 231/240 | 36 |
| 0.70 | 0.70 | 199 | 19 | 22 | 17% | 5 | 2 | 0 | 233/240 | 231/240 | 17 |
| 0.75 | 0.50 | 199 | 23 | 18 | 17% | 5 | 1 | 0 | 234/240 | 231/240 | 43 |
| 0.75 | 0.55 | 199 | 23 | 18 | 17% | 5 | 1 | 0 | 234/240 | 231/240 | 43 |
| 0.75 **(now)** | 0.60 | 199 | 23 | 18 | 17% | 5 | 1 | 0 | 234/240 | 231/240 | 43 |
| 0.75 | 0.65 | 198 | 20 | 22 | 18% | 2 | 1 | 0 | 236/240 | 230/240 | 40 |
| 0.75 | 0.70 | 198 | 20 | 22 | 18% | 2 | 1 | 0 | 236/240 | 230/240 | 40 |
| 0.80 | 0.50 | 199 | 23 | 18 | 17% | 5 | 1 | 0 | 234/240 | 231/240 | 48 |
| 0.80 | 0.55 | 199 | 23 | 18 | 17% | 5 | 1 | 0 | 234/240 | 231/240 | 48 |
| 0.80 | 0.60 | 199 | 23 | 18 | 17% | 5 | 1 | 0 | 234/240 | 231/240 | 48 |
| 0.80 | 0.65 | 198 | 20 | 22 | 18% | 2 | 1 | 0 | 236/240 | 230/240 | 45 |
| 0.80 | 0.70 | 198 | 20 | 22 | 18% | 2 | 1 | 0 | 236/240 | 230/240 | 45 |
| 0.85 | 0.50 | 199 | 23 | 18 | 17% | 5 | 1 | 0 | 234/240 | 231/240 | 53 |
| 0.85 | 0.55 | 199 | 23 | 18 | 17% | 5 | 1 | 0 | 234/240 | 231/240 | 53 |
| 0.85 | 0.60 | 199 | 23 | 18 | 17% | 5 | 1 | 0 | 234/240 | 231/240 | 53 |
| 0.85 | 0.65 | 198 | 20 | 22 | 18% | 2 | 1 | 0 | 236/240 | 230/240 | 50 |
| 0.85 | 0.70 | 198 | 20 | 22 | 18% | 2 | 1 | 0 | 236/240 | 230/240 | 50 |
| 0.90 | 0.50 | 199 | 23 | 18 | 17% | 5 | 1 | 0 | 234/240 | 231/240 | 80 |
| 0.90 | 0.55 | 199 | 23 | 18 | 17% | 5 | 1 | 0 | 234/240 | 231/240 | 80 |
| 0.90 | 0.60 | 199 | 23 | 18 | 17% | 5 | 1 | 0 | 234/240 | 231/240 | 80 |
| 0.90 | 0.65 | 198 | 20 | 22 | 18% | 2 | 1 | 0 | 236/240 | 230/240 | 77 |
| 0.90 | 0.70 | 198 | 20 | 22 | 18% | 2 | 1 | 0 | 236/240 | 230/240 | 77 |
| 0.95 | 0.50 | 199 | 23 | 18 | 17% | 5 | 1 | 0 | 234/240 | 231/240 | 172 |
| 0.95 | 0.55 | 199 | 23 | 18 | 17% | 5 | 1 | 0 | 234/240 | 231/240 | 172 |
| 0.95 | 0.60 | 199 | 23 | 18 | 17% | 5 | 1 | 0 | 234/240 | 231/240 | 172 |
| 0.95 | 0.65 | 198 | 20 | 22 | 18% | 2 | 1 | 0 | 236/240 | 230/240 | 169 |
| 0.95 | 0.70 | 198 | 20 | 22 | 18% | 2 | 1 | 0 | 236/240 | 230/240 | 169 |

Self-check: replaying 0.75 / 0.60 gives the run's own outcome on 240/240 tickets.
