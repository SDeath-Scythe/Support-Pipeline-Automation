"""Run the pipeline on free-tier models and compare them with the Claude setup. A test, not calibration.

    python scripts/run_free_models.py                       # every profile whose keys are set
    python scripts/run_free_models.py --profiles google groq --set data/probes/holdout_30.jsonl

Each profile runs the same tickets with the recommended fixes on, the same draft judge (the
evaluator role, unchanged) and the same scoring as the Claude runs. Writes one page per profile
plus docs/experiments/free_models/<set>.md with a side-by-side table.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pipeline.config import load_yaml  # noqa: E402

REC = "F2+F3c+F6b+F7+F11+F12+F14b"   # the recommended set (docs/experiments/LOG.md)
E = [sys.executable, str(ROOT / "scripts/experiment.py")]


def keys_ok(profile: dict, providers: dict) -> bool:
    return all(os.getenv(providers[entry[0]]["key_env"]) for entry in profile.values())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiles", nargs="*")
    ap.add_argument("--set", default=str(ROOT / "data/probes/holdout_30.jsonl"))
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--table-only", action="store_true", help="rebuild the table from runs already made")
    args = ap.parse_args()
    raw = load_yaml("free_models.yaml")
    names = args.profiles or [n for n, p in raw["profiles"].items() if keys_ok(p, raw["providers"])]
    if not names:
        sys.exit("No profile has its API keys set. Run scripts/check_free_models.py to see what is missing.")
    set_name = Path(args.set).stem

    # The Claude reference: the recommended set on the same tickets (cached if it already ran).
    if not args.table_only:
        subprocess.run(E + ["run", REC, "--set", args.set, "--workers", "3"], check=True)
        subprocess.run(E + ["report", REC, "--set", args.set], check=True)
    for name in ([] if args.table_only else names):
        env = {**os.environ, "LLM_PROFILE": name}
        label = f"free-{name}"
        subprocess.run(E + ["run", REC, "--set", args.set, "--label", label, "--workers", str(args.workers)],
                       env=env, check=True)
        subprocess.run(E + ["report", REC, "--set", args.set, "--label", label, "--vs", REC], env=env, check=True)

    keys = [("final_subcategory", "Ticket type correct"), ("wrong_not_escalated", "Wrong type reaching a draft"),
            ("draft_available", "Draft given when it should be"), ("priority", "Priority correct"),
            ("fee", "Fee correct"), ("escalated", "Escalated"), ("bad_drafts", "Bad drafts (judge)"),
            ("mean_score", "Mean draft score (1-5)")]
    cols = [(REC, "Claude (Haiku + Sonnet)")] + [(f"free-{n}", n) for n in names]
    metrics, meta = {}, {}
    for label, _ in cols:
        metrics[label] = json.loads((ROOT / f"docs/experiments/{set_name}/metrics/{label}.json").read_text())["metrics"]
        run = json.loads((ROOT / f"runs/exp/{set_name}/{label}.json").read_text())
        rows = run["tickets"]
        meta[label] = {
            "models": run["meta"]["models"],
            "errors": sum("model_error" in r["result"].get("flags", []) for r in rows),
            "sec": sum(r["seconds"] for r in rows) / len(rows),
            "cached": (run["meta"].get("usage") or {}).get("cached_calls", 0) == (run["meta"].get("usage") or {}).get("model_calls", -1),
        }

    def fmt(v):
        return f"{v[0]}/{v[1]}" if isinstance(v, list) else ("—" if v is None else str(v))

    lines = [f"# Free models vs Claude on {set_name}", "",
             "A test on the free tiers, **not calibration**. Same tickets, same fixes on "
             f"(`{REC}`), same draft judge (Claude, unchanged) and same scoring for every column.", "",
             "| | " + " | ".join(t for _, t in cols) + " |", "|---" * (len(cols) + 1) + "|"]
    for k, title in keys:
        lines.append(f"| {title} | " + " | ".join(fmt(metrics[c].get(k)) for c, _ in cols) + " |")
    lines.append("| Model errors (call failed, escalated) | " + " | ".join(str(meta[c]["errors"]) for c, _ in cols) + " |")
    lines.append("| Seconds per ticket (incl. rate limits) | " + " | ".join("cached" if meta[c]["cached"] else f"{meta[c]['sec']:.1f}" for c, _ in cols) + " |")
    lines += ["", "Models per column:", ""]
    for c, t in cols:
        m = meta[c]["models"]
        lines.append(f"- **{t}**: classifier `{m['classifier']}`, re-check `{m['rechecker']}`, drafter `{m['drafter']}`")
    lines += ["", "Caveats: one run per column (classification moves about ±2 tickets on 95 between identical "
              "runs, draft scores about ±0.1); the judge is a Claude model and may prefer Claude-style drafts; "
              "free tiers rate-limit, so seconds per ticket are not production latency."]
    out = ROOT / "docs/experiments/free_models" / f"{set_name}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
