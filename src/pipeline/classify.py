"""Stage 2: classify the ticket and extract its fields (classifier role, Haiku)."""

from __future__ import annotations

import json
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


# F14 (fraud_secondary_rule): "pick exactly one" read as "nothing else", and rule 1 (put the other
# issue in secondary) contradicted rule 5 (a consequence of the main problem is not a second issue),
# so "gave my code, now locked out" got login_otp as secondary on some runs and none on others.
_ONE_ORIG = "Pick exactly one `category` and one `subcategory` from this list. Use the keys, not the labels."
_ONE_NEW = ("Pick exactly one `category` and one `subcategory` for the main issue, using the keys from this "
            "list. `secondary_subcategory` is optional; use it only as rules 1 and 5 describe.")
_FRAUD_ORIG = "   Put the other issue in `secondary_subcategory`."
_FRAUD_NEW = ("   If the customer *also* raises a separate request that is not a result of the fraud (see rule 5), "
              "put it in `secondary_subcategory`. Being locked out, or losing money, because of the scam is part "
              "of the fraud, not a second issue.")


# F16 (warqa_usd), from the project author (a native speaker): "ورقة" is a 100 USD note, so
# "خمسين ورقة" is 5,000 USD, not 50,000 IQD as the amount_iqd example said (it also contradicted
# the amount_usd line). A classifier-prompt edit: test with replicates on the API before adopting.
_WARQA_ORIG = '"خمسين" or "خمسين ورقة" about money means 50,000;'
_WARQA_NEW = ('"خمسين" or "خمسين الف" about money means 50,000 IQD ("ورقة" is a 100 USD note, so '
              '"خمسين ورقة" = 5,000 USD and goes in amount_usd);')


# F20 (duplicate_payment_hint), from the author's label check (29 Oct): "paid the same amount twice by
# mistake" was read as a shop payment or a wrong recipient (dev-0109, 0138, 0190). A hint on
# reversal_request only; the rest of the prompt is unchanged.
_DUPLICATE_HINT = ("wants a payment or transfer undone although it reached the intended person or shop: "
                   "the same amount sent twice by mistake, or a cancelled deal; if the money went to the wrong "
                   "person, that is wrong_recipient")


def system_prompt() -> str:
    return _system_prompt(enabled("fee_amount"), enabled("runner_up"), enabled("lookalike_hints"),
                          enabled("fraud_secondary_rule"), enabled("warqa_usd"), enabled("duplicate_payment_hint"))


@lru_cache(maxsize=32)
def _system_prompt(fee_field: bool, runner_up: bool = False, lookalike: bool = False,
                   fraud_rule: bool = False, warqa: bool = False, duplicate: bool = False) -> str:
    """The classifier prompt, with the taxonomy filled in from config/taxonomy.yaml."""
    raw = load_yaml("taxonomy.yaml")
    # F13 (lookalike_hints): sharper one-line definitions for the look-alike subcategories.
    extra = load_yaml("experiments/lookalike_hints.yaml") if lookalike else {}
    if duplicate:
        extra = {**extra, "reversal_request": _DUPLICATE_HINT}
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
    if fraud_rule:
        prompt = prompt.replace(_ONE_ORIG, _ONE_NEW).replace(_FRAUD_ORIG, _FRAUD_NEW)
    if warqa:
        prompt = prompt.replace(_WARQA_ORIG, _WARQA_NEW)
    if runner_up:
        prompt = prompt.replace("\n## Output", _RUNNER_UP + "\n## Output").replace(
            '"confidence": 0.0', '"runner_up": null, "confidence": 0.0')
    return prompt


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
