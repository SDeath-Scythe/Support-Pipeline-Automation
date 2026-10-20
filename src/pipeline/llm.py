"""The single place the pipeline talks to a model.

Every call goes through `call(role, ...)`. The role decides the model, read from
config/models.yaml, so any model can be swapped by editing one line.

Two backends, same prompts and same code path:

- `api`  Anthropic API with ANTHROPIC_API_KEY. Required for anything that produces
         a number (accuracy, calibration, thresholds, the MVP and demo runs).
- `cli`  Claude Code in headless mode (`claude -p`) on your own Claude plan.
         Free for development: wiring, smoke tests, reading outputs by eye.
         Claude Code still adds ~2.9k tokens of its own context and ignores
         temperature/max_tokens, so confidence scores are close to, but not the
         same as, the API. Never tune thresholds on it.

Pick one with `backend:` in config/models.yaml, or override per run with the
LLM_BACKEND environment variable.

Experiments only: set LLM_CACHE_DIR to reuse the reply to an identical call (same
model, system and user prompt). Runs with and without a fix then differ only where the
fix changes a model's input, not because the model answered differently a second time.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from dotenv import load_dotenv

from .config import llm_backend, models

load_dotenv()

BACKENDS = ("api", "cli")

# Keys that would make Claude Code bill the API instead of the Claude plan.
_API_ENV_KEYS = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")

_client = None


class BackendError(RuntimeError):
    """Raised when a step needs a backend that is not active."""


def backend() -> str:
    """The active backend: LLM_BACKEND env var first, then config/models.yaml."""
    name = (os.getenv("LLM_BACKEND") or llm_backend()).strip().lower()
    if name not in BACKENDS:
        raise BackendError(f"Unknown LLM backend '{name}'. Use one of: {', '.join(BACKENDS)}.")
    return name


def require_api(purpose: str) -> None:
    """Stop a run that would produce numbers on the dev-only backend.

    Call this at the top of evaluation, calibration and threshold-tuning scripts.
    """
    if backend() != "api":
        raise BackendError(
            f"{purpose} must run on the API backend so the numbers match the real pipeline. "
            "Set LLM_BACKEND=api (and ANTHROPIC_API_KEY in .env)."
        )


def _get_client():
    global _client
    if _client is None:
        import anthropic

        if not os.getenv("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key.")
        _client = anthropic.Anthropic()
    return _client


def _call_api(cfg: dict, system: str, user: str) -> str:
    resp = _get_client().messages.create(
        model=cfg["model"],
        max_tokens=cfg["max_tokens"],
        temperature=cfg["temperature"],
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
    )
    return "".join(block.text for block in resp.content if block.type == "text")


def _cli_command(model: str, system: str) -> list[str]:
    exe = os.getenv("CLAUDE_BIN") or shutil.which("claude") or "claude"
    return [
        exe, "-p",
        "--model", model,
        "--system-prompt", system,      # replaces Claude Code's default prompt
        "--disallowedTools", "*",       # no tools at all. (--tools "" still sent ~14k tokens of
                                        # tool definitions; this brings the extra context to ~2.9k)
        "--output-format", "json",
        "--no-session-persistence",
        "--strict-mcp-config",          # no MCP servers
        "--disable-slash-commands",
        "--setting-sources", "",        # ignore user/project settings
    ]


def _call_cli(cfg: dict, system: str, user: str) -> str:
    # Strip API keys so Claude Code uses the logged-in Claude plan, never API credits.
    env = {k: v for k, v in os.environ.items() if k not in _API_ENV_KEYS}
    proc = subprocess.run(
        _cli_command(cfg["model"], system),
        input=user,                     # via stdin: no argument-length limits
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=cfg.get("timeout_s", 180),
        env=env,
        cwd=tempfile.gettempdir(),      # outside the repo, so no CLAUDE.md is picked up
    )
    if proc.returncode != 0:
        raise RuntimeError(f"claude -p exited {proc.returncode}: {proc.stderr.strip()[:500]}")
    data = json.loads(proc.stdout)
    if data.get("is_error"):
        raise RuntimeError(f"claude -p error: {str(data.get('result'))[:500]}")
    return data["result"]


def _cached(cfg: dict, system: str, user: str, send) -> str:
    """Return the stored reply for this exact call, or make it once and store it.

    A lock directory per key stops two parallel runs paying for the same call twice.
    """
    cache_dir = os.getenv("LLM_CACHE_DIR")
    if not cache_dir:
        return send(cfg, system, user)
    key = hashlib.sha256(json.dumps([cfg["model"], system, user]).encode("utf-8")).hexdigest()
    path = Path(cache_dir) / f"{key}.json"
    lock = path.with_suffix(".lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    while True:
        try:
            lock.mkdir()
            break
        except FileExistsError:
            if time.time() - lock.stat().st_mtime > 600:   # left behind by a crashed run
                shutil.rmtree(lock, ignore_errors=True)
            time.sleep(0.5)
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))["reply"]
        reply = send(cfg, system, user)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"model": cfg["model"], "reply": reply}, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)
        return reply
    finally:
        shutil.rmtree(lock, ignore_errors=True)


def call(role: str, system: str, user: str, *, retries: int = 1) -> str:
    """Send one message for `role` and return the text reply.

    Retries once on failure; the caller escalates the ticket if it still fails.
    """
    cfg = models()[role]
    send = _call_api if backend() == "api" else _call_cli
    last_error: Exception | None = None
    for _ in range(retries + 1):
        try:
            return _cached(cfg, system, user, send)
        except Exception as e:  # noqa: BLE001 - surfaced to caller after retry
            last_error = e
    raise RuntimeError(f"Model call failed for role '{role}' on the {backend()} backend") from last_error
