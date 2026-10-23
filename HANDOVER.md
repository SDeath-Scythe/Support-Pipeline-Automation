# Handover: testing and improving the support pipeline

**Period:** 20–23 Oct 2026 · **Branch:** `claude/eager-tesla-x1dcxj` (nothing on `main`) · **Commits:** all after `cb5b89c` · **Tests:** 25 → 51, all passing

This document hands over everything done in one working session with the Claude Code assistant: what was tested, what was learned, what was built, why each choice was made, and what to do next. It covers the whole session, from the first smoke test to the final hold-out check. The detailed numbers live in [`docs/experiments/LOG.md`](docs/experiments/LOG.md) and the per-config pages; this file is the guided tour.

---

## TL;DR

> **The pipeline works.** On the first smoke test it classified 20/20 new synthetic tickets correctly and drafted sensible Iraqi-dialect replies. The work since then made it measurably better, and built the tooling to prove each change rather than guess.

- **Recommended changes** (all behind flags, **off by default**, so `main` behaviour is unchanged until you turn them on):

  | Flag | Code | What it does |
  |---|---|---|
  | `draft_check` | F2 | Rule checks on every draft (stray Latin letters, promises, PIN/OTP requests, invented numbers); a failing draft is flagged with the reason |
  | `recheck_cross_team` | F3c | When the two models disagree, use the **re-check model's** answer and flag it, instead of escalating (never for fraud) |
  | `fee_followup` | F6b | A small extra call extracts the disputed fee, only for fee tickets |
  | `no_now_urgency` | F7 | "هسه" (now) no longer raises priority |
  | `ask_if_missing` | F11 | The draft only asks for a shop / agent / bill detail if the ticket doesn't already give it |
  | `no_specific_followup` | F12 | The draft must not promise to send a specific answer, date or result |
  | `fraud_secondary_cleanup` | F14b | A fraud ticket's "second issue" is cleared when it's only a consequence of the fraud (added in the follow-up, see 6) |

  Turn them all on with:
  ```bash
  PIPELINE_FIXES=draft_check,recheck_cross_team,fee_followup,\
  no_now_urgency,ask_if_missing,no_specific_followup,fraud_secondary_cleanup \
    python app/server.py
  ```

- **Confirmed on 30 sealed tickets** that no fix had seen (3 runs per arm):

  | | Baseline | Recommended |
  |---|---|---|
  | Subcategory used correct | 28/30 | **29/30** |
  | Draft given when it should be | 28–29/30 | **29–30/30** |
  | Priority correct | 28/30 | **30/30** |
  | Disputed fee correct | 0/2 | **2/2** |
  | Mean draft score (1–5, model judge) | 4.44 | **4.63** |
  | Drafts asking for the right info | 78% | **89%** |
  | Model calls (30 tickets) | 63 | 68 |

- **Most important next step:** measure on the API backend and have a person hand-check about 30 labels and 30 drafts. Every number above comes from the development (`cli`) backend, with tickets and labels written by the assistant and drafts graded by a model. See [Recommendations](#10-recommendations-for-the-future).

---

## Contents

1. [Where we started](#1-where-we-started)
2. [Timeline at a glance](#2-timeline-at-a-glance)
3. [Phase 1: smoke test](#3-phase-1-smoke-test)
4. [Phase 2: from observations to candidate fixes](#4-phase-2-from-observations-to-candidate-fixes)
5. [Phase 3: how fixes were tested (the method)](#5-phase-3-how-fixes-were-tested-the-method)
6. [Phase 4: every fix, from idea to verdict](#6-phase-4-every-fix-from-idea-to-verdict)
7. [Phase 5: monitoring additions](#7-phase-5-monitoring-additions)
8. [Lessons learned](#8-lessons-learned)
9. [What changed in the repo](#9-what-changed-in-the-repo)
10. [Recommendations for the future](#10-recommendations-for-the-future)
11. [Caveats](#11-caveats)
12. [How to reproduce anything here](#12-how-to-reproduce-anything-here)

---

## 1. Where we started

The repo (as of `cb5b89c`) had a working pipeline: clean → classify + extract (Haiku) → confidence gate → re-check (Sonnet) → route + priority → draft (Sonnet) → human review. It also had a local viewer, 25 unit tests, two probe sets (`edge_cases`, `mixed_30`) and a `cli` / `api` backend switch.

The session's brief, in the order it was given:

1. *"Go through the repo, test it with multiple synthetic tickets, follow its guidance, and show screenshots of the viewer."*
2. *"What do you recommend to improve the workflow?"*
3. *"Before doing any of these, find which really affect us and whether good or bad: test each fix with and without it on 20–30 tickets, then pairs, then all together. Document everything and commit each step. Monitoring-only items come later."*
4. *"Try the re-check follow-up, and any other ideas to get better results."*
5. *"What do you think still needs improvement?"*

Ground rules followed throughout: work only on the feature branch, commit as the author (no assistant co-author line), and document what was done, where and why.

## 2. Timeline at a glance

```mermaid
flowchart LR
    A[Smoke test<br/>20 new tickets<br/>+ mixed_30] --> B[10 recommendations<br/>author picks which<br/>to test]
    B --> C[Experiment harness<br/>flags, cache, judge,<br/>30-ticket test set]
    C --> D[Round 1<br/>5 fixes: singles,<br/>10 pairs, all five]
    D --> E[Round 2<br/>v2 of F2 and F8,<br/>replicates, F3 on<br/>65 more tickets]
    E --> F[Monitoring<br/>tokens and cost,<br/>viewer upgrades]
    F --> G[Round 3<br/>F3b/F3c, F9-F13, F6b<br/>95-ticket dev set,<br/>sealed hold-out]
    G --> H[Recommendation<br/>confirmed on<br/>hold-out]
```

| Phase | Commits | Outcome |
|---|---|---|
| Smoke test | `89828ff` | Pipeline works end to end; 5 weak spots found |
| Harness and test set | `e83f638`, `6085e77` | Every fix can be measured with and without, on fixed tickets |
| Fixes F2, F3, F5–F8 | `e961ffe` … `877f223` | Each behind its own flag |
| Round 1 | `994ebda` … `52fc5aa` | F7 is a clear win; F2 had a false alarm; F3 never triggered |
| Round 2 | `c51d9c4` … `419c050` | F2 v2 and F8 v2; F6 classification gain was noise; F3 exercised |
| Monitoring | `1bda052`, `c7d8f0a`, `f68221d` | Token/cost logging; viewer shows experiment runs and sorts the queue |
| Round 3 | `9806f5f` … `3776f13` | F3c and F6b replace F3 and F6; F11 and F12 v2 added; hold-out confirms |

---

## 3. Phase 1: smoke test

**What was done (`89828ff`).** Installed the requirements, ran the test suite (25 passed), confirmed the `cli` backend works in the container, then followed `data/README.md` to write **20 new labelled synthetic tickets** (`data/probes/synthetic_20.jsonl`). They cover the three dialects, the six writing styles and the listed edge cases (missing fields, fraud, prompt injection, negation, off-topic, two issues). Both `synthetic_20` and `mixed_30` were run through `scripts/run_batch.py`, and the viewer was screenshotted with headless Chromium.

**Why `cli`:** the README says to use `cli` for smoke tests of 5–20 tickets, and no API key was available.

**Result:** synthetic_20 got the subcategory right on 20/20, outcome 19/20 and priority 20/20. mixed_30 got 29/30 on each.

| Run overview | Prompt injection ignored (s15) |
|---|---|
| ![Smoke-test overview](docs/test-runs/2026-10-20-smoke/screenshots/overview.png) | ![s15](docs/test-runs/2026-10-20-smoke/screenshots/ticket-s15.png) |

| Missing reference and amount: capped, flagged (s13) | Fraud: escalated, no draft (s14) |
|---|---|
| ![s13](docs/test-runs/2026-10-20-smoke/screenshots/ticket-s13.png) | ![s14](docs/test-runs/2026-10-20-smoke/screenshots/ticket-s14.png) |

| Re-check disagreed: escalated (s18) | A ticket pasted and run live |
|---|---|
| ![s18](docs/test-runs/2026-10-20-smoke/screenshots/ticket-s18.png) | ![live](docs/test-runs/2026-10-20-smoke/screenshots/live-done.png) |

**What the smoke test revealed**, which drove everything after it:

| Seen in | Observation |
|---|---|
| s15 | Draft started with a stray Latin letter: `hلا هلا بيك` |
| s17 | Off-topic ticket ("dollar rate?"); the draft promised the team would get back with the rate |
| s18 | The two models disagreed (reversal vs wrong recipient) and the ticket was escalated, although both answers go to the same team |
| s07 | "Took a 10,000 fee on a 100,000 withdrawal": the 100,000 was extracted, not the disputed fee |
| m23 | "Arrived short" read as "not received" instead of a fee question |
| all | `config/policy.yaml` is all `null`, so drafts can't state any fact |

Full record: [`docs/test-runs/2026-10-20-smoke/README.md`](docs/test-runs/2026-10-20-smoke/README.md).

---

## 4. Phase 2: from observations to candidate fixes

Ten recommendations came out of the smoke test. You decided what to do with each:

| # | Recommendation | Your decision | What happened |
|---|---|---|---|
| 1 | Record what agents do with drafts | Not now: the viewer is only for you | Not built |
| 2 | Rule checks on drafts | Try it | **F2** → adopted (v2) |
| 3 | Don't escalate a same-team re-check disagreement | Try it | **F3** → replaced by **F3c** |
| 4 | Improve confidence without 3 calls per ticket | Recommend something | Tested as F9, F10, F13; the winner was F3c |
| 5 | Fill `policy.yaml` | Test in isolation, before/after | **F5**: tested with placeholder values |
| 6 | Extract the disputed fee | Do it | **F6** → replaced by **F6b** |
| 7 | Urgency words | Check that "now" doesn't raise priority | **F7** → adopted |
| 8 | Fixed reply for unclear tickets | Good idea, hint at the info needed | **F8**: your call (trade-off) |
| 9 | Evaluation gaps | Do it (monitoring: later) | Judge, field accuracy, cost logging |
| 10 | Sort the queue | Do it (monitoring: later) | Viewer sort by priority or team |

---

## 5. Phase 3: how fixes were tested (the method)

The rule was: **no fix is adopted on a hunch.** Each one is run with and without, on the same tickets, alone, then in pairs, then all together. Every step is committed. Here is how that was made reliable, and why each piece exists.

### Where each fix acts

```mermaid
flowchart LR
    T[Ticket] --> C[Clean<br/>rules]
    C --> K["Classify + extract<br/>Haiku<br/>(F6, F10, F13)"]
    K --> FEE["Fee call<br/>(F6b)"]
    FEE --> G{"Confidence gate<br/>rules<br/>(F9, F10)"}
    G -->|pass| R["Route + priority<br/>rules<br/>(F7)"]
    G -->|re-check| RC["Re-check<br/>Sonnet<br/>(F3, F3b, F3c)"]
    RC --> R
    G -->|escalate| E[Escalated<br/>no draft]
    R --> D["Draft<br/>Sonnet<br/>(F5, F8, F11, F12)"]
    D --> DC["Draft checks<br/>(F2)"]
    DC --> H[Human review]
```

### The pieces

| Piece | Where | Why it exists |
|---|---|---|
| **Feature flags** | `src/pipeline/fixes.py`, env `PIPELINE_FIXES` | The same code runs "with" and "without". All flags are off by default, so nothing changes for anyone who doesn't opt in. |
| **Response cache** | `llm.py`, env `LLM_CACHE_DIR` | An identical model call (same model, system and user prompt) returns the stored reply. Two configs then differ **only where the fix changes what a model is sent**, not because the model answered differently a second time. It also makes pair runs almost free. |
| **Per-role salt** | env `LLM_CACHE_SALT=drafter=d1` | Fresh replies for one role while the others stay fixed, e.g. re-draft with the same classifications. Added in round 3 because draft scores swing about ±0.1 between identical runs. |
| **Noise floor** | uncached and salted replicates | Measures how much changes by pure chance, so a "gain" smaller than that isn't believed. |
| **Draft judge** | `scripts/prompts/judge_draft.md` (the `evaluator` role) | Rates each draft: understood, grounded, no promise, asks right, safe, tone, clean, and a 1–5 "editing effort" score. Its own consistency was measured: graded twice, the same verdict 28/28 and scores within 1 point 28/28. |
| **Scorer and reports** | `scripts/experiment.py` | Scores against gold labels, compares with baseline, lists changed tickets, and computes **interaction** (does a pair score differently from the sum of its parts?). Also builds summary tables and pools replicates. |
| **Test sets** | `data/probes/` | `fixes_30` (rounds 1–2), `dev_95` (round 3 dev = four sets joined), and **`holdout_30`**, written before any round-3 result and run only once at the end. None of the tickets that inspired a fix are used to judge it. |

### Metrics that matter for the agent

- **Subcategory used correct:** the answer the pipeline acted on (which, with F3c, can be the re-check's).
- **Wrong type, not escalated:** a wrong type that still reaches the agent as a draft. This is the riskiest error.
- **Draft given iff it should be:** a draft for every ticket that shouldn't be escalated, none for those that should.
- **Bad drafts marked ready:** judge-rated bad drafts that the pipeline marked as ready to approve.
- Priority, fee and amount accuracy, escalations, model calls.

---

## 6. Phase 4: every fix, from idea to verdict

Each entry gives the observation that started it, the reasoning, how it was built, and what the data said. The numbers are the key ones; the full tables are in [`docs/experiments/LOG.md`](docs/experiments/LOG.md).

### ✅ F7: "هسه" no longer raises priority · adopt

- **Observation:** `URGENT_WORDS` contains "هسه" (now), which is everyday wording ("هسه شلون ارجعه؟"), so ordinary tickets were bumped a level.
- **Implementation:** `route.py`: `urgent_words()` leaves out `NOW_WORDS` when the flag is on. Real urgency ("ضروري", "عاجل") still counts.
- **Result:** priority 24/30 → **29/30** on fixes_30; all five casual-"هسه" tickets fixed; f06 ("ضروري") still P1. It's rule-only, so there's no noise. Hold-out: priority 30/30.

### ✅ F2: rule checks on every draft · adopt (v2)

- **Observation:** s15's `hلا`; drafts can slip on promises or numbers the prompt forbids.
- **Implementation:** `src/pipeline/draft_check.py` checks for a Latin letter glued to Arabic, promises of an outcome or a time not in the known facts, a request for a PIN/OTP (a "لا تشارك" warning is allowed), and numbers not in the ticket, fields or facts. A failure flags the ticket with an Arabic note.
- **Round 1:** it flagged f12 for a "promise", but "وراح نرجع نخبرك" means *we'll get back to you*. That was a false alarm, and it caught 0 of the judge's bad drafts.
- **v2 (`c51d9c4`):** a "return" verb only counts with money near it; times are compared after digit normalisation (`24` = `٢٤`); "الف وحدة" counts as 1,000. To avoid tuning on the test set, it was checked against **all 161 drafts produced so far**: 2 flags, both real (`hلا`, `wياهم`), and **0 false alarms**.
- **Limit:** rules can't see meaning-level problems such as a promised branch address. That's what F12 is for.

### ❌→✅ F3 → F3b → **F3c**: trust the re-check model · adopt F3c

- **Observation (s18):** the models disagreed inside one team and the ticket was escalated with no draft.
- **F3 (round 1):** a same-team disagreement gets a flagged draft. On fixes_30 it **never triggered**, so it was run on 65 more tickets: 2/2 same-team disagreements became flagged drafts scoring 4/5.
- **Follow-up spotted in the viewer:** under F3, the draft followed the *first* model, which was wrong in m02.

  ![m02: F3 flagged a same-team disagreement](docs/experiments/screenshots/f3-m02-same-team-flagged.png)

- **Evidence that changed the design:** across every disagreement seen, the **re-check model matched gold on 5 of 6 distinct tickets**, and 4 of 6 disagreements were *cross-team*, which F3 still escalated.
- **F3b:** same-team only, use the re-check's answer. **F3c:** any non-fraud disagreement uses the re-check's answer: the gate rules are re-run for it, it is routed to that answer's team, the first answer is kept as `recheck_alternative`, and the ticket is flagged. Fraud is never overridden either way.
- **Result (dev_95):** subcategory used **90 → 95/95**, draft given iff it should be 90 → 95/95, escalated 13 → 8, priority 86 → 90, **0** wrong types reaching a draft, only +5 calls. F3b was a subset of this gain.

### ❌→✅ F6 → **F6b**: the disputed fee · adopt F6b

- **Observation (s07):** the transaction amount was extracted instead of the disputed fee.
- **F6 (round 1):** an optional `fee_iqd` field in the classifier prompt. Fee 0/4 → 4/4, confirmed in a replicate, and adopted in round 2.
- **Round 3 found a hidden cost:** on the larger dev set, the extra field **shifted some classifications** (an agent top-up read as cash-in at exactly 0.75, which passes the gate unchecked; "raise my limit" read as a fee question). Wrong types reached drafts in both runs, F3c+F6 scored 92 vs F3c's 95, and on the hold-out the round-2 set scored *below* baseline (27/30).
- **F6b:** leave the classifier prompt untouched; once a ticket is classified as a fee subcategory, one **small separate call** (`prompts/fee_system.md`) returns the fee.
- **Result:** classification identical to baseline, fee 4/4 (2/2 on the hold-out), about one cheap call per fee ticket.

  ![f17: the disputed fee (7,000) shown separately; tokens per step](docs/experiments/screenshots/f17-fee-and-tokens.png)

  *(Screenshot from the F6 run; F6b shows the fee the same way.)*

### ✅ F11: ask only for what's missing · adopt

- **Observation:** drafts asked for the shop name when the ticket said "Amazon". The classifier can't extract shop, agent location or bill type, so they always looked "missing".
- **Implementation:** `draft.py` splits the asks. Fields the pipeline can check stay "ask for"; the rest become "ask only if the ticket doesn't already give them".
- **Result (pooled, 3 × 28 drafts):** asks right 82% → 87%.

### ❌→✅ F12: no promised specifics · adopt v2

- **Observation:** the judge's worst drafts promised a branch address and a refund date.
- **v1:** one rule in the drafter prompt ending "the team will check **and follow up**". Bad drafts jumped **2 → 13/84**, because the drafter's follow-up phrase kept coming out broken (`wياك`, `يتابعونويا`).
- **v2 (`cb634ec`):** the same rule, ending "it is enough to say the relevant team will check it". Bad drafts went to **0/84**, no promise 100%.
- **With F11:** asks right **94%**, grounded 100%. They help each other.

### ⚖️ F8: fixed reply for unclear tickets · your call

- **Idea:** a template instead of a drafter call for greetings and vague tickets, hinting at the useful details. The text lives in `config/templates.yaml`.
- **Result:** saves about 6% of calls (63 → 59). On the 4 unclear tickets, scores were model 5 5 3 4, template v1 4 5 2 4, v2 4 4 3 4. A fixed text can't answer an off-topic question or fit every opening. It's cheaper but slightly worse, so it's a business choice.

### ⏸ F5: filled-in policy facts · fill in the real values

- Tested in isolation as you asked, with **placeholder** values in `config/experiments/policy_filled.yaml`. The real `policy.yaml` is untouched.
- Mean score 4.50 → 4.61, within noise. Drafts now state response times and hours. The judge rewards safety, not information, so the benefit is under-measured. Fill in the real values, then re-test.

### ❌→✅ F14 → **F14b**: the fraud / second-issue rule · adopt F14b

- **Observation (raised by the author):** the classifier prompt says "pick exactly one category and one subcategory", but rule 1 says, for fraud, "put the other issue in `secondary_subcategory`". Rule 1 also contradicts rule 5 ("being locked out after a scam … stays with the main subcategory"). In saved runs the model split on it: e02 ("gave my code, now locked out") got `login_otp` as the second issue on some runs and none on others. Across 522 saved fraud classifications, 26 (5%) were like this.
- **F14:** reword those two sentences in the prompt. Tested on existing tickets only, with replicates. The second-issue field improved on one ticket, but **3 wrong ticket types reached a draft in every run** (0 before), and the recommended set fell 95 → 92/95. The re-check model shares the prompt, so both models started making the same mistakes and F3c's safety net disappeared. **Not adopted.**
- **F14b:** enforce the same rule in code after each classification. A fraud ticket's second issue is cleared when it is a consequence (an account-access or fraud subcategory); a separate request is kept. No model input changes. Result: **identical on every metric in all 6 comparisons**, and it clears all 26 inconsistent cases. **Adopt.**

### ❌ Tried and dropped

| Fix | Idea | Why dropped |
|---|---|---|
| F9 | Re-check answers in look-alike pairs under 0.90 | +6 calls, no gain on top of F3c |
| F10 | Classifier names a runner-up | +16 calls, slightly worse, wrong types reached drafts |
| F13 | Sharper look-alike hints in the classifier prompt | Helps alone (90 → 92), but **−4 with F3c**: a surer first model sends fewer tickets to the re-check F3c relies on |
| F14 | Reworded fraud / second-issue rule in the classifier prompt | Both models start making the same mistakes; 3 wrong types reach drafts in every run. Replaced by F14b |

### Combinations

- **Rounds 1–2:** every pair and the all-five run scored exactly the sum of their parts, because those fixes act on different stages.
- **Round 3:** real interactions appeared. F3c × F13 −4 and F3c × F6 −3 (both through fewer re-checks), and F11 × F12 positive. This is why the recommended set was confirmed **as a whole** on the hold-out, not assembled from single results.

![All five round-2 fixes, fresh run: overview with tokens and cost](docs/experiments/screenshots/all5-overview.png)

---

## 7. Phase 5: monitoring additions

Built after the experiments, as you asked. These help *us* watch the pipeline and change nothing an agent sees.

- **Token and cost logging** (`1bda052`): every model step records its tokens (and, on `cli`, the cost Claude Code reports) in the run events, marked when the reply came from the cache. `run_batch.py` prints and stores totals in `meta.usage`. A fresh 30-ticket run used about 6,200 tokens and $0.002 per ticket (cli-reported, including the cli's own context).
- **Viewer** (`c7d8f0a`): experiment runs are listed in their own group; the queue can be sorted by priority (P1 and escalated first) or grouped by team; the overview shows tokens and cost per ticket; each model step shows its tokens; the disputed fee is shown with the fields.

![Queue sorted by priority; tokens and cost per ticket in the overview](docs/experiments/screenshots/queue-by-priority.png)

---

## 8. Lessons learned

1. **Measure noise before believing a gain.** Identical runs moved classification by about 2/95 tickets and the mean draft score by about 0.1. Several early "gains" (F6 on f14, F5's score) were inside that.
2. **Prompt changes have side effects elsewhere.** Adding one field (F6), sharper hints (F13) or rewording one rule (F14) shifted unrelated classifications. Because the classifier and the re-check share the prompt, an edit can make *both* models wrong in the same way and silently remove the safety net. Prefer a code rule (F14b) or a separate small call (F6b) over editing the main prompt, and always test prompt edits with replicates.
3. **The wording of an instruction can break the output.** F12 v1's "follow up" produced malformed Arabic; the same idea, worded differently, was the best draft fix.
4. **The second opinion is the confidence signal.** The model's own confidence is already well ordered (95/95 right at ≥0.90, 40/42 at 0.75–0.90, 12/18 below). The cheap win was *acting on* the existing re-check (F3c), not adding more checks (F9, F10).
5. **Keep a test set you never look at.** The hold-out caught that the round-2 set was worse than baseline, which tuning on `fixes_30` alone had hidden.
6. **Audit your own labels.** s18 was labelled `reversal_request`, but the classifier prompt's own rule 5 says it is `wrong_recipient`. It was corrected (`0f580ca`), documented, and every config re-scored. The judge also had a bug: it didn't know the drafter is told the team name, so it marked team names as invented. That was fixed (`30a1722`) and everything re-scored.

---

## 9. What changed in the repo

All on `claude/eager-tesla-x1dcxj`. With no flags set, the pipeline behaves exactly as before; the classifier and drafter prompts are byte-identical, and this was checked.

| Area | Files | Change |
|---|---|---|
| Fix flags | `src/pipeline/fixes.py` | 16 flags, read from `PIPELINE_FIXES` |
| Classifier | `classify.py`, `prompts/fee_system.md`, `schemas.py` | F6 field, F10 runner-up, F13 hints (all flag-gated); F6b fee prompt and parser; optional `fee_iqd` and `runner_up` fields |
| Gate | `gate.py` | F9 look-alike and F10 runner-up re-check triggers |
| Run | `run.py` | F3/F3b/F3c re-check handling, F6b fee call, F8 template, F2 checks, Arabic flag notes |
| Route | `route.py` | F7 `urgent_words()` |
| Draft | `draft.py`, `draft_check.py` | F5 policy source, F11 split asks, F12 rule; F2 checks module |
| Model calls | `llm.py` | Response cache with a lock per key, per-role salt, `last_usage()` |
| Config | `config/templates.yaml`, `config/experiments/*.yaml`, `taxonomy.yaml` (look-alike pairs), `thresholds.yaml` (`confusable_below`) | Template text, placeholder policy, F13 hints. The real `policy.yaml` is untouched. |
| Scripts | `scripts/experiment.py`, `scripts/prompts/judge_draft.md`, `run_batch.py` | Experiment runner, scorer, judge, pooling; `--out`, fixes and usage in run meta |
| Viewer | `app/server.py`, `app/static/index.html` | Experiment runs, safe run paths, queue sort, tokens and cost, fee field |
| Data | `data/probes/synthetic_20`, `fixes_30`, `dev_95`, `holdout_30` (+ `data/README.md` table) | 20 + 30 + 30 new labelled tickets; dev_95 joins existing sets |
| Tests | `tests/test_pipeline.py` | 25 → 51 tests: every flag on and off, cache and salt, draft checks, fee parsing |
| Docs | `docs/test-runs/…`, `docs/experiments/…`, this file | Smoke-test record, method, log, per-config pages, screenshots |

Run outputs (`runs/`) and the response cache stay git-ignored, as `runs/` already was.

---

## 10. Recommendations for the future

In priority order. Items 1–3 matter more than any new idea.

### 1. Validate the measurements *(highest priority)*
Every number came from the `cli` backend, which the README itself says not to use for numbers. The tickets and gold labels were written by a Claude model and scored against Claude models, and the judge is a Claude model grading Claude drafts. These could share blind spots.
**How:** with an API key, re-run `baseline` vs the recommended set (`scripts/experiment.py`, `--backend api`). Have you or a native Iraqi speaker hand-check about 30 labels and score about 30 drafts, then compare those scores with the judge's: keep the judge if they agree, fix the rubric if not. This is the "80 hand-checked tickets" step from `data/README.md`.

### 2. Grow and ground the data
About 155 tickets exist, none checked for dialect realism by a native speaker, and the 400-ticket generator isn't built. `holdout_30` is now **spent** (h19 was inspected).
**How:** build the Opus generator (subcategory × dialect × style); add a few real, anonymised phrasings from support staff; write a **fresh hold-out for every round**.

### 3. Make the recommendation the real code, and delete the rest
Sixteen flags are off by default, so the shipped behaviour is still the baseline. The dead variants (F3, F3b, F6, F9, F10, F13, F14) make `run.py` and the gate harder to read.
**How:** make F2, F3c, F6b, F7, F11, F12 v2 and F14b the normal code path; delete the dropped flags (including F14) and their code (they live on in `LOG.md` and git history); keep F8 as a config option and F5 waiting on real values. Keep the experiment harness for future ideas.

### 4. Fix the remaining classification confusions
"Raise my limit" keeps being read as a fee/limit question (s05, m08, h19). An agent top-up drifts to cash-in (f15). A confidence of exactly 0.75 passes the gate without a re-check.
**How:** test a sharper `limit_upgrade` hint, then a `pass_above` slightly above 0.75, each with and without, and confirm on a *new* hold-out. With F3c, the real lever is **when** the re-check runs; set that threshold from API calibration.

### 5. Fill in `config/policy.yaml`
This is a company decision. Real response times and hours make drafts genuinely useful (F5 showed no harm). Re-test before/after, like F5.

### 6. Prepare for real data
The response cache and run files store full ticket text; `mask_for_logs` isn't applied to them. Prompt injection was tested on only 3 tickets.
**How:** mask stored text, keep the cache to synthetic experiments only, and add about 10 adversarial tickets (Arabizi injection, fake "system" messages, requests for other customers' data) to the regression tests.

### 7. Decide whether the fixing team should get a written handoff
Today **every draft is a reply to the customer**; the drafter's prompt says so. The team that fixes the issue gets only structured data: the team, the priority, the extracted fields and a fixed one-line note per flag. **Escalated tickets (all fraud included) get no text at all.** A second, internal note (for example "Customer sent 40,000 IQD to the wrong number, ref 61200984; asks how long the return takes; recipient number still missing") would help most on exactly those escalated tickets.
**How:** a separate drafter call with its own prompt, written for the team rather than the customer. Test it with the same with/without method, with the judge rating usefulness to the team.

### 8. Once agents use it: measure edits, not judge scores
How often agents approve, edit or take over (recommendation #1, deferred) will replace the model judge as the true quality metric.

**What to stop doing:** adding more prompt or rule tweaks on the `cli` backend. Round 3 showed fixes interact through prompt changes; the next real gains come from items 1–3.

---

## 11. Caveats

- **Backend:** all results are from `cli` (Claude Code headless). Use them to compare configs, not to set thresholds or report MVP numbers.
- **Who wrote the data:** synthetic tickets and gold labels were written by the assistant. One label (s18) was corrected mid-way, with the reason documented.
- **Judge:** a model judge, consistent with itself, but not yet checked against a person.
- **Iteration on observations:** F2 v2, F8 v2 and F12 v2 were improved after seeing results. F2 v2 was validated on all 161 drafts, and the final set on the sealed hold-out.
- **Small samples:** 30-ticket sets; differences of 1–2 tickets are within noise unless replicated (see the replicate rows in each summary).

---

## 12. How to reproduce anything here

```bash
pip install -r requirements.txt
pytest                                             # 51 tests

# The viewer (shows saved runs and experiment runs)
python app/server.py                               # http://localhost:8000

# One config on a set (runs go to runs/exp/<set>/, git-ignored)
python scripts/experiment.py run baseline --set data/probes/dev_95.jsonl
python scripts/experiment.py run F2+F3c+F6b+F7+F11+F12 --set data/probes/dev_95.jsonl
python scripts/experiment.py report F2+F3c+F6b+F7+F11+F12 --set data/probes/dev_95.jsonl

# Noise checks: fresh classifier, or fresh drafts with classification fixed
python scripts/experiment.py run baseline --salt classifier=c1 --label baseline-c1
python scripts/experiment.py run baseline --salt drafter=d1 --label baseline-d1
python scripts/experiment.py pool --a baseline,baseline-d1 --b F11,F11-d1 --name F11

# On the API (for real numbers)
python scripts/experiment.py run baseline --backend api
```

**Where to read next:**
- [`docs/experiments/LOG.md`](docs/experiments/LOG.md): the full results log, newest first
- [`docs/experiments/README.md`](docs/experiments/README.md): the method and the flag table
- [`docs/experiments/holdout_30/summary.md`](docs/experiments/holdout_30/summary.md): the final check
- [`docs/experiments/dev_95/summary.md`](docs/experiments/dev_95/summary.md): every round-3 config
- [`docs/experiments/fixes_30/summary.md`](docs/experiments/fixes_30/summary.md): rounds 1–2
- [`docs/test-runs/2026-10-20-smoke/README.md`](docs/test-runs/2026-10-20-smoke/README.md): the first smoke test
- `git log cb5b89c..HEAD`: every step with its reason in the commit message
