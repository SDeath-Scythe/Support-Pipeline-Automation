"""Run a set of tickets through the full pipeline and record every stage event.

    LLM_BACKEND=cli python scripts/run_batch.py data/probes/mixed_30.jsonl
    LLM_BACKEND=api python scripts/run_batch.py data/probes/mixed_30.jsonl --workers 8

Saves runs/<timestamp>-<set>-<backend>.json. Open it in the viewer (python app/server.py)
to see the overview and replay any ticket stage by stage.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pipeline.config import models  # noqa: E402
from pipeline.config import thresholds as load_thresholds  # noqa: E402
from pipeline.fixes import active as active_fixes  # noqa: E402
from pipeline.llm import backend, budget_usd, model_for  # noqa: E402
from pipeline.run import process  # noqa: E402


def run_one(ticket: dict) -> dict:
    events: list[dict] = []
    t0 = time.time()
    try:
        result = process(ticket["text"], events.append)
    except Exception as e:  # noqa: BLE001 - recorded, never crashes the batch
        result = {"outcome": "escalated", "flags": ["model_error"], "error": f"{type(e).__name__}: {e}"}
    secs = round(time.time() - t0, 1)
    print(f"  {ticket.get('id', '?'):>4}  {result['outcome']:<9}  {secs:>5}s", flush=True)
    return {"ticket": ticket, "events": events, "result": result, "seconds": secs}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?", default=str(ROOT / "data/probes/mixed_30.jsonl"))
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--out", help="output file (default runs/<timestamp>-<set>-<backend>.json)")
    args = ap.parse_args()

    src = Path(args.file)
    tickets = [json.loads(line) for line in src.read_text(encoding="utf-8").splitlines() if line.strip()]
    fixes = sorted(active_fixes())
    print(f"Running {len(tickets)} tickets from {src.name} on the {backend()} backend, {args.workers} at a time"
          f"{', fixes: ' + ', '.join(fixes) if fixes else ''}")
    started = datetime.now()
    t0 = time.time()
    with ThreadPoolExecutor(args.workers) as pool:
        rows = list(pool.map(run_one, tickets))

    usage = [e["data"].get("usage") or {} for r in rows for e in r["events"] if e["status"] == "done"]
    usage = [u for u in usage if u]
    totals = {
        "model_calls": len(usage),
        "cached_calls": sum(bool(u.get("cached")) for u in usage),
        "input_tokens": sum(u.get("input_tokens", 0) for u in usage),
        "output_tokens": sum(u.get("output_tokens", 0) for u in usage),
        # cache hits replay a stored cost but spend nothing, so they are left out
        "cost_usd": round(sum(u.get("cost_usd") or 0 for u in usage if not u.get("cached")), 4),
    }
    if backend() == "api":
        totals["cost_per_ticket_usd"] = round(totals["cost_usd"] / max(1, len(rows)), 5)
        totals["budget_usd"] = budget_usd()
        totals["budget_hit"] = any("BudgetExceeded" in json.dumps(r["events"], ensure_ascii=False) for r in rows)
    print(f"Model calls {totals['model_calls']} ({totals['cached_calls']} from cache), "
          f"tokens in {totals['input_tokens']:,} / out {totals['output_tokens']:,}, reported cost ${totals['cost_usd']}")
    if totals.get("budget_hit"):
        print(f"WARNING: the ${totals['budget_usd']:.2f} budget was reached; tickets after it were not classified "
              "and this run's numbers are not valid. Raise LLM_BUDGET_USD and re-run (cached calls are free).")
    out = Path(args.out) if args.out else ROOT / "runs" / f"{started:%Y%m%d-%H%M%S}-{src.stem}-{backend()}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "meta": {
            "set": src.stem, "backend": backend(), "started": started.isoformat(timespec="seconds"),
            "wall_seconds": round(time.time() - t0, 1), "workers": args.workers,
            "models": {r: model_for(r) for r in models()},
            "profile": os.getenv("LLM_PROFILE") or None,
            "thresholds": load_thresholds()["confidence"],
            "fixes": fixes,
            "usage": totals,
        },
        "tickets": rows,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
