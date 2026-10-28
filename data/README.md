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
- Code checks every ticket: schema and taxonomy keys, placeholders used as specified, the reference really in the text (`gate.reference_in_text`), no invented long numbers, no brand names, style sanity, "ورقة" only where the spec asks for dollar notes, no Mosuli غ for ر. Failed specs are regenerated until each split is full.
- **Variety:** a ticket is rejected if it is a near-duplicate of any ticket in any split or in `probes/`: normalised characters more than 0.8 similar, or content words more than 0.5 similar with common dialect variants folded (this catches the same sentence rewritten in another dialect, like dev-0083 / dev-0138 in the first build). A ticket is also rejected if it would put any dialect marker word in more than 10% of its split; the build fails if any marker is above 15%. From round 2 the generator is told which marker words are already at the cap (`avoid_words`), and from round 7 a spec whose draft was a near-duplicate gets that draft back (`too_similar_to`) with a request for a clearly different ticket.
- **Priority and outcome come from code**: the taxonomy and routing rules with the recommended flags on. With F15, gold priority is the subcategory's `default_priority`, raised one level only for an amount of 1,000,000 IQD or more; no word changes it. Outcome: escalated for fraud, flagged if a required field is missing, otherwise drafted.
- **Blind audit:** the `evaluator` role (Opus) labels every ticket without seeing its gold label, using the classifier rules with F16 ("ورقة" = 100 USD). A disagreement never changes gold; it goes into `review_reason`. `review_reason` also marks every two-issue ticket and every ticket whose amount is in ورقة.
- **heldout** was generated in its own run with its own seed, and only its statistics were printed. Keep it unread until the progress review.
- Hand check: `data/review/handcheck_80.csv` (columns ok / fix / note left blank, for Google Sheets), from dev and mvp_test only: every audit dispute, every two-issue ticket and every ticket with "ورقة" or a USD amount, then at least 30 random tickets spread across subcategories and dialects.

## Corrections from the project author (a native Iraqi speaker), 23 Oct

The first build (seeds 1001 / 2002 / 3003) was replaced because of three corrections:

1. **"ورقة" is a 100 USD note.** "خمسين ورقة" = 50 × 100 = 5,000 USD (`amount_usd` 5000); "خمسين الف" = 50,000 IQD. The first build used "خمسين ورقة" for 50,000 IQD, as the classifier prompt's example did (fixed behind F16 `warqa_usd`). Now "ورقة" appears only where the spec gives `usd_as_warqa`, and gold `amount_usd` = count × 100.
2. **Mosuli does not spell ر as غ** ("اعغفها", "شهغ", "انتظغ" are wrong). The prompt uses other Mosuli features (ق kept, ايش) and standard spelling when unsure; code rejects known غ-for-ر forms.
3. **No word raises priority**, not "هسه", "ضروري", "عاجل", "بسرعة", "صارلي يومين" or any other. Gold priority is the subcategory default, raised one level only for ≥ 1,000,000 IQD (F15 `no_urgency_words`, which supersedes F7).

Also: "هسه" was in 26% of the first build's tickets and was one of the prompt's dialect examples; it is no longer an example, and each marker word is capped as above.

## Dataset (regenerated 23 Oct 2026, seeds 1101 / 2202 / 3303)

| | dev | mvp_test | heldout | total |
|---|---|---|---|---|
| Seed | 1101 | 2202 | 3303 | |
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
| Dialect: baghdadi | 120 | 38 | 40 | 198 |
| Dialect: southern | 67 | 25 | 24 | 116 |
| Dialect: mosuli | 53 | 17 | 16 | 86 |
| Style: short | 67 | 29 | 27 | 123 |
| Style: long | 52 | 18 | 17 | 87 |
| Style: typos | 31 | 14 | 12 | 57 |
| Style: mixed_english | 46 | 10 | 10 | 66 |
| Style: voice_note_style | 37 | 7 | 12 | 56 |
| Style: arabizi | 7 | 2 | 2 | 11 |
| Difficulty: easy | 90 | 28 | 29 | 147 |
| Difficulty: medium | 88 | 32 | 32 | 152 |
| Difficulty: hard | 62 | 20 | 19 | 101 |
| Tagged edge cases | 43 (17.9%) | 14 (17.5%) | 14 (17.5%) | 71 |
| Outcome: drafted | 198 | 65 | 64 | 327 |
| Outcome: flagged | 25 | 9 | 10 | 44 |
| Outcome: escalated | 17 | 6 | 6 | 29 |
| Priority: P1 | 28 | 10 | 11 | 49 |
| Priority: P2 | 90 | 28 | 27 | 145 |
| Priority: P3 | 122 | 42 | 42 | 206 |
| amount_usd (of which as ورقة) | 8 (6) | 2 (1) | 4 (4) | 14 (11) |
| Two-issue tickets | 9 | 3 | 3 | 15 |
| Audit disputed (in review) | 5 | 0 | 3 | 8 |
| Any review_reason | 19 | 4 | 9 | 32 |
| Generator calls (Opus) | 37 | 18 | 14 | 69 |
| Audit calls (Opus) | 49 | 9 | 8 | 66 |

Dev's audit calls include one full re-audit: a bug in the ورقة check (it only read Arabic script, so an Arabizi "5 wara8a" ticket was rejected nine times) was fixed mid-build, and the fix changed the filled-in numbers, so every dev ticket was audited again.

Across all 400 tickets, no pair is above 0.8 on characters or 0.5 on content words (the closest pair is 0.76 on characters), and no ticket is a near-duplicate of a probe. No draft was rejected for Mosuli غ-for-ر.

### Marker words (% of tickets in the split)

Cap 10% at acceptance, build fails above 15%. Words not listed (شكو، بلكي، لعد، خوش، عيني، اغاتي، يابه) are at 0%. "اريد" is not counted, because it is also standard Arabic (أريد).

| Word | dev | mvp_test | heldout |
|---|---|---|---|
| هسه | 10.0% | 10.0% | 10.0% |
| ايش | 10.0% | 10.0% | 10.0% |
| شلون | 10.0% | 10.0% | 6.2% |
| شنو | 10.0% | 5.0% | 8.8% |
| گلت / گال | 9.2% | 10.0% | 5.0% |
| ماكو | 7.5% | 5.0% | 6.2% |
| ليش | 6.7% | 5.0% | 1.2% |
| شنهو | 5.8% | 6.2% | 5.0% |
| هيج | 4.6% | 3.8% | 2.5% |
| اكو | 4.2% | 6.2% | 10.0% |
| يمعود | 4.2% | 8.8% | 8.8% |
| صارلي | 4.2% | 5.0% | 2.5% |
| ويا | 2.9% | 2.5% | 0.0% |
| هواي | 2.9% | 2.5% | 5.0% |
| كلش | 2.5% | 2.5% | 2.5% |
| شگد / شكد | 2.1% | 5.0% | 1.2% |
| چان | 1.7% | 1.2% | 1.2% |
| *Urgency words (F15: no effect on priority)* | | | |
| ضروري | 9.6% | 10.0% | 8.8% |
| بسرعة | 4.2% | 6.2% | 3.8% |
| عاجل | 1.2% | 0.0% | 0.0% |

### Repair after the hand-check (28 Oct 2026)

The author's hand-check (80 rows: 71 correct, 9 with a wrong label) found three things code didn't check. Instead of rebuilding, only the tickets that break a rule were replaced (`generate_tickets.py repair`); every other ticket keeps its text, including all 71 the author approved.

1. **One issue per ticket.** Most people raise one problem, not two unrelated ones. A second issue is now always drawn from `RELATED`, pairs that come from the same situation (same transfer, agent visit or app session), and the generator is told the link. Tickets whose second issue wasn't related were rewritten.
2. **Iraqi dialect only.** Code now rejects Levantine, Gulf, Egyptian and standard-Arabic forms (`DRIFT`: بدي، هيك، كتير، بقدر، شو، وايد، كذا، مش، عايز، لقد، سوف، الذي…). كيف (Mosuli) and ابي (Basra) are allowed. The 2026 Mizan benchmark for Iraqi Arabic names "fusha in disguise" as the main failure of model-written dialect data; this build has no standard-Arabic hits.
3. **No repeated stories.** The off-topic edge case had produced "dollar rate + weather" five times. Off-topic tickets now get their own topic, handed out in order (`OFF_TOPIC_TOPICS`), and one dollar-rate ticket is kept (dev-0068). A replacement ticket is shown the other tickets of its type and told to describe a different situation.

Also from the hand-check: a support-request number is never a transaction reference, and `login_otp` means the same phone and SIM (a new phone or SIM is `sim_change`).

| | dev | mvp_test | heldout |
|---|---|---|---|
| Replaced | 13 | 6 | 5 |
| Unrelated second issue | 7 | 2 | 2 |
| Dialect drift | 2 | 1 | 2 |
| Story repeat / hand-check | 4 | 3 | 1 |

mvp-0003 (drift) was replaced twice: the first replacement told a phone-change story, which is `sim_change`, not its `login_otp` label.

Each split's `build_info.json` lists every replaced ID with its reason under `repairs`. Heldout was repaired by code only; its text was not read. The new tickets were blind-audited; disputes are in `review_reason`, which also says `repaired: <reason>`.

**Gold labels were recomputed for all 400 tickets** with the author's rules F18 (`reference_when_needed`: no transaction number is required when the recipient's phone identifies the transfer, or for a reversal request) and F19 (`usd_large_amount`: ≥ 750 USD raises priority like ≥ 1,000,000 IQD; dollars are never converted). This matches the author's 8 label corrections on the sheet. After the repair:

| | dev | mvp_test | heldout |
|---|---|---|---|
| Outcome: drafted / flagged / escalated | 208 / 15 / 17 | 68 / 6 / 6 | 67 / 7 / 6 |
| Priority: P1 / P2 / P3 | 31 / 87 / 122 | 10 / 28 / 42 | 13 / 25 / 42 |

The 14 replaced rows on the hand-check sheet have the new text, and their «صحيح؟» is cleared for re-checking.

### Hand-check sheet (`review/handcheck_80.csv`, seed 4404)

80 rows: 63 dev, 17 mvp_test, no heldout. All 26 must-check tickets (5 audit disputes, 12 two-issue, 9 with ورقة or a USD amount) plus 54 random tickets chosen to spread across subcategories and dialects (random: 21 southern, 19 Mosuli, 14 Baghdadi). All 23 subcategories appear. Rows are shuffled.

Each split's `build_info.json` records its seed, model calls, rejected drafts and audit disputes.

Regenerate (model replies are cached under `runs/generation/<split>-s<seed>/`, so a re-run with the same seed reuses them; a new seed starts fresh):

```bash
python scripts/generate_tickets.py build --split dev      --seed 1101 --n 240
python scripts/generate_tickets.py build --split mvp_test --seed 2202 --n 80
python scripts/generate_tickets.py build --split heldout  --seed 3303 --n 80   # separate run; prints statistics only
python scripts/generate_tickets.py repair --split dev --dry-run               # then without --dry-run; same for each split
python scripts/generate_tickets.py handcheck --seed 4404
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
