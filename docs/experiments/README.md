# Fix experiments

Each candidate fix is tested **with and without** it on the same tickets before it is adopted, first one at a time, then in pairs, then all together. This page explains the method; the results log is in [LOG.md](LOG.md), and per-config pages are in `fixes_30/`.

## The fixes under test

The numbers follow the recommendation list from the 20 Oct smoke test ([../test-runs/2026-10-20-smoke/README.md](../test-runs/2026-10-20-smoke/README.md)).

| Code | Flag | What it changes | Stage |
|---|---|---|---|
| F2 | `draft_check` | Rule checks on every draft (stray Latin letters, promises, asking for a PIN/OTP, numbers that are not in the ticket or facts). A failing draft is **flagged** with the reason. | after draft |
| F3 | `recheck_same_team` | When the re-check disagrees but both answers go to the **same team** (and neither is fraud), flag the ticket with a draft instead of escalating it. | gate |
| F5 | `policy_facts` | The drafter gets filled-in facts (response times, support hours). **Tested on its own only**, as asked. | draft |
| F6 | `fee_amount` | The classifier extracts the disputed fee (`fee_iqd`) separately from the transaction amount. | classify |
| F7 | `no_now_urgency` | "هسه" (now) no longer raises priority. | route |
| F3b | `recheck_use_second` | Round 3: a same-team disagreement is drafted from the re-check's answer, flagged. | gate |
| F3c | `recheck_cross_team` | Round 3: any non-fraud disagreement is drafted from the re-check's answer (routed to its team), flagged. | gate |
| F6b | `fee_followup` | Round 3: a separate small call extracts the fee, only for fee tickets; the classifier prompt is unchanged. | after classify |
| F9 | `confusable_recheck` | Round 3: re-check an answer in a look-alike pair (`config/taxonomy.yaml`) under 0.90. | gate |
| F10 | `runner_up` | Round 3: the classifier names a runner-up; one under 0.90 triggers the re-check. | classify + gate |
| F11 | `ask_if_missing` | Round 3: shop / agent / bill details are asked for only if the ticket doesn't give them. | draft |
| F12 | `no_specific_followup` | Round 3: the drafter must not promise to send a specific answer, date or result (v2 wording). | draft |
| F13 | `lookalike_hints` | Round 3: sharper classifier hints for look-alike subcategories. | classify |
| F14 | `fraud_secondary_rule` | Follow-up: reworded fraud / second-issue rule in the classifier prompt (not adopted). | classify |
| F14b | `fraud_secondary_cleanup` | Follow-up: the same rule enforced in code after each classification. | after classify |
| F8 | `unclear_template` | Unclear / off-topic tickets get a fixed reply that asks what the problem is (and vaguely what details help), with no drafter call. | draft |

Not tested here, because they only help us monitor and do not change what the agent sees: review logging (1), cost logging and the evaluation additions (part of 9), queue sorting (10). They come after the experiments. Confidence (4) is a separate discussion.

Flags are read from `PIPELINE_FIXES` (see `src/pipeline/fixes.py`). With no flags set, the pipeline behaves exactly as before.

## Method

**Test set.** `data/probes/fixes_30.jsonl`: 30 new tickets, none of which were used to come up with the fixes (testing on s07, s15, s17 and s18 would be circular). About two-thirds target a fix (`targets` field); the rest are ordinary tickets that catch regressions. Gold labels are the *desired* behaviour; for example, a ticket with a casual "هسه" has the default priority as gold.

**Same answers unless the fix changes the question.** `LLM_CACHE_DIR` makes an identical model call (same model, system prompt and user prompt) return the stored reply. So when a fix only changes rules (F2, F3, F7), the models give exactly the same answers in both runs, and every difference is caused by the fix. When a fix changes what a model is sent (F5, F6, F8), only those calls are made fresh. The key also names the backend for any non-cli backend (`api`, or `openai:<provider>` for the free-model profiles), so an API validation run can never be served a stored cli reply; cli keys are unchanged, so existing cache entries stay valid.

**Noise floor.** The `cli` backend ignores temperature, so the same ticket can come back differently. The baseline is run twice more **without** the cache to measure how much changes by chance. A fix that changes model inputs (F5, F6, F8) must beat that noise to count.

**Draft quality.** A judge (the `evaluator` role, dev only; prompt in `scripts/prompts/judge_draft.md`) checks each draft: understood, grounded, no promise, asks for the right info, safe, tone, clean, and a 1–5 score for how much editing it needs. The judge never sees which config produced the draft. Its own noise is measured by grading the same drafts twice.

**Metrics that matter for the agent** (all in the per-config pages):
- subcategory, outcome, priority, amount, fee accuracy against gold;
- draft given iff it should be (an escalated ticket has no draft for the agent);
- **bad drafts marked ready**: drafts the judge calls bad (not understood, ungrounded, promising, unsafe, unclean, or score ≤ 2) that the pipeline marked `drafted`. This is the riskiest case for an agent who skims;
- mean draft score, number of escalations and model calls.

**Combos.** For each pair, the report shows what the pair would score if the two fixes simply added up, and the difference from what was observed (the *interaction*).

**Backend caveat.** There is no API key in this environment, so everything runs on the `cli` backend. Per the main README, these numbers are for comparing configs with each other, not for thresholds or the MVP results.

## Reproduce

```bash
python scripts/experiment.py run baseline
python scripts/experiment.py run baseline --nocache --label baseline-rep1
python scripts/experiment.py report baseline
python scripts/experiment.py run F2 && python scripts/experiment.py report F2
python scripts/experiment.py run F2+F3 && python scripts/experiment.py report F2+F3
python scripts/experiment.py summary
```

Run files go to `runs/exp/` and the cache to `runs/cache/` (both ignored by git, as `runs/` already was).
