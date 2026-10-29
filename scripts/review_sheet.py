"""Build a short sheet for the author to check gold labels by hand (CSV, opens in Google Sheets).

    python scripts/review_sheet.py --set data/dev/tickets.jsonl --runs rec,rec-r1,baseline,baseline-r1

Gold labels were written and reviewed by AI models, so a wrong label looks exactly like a model
error. The sheet takes the tickets where the runs disagree with gold (most consistent
disagreements first, type before outcome before priority), up to --disagree, and adds --agree
random tickets where everything matched, to check whether model and label are ever wrong together.
Never use it on heldout (it prints ticket text).
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from experiment import _ev, load_run, run_path, set_key  # noqa: E402
from pipeline.config import taxonomy  # noqa: E402


def label(key: str | None) -> str:
    sub = taxonomy().subcategories.get(key or "")
    return f"{key} ({sub.label_ar})" if sub else str(key)


def _gate_outcome(res: dict) -> str:
    if res["outcome"] != "flagged":
        return res["outcome"]
    return "flagged" if any(not f.startswith("draft:") for f in res.get("flags") or []) else "drafted"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True)
    ap.add_argument("--runs", required=True, help="comma-separated run labels")
    ap.add_argument("--disagree", type=int, default=14)
    ap.add_argument("--agree", type=int, default=4)
    ap.add_argument("--seed", type=int, default=1029)
    ap.add_argument("--out")
    args = ap.parse_args()

    set_name = set_key(args.set)
    if set_name == "heldout":
        raise SystemExit("Not for heldout: the sheet shows ticket text.")
    labels = args.runs.split(",")
    runs = [load_run(set_name, lb) for lb in labels]
    # The second model's answer on every ticket, if calibrate.py recheck-all was run on the first run.
    rc_file = run_path(set_name, labels[0]).with_suffix(".recheck_all.json")
    recheck_all = json.loads(rc_file.read_text(encoding="utf-8")) if rc_file.exists() else {}
    by_id: dict[str, list[dict]] = {}
    for run in runs:
        for row in run["tickets"]:
            by_id.setdefault(row["ticket"]["id"], []).append(row)

    picked, agreed = [], []
    for tid, rows in by_id.items():
        g = rows[0]["ticket"]
        subs = [(r["result"].get("extraction") or {}).get("subcategory") for r in rows]
        outs = [_gate_outcome(r["result"]) for r in rows]
        pris = [r["result"].get("priority") for r in rows]
        n_sub = sum(s != g["subcategory"] for s in subs)
        n_out = sum(o != g["outcome"] for o in outs)
        n_pri = sum(p != g["priority"] for p in pris)
        if not (n_sub or n_out or n_pri):
            agreed.append(tid)
            continue
        what = [f"type {n_sub}/{len(rows)} runs"] * bool(n_sub) + [f"outcome {n_out}/{len(rows)}"] * bool(n_out) \
            + [f"priority {n_pri}/{len(rows)}"] * bool(n_pri)
        picked.append(((n_sub, n_out, n_pri), tid, "; ".join(what)))
    picked.sort(key=lambda x: x[0], reverse=True)
    total_disagree = len(picked)
    picked = picked[:args.disagree]
    rng = random.Random(args.seed)
    spot = rng.sample(sorted(agreed), min(args.agree, len(agreed)))

    out = Path(args.out) if args.out else ROOT / "data/review" / f"{set_name}_label_check.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    head = ["id", "why on this sheet", "ticket",
            "gold type", "type used (most runs)", "first model's type", "second model's type",
            "gold outcome", "pipeline outcome", "gold priority", "pipeline priority",
            "gold amount", "pipeline amount",
            "WHICH TYPE IS RIGHT? (gold / pipeline / neither)", "correct type if neither", "note"]
    rows_out = []
    entries = [(tid, what) for _, tid, what in picked] + [(tid, "spot-check: pipeline agreed with gold") for tid in spot]
    rng.shuffle(entries)          # so the spot-checks don't stand out
    for tid, what in entries:
        rows = by_id[tid]
        g = rows[0]["ticket"]
        first = rows[0]

        def common(values):
            return Counter(values).most_common(1)[0][0]

        rc = _ev(first, "recheck")
        second = (recheck_all.get(tid, {}).get("extraction") or {}).get("subcategory") or \
            (rc["data"]["extraction"]["subcategory"] if rc and rc["status"] == "done" else "")
        cl = _ev(first, "classify")
        first_type = cl["data"]["extraction"]["subcategory"] if cl and cl["status"] == "done" else ""
        ex = first["result"].get("extraction") or {}
        amount = lambda d: (f"{d['amount_iqd']:,} IQD" if d.get("amount_iqd") is not None  # noqa: E731
                            else f"{d['amount_usd']} USD" if d.get("amount_usd") is not None else "")
        rows_out.append([
            tid, what, g["text"],
            label(g["subcategory"]), label(common([(r["result"].get("extraction") or {}).get("subcategory") for r in rows])),
            label(first_type), label(second) if second else "(not re-checked)",
            g["outcome"], common([_gate_outcome(r["result"]) for r in rows]),
            g["priority"], common([r["result"].get("priority") for r in rows]),
            amount(g), amount(ex), "", "", "",
        ])
    with open(out, "w", encoding="utf-8-sig", newline="") as f:   # BOM: Excel/Sheets read Arabic as UTF-8
        w = csv.writer(f)
        w.writerow(head)
        w.writerows(rows_out)
    print(f"{total_disagree} tickets disagree with gold in at least one run; sheet has {len(picked)} of them "
          f"+ {len(spot)} spot-checks = {len(rows_out)} rows. Saved {out}")


if __name__ == "__main__":
    main()
