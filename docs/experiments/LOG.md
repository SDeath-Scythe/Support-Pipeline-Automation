# Results log: fix experiments, 20 Oct 2026

Method: [README.md](README.md). Per-config pages and the summary table: [fixes_30/summary.md](fixes_30/summary.md) (round 1 kept as [summary-round1.md](fixes_30/summary-round1.md)). Every step below is its own commit on `claude/eager-tesla-x1dcxj`.

All numbers come from the `cli` backend: good for comparing configs with each other, **not** for thresholds or the MVP. Gold labels for `fixes_30` were written by the assistant, and the draft judge is a model, so treat single-ticket differences with care.

## 29 Oct: first API runs, and the cli judge becomes the default

The first runs on the **API** backend (the $35 test key), with the recommended set plus F17, F18 and F19 on, on a 30-ticket sample of dev (one ticket from each of the 23 subcategories plus 7 at random, seed 29; the file lives in `runs/sets/`, git-ignored).

- **Cost:** 10-ticket pilot $0.030, the other 20 tickets $0.052: **about $0.002–0.003 per ticket**. The drafter (Sonnet) is ~70% of it. The prompt cache works: 62,562 prompt tokens were read from it in the 20-ticket run, and the first ticket now runs alone so the parallel workers don't each pay to write the same cache entry.
- **Accuracy on the 30:** subcategory used correct 29/30, priority 29/30. The two differences from gold: dev-0121 (the models disagreed; F3c used the re-check's answer, which is correct, and flagged it, as designed) and dev-0109 (gold `reversal_request`, classified and drafted as `merchant_payment`: a wrong type that reached a draft).
- **F2 false alarm, fixed:** dev-0077's draft echoed the customer's "declined" before an Arabic comma, and F2 counted the comma (and tatweel) as an Arabic letter. Only Arabic letters count now.

**Judge on cli vs API** ([dev_sample30/judge_backends-rec.md](dev_sample30/judge_backends-rec.md)): the same 27 drafts graded 3 times on each backend.

| | Score identical | Score within 1 | Same bad/ok verdict |
|---|---|---|---|
| cli vs cli | 83% | 100% | 95% |
| API vs API | 85% | 100% | 98% |
| **cli vs API** | **82%** | **100%** | **97%** |

The cli judge agrees with the API judge as well as each agrees with itself; per-draft average scores differ by 0.14 (cli mean 4.33, API 4.42), never by more than 1. **Decision (author's rule: if similar, take the free one): drafts are graded on cli by default** (`report` and `judge-noise` take `--judge-backend api` to override). Pipeline numbers still come from the API. The API grading cost $0.65 for 81 gradings.

## Current recommendation (after round 3)

**Adopt F2 + F3c + F6b + F15 + F11 + F12 (v2) + F14b.** F15 (no word raises priority) replaced F7 on 23 Oct after a correction from the project author; F14b was added after the fraud/secondary follow-up below. **F16** (the meaning of "ورقة") is pending an API test with replicates. This replaces F3 with F3c and F6 with F6b compared with the round-2 advice. F8 stays your call; F5 needs your real policy values. Do not adopt F9, F10 or F13 (reasons below).

Confirmed on **holdout_30**: 30 tickets written before any round-3 result and run only once the recommendation was fixed. Three runs of each arm (as run, fresh classifier, fresh drafter):

| Metric | Baseline | Recommended | Round-2 set (F2+F3+F6+F7) |
|---|---|---|---|
| Subcategory used correct | 28 / 28 / 28 | **29 / 29 / 29** | 27 |
| Draft given iff it should be | 29 / 28 / 29 | **30 / 29 / 30** | 27 |
| Priority correct | 28 / 28 / 28 | **30 / 30 / 30** | 29 |
| Fee correct | 0/2 | **2/2** | 2/2 |
| Escalated | 3 / 4 / 3 | 2 / 3 / 2 | 5 |
| Mean draft score (pooled, ~55 drafts each) | 4.44 | **4.63** | 4.36 |
| Drafts asking for the right info (pooled) | 78% | **89%** | — |
| Grounded (pooled) | 98% | **100%** | — |
| Model calls | 63 | 68 | 59 |

Pages: [holdout_30/summary.md](holdout_30/summary.md), [pooled drafts](holdout_30/pooled-rec-vs-baseline.md). The dev results (95 tickets, `dev_95`) are in [dev_95/summary.md](dev_95/summary.md).

One ticket is missed by every configuration: **h19** ("I want to raise my monthly limit, how long, which papers?") is read as a fee/limit *question* instead of `limit_upgrade`. It's the same confusion as s05 and m08 on the dev set. Adding `[limit_upgrade, fees_limits_question]` as a look-alike pair, or a sharper hint, is the next thing to try. It was left alone here so the hold-out stays a fair test.

### Corrections from the project author (23 Oct): F15 and F16

The project author, a native Iraqi speaker, corrected two assumptions built into the pipeline:

| Flag | Change | Why | Status |
|---|---|---|---|
| **F15** `no_urgency_words` | No word changes priority; only the subcategory default and the ≥ 1,000,000 IQD amount rule | No word (هسه, ضروري, عاجل, بسرعة, صارلي يومين…) reliably marks urgency. F7 only removed هسه | **Adopt, replaces F7.** Rule-only, so no model noise. The old probe sets' gold priorities assumed urgent words raise priority, so priority scores on those sets will drop under F15; the regenerated dataset is labelled with F15 |
| **F16** `warqa_usd` | The classifier prompt's amount example: "ورقة" is a 100 USD note, "خمسين ورقة" = 5,000 USD (amount_usd); "خمسين الف" = 50,000 IQD | The old example said "خمسين ورقة" = 50,000 IQD: wrong, and it contradicted the amount_usd line | **Not run.** It edits the shared classifier prompt; F6, F13 and F14 all shifted other classifications, so test it with replicates on the API before adopting |

### Follow-up: the fraud / secondary-subcategory rule (F14, F14b)

**Raised by the author:** the classifier prompt says "pick exactly one category and one subcategory", yet rule 1 says "put the other issue in `secondary_subcategory`" for fraud. Worse, rule 1 contradicts rule 5 ("being locked out after a scam … stays with the main subcategory"). Across all 522 saved fraud classifications, 26 (5%) put a consequence of the fraud in the secondary field: e02 and f22 (`login_otp`), f26 (`unauthorized_charge`). The same ticket got different answers on different runs.

Tested only on existing tickets (dev_95, holdout_30), with 3 runs per arm on dev:

| Fix | Change | Result | Verdict |
|---|---|---|---|
| **F14** | Reword the two prompt sentences so rule 1 defers to rule 5 | Secondary correct 64/63/63 → 65/64/64 (one ticket). But subcategory used 90/88/91 → **87/86/87**, and 95 → **92** inside the recommended set; **3 wrong types reach a draft in every run** (0 before). The re-check uses the same prompt and now makes the same mistakes (m02, m23), so the disagreement F3c relies on disappears; m08 also flips. Hold-out 28 → 27/26. | **Do not adopt** |
| **F14b** | Same rule enforced in code: a fraud ticket's secondary is cleared when it is an account-access or fraud subcategory (a consequence); a separate request (e.g. e13's top-up) is kept | Identical to its baseline on every metric in all 6 comparisons (no model input changes, so it can't shift classifications); clears all 26 inconsistent cases seen | **Adopt** (small, safe) |

Lesson, the third time it has shown up (F6, F13, F14): the classifier and the re-check share one prompt, so editing it can make both models wrong in the same way and silently remove the safety net. Prefer code rules or separate calls over prompt edits, and always test a prompt edit with replicates.

### Round 3: what was tried

| Fix | Idea | Dev result (dev_95, 95 tickets) | Verdict |
|---|---|---|---|
| **F3b** | Same-team disagreement: use the re-check's answer | Subcategory used 90 → 92, escalated 13 → 11 | Subset of F3c |
| **F3c** | Any non-fraud disagreement: use the re-check's answer, flagged (fraud never overridden) | **90 → 95/95**, draft given 90 → 95/95, escalated 13 → 8, priority 86 → 90, 0 wrong types reaching a draft, +5 calls | **Adopt** (replaces F3) |
| **F9** | Re-check look-alike answers under 0.90 | +6 calls, no gain alone; with F3c, 95 → 95 and one fewer draft | Drop |
| **F10** | Classifier names a runner-up | +16 calls, 90 → 89, wrong types reach drafts (2 runs) | Drop |
| **F13** | Sharper look-alike hints in the classifier prompt | Alone 90 → 92/93, but with F3c **−4** (it makes the first model surer, so fewer tickets reach the re-check F3c relies on) | Drop |
| **F11** | Ask for shop / agent / bill details only if the ticket doesn't give them | Pooled 3×28 drafts: asks right 82% → 87%, bad 2 → 2 | **Adopt** |
| **F12 v1** | No promising to send a specific answer, date or result | Bad drafts **2 → 13/84**: its "check and follow up" wording made the drafter's follow-up phrase come out broken ("wياك", "يتابعونويا") | Replaced by v2 |
| **F12 v2** | Same rule without that wording | Bad drafts 2 → **0/84**, no promise 98% → 100%; with F11: asks right 94%, grounded 100% | **Adopt** |
| **F6 (re-test)** | The round-2 fee field in the classifier prompt | On the larger dev set it **costs classification**: 2 and 1 wrong types reach drafts; F3c+F6 92 vs F3c 95 | Replaced by F6b |
| **F6b** | Separate small fee call only for fee tickets; classifier prompt untouched | Classification identical to baseline; fee 4/4 with F3c; about +1 small call per fee ticket | **Adopt** (replaces F6) |

**Interactions are real in round 3** (unlike rounds 1–2): F3c × F13 −4 and F3c × F6 −3 on subcategory used, both through the same mechanism (a prompt change makes the first model surer, so fewer tickets reach the re-check). F11 × F12 is positive: asks right 87% and 89% alone, 94% together. All pair pages are in `dev_95/`.

**Method additions in round 3:** draft replicates with the classification held fixed (`LLM_CACHE_SALT=drafter=d1`), pooled scoring (`experiment.py pool`), a classifier-noise replicate per key config (`classifier=c1`; about ±2 tickets on 95), "subcategory used" and "wrong type, not escalated" metrics, and the sealed hold-out set.

**Label correction:** s18's gold label was changed from `reversal_request` to `wrong_recipient`, because the classifier prompt's own rule 5 says wanting the money back after a wrong transfer stays with the main subcategory. Every config was re-scored; no model output changed.

## Rounds 1–2

## Verdict per fix

| Fix | What it did on the tickets | Side effects | Recommendation |
|---|---|---|---|
| **F7** casual "هسه" | Priority 24/30 → **29/30**. All five casual-"هسه" tickets fixed; real urgency (f06, "ضروري") still P1. | None. Rule-only, so this result has no noise. | **Adopt.** |
| **F3** same-team re-check | On fixes_30, no same-team disagreement happened, so no effect. On 65 more tickets: **2 of 2** same-team disagreements (s18 reversal vs wrong recipient, m02 forgot PIN vs login) went from "escalated, no draft" to "flagged with a draft" scoring 4/5. | None seen; cross-team and fraud still escalate. Small sample (2 cases). | ~~Adopt~~ **Superseded by F3c** (round 3). |
| **F2** draft checks (v2) | v1 had a false alarm (f12, "we'll get back to you" read as a refund promise). v2 fixed that and two other false alarms found in a wider check. On all **161** distinct drafts so far, v2 flags **2**, both real stray Latin letters ("hلا", "wياهم"); **0** false alarms. | Catches nothing meaning-level: the judge's bad drafts (a promised branch address, an implied refund date) pass the rules. | **Adopt.** Cheap, no false alarms; catches about 1% of drafts. |
| **F6** fee field | Fee **0/4 → 4/4**, and again 4/4 in an uncached replicate. Classification: +f14 −f15 in round 1, not repeated in the replicate, so **no effect beyond noise**. | The classifier prompt changed, so it needs re-checking on the API dev set. | ~~Adopt~~ **Superseded by F6b**: on the larger round-3 dev set the prompt change cost classification. |
| **F8** unclear template | Saves the drafter call on unclear tickets (4/30 here; 63 → 59 calls). Draft scores on those 4 tickets: model drafts 5 5 3 4; template v1 4 5 2 4; v2 4 4 3 4. | Slightly lower quality: a fixed text can't answer an off-topic question (f09) and can't fit every opening (greeting vs "I have a problem"). | **Your call.** It saves about 6% of calls at a small quality cost. If you want it, v2 is the safer text. |
| **F5** policy facts (isolated) | Mean score 4.50 → 4.61, inside the noise floor (4.50–4.65 between identical baseline runs). Drafts now state response times and support hours. | One draft had a stray Latin letter (F2 v2 catches it). The judge rewards safety and editing effort, not added information, so the benefit is under-measured. | **Fill `config/policy.yaml` with your real values,** then re-test on the API. The values used here are placeholders (`config/experiments/policy_filled.yaml`). |

**Follow-up for F3 (tested in round 3 as F3b/F3c; F3c adopted):** under F3 the draft and priority follow the *first* model's answer. In m02 that was wrong (login/OTP, P2), while the re-check had it right (forgot PIN, P3); see `screenshots/f3-m02-same-team-flagged.png`. Across all baseline runs, the re-check model was right in 7 of the 8 disagreements. A variant F3b that drafts from the re-check's answer is worth testing next.

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

**Tested in round 3:** neither was worth it. F10 added 16 calls and made accuracy slightly worse. F9 added calls without beating F3c, which uses the re-check that already runs on about 21% of tickets. For confidence, the best cheap lever turned out to be acting on the existing re-check's answer (F3c), not adding more checks. Calibration on the API dev set is still the next step before any threshold change.

## Monitoring additions (after the experiments)

These don't change what the agent sees; they help us watch the pipeline.

- **Cost logging:** every model step records its tokens (and, on cli, the cost Claude Code reports) in the run events, marked when the reply came from the cache; `run_batch.py` prints and stores run totals in `meta.usage`. The fresh all-five run used 59 calls, about 174k input and 12k output tokens, reported $0.06 for 30 tickets (about 6,200 tokens and $0.002 per ticket, including the cli's own context).
- **Viewer:** experiment runs appear under their own group in the source list; the queue can be sorted by priority (P1 and escalated first) or grouped by team; the overview shows tokens and cost per ticket; each model step shows its tokens. Screenshots are in `screenshots/`.
