# Browser smoke test

Run `node tests/ui/smoke.cjs` from the repo root (needs Node with Playwright and its Chromium). `--screens <dir>` also saves each pass's screenshots, and `--pass <name>` runs one pass: `desk-light`, `desk-dark`, `phone-light`, `phone-dark` or `fresh-clone`. Decisions go to a temporary file, and it exits non-zero if any check fails.

- The first four passes start their own viewer with no API key and `PIPELINE_MODE=off`, so no model is called.
- `fresh-clone` starts it as a fresh clone would: no key, no `PIPELINE_MODE`, no `LLM_BACKEND` (so the viewer's default, the API) and no claude CLI. Live runs are then off, and the page says so. It pastes no ticket, and the browser refuses `/api/stream` anyway.

To retake the screenshots in `docs/demo/`:

```bash
node tests/ui/smoke.cjs --pass fresh-clone --demo docs/demo
```

`inbox-done.png` is the session summary after this pass decides all 80 tickets by script, each in well under 3 s: its times are the script's, not a person's, and the page says so («… انحسمت بأقل من 3 ثواني»). The other images show one ticket or view each, in the state a fresh clone gives (no key: live runs are off, and no kill-switch banner).
