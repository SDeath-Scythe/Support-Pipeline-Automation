"""Run a set of tickets through the full pipeline and record every stage event.

    LLM_BACKEND=cli python scripts/run_batch.py data/probes/mixed_30.jsonl
    LLM_BACKEND=api python scripts/run_batch.py data/probes/mixed_30.jsonl --workers 8

Saves runs/<timestamp>-<set>-<backend>.json. Open it in the viewer (python app/server.py)
to see the overview and replay any ticket stage by stage.
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

from pipeline.config import models  # noqa: E402
from pipeline.config import thresholds as load_thresholds  # noqa: E402
from pipeline.llm import backend  # noqa: E402
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
    args = ap.parse_args()

    src = Path(args.file)
    tickets = [json.loads(line) for line in src.read_text(encoding="utf-8").splitlines() if line.strip()]
    print(f"Running {len(tickets)} tickets from {src.name} on the {backend()} backend, {args.workers} at a time")
    started = datetime.now()
    t0 = time.time()
    with ThreadPoolExecutor(args.workers) as pool:
        rows = list(pool.map(run_one, tickets))

    out_dir = ROOT / "runs"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"{started:%Y%m%d-%H%M%S}-{src.stem}-{backend()}.json"
    out.write_text(json.dumps({
        "meta": {
            "set": src.stem, "backend": backend(), "started": started.isoformat(timespec="seconds"),
            "wall_seconds": round(time.time() - t0, 1), "workers": args.workers,
            "models": {r: c["model"] for r, c in models().items()},
            "thresholds": load_thresholds()["confidence"],
        },
        "tickets": rows,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Saved {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
