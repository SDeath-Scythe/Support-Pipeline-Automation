"""Check which free-model profiles can run: keys present, model ids valid, one Iraqi ticket each.

    python scripts/check_free_models.py

For every provider in config/free_models.yaml: is its key set, which models does the key list,
and does each configured model classify one Iraqi-dialect ticket into valid JSON? Prints a table;
calls nothing for providers without a key. Use it before scripts/run_free_models.py, and to fix
model ids when a provider renames them.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pipeline import classify as cls  # noqa: E402
from pipeline.clean import clean  # noqa: E402
from pipeline.config import load_yaml  # noqa: E402
from pipeline.llm import _call_openai  # noqa: E402

TICKET = clean("دزيت ٧٥ الف لاختي من الصبح وما وصلتها، رقم العملية 5520193. شنو السالفة؟")


def listed_models(p: dict) -> set[str] | None:
    req = urllib.request.Request(p["base_url"].rstrip("/") + "/models",
                                 headers={"Authorization": f"Bearer {os.environ[p['key_env']]}",
                                          "User-Agent": "support-pipeline-test/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
    except Exception as e:  # noqa: BLE001
        print(f"   could not list models: {e}")
        return None
    return {m["id"].removeprefix("models/") for m in data.get("data", [])}


def main() -> None:
    raw = load_yaml("free_models.yaml")
    used: dict[str, set[tuple[str, bool]]] = {}
    for prof in raw["profiles"].values():
        for provider, model, *opts in prof.values():
            used.setdefault(provider, set()).add((model, "merge_system" in opts))

    ready = set()
    for provider, p in raw["providers"].items():
        if provider not in used:
            continue
        if not os.getenv(p["key_env"]):
            print(f"{provider:10} {p['key_env']} not set: skipped")
            continue
        print(f"{provider:10} key found")
        listed = listed_models(p)
        ok_all = True
        for model, merge in sorted(used[provider]):
            if listed is not None and model not in listed:
                print(f"   {model:50} NOT in the provider's model list")
                ok_all = False
                continue
            cfg = {**p, "provider": provider, "model": model, "merge_system": merge,
                   "max_tokens": 4096, "temperature": 0.0}
            t0 = time.time()
            try:
                ex = cls.parse(_call_openai(cfg, cls.system_prompt(), cls.user_prompt(TICKET)))
                print(f"   {model:50} ok  {time.time() - t0:5.1f}s  -> {ex.subcategory}, "
                      f"{ex.amount_iqd}, ref {ex.reference}, conf {ex.confidence}")
            except Exception as e:  # noqa: BLE001
                print(f"   {model:50} FAILED: {str(e)[:160]}")
                ok_all = False
        if ok_all:
            ready.add(provider)

    print("\nProfiles ready to run:")
    for name, prof in raw["profiles"].items():
        need = {entry[0] for entry in prof.values()}
        print(f"   {name:10} {'yes' if need <= ready else 'no (needs ' + ', '.join(sorted(need - ready)) + ')'}")


if __name__ == "__main__":
    main()
