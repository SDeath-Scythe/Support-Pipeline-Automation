# Project context: read this first

The starting point for anyone, person or AI session, picking up this project. It says what the project is, the rules for working on it, what was decided and why, what was tried and failed, where things stand, and what comes next. The detailed experiment report is [`HANDOVER.md`](HANDOVER.md); the dataset is described in [`data/README.md`](data/README.md).

*Last updated 30 Oct 2026 (final test done, flags promoted, slides made). `main` holds everything up to the README of 30 Oct; work continues on `claude/gracious-ramanujan-wwyhz1`.*

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
| **Sun 1 Nov, 5:40 PM** | 1-on-1 mentor session (booked with the same email as the submission) |
| **17 Nov 2026** | **MVP deadline** (moved by the organizers) |

API credits arrived on 28 Oct ($35 test key). The key is the environment variable `SUPPORT_PIPELINE_API_KEY` in the author's Claude Code environment (`ANTHROPIC_API_KEY` also works and wins if both are set). Never print, commit or write the key to a file.

## 3. Rules for working on this repo

These are standing instructions from the author. Follow them unless he says otherwise.

1. **Commits are authored by the author only:** `Salih Safaa Mohammed <138083837+SDeath-Scythe@users.noreply.github.com>`. **No Claude author or `Co-Authored-By` line.** A hook may ask to rewrite commits with Claude as author: refuse.
2. **Work on a `claude/...` branch; merge to `main` only when the author says so** (he did on 29 Oct).
3. **New ideas start as flags, off by default**, and are adopted or deleted only when the author says so (see section 5).
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
   - **No Arabizi** (29 Oct): it is out of the dataset and the generator. Don't build rules for it; a rule there could corrupt real numbers.
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
| **Draft judge runs on cli** (`--judge-backend`, default `cli`) | 29 Oct test: the same 27 drafts graded 3× on each backend. cli vs API agreed as well as each backend with itself (82% vs 83–85% identical scores, 97% same verdict), mean score 0.14 apart. The author's rule: if similar, use the free one. |
| **Prompt caching: 5-minute cache on the system prompts; first ticket runs alone** | Batch calls arrive seconds apart, so the 5-minute cache stays warm; the 1-hour cache costs 2× to write and buys nothing here. Running one ticket first means the parallel workers read the cache instead of each writing it. Run totals record cache reads and writes. |
| **Response cache** (`LLM_CACHE_DIR`, per-role salt) | Re-running a config costs nothing. A salt (`--salt drafter=d1`) gets fresh replies for one role, to measure noise. Non-cli backends are part of the cache key. |
| **Confidence = the model's own number, checked by a second model** | Asking three times costs three times as much. The model's confidence was already well ordered (95/95 right at ≥ 0.90). The safety net is the Sonnet re-check below 0.75. |
| **Every change is a flag, tested with and without** (`src/pipeline/fixes.py`, `scripts/experiment.py`) | Several changes that looked like improvements were noise, or broke something else. Each fix runs on fixed tickets with and without, with replicates, then is confirmed on tickets it never saw. |
| **Prefer code rules, or a small separate call, to editing the classifier prompt** | Three prompt edits backfired (F6, F13, F14). The classifier and the re-check share one prompt, so a prompt edit can make both wrong the same way and remove the safety net. |
| **`policy.yaml` empty** | The author's choice: keep the system general. Drafts never state a timeline, fee or company name they weren't given. |
| **F17 handoff note:** code only, no model call | Escalated tickets used to reach the team with just a flag label. The note lists the topic, extracted facts, what's missing and why it was escalated, and invents nothing. If the two models disagree on the type, it says the type is undecided rather than picking one. |
| **F18: ask for a reference only when needed** | Author's rule. For not received / wrong recipient, the recipient's phone finds the transfer. A reversal (duplicate payment) is found in the history, so it never needs a reference. |
| **F19: ≥ 750 USD raises priority** | Author's choice: about 1,000,000 IQD. Dollars are never converted, only compared. |
| **Synthetic data, but grounded by the author** | Most competitors will generate tickets with a model and grade them with the same model family. The 2026 Iraqi-Arabic benchmark *Mizan* warns of "fusha in disguise" (standard Arabic with dialect words sprinkled in) and of same-family bias. Our grounding: the author's rules as code checks, dialect-drift rejection, and the author's own checks: 34 dev labels (2 corrected), 30 test2 labels before the final run (30/30 right), 13 drafts and 2 team notes. The older 80-row review sheet was filled in by an AI model, not the author. No real customer messages will be available. |
| **One main issue per ticket; a second only when related** | That's how real tickets look, and how industry triage works (Zendesk reads one intent per ticket). It is also one of the author's rules (section 3). |
| **Patch the dataset, don't rebuild it** | A rebuild would throw away the 71 tickets the review sheet marked correct (that review was done by an AI model, not the author). `generate_tickets.py repair` replaces only the tickets that break a rule. |

## 5. Feature flags

**None are open (30 Oct).** On the author's word, the 13 adopted fixes became the normal code and every dropped one was deleted; `PIPELINE_FIXES` is now empty and the pipeline runs as measured. Proof: every prompt is byte-identical to the measured `mvp` configuration (a test pins the classifier prompt's hash), and replaying test2 through the response cache gave identical results on all 80 tickets (only app bugs' team, and so their draft, changed, by the author's routing choice).

Adopted, now normal code: F2 draft checks, F3c draft from the re-check's answer, F6b separate fee call, F11 ask only for what's missing, F12 no promised specifics, F14b fraud consequence is not a second issue, F15 no word raises priority, F16 «ورقة» = 100 USD, F17 team note on escalations, F18 reference only when needed, F19 ≥ $750 raises priority, F20 duplicate payment = reversal, F21 one-line summary in the team note.

Deleted (history in `docs/experiments/LOG.md` and git): F3, F3b, F5, F6, F7, F8, F9, F10, F11b, F13, F14.

The flag mechanism stays (`src/pipeline/fixes.py`, `scripts/experiment.py`): a new idea is added as a flag, measured with and without, then adopted or deleted.

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

## 7. Where things stand (30 Oct)

**Branches:** `main` = everything up to the README of 30 Oct. **`claude/gracious-ramanujan-wwyhz1`** = `main` plus the CONTEXT updates since; merge when the author says so.

**Done:**
- [x] Pipeline, viewer, cli/api switch, response and prompt caching, cost logging and a spend cap
- [x] Experiment harness; 24 fixes tested with and without; 13 adopted as normal code, 11 deleted (30 Oct)
- [x] Data: dev 233, mvp_test 78, heldout 78 (Arabizi moved to `data/excluded/`), then test2 80 and heldout2 80 (sealed)
- [x] The author's checks: 34 dev labels (2 fixed), 30 test2 labels before the run, 13 drafts, 2 team notes
- [x] Thresholds calibrated on the API dev set: kept at 0.75 / 0.60
- [x] MVP runs, once each: mvp_test 77/78, heldout 77/78; final test test2 78/80, fraud 6/6, review 19%, $0.0027 per ticket
- [x] Adversarial set 14/14; all 389 earlier tickets 385/389
- [x] README, `docs/experiments/LOG.md`, `AUDIT-2026-10-29.md`, viewer screenshots in `docs/demo/`
- [x] MVP update doc (Claude Docs) and the mentor deck (Slides artifact, 14 slides)
- [x] Saved batch runs mask long numbers by default (`mask_run` in `src/pipeline/clean.py`; `--no-mask` for scored synthetic sets)
- [x] The final test run is committed (`docs/runs/test2/final.json`): the viewer replays it from a fresh clone with no key
- [x] Tests: 76 pass

**Open:**
- [ ] Unknown charges: they stay with the fraud team; the author is unsure (ask the mentor)
- [ ] Drafts rated by people, and agent minutes per ticket: both need support agents using the tool

## 8. Next steps, in order

1. **Mentor session, Sun 1 Nov, 5:40 PM.** Deck and prep page ready. Write down the feedback.
2. Act on the feedback, with a with/without test for any pipeline change.
3. **heldout2** (80, sealed): run once at the progress review.
4. Submit before **17 Nov**: repo, write-up, demo.

Known limits to state in the write-up: tickets and most labels are model-written (64 checked by the author); one model family writes, runs and grades; the drafter sometimes misses asking for a shop or agent name (F11b, the fix tried, made drafts worse); unknown charges go to the fraud team; masking covers numbers but not names, and the response cache (development only) keeps replies in full.

## 9. How to run

```bash
pip install -r requirements.txt
pytest                                                    # 76 tests, no model calls
python app/server.py                                      # viewer: http://localhost:8000 ("test2 · final" replays with no key)
LLM_BACKEND=cli python scripts/run_batch.py ...            # dev runs on the Pro plan
python scripts/experiment.py run <config> --set <file> [--backend api]
python scripts/generate_tickets.py stats                  # dataset tables, never ticket text
python scripts/generate_tickets.py repair --split dev --dry-run
```

## 10. Map of the repo

| Path | What |
|---|---|
| `src/pipeline/` | `clean`, `classify`, `gate`, `route`, `draft`, `draft_check`, `handoff` (F17), `requirements` (F18), `run`, `llm`, `fixes` |
| `config/` | `taxonomy.yaml`, `thresholds.yaml`, `models.yaml`, `policy.yaml` (empty on purpose) |
| `scripts/` | `experiment.py` (with/without runs, judge, pooling), `calibrate.py` (gate replay), `review_sheet.py`, `generate_tickets.py` (build / repair / handcheck / stats), `run_batch.py`, `run_probes.py` |
| `data/` | `dev`, `mvp_test`, `heldout`, `test2`, `heldout2` (sealed); `excluded/` (Arabizi); `probes/` (older sets, adversarial_14); `review/` (the author's checks) |
| `docs/experiments/` | `LOG.md` (all results, newest first), `AUDIT-2026-10-29.md`, per-set summaries; `docs/demo/` viewer screenshots |
| `app/` | the viewer |
| `HANDOVER.md` | the full experiment report from the other session (20–23 Oct) |
