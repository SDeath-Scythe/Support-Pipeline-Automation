# Results log: fix experiments, 20 Oct 2026

Method: [README.md](README.md). Per-config pages and the summary table: [fixes_30/summary.md](fixes_30/summary.md) (round 1 kept as [summary-round1.md](fixes_30/summary-round1.md)). Every step below is its own commit on `claude/eager-tesla-x1dcxj`.

All numbers come from the `cli` backend: good for comparing configs with each other, **not** for thresholds or the MVP. Gold labels for `fixes_30` were written by the assistant, and the draft judge is a model, so treat single-ticket differences with care.

## Verdict per fix

| Fix | What it did on the tickets | Side effects | Recommendation |
|---|---|---|---|
| **F7** casual "هسه" | Priority 24/30 → **29/30**. All five casual-"هسه" tickets fixed; real urgency (f06, "ضروري") still P1. | None. Rule-only, so this result has no noise. | **Adopt.** |
| **F3** same-team re-check | On fixes_30, no same-team disagreement happened, so no effect. On 65 more tickets: **2 of 2** same-team disagreements (s18 reversal vs wrong recipient, m02 forgot PIN vs login) went from "escalated, no draft" to "flagged with a draft" scoring 4/5. | None seen; cross-team and fraud still escalate. Small sample (2 cases). | **Adopt.** The agent gets a usable draft and a note naming both options. |
| **F2** draft checks (v2) | v1 had a false alarm (f12, "we'll get back to you" read as a refund promise). v2 fixed that and two other false alarms found in a wider check. On all **161** distinct drafts so far, v2 flags **2**, both real stray Latin letters ("hلا", "wياهم"); **0** false alarms. | Catches nothing meaning-level: the judge's bad drafts (a promised branch address, an implied refund date) pass the rules. | **Adopt.** Cheap, no false alarms; catches about 1% of drafts. |
| **F6** fee field | Fee **0/4 → 4/4**, and again 4/4 in an uncached replicate. Classification: +f14 −f15 in round 1, not repeated in the replicate, so **no effect beyond noise**. | The classifier prompt changed, so it needs re-checking on the API dev set. | **Adopt.** Agents and drafts see the disputed fee, not the transaction amount. |
| **F8** unclear template | Saves the drafter call on unclear tickets (4/30 here; 63 → 59 calls). Draft scores on those 4 tickets: model drafts 5 5 3 4; template v1 4 5 2 4; v2 4 4 3 4. | Slightly lower quality: a fixed text can't answer an off-topic question (f09) and can't fit every opening (greeting vs "I have a problem"). | **Your call.** It saves about 6% of calls at a small quality cost. If you want it, v2 is the safer text. |
| **F5** policy facts (isolated) | Mean score 4.50 → 4.61, inside the noise floor (4.50–4.65 between identical baseline runs). Drafts now state response times and support hours. | One draft had a stray Latin letter (F2 v2 catches it). The judge rewards safety and editing effort, not added information, so the benefit is under-measured. | **Fill `config/policy.yaml` with your real values,** then re-test on the API. The values used here are placeholders (`config/experiments/policy_filled.yaml`). |

**Follow-up for F3 (not tested yet):** under F3 the draft and priority follow the *first* model's answer. In m02 that was wrong (login/OTP, P2), while the re-check had it right (forgot PIN, P3); see `screenshots/f3-m02-same-team-flagged.png`. Across all baseline runs, the re-check model was right in 7 of the 8 disagreements. A variant F3b that drafts from the re-check's answer is worth testing next.

## Combinations

All 10 pairs of {F2, F3, F6, F7, F8} and the full set were run in both rounds. **Every combination scored exactly the sum of its single fixes: zero interaction on every metric.** That fits the design: each fix acts on a different stage (F6 classify, F3 gate, F7 route, F8 and F2 draft), and F2's checks pass the F8 template. So the fixes can be adopted or dropped independently.

All five together (round 2) vs baseline on fixes_30:

| Metric | Baseline | All five |
|---|---|---|
| Outcome matches gold | 29/30 | **30/30** |
| Draft given iff it should be | 29/30 | **30/30** |
| Priority correct | 24/30 | **29/30** |
| Fee correct | 0/4 | **4/4** |
| Escalated | 2 | 1 |
| Model calls | 63 | 58 |
| Bad drafts / mean score | 2 / 4.50 | 3 / 4.38 (within noise) |

A fresh uncached replicate of all five (`fixes_30/all5-rep1.md`) confirms the robust gains: priority 29/30, fee 4/4, 59 model calls. f14 was wrong again, as in the F6 replicate, so the outcome/escalation gain in the table above is noise, not a fix.

## Noise floor and judge

- Two uncached baseline replicates: classification flipped on 0 and 2 tickets (f14, f15 are the unstable ones); bad drafts 0–2; mean score 4.50–4.65. **Draft-quality differences under about ±2 bad drafts or ±0.15 mean score are noise.**
- The judge graded the same 28 drafts twice: the same bad/ok verdict 28/28, and scores always within 1.
- Judge fix during round 1: the judge hadn't been told the drafter is given the handling team, so it marked team names as invented. All configs were re-scored after the fix.

## Timeline

| Step | What was tried | Result |
|---|---|---|
| Harness | Flags, response cache, judge, scorer | Commit `e83f638` |
| Test set | `fixes_30`: 30 new tickets, not the ones that motivated the fixes | `6085e77` |
| Fixes | F7, F3, F2, F8, F6, F5 behind flags, off by default | one commit each |
| Round 1 | Baseline, 2 noise replicates, judge noise, 6 singles, 10 pairs, all five | F7 clear win; F2 false alarm; F3 untested; F8 hurts the off-topic ticket |
| Round 2 | F2 v2 (3 false-alarm fixes), F8 v2 text, F6 replicate, F3 on 65 more tickets, re-run of every config with F2/F8 | See the verdicts above |

## Confidence (item 4): recommendation without 3 calls per ticket

What the data shows (155 baseline classifications across the four sets, cli backend):

| Model's own confidence | Correct |
|---|---|
| ≥ 0.90 | 95/95 |
| 0.75 – 0.90 | 40/42 |
| 0.60 – 0.75 | 12/18 |

- The score is already ordered the right way, and the gate only re-checks about 21% of tickets, so the pipeline averages about 2.1 calls per ticket. Nothing here needs three calls per ticket.
- The re-check earns its cost: in 7 of its 8 disagreements, the first model was the one that was wrong.
- The misses that get through sit at 0.75–0.90, and the disagreements cluster on a few **confusable pairs**: not received ↔ fee question (4 times), reversal ↔ wrong recipient, cash-in ↔ top-up, login ↔ forgot PIN, not received ↔ merchant payment.

Recommended, cheapest first:
1. **Confusable-pairs rule (no extra cost on most tickets):** a short list in `config/taxonomy.yaml`. If the predicted subcategory is in a confusable pair and confidence is under 0.90, re-check. This targets the 0.75–0.90 misses without re-checking everything.
2. **Runner-up in the same call:** ask the classifier for its second choice. If the runner-up is a different team with a small margin, re-check. It costs a few output tokens, not a call.
3. **Calibrate on the API dev set** (the repo's `require_api` path) and set the thresholds from the calibration table in the viewer. The cli numbers above are a direction, not thresholds.

These can be tested with this same harness, as F9 (confusable pairs) and F10 (runner-up).

## Monitoring additions (after the experiments)

These don't change what the agent sees; they help us watch the pipeline.

- **Cost logging:** every model step records its tokens (and, on cli, the cost Claude Code reports) in the run events, marked when the reply came from the cache; `run_batch.py` prints and stores run totals in `meta.usage`. The fresh all-five run used 59 calls, about 174k input and 12k output tokens, reported $0.06 for 30 tickets (about 6,200 tokens and $0.002 per ticket, including the cli's own context).
- **Viewer:** experiment runs appear under their own group in the source list; the queue can be sorted by priority (P1 and escalated first) or grouped by team; the overview shows tokens and cost per ticket; each model step shows its tokens. Screenshots are in `screenshots/`.
