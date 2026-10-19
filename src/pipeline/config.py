"""Load the YAML config files. Everything tunable lives in config/, not in code."""

from __future__ import annotations

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
                team=cat["team"],
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
