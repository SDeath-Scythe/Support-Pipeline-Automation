"""The single place the pipeline talks to a model.

Every call goes through `call(role, ...)`. The role decides the model, read from
config/models.yaml, so any model can be swapped by editing one line.

Two backends, same prompts and same code path:

- `api`  Anthropic API with ANTHROPIC_API_KEY (or SUPPORT_PIPELINE_API_KEY). Required for anything that produces
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
LLM_CACHE_ONLY=1 replays the cache and never calls a model: a call with no stored reply raises
CacheMiss, so a replay cannot spend.

Real tickets: set REAL_DATA=1. assert_real_data_safe() then refuses every development path that
would send a ticket somewhere it shouldn't go or keep it unmasked on disk (the cli backend, free-model
profiles, the response cache, an API endpoint other than Anthropic's).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

from .config import llm_backend, load_yaml, models, pipeline_mode

load_dotenv()

BACKENDS = ("api", "cli")

# Where the API key can come from, in order. SUPPORT_PIPELINE_API_KEY is the name the author's
# Claude Code environment uses; ANTHROPIC_API_KEY (or .env) works as before.
API_KEY_VARS = ("ANTHROPIC_API_KEY", "SUPPORT_PIPELINE_API_KEY")

# The only API endpoint real tickets may go to (see assert_real_data_safe).
ANTHROPIC_API_URL = "https://api.anthropic.com"

# Keys that would make Claude Code bill the API instead of the Claude plan.
_API_ENV_KEYS = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "SUPPORT_PIPELINE_API_KEY")

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


class BudgetExceeded(RuntimeError):
    """Raised instead of an API call once this run has spent its budget (see models.yaml)."""


class CacheMiss(RuntimeError):
    """Raised under LLM_CACHE_ONLY=1 when the response cache has no reply for a call."""


def _env_on(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")


def real_data() -> bool:
    """True when this process handles real customer tickets (REAL_DATA=1). Fails closed: any value
    but empty, 0, false, no or off counts as on, so a typo («REAL_DATA=y») never drops the guard."""
    return os.getenv("REAL_DATA", "").strip().lower() not in ("", "0", "false", "no", "off")


def cache_only() -> bool:
    return _env_on("LLM_CACHE_ONLY")


def assert_real_data_safe() -> None:
    """Under REAL_DATA=1, refuse the development paths that are fine for synthetic tickets only.

    cli runs a personal Claude Code login; LLM_PROFILE sends tickets to third-party free tiers;
    the response cache stores replies unmasked on disk (cache-only replays it); ANTHROPIC_BASE_URL
    (read by the SDK, also from .env) would send tickets and the key to another host. Called at startup
    by the viewer and run_batch, and again by every call(), so no path skips it.
    """
    if not real_data():
        return
    found = []
    if backend() == "cli":
        found.append("LLM_BACKEND is cli (a personal Claude Code login); use LLM_BACKEND=api")
    base_url = os.getenv("ANTHROPIC_BASE_URL", "").strip().rstrip("/")
    if base_url and base_url != ANTHROPIC_API_URL:
        found.append(f"ANTHROPIC_BASE_URL points away from {ANTHROPIC_API_URL} (tickets and the key would "
                     "go to that host); unset it")
    for var, why in (("LLM_PROFILE", "sends tickets to free-tier models of other providers"),
                     ("LLM_CACHE_DIR", "stores model replies unmasked on disk"),
                     ("LLM_CACHE_ONLY", "replays stored development replies")):
        if os.getenv(var):
            found.append(f"{var} is set ({why}); unset it")
    if found:
        raise BackendError("REAL_DATA=1 refuses to run: " + "; ".join(found) + ".")


# Dollars spent on the API by this process (cache hits cost nothing and are not counted).
_spend_lock = threading.Lock()
_spent = {"usd": 0.0}


def spent_usd() -> float:
    return _spent["usd"]


def budget_usd() -> float:
    """The run's API budget in dollars; 0 means no cap. A cap that is not a finite number of 0 or more
    («nan», «-1», «five») raises BackendError: NaN would compare as never reached and switch the cap off."""
    env = os.getenv("LLM_BUDGET_USD")
    raw = env if env not in (None, "") else (load_yaml("models.yaml").get("budget_usd", 0) or 0)
    try:
        cap = float(raw)
    except (TypeError, ValueError):
        cap = math.nan
    if isinstance(raw, bool) or not math.isfinite(cap) or cap < 0:
        raise BackendError("LLM_BUDGET_USD (or budget_usd in config/models.yaml) must be a number of dollars, "
                           "0 or more (0 = no cap).")
    return cap


_PRICE_KEYS = ("input", "output", "cache_write", "cache_read")


def _price(model: str) -> dict | None:
    """The model's price entry, only if it has all four rates as finite numbers of 0 or more: a partial
    entry would fail after a paid reply, leaving that spend uncounted."""
    p = (load_yaml("models.yaml").get("prices") or {}).get(model)
    ok = isinstance(p, dict) and all(
        isinstance(p.get(k), (int, float)) and not isinstance(p.get(k), bool) and math.isfinite(p[k]) and p[k] >= 0
        for k in _PRICE_KEYS)
    return p if ok else None


def price_usd(model: str, usage) -> float | None:
    """Cost of one API response from its usage block, or None if the model has no (complete) price."""
    p = _price(model)
    if not p:
        return None
    tokens = {"input": usage.input_tokens, "output": usage.output_tokens,
              "cache_write": getattr(usage, "cache_creation_input_tokens", 0) or 0,
              "cache_read": getattr(usage, "cache_read_input_tokens", 0) or 0}
    return sum(tokens[k] * p[k] for k in tokens) / 1_000_000


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
            "Set LLM_BACKEND=api (and ANTHROPIC_API_KEY or SUPPORT_PIPELINE_API_KEY)."
        )


def api_key() -> str | None:
    """The API key from the first of API_KEY_VARS that is set."""
    return next((os.environ[v] for v in API_KEY_VARS if os.getenv(v)), None)


def _get_client():
    global _client
    if _client is None:
        import anthropic

        key = api_key()
        if not key:
            raise BackendError(f"No API key: set one of {', '.join(API_KEY_VARS)} "
                               "(or copy .env.example to .env and add it).")
        # No SDK retries: call() retries a transient failure once, so one ticket makes at most two
        # requests per step instead of six, each bounded by timeout_s.
        _client = anthropic.Anthropic(api_key=key, max_retries=0,
                                      timeout=float(load_yaml("models.yaml").get("timeout_s", 60)))
    return _client


def _call_api(cfg: dict, system: str, user: str) -> str:
    # No temperature: Haiku 5.5 and Sonnet 5.5 reject a non-default value, and API version
    # 2026-10-21 rejects it on every model (models.yaml keeps it for the free-model profiles).
    # These models think by default; `effort` sets how much, and thinking counts toward max_tokens.
    extra = {"output_config": {"effort": cfg["effort"]}} if cfg.get("effort") else {}
    if cfg.get("timeout_s"):     # a long dev-only role (generator, evaluator) keeps its own limit
        extra["timeout"] = float(cfg["timeout_s"])
    cap = budget_usd()
    if cap and not _price(cfg["model"]):
        # Fail closed: an unpriced model's spend would not count toward the cap.
        raise BackendError(f"No price for {cfg['model']} in config/models.yaml while a budget is set; "
                           "add input, output, cache_write and cache_read under `prices` "
                           "(or set LLM_BUDGET_USD=0 to run without a cap).")
    if cap and spent_usd() >= cap:
        raise BudgetExceeded(f"API budget of ${cap:.4f} reached (spent ${spent_usd():.4f}). "
                             "Raise LLM_BUDGET_USD to continue.")
    resp = _get_client().messages.create(
        model=cfg["model"],
        max_tokens=cfg["max_tokens"],
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
        **extra,
    )
    u = resp.usage
    cache_read = getattr(u, "cache_read_input_tokens", 0) or 0
    cache_write = getattr(u, "cache_creation_input_tokens", 0) or 0
    # input_tokens counts every prompt token; the cache split shows whether prompt caching works.
    _usage.value = {"input_tokens": u.input_tokens + cache_read + cache_write, "output_tokens": u.output_tokens,
                    "cache_read_tokens": cache_read, "cache_write_tokens": cache_write}
    if hasattr(u, "inference_geo"):     # where the request was served, for the data-residency record
        _usage.value["inference_geo"] = u.inference_geo
    cost = price_usd(cfg["model"], u)
    if cost is not None:
        _usage.value["cost_usd"] = round(cost, 6)
        with _spend_lock:
            _spent["usd"] += cost
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
            backend_tag: str | None = None, attempt: int = 0) -> str:
    """Return the stored reply for this exact call, or make it once and store it.

    A lock directory per key stops two parallel runs paying for the same call twice.
    `backend_tag` is None for cli (keys unchanged from before it existed) and names any other
    backend, so the same model and prompts on the API never return a cli reply.
    """
    cache_dir = os.getenv("LLM_CACHE_DIR")
    if not cache_dir:
        if cache_only():
            raise BackendError("LLM_CACHE_ONLY=1 needs LLM_CACHE_DIR (the cache to replay).")
        return send(cfg, system, user)
    parts = ([cfg["model"], system, user] + ([_salt(role)] if _salt(role) else [])
             + ([f"attempt={attempt}"] if attempt else [])
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
        if cache_only():
            raise CacheMiss(f"No stored reply for this {cfg['model']} call (LLM_CACHE_ONLY=1); nothing was sent.")
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


@lru_cache(maxsize=1)
def _sdk_errors() -> tuple[tuple[type[Exception], ...], tuple[type[Exception], ...]]:
    """(transient, every) Anthropic SDK error classes; APITimeoutError is an APIConnectionError."""
    try:
        import anthropic
    except ImportError:      # cli-only install: no SDK errors to tell apart
        return (), ()
    names = ("APIConnectionError", "RateLimitError", "InternalServerError",
             "OverloadedError", "ServiceUnavailableError", "DeadlineExceededError")
    return tuple(getattr(anthropic, n) for n in names if hasattr(anthropic, n)), (anthropic.AnthropicError,)


_retry_check = threading.local()


@contextmanager
def before_retry(check):
    """Run `check` before any retry call() makes on this thread; it raises to stop. process() passes
    its should_stop check, so a page closed during a failed call is not sent a second, paid attempt."""
    prev = getattr(_retry_check, "fn", None)
    _retry_check.fn = check
    try:
        yield
    finally:
        _retry_check.fn = prev


def _pause(seconds: float) -> None:
    time.sleep(seconds)


def _backoff(e: Exception) -> float:
    """Seconds to wait before retrying `e`. The SDK's own retries are off, so a rate limit or an
    overloaded or failing server waits as the API asks (retry-after, at most 10 s), or 1-2 s; a timeout
    or a dropped connection, or a cli failure, is retried at once."""
    response = getattr(e, "response", None)
    status = getattr(response, "status_code", 0)
    if not (status == 429 or status >= 500):
        return 0.0
    try:
        return min(10.0, max(0.0, float(response.headers.get("retry-after"))))
    except (TypeError, ValueError):
        return 1.0 + random.random()


def _retryable(e: Exception) -> bool:
    """Worth one more try? Our own refusals never are (a retry would spend or fail the same way), nor
    an API error that says the request itself is wrong (bad request, key, permission, unknown model).
    A timeout, dropped connection, rate limit or server error is; so is a cli or free-model failure,
    which carries no type to tell."""
    if isinstance(e, (BudgetExceeded, CacheMiss, BackendError)):
        return False
    transient, sdk = _sdk_errors()
    return isinstance(e, transient) or not isinstance(e, sdk)


def call(role: str, system: str, user: str, *, retries: int = 1, attempt: int = 0) -> str:
    """Send one message for `role` and return the text reply.

    Retries once on a transient failure (see _retryable), after the wait _backoff asks for and the
    caller's before_retry check; the caller escalates the ticket if it still fails. A refusal (budget,
    cache-only miss, real-data guard, a rejected request) is raised as it is, so the caller can tell
    which. `attempt` > 0 asks for a fresh reply to the same prompt (its own cache slot), e.g. when the
    first reply could not be parsed.
    """
    assert_real_data_safe()
    if pipeline_mode() == "off":     # the kill switch holds even for a caller that forgot to check it
        raise BackendError("PIPELINE_MODE is off: model calls are switched off.")
    route = profile_route(role)
    cfg = route or models()[role]
    _usage.value = {}
    send = _call_openai if route else (_call_api if backend() == "api" else _call_cli)
    tag = f"openai:{route['provider']}" if route else (None if backend() == "cli" else backend())
    if tag == "api" and cfg.get("effort"):
        tag = f"api,effort={cfg['effort']}"      # a new effort level gets fresh replies
    last_error: Exception | None = None
    for n in range(retries + 1):
        if n:
            _pause(_backoff(last_error))
            check = getattr(_retry_check, "fn", None)
            if check is not None:
                check()
        try:
            return _cached(cfg, system, user, send, role, tag, attempt)
        except Exception as e:  # noqa: BLE001 - surfaced to caller after retry
            if not _retryable(e):
                raise
            last_error = e
    where = f"{route['provider']}/{route['model']}" if route else f"the {backend()} backend"
    raise RuntimeError(f"Model call failed for role '{role}' on {where}") from last_error
