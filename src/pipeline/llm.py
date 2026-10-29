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

Comparison tests only: set LLM_PROFILE to a profile in config/free_models.yaml to send the
classifier, rechecker and drafter roles to free-tier models through their OpenAI-compatible
APIs (keys from the environment). Other roles keep config/models.yaml. Unset, nothing changes.

Experiments only: set LLM_CACHE_DIR to reuse the reply to an identical call (same
model, system and user prompt). Runs with and without a fix then differ only where the
fix changes a model's input, not because the model answered differently a second time.
The key also names the backend for every non-cli backend (api, or openai:<provider>), so an
API run never gets a stored cli reply back; cli keys are unchanged, so old cli entries stay valid.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

from .config import llm_backend, load_yaml, models

load_dotenv()

BACKENDS = ("api", "cli")

# Keys that would make Claude Code bill the API instead of the Claude plan.
_API_ENV_KEYS = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")

_client = None

# Token use of the last call made on this thread (each ticket runs on one thread).
_usage = threading.local()


def last_usage() -> dict:
    """Tokens (and, on cli, the cost Claude Code reports) of this thread's last call.

    {"input_tokens", "output_tokens", "cost_usd"?, "cached"?}. Empty if unknown.
    """
    return dict(getattr(_usage, "value", {}))


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
    # No temperature: Haiku 5.5 and Sonnet 5.5 reject a non-default value, and API version
    # 2026-10-21 rejects it on every model (models.yaml keeps it for the free-model profiles).
    # These models think by default; `effort` sets how much, and thinking counts toward max_tokens.
    extra = {"output_config": {"effort": cfg["effort"]}} if cfg.get("effort") else {}
    resp = _get_client().messages.create(
        model=cfg["model"],
        max_tokens=cfg["max_tokens"],
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
        **extra,
    )
    u = resp.usage
    _usage.value = {"input_tokens": u.input_tokens + (getattr(u, "cache_read_input_tokens", 0) or 0)
                    + (getattr(u, "cache_creation_input_tokens", 0) or 0), "output_tokens": u.output_tokens}
    text = "".join(block.text for block in resp.content if block.type == "text")
    if not text:
        raise RuntimeError(f"No reply text from {cfg['model']} (stop_reason={resp.stop_reason})")
    return text


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
    u = data.get("usage") or {}
    _usage.value = {"input_tokens": sum(u.get(k, 0) or 0 for k in
                                        ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")),
                    "output_tokens": u.get("output_tokens", 0), "cost_usd": data.get("total_cost_usd")}
    return data["result"]


def _salt(role: str | None) -> str:
    """LLM_CACHE_SALT="drafter=r1" gives that role fresh replies (a new cache slot) while
    other roles keep theirs: used to replicate drafts with the classification held fixed."""
    pairs = dict(p.split("=", 1) for p in os.getenv("LLM_CACHE_SALT", "").split(",") if "=" in p)
    return pairs.get(role or "", "")


def _cached(cfg: dict, system: str, user: str, send, role: str | None = None,
            backend_tag: str | None = None) -> str:
    """Return the stored reply for this exact call, or make it once and store it.

    A lock directory per key stops two parallel runs paying for the same call twice.
    `backend_tag` is None for cli (keys unchanged from before it existed) and names any other
    backend, so the same model and prompts on the API never return a cli reply.
    """
    cache_dir = os.getenv("LLM_CACHE_DIR")
    if not cache_dir:
        return send(cfg, system, user)
    parts = ([cfg["model"], system, user] + ([_salt(role)] if _salt(role) else [])
             + ([f"backend={backend_tag}"] if backend_tag else []))
    key = hashlib.sha256(json.dumps(parts).encode("utf-8")).hexdigest()
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
            stored = json.loads(path.read_text(encoding="utf-8"))
            _usage.value = {**stored.get("usage", {}), "cached": True}
            return stored["reply"]
        reply = send(cfg, system, user)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"model": cfg["model"], "reply": reply, "usage": last_usage()},
                                  ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)
        return reply
    finally:
        shutil.rmtree(lock, ignore_errors=True)


# --- free-model profiles (comparison tests; see config/free_models.yaml) ---

_rate_lock = threading.Lock()
_next_slot: dict[str, float] = {}


def profile_route(role: str) -> dict | None:
    """The provider/model a role is sent to under LLM_PROFILE, or None to use models.yaml."""
    name = os.getenv("LLM_PROFILE")
    if not name:
        return None
    raw = load_yaml("free_models.yaml")
    if name not in raw["profiles"]:
        raise BackendError(f"Unknown LLM_PROFILE '{name}'. Use one of: {', '.join(raw['profiles'])}.")
    entry = raw["profiles"][name].get(role)
    if entry is None:
        return None
    provider, model, *opts = entry
    return {**raw["providers"][provider], "provider": provider, "model": model,
            "merge_system": "merge_system" in opts,
            # free models include reasoning models that spend tokens before answering
            "max_tokens": max(models()[role]["max_tokens"], 4096),
            "temperature": models()[role]["temperature"]}


def model_for(role: str) -> str:
    """The model a role actually uses (profile model, or the one in config/models.yaml)."""
    route = profile_route(role)
    return f"{route['provider']}/{route['model']}" if route else models()[role]["model"]


def _wait_turn(provider: str, rpm: float) -> None:
    """Space calls to one provider so a free tier's requests-per-minute limit is respected."""
    with _rate_lock:
        now = time.time()
        slot = max(now, _next_slot.get(provider, 0.0))
        _next_slot[provider] = slot + 60.0 / rpm
    time.sleep(max(0.0, slot - now))


def _call_openai(cfg: dict, system: str, user: str) -> str:
    key = os.getenv(cfg["key_env"])
    if not key:
        raise BackendError(f"{cfg['key_env']} is not set (needed for {cfg['provider']}).")
    messages = ([{"role": "user", "content": f"{system}\n\n{user}"}] if cfg.get("merge_system")
                else [{"role": "system", "content": system}, {"role": "user", "content": user}])
    body = {"model": cfg["model"], "messages": messages,
            "temperature": cfg["temperature"], "max_tokens": cfg["max_tokens"]}
    for attempt in range(6):
        _wait_turn(cfg["provider"], float(cfg.get("rpm", 10)))
        req = urllib.request.Request(
            cfg["base_url"].rstrip("/") + "/chat/completions", data=json.dumps(body).encode("utf-8"),
            # A named User-Agent: Groq's Cloudflare front blocks Python's default one (error 1010).
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                     "User-Agent": "support-pipeline-test/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=cfg.get("timeout_s", 180)) as resp:
                data = json.load(resp)
            break
        except urllib.error.HTTPError as e:
            detail = e.read()[:300].decode("utf-8", "replace")
            if e.code in (429, 500, 502, 503, 504) and attempt < 5:   # rate limit or busy: back off
                time.sleep(float(e.headers.get("Retry-After") or 0) or min(60, 5 * 2 ** attempt))
                continue
            raise RuntimeError(f"{cfg['provider']} HTTP {e.code} for {cfg['model']}: {detail}") from None
    text = data["choices"][0]["message"].get("content") or ""
    u = data.get("usage") or {}
    _usage.value = {"input_tokens": u.get("prompt_tokens", 0), "output_tokens": u.get("completion_tokens", 0),
                    "provider": cfg["provider"], "model": cfg["model"]}
    return text


def call(role: str, system: str, user: str, *, retries: int = 1) -> str:
    """Send one message for `role` and return the text reply.

    Retries once on failure; the caller escalates the ticket if it still fails.
    """
    route = profile_route(role)
    cfg = route or models()[role]
    _usage.value = {}
    send = _call_openai if route else (_call_api if backend() == "api" else _call_cli)
    tag = f"openai:{route['provider']}" if route else (None if backend() == "cli" else backend())
    if tag == "api" and cfg.get("effort"):
        tag = f"api,effort={cfg['effort']}"      # a new effort level gets fresh replies
    last_error: Exception | None = None
    for _ in range(retries + 1):
        try:
            return _cached(cfg, system, user, send, role, tag)
        except Exception as e:  # noqa: BLE001 - surfaced to caller after retry
            last_error = e
    where = f"{route['provider']}/{route['model']}" if route else f"the {backend()} backend"
    raise RuntimeError(f"Model call failed for role '{role}' on {where}") from last_error
