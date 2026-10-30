"""Calibrate the confidence gate (pass_above, recheck_from) on a saved run, API backend only.

    python scripts/calibrate.py recheck-all --set data/dev/tickets.jsonl --label rec
    python scripts/calibrate.py table       --set data/dev/tickets.jsonl --label rec

recheck-all asks the re-check model about every ticket of the run, not only the ones the gate
sent it, so any threshold can be replayed. Calls the run already made come from the response
cache (runs/cache/), so only the other tickets cost anything. Answers go to
runs/exp/<set>/<label>.recheck_all.json.

table replays the gate (same rules as pipeline.run) for a grid of
thresholds and writes docs/experiments/<set>/calibration-<label>.md. No model calls.
Gold labels are model-written; check the disagreements by hand before trusting a choice.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from experiment import _ev, docs_dir, load_run, run_path, set_key  # noqa: E402

PASS_ABOVE = [0.70, 0.75, 0.80, 0.85, 0.90, 0.95]
RECHECK_FROM = [0.50, 0.55, 0.60, 0.65, 0.70]


def _use_run_settings(run: dict, salt: str | None = None) -> None:
    """Same cache as the run. The replay uses the current gate rules; flags named in runs made before
    30 Oct are the normal code now (or were deleted), so they are not set."""
    os.environ["LLM_CACHE_DIR"] = str(ROOT / "runs/cache")
    if salt is not None:
        os.environ["LLM_CACHE_SALT"] = salt


def recheck_path(set_name: str, label: str) -> Path:
    return run_path(set_name, label).with_suffix(".recheck_all.json")


def cmd_recheck_all(args) -> None:
    set_name, label = set_key(args.set), args.label
    run = load_run(set_name, label)
    if run["meta"]["backend"] != "api":
        raise SystemExit("Calibrate on an API run only (cli scores are not comparable).")
    _use_run_settings(run, args.salt)
    os.environ["LLM_BACKEND"] = "api"
    from pipeline import classify as cls
    from pipeline import llm
    from pipeline.clean import clean
    from pipeline.run import _model_step

    llm.require_api("Calibration")

    def one(row):
        tid = row["ticket"]["id"]
        try:
            ex2, info = _model_step("rechecker", cls.system_prompt(), cls.user_prompt(clean(row["ticket"]["text"])))
            return tid, {"extraction": ex2.model_dump(), "usage": info["usage"]}
        except Exception as e:  # noqa: BLE001 - recorded; the table counts it as a failed re-check
            return tid, {"error": f"{type(e).__name__}: {e}"}

    with ThreadPoolExecutor(args.workers) as pool:
        out = dict(pool.map(one, run["tickets"]))
    fresh = [v["usage"] for v in out.values() if "usage" in v and not v["usage"].get("cached")]
    cost = sum(u.get("cost_usd") or 0 for u in fresh)
    errors = sum("error" in v for v in out.values())
    recheck_path(set_name, label).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(out)} tickets re-checked ({len(fresh)} new calls, ${cost:.4f}; {errors} errors). "
          f"Saved {recheck_path(set_name, label)}")


# ---------------------------------------------------------------- replay the gate

def replay(run: dict, rechecks: dict, pass_above: float, recheck_from: float) -> list[dict]:
    """Each ticket's outcome under these thresholds, following pipeline.run.process (draft-check
    flags are left out: they depend on the draft, not the gate)."""
    from pipeline import gate
    from pipeline.clean import clean
    from pipeline.config import taxonomy, thresholds
    from pipeline.schemas import Extraction

    base = thresholds()
    # A missing required field caps the score so the ticket is re-checked and flagged, not escalated
    # (see gate.py); keep it at the bottom of the re-check band whatever recheck_from is.
    conf = {**base["confidence"], "pass_above": pass_above, "recheck_from": recheck_from,
            "missing_field_cap": max(base["confidence"]["missing_field_cap"], recheck_from)}
    gate.thresholds = lambda: {**base, "confidence": conf}
    tax = taxonomy()
    rows = []
    try:
        for row in run["tickets"]:
            g = row["ticket"]
            cl = _ev(row, "classify")
            if not cl or cl["status"] != "done":
                rows.append({"id": g["id"], "outcome": "escalated", "final": None, "rechecked": False, "gold": g})
                continue
            text = clean(g["text"])
            ex = Extraction.model_validate(cl["data"]["extraction"])
            gr = gate.check(ex, text)
            outcome, final, rechecked = None, ex, False
            if gr.escalate:
                outcome = "escalated"
            elif gr.needs_recheck:
                rechecked = True
                r2 = rechecks.get(g["id"], {})
                if "extraction" not in r2:
                    outcome = "escalated"                                  # model error
                else:
                    ex2 = Extraction.model_validate(r2["extraction"])
                    sub2 = tax.subcategories.get(ex2.subcategory)
                    if ex2.subcategory == ex.subcategory:
                        outcome = "flagged" if gr.flags else "drafted"
                    elif (sub2 is not None and not sub2.always_escalate
                          and not gate.check(ex2, text).escalate):
                        final, outcome = ex2, "flagged"                    # drafted from the re-check
                    else:
                        outcome = "escalated"
            else:
                outcome = "flagged" if gr.flags else "drafted"
            rows.append({"id": g["id"], "outcome": outcome, "final": final.subcategory, "rechecked": rechecked,
                         "confidence": ex.confidence, "gold": g})
    finally:
        gate.thresholds = thresholds
    return rows


def summarise(rows: list[dict]) -> dict:
    n = len(rows)
    sent = [r for r in rows if r["outcome"] != "escalated"]
    return {
        "drafted": sum(r["outcome"] == "drafted" for r in rows),
        "flagged": sum(r["outcome"] == "flagged" for r in rows),
        "escalated": sum(r["outcome"] == "escalated" for r in rows),
        "review_rate": sum(r["outcome"] != "drafted" for r in rows) / n,
        "wrong_drafted": sum(r["final"] != r["gold"]["subcategory"] for r in sent),
        "wrong_ready": sum(r["final"] != r["gold"]["subcategory"] for r in sent if r["outcome"] == "drafted"),
        "fraud_drafted": sum(r["gold"]["category"] == "fraud_security" for r in sent),
        "final_correct": sum(r["final"] == r["gold"]["subcategory"] for r in rows),
        "outcome_ok": sum(r["outcome"] == r["gold"]["outcome"] for r in rows),
        "rechecks": sum(r["rechecked"] for r in rows),
    }


def cmd_table(args) -> None:
    set_name, label = set_key(args.set), args.label
    run = load_run(set_name, label)
    rp = recheck_path(set_name, label)
    if not rp.exists():
        raise SystemExit(f"Run recheck-all first ({rp} is missing).")
    rechecks = json.loads(rp.read_text(encoding="utf-8"))
    _use_run_settings(run)
    n = len(run["tickets"])

    # Self-check: at the run's own thresholds the replay must give the run's own outcomes.
    actual = {r["ticket"]["id"]: _gate_outcome(r) for r in run["tickets"]}
    replayed = {r["id"]: r["outcome"] for r in replay(run, rechecks, 0.75, 0.60)}
    mismatch = sorted(i for i in actual if actual[i] != replayed[i])
    print(f"Replay at 0.75 / 0.60 matches the run on {n - len(mismatch)}/{n} tickets"
          + (f"; differs on {', '.join(mismatch)}" if mismatch else ""))

    # How well the classifier's own confidence is ordered.
    first = replay(run, rechecks, 0.75, 0.60)
    bins = [(0.95, 1.01), (0.90, 0.95), (0.85, 0.90), (0.80, 0.85), (0.75, 0.80), (0.60, 0.75), (0.0, 0.60)]
    lines = [f"# Gate calibration: {label} on {set_name}", "",
             f"{n} tickets, run on `{run['meta']['backend']}` with fixes: {', '.join(run['meta'].get('fixes') or []) or 'none'}. "
             "The re-check model's answer is known for every ticket (`calibrate.py recheck-all`), so each threshold "
             "pair below is a replay of the gate with no new model calls. Draft-check flags are left out.", "",
             "**Gold labels are model-written and not yet checked by a person**: a wrong label looks like a model error.", "",
             "## Classifier confidence vs correct (first model)", "",
             "| Confidence | Tickets | Correct | Re-check model correct |", "|---|---|---|---|"]
    for lo, hi in bins:
        sel = [r for r in first if r.get("confidence") is not None and lo <= r["confidence"] < hi]
        if not sel:
            continue
        ok = sum(_first_sub(run, r["id"]) == r["gold"]["subcategory"] for r in sel)
        rc = sum((rechecks.get(r["id"], {}).get("extraction") or {}).get("subcategory") == r["gold"]["subcategory"]
                 for r in sel)
        lines.append(f"| {lo:.2f}–{min(hi, 1):.2f} | {len(sel)} | {ok}/{len(sel)} | {rc}/{len(sel)} |")

    lines += ["", "## Threshold grid", "",
              "Review rate = flagged + escalated (anything that needs more than a quick approve). "
              "Wrong → draft = wrong type that still gets a draft (flagged or ready); wrong → ready = of those, "
              "marked ready with no flag. Fraud → draft must be 0.", "",
              "| pass_above | recheck_from | Ready | Flagged | Escalated | Review rate | Wrong → draft | Wrong → ready "
              "| Fraud → draft | Type used correct | Outcome = gold | Re-checks |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    current = (0.75, 0.60)
    for pa in PASS_ABOVE:
        for rf in RECHECK_FROM:
            if rf > pa:
                continue
            s = summarise(replay(run, rechecks, pa, rf))
            mark = " **(now)**" if (pa, rf) == current else ""
            lines.append(f"| {pa:.2f}{mark} | {rf:.2f} | {s['drafted']} | {s['flagged']} | {s['escalated']} | "
                         f"{100 * s['review_rate']:.0f}% | {s['wrong_drafted']} | {s['wrong_ready']} | {s['fraud_drafted']} | "
                         f"{s['final_correct']}/{n} | {s['outcome_ok']}/{n} | {s['rechecks']} |")
    errors = sum("error" in v for v in rechecks.values())
    if errors:
        lines += ["", f"{errors} re-check calls failed; those tickets count as escalated when re-checked."]
    lines += ["", f"Self-check: replaying 0.75 / 0.60 gives the run's own outcome on {n - len(mismatch)}/{n} tickets"
              + (f" (differs: {', '.join(mismatch)})." if mismatch else ".")]
    out = docs_dir(set_name) / f"calibration-{label}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nSaved {out}")


def _gate_outcome(row: dict) -> str:
    """The run's outcome without draft-check flags (those depend on the draft, not the gate)."""
    res = row["result"]
    if res["outcome"] != "flagged":
        return res["outcome"]
    return "flagged" if any(not f.startswith("draft:") for f in res.get("flags") or []) else "drafted"


def _first_sub(run: dict, tid: str) -> str | None:
    row = next(r for r in run["tickets"] if r["ticket"]["id"] == tid)
    cl = _ev(row, "classify")
    return cl["data"]["extraction"]["subcategory"] if cl and cl["status"] == "done" else None


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("recheck-all", "table"):
        p = sub.add_parser(name)
        p.add_argument("--set", required=True)
        p.add_argument("--label", required=True, help="the saved run to calibrate on")
        p.add_argument("--workers", type=int, default=5)
        p.add_argument("--salt", help="the run's LLM_CACHE_SALT, so its re-check calls are reused")
    args = ap.parse_args()
    {"recheck-all": cmd_recheck_all, "table": cmd_table}[args.cmd](args)


if __name__ == "__main__":
    main()
