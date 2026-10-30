# Support Pipeline Automation

**Agentic AI Challenge Iraq · Topic 06** · Salih Safaa Mohammed

A batch pipeline that sorts customer support tickets written in **Iraqi Arabic dialect** (Baghdadi, southern, Mosuli), pulls out the details, routes each ticket to the right team with a priority, and pre-drafts a reply in Iraqi Arabic. **A person approves, edits or takes over every ticket. Nothing is sent automatically.**

## Results (final test, 30 Oct)

80 fresh tickets (`data/test2`), run **once** with the final configuration on the API. The author, a native speaker, checked 30 of their labels **before** the run (30/30 right).

| | test2 (80) |
|---|---|
| Ticket type correct | **78/80 (97.5%)** (77/80 as first scored; the author then corrected one label he hadn't checked) |
| Priority correct | 79/80 |
| Transaction reference extracted | 21/21 |
| Fraud tickets escalated, none drafted | **6/6** |
| Needs more than a quick approve (flagged or escalated) | **19%** (target ≤ 30%) |
| Drafts that promise an outcome or ask for a code | 1/74 · 0/74 |
| Cost / time per ticket | **$0.0027** · about 5 s |

Across all 389 measured tickets (dev, mvp_test, heldout): type 385/389 (99.0%), every dialect and writing style at 96–100%, all 28 fraud tickets escalated. Fourteen adversarial tickets (prompt injection, a fake verdict planted in the ticket, requests for another customer's data or for the bot's instructions, Kurdish, empty, very long) were all handled. Details: [`docs/experiments/AUDIT-2026-10-29.md`](docs/experiments/AUDIT-2026-10-29.md) and [`docs/experiments/LOG.md`](docs/experiments/LOG.md).

## The user

A Level-1 support agent handling 100–150 tickets a day, most of them repetitive: transfers that didn't arrive, money sent to the wrong person, login and code problems, agent disputes. The pipeline does the first pass; the agent decides.

## How it works

```
ticket → clean → classify + extract → confidence gate → re-check if unsure → route + priority → draft → person
         rules     Haiku 5.5              rules             Sonnet 5.5             rules         Sonnet 5.5
                                            │
                                            └─ fraud, or still unsure → escalated, with a short note for the team
```

A fixed workflow, not a free-roaming agent: predictable and testable. Models are used only where judgment is needed; routing, priority and the safety checks are plain rules.

- **Confidence gate.** The classifier's confidence is lowered when a rule disagrees (a required field is missing, or a "reference" it found isn't in the text). Below 0.60: escalated. 0.60–0.75, or a high-risk type: a second model classifies the ticket blind. If the two disagree, the ticket is drafted from the second model's answer and flagged; if the second answer is fraud or fails the gate itself, it is escalated. Fraud and security tickets are always escalated.
- **Priority** comes from the problem type, raised one level for a large amount (≥ 1,000,000 IQD or ≥ $750). No word in the ticket changes it.
- **Three outcomes:** ready to approve; flagged (a person should check one thing, named in the note); escalated (no customer draft; the team gets a note with the topic, the facts found, what's missing, why it was escalated, and a one-line summary of what happened).
- **Grounded drafts.** The drafter is told only the ticket, the extracted facts and [`config/policy.yaml`](config/policy.yaml), which is empty on purpose: a deploying team adds its own hours and response times there. Rule checks flag any draft that promises an outcome or a time, asks for a code or PIN, contains a number not in the ticket, or has stray Latin letters.
- **Taxonomy:** 8 categories, 23 types, 9 teams ([`config/taxonomy.yaml`](config/taxonomy.yaml)).

## How it was built and measured

- **Every change was tested with and without it** on the same tickets, with repeat runs to measure noise, before being adopted. Several that looked like improvements were noise or broke something else and were dropped; the log of every test is [`docs/experiments/LOG.md`](docs/experiments/LOG.md).
- **Numbers come from the API.** Development runs used Claude Code on the author's plan (`LLM_BACKEND=cli`, free); every reported number and the thresholds come from the API (`LLM_BACKEND=api`).
- **Data:** 400 synthetic tickets for development (dev 233, mvp_test 78, heldout 78), then 160 fresh ones for the final test (test2 80, and heldout2 80, sealed until the progress review). Written by Claude Opus from a seeded plan that crosses type × dialect × writing style × edge case, with code checks for dialect drift, invented numbers and near-duplicates.
- **Human checks:** the author reviewed 34 dev labels (2 corrected), 13 drafts and 2 team notes, and 30 test2 labels before the final run. His rules as a native speaker are part of the code and the data (for example «ورقة» is a 100-dollar note, and no urgency word raises priority).

## Known limits

- The tickets and most labels are model-written; a person checked 64 of them. There are no real customer messages in the evaluation.
- The ticket writer, the pipeline and the draft grader are models from the same family.
- The drafter sometimes doesn't ask for a shop or agent's name when the customer only says "the restaurant"; the fix tried made drafts worse.
- Masking covers numbers only: saved runs hide every phone, card, account and transaction number of 7+ digits (shorter references stay visible), but not names. The response cache, a development tool, keeps replies in full and must stay off for real tickets.

## Run it

```bash
pip install -r requirements.txt
pytest                                          # 76 tests, no model calls
python app/server.py                            # viewer: http://localhost:8000, no key needed

export SUPPORT_PIPELINE_API_KEY=...             # or ANTHROPIC_API_KEY
LLM_BACKEND=api python app/server.py            # the same viewer, able to run new tickets
LLM_BACKEND=api python scripts/run_batch.py data/test2/tickets.jsonl
```

**See the final test without a key:** start the viewer and pick "test2 · final" in the list. It replays the measured run ([`docs/runs/test2/final.json`](docs/runs/test2/final.json), committed as it was run on 30 Oct) and scores it against the current labels: type 78/80, priority 79/80.

**Saved runs are masked:** `run_batch.py` hides phone, card, account and transaction numbers (7+ digits, keeping the first and last two) in the file it saves. `--no-mask` keeps them, for synthetic test sets scored against their gold labels; the experiment script uses it. Names are not masked.

The viewer (standard library only) replays saved runs with an overview (accuracy, outcomes, confidence vs. accuracy, cost) and shows any ticket stage by stage, including exactly what each model was sent and returned. You can also paste a new ticket and watch it go through live. Screenshots: [`docs/demo/`](docs/demo/).

| Model role | Model | Used for |
|---|---|---|
| classifier | Claude Haiku 5.5 | classify and extract; the fee and the team-note summary |
| rechecker, drafter | Claude Sonnet 5.5 | the second opinion; the draft reply |
| generator, evaluator | Claude Opus 5.5 | development only: writing tickets, grading drafts |

Any model is one line in [`config/models.yaml`](config/models.yaml). Each API run is priced from its token counts and stops at a spending cap (`budget_usd`, default $5).

## Repo layout

```
src/pipeline/   clean, classify, gate, route, draft, draft_check, handoff, requirements, run, llm
config/         taxonomy, thresholds, models (and prices), policy (empty on purpose)
app/            the viewer
scripts/        run_batch, experiment (with/without tests, judge), calibrate, review_sheet, generate_tickets
data/           dev, mvp_test, heldout, test2, heldout2 (sealed); probes/ older test sets; review/ the author's checks
docs/           experiments/ (LOG.md, AUDIT, per-set pages), runs/ (the final test, replayable), demo/ screenshots, design brief
CONTEXT.md      goals, rules, decisions and status, for anyone picking the project up
```

## Disclosure

- All data is synthetic. No real customer data is used anywhere.
- Claude Code was used as a coding assistant. Claude Opus wrote the synthetic tickets and grades drafts during development.
