"""Run the edge-case probe tickets through clean -> classify -> gate -> route and score them.

    LLM_BACKEND=cli python scripts/run_probes.py            # free, on your Claude plan
    LLM_BACKEND=api python scripts/run_probes.py            # real numbers

Results are saved to runs/<timestamp>-probes-<backend>.jsonl.
Re-check and drafting are not built yet, so the outcome assumes the re-check agrees.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pipeline.classify import classify  # noqa: E402
from pipeline.clean import clean  # noqa: E402
from pipeline.gate import _key, check  # noqa: E402
from pipeline.llm import backend  # noqa: E402
from pipeline.route import route  # noqa: E402

FIELDS = ["category", "subcategory", "secondary_subcategory", "reference", "recipient_phone",
          "amount_iqd", "amount_usd", "priority", "outcome"]


def same(field: str, got, want) -> bool:
    if field in ("reference", "recipient_phone"):
        return (_key(got) if got else None) == (_key(want) if want else None)
    return got == want


def run_one(gold: dict) -> dict:
    text = clean(gold["text"])
    started = time.time()
    try:
        ex = classify(text)
    except Exception as e:  # noqa: BLE001
        return {"id": gold["id"], "error": f"{type(e).__name__}: {e}", "seconds": round(time.time() - started, 1)}
    gate = check(ex, text)
    team, priority = route(ex, text) if not gate.flags.count("invalid_category") else (None, None)
    outcome = "escalated" if gate.escalate else ("flagged" if gate.flags else "drafted")
    got = {**ex.model_dump(), "priority": priority, "outcome": outcome}
    return {
        "id": gold["id"],
        "got": got,
        "gate": gate.model_dump(),
        "team": team,
        "recheck": gate.needs_recheck,
        "seconds": round(time.time() - started, 1),
        "wrong": [f for f in FIELDS if not same(f, got.get(f), gold.get(f))],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(ROOT / "data/probes/edge_cases.jsonl"))
    ap.add_argument("--workers", type=int, default=5)
    args = ap.parse_args()

    golds = [json.loads(line) for line in open(args.file, encoding="utf-8") if line.strip()]
    with ThreadPoolExecutor(args.workers) as pool:
        results = list(pool.map(run_one, golds))

    out_dir = ROOT / "runs"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"{datetime.now():%Y%m%d-%H%M%S}-probes-{backend()}.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for gold, res in zip(golds, results):
            f.write(json.dumps({"gold": gold, **res}, ensure_ascii=False) + "\n")

    print(f"backend: {backend()}   tickets: {len(golds)}   saved: {out.relative_to(ROOT)}\n")
    for gold, res in zip(golds, results):
        if "error" in res:
            print(f"{gold['id']}  ERROR  {res['error']}")
            continue
        g = res["got"]
        mark = "PASS" if not res["wrong"] else "MISS"
        print(f"{gold['id']}  {mark}  {g['subcategory']:<22} conf {g['confidence']:.2f} -> {res['gate']['confidence']:.2f}"
              f"  {g['priority']}  {g['outcome']:<9}{' +recheck' if res['recheck'] else ''}")
        for f in res["wrong"]:
            print(f"        {f}: got {g.get(f)!r}, expected {gold.get(f)!r}")
    ok = [r for r in results if "error" not in r]
    n_pass = sum(not r["wrong"] for r in ok)
    sub_ok = sum("subcategory" not in r["wrong"] for r in ok)
    print(f"\nfully correct: {n_pass}/{len(golds)}   subcategory correct: {sub_ok}/{len(golds)}")


if __name__ == "__main__":
    main()
