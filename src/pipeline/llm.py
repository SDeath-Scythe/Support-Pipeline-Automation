"""The single place the pipeline talks to a model.

Every call goes through `call(role, ...)`. The role decides the model, read from
config/models.yaml, so any model can be swapped by editing one line.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

from .config import models

load_dotenv()

_client = None


def _get_client():
    global _client
    if _client is None:
        import anthropic

        if not os.getenv("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key.")
        _client = anthropic.Anthropic()
    return _client


def call(role: str, system: str, user: str, *, retries: int = 1) -> str:
    """Send one message for `role` and return the text reply.

    Retries once on failure; the caller escalates the ticket if it still fails.
    """
    cfg = models()[role]
    last_error: Exception | None = None
    for _ in range(retries + 1):
        try:
            resp = _get_client().messages.create(
                model=cfg["model"],
                max_tokens=cfg["max_tokens"],
                temperature=cfg["temperature"],
                system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": user}],
            )
            return "".join(block.text for block in resp.content if block.type == "text")
        except Exception as e:  # noqa: BLE001 - surfaced to caller after retry
            last_error = e
    raise RuntimeError(f"Model call failed for role '{role}'") from last_error
