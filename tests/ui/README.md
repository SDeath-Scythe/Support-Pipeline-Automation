# Browser smoke test

Run `node tests/ui/smoke.cjs` from the repo root (needs Node with Playwright and its Chromium; `--screens <dir>` also saves screenshots, `--pass desk-light` runs one of the four passes). It starts its own viewer with no API key and `PIPELINE_MODE=off`, so no model is called, and writes decisions to a temporary file; it exits non-zero if any check fails.
