"""Stage 2: classify the ticket and extract its fields (classifier role, Haiku)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from .config import load_yaml
from .llm import call
from .schemas import Extraction

_PROMPT = Path(__file__).parent / "prompts" / "classify_system.md"


@lru_cache(maxsize=1)
def system_prompt() -> str:
    """The classifier prompt, with the taxonomy (and each subcategory's hint) from config/taxonomy.yaml."""
    raw = load_yaml("taxonomy.yaml")
    lines = []
    for cat_key, cat in raw["categories"].items():
        lines.append(f"- `{cat_key}` ({cat['label']})")
        for sub_key, sub in cat["subcategories"].items():
            hint = f" ({sub['hint']})" if sub.get("hint") else ""
            lines.append(f"  - `{sub_key}`: {sub['label']}{hint}")
    return _PROMPT.read_text(encoding="utf-8").replace("{taxonomy}", "\n".join(lines))


def _first_object(reply: str) -> dict:
    """The first complete JSON object in the reply. Tolerates code fences, stray text and text
    after the object (some models add a second object or a note, which a greedy {.*} would join)."""
    start = reply.find("{")
    if start < 0:
        raise ValueError(f"No JSON object in reply: {reply[:200]!r}")
    obj, _ = json.JSONDecoder().raw_decode(reply[start:])
    return obj


def parse(reply: str) -> Extraction:
    """Parse the model reply into an Extraction. Tolerates code fences or stray text."""
    return Extraction.model_validate(_first_object(reply))


_FEE_PROMPT = Path(__file__).parent / "prompts" / "fee_system.md"


def fee_prompt() -> str:
    """A small separate call for the disputed fee, only on fee tickets. Adding a fee field to the
    classifier prompt shifted other classifications (round 3), so the classifier prompt stays as it is."""
    return _FEE_PROMPT.read_text(encoding="utf-8")


def parse_fee(reply: str) -> int | None:
    try:
        value = _first_object(reply).get("fee_iqd")
    except ValueError:
        value = None
    return int(value) if isinstance(value, (int, float)) and value > 0 else None


def user_prompt(cleaned_text: str) -> str:
    return f"<ticket>\n{cleaned_text}\n</ticket>"


def classify(cleaned_text: str, role: str = "classifier") -> Extraction:
    """Classify with the given role. The re-check calls this with role="rechecker":
    the second model classifies blind, without seeing the first answer, so it can't be anchored by it."""
    return parse(call(role, system_prompt(), user_prompt(cleaned_text)))
