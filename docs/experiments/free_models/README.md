# Free models: test setup

A **test**, not calibration: can free-tier models run this pipeline on Iraqi-dialect tickets, and how do they compare with the Claude setup on the same tickets?

## Which models, and why

Models were picked from the **Mizan** benchmark ([arXiv 2609.13980](https://arxiv.org/abs/2609.13980), Sept 2026), the only published evaluation found with an Iraqi-dialect track (27 systems, a 340-item pilot). Among models with a free API tier:

| Model | Iraqi track | Free access | Used in profile |
|---|---|---|---|
| gemini-2.5-flash | 83.6 | Google AI Studio | `google` (re-check, draft), `mixed` |
| llama-4-maverick | 83.0 | Groq | `groq` (draft), `mixed` (re-check) |
| gemma-3-27b-it | 82.7 | Google AI Studio | `google` (classify) |
| gpt-oss-120b | 82.0 | Groq | `groq` (re-check) |
| mistral-saba (Arabic-focused) | 80.9 | Mistral | `mistral` (re-check, draft) |
| llama-3.3-70b | 79.1 | Groq | `groq` (classify) |
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
