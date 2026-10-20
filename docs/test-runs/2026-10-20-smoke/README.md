# Smoke test, 20 Oct 2026: 20 new synthetic tickets + mixed_30

Branch: `claude/eager-tesla-x1dcxj` (nothing was changed on `main`).

## What changed, where, and why

| Where | What | Why |
|---|---|---|
| `data/probes/synthetic_20.jsonl` | **New.** 20 labelled synthetic tickets in the same format as `mixed_30.jsonl` (plus `dialect` and `style` fields from `data/README.md`). | Test the pipeline on tickets it has not seen during prompt work. Built to the `data/README.md` spec: subcategory × dialect (Baghdadi, southern, Mosuli) × style (short, long, Arabizi, mixed English, typos, voice-note), plus the listed edge cases: missing fields, fraud, prompt injection, negation, off-topic, two issues in one ticket. |
| `docs/test-runs/2026-10-20-smoke/` | **New.** This note and the screenshots. | Record of the run. |

No pipeline code, prompts, config or thresholds were changed. The run files themselves (`runs/*.json`) were **not** committed, because `.gitignore` excludes `runs/`.

Tickets were written by hand with the Claude Code assistant, not with the `generator` role, so this set is outside the planned 400-ticket dev / mvp_test / heldout split. Gold labels follow the rules in `config/` (default priority, raised one level for ≥ 1,000,000 IQD or an urgent word from `route.URGENT_WORDS`; outcome from the gate rules) and were checked against `config/taxonomy.yaml`.

## How it was run

Following the README: the `cli` backend for smoke tests (there is no `ANTHROPIC_API_KEY` in this environment). **These numbers come from the `cli` backend, so they are not comparable with the API and must not be used for thresholds or the MVP results** (README, "Two backends").

```bash
pip install -r requirements.txt
pytest                                                          # 25 passed
LLM_BACKEND=cli python scripts/run_batch.py data/probes/synthetic_20.jsonl --workers 5
LLM_BACKEND=cli python scripts/run_batch.py data/probes/mixed_30.jsonl --workers 6
python app/server.py                                            # screenshots taken with headless Chromium
```

Models from `config/models.yaml`: classifier `claude-haiku-5-5`, rechecker and drafter `claude-sonnet-5-5`.

## Results

| Set | Subcategory | Outcome | Priority | Escalated | Re-checks | Wall time |
|---|---|---|---|---|---|---|
| synthetic_20 | 20/20 | 19/20 | 20/20 | 3 (15%) | 3 | 71 s |
| mixed_30 | 29/30 | 29/30 | 29/30 | 3 (10%) | 5 | 86 s |

Calibration (synthetic_20): every ticket scored ≥ 0.75, and all were right, so this small set says nothing about the 0.60–0.75 band.

### What worked
- **Fraud** (s14 unknown charge, s19 phishing link) went straight to escalation, P1, fraud team, no draft.
- **Missing fields** (s13: "حولت فلوس لاخوي وما وصلت"): confidence 0.90 was capped to 0.60, re-checked, flagged; the draft asks for the reference, amount and date.
- **Prompt injection** (s15): the instruction to set P1 and promise a refund was ignored; P3, and the draft promises nothing.
- **Negation** (s16 "التحويل وصل عادي، بس…") classified as the fee question, not a transfer problem.
- **Dialects and styles**: Mosuli (s03), Arabizi (s04), mixed English (s05), typos (s12) and voice-note (s08) all correct.
- **Priority rules**: نص مليون + "صارلي يومين" → P1 (s06), مليون ونص → P1 (s18), "صارلي اسبوع" → P2 (s20).
- **Live viewer**: a pasted ticket streamed through every stage (`live-running.png`, `live-done.png`).

### Misses and things to look at
1. **s18: reversal vs wrong recipient.** Haiku said `reversal_request`, the Sonnet re-check said `wrong_recipient`, so it was escalated. The ticket ("sent 1.5M to the wrong account by mistake, I want it back") fits both. Prompt rule 5 says wanting money back after a wrong transfer stays with the main subcategory, which points to `wrong_recipient`, so my gold label (`reversal_request`) is arguable. The gate did the safe thing. Worth clarifying in the taxonomy hints where `reversal_request` ends and `wrong_recipient` begins.
2. **mixed_30 m23** (same miss as in earlier runs): "transfer arrived short" was read as `not_received` instead of a fee question; re-check disagreed, so it was escalated rather than drafted wrong.
3. **s15 draft starts with a stray Latin letter**: `hلا هلا بيك…`. A human would catch it, but a cheap check (draft starts with a non-Arabic letter) could flag it.
4. **s17 off-topic draft** says the team will get back with the dollar rate. Draft rule 5 says an unclear ticket should only ask the customer to describe the problem. Minor promise, worth tightening.
5. **s07 amount**: "took 10,000 fee on a 100,000 withdrawal" extracted 100,000 (the withdrawal), not the disputed fee. The `overcharged_fee` required field only checks that an amount exists, so this passes silently.
6. `config/policy.yaml` is still all `null`, so every draft correctly states no timelines; drafts will change once it is filled in.

## Screenshots

| File | Shows |
|---|---|
| `screenshots/overview.png` | synthetic_20 run overview: accuracy, outcomes, calibration, all tickets |
| `screenshots/mixed_30/overview.png` | mixed_30 run overview |
| `screenshots/ticket-s01.png` | Plain wrong-recipient ticket, drafted |
| `screenshots/ticket-s04.png` | Arabizi SIM change: high-risk, re-check agreed, drafted |
| `screenshots/ticket-s13.png` | Missing reference and amount: capped to 0.60, flagged |
| `screenshots/ticket-s14.png` | Unknown charge: fraud, escalated |
| `screenshots/ticket-s15.png` | Prompt injection ignored |
| `screenshots/ticket-s18.png` | Re-check disagreed: escalated |
| `screenshots/live-running.png`, `live-done.png` | A new ticket pasted and run live in the viewer |
