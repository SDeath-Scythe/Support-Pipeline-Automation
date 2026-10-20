"""Stage 2: classify the ticket and extract its fields (classifier role, Haiku)."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from .config import load_yaml
from .fixes import enabled
from .llm import call
from .schemas import Extraction

_PROMPT = Path(__file__).parent / "prompts" / "classify_system.md"


# F6 (fee_amount): when a customer disputes a fee, keep the fee apart from the transaction
# amount, so the agent and the draft talk about the right number.
_FEE_FIELD = (
    "- `fee_iqd`: only when the customer disputes or asks about a fee, commission or deduction "
    "(عمولة، رسوم، استقطاع): the fee amount in IQD as an integer. "
    "`amount_iqd` stays the amount of the transaction itself. If the fee is not stated but the "
    "customer gives what they sent and what arrived, the fee is the difference. Otherwise null.\n"
)


# F10 (runner_up): the model names its second choice in the same call, so a close call can be
# re-checked without asking a second model on every ticket.
_RUNNER_UP = (
    "\n## Runner-up\n"
    "`runner_up`: if another subcategory is also plausible for this ticket, its key; otherwise null. "
    "Name one whenever you hesitated between two.\n"
)


def system_prompt() -> str:
    return _system_prompt(enabled("fee_amount"), enabled("runner_up"), enabled("lookalike_hints"))


@lru_cache(maxsize=8)
def _system_prompt(fee_field: bool, runner_up: bool = False, lookalike: bool = False) -> str:
    """The classifier prompt, with the taxonomy filled in from config/taxonomy.yaml."""
    raw = load_yaml("taxonomy.yaml")
    # F13 (lookalike_hints): sharper one-line definitions for the look-alike subcategories.
    extra = load_yaml("experiments/lookalike_hints.yaml") if lookalike else {}
    lines = []
    for cat_key, cat in raw["categories"].items():
        lines.append(f"- `{cat_key}` ({cat['label']})")
        for sub_key, sub in cat["subcategories"].items():
            text = extra.get(sub_key) or sub.get("hint")
            hint = f" ({text})" if text else ""
            lines.append(f"  - `{sub_key}`: {sub['label']}{hint}")
    prompt = _PROMPT.read_text(encoding="utf-8").replace("{taxonomy}", "\n".join(lines))
    if fee_field:
        usd = next(line for line in prompt.splitlines(keepends=True) if line.startswith("- `amount_usd`"))
        prompt = prompt.replace(usd, usd + _FEE_FIELD).replace('"amount_usd": null, ', '"amount_usd": null, "fee_iqd": null, ')
    if runner_up:
        prompt = prompt.replace("\n## Output", _RUNNER_UP + "\n## Output").replace(
            '"confidence": 0.0', '"runner_up": null, "confidence": 0.0')
    return prompt


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
