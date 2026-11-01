# Security

For a regulated financial institution's security team deciding whether this could be connected to its systems, and for the challenge judges. It says what the code does, what it does not do, and what the institution would still have to do. It claims compliance with no framework.

## In short

- **What it is.** An MVP that has only processed synthetic tickets, on one computer. A person approves, edits or takes over every ticket, and nothing is sent to a customer. It is not fit today for real tickets.
- **What leaves the machine.** The full ticket text, including any card number or code the customer typed, goes to the Anthropic API. Inference runs in the US or "global", storage at rest is in the US, and no option keeps either in Iraq. Plan on 30-day retention unless zero data retention is signed (section 5).
- **What the code refuses.** `REAL_DATA=1` refuses the development paths: a personal login, an unmasked cache, any other endpoint. `PIPELINE_MODE=off` stops every model call. The guard is opt-in: by default the tool runs in development mode (section 1).
- **Top residual risks.** Fraud handling rests on one model's label. Names are never masked. There is no user sign-in. A live run leaves no record that a ticket was sent out, apart from a decision line if the agent decides on it. Data residency is an open legal question. All assurance so far is in-house and AI-generated.
- **What the institution decides first.** Permission to disclose Restricted data, DLP, a legal basis and a transfer impact assessment (section 4). Then a shadow pilot (section 2).
- **Check it yourself.** Section 1 has commands that need no key and call no model.

**How to read this page**
- **References.** Every `file:line` points to commit `d1280b6` (1 Nov 2026, the agent inbox with its polish). The function, setting or constant is named beside each code reference, so it can be found after lines move. Tests are `tests/<file>::<name>`. Browser checks are quoted by the label that `tests/ui/smoke.cjs` prints.
- **Short file names.** `run.py`, `llm.py`, `clean.py`, `gate.py`, `route.py`, `draft.py`, `draft_check.py`, `handoff.py`, `config.py`, `schemas.py`, `fixes.py` and `prompts/` are in `src/pipeline/`. `server.py` is `app/server.py`, and `util.js`, `state.js`, `inbox.js` and `composer.js` are in `app/static/js/`. `run_batch.py` is `scripts/run_batch.py`. `LOG.md` and `AUDIT` (`AUDIT-2026-10-29.md`) are in `docs/experiments/`.
- **Evidence.** Every claim is backed by a file and line, a test, an entry in [`docs/experiments/LOG.md`](docs/experiments/LOG.md), or a public source with its URL. Anything marked *(inference)* is a reading, not a stated fact. Quotes from Arabic-only texts are unofficial translations, made with the coding assistant.
- **Related pages.** Measured failures: [FAILURE_MODES.md](FAILURE_MODES.md). Who made what: [DISCLOSURE.md](DISCLOSURE.md).
- **Sources** were read between 30 Oct and 1 Nov 2026. The Anthropic pages were fetched again on 1 Nov 2026.

## 1. Status

It has only ever processed **synthetic tickets**: "No real customer data is used anywhere" (`README.md:113`). It runs on one computer (`server.py:1069-1070`, `make_server`, bound to 127.0.0.1).

- **Intended today only for:** demos and evaluation on synthetic data, and a design review like this one.
- **Not fit today for:** real customer tickets, use by more than one person, or any connection to production systems.
- **Before any real ticket:** the decisions in section 4, the actions in section 8, and a pilot like the one in section 2.

**The real-data guard is opt-in.** With `REAL_DATA` unset, the tool runs in development mode and every refusal is skipped (`llm.py:102-105`, `real_data`; `:120-121`, `assert_real_data_safe`).
- The scripts' default backend is `cli`, the author's personal Claude Code login (`config/models.yaml:10`, `backend`). The viewer defaults to `api` instead (`server.py:399-409`, `default_viewer_backend`). With no key it runs no live tickets (`server.py:423-424`, `live_status`), and `LLM_BACKEND=cli` has to be set to use a Claude Code login (`test_server_security.py::test_viewer_backend_default_is_the_api_unless_llm_backend_is_set`, `::test_viewer_keeps_an_explicit_cli_backend`).
- The unmasked response cache and `--no-mask` are allowed.
- Nothing in the code detects that a ticket is real. Only procedure stops a real ticket being pasted into a development setup (section 8, Access).

**Who has checked this.** All assurance so far is in-house. The author states that the coding assistant wrote most of the code and tests, and that the 1 Nov security review and the reviews of the agent inbox (including its security and privacy lens, `LOG.md:67`) were run by AI agents through it (DISCLOSURE.md, section 3). The adversarial set is 14 tickets, run once (`AUDIT:27`). No review of the code or the controls by anyone outside the project is recorded.

**Checked on 1 Nov 2026 with no model calls:**

| Check | Result |
|---|---|
| `python -m pytest -q`, with API keys removed | all pass: 648 at `d1280b6` (`LOG.md:100`), and 648 again when this page was updated |
| `node tests/ui/smoke.cjs`: the page in Chromium through Playwright, with no key and no model call | 359/359 checks over five passes: desktop and phone, light and dark, and a fresh clone (`LOG.md:100`) |
| Secret patterns in the whole git history (command below) | 0 |
| `pip-audit`, run once on 1 Nov in a scratch environment with `requirements-dev.txt` installed (`LOG.md:118`) | No known vulnerabilities found. The bounded ranges can resolve to newer versions that were not scanned. The inbox added no Python package. |

**Measured earlier on the API, once each:**

| Check | Result |
|---|---|
| 14 adversarial tickets, 29 Oct, $0.04 (`data/probes/adversarial_14.jsonl`) | 14/14 handled as expected (`AUDIT:27-45`) |
| Fraud tickets escalated, none drafted | 28/28 on dev, mvp_test and heldout, 29 Oct (`README.md:21`); 6/6 on test2, 30 Oct (`README.md:16`) |

**Check it yourself (no key, no model calls).** From the repo root:

```bash
# Every test, with any API key removed. Expect: all pass.
env -u ANTHROPIC_API_KEY -u SUPPORT_PIPELINE_API_KEY python -m pytest -q

# The page in a real browser. Needs Node with Playwright and its Chromium, and takes a few minutes.
# Each pass starts its own viewer and removes the key variables first. Expect: every check passes.
node tests/ui/smoke.cjs

# Common secret patterns in the whole git history. Expect: 0.
# (The brackets stop the pattern from matching this page.)
git log -p --all | grep -c -E 'sk-[a]nt-|AKIA[0-9A-Z]{16}|gh[p]_[A-Za-z0-9]{20}|BEGIN [A-Z ]*PRIVATE KEY'

# Known vulnerabilities in the runtime packages (needs network).
# Expect: no known vulnerabilities, as on 1 Nov (a new advisory can change this).
pip install pip-audit && pip-audit -r requirements.txt

# The viewer refuses other callers. With the pipeline off, no key is needed.
# DECISIONS_FILE keeps the last command away from your own decision log.
DECISIONS_FILE="$(mktemp)" PIPELINE_MODE=off PORT=8791 python app/server.py &
curl -s -o /dev/null --retry-connrefused --retry 20 --retry-delay 1 http://127.0.0.1:8791/   # wait for the viewer to start
curl -s -o /dev/null -w '%{http_code}\n' -H 'Host: attacker.test' http://127.0.0.1:8791/api/meta            # expect 421
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8791/api/meta                                      # expect 403 (no token)
curl -s -o /dev/null -w '%{http_code}\n' -H 'Origin: https://attacker.test' http://127.0.0.1:8791/api/meta   # expect 403
curl -s -D - -o /dev/null http://127.0.0.1:8791/ | grep -i '^content-security-policy'   # expect no 'unsafe-inline'
curl -s -o /dev/null -w '%{http_code}\n' --path-as-is http://127.0.0.1:8791/static/../server.py              # expect 404

# The page's token, then an edit re-checked, then an approval of a reply that asks for the code.
TOKEN=$(curl -s http://127.0.0.1:8791/ | sed -n 's/.*name="viewer-token" content="\([^"]*\)".*/\1/p')
curl -s -H "X-Viewer-Token: $TOKEN" -H 'Content-Type: application/json' \
  -d '{"draft":"دزلنا الرمز اللي وصلك","allowed_text":""}' http://127.0.0.1:8791/api/check        # expect asks_secret
curl -s -o /dev/null -w '%{http_code}\n' -H "X-Viewer-Token: $TOKEN" -H 'Content-Type: application/json' \
  -d '{"run":"saved/test2/final","ticket_id":"t2-0001","action":"approved","pipeline_outcome":"drafted","seconds":5,"final_text":"دزلنا الرمز اللي وصلك"}' \
  http://127.0.0.1:8791/api/decision                                                             # expect 409
kill %1
```

## 2. A pilot the institution could approve

*A suggestion (inference). Nothing here has been run.* The controls it relies on are in `d1280b6`: `REAL_DATA`, `PIPELINE_MODE`, the spending cap, the decision log, and the agent inbox that writes to it (section 7). No agent has used the inbox yet, so the log holds no human data (`LOG.md:59`).

| Part | Suggested |
|---|---|
| Host | One institution-managed computer with full-disk encryption, run by one named analyst. Not a personal laptop. |
| Settings | The service definition sets `REAL_DATA=1`, `LLM_BACKEND=api` and `PIPELINE_MODE=classify_only`. It injects the API key and `DECISIONS_HASH_KEY` from the vault. No `.env` file on the host (section 3). |
| Provider | A dedicated Anthropic organisation, with the ZDR decision taken, `allowed_inference_geos` set and an account spending limit (section 5). |
| Stage 1: shadow, no drafts | A sample of tickets approved for disclosure under section 4. Nothing is written to the ticketing system or sent. Types, teams and priorities are compared with what agents actually did. |
| Stage 2: shadow, with drafts | `PIPELINE_MODE=full`. Drafts are shown to the analyst only, in the inbox. Each approve, edit, take-over or forward goes to the decision log. Still nothing is sent. |
| Exit criteria | Stage 1: fraud tickets (as the fraud team decided) that the pipeline did not escalate: 0; type agreement with the agents' own types. Stage 2: review rate at or below 30% (`README.md:17`); wrong type among ready drafts; every draft flagged for asking for a code, or (if switched on) for mentioning an investigation, read by a person; edit and override rates per type, from the decision log. |
| Stop and owner | The triggers in section 10. The accountable owner named under section 8 signs off each stage. |

## 3. Data flow

From a ticket arriving to an agent's decision:

| # | Step | Runs on | What it sees | Leaves the machine |
|---|---|---|---|---|
| 1 | Ticket arrives: a batch file (`run_batch.py`) or pasted into the local viewer (`POST /api/stream`) | this computer | full text | nothing |
| 2 | Clean: digits and spaces normalised (`run.py:261`, `process`) | this computer | full text | nothing |
| 3 | Limits and kill switch. Over 4,000 characters, or `PIPELINE_MODE=off`: the ticket goes to a person, with no model call (`run.py:267-271`, `process`) | this computer | full text | nothing |
| 4 | Classify and extract, Haiku (`run.py:276`, `process`) | Anthropic API | full text between `<ticket>` tags, plus the taxonomy | **full ticket text** |
| 5 | Confidence gate: rules (`gate.py:44`, `check`) | this computer | the extraction | nothing |
| 6 | Re-check, Sonnet, only when unsure or high-risk (`run.py:310-313`, `process`) | Anthropic API | full text; it does not see the first answer | **full ticket text** |
| 7 | Fee call, Haiku, on fee tickets only (`run.py:348-351`, `process`) | Anthropic API | full text | **full ticket text** |
| 8 | Route and priority: rules on the model's type and amount (`route.py:15-29`, `route`) | this computer | the extraction | nothing |
| 9 | Draft, Sonnet (`run.py:375`, `process`), then rule checks on the draft (`run.py:381-383`) | Anthropic API, then this computer | full text, extracted fields, team, policy facts (empty) | **full ticket text** |
| 10 | Escalated tickets, fraud included: a team note built by code (`handoff.py:86`, `note`), plus a one-line summary from Haiku (`run.py:227-231`, `finish` in `process`). Tickets the system escalates itself (too long, switched off, drafts off) get no summary call. | Anthropic API for the summary | full text | **full ticket text** |
| 11 | The agent decides in the inbox: approve, edit, take over or forward (`POST /api/decision`). An edit is checked again by the same draft rules (`POST /api/check`). | this computer | the result, and the agent's edit | nothing |

**What leaves the machine:**
- **The full ticket text, as the customer wrote it.** That includes names, phone, account and card numbers, and any code the customer typed. Nothing is masked before sending (section 11).
- **How often:** about 2.3 calls per ticket (180 model calls for the 80 test2 tickets, `LOG.md:128`).
- **One ticket per call.** Each model call carries one ticket (`run.py:276`, `:313`, `:351`, `:375`, `:231`, all in `process`). No ticket's text is in another ticket's prompt. The prompt cache marks only the fixed system prompt (`llm.py:246`, `_call_api`).
- **Fraud tickets too.** They are classified, and get a model-written summary line, before a person sees them. They get no customer draft.
- **Where it goes:** under `REAL_DATA=1`, only to `https://api.anthropic.com` (`llm.py:125-128`, `assert_real_data_safe`).
- **The page itself** sends nothing to another host: no fonts, scripts or styles from outside, and `connect-src 'self'` (section 7).

**Where inference runs:**
- The code sends no `inference_geo` (`llm.py:243-249`, `_call_api`), so the Anthropic workspace's default applies. That is `global` unless the workspace was set up otherwise.
- Anthropic offers two inference locations. `us` keeps inference in the US. `global` "may run in any available geography". Storage at rest is US-only: "Workspace geo: Only `"us"` is currently available" ([data residency](https://platform.claude.com/docs/en/manage-claude/data-residency)).
- **No option keeps processing or storage in Iraq.**
- When the API reports `usage.inference_geo`, the code records it (`llm.py:256-257`, `_call_api`). The committed final run predates this, so it has no record of where it ran.

**What is saved:**

| Store | What it holds | Protection |
|---|---|---|
| Input batch file, supplied by the institution (`README.md:67`) | full ticket text, unmasked | **None from the tool.** It neither creates nor protects this file. Delete it after the run. |
| Batch run file, `runs/<time>-<set>-<backend>.json` (`run_batch.py:123`, `:143`, `main`) | ticket text, every prompt, every model reply, drafts, team notes, token counts | Masked by default (`clean.py:205-225`, `mask_for_logs`, `mask_run`). Numbers of 7 or more digits keep only their first and last two digits. Card numbers are masked, and so is a code written after a code word. **Names are not masked.** Owner-only (0600) under `REAL_DATA=1` (`run_batch.py:152`, `save`). Git-ignored (`.gitignore:17`). |
| Decision log, `runs/decisions.jsonl`, written by the inbox (`server.py:585-642`, `decision_record`; `:672-698`, `append_decision`) | Per decision: UTC time, reviewer, run, ticket id, action, pipeline outcome, flags, reason codes, seconds, visits, corrections, the warning kinds the agent ticked, model ids, keyed hashes of the two system prompts and of the draft and final reply, the number of edited characters, and for an undo the decision it takes back | **No draft or reply text.** HMAC-SHA256 hashes (`server.py:530-537`, `_HASH_KEY`, `_sha256`). Owner-only (0600) (`server.py:695`, `append_decision`). |
| The agent's browser, `localStorage` | one entry with five preferences: the mode, whether single-letter shortcuts are on, whether the "why" panel is open, the run on screen, and whether the first-visit card was closed (`util.js:231-255`, `loadPrefs`, `savePrefs`) | No ticket text, drafts, edits or ticks. Those stay in the page's memory (`state.js:1-2`). |
| A `.env` file, if someone creates one (looked for from `src/pipeline/` upward, so the repository folder counts) | the API key and any other setting | **Plain text on disk.** `llm.py` loads it at import (`llm.py:54`, `:58`), and the no-key error suggests creating it (`llm.py:217-219`, `_get_client`). Git-ignored (`.gitignore:2-4`), which only keeps it out of git. |
| stderr | an error's type and stack | Under `REAL_DATA=1`, no error message (`run.py:86-94`, `_log_error`; `server.py:725-733`, `_log_exception`) |
| `docs/runs/test2/final.json` (committed) | the measured synthetic final run, unmasked, so the viewer can replay it without a key | Synthetic data only |

**What is never saved:**
- **Live viewer runs.** The ticket, prompts and replies go to the page and are not written to disk (`server.py:750-769`, `_work`). If the agent decides on a live ticket, the decision log gets a line with run `live` and no text. Otherwise nothing local records that the ticket was sent to the provider. A batch run does: its run file lists every ticket.
- **Request logs.** The viewer logs no requests (`server.py:795-796`, `log_message`).
- **The agent's edits.** `POST /api/check` logs and keeps nothing (`server.py:1037-1049`, `_post_check`), and the page holds edits in memory only.
- **The API key, by the code.** It is read from the environment (`llm.py:206-208`, `api_key`), never logged, and never put in a prompt. A `.env` file, if used, holds it in plain text (table above).
- **Exception messages.** They never reach the page or a run file (`run.py:80-83`, `_error`; `server.py:863-873`, `_handle`).
- **The response cache under `REAL_DATA=1`.** The cache keeps replies in full, and the guard refuses it (`llm.py:129-133`, `assert_real_data_safe`).

## 4. Data classification and the decision to send tickets out

**How the Central Bank of Iraq (CBI) classifies this data.** The CBI Cyber Resilience Controls for the financial and banking sector define four levels: Public, Restricted, Confidential and Top Secret ([CBI, Identify 4, printed pp. 19-23](https://cbi.iq/static/uploads/up/file-171939658616261.pdf)).

- **Restricted** includes information "relating to the personal information of persons protected under any regulation" (p. 19). Ticket text is therefore at least Restricted *(inference: the institution may classify it higher)*.
- "Restricted information may not be disclosed except after obtaining formal permission from the institution" (p. 22).
- Restricted information may be stored only on the institution's devices, or on external devices it has authorised, "such as those used by third parties or cloud service providers" (p. 20).
- "Information leakage prevention controls must be applied and implemented on restricted information" (p. 21).
- **If the institution classifies ticket text as Confidential,** the same table says such information must be stored "only on the institution's own information assets and technologies" (p. 20). Sending tickets to an external model would then likely not be allowed *(inference)*.

| Data | Level *(inference)* | Goes to the model provider | Kept on this computer |
|---|---|---|---|
| Ticket text (names, phone, account and card numbers, codes) | Restricted or higher | yes, in full | input file; run files, numbers masked |
| Extracted fields (reference, phone, amount, date) | Restricted | yes, in the draft prompt | run files, long numbers masked |
| Drafts and team notes | Restricted (they repeat ticket facts) | they are model output | run files, masked |
| Decision log | Restricted (reviewer and ticket ids; no text) | no | `runs/decisions.jsonl` |
| Prompts, taxonomy, policy file | Public as published here (a filled-in policy file is the institution's to classify) | yes | in git |
| API key | a secret, under the institution's secrets policy | it authenticates the calls | environment, or a `.env` file if one is used |

**Sending real tickets to an external model is the deploying institution's decision.** This repository cannot make it. Before any real ticket goes out, the institution needs:

1. **Formal permission to disclose Restricted data**, given by the institution itself (CBI Identify 4, above).
2. **Data leakage prevention (DLP) on the path to the model endpoint** (CBI Identify 4, above).
3. **A legal basis, and an updated customer privacy notice if needed.**
   - Under Anthropic's Commercial Terms, the customer "represents and warrants that it has all rights and permissions required to submit Inputs" (L.1) and must comply with "any applicable data privacy laws" (D.1) ([terms](https://www.anthropic.com/legal/commercial-terms)).
   - The CBI Regulation of Financial Consumer Protection requires "precise control systems" to keep consumer data confidential (Chapter Two, Sixth) ([regulation](https://cbi.iq/static/uploads/up/file-173633457125732.pdf)).
4. **A transfer impact assessment.** Anthropic's DPA bases transfers on the EU Standard Contractual Clauses (I.1). It offers information "reasonably necessary for Customer to complete a transfer impact assessment" (I.4) ([DPA](https://www.anthropic.com/legal/data-processing-addendum)).

**Data residency is an open legal question, and this document does not resolve it.**
- A 2018 CBI notice requires certain licensed providers to process and keep their data "within its centers inside Iraq exclusively" ([CBI notice](https://cbi.iq/static/uploads/up/file-152404847844462.pdf); the PDF metadata dates it 18 Apr 2018).
- The open points are whether the notice applies to a given institution, whether it covers support-ticket text sent out for inference, and whether it has been changed since.
- These are for the institution's legal and compliance team. No Anthropic option keeps the data in Iraq (section 3).

## 5. Vendor facts: Anthropic API

| Topic | What the source says | Source |
|---|---|---|
| Training | "Anthropic may not train models on Customer Content from Services." (Section B) | [Commercial Terms](https://www.anthropic.com/legal/commercial-terms), effective 17 Jun 2025 |
| Standard retention | For API users, inputs and outputs are deleted "within 30 days of receipt or generation", unless agreed otherwise, for example under zero data retention. The API docs refer readers to this article for standard retention. Covered Models (Claude Fable 5.1, Mythos 5.1, Fable 5 and Mythos 5) need 30-day retention; the Haiku 5.5 and Sonnet 5.5 used here are not among them. **Plan on 30 days unless ZDR is signed.** | [Privacy Center article](https://privacy.claude.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data); [API and data retention](https://platform.claude.com/docs/en/manage-claude/api-and-data-retention) |
| Zero data retention (ZDR) | By arrangement with Anthropic, enabled per organisation. Under ZDR, Anthropic "does not store customer prompts or responses at rest after the API response is returned". Eligible: the Messages API, prompt caching, effort. Not eligible: the Batch API (29-day retention) and the Files API. The pipeline uses only the Messages API, a 5-minute prompt cache and `effort` (`llm.py:243-249`, `_call_api`). **Keep it that way:** do not move to the Batch or Files APIs. | [API and data retention](https://platform.claude.com/docs/en/manage-claude/api-and-data-retention) |
| Flagged content | Even under ZDR: "if a chat or session is flagged, Anthropic may retain inputs and outputs for up to 2 years." The Privacy Center adds that trust-and-safety classification scores are kept up to 7 years. | both pages above |
| Data Processing Addendum | Breach notice "without undue delay, but in any event within 48 hours" (G.1). New subprocessors: 15 days to object (C.3). Annual external audits, with a SOC 2 report on request (F.1). Customer audit at most once in 12 months, unless a regulator requires one (F.2(c)). Deletion within 30 days of termination (H.1). AES-256 at rest and TLS 1.2+ in transit (Schedule 2, E). No clause on government or law-enforcement access requests was found. | [DPA](https://www.anthropic.com/legal/data-processing-addendum), effective 24 Feb 2025 |
| Inference location | `global` (the default) or `us` (1.1× the price). Storage at rest is `us` only. A workspace can restrict locations with `allowed_inference_geos` and set `default_inference_geo`. | [data residency](https://platform.claude.com/docs/en/manage-claude/data-residency) |

## 6. Threat model: OWASP Top 10 for LLM Applications (2025)

Source: [OWASP GenAI](https://genai.owasp.org/llm-top-10/). The pipeline uses no retrieval, no tools and no fine-tuning, so some items barely apply. Controls named here are detailed, with file and test, in section 7. The residual risk is an assessment *(inference)* for real tickets, before the institution's own controls.

| ID | The risk here | What the code does | Test | What remains | Residual |
|---|---|---|---|---|---|
| **LLM01** Prompt injection | Customer text is in every prompt. It may try to change the type, team or priority, win a promise, or forge "facts". | Every prompt says the ticket is data (`prompts/classify_system.md:5-6`, `draft_system.md:13`). A `<ticket>` tag typed by the customer is neutralised (`clean.py:53`, `neutralise_tags`). Team and priority are rules on the model's type and amount (`route.py:15-29`, `route`): no urgency word changes them, but a ticket that steers the type, or plants an amount, can. Fraud is escalated by a rule on the model's label (`gate.py:58-62`, `check`). A draft may take a time only from the policy facts (`draft_check.py:208-215`, `_promise`). | `test_text_rules.py::test_prompts_neutralise_tags_and_keep_plain_tickets_byte_identical`, `::test_a_forged_facts_line_inside_the_ticket_allows_nothing`; `test_pipeline.py::test_no_word_raises_priority_but_amount_does`; adversarial set 14/14 (`AUDIT:27-45`) | Injection tickets got the right type on 8 of 9 (`AUDIT:15`). In t2-0041 the type moved, but the injection failed (`LOG.md:230`). A fraud ticket that the model labels as an ordinary type is not escalated ([failure mode 3](FAILURE_MODES.md#3-a-risky-ticket-rests-on-one-models-label)). A model-extracted reference reaches the drafter prompt outside the ticket tags (section 11). See also [failure mode 7](FAILURE_MODES.md#7-instructions-planted-in-a-ticket). | Medium; High for a fraud ticket steered to an ordinary type |
| **LLM02** Sensitive information disclosure | Tickets hold personal and card data. It goes to the provider and into saved files, and a draft could repeat a card number or code. | Masking of saved runs, no request log, no error text, and the real-data guard (section 7). The decision log is written by the inbox, and a line still holds no text. `/api/check` logs and keeps nothing, and the page keeps edits in memory, with only five preferences in `localStorage` (section 7). Sealed test sets are never served (`server.py:249-275`, `_index`, `run_file`). | `test_text_rules.py::test_mask_hides_separated_numbers_and_codes`; `test_server_security.py::test_decision_is_logged_with_hashes_and_never_the_text`, `::test_crash_log_under_real_data_has_no_message`; `test_server_ui.py::test_check_never_logs_or_stores_the_text`; `test_viewer_page.py::test_only_preferences_go_to_local_storage` | The full text, names included, goes to the provider. Names are never masked. The drafter is told to mention the reference the customer gave (`draft_system.md:16`), so a card number extracted as a reference would be repeated. `sensitive_number` is off. See [failure mode 8](FAILURE_MODES.md#8-numbers-codes-and-names-leave-the-pipeline-unmasked). | High |
| **LLM03** Supply chain | A compromised package, endpoint or model. | 4 runtime packages with upper version bounds (`requirements.txt`). pip-audit clean on 1 Nov (section 1). The real-data guard pins the endpoint and refuses other providers (section 7). Model ids are in one file (`config/models.yaml:42-57`, `roles`). The page's fonts are bundled, with their hashes recorded (section 7). The classifier prompt's hash is pinned in a test. | `test_pipeline_safety.py::test_real_data_refuses_another_api_endpoint`; `test_pipeline.py::test_classifier_prompt_has_the_authors_rules` | No lock file with hashes, and no SBOM. A model update can change behaviour, so it needs change control (section 8). | Medium |
| **LLM04** Data and model poisoning | Mostly n/a: nothing is trained or fine-tuned, and there is no retrieval. | Models are used as provided. Configuration is loaded with `yaml.safe_load` (`config.py:16-18`, `load_yaml`). Ticket text cannot change the taxonomy, prompts or policy. | `test_pipeline.py::test_classifier_prompt_has_the_authors_rules` | The evaluation data is synthetic and written by the same model family (`README.md:54`). That is an evaluation limit, not poisoning. | Low |
| **LLM05** Improper output handling | Model output sets routing, appears in a web page, and could reach a customer. | The classifier JSON is checked against a schema (`schemas.py:21-34`, `Extraction`). An unknown category is escalated (`gate.py:52-56`, `check`). An extracted reference that is not in the ticket lowers the score to 0.60, forces the re-check and flags the draft (`gate.py:71-74`). A summary over 300 characters, or with a number not in the ticket, is dropped (`run.py:149`, `_team_summary`). Drafts are rule-checked, and so is the agent's edit (section 7). The page builds every node with `textContent` or a text node, not from an HTML string (`util.js:7-33`, `el`), under a strict CSP with no inline code (`server.py:79-80`, `CSP`). Stream events are JSON-encoded (`server.py:1001-1002`, `_pump`). Model output is never run as code or used in a query. | `test_pipeline.py::test_mismatched_category_escalates`, `::test_invented_reference_is_capped_and_rechecked`, `::test_parse_takes_the_first_json_object`; `test_text_rules.py::test_asks_secret_is_caught`; `test_viewer_page.py::test_scripts_never_build_markup_from_strings_or_reach_another_site`; `test_server_ui.py::test_strict_csp_on_every_response` | The reference check is a substring test (`gate.py:31-41`, `reference_in_text`), so any span copied from the ticket passes with no flag. The reference field has no length or character limit (`schemas.py:27`). An integration must encode drafts for its own channel (section 9). | Medium |
| **LLM06** Excessive agency | A model acting on accounts or sending replies. | No model call has tools (`llm.py:243-249`, `_call_api`; the cli backend passes `--disallowedTools "*"`, `llm.py:275`, `_cli_command`). Nothing is sent (`README.md:5`). The only outside system it calls is the model API. A ticket classified as fraud, by the first model or by the re-check, always goes to a person (`run.py:326`, `:332-341`, `process`). | `test_pipeline.py::test_run_fraud_is_escalated_without_draft`, `::test_recheck_disagreement_uses_the_second_answer_but_never_for_fraud`; `test_pipeline_safety.py::test_account_risk_ticket_gets_no_draft` | A fraud ticket that the first model labels as an ordinary account problem at 0.75 or more is not re-checked and gets a draft ([failure mode 3](FAILURE_MODES.md#3-a-risky-ticket-rests-on-one-models-label)). Keep integrations to internal notes (section 9). | Low |
| **LLM07** System prompt leakage | Low. The prompts hold no secrets, keys or company facts. They are public in `src/pipeline/prompts/` and shown in the viewer (`server.py:907-908`, `_get`). | `config/policy.yaml` has no company facts, on purpose (`CONTEXT.md:49`). The key is never in a prompt. | Adversarial ticket asking for the instructions: no leak (`AUDIT:41`) | Whatever the institution adds to `policy.yaml` goes to the provider and into drafts. Put nothing there that must stay internal. | Low |
| **LLM08** Vector and embedding weaknesses | **n/a.** No embeddings, no vector store, no retrieval. | n/a | n/a | Re-assess if retrieval is ever added. | n/a |
| **LLM09** Misinformation | A wrong type, a promised refund or time, an invented fee, and an agent who trusts it. | The drafter gets only the policy facts, which are empty (`draft.py:60-72`, `policy_facts`; `draft_system.md:9-11`). Draft checks flag a promise, a time or an unknown number (section 7). A confidence gate and a blind re-check (`gate.py:44-86`, `check`; `run.py:308-341`, `process`). A person approves every draft in the inbox: a flagged draft needs a tick on what to check first (section 7). | `test_text_rules.py::test_outcome_promises_are_still_caught`, `::test_a_time_the_customer_wrote_is_still_a_promise`; `test_pipeline.py::test_policy_facts_reach_the_drafter_only_when_filled`, `::test_low_confidence_escalates`; smoke: "flagged: approving before the tick does nothing" | test2: type 78/80, and 1 of 74 drafts promised something (`README.md:13`, `:18`). After the t2-0033 relabel, 2 wrong types reached a draft and 1 was marked ready (t2-0041) (`LOG.md:228`, `:230`); 3 as first scored (`LOG.md:222`). The person who approves may trust a ready draft too much ([failure modes 2](FAILURE_MODES.md#2-a-fairly-confident-wrong-type-gets-a-ready-draft) and [11](FAILURE_MODES.md#11-the-person-approves-without-catching-the-error)). | Medium |
| **LLM10** Unbounded consumption | Long tickets, many tickets, retries, or a web page starting paid runs. | Input limits, the spending cap and bounded retries (section 7). One live run at a time (`server.py:966-968`, `_post_stream`). Closing the page stops the run (`run.py:186-193`, `process`). | `test_pipeline.py::test_api_cost_and_budget_cap`; `test_server_security.py::test_only_one_live_run_at_a_time_429`, `::test_closing_the_page_stops_the_run` | The cap is per process, not per day. Calls already in flight can overshoot it by a few calls (`models.yaml:25-28`, `budget_usd`). Production also needs a spending limit on the provider account. `/api/check` takes up to about 0.5 s on 8,000 characters of repetitive text, on this computer only (`LOG.md:64`). | Low |

## 7. Controls built in

| Control | What it does | Where | Test |
|---|---|---|---|
| Local-only viewer | Binds to 127.0.0.1. The Host must be `localhost`, `127.0.0.1` or `[::1]` on its port, else 421. A foreign Origin gets 403. Each viewer process makes a random token, puts it in the page, and requires it on every `/api/` call (else 403). A live run is a `POST`; `GET /api/stream` gets 405. | `server.py:1069-1070` (`make_server`), `:74-75` (`TOKEN`, `LOOPBACK`), `:840-853` (`_guard`), `:891` and `:912-913` (`_get`) | `test_server_security.py::test_wrong_host_is_refused_421`, `::test_foreign_origin_is_refused_403`, `::test_api_needs_the_page_token`, `::test_get_stream_never_starts_a_run_405` |
| Response headers | The strict CSP (page controls, below), `X-Frame-Options: DENY`, `nosniff`, `no-referrer`, COOP and `no-store` on every response. No Python version in the `Server` header. | `server.py:79-89` (`CSP`, `SECURITY_HEADERS`), `:792-801` (`version_string`, `end_headers`) | `test_server_security.py::test_security_headers_on_every_response` |
| Input limits | 4,000 characters per ticket, 1,000 tickets per batch, 64 KB per request. A lone surrogate is refused. | `config/thresholds.yaml:15-18` (`limits`); `run.py:267` (`process`); `run_batch.py:78-81` (`main`); `server.py:925-949` (`_read_json`), `:951-965` (`_post_stream`) | `test_pipeline_safety.py::test_too_long_ticket_is_escalated_before_any_model_call`, `::test_run_batch_refuses_too_many_tickets`; `test_server_security.py::test_oversize_body_is_refused_413`, `::test_ticket_over_the_char_limit_is_refused_413`, `::test_a_lone_surrogate_is_refused_400` |
| Kill switch `PIPELINE_MODE` | `off`: no model call, and every ticket goes to a person. `classify_only`: sorted and routed, no draft. Read before every model call, so no restart is needed. A bare `off` in YAML counts as off, and an unknown value never runs the full pipeline. | `config.py:106-125` (`_default_mode`, `pipeline_mode`); `llm.py:500-501` (`call`); `run.py:269-271`, `:363-366` (`process`) | `test_pipeline_safety.py::test_pipeline_off_makes_no_model_call`, `::test_llm_call_refuses_when_off`, `::test_classify_only_routes_but_never_drafts`, `::test_bare_off_in_models_yaml_switches_the_pipeline_off`, `::test_invalid_mode_escalates_instead_of_raising` |
| Real-data guard `REAL_DATA=1` (opt-in, section 1) | Refuses the cli backend, free-model profiles, the response cache, cache-only replay and any endpoint other than `api.anthropic.com`. `run_batch` refuses `--no-mask`. Any value except empty, `0`, `false`, `no` or `off` turns it on, so a typo keeps it on. Checked at startup and on every model call. | `llm.py:102-135` (`real_data`, `assert_real_data_safe`), `:499` (`call`); `run_batch.py:64`, `:69-71` (`main`); `server.py:1076-1084` (`main`) | `test_pipeline_safety.py::test_real_data_refuses_development_paths`, `::test_real_data_fails_closed_on_any_value_that_is_not_off`, `::test_real_data_refuses_another_api_endpoint`, `::test_run_batch_refuses_no_mask_and_cli_with_real_data`; `test_server_security.py::test_main_refuses_unsafe_real_data_setup` |
| Spending cap and retries | $5 per process by default, checked before each call. A model with no complete price is refused while a cap is set. A cap that is not a number refuses to start. SDK retries are off. On the API, one retry, only on a timeout, a dropped connection, a rate limit or a server error, waiting at most 10 s. 60 s timeout. A refused or invalid request is not retried. | `models.yaml:23-29` (`timeout_s`, `budget_usd`); `llm.py:147-172` (`budget_usd`, `_price`), `:222-242` (`_get_client`, `_call_api`), `:465-521` (`_backoff`, `_retryable`, `call`) | `test_pipeline.py::test_api_cost_and_budget_cap`; `test_pipeline_safety.py::test_unpriced_model_fails_closed_under_a_budget`, `::test_a_budget_that_is_not_a_number_of_dollars_refuses`, `::test_api_client_has_no_sdk_retries_and_a_timeout`, `::test_rejected_request_is_not_retried`, `::test_our_own_refusals_are_not_retried` |
| Fails closed | `process()` never raises. Any error escalates the ticket to a person with a note, and the live stream always ends. | `run.py:397-414` (`process`); `server.py:750-769` (`_work`) | `test_pipeline_safety.py::test_crash_inside_route_ends_as_internal_error_without_the_message`; `test_server_security.py::test_a_crashing_pipeline_still_ends_the_stream` |
| Masking of saved runs | Numbers of 7 or more digits, including ones split by `-`, `.` or spaces, keep only their first and last two digits. Card numbers are found with a Luhn check. A 3- to 8-digit code after a code word is fully hidden. Dates and comma amounts are kept. Names are not masked. | `clean.py:142-225` (`_card` to `mask_run`); `run_batch.py:143` (`main`) | `test_text_rules.py::test_mask_hides_separated_numbers_and_codes`, `::test_mask_keeps_dates_amounts_and_short_references`; `test_pipeline.py::test_mask_run_masks_every_string_and_keeps_numbers` |
| Draft checks | Always on: `asks_secret`, `promise` (a time only from policy facts), `unknown_number`, `stray_latin`. Behind flags, off by default: `hold_reason`, `sensitive_number`. A draft with a problem is still shown, flagged with the reason. | `draft_check.py:351-375` (`findings`); `fixes.py:18-26` (`FIXES`); `run.py:381-390` (`process`) | `test_text_rules.py::test_asks_secret_is_caught`, `::test_a_warning_or_a_mention_is_not_asking`, `::test_hold_reason_only_when_enabled`, `::test_sensitive_number_only_when_enabled_even_if_the_ticket_had_it` |
| No tipping off | Iraq's AML/CFT Law No. 39 of 2015 forbids disclosing to the customer "any legal procedures taken regarding transactions ... suspected of money laundering or terrorism financing" (Art. 12 Fourth). Disclosing "any action of reporting, investigation or inspection" carries up to 3 years in prison, a fine of IQD 15-50 million, or both (Art. 39 Second(b)) ([CBI-hosted English text](https://cbi.iq/static/uploads/up/file-150199913642139.pdf)). **The tool never sees AML or STR status.** Its only input is the ticket text and the config (`run.py:186`, `process`), and it has no connection to case or transaction systems. The `hold_reason` rule flags a draft that mentions an investigation, a suspicion, a report or money laundering (`draft_check.py:138-147`, `_HOLD`; `:332-343`, `_hold_reason`). It is off by default and fired on 0 saved drafts (`LOG.md:147`). | as listed | `test_text_rules.py::test_hold_reason_only_when_enabled`, `::test_hold_reason_leaves_ordinary_words` |
| Fraud and account risk go to a person | Tickets classified as fraud or security are always escalated, with no draft (`config/taxonomy.yaml:97`, `always_escalate`; `gate.py:58-62`, `check`). The rule acts on the model's label, not the ticket's content (section 11). Behind a flag (off), a blocked account or a SIM change also goes to a person with no draft (`gate.py:64-68`). In the inbox an escalated ticket has no draft box, and an agent's correction to fraud removes the draft. | as listed | `test_pipeline.py::test_fraud_always_escalates`, `::test_run_fraud_is_escalated_without_draft`; `test_pipeline_safety.py::test_account_risk_gate_only_when_enabled`; smoke: "escalated …: no draft box", "H1: correcting … to fraud removes the draft and offers forward" |
| Decision log | Written by the inbox (`POST /api/decision`). Append-only, with a self-declared reviewer name. Each decision is one line, written under a lock, with a UTC time and the reviewer: `REVIEWER`, or else the computer's login name (`server.py:523-527`, `reviewer`). Owner-only file. Keyed hashes, never text. The hash key is `DECISIONS_HASH_KEY`, else a new random key each time the viewer starts, so hashes from different runs of the viewer cannot be compared (`server.py:530-533`, `_HASH_KEY`). An undo is a new line that points at the earlier one. **The same OS user can edit or delete the file.** Production logs belong in the institution's SIEM or WORM store. | `server.py:512-720` (`decision_record`, `append_decision`, `read_decisions`), `:1051-1062` (`_post_decision`) | `test_server_security.py::test_decision_is_logged_with_hashes_and_never_the_text`, `::test_concurrent_decisions_never_interleave`, `::test_decision_log_is_readable_by_its_owner_only` |
| Dependencies | 4 runtime packages, each with upper bounds (bounded, not exact pins). Two unused packages were removed (`LOG.md:118`). | `requirements.txt`, `requirements-dev.txt` | none (pip-audit, section 1) |
| Secrets | The key comes from the environment. For development, `llm.py` also loads a git-ignored `.env` file, looked for from `src/pipeline/` upward (the repository folder included), so the key can sit there in plain text (`llm.py:54`, `:58`). `.env`, `*.pem` and `*.key` are git-ignored. The cli subprocess gets no API keys. | `llm.py:206-208` (`api_key`), `:287` (`_call_cli`); `.gitignore:1-6` | `test_pipeline.py::test_cli_backend_uses_plan_not_api_key`, `::test_api_key_from_either_variable` |

**Controls in the page (the agent inbox, `36b843b` and `d1280b6`).** They close the open CSP item of the hardening entry (`LOG.md:168`, `:24`). The page is a markup shell, and its code is ES modules under `app/static/js/`. In the smoke-test labels, "…" stands for a ticket id.

| Control | What it does | Where | Test |
|---|---|---|---|
| Strict CSP | Every response carries `default-src 'self'; script-src 'self'; style-src 'self'; font-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'`. There is no `'unsafe-inline'`: `index.html` has no inline script or style, no `style=` attribute and no inline event handler. | `server.py:79-80` (`CSP`), `:82-89` (`SECURITY_HEADERS`), `:798-801` (`end_headers`); `app/static/index.html` | `test_server_ui.py::test_strict_csp_on_every_response`; `test_viewer_page.py::test_index_html_has_nothing_the_csp_blocks`; smoke, in all five passes: "no console errors, CSP violations or requests to another host" |
| Local fonts | IBM Plex Sans Arabic and IBM Plex Mono from @fontsource 5.3.0, under the SIL Open Font License 1.1 (`OFL.txt`), served from the viewer. `SOURCE.txt` records each file's URL and sha256, and the test recomputes every hash. | `app/static/fonts/` (`fonts.css`, `SOURCE.txt`, `OFL.txt`) | `test_server_ui.py::test_font_files_match_their_recorded_sha256_and_licence`, `::test_fonts_are_local_with_swap_and_unicode_ranges`, `::test_fonts_css_and_every_font_it_names_are_served` |
| No third-party requests | Every URL in `index.html` is under `/static/`. The scripts hold no absolute URL except the SVG namespace, which is not fetched. The stylesheets import nothing from outside. `connect-src 'self'` stops the rest. | `app/static/` | `test_viewer_page.py::test_scripts_never_build_markup_from_strings_or_reach_another_site`, `::test_stylesheets_load_nothing_from_another_site`, `::test_every_file_the_page_loads_is_served_with_its_type`; smoke: "no console errors, CSP violations or requests to another host" |
| Static files by allow-list | `/static/` serves a file only when each part of the path is a plain name that does not start with a dot, the extension is exactly `.js`, `.css`, `.woff2`, `.svg` or `.txt` (each with its own content type), and the file is still inside `app/static/` once symlinks are followed. The path is not percent-decoded. Traversal, encoded dots, hidden files, folders, other types and symlinks out get 404. Static files need no token but keep the Host and Origin checks. | `server.py:149-157` (`STATIC_TYPES`, `_STATIC_PART`), `:177-198` (`static_file`), `:893-895` (`_get`) | `test_server_ui.py::test_anything_else_under_static_is_404`, `::test_static_file_never_resolves_outside_the_folder`, `::test_each_allowed_type_has_its_exact_content_type`, `::test_static_needs_no_token_but_keeps_the_host_and_origin_checks` |
| Edits checked again (`POST /api/check`) | The agent's edit goes through the same draft rules and policy facts as the pipeline, about 400 ms after typing stops. Older calls are cancelled, and findings count only for the exact text they were computed on. It has the same guards as every POST (Host, Origin, token, JSON, 64 KB). A draft may be up to twice the ticket limit (8,000 characters). It logs and keeps nothing. | `server.py:484-507` (`check_request`), `:1037-1049` (`_post_check`); `draft.py:80-84` (`facts_text`); `composer.js:119-139` (`buildComposer`) | `test_server_ui.py::test_check_returns_exactly_what_the_pipeline_computes`, `::test_check_allows_a_time_only_from_the_policy_facts`, `::test_check_has_the_same_guards_as_every_post`, `::test_check_limits_are_413_and_the_edges_pass`, `::test_check_never_logs_or_stores_the_text`; smoke: "an edit asking for the code blocks approval", "the phrase is highlighted in the draft" |
| Blocked replies refused | A reply with a blocking finding cannot be approved: `asks_secret`, and `hold_reason` or `sensitive_number` when their flag is on. On approve, the page locks the draft and checks the final text again. The server then runs the same blocking rules on the final text of every approve or edit, and refuses a match with 409, writing nothing. A take-over or a forward is still recorded. | `server.py:138-143` (`BLOCKING_CHECKS`, `BLOCKED_AR`), `:653-658` (`blocking_in`), `:680-684` (`append_decision`); `inbox.js:580-597` (`approval`), `:779-811` (`approve`) | `test_server_security.py::test_an_approval_that_asks_for_a_code_is_refused_409`; smoke: "Ctrl+Enter inside a blocked draft does not approve", "SEC-1: text typed while the check ran is not in the approved reply", "SEC-1 / F8: the server refuses a secret request (409) and a second decision on one ticket (409)" |
| Decisions restored, and undo | On load, the page reads the run's decisions (`GET /api/decisions`) and shows the one that stands on each ticket: the latest not undone, worked out the same way by the page and the server. An undo is a new line that names the decision it takes back. On a saved run, a second decision on a ticket that has one (from another tab), or an undo of a decision that no longer stands, gets 409. Live tickets are not compared across pages. | `server.py:661-669` (`standing`), `:686-693` (`append_decision`), `:909-911` (`_get`); `state.js:161-174` (`standing`, `restoreDecisions`), `:243-256` (`undo`) | `test_server_security.py::test_a_second_decision_on_a_saved_run_ticket_is_refused_409`, `::test_standing_matches_the_page`, `::test_decisions_are_filtered_by_run`, `::test_live_tickets_are_not_compared_across_pages`; smoke: "undo logs «undone» with undoes = the approve's id", "after a reload the counter is «خلصت 4 من 80»" |
| Text is shown as text | Every node is built with `textContent` or a text node, not from an HTML string. `innerHTML`, `insertAdjacentHTML`, `document.write` and `eval` do not appear in the scripts. Direction-control characters are dropped from customer text on screen, with a note. Maps keyed by data have no inherited keys. | `util.js:7-33` (`el`, `add`), `:162-171` (`plainText`), `:37` (`dict`) | `test_viewer_page.py::test_scripts_never_build_markup_from_strings_or_reach_another_site`; smoke: "SEC-3: direction controls are dropped from the customer text, and the page says so", "SEC-4: a flag named «constructor» does not break the inbox" |
| Little kept in the browser | Ticket text, drafts, edits and ticks stay in memory. `localStorage` holds one entry with five preferences, and the page works with storage blocked. The paste box has no autocomplete or spellcheck, and forgets cancelled text. | `util.js:231-255` (`loadPrefs`, `savePrefs`); `state.js:1-2`; `app/static/index.html:104` | `test_viewer_page.py::test_only_preferences_go_to_local_storage`; smoke: "SEC-2: the new-ticket box has no autocomplete or spellcheck and forgets cancelled text", "with storage blocked the inbox works, and the card shows and closes" |

## 8. Responsibility matrix

The PCI SSC AI principles say "ultimate responsibility must come down to a single individual", and that "there needs to be ways to log and monitor what an AI system is doing" ([PCI SSC, 11 Sep 2025](https://blog.pcisecuritystandards.org/ai-principles-securing-the-use-of-ai-in-payment-environments)). The institution names **one accountable owner** for the deployment. The roles in the last column are suggestions.

| Area | The pipeline does | The deploying institution must | Suggested owner |
|---|---|---|---|
| Access | Local viewer with a per-process token (section 7). The real-data guard is opt-in (section 1). | Put SSO with MFA and TLS in front of the viewer before a second person uses it. CBI control 14.1.4 requires MFA for staff web applications reachable over the internet ([CBI](https://cbi.iq/static/uploads/up/file-171939658616261.pdf)). The token stops other web pages, not other users (`LOG.md:162`). Agents never start the tool themselves: the service definition sets `REAL_DATA=1` and `LLM_BACKEND=api`. | IT security |
| Secrets | Reads the key from the environment or a `.env` file, and never logs it | Keep the key in a vault and inject it into the service environment. Keep no `.env` file on the host. Use a dedicated provider workspace with spending and rate limits, one key per environment, and rotation. Set `DECISIONS_HASH_KEY` from the vault, or the log's hashes cannot be compared after a restart. | IT security |
| Retention and storage | Writes run files and the decision log with no expiry. Does not manage the input file. | Full-disk encryption on the host. Keep the input file, run files and the decision log on an encrypted volume, each with a retention period. AML Law Art. 11 keeps certain records for five years; whether ticket files count is the institution's call. | Data protection officer |
| Logging | The inbox writes a local decision log. A live run leaves no record of what was sent out, unless the agent decides on it (section 3). | Forward the decision log to the SIEM or a WORM store, and alert on it. Take the reviewer from SSO, not from `REVIEWER`. Keep a metadata-only disclosure log (time, user, ticket id, model, `inference_geo`, token counts, no text), or rely on the provider's usage records. | Security operations |
| Assurance | Unit tests and a browser smoke test, both with no model calls, a 14-ticket adversarial set run once, and the 1 Nov security review and the agent inbox's reviews (including a security and privacy lens, `LOG.md:67`), which the author states were run by AI agents through the coding assistant (DISCLOSURE.md, section 3). No outside review. | An independent penetration test and code review before go-live | IT security |
| Privacy | Masks numbers in saved files | Run a DPIA, approve disclosure of Restricted data, set the legal basis and notice, and run the transfer impact assessment (section 4) | Data protection officer, legal |
| Vendor | Uses only ZDR-eligible API features | Sign the commercial contract and DPA. Decide on ZDR (section 5). Set `allowed_inference_geos`. | Procurement, legal |
| CBI notification | none | Report a disclosure or suspected leak of Restricted data directly to CBI by official letter or email (CBI Identify 4, p. 23). Report complaints quarterly (Consumer Protection Regulation, Chapter Two, Seventh(3)). | Compliance |
| AML reporting | Keeps AML status out of the tool. A fraud flag is a routing hint only. | Keep the reporting procedure outside the tool, with the AML reporting officer. Team notes stay factual. | AML reporting officer |
| SIM change and account recovery | Routes them to the accounts team, with an optional flag to escalate them | Verify identity in the institution's own process. GSMA: "SIM Swap occurs when a fraudster manipulates the customer service process to take over an open account" ([GSMA](https://www.gsma.com/solutions-and-impact/technologies/mobile-identity/wp-content/uploads/2020/10/GSMA-What-is-SIM-Swap.pdf)). Drafts must never confirm account details or promise a change *(inference)*. | Head of support operations |
| Monitoring | Logs each action, reason code, correction, warning ticked, time taken, number of visits and edit size | Each week, a senior agent reviews a sample of approved drafts. Track flag, edit and override rates from the decision log (NIST AI 600-1 MS-4.2-004, "monitor and document instances where human operators ... override the GAI's decisions" ([NIST](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf))). Set the triggers for switching it off (NIST MG-2.4-004). | Head of support operations |
| Change control | Every change is a flag, run with and without it (`docs/experiments/README.md`). The classifier prompt hash is pinned. | Put prompts, taxonomy, policy and model ids under formal change control (CBI 10.1.3). Re-run with and without on dev, plus the adversarial set, before any change goes live. | Change board |
| Policy facts | Drafts state no time, fee or limit (`config/policy.yaml` is empty) | Fill in the institution's own hours and response times | Head of support operations |

## 9. Integration contract (generic)

No ticketing adapter exists today. The only outbound calls are model calls (`src/pipeline/llm.py`). Any integration should keep to these rules:

- **Identity.** A dedicated, least-privilege integration identity. It reads new tickets, and it writes only one internal note per ticket: type, team, priority and draft. It cannot reply to a customer, change a ticket's status, merge or delete.
- **Replies** are sent by the agent, from the ticketing tool, under the agent's own login.
- **Inbound events.** Pull tickets if possible. If webhooks are used, verify an HMAC signature over the raw body with a constant-time compare. Accept only a short timestamp window, and drop replays by event id.
- **Model traffic.** One allow-listed endpoint (`https://api.anthropic.com`), over TLS. It goes through the institution's egress proxy with DLP, using a key from the vault.
- **Output handling.** Validate the classifier JSON against the schema. Encode drafts for the target channel. Never put model output into a query or an API call.
- **No connection** to core banking, the ledger, AML case management or document stores. Refunds and reversals stay human actions in the institution's own systems.
- **Attachments are not passed** to the pipeline (section 11).

## 10. Incident runbook

**Triggers:**
- a fraud ticket gets a draft
- a draft that tips off, asks for a code or makes a promise reaches a customer
- a leaked key, input file, run file or decision log
- a breach notice from the vendor
- a sudden rise in flags or overrides
- a legal or residency stop

**Steps:**
1. **Switch off.** Set `PIPELINE_MODE=off`, or `mode: "off"` in `config/models.yaml`. It is read before every model call, so no restart is needed (`config.py:106-125`, `pipeline_mode`). Every ticket then goes to the manual queue.
2. **Rotate the key.** Revoke it at the provider, issue a new one, and replace it in the vault.
3. **Preserve.** Copy the run files and `runs/decisions.jsonl` read-only, with their hashes, before any clean-up. Keep stderr logs.
4. **Assess what left the network.** Which tickets were processed in the window (batch run files; a live run leaves nothing but a decision line, if the agent made one), how many model calls (`meta.usage`), where inference ran (`inference_geo`, if recorded), and the provider's usage records.
5. **Notify.**
   - CBI: as the institution's CBI duties require. For Restricted data, report directly to CBI by official letter or email, with the facts and the type of event (Identify 4, p. 23).
   - The vendor: Anthropic must notify the institution within 48 hours of becoming aware of a breach on its side (DPA G.1).
   - Tipping off: if an incident may involve it, the AML reporting officer decides what follows.
6. **Find the cause and fix it,** with a test that fails before the fix. Re-run with and without on dev, plus the adversarial set.
7. **Re-enable.** The accountable owner signs off. Start with `classify_only` (no drafts), then `full`, and watch the flag and override rates in the decision log.

## 11. Not yet done, and open questions

- **Fraud handling rests on one model's label.** A fraud ticket that the first model labels `login_otp`, `forgot_pin` or `blocked_account` at 0.75 or more gets no re-check and gets a draft (`gate.py:85`, `check`; `config/taxonomy.yaml:54-56`). No synthetic ticket has done this. On test2, the first model labelled all 6 fraud tickets as fraud, at confidence 0.80 to 0.95 ([failure mode 3](FAILURE_MODES.md#3-a-risky-ticket-rests-on-one-models-label)).
- **A model-extracted reference reaches the drafter prompt outside the ticket tags** (`draft.py:99-100`, `user_prompt`), and a span copied from the ticket passes the gate unflagged (section 6, LLM05). Reproduced with no model call; whether a model would extract such a span is untested ([failure mode 7](FAILURE_MODES.md#7-instructions-planted-in-a-ticket)). *Option for the author, behind a flag:* neutralise the reference and allow only digits, Latin letters and separators, up to a fixed length.
- **The real-data guard is opt-in** (section 1). *Option for the author:* refuse to start unless `REAL_DATA` is set explicitly, with `REAL_DATA=0` for development.
- **A `.env` file can hold the key in plain text** and can set other variables (section 3). *Option for the author:* under `REAL_DATA=1`, refuse to start when a `.env` file is found.
- **No record of what a live run sent out** (section 3), unless the agent decides on the ticket. A metadata-only disclosure log is not built.
- **No agent has used the inbox yet** (`LOG.md:59`). The decision log holds no human data, and whether its friction (the tick on a flagged draft, the blocked approve) works with real agents is untested.
- **Names are not masked** anywhere (`clean.py:205-208`, `mask_for_logs`).
- **No pseudonymisation before sending.** The design would replace phone numbers, card numbers and codes with tokens, keep the map in memory, and map them back afterwards. It changes what the model is sent, so it needs API runs with and without it on dev, which the author must approve (`CONTEXT.md:47`).
- **Fraud tickets reach the model.** Classification and a summary line both see the full text. A flag to skip the summary call for fraud is not built.
- **Attachments, images and voice notes** are future plans (`CONTEXT.md:160`). None may reach a model until assessed separately: verification tickets can carry identity documents.
- **Classification and residency** are open (section 4). If the institution classifies ticket text as Confidential, an external model may be ruled out.
- **Known misses in the rules** (`LOG.md:203`, `:206`):
  - A code written before its word («482913 هذا الرمز») is not masked.
  - A request more than three words before the secret is not caught.
  - «خلال اربعة وعشرين ساعة» is not caught as a time.
- **Three flags are off by default,** waiting for the author to decide:
  - `hold_reason` and `sensitive_number` fired on 0 saved drafts, so their benefit is untested. While they are off, they block no approval in the inbox or on the server: only `asks_secret` does (`server.py:653-658`, `blocking_in`; `LOG.md:63`).
  - `escalate_account_risk` raises the test2 review rate from 19% to 26%, with one wrong case (`LOG.md:149-153`).
- **Single user.** The reviewer name is self-declared. When two pages decide one ticket of a saved run, the second gets a 409, but live tickets are not compared across pages. The decision log has no expiry, and the same OS user can change it.
- **Dependencies** have bounds, not hash-pinned versions. There is no SBOM.
- **Development-only scripts** (`calibrate.py`, `run_probes.py`) still record exception messages in their own outputs (`LOG.md:167`).

## 12. Reporting a vulnerability

- Use the repository host's private vulnerability reporting (the **Security** tab, then **Report a vulnerability**).
- If that is not available, open an issue that asks for a contact. Leave out the details.
- **Never paste real customer data, or an API key,** into a report, an issue or a test ticket.
