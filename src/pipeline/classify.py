"""Stage 2: classify the ticket and extract its fields (classifier role, Haiku)."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from .config import load_yaml
from .llm import call
from .schemas import Extraction

_PROMPT = Path(__file__).parent / "prompts" / "classify_system.md"


@lru_cache(maxsize=1)
def system_prompt() -> str:
    """The classifier prompt, with the taxonomy filled in from config/taxonomy.yaml."""
    raw = load_yaml("taxonomy.yaml")
    lines = []
    for cat_key, cat in raw["categories"].items():
        lines.append(f"- `{cat_key}` ({cat['label']})")
        for sub_key, sub in cat["subcategories"].items():
            hint = f" ({sub['hint']})" if sub.get("hint") else ""
            lines.append(f"  - `{sub_key}`: {sub['label']}{hint}")
    return _PROMPT.read_text(encoding="utf-8").replace("{taxonomy}", "\n".join(lines))


_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


def parse(reply: str) -> Extraction:
    """Parse the model reply into an Extraction. Tolerates code fences or stray text."""
    match = _JSON_OBJECT.search(reply)
    if not match:
        raise ValueError(f"No JSON object in reply: {reply[:200]!r}")
    return Extraction.model_validate(json.loads(match.group()))


def user_prompt(cleaned_text: str) -> str:
    return f"<ticket>\n{cleaned_text}\n</ticket>"


def classify(cleaned_text: str, role: str = "classifier") -> Extraction:
    """Classify with the given role. The re-check calls this with role="rechecker":
    the second model classifies blind, without seeing the first answer, so it can't be anchored by it."""
    return parse(call(role, system_prompt(), user_prompt(cleaned_text)))
