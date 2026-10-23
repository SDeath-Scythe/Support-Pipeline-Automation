# Free models vs Claude on holdout_30

A test on the free tiers, **not calibration**. Same tickets, same fixes on (`F2+F3c+F6b+F7+F11+F12+F14b`), same draft judge (Claude, unchanged) and same scoring for every column.

| | Claude (Haiku + Sonnet) | groq | google |
|---|---|---|---|
| Ticket type correct | 29/30 | 26/30 | 27/30 |
| Wrong type reaching a draft | 1 | 4 | 1 |
| Draft given when it should be | 30/30 | 30/30 | 20/30 |
| Priority correct | 30/30 | 27/30 | 27/30 |
| Fee correct | 2/2 | 1/2 | 0/2 |
| Escalated | 2 | 2 | 12 |
| Bad drafts (judge) | 1 | 8 | 1 |
| Mean draft score (1-5) | 4.64 | 4.21 | 4.56 |
| Model errors (call failed, escalated) | 0 | 0 | 10 |
| Seconds per ticket (incl. rate limits) | cached | 22.1 | 196.8 |

Models per column:

- **Claude (Haiku + Sonnet)**: classifier `claude-haiku-5-5`, re-check `claude-sonnet-5-5`, drafter `claude-sonnet-5-5`
- **groq**: classifier `groq/qwen/qwen3.8-27b`, re-check `groq/openai/gpt-oss-120b`, drafter `groq/openai/gpt-oss-120b`
- **google**: classifier `google/gemma-4-31b-it`, re-check `google/gemini-3.5-flash`, drafter `google/gemini-3.5-flash`

Caveats: one run per column (classification moves about ±2 tickets on 95 between identical runs, draft scores about ±0.1); the judge is a Claude model and may prefer Claude-style drafts; free tiers rate-limit, so seconds per ticket are not production latency.
