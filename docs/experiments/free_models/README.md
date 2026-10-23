# Free models: test setup

A **test**, not calibration: can free-tier models run this pipeline on Iraqi-dialect tickets, and how do they compare with the Claude setup on the same tickets?

## Results, 23 Oct 2026 (holdout_30, recommended fixes on)

Full table: [holdout_30.md](holdout_30.md). Per-ticket pages: `../holdout_30/free-groq.md`, `../holdout_30/free-google.md`.

| | Claude (Haiku + Sonnet) | Groq (Qwen 3.8 27B + gpt-oss-120b) | Google (Gemma 4 31B + Gemini 3.5 Flash) |
|---|---|---|---|
| Ticket type correct | 29/30 | 26/30 | 27/30 |
| Wrong type reaching a draft | 1 | 4 | 1 |
| Draft given when it should be | 30/30 | 30/30 | 20/30 ⚠ |
| Priority correct | 30/30 | 27/30 | 27/30 |
| Fee correct | 2/2 | 1/2 | 0/2 |
| Bad drafts (judge) | 1 | 8 | 1 (of 20) |
| Mean draft score (1–5) | 4.64 | 4.21 | 4.56 (of 20) |
| Failed model calls | 0 | 0 | 10 tickets ⚠ |
| Cost | ≈ $0.26 (cli-reported) | $0 | $0 |

**Reading it:**
- **Groq works reliably on the free tier** (no failures, about 22 s per ticket), but it is clearly weaker: 4 wrong types reached a draft (vs 1) and 8 bad drafts (vs 1). The drafts often promise an update "قريباً" (soon), a fact they weren't given, and sometimes slip into non-Iraqi wording ("إنّو"). Its classification misses are the same look-alike pairs as Claude's (fee question vs not received, top-up vs cash-in, wrong recipient vs reversal).
- **Google's quality is close to Claude's where it ran** (mean 4.56 and 1 bad draft over 20 drafts), but **its free tier could not finish the test**. Gemini 3.5 Flash hit the daily free quota ("You exceeded your current quota"), so 8 calls failed and those tickets were escalated. Two more failed because Gemma returned extra text after its JSON. The parser now reads the first complete JSON object; that's a robustness fix for every model.
- **Mistral did not run:** the key's limit is 0 requests per minute, so the free "Experiment" plan isn't active on that account (phone verification at console.mistral.ai).
- **mixed did not run:** it depends on the same exhausted Gemini quota.

**What it suggests (one run each, not calibration):** none of the free options matches the Claude setup on this pipeline as-is. Google is the closest in quality but its free quota is too small for a real batch of 100–150 tickets a day. Groq has the capacity but produces more risky drafts, which the F2 draft checks partly catch; adding "قريباً" to the promise rule would catch most of them. The prompts were tuned on Claude, so other models might improve with model-specific wording. That would be its own with/without test.

**To finish the test:** once the Gemini quota resets (daily), run `python scripts/run_free_models.py --profiles google mixed`. Calls that already succeeded are reused from the cache, so only the failed ones are re-sent. Activate the Mistral plan, then add `mistral`.

## Which models, and why

Models were picked from the **Mizan** benchmark ([arXiv 2609.13980](https://arxiv.org/abs/2609.13980), Sept 2026), the only published evaluation found with an Iraqi-dialect track (27 systems, a 340-item pilot). Among models with a free API tier:

| Model | Iraqi track | Free access | Used in profile |
|---|---|---|---|
| gemini-2.5-flash | 83.6 | Google AI Studio (closed to new users by Oct 2026; replaced by gemini-3.5-flash) | `google`, `mixed` |
| llama-4-maverick | 83.0 | Groq (no longer served by Oct 2026) | — |
| gemma-3-27b-it / **gemma-4-31b-it** | 82.7 / **82.4** | Google AI Studio (Gemma 4 is what the key lists) | `google` (classify) |
| gpt-oss-120b | 82.0 | Groq | `groq` (re-check, draft), `mixed` (re-check) |
| mistral-saba (Arabic-focused) | 80.9 | Mistral (no longer served; Mistral Medium used instead) | — |
| llama-3.3-70b | 79.1 | Groq (no longer served; Qwen 3.8 27B classifies instead) | — |
| *claude-haiku-4-5, for reference* | *81.9* | | |

**Not used:** the Arabic-specialised 7–9B models (ALLaM-7B 64.7, SILMA-9B 63.2). The paper finds they score about 10 points *below* general models of the same size on Iraqi Arabic, because their specialisation is mostly Modern Standard Arabic.

Each profile pairs two **different** models for classify and re-check. Round 3 showed the re-check only catches errors when the second opinion can disagree (F3c).

## How it works

- `config/free_models.yaml` defines the providers (OpenAI-compatible URL, key variable, rate limit) and the profiles (role → provider, model).
- `LLM_PROFILE=<name>` sends the classifier, rechecker and drafter roles to that profile. All other roles, including the **draft judge**, keep `config/models.yaml`, so every profile is judged the same way. Unset, nothing changes.
- `llm.py` spaces the calls to stay under each free tier's requests-per-minute limit, backs off on HTTP 429 and 5xx, and records tokens. Saved runs record the real model names.

## To run it

1. Add one or more keys in the environment settings (Network secrets / environment variables), then start a new session:
   - `GEMINI_API_KEY` (Google AI Studio): profiles `google`, `mixed`
   - `GROQ_API_KEY` (Groq): profiles `groq`, `mixed`
   - `MISTRAL_API_KEY` (Mistral): profile `mistral`
2. Check what each key can reach (and fix model ids if a provider renamed them):
   ```bash
   python scripts/check_free_models.py
   ```
3. Run every profile that has keys:
   ```bash
   python scripts/run_free_models.py                # holdout_30 by default
   ```
   This writes `docs/experiments/free_models/holdout_30.md`: a table of each profile against the Claude setup, all with the recommended fixes on.

## Caveats

- One run per profile: classification moves about ±2 tickets on 95 between identical runs, and draft scores about ±0.1.
- The judge is a Claude model and may prefer Claude-style drafts; a person checking a sample is the real test (see HANDOVER.md, recommendation 1).
- The prompts were written and tuned with Claude models; other models may need different wording to do their best. This test measures them as-is.
- Free tiers rate-limit, so seconds per ticket here aren't production latency.
- Free tiers may use your inputs for training, so use synthetic tickets only, never real customer data.
