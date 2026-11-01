"""Load the YAML config files. Everything tunable lives in config/, not in code."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


def load_yaml(name: str) -> dict[str, Any]:
    with open(CONFIG_DIR / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


@dataclass(frozen=True)
class Subcategory:
    key: str
    label: str
    label_ar: str
    category: str
    team: str
    default_priority: str
    required_fields: tuple[str, ...]
    high_risk: bool
    always_escalate: bool


@dataclass(frozen=True)
class Taxonomy:
    teams: dict[str, dict[str, str]]
    categories: dict[str, str]          # category key -> label
    categories_ar: dict[str, str]       # category key -> Arabic label (shown in the UI)
    subcategories: dict[str, Subcategory]

    def get(self, subcategory: str) -> Subcategory:
        return self.subcategories[subcategory]


@lru_cache(maxsize=1)
def taxonomy() -> Taxonomy:
    raw = load_yaml("taxonomy.yaml")
    subs: dict[str, Subcategory] = {}
    cats: dict[str, str] = {}
    cats_ar: dict[str, str] = {}
    for cat_key, cat in raw["categories"].items():
        cats[cat_key] = cat["label"]
        cats_ar[cat_key] = cat.get("label_ar", cat["label"])
        for sub_key, sub in cat["subcategories"].items():
            if sub_key in subs:
                raise ValueError(f"Duplicate subcategory key: {sub_key}")
            subs[sub_key] = Subcategory(
                key=sub_key,
                label=sub["label"],
                label_ar=sub.get("label_ar", sub["label"]),
                category=cat_key,
                team=sub.get("team", cat["team"]),   # a subcategory may name its own team (app_bug -> tech)
                default_priority=sub["default_priority"],
                required_fields=tuple(sub.get("required_fields", [])),
                high_risk=bool(sub.get("high_risk", False)),
                always_escalate=bool(cat.get("always_escalate", False)),
            )
    return Taxonomy(teams=raw["teams"], categories=cats, categories_ar=cats_ar, subcategories=subs)


@lru_cache(maxsize=1)
def models() -> dict[str, dict[str, Any]]:
    return load_yaml("models.yaml")["roles"]


@lru_cache(maxsize=1)
def llm_backend() -> str:
    """Default backend from models.yaml; the LLM_BACKEND env var overrides it."""
    return str(load_yaml("models.yaml").get("backend", "api"))


@lru_cache(maxsize=1)
def thresholds() -> dict[str, Any]:
    return load_yaml("thresholds.yaml")


# Hard limits that keep one bad input from costing money or time (config/thresholds.yaml `limits`).
_LIMIT_DEFAULTS = {"max_ticket_chars": 4000, "max_batch_tickets": 1000, "max_request_bytes": 65536}


def limits() -> dict[str, int]:
    """The `limits` block of thresholds.yaml, with the defaults filled in for a missing block or key."""
    raw = thresholds().get("limits") or {}
    out = {**_LIMIT_DEFAULTS, **{k: int(v) for k, v in raw.items()}}
    bad = [k for k, v in out.items() if v <= 0]
    if bad:
        raise ValueError(f"limits in thresholds.yaml must be positive: {', '.join(bad)}")
    return out


# Kill switch. off: no model is called and every ticket goes to a person. classify_only: tickets are
# still sorted and routed, but no reply is drafted. full: the normal pipeline.
PIPELINE_MODES = ("off", "classify_only", "full")


def _default_mode() -> str:
    """`mode:` in models.yaml, read on every call so an edit stops a running viewer or batch at its next
    model call. YAML reads a bare `off` (or no, false) as False: that means off, never full."""
    raw = load_yaml("models.yaml").get("mode")
    if raw is None:
        return "full"
    if raw is False:
        return "off"
    if not isinstance(raw, str):
        raise ValueError(f"Unknown mode in models.yaml: {raw!r}. Use one of: {', '.join(PIPELINE_MODES)}.")
    return raw


def pipeline_mode() -> str:
    """The run mode: PIPELINE_MODE env var first, then `mode:` in models.yaml, else full.
    An unknown value raises rather than silently running the full pipeline."""
    name = (os.getenv("PIPELINE_MODE") or _default_mode()).strip().lower()
    if name not in PIPELINE_MODES:
        raise ValueError(f"Unknown PIPELINE_MODE '{name}'. Use one of: {', '.join(PIPELINE_MODES)}.")
    return name
