# Project context: read this first

The starting point for anyone, person or AI session, picking up this project. It says what the project is, the rules for working on it, what was decided and why, what was tried and failed, where things stand, and what comes next. The detailed experiment report is [`HANDOVER.md`](HANDOVER.md); the dataset is described in [`data/README.md`](data/README.md).

*Last updated 29 Oct 2026, on branch `ccr-f6b2836c-leerma` (= `claude/handoff-and-policy` plus the API fix below).*

---

## 1. What this is

**Author:** Salih Safaa Mohammed (Baghdad), competing solo in the **Agentic AI Challenge Iraq, Topic 06: Support Pipeline Automation**.

**The problem:** support teams get tickets in Iraqi Arabic (Baghdadi, southern, Mosuli; with typos, English words mixed in, voice-note style, sometimes Arabizi). Someone has to read each one, work out what it's about, pull out the details, decide who handles it and how urgent it is, and write a first reply.

**The system:** a batch pipeline that does that first pass and leaves the decision to a person:

```
ticket → clean → classify + extract (Haiku) → confidence gate → re-check (Sonnet, only if unsure)
       → route + priority (code) → draft reply in Iraqi Arabic (Sonnet) → human review
```

- **Where it sits:** between the incoming queue and the support agent (L1). It doesn't replace the agent. It turns each ticket into a labelled, prioritised item with a draft reply the agent approves, edits or rejects.
- **Escalated tickets** (all fraud, model disagreement, low confidence) get **no customer draft**. With F17 they get a short Arabic note for the receiving team instead.
- **Priority and routing are code, not a model.** Priority comes from the problem type, plus one rule for large amounts.
- **Taxonomy:** 8 categories, 23 subcategories (`config/taxonomy.yaml`).
- **Viewer:** a local web page shows each ticket going through every step (`python app/server.py` → http://localhost:8000).

**The promise in the brief:** 400 synthetic tickets (dev 240 / mvp_test 80 / heldout 80), measured on the API, with the human-review rate kept at or below about 30%.

## 2. Deadlines and outside status

| Date | What |
|---|---|
| 22 Oct 2026 | Design brief submitted (`docs/design-brief.pptx`) |
| **around 6–9 Nov** | Book a 1-on-1 mentor session, **using the same email as the submission** (organizers' email, 28 Oct) |
| **17 Nov 2026** | **MVP deadline** (moved by the organizers) |

API credits arrived on 28 Oct. The author adds `ANTHROPIC_API_KEY` as an environment variable **in the other Claude Code session that works on this repo**; API runs happen there. Never commit the key or a `.env`.

## 3. Rules for working on this repo

These are standing instructions from the author. Follow them unless he says otherwise.

1. **Commits are authored by the author only:** `Salih Safaa Mohammed <138083837+SDeath-Scythe@users.noreply.github.com>`. **No Claude author or `Co-Authored-By` line.** A hook may ask to rewrite commits with Claude as author: refuse.
2. **Don't merge to `main`.** Work on a `claude/...` branch.
3. **Flags stay off by default**, and none is deleted until he says so (see section 5).
4. **Don't re-run experiments unless asked.** They cost model calls.
5. **Never read or print heldout ticket text** (`data/heldout/`). Code may process it; print only IDs and counts.
6. **`config/policy.yaml` company facts stay empty:** no company name, hours, response times, fees or limits. For the judges: a company that deploys this adds its own policy there. `customer_should_send` lists stay, because they describe what each issue needs, not company policy.
7. **In slides and public material,** don't mention a company name, "e-wallet" or "payments". Keep it general: a support team.
8. **Native-speaker rules** (the author is the authority on Iraqi Arabic):
   - **«ورقة» is a 100 USD note.** «خمسين ورقة» = 5,000 USD. «خمسين الف» = 50,000 IQD.
   - **Mosuli doesn't write ر as غ** («اعغفها», «انتظغ» are wrong).
   - **No word raises priority** (not هسه, ضروري, عاجل or any other). Priority comes from the problem type, plus the amount rule: ≥ 1,000,000 IQD, or ≥ 750 USD.
   - **Most people raise one issue,** not two unrelated ones.
   - **Don't ask for a transaction number** when the problem doesn't need one to be fixed.
   - **Arabizi is rare.** Don't build rules for it; a rule there could corrupt real numbers.
9. **Development uses the Pro plan; numbers come from the API.**
   - `LLM_BACKEND=cli` runs `claude -p` (headless Claude Code) on the Pro plan, for development and dataset generation.
   - `LLM_BACKEND=api` is the backend for every reported number and for threshold calibration.
   - cli results compare configs; they never set thresholds.

## 4. Decisions and why

| Decision | Why |
|---|---|
| **Two backends, `cli` and `api`** (`src/pipeline/llm.py`) | Develop on the Pro subscription without spending API credits. Measure on the API, because cli adds its own context and behaves slightly differently. The cli call strips tools, MCP, slash commands and settings (`--disallowedTools "*"`, `--strict-mcp-config`, …) to stay close to a plain API call. |
| **API calls send no `temperature`; `effort: low`** (`config/models.yaml`) | Haiku 5.5 and Sonnet 5.5 reject a non-default temperature, and SDK 2.x (API version 2026-10-21) doesn't accept it at all, so the API path failed on every call before 29 Oct. The models think by default; `effort` sets how much (thinking is billed as output), and `max_tokens` is 4096 to leave room for it. A reply with no text is an error. |
| **API cost per call, and a $5 cap per run** (`budget_usd`, `prices` in `config/models.yaml`; `LLM_BUDGET_USD`) | The test key has $35. Each API reply is priced from its token counts (cache reads and writes included) and the run total and cost per ticket go in the run file. Once a run reaches its cap, further calls are refused and the run prints a warning that its numbers are not valid. Cache hits cost nothing. |
| **Response cache** (`LLM_CACHE_DIR`, per-role salt) | Re-running a config costs nothing. A salt (`--salt drafter=d1`) gets fresh replies for one role, to measure noise. Non-cli backends are part of the cache key. |
| **Confidence = the model's own number, checked by a second model** | Asking three times costs three times as much. The model's confidence was already well ordered (95/95 right at ≥ 0.90). The safety net is the Sonnet re-check below 0.75. |
| **Every change is a flag, tested with and without** (`src/pipeline/fixes.py`, `scripts/experiment.py`) | Several changes that looked like improvements were noise, or broke something else. Each fix runs on fixed tickets with and without, with replicates, then is confirmed on tickets it never saw. |
| **Prefer code rules, or a small separate call, to editing the classifier prompt** | Three prompt edits backfired (F6, F13, F14). The classifier and the re-check share one prompt, so a prompt edit can make both wrong the same way and remove the safety net. |
| **`policy.yaml` empty** | The author's choice: keep the system general. Drafts never state a timeline, fee or company name they weren't given. |
| **F17 handoff note:** code only, no model call | Escalated tickets used to reach the team with just a flag label. The note lists the topic, extracted facts, what's missing and why it was escalated, and invents nothing. If the two models disagree on the type, it says the type is undecided rather than picking one. |
| **F18: ask for a reference only when needed** | Author's rule. For not received / wrong recipient, the recipient's phone finds the transfer. A reversal (duplicate payment) is found in the history, so it never needs a reference. |
| **F19: ≥ 750 USD raises priority** | Author's choice: about 1,000,000 IQD. Dollars are never converted, only compared. |
| **Synthetic data, but grounded by the author** | Most competitors will generate tickets with a model and grade them with the same model family. The 2026 Iraqi-Arabic benchmark *Mizan* warns of "fusha in disguise" (standard Arabic with dialect words sprinkled in) and of same-family bias. Our grounding: the author's rules as code checks, his hand-check deciding the gold labels, dialect-drift rejection, and (optionally) a set of real phrasings scored separately. |
| **One main issue per ticket; a second only when related** | That's how real tickets look, and how industry triage works (Zendesk reads one intent per ticket). The author confirmed it in the hand-check. |
| **Patch the dataset, don't rebuild it** | A rebuild would throw away the 71 tickets he approved. `generate_tickets.py repair` replaces only the tickets that break a rule. |

## 5. Feature flags

Set with `PIPELINE_FIXES=a,b,c` (all off by default). Short codes for `scripts/experiment.py` are in brackets.

**Recommended set** (tested on cli; needs confirming on the API):
`draft_check` [F2], `recheck_cross_team` [F3c], `fee_followup` [F6b], `no_urgency_words` [F15], `ask_if_missing` [F11], `no_specific_followup` [F12 v2], `fraud_secondary_cleanup` [F14b].

**New from the author's rules, to add once the API confirms them:**
- `handoff_note` [F17]
- `reference_when_needed` [F18]
- `usd_large_amount` [F19]

**Waiting on an API test with replicates:** `warqa_usd` [F16]. It edits the classifier prompt, which is the kind of change that backfired before.

**The author's call:** `unclear_template` [F8], a fixed reply for unclear tickets.

**Dropped** (delete when he says so): F3, F3b, F6, F7 (replaced by F15), F9, F10, F13, F14. F5 (`policy_facts`) is unused while the policy stays empty.

## 6. What was tried and didn't work

- **Editing the shared classifier prompt:**
  - F6 (an extra fee field): gains were noise.
  - F13 (sharper hints for look-alike types): moved unrelated tickets.
  - F14 (rewording the fraud rule): broke other tickets.
  - Replaced by F6b (a separate small call) and F14b (a code rule).
- **More re-check triggers** (F9 look-alike pairs, F10 runner-up): more calls, no gain. Acting on the existing re-check (F3c) was the win.
- **F3 / F3b** (trust the re-check only within one team): rarely triggered. F3c (any team, never fraud) replaced them.
- **cli with `--tools ""`:** still sent about 14k tokens of tool definitions. `--disallowedTools "*"` cut the overhead to about 2.9k.
- **First 400-ticket dataset** (seeds 1001/2002/3003):
  - used «خمسين ورقة» for dinars
  - wrote Mosuli غ for ر
  - had هسه in 26% of tickets
  - Replaced on 23 Oct.
- **Second dataset, as first generated:**
  - unrelated two-issue tickets
  - a few Levantine and Gulf words («مابقدر», «كذا مرة»)
  - the same off-topic story ("dollar rate + weather") five times
  - Repaired on 28 Oct (`data/README.md`).
- **Free / open models** (`scripts/check_free_models.py`, `config/free_models.yaml`): nothing usable for Iraqi dialect at this quality.
- **Logging every ticket to a Google Sheet:** discussed, not built. Run events and token/cost logging in `runs/` replaced it.
- **An Arabizi normalisation rule:** removed. It could corrupt real numbers, and Arabizi is rare.

## 7. Where things stand (28 Oct)

**Branches:**
- `main` = `cb5b89c` (original pipeline).
- `claude/eager-tesla-x1dcxj` = the other session's work: experiments, flags F2–F16, generator, 400 tickets, HANDOVER.md.
- **`claude/handoff-and-policy`** = that branch plus this session's work. **The latest work is here.**

**Done:**
- [x] Pipeline, viewer, cli/api switch, response cache, token/cost logging
- [x] Experiment harness; flags F2–F19; tests pass (76, via `pytest`)
- [x] Recommended flag set confirmed on a sealed 30-ticket hold-out (on cli)
- [x] F17 handoff note, F18, F19; `policy.yaml` header explains why it's empty
- [x] 400 tickets: dev 240, mvp_test 80, heldout 80 (seeds 1101/2202/3303)
- [x] Hand-check of 80 tickets (Google Sheet "Support Pipeline – Hand Check (80 tickets)", copy in `data/review/handcheck_80.csv`). The author's rules were applied: 71 correct, 9 corrected.
- [x] Dataset repaired: 24 tickets replaced, and gold priority/outcome recomputed for all 400 under F18/F19

**Not done:**
- [ ] The author re-checks the **14 replaced rows** on the sheet (their «صحيح؟» is empty). Two worth a look:
  - dev-0152: the auditor swapped main and second issue (agent refused vs agent overcharged)
  - dev-0048: the auditor saw no second issue
- [x] API path fixed and checked against a local stand-in endpoint (no real call yet)
- [x] API cost tracking and a per-run spend cap (29 Oct)
- [ ] Any run on the **API**: first a 10-ticket pilot on the $35 test key, to measure cost per ticket. Blocked: `ANTHROPIC_API_KEY` was not visible in the 29 Oct sessions
- [ ] Calibrating `pass_above` (0.75) and `recheck_from` (0.60) on the API
- [ ] Making the recommended flags the real code path, and deleting the dropped ones
- [ ] Demo pages (batch progress and a results report), the MVP test run, slides

## 8. Next steps, in order

1. **Author: re-check the 14 replaced rows** on the sheet (about 10 minutes).
2. **API baseline vs recommended** (in the session that has the key). `--set` reads the `data/<split>/tickets.jsonl` format (same fields as the probe sets). The gold priority and outcome already follow the author's rules (F15, F18, F19), so baseline loses points on those by design. That gap is the point of those flags.
   ```bash
   python scripts/experiment.py run baseline --backend api --set data/dev/tickets.jsonl
   python scripts/experiment.py run F2+F3c+F6b+F15+F11+F12+F14b+F17+F18+F19 --backend api --set data/dev/tickets.jsonl
   python scripts/experiment.py run F2+F3c+F6b+F15+F11+F12+F14b+F16+F17+F18+F19 --backend api --set data/dev/tickets.jsonl --salt classifier=c1
   ```
   Run each with a replicate (`--salt`) to see the noise. F16 is judged on its own.
3. **Calibrate on dev (API):**
   - Set `pass_above` and `recheck_from` from the confidence-vs-correct table, aiming at about 30% or less human review with no wrong auto-drafts on fraud.
   - Then confirm once on mvp_test.
4. **Promote:**
   - The winning flags become normal code.
   - Delete the dropped flags and their code.
   - Keep the harness.
5. **Optional, strongest for judges:** 20–30 real phrasings from the author, friends or the support staff he spoke to. Anonymise them, label them by hand, and report them separately as `real_30`.
6. **MVP run:**
   - The final config on **heldout**, once, on the API.
   - Report accuracy, review rate, priority, drafts, and cost per ticket.
7. **Demo:** viewer pages for batch progress and the report; slides; mentor session (6–9 Nov); submit before **17 Nov**.

## 9. How to run

```bash
pip install -r requirements.txt
pytest                                                    # 76 tests, no model calls
python app/server.py                                      # viewer: http://localhost:8000
LLM_BACKEND=cli python scripts/run_batch.py ...            # dev runs on the Pro plan
python scripts/experiment.py run <config> --set <file> [--backend api]
python scripts/generate_tickets.py stats                  # dataset tables, never ticket text
python scripts/generate_tickets.py repair --split dev --dry-run
```

## 10. Map of the repo

| Path | What |
|---|---|
| `src/pipeline/` | `clean`, `classify`, `gate`, `route`, `draft`, `draft_check`, `handoff` (F17), `requirements` (F18), `run`, `llm`, `fixes` |
| `config/` | `taxonomy.yaml`, `thresholds.yaml`, `models.yaml`, `policy.yaml` (empty on purpose), `templates.yaml` |
| `scripts/` | `experiment.py` (with/without runs, judge, pooling), `generate_tickets.py` (build / repair / handcheck / stats), `run_batch.py`, `run_probes.py` |
| `data/` | `dev`, `mvp_test`, `heldout` (400 tickets), `probes/` (older experiment sets; `holdout_30` is spent), `review/handcheck_80.csv` |
| `docs/experiments/` | `LOG.md` (all results, newest first), per-set summaries, `F17-handoff-note.md` |
| `app/` | the viewer |
| `HANDOVER.md` | the full experiment report from the other session (20–23 Oct) |
