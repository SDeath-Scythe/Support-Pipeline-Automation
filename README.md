# Support Pipeline Automation

**Agentic AI Challenge Iraq · Topic 06**
By Salih Safaa Mohammed

A batch pipeline that sorts customer support tickets written in **Iraqi Arabic dialect** and pre-drafts the replies. A human approves, edits or takes over every ticket. **Nothing is ever sent automatically.**

## The user

A Level-1 support agent at a private-sector company, handling roughly 100–150 tickets a day. Most are repetitive: failed transfers, wrong recipients, login and OTP problems, agent disputes.

## How it works

```
Ticket batch → Clean → Classify + extract → Confidence gate → Route + priority → Draft reply → Human review
   (input)     (rules)     (Haiku 5.5)          (rules)           (rules)        (Sonnet 5.5)   (approve/edit)
                                                   │
                                                   └── low confidence or fraud → escalated with a note
```

A fixed workflow, not a free-roaming agent: predictable and testable. LLMs are used only where judgment is needed.

**Confidence gate**
- The model's score is lowered when a rule disagrees: a required field is missing, or an extracted reference doesn't appear in the ticket text.
- Above 0.75 → continues. 0.60–0.75, or a high-risk subcategory → a second model re-checks; if it disagrees, escalate.
- Under 0.60 → escalate. Fraud and security tickets are always escalated.

**Three outcomes:** drafted (ready to approve), flagged (one field to check), escalated (no draft, a note explains why).

**Grounding:** drafts may only state facts from [`config/policy.yaml`](config/policy.yaml). No invented timelines, fees or outcomes.

## Models

Each role reads its model from [`config/models.yaml`](config/models.yaml), so any model can be swapped by changing one line.

| Role | Model | Where |
|---|---|---|
| classifier | Claude Haiku 5.5 | Live pipeline |
| drafter, rechecker | Claude Sonnet 5.5 | Live pipeline |
| generator, evaluator | Claude Opus 5.5 | Development only (synthetic data, grading) |

## Repo layout

```
config/       taxonomy (8 categories, 23 subcategories), models, thresholds, policy facts
src/pipeline/ clean, gate, route, llm wrapper (classify and draft come next)
tests/        unit tests for the rule-based stages
data/         synthetic tickets and the dev / MVP test / held-out split
docs/         design brief
```

## Run

```bash
pip install -r requirements.txt
cp .env.example .env        # add your ANTHROPIC_API_KEY
pytest
```

## Status

| Week | Plan | Status |
|---|---|---|
| 18–22 Oct | Brief, repo, category tree, generator prompt, first 50 tickets | In progress |
| 23–29 Oct | All 400 tickets, hand-check, split; classify + extract; first dev results | |
| 30 Oct–5 Nov | Confidence gate, routing, drafts, batch runner, demo pages | Gate and routing started early |
| 6–8 Nov | MVP test run, one-page update, submit | |

## Disclosure

- All data is synthetic. Account details are masked before logging.
- Claude Code is used as a coding assistant. Claude Opus generates the synthetic tickets and grades drafts during development.
