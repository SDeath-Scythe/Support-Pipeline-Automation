# Browser smoke test

Run `node tests/ui/smoke.cjs` from the repo root. It needs Node with Playwright and its Chromium, and Python with `requirements.txt` installed: each pass starts its own viewer with `python app/server.py` (set `PYTHON` to use another interpreter). `--screens <dir>` also saves each pass's screenshots, and `--pass <name>` runs one pass: `desk-light`, `desk-dark`, `phone-light`, `phone-dark` or `fresh-clone`. Decisions go to a file in a temporary folder, removed at the end, and it exits non-zero if any check fails.

- The first four passes start their own viewer with no API key and `PIPELINE_MODE=off`, so no model is called. They work on the committed final run (`saved/test2/final`) at desktop width (1366 × 850) and phone width (360 × 780), in light and dark.
- `fresh-clone` starts it as a fresh clone would: no key, no `PIPELINE_MODE`, no `LLM_BACKEND` (so the viewer's default, the API) and no claude CLI. Live runs are then off, and the page says so. It pastes no ticket, and the browser refuses `/api/stream` anyway.

On 1 Nov 2026 (commit d1280b6) it ran 359 checks, all passing: 94 in each desktop pass, 70 in each phone pass and 31 in `fresh-clone`. On 5 Nov 2026, with the three safety rules adopted, it ran 361, all passing: `fresh-clone` has two more, for a blocked-account or SIM-change ticket and its identity tick. After the review of that change it runs 369: 96 in each desktop pass, 71 in each phone pass and 35 in `fresh-clone`. The server now gives the committed run the `account_risk` flag, so the tab counts are 15 / 6 / 59 and no browser route feeds it. A full run takes several minutes; the script gives up after six (exit code 2).

To retake the screenshots in `docs/demo/`:

```bash
node tests/ui/smoke.cjs --pass fresh-clone --demo docs/demo
```

`inbox-done.png` is the session summary after this pass decides all 80 tickets by script, each in well under 3 s: its times are the script's, not a person's, and the page says so («… انحسمت بأقل من 3 ثواني»). The other images show one ticket or view each, in the state a fresh clone gives (no key: live runs are off, and no kill-switch banner).
