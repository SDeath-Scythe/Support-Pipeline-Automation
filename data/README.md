# Data

All tickets are **synthetic**. No real customer data is used anywhere in this project.

## Plan (400 tickets)

| Set | Size | Used for |
|---|---|---|
| `dev/` | 240 | Prompt work and threshold tuning |
| `mvp_test/` | 80 | Results reported at the MVP (08/11) |
| `heldout/` | 80 | Generated in a separate run and not looked at until the progress review |

Every subcategory appears at least 3 times in each test set (23 × 3 = 69 ≤ 80), and in dev.

## How tickets are made

`scripts/generate_tickets.py` (seeded, deterministic plan; model calls on the cli backend):

- A spec list per split from its seed: subcategory (the category mix of a real L1 day, after at least 3 per subcategory), dialect (Baghdadi / southern / Mosuli), style (short, long, typos, mixed English, voice-note style, Arabizi capped at 3%), difficulty, and a tagged **edge case** for about 18% (missing or fake reference, two issues, off-topic, prompt injection, negation, phone instead of a reference, amount slang, USD amount, fraud hidden as the second issue).
- The `generator` role (Opus) writes about 10 tickets per call, as JSON. It writes `{REF}` and `{PHONE}`; code fills them (references: 7–10 digits, with dashes, spaces, Arabic-Indic digits or a 2-letter prefix; phones: fake `07[3-9]XXXXXXXX`), so the gold value is what code inserted. The amount is fixed in the spec, so gold amounts are exact. No real company, brand, bank or person names (checked against a block list).
- Code checks every ticket: schema and taxonomy keys, placeholders used as specified, the reference really in the text (`gate.reference_in_text`), no invented long numbers, no brand names, style sanity, and near-duplicates (normalised similarity > 0.85) against every other split and the probe sets. Failed specs are regenerated until each split is full.
- **Priority and outcome come from code**: the taxonomy and routing rules with the recommended flags on (F7: "هسه" alone does not raise priority). Outcome: escalated for fraud, flagged if a required field is missing, otherwise drafted.
- **Blind audit:** the `evaluator` role (Opus) labels every ticket without seeing its gold label. A disagreement never changes gold; it goes into `review_reason`. `review_reason` also marks every ticket containing "هسه" (priority check) and every two-issue ticket.
- **heldout** was generated in its own run with its own seed, and only its statistics were printed. Keep it unread until the progress review.
- Hand check: `data/review/handcheck_80.csv` (columns ok / fix / note left blank, for Google Sheets).

## Dataset (generated 23 Oct 2026)

| | dev | mvp_test | heldout | total |
|---|---|---|---|---|
| Tickets | 240 | 80 | 80 | 400 |
| transfers (25% target) | 60 | 19 | 19 | 98 |
| account_access (15% target) | 36 | 12 | 12 | 60 |
| agents_cash (15% target) | 36 | 10 | 10 | 56 |
| bills_topup (12% target) | 29 | 9 | 9 | 47 |
| general (10% target) | 24 | 12 | 12 | 48 |
| cards (8% target) | 19 | 6 | 6 | 31 |
| verification (8% target) | 19 | 6 | 6 | 31 |
| fraud_security (7% target) | 17 | 6 | 6 | 29 |
| Fewest tickets in any subcategory | 5 | 3 | 3 | 3 |
| Dialect: baghdadi | 123 | 35 | 28 | 186 |
| Dialect: southern | 77 | 25 | 25 | 127 |
| Dialect: mosuli | 40 | 20 | 27 | 87 |
| Style: short | 79 | 26 | 25 | 130 |
| Style: long | 38 | 14 | 13 | 65 |
| Style: typos | 37 | 9 | 13 | 59 |
| Style: mixed_english | 35 | 12 | 14 | 61 |
| Style: voice_note_style | 44 | 18 | 14 | 76 |
| Style: arabizi | 7 | 1 | 1 | 9 |
| Difficulty: easy | 72 | 29 | 37 | 138 |
| Difficulty: medium | 98 | 29 | 19 | 146 |
| Difficulty: hard | 70 | 22 | 24 | 116 |
| Tagged edge cases | 43 | 14 | 14 | 71 |
| Outcome: drafted | 200 | 69 | 66 | 335 |
| Outcome: flagged | 23 | 5 | 8 | 36 |
| Outcome: escalated | 17 | 6 | 6 | 29 |
| Priority: P1 | 42 | 14 | 10 | 66 |
| Priority: P2 | 94 | 30 | 33 | 157 |
| Priority: P3 | 104 | 36 | 37 | 177 |
| Audit disputed (in review) | 3 | 0 | 2 | 5 |
| Any review_reason | 70 | 25 | 22 | 117 |
| Generator calls (Opus) | 26 | 10 | 9 | 45 |
| Audit calls (Opus) | 24 | 8 | 8 | 40 |

Each split's `build_info.json` records its seed, model calls, rejected drafts (brand name, near-duplicate, USD not stated) and audit disputes.

Regenerate (model replies are cached under `runs/generation/`, so a re-run with the same seed reuses them; delete that folder for fresh tickets):

```bash
python scripts/generate_tickets.py build --split dev      --seed 1001 --n 240
python scripts/generate_tickets.py build --split mvp_test --seed 2002 --n 80
python scripts/generate_tickets.py build --split heldout  --seed 3003 --n 80   # separate run; prints statistics only
python scripts/generate_tickets.py handcheck --seed 4004
python scripts/generate_tickets.py stats                                       # coverage tables, no ticket text
```

## Labels (one JSON object per ticket, `.jsonl`)

```json
{"id": "dev-0001", "text": "…", "category": "transfers", "subcategory": "not_received",
 "secondary_subcategory": null, "reference": "4471-9032", "recipient_phone": null,
 "amount_iqd": 50000, "amount_usd": null, "date": "البارحة", "priority": "P2", "outcome": "drafted",
 "dialect": "baghdadi", "style": "short", "difficulty": "easy", "edge_case": null,
 "split": "dev", "batch": "r1_b03", "generator_model": "claude-opus-5-5", "review_reason": null}
```

## Probe sets used in experiments (`probes/`)

| File | Tickets | Use |
|---|---|---|
| `edge_cases.jsonl`, `mixed_30.jsonl`, `synthetic_20.jsonl` | 15, 30, 20 | Early probes and smoke tests |
| `fixes_30.jsonl` | 30 | Rounds 1–2 of the fix experiments |
| `dev_95.jsonl` | 95 | The four sets above joined (generated, same lines), the round-3 dev set |
| `holdout_30.jsonl` | 30 | Sealed: only run for the final round-3 check |
