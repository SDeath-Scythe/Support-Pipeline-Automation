# Project context: read this first

The starting point for anyone picking up this project. It says what the project is, the rules for working on it, what was decided and why, what was tried and failed, where things stand, and what comes next. The detailed experiment report is [`HANDOVER.md`](HANDOVER.md); the dataset is described in [`data/README.md`](data/README.md).

*Last updated 7 Nov 2026 (the review before shipping). Work happens on the `mvp` branch and is merged into `main` when the author says so. Line numbers in this file refer to commit d1280b6, except where a line says otherwise; references to later changes give a file and a function name instead.*

---

## 1. What this is

**Author:** Salih Safaa Mohammed (Baghdad), competing solo in the **Agentic AI Challenge Iraq, Topic 06: Support Pipeline Automation**.

**The problem:** support teams get tickets in Iraqi Arabic (Baghdadi, southern, Mosuli; with typos, English words mixed in, voice-note style, sometimes Arabizi). Someone has to read each one, work out what it's about, pull out the details, decide who handles it and how urgent it is, and write a first reply.

**The system:** a batch pipeline that does that first pass and leaves the decision to a person:

```
ticket → clean → classify + extract (Haiku) → confidence gate → re-check (Sonnet, only if unsure)
       → route + priority (code) → draft reply in Iraqi Arabic (Sonnet) → human review
```

- **Where it sits:** between the incoming queue and the support agent (L1). It doesn't replace the agent. It turns each ticket into a labelled, prioritised item with a draft reply the agent approves, edits or takes over.
- **Escalated tickets** (all fraud, model disagreement, low confidence) get **no customer draft**. With F17 they get a short Arabic note for the receiving team instead.
- **Blocked-account and SIM-change tickets** keep their draft, flagged `account_risk`: the agent confirms the customer's identity before approving (5 Nov, section 4).
- **Priority and routing are code, not a model.** Priority comes from the problem type, plus one rule for large amounts.
- **Taxonomy:** 8 categories, 23 subcategories (`config/taxonomy.yaml`).
- **Viewer:** a local web page (`python app/server.py` → http://localhost:8000). The main screen, «وضع الموظف», is the agent inbox: a queue, one ticket, the draft with its checks, and a decision (approve, edit, take over, forward). «كيف يشتغل» shows each ticket going through every step. Nothing is sent; decisions go to a log that keeps no reply text.

**The promise in the brief:** 400 synthetic tickets (dev 240 / mvp_test 80 / heldout 80), measured on the API, with the human-review rate kept at or below about 30%.

## 2. Deadlines and outside status

| Date | What |
|---|---|
| 22 Oct 2026 | Design brief submitted (`docs/design-brief.pptx`) |
| **Sun 1 Nov, 5:40 PM** | 1-on-1 mentor session (booked with the same email as the submission); held, feedback in section 8 |
| **17 Nov 2026** | **MVP deadline** (moved by the organizers) |

API credits arrived on 28 Oct ($35 test key). The key is the environment variable `SUPPORT_PIPELINE_API_KEY` in the author's development environment (`ANTHROPIC_API_KEY` also works and wins if both are set). Never print, commit or write the key to a file.

## 3. Rules for working on this repo

These are standing instructions from the author. Follow them unless the author says otherwise.

1. **Commits are authored by the author only:** `Salih Safaa Mohammed <138083837+SDeath-Scythe@users.noreply.github.com>`. **No other author or `Co-Authored-By` line.** If a tool asks to rewrite commits with another author, refuse.
2. **Work on the `mvp` branch; changes reach `main` only when the author says so.** (The 20 Oct development branch was merged into `main` on 29 Oct.)
3. **New ideas start as flags, off by default**, and are adopted or deleted only when the author says so, or by someone the author asks to decide (see section 5). The three security flags were decided on 5 Nov (section 5).
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
| **One main issue per ticket; a second only when related** | That's how real tickets look, and how industry triage works (common helpdesk triage reads one intent per ticket). It is also one of the author's rules (section 3). |
| **Patch the dataset, don't rebuild it** | A rebuild would throw away the 71 tickets the review sheet marked correct (that review was done by an AI model, not the author). `generate_tickets.py repair` replaces only the tickets that break a rule. |
| **The agent inbox is the main screen; «كيف يشتغل» keeps the process view** (1 Nov) | Mentor feedback: more care on UI/UX. The old first screen was a debugger. An agent needs a queue, one ticket, a draft to check and a quick way to decide. Friction follows risk: one key for a ready draft, one tick on the points to check for a flagged one, no draft for an escalation. |
| **The viewer defaults to `api`; the scripts stay on `cli`** (`app/server.py` `default_viewer_backend`; `config/models.yaml` `backend`) | The viewer is what a reader starts. On someone else's computer, cli would run pasted tickets on their own Claude Code login, with a setup no number was measured on. With no key, live runs are off and saved runs still replay. |
| **The decision log keeps no reply text; the server refuses a blocked approval** (`app/server.py` `decision_record`, `append_decision`) | The log is for measuring the pipeline, and a reply can carry a customer's details, so it keeps keyed hashes and a count of edited characters. An approved or edited reply that still has a blocking check (`asks_secret`; since 5 Nov also `hold_reason` and `sensitive_number`) gets 409, so a stale check in the page or a hand-made request can't pass it. |
| **`hold_reason` adopted: always on, and it blocks an approval** (5 Nov; `src/pipeline/draft_check.py` `findings`, `_hold_reason`; `app/server.py` `BLOCKING_CHECKS`) | A draft must not hint at an investigation, a suspicion, a report or money laundering: telling the customer is tipping off, which Iraq's AML/CFT Law 39/2015 forbids. «رفعنا بلاغ» and «سجلنا بلاغ بمشكلتك» stay flagged although they may only mean "we raised a ticket": a false alarm costs the agent an edit, and a miss is a legal breach. It fired on 0 of 2,531 saved drafts, so it costs nothing measurable. Decided for a regulated financial institution (LOG, 5 Nov). |
| **`sensitive_number` adopted: always on, and it blocks an approval** (5 Nov; `src/pipeline/draft_check.py` `findings`, `_sensitive_number`) | A draft must not repeat a card number or a code: the reply would put it in one more place, and repeating it back is poor card-industry practice. It fired on 0 of 2,531 saved drafts. Decided the same way. |
| **Blocked account or SIM change: a flag, not an escalation (`account_risk`)** (5 Nov; `src/pipeline/run.py` `ACCOUNT_RISK`, `process`; `app/static/js/labels.js` `CONFIRM_AR`) | Both are common steps in taking over someone else's account, so the agent confirms the customer's identity by the institution's own procedure before approving: approve waits for the tick «تأكدت من هوية الزبون». It replaces the 1 Nov `escalate_account_risk` flag, which escalated them with no draft. Their drafts were safe (they acknowledge and pass the ticket to the accounts team), so the draft is kept. The flag reads the type after the re-check, which removes the old flag's false positive (t2-0009: first model `sim_change` at 0.60, re-check `login_otp`). test2 review rate 19% → 26%; mvp_test 27% → 32% from its saved run, over the 30% target. Fraud is still escalated. Decided the same way. |

## 5. Feature flags

**Two are open (7 Nov): `summary_qualifiers`** (the escalation summary keeps the customer's qualifiers, in Arabic; it left 1 English word in 54 summaries, and the bar was 0) **and `draft_rules_r2`** (a revised drafter prompt from the second round of role-played test sessions; it removed the singular voice and the stiff words, but the judge's grades went down). The three flags opened by the 1 Nov security review are now normal code. They were decided on 5 Nov (section 4; LOG, 5 Nov), with no prompt change and no model call:
- `hold_reason` (no tipping off) and `sensitive_number` (no card number or code repeated back) always run, and both block an approval, in the inbox and at the server, as `asks_secret` does (`app/server.py` `BLOCKING_CHECKS`). «رفعنا بلاغ» and «سجلنا بلاغ بمشكلتك» stay flagged. Neither rule fired on any of 2,531 saved drafts.
- `escalate_account_risk` was changed into the `account_risk` flag: a blocked account or a SIM change keeps its draft, and the agent ticks «تأكدت من هوية الزبون» before approving. It reads the type after the re-check and never escalates. test2, replayed from the cache: 6 tickets flagged, all the right type, t2-0009 no longer caught; review rate 19% → 26%. mvp_test, from its saved run: 4 flagged, 27% → 32%, over the 30% target.
- `PIPELINE_FIXES` names nothing. Naming one of the three old flags is refused with what became of it (`src/pipeline/fixes.py` `ADOPTED`, `active`), and the viewer and `run_batch` refuse to start with one. On 7 Nov twelve more flags from the role-played test sessions were adopted the same way, after with/without runs, and five from their second round, then `style_notes` (LOG, 7 Nov entries); then, after the review before shipping, six more (`secret_forms_r3`, `ticket_rules_r3`, `draft_checks_r3`, `second_request_unknown`, `drafter_inputs_r3`, `security_line`); `summary_qualifiers` and `draft_rules_r2` are still flags.

**30 Oct, the first adoption.** On the author's word, the 13 adopted fixes became the normal code and every dropped one was deleted; `PIPELINE_FIXES` is now empty and the pipeline runs as measured. Proof: every prompt is byte-identical to the measured `mvp` configuration (a test pins the classifier prompt's hash), and replaying test2 through the response cache gave identical results on all 80 tickets (only app bugs' team, and so their draft, changed, by the author's routing choice).

Adopted on 30 Oct, now normal code: F2 draft checks, F3c draft from the re-check's answer, F6b separate fee call, F11 ask only for what's missing, F12 no promised specifics, F14b fraud consequence is not a second issue, F15 no word raises priority, F16 «ورقة» = 100 USD, F17 team note on escalations, F18 reference only when needed, F19 ≥ $750 raises priority, F20 duplicate payment = reversal, F21 one-line summary in the team note.

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
- **Logging every ticket to a spreadsheet:** discussed, not built. Run events and token/cost logging in `runs/` replaced it.
- **An Arabizi normalisation rule:** removed. It could corrupt real numbers, and Arabizi is rare.

## 7. Where things stand (7 Nov)

**Branches:** work happens on **`mvp`** and is merged into `main`. Since 30 Oct (8dfd12c, masking and the committed final run) they added the security hardening (76463d4), SECURITY.md and FAILURE_MODES.md (e4621cf), the agent inbox (36b843b) and its polish (d1280b6), the docs update (bfe8893), the 5 Nov adoption of the three safety rules (the commit after bfe8893) and the calmer inbox, then on 7 Nov the code-request check and the fixes from six role-played test sessions.

**Done:**
- [x] Pipeline, viewer, cli/api switch, response and prompt caching, cost logging and a spend cap
- [x] Experiment harness; 24 fixes tested with and without; 13 adopted as normal code, 11 deleted (30 Oct)
- [x] Data: dev 233, mvp_test 78, heldout 78 (Arabizi moved to `data/excluded/`), then test2 80 and heldout2 80 (sealed)
- [x] The author's checks: 34 dev labels (2 fixed), 30 test2 labels before the run, 13 drafts, 2 team notes
- [x] Thresholds calibrated on the API dev set: kept at 0.75 / 0.60
- [x] MVP runs, once each: mvp_test 77/78, heldout 77/78; final test test2 78/80, fraud 6/6, review 19%, $0.0027 per ticket
- [x] Adversarial set 14/14; all 389 earlier tickets 385/389
- [x] README, `docs/experiments/LOG.md`, `AUDIT-2026-10-29.md`, viewer screenshots in `docs/demo/` (nine, retaken on 7 Nov, after the review before shipping, as a fresh clone shows the page)
- [x] The one-page MVP update and the mentor deck (14 slides)
- [x] Saved batch runs mask long numbers by default (`mask_run` in `src/pipeline/clean.py`; `--no-mask` for scored synthetic sets)
- [x] The final test run is committed (`docs/runs/test2/final.json`): the viewer replays it from a fresh clone with no key
- [x] Security and reliability hardening (1 Nov, 76463d4, no model calls): local-only viewer with a token, input limits, kill switch (`PIPELINE_MODE`), real-data guard (`REAL_DATA=1`), bounded spending and retries, no error text in the page, wider masking, rewritten secret/time/promise checks, decision log (no reply text). test2 replays from the cache unchanged. Details: LOG.md, 1 Nov: Security and reliability hardening
- [x] SECURITY.md and FAILURE_MODES.md (1 Nov, e4621cf): what a regulated financial institution's security team would need to decide, with no compliance claim; eleven failure modes, with how often and what is left
- [x] The agent inbox (1 Nov, 36b843b) and its polish (d1280b6), no model calls:
  - «وضع الموظف» is the main screen: a queue in four tabs, one ticket with its facts underlined, the draft with its checks (run again on each edit through `POST /api/check`), and approve, edit, take over or forward, each with undo. «كيف يشتغل» keeps everything the old viewer showed.
  - The page writes the decision log (`POST /api/decision`). The server refuses (409) an approved or edited reply whose final text still has a blocking check.
  - Strict CSP with no `'unsafe-inline'`; fonts bundled under `app/static/fonts/` (OFL); no request to another host; `/static/` served by an allow-list.
  - Reviews: 53 findings on the inbox, then 16 in the polish. Each was reproduced first, then fixed (the 53 in full or in part).
  - The viewer now defaults to the API backend; the scripts still default to cli. A first-visit card explains the tabs.
  - Details: LOG.md, 1 Nov: The agent inbox
- [x] The three safety rules adopted (5 Nov, no model calls; LOG.md, 5 Nov: Three safety rules adopted):
  - `hold_reason` and `sensitive_number` always run and block an approval; «رفعنا بلاغ» and «سجلنا بلاغ بمشكلتك» stay flagged. 0 of 2,531 saved drafts flagged by either.
  - `account_risk`: a blocked account or a SIM change keeps its draft and needs the identity tick «تأكدت من هوية الزبون»; read after the re-check, never an escalation. Fraud unchanged.
  - test2, replayed from the cache with 0 misses: type 78/80, priority 79/80, fraud 6/6, all prompts identical; 6 tickets drafted → flagged, all the right type; t2-0009 no longer caught; review rate 19% → 26%. mvp_test, from its saved run: 27% → 32%, over the 30% target.
  - mvp_test and dev cannot be fully replayed from the cache: 10 app-bug drafts (and their summaries) are missing since the 30 Oct routing change.
  - The review of the adoption (14 findings, LOG.md 5 Nov, "Review"): the viewer gives saved runs the flag (the final run shows 15 / 6 / 59); the tick is logged and the server refuses an approval without it; an agent's correction to either type asks for it; an escalation of either type has the reminder in its team note; clearer Arabic wording.
- [x] Six role-played test sessions with live model calls (7 Nov; LOG.md, 7 Nov: Role-played test sessions): 70 live tickets for about $0.23, 43 confirmed issues (7 high). The viewer and server fixes were made directly; the pipeline fixes were 13 flags measured with and without, and 12 were adopted. Fixes cost $1.40 in API calls.
- [x] Before the second round of test sessions (7 Nov, no model calls; LOG.md, 7 Nov: Before the second round of test sessions): the viewer serves a saved run with today's draft-check flags and text rules, for the rules that need no model call (the final run shows 21 / 6 / 53); «كيف يشتغل» hides a card number or code the customer wrote, as the inbox does; `claims_done` also catches «مسجل عندنا» (something said to be on record with us).
- [x] Second round of role-played test sessions (7 Nov; LOG.md, 7 Nov: Second round of role-played test sessions): five sessions came back, 54 live tickets for $0.19. Of 41 issues re-checked, 24 fixed, 16 partly, 1 not (T08). 36 new issues confirmed (6 high). The page and server fixes were made directly: the team note hides a typed code, hyphenated numbers read in order, every point must be ticked (the server checks the pipeline's points; the draft warnings' ticks from the review before shipping on), a fraud forward to another team needs a tick, blank lines, the phone toast, direction. The draft checks were extended and measured on the saved drafts (no new false alarm in the blocking checks; two new warnings, `persona_slip` and `asks_given`). Five flags adopted (`secret_forms`, `complaint_reasons`, `device_lost_negation`, `second_request_flag`, `drafter_inputs_r2`); `draft_rules_r2` not adopted (the judge's grades went down). The final run then showed 31 / 6 / 43. Fixes cost $0.83 in API calls.
- [x] Style notes, not ticks (7 Nov, no model calls; LOG.md, 7 Nov: Second round, "Style notes, not ticks"): `dialect_words` and `persona_slip` (a stiff or non-Iraqi word, a singular voice) are style points, not risks, so they no longer flag a ready draft or ask for a tick (`style_notes`, adopted after with/without runs). They still run and are highlighted, and the page says them in one muted line under the draft; the server refuses a tick of one. Measured cache-only: review rate dev 99 → 64 of 233, test2 37 → 26 of 80, mvp_test 44 → 32 of 78; every ticket that moved had only style findings, and no other flag, check, team or priority changed. The final run now shows 20 / 6 / 54.
- [x] Review before shipping (7 Nov; LOG.md, 7 Nov: Second round, "Review before shipping"): 54 issues reproduced and fixed (6 high), except a few left open there. The server checks every tick an approval of the reply as served needs, and refuses ticks that never applied; the draft box deletes, undoes and copies as the agent expects; a typed code stays hidden in a live ticket and the queue row. Six flags measured with and without, all adopted: `secret_forms_r3`, `ticket_rules_r3`, `draft_checks_r3`, `second_request_unknown` (cache-only: no outcome moved on any set, only style notes added) and `drafter_inputs_r3`, `security_line` (the drafter quotes the customer's amount only when the words read as it, and is told what to advise on a typed secret; 20 live re-drafts, $0.047).
- [x] Tests: 2,238 pytest tests pass (no model calls); the browser smoke script `tests/ui/smoke.cjs` passes 591/591 checks

**Open:**
- [ ] Unknown charges: they stay with the fraud team; the author is unsure, and the mentor notes (section 8) record no answer. FAILURE_MODES.md (mode 4) leaves the decision to the deploying institution, with its fraud team.
- [ ] The author's user-research notes from support staff (still open). No agent has used the inbox yet (the 7 Nov test sessions were role-played), so the decision log and the session summary hold no human data. Drafts rated by people and agent minutes per ticket wait on this.
- [x] The one-page update ("Support Pipeline Automation: MVP Update") refreshed on 1 Nov: the inbox and security section with a screenshot, known limits and next steps
- [ ] heldout2, run once on this final version: the next run
- [ ] The review rate with `account_risk`: 32% on mvp_test (from its saved run), over the 30% target; by today's rules (the 7 Nov draft warnings too) test2 33% and mvp_test 41% on their saved drafts, 30% and 36% with the current drafter; heldout2 will show it on fresh tickets
- [ ] What `account_risk` does not cover: a ticket whose re-check moved the type away (mvp-0046) gets no identity reminder unless the agent picks the first model's answer; the tick is the agent's word (the server requires it and the log records it, but nothing checks that identity was verified) (SECURITY.md section 11)
- [ ] Submission before 17 Nov

## 8. Next steps, in order

**Mentor feedback (Sun 1 Nov, 1-on-1 call; no slides were used):**
- Care more about **functionality, security and UI/UX**.
- Care about **the process more than the results**.
- Images and videos in tickets: yes, but **not in the MVP**. List them under future plans.
- Ask for help whenever needed.

Done since the call (section 7): the security hardening, the agent inbox and its polish, SECURITY.md and FAILURE_MODES.md, (5 Nov) the three flags decided, and (7 Nov) the fixes from six role-played test sessions.

1. **heldout2** (80, sealed): the next run, once, on this final version. Before it, the author decides whether to run the small fraud-worded probe set that FAILURE_MODES.md (mode 3) proposes (about $0.05).
2. **User research (still open):** the author's notes on the conversations already held with support staff (role, when, what they said); then, if possible, a few support staff try the inbox on the final run. Note what slows them down or confuses them; the decision log records each decision without reply text.
3. Any pipeline change gets a with/without test on dev.
4. Submit before **17 Nov**: repo, write-up (organised around the process), demo.

**Future plans (not in the MVP):** images and videos in tickets (screenshots of an error or a receipt, voice notes).

Known limits to state in the write-up: tickets and most labels are model-written (64 checked by the author); one model family writes, runs and grades; no support agent has used the inbox yet, so draft quality as agents see it, time saved and how carefully agents review are not measured; the drafter sometimes misses asking for a shop or agent name (F11b, the fix tried, made drafts worse); unknown charges go to the fraud team; blocked-account and SIM-change tickets need an identity tick that the tool cannot check, and it raises the review rate (mvp_test 32%, over the 30% target; by today's rules test2 33% and mvp_test 41% on their saved drafts, 30% and 36% with the current drafter); masking covers numbers and codes but not names, and the response cache (development only) keeps replies in full.

## 9. How to run

```bash
pip install -r requirements-dev.txt                       # adds pytest to requirements.txt
env -u SUPPORT_PIPELINE_API_KEY -u ANTHROPIC_API_KEY python -m pytest -q   # 2,238 tests, no model calls
python app/server.py                                      # viewer: http://localhost:8000, API backend by default
node tests/ui/smoke.cjs                                   # browser smoke test: 591 checks, several minutes
LLM_BACKEND=cli python scripts/run_batch.py ...            # dev runs on the Pro plan
python scripts/experiment.py run <config> --set <file> [--backend api]
python scripts/generate_tickets.py stats                  # dataset tables, never ticket text
python scripts/generate_tickets.py repair --split dev --dry-run
```

- **The viewer** runs new tickets on the API backend unless `LLM_BACKEND` says otherwise (`app/server.py` `default_viewer_backend`). With no key, live runs are off, the page says why, and saved runs still replay: it opens on the committed final run (`docs/runs/test2/final.json`). With a key, a pasted ticket runs the measured configuration under the spending cap. Decisions go to `runs/decisions.jsonl` (git-ignored; `DECISIONS_FILE` moves it).
- **`LLM_BACKEND=cli` is for development scripts only.** It is the scripts' default (`config/models.yaml` `backend`). Every pipeline run behind a reported number, and the thresholds, used `LLM_BACKEND=api`. The draft judge runs on cli (section 4).
- **The smoke script** starts its own viewers with no key, so it calls no model. It needs Node with Playwright and its Chromium ([`tests/ui/README.md`](tests/ui/README.md)).
- **Safety switches:** `PIPELINE_MODE=off` stops every model call; `REAL_DATA=1` refuses the development paths. Details: SECURITY.md.

## 10. Map of the repo

| Path | What |
|---|---|
| `src/pipeline/` | `clean`, `classify`, `gate`, `route`, `draft`, `draft_check`, `handoff` (F17), `requirements` (F18), `run`, `llm`, `fixes`, `config` (limits, kill switch) |
| `config/` | `taxonomy.yaml`, `thresholds.yaml` (also the input `limits`), `models.yaml` (backend, kill switch `mode`, spending cap, prices), `policy.yaml` (empty on purpose) |
| `scripts/` | `experiment.py` (with/without runs, judge, pooling), `calibrate.py` (gate replay), `review_sheet.py`, `generate_tickets.py` (build / repair / handcheck / stats), `run_batch.py`, `run_probes.py` |
| `data/` | `dev`, `mvp_test`, `heldout`, `test2`, `heldout2` (sealed); `excluded/` (Arabizi); `probes/` (older sets, adversarial_14); `review/` (the author's checks) |
| `docs/experiments/` | `LOG.md` (all results, newest first), `AUDIT-2026-10-29.md`, per-set summaries |
| `docs/runs/`, `docs/demo/` | the committed final run (`test2/final.json`); the nine viewer screenshots |
| `app/server.py` | the viewer's server: local only, a token per process, security headers, the `/static/` allow-list; `POST /api/stream` (a live run), `/api/check` (the draft checks on an edit), `/api/decision` (the decision log) |
| `app/static/` | `index.html` (markup only, no inline code); `css/app.css`; `js/` (ES modules: `inbox.js` the agent inbox, `process.js` «كيف يشتغل», `main.js`, `state.js` and helpers); `fonts/` (IBM Plex Sans Arabic and IBM Plex Mono, OFL; `SOURCE.txt` has each file's sha256) |
| `tests/` | pytest suites (no model calls); `tests/ui/` the browser smoke script `smoke.cjs` and its README |
| `SECURITY.md` | for a regulated financial institution's security team: what leaves the machine, the controls, what the institution would still have to do. No compliance claim. |
| `FAILURE_MODES.md` | eleven failure modes: how often, how each was found, what was done, what is left |
| `HANDOVER.md` | the full experiment report from the other session (20–23 Oct) |
| `runs/` | git-ignored: batch and experiment runs, and the decision log (`decisions.jsonl`) |
