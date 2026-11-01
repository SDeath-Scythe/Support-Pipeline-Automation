# Disclosure

What this project is built from, who or what made each part, and what its numbers can and cannot support. It expands the "Disclosure" section of the [README](README.md). Each claim points to a file in this repo or a public source; inference is marked, and statements that rest only on the author's word say so.

Short names: LOG = [`docs/experiments/LOG.md`](docs/experiments/LOG.md), AUDIT = [`docs/experiments/AUDIT-2026-10-29.md`](docs/experiments/AUDIT-2026-10-29.md). Line numbers are as of commit `76463d4` (1 Nov 2026).

## In short

- **Every ticket is synthetic**, written by a Claude model. No real customer data is in the repo or was used in any run.
- **Most gold labels come from the plan the tickets were written to.** The author, a native speaker of Iraqi Arabic, checked 64 labels, 13 drafts and 2 team notes.
- **An AI coding assistant (Claude Code) did most of the building.** The author states that it wrote most of the code, tests and documents, and that the 1 Nov security review was run by AI agents through it (section 3). The author set the rules and made every adopt-or-delete decision. Every commit carries the author's name.
- **One model family** writes the tickets, runs the pipeline and grades the drafts.
- **No outside review and no compliance claim.** No review of the code or the security controls by anyone outside the project is recorded. The system has not been tested on real tickets or reviewed by any financial institution or regulator.

## 1. Data

**All synthetic.** No real customer message, account or transaction is in the repo or was used in any run ([`data/README.md`](data/README.md):3; README.md:100).

**How the tickets were made** (`scripts/generate_tickets.py`; data/README.md:15-26):
- A seeded plan fixes each ticket's type, dialect (Baghdadi, southern, Mosuli), style, difficulty and amount, and gives about 18% an edge case (line 19).
- The `generator` role, Claude Opus 5.5 ([`config/models.yaml`](config/models.yaml):58-62), writes the text, about 10 tickets per call, on the cli backend: Claude Code on the author's plan (line 17; commit `6e0521d`).
- Code inserts references and phone numbers, so those gold values are exact (line 20). Phones are random digits in the Iraqi mobile format (`generate_tickets.py`:440-441), so some may match real numbers by chance *(inference)*.
- Code rejects invented numbers, blocked brand names, non-Iraqi dialect, over-used dialect words, near-duplicates and breaks of the author's dialect rules (lines 21-22, 120). Priority and outcome come from code rules (line 23).

**The sets** (counts from each split file; seeds from each `build_info.json`):

| Set | Tickets | Seed | Use |
|---|---|---|---|
| dev | 233 | 1101 | development, threshold calibration |
| mvp_test | 78 | 2202 | test, run once (29 Oct) |
| heldout | 78 | 3303 | **sealed**, run once (29 Oct) |
| test2 | 80 | 5505 | final test, run once (30 Oct); 30 labels checked by the author first |
| heldout2 | 80 | 6606 | **sealed**, not run yet |
| `data/excluded/` | 11 | n/a | Arabizi, removed on 29 Oct by the author's decision (dev 7, mvp_test 2, heldout 2) |
| `data/probes/` | 139 distinct | n/a | early experiments (19–23 Oct), 14 adversarial inputs (29 Oct) |

**Sealing.** The rule is to never read or print heldout ticket text, only ids and counts (CONTEXT.md:48). heldout and heldout2 were built in separate runs that printed only statistics, and heldout's later changes were made by code (data/README.md:25, 30, 134). The viewer will not serve sealed sets (LOG:17), and heldout's per-ticket pages stay out of git (LOG:139). Caveats: this rests on process, which the repo cannot prove, and LOG:159 describes one heldout draft (hold-0015), so at least one heldout model reply was seen. The early probe set holdout_30 was reused after its first run and no longer counts as unseen ([HANDOVER.md](HANDOVER.md):353).

**Where the synthetic tickets went:** the Anthropic API and Claude Code. On 23 Oct, holdout_30 was also sent to free-tier models from other vendors for a comparison; none was used after that ([`docs/experiments/free_models/README.md`](docs/experiments/free_models/README.md); CONTEXT.md:120). Real-data mode refuses those profiles (LOG:28).

**No API key** is in the repo or its history. `.gitignore`:1-6 excludes key files, and a scan of the whole git history for common key patterns found none on 1 Nov (the command is in [SECURITY.md](SECURITY.md), section 1).

## 2. Labels

| Labels | Written by |
|---|---|
| dev, mvp_test, heldout, test2, heldout2 | **The seeded plan**, plus code for references, phones, priority and outcome (data/README.md:19-23). A model wrote each ticket to fit its plan; where it missed, the label is wrong. The first 400 were recomputed with the author's rules F18 and F19 on 28 Oct (line 136). |
| Blind audit | **Claude Opus 5.5** (`evaluator`), without seeing gold. A disagreement flags the ticket for review and never changes gold (line 24). Disputes: dev 5, mvp_test 0, heldout 3, test2 2, heldout2 2 (`build_info.json`). |
| `fixes_30` and the other early probe sets | **The coding assistant** (LOG:5; HANDOVER.md:385) |
| `data/review/handcheck_80.csv` (80 rows) | **An AI model** applying the author's rules, not the author (data/README.md:117) |

**The author's checks** (answers in [`data/review/`](data/review/)):

| When | What | Found | What it changed |
|---|---|---|---|
| 23 Oct | The first 400-ticket build | Three wrong assumptions: «ورقة», Mosuli غ for ر, urgency words | Dataset rebuilt; F15, F16 (data/README.md:32-38) |
| 29 Oct | 18 dev labels (14 most disputed, 4 random) | Gold right on 16; 2 corrected | The double-payment error, fixed by F20 (LOG:187, 195-197) |
| 29 Oct | 13 dev drafts, 2 team notes | 10 send as is, 3 small edits, 0 rewrites; right questions on 9 of 13 | F21 team-note summary; judge stops penalising loanwords; generator dialect fixes (LOG:165, 174-177) |
| 30 Oct | 30 test2 labels, before the run | 30/30 right; 3 a bit off in dialect | Two more words banned in the generator (LOG:120) |
| 30 Oct | After the run: t2-0033, a note on t2-0021 | One wrong label; app bugs belong with tech support | test2 77/80 → 78/80; routing change (LOG:116, 133) |

- **In total:** 64 labels (34 dev, 30 test2), 13 drafts and 2 team notes (CONTEXT.md:132). No mvp_test or heldout label was checked by a person (LOG:139).
- **All three corrected labels moved to the pipeline's answer** (dev-0094, dev-0152, t2-0033), each after a person's ruling. That can only raise scores, so LOG gives the score before and after (LOG:124, 203).
- **The draft judge is a model:** Claude Opus 5.5 (`evaluator`; prompt [`scripts/prompts/judge_draft.md`](scripts/prompts/judge_draft.md)), on the cli backend by default (CONTEXT.md:70). On the 13 drafts the author rated, it mostly agreed, but it was too strict on English loanwords; that is fixed (AUDIT:64; LOG:175).

## 3. AI use in building

<!-- the author to confirm wording -->

**The author states** the following. It is not otherwise recorded in the repo.
- **Claude Code**, Anthropic's AI coding assistant, wrote most of the code, tests and documentation, under the author's direction. It also wrote the 14 adversarial tickets, ran the experiments, wrote the logs, and drafted this page, SECURITY.md and FAILURE_MODES.md.
- **The 1 Nov security review** (12 findings) and its "six reviewers" (LOG:9, 76) were AI agents run through the coding assistant, not people. "Checked by hand" in LOG:9 means that each finding was reproduced with no model call before it was fixed.
- **This page, SECURITY.md and FAILURE_MODES.md** were checked the same way, by AI reviewer agents, before they were committed.

**Recorded in the repo:**
- **The assistant's role.** It wrote the tickets and gold labels of the early probe sets (LOG:5; HANDOVER.md:385). HANDOVER.md is its report of one working session (HANDOVER.md:7). Which Claude model it ran on in each session is not recorded.
- **The author's role.** The author:
  - set the goals and working rules (CONTEXT.md, section 3)
  - wrote the native-speaker rules, which are now code checks (CONTEXT.md:51-57, 80)
  - checked labels and drafts as a native speaker (section 2)
  - decided to adopt or delete each flag (CONTEXT.md:46, 92)
  - made the decisions recorded in CONTEXT and LOG. These include keeping company policy out of `config/policy.yaml` (CONTEXT.md:76), dropping Arabizi (data/README.md:30), the F18 and F19 rules (CONTEXT.md:78-79), grading drafts on the free backend when results match (CONTEXT.md:70), and routing app bugs to tech support (LOG:116).
  - passed on the mentor's feedback (CONTEXT.md:149-153).
- **Backends.** Development runs, dataset generation and draft grading used the cli backend: Claude Code on the author's Claude plan (CONTEXT.md:58-61). Every pipeline run behind a README number, and the threshold calibration, used the Anthropic API (README.md:47). Those drafts were then graded by the judge on cli. Rounds 1–3 of the fix experiments (20–23 Oct) ran on cli and only compare configurations (LOG:5).
- **Commits.** All 170 commits (`git log --all`, 1 Nov) carry the author's name, by the author's rule (CONTEXT.md:44). The author field shows who directed and accepted the work, not who typed it; this page is the record of who wrote what. The README's own line says only that Claude Code "was used as a coding assistant" (README.md:101); this page is the fuller record.
- **Other material.** The MVP update document and the 14-slide mentor deck were made with Claude's document and slide tools (CONTEXT.md:137).

## 4. Evaluation limits

**One model family** writes the tickets (Opus), runs the pipeline (Haiku, Sonnet), and audits labels and grades drafts (Opus). They may share blind spots (AUDIT:63; README.md:54).

**Each test set was run once**, with the locked configuration, on the API (LOG:118-159; CONTEXT.md:157):

| Set | Run | Type correct | Fraud escalated, none drafted | Review rate |
|---|---|---|---|---|
| mvp_test (78) | 29 Oct | 77/78 | 6/6 | 27% |
| heldout (78, sealed) | 29 Oct | 77/78 | 5/5 | 18% |
| test2 (80) | 30 Oct | 77/80 as run; 78/80 after one relabel | 6/6 | 19% |
| heldout2 (80, sealed) | not yet; to run once on the final version | n/a | n/a | n/a |

**What the numbers show:** on synthetic, model-written Iraqi Arabic with model-written gold, the ticket type matched on 96–99% of each test set, every fraud ticket was escalated with no draft, and the review rate stayed under the 30% target.

**What they do not show:**
- **Accuracy on real customer messages.** Model-written dialect can drift toward standard Arabic ("fusha in disguise", named by the Mizan benchmark, [arXiv:2609.13980](https://arxiv.org/abs/2609.13980)). The code checks reduce this, not remove it (data/README.md:120).
- **Agent time saved, draft quality as support agents see it, or how carefully agents review.** None is measured yet (CONTEXT.md:145; [FAILURE_MODES.md](FAILURE_MODES.md), failure mode 11). Draft scores come from the model judge; the author rated 13 drafts.
- **Small differences.** On 78 tickets, one error moves accuracy by 1.3 points; 77/78 has a 95% confidence interval of 93.1–99.8% (AUDIT:7).
- **Behaviour at volume.** At most five tickets were run in parallel (AUDIT:68).

## 5. Models and costs

| Role | Model ([`config/models.yaml`](config/models.yaml)) | Used for |
|---|---|---|
| classifier | `claude-haiku-5-5` | classify and extract; the fee call; the team-note summary |
| rechecker | `claude-sonnet-5-5` | second opinion when unsure |
| drafter | `claude-sonnet-5-5` | the draft reply |
| generator | `claude-opus-5-5` | development only: writing tickets |
| evaluator | `claude-opus-5-5` | development only: blind label audit, draft grading |

- **API spend.** The key is a $35 test key, received on 28 Oct (CONTEXT.md:38). No running total is kept. The per-run costs in LOG and AUDIT add up to about $5.70 *(inference: entries may overlap and small checks are not itemised; LOG:130, 155, 163, 187, 189, 207, 219, 233, 245; AUDIT:27)*. The API account's usage page is the authority. The 1 Nov hardening made no model calls (LOG:9).
- **Cost per ticket:** $0.0027 on test2 (LOG:130); about $0.40 for 150 tickets a day (AUDIT:58).
- **Spending cap:** $5 per process by default (`budget_usd`, config/models.yaml:25-29; `LLM_BUDGET_USD`). One batch run is one process. In the viewer, the cap counts every live run since the server started (`src/pipeline/llm.py:138-140`). At the cap, further calls are refused and the run warns its numbers are invalid (CONTEXT.md:69). Calls already in flight still finish, so a run can go a few calls over. No run has reached it (AUDIT:53).

## 6. Third-party material

- **Fonts:** the Plex Sans Arabic and Plex Mono font families, under the SIL Open Font License 1.1. The committed viewer loads them from an external font host (`app/static/index.html`:7-9 at `76463d4`). The UI work in progress bundles them in `app/static/fonts/`, with the licence text (`OFL.txt`) and each file's source and checksum (`SOURCE.txt`).
- **Python packages** ([`requirements.txt`](requirements.txt)): `anthropic` (Apache-2.0), `pydantic` (MIT), `pyyaml` (MIT), `python-dotenv` (BSD-3-Clause); for tests, `pytest` (MIT). Licences as listed in the installed packages' metadata. The viewer uses the Python standard library only (README.md:76).
- **Documents cited in [SECURITY.md](SECURITY.md)**, all public and linked there: Central Bank of Iraq regulations and notices, including the English text of Iraq's AML/CFT Law No. 39 of 2015; the [OWASP Top 10 for LLM Applications 2025](https://genai.owasp.org/llm-top-10/); [NIST AI 600-1](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf); the PCI SSC's AI principles; a GSMA paper on SIM swap; and Anthropic's terms and data-retention pages. They are cited and briefly quoted, not copied. Quotes from Arabic-only texts are unofficial translations, made with the coding assistant.
- **Mizan** ([arXiv:2609.13980](https://arxiv.org/abs/2609.13980)) is cited for a dialect-data risk and was used to pick which free models to test. None of its data is used.

## 7. What is not claimed

- **Compliance.** The repo claims compliance with no law, regulation or standard, including those above. SECURITY.md says what the code does and what a deploying institution must still do.
- **Results on real tickets.** All results are on synthetic data (README.md:53).
- **Outside review.** No financial institution or regulator has reviewed, tested or endorsed this system. No outside code or security review is recorded.
- **Autonomy.** Nothing is sent automatically. A person approves, edits or takes over every ticket (README.md:5).
- **Full masking.** Saved runs mask numbers and codes, not names. The development response cache keeps replies in full (README.md:56).
- **Images and voice notes.** These are a future plan, not part of the MVP (CONTEXT.md:160).
