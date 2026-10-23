"""Test candidate fixes with and without them on the same tickets, and write up the results.

    python scripts/experiment.py run baseline              # all fixes off
    python scripts/experiment.py run F2+F3                 # fixes F2 and F3 on
    python scripts/experiment.py run baseline --nocache --label baseline-rep1   # noise check
    python scripts/experiment.py report F2+F3              # judge drafts, score, compare with baseline
    python scripts/experiment.py judge-noise baseline      # grade the same drafts twice
    python scripts/experiment.py summary                   # one table for every config run so far

Runs go to runs/exp/<set>/<label>.json (not committed). Reports go to
docs/experiments/<set>/. Model replies are cached in runs/cache/ so two configs only
differ where a fix changes what a model is sent. See docs/experiments/README.md.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pipeline.config import load_yaml, taxonomy  # noqa: E402
from pipeline.draft import FIELD_AR  # noqa: E402
from pipeline.gate import _key  # noqa: E402

CODES = {
    "F2": "draft_check",
    "F3": "recheck_same_team",
    "F5": "policy_facts",
    "F6": "fee_amount",
    "F7": "no_now_urgency",
    "F8": "unclear_template",
    "F3b": "recheck_use_second",
    "F3c": "recheck_cross_team",
    "F9": "confusable_recheck",
    "F10": "runner_up",
    "F11": "ask_if_missing",
    "F12": "no_specific_followup",
    "F13": "lookalike_hints",
    "F6b": "fee_followup",
    "F14": "fraud_secondary_rule",
    "F14b": "fraud_secondary_cleanup",
    "F15": "no_urgency_words",
    "F16": "warqa_usd",
    "F17": "handoff_note",
}
DEFAULT_SET = ROOT / "data/probes/fixes_30.jsonl"
CACHE = ROOT / "runs/cache"
JUDGE_PROMPT = (ROOT / "scripts/prompts/judge_draft.md").read_text(encoding="utf-8")
JUDGE_CHECKS = ["understood", "grounded", "no_promise", "asks_right", "safe", "tone", "clean"]


def flags_for(config: str) -> list[str]:
    if config.startswith("baseline"):
        return []
    return [CODES[c] for c in config.split("+")]


def run_path(set_name: str, label: str) -> Path:
    return ROOT / "runs/exp" / set_name / f"{label}.json"


def docs_dir(set_name: str) -> Path:
    return ROOT / "docs/experiments" / set_name


def load_run(set_name: str, label: str) -> dict:
    """A saved run, with gold labels taken from the current set file (so a corrected label
    applies to runs made before the correction; the model outputs are untouched)."""
    run = json.loads(run_path(set_name, label).read_text(encoding="utf-8"))
    src = ROOT / "data/probes" / f"{set_name}.jsonl"
    if src.exists():
        gold = {d["id"]: d for d in map(json.loads, src.read_text(encoding="utf-8").splitlines()) if d}
        for row in run["tickets"]:
            row["ticket"] = gold.get(row["ticket"].get("id"), row["ticket"])
    return run


# ---------------------------------------------------------------- run

def cmd_run(args) -> None:
    src = Path(args.set)
    label = args.label or args.config
    env = {**os.environ, "PIPELINE_FIXES": ",".join(flags_for(args.config)), "LLM_BACKEND": args.backend}
    if args.salt:
        env["LLM_CACHE_SALT"] = args.salt
    if args.nocache:
        env.pop("LLM_CACHE_DIR", None)
    else:
        env["LLM_CACHE_DIR"] = str(CACHE)
    subprocess.run([sys.executable, str(ROOT / "scripts/run_batch.py"), str(src), "--workers", str(args.workers),
                    "--out", str(run_path(src.stem, label))], env=env, check=True)


# ---------------------------------------------------------------- judge

def _ev(row: dict, stage: str) -> dict | None:
    return next((e for e in row["events"] if e["stage"] == stage and e["status"] != "running"), None)


def needed_info(sub: str) -> list[str]:
    tax = taxonomy()
    fields = list(tax.get(sub).required_fields) if sub in tax.subcategories else []
    policy = (load_yaml("policy.yaml")["subcategories"].get(sub) or {}).get("customer_should_send", [])
    return [FIELD_AR.get(f, f) for f in dict.fromkeys(fields + policy)]


def judge_prompt(row: dict, salt: str = "") -> str | None:
    draft = row["result"].get("draft_ar")
    if not draft:
        return None
    gold = row["ticket"]
    tax = taxonomy()
    sub = tax.subcategories.get(gold["subcategory"])
    issue = f"{tax.categories[sub.category]} / {sub.label}" if sub else gold["subcategory"]
    if gold.get("secondary_subcategory") in tax.subcategories:
        issue += f" (second question: {tax.get(gold['secondary_subcategory']).label})"
    dr = _ev(row, "draft")
    facts, team = "none", None
    for line in (dr or {}).get("data", {}).get("user_prompt", "").splitlines():
        if line.startswith("Known facts:"):
            facts = line.removeprefix("Known facts:").strip()
        elif line.startswith("Handled by:"):
            team = line.removeprefix("Handled by:").strip()
    if team:   # the drafter is told the team, so naming it is grounded
        facts += f"; the issue is handled by {team}"
    needed = needed_info(gold["subcategory"])
    return "\n".join([
        f"<ticket>\n{gold['text']}\n</ticket>",
        f"Correct issue: {issue}",
        "Information the company needs for this issue: " + (", ".join(needed) if needed else "nothing specific"),
        f"Known facts: {facts}",
        f"<draft>\n{draft}\n</draft>",
    ]) + salt


def judge_all(run: dict, salt: str = "") -> dict[str, dict]:
    from pipeline.llm import call

    os.environ["LLM_CACHE_DIR"] = str(CACHE)

    def one(row):
        user = judge_prompt(row, salt)
        if user is None:
            return row["ticket"]["id"], None
        reply = call("evaluator", JUDGE_PROMPT, user)
        m = re.search(r"\{.*\}", reply, re.DOTALL)
        try:
            return row["ticket"]["id"], json.loads(m.group())
        except (AttributeError, ValueError):
            return row["ticket"]["id"], {"error": reply[:200]}

    with ThreadPoolExecutor(5) as pool:
        return dict(pool.map(one, run["tickets"]))


def bad(j: dict | None) -> bool:
    if not j or "error" in j:
        return False
    return not all(j.get(k) for k in ("understood", "grounded", "no_promise", "safe", "clean")) or j.get("score", 5) <= 2


# ---------------------------------------------------------------- score

def score(run: dict, judged: dict[str, dict]) -> tuple[dict, list[dict]]:
    rows = []
    for row in run["tickets"]:
        g, r = row["ticket"], row["result"]
        cl, rc, dr = _ev(row, "classify"), _ev(row, "recheck"), _ev(row, "draft")
        ex = cl["data"].get("extraction", {}) if cl and cl["status"] == "done" else {}
        j = judged.get(g["id"])
        has_draft = bool(r.get("draft_ar"))
        final = (r.get("extraction") or {}).get("subcategory", ex.get("subcategory"))   # the answer used
        rows.append({
            "id": g["id"], "targets": g.get("targets", ""),
            "gold_sub": g["subcategory"], "sub": ex.get("subcategory"),
            "sub_ok": ex.get("subcategory") == g["subcategory"],
            "final_sub": final, "final_ok": final == g["subcategory"],
            "secondary": (r.get("extraction") or ex).get("secondary_subcategory"),
            "secondary_ok": None if "secondary_subcategory" not in g else
                            (r.get("extraction") or ex).get("secondary_subcategory") == g["secondary_subcategory"],
            "gold_fraud": g.get("category") == "fraud_security",
            "wrong_not_escalated": r["outcome"] != "escalated" and final != g["subcategory"],
            "gold_outcome": g["outcome"], "outcome": r["outcome"], "outcome_ok": r["outcome"] == g["outcome"],
            "draft_avail_ok": has_draft == (g["outcome"] != "escalated"),
            "gold_priority": g["priority"], "priority": r.get("priority"), "priority_ok": r.get("priority") == g["priority"],
            "amount_ok": None if "amount_iqd" not in g else ex.get("amount_iqd") == g["amount_iqd"],
            "fee_ok": None if g.get("fee_iqd") is None else
                      (r.get("extraction") or ex).get("fee_iqd") == g["fee_iqd"],   # the fee used (F6b adds it late)
            "ref_ok": None if "reference" not in g else
                      (_key(ex["reference"]) if ex.get("reference") else None) == (_key(g["reference"]) if g["reference"] else None),
            "flags": r.get("flags", []),
            "calls": (cl is not None and cl["status"] == "done") + (rc is not None and rc["status"] == "done")
                     + (dr is not None and dr["status"] == "done" and not dr["data"].get("template"))
                     + bool(r.get("fee_followup")),
            "draft": r.get("draft_ar"), "judge": j, "bad": bad(j),
            "bad_ready": r["outcome"] == "drafted" and bad(j),
        })
    n = len(rows)
    drafts = [x for x in rows if x["judge"] and "error" not in x["judge"]]

    def rate(key, pool=rows):
        pool = [x for x in pool if x[key] is not None]
        return (sum(bool(x[key]) for x in pool), len(pool))

    m = {
        "tickets": n,
        "subcategory": rate("sub_ok"), "final_subcategory": rate("final_ok"),
        "secondary": rate("secondary_ok"),
        "secondary_fraud": rate("secondary_ok", [x for x in rows if x["gold_fraud"]]),
        "wrong_not_escalated": sum(x["wrong_not_escalated"] for x in rows), "outcome": rate("outcome_ok"), "draft_available": rate("draft_avail_ok"),
        "priority": rate("priority_ok"), "amount": rate("amount_ok"), "fee": rate("fee_ok"), "reference": rate("ref_ok"),
        "escalated": sum(x["outcome"] == "escalated" for x in rows),
        "flagged": sum(x["outcome"] == "flagged" for x in rows),
        "drafted": sum(x["outcome"] == "drafted" for x in rows),
        "drafts": len(drafts),
        "bad_drafts": sum(x["bad"] for x in drafts),
        "bad_ready": sum(x["bad_ready"] for x in rows),
        "mean_score": round(sum(x["judge"]["score"] for x in drafts) / len(drafts), 2) if drafts else None,
        "model_calls": sum(x["calls"] for x in rows),
        **{f"judge_{k}": (sum(bool(x["judge"].get(k)) for x in drafts), len(drafts)) for k in JUDGE_CHECKS},
    }
    return m, rows


# ---------------------------------------------------------------- report

LABELS = [
    ("subcategory", "Subcategory correct (first model)", +1),
    ("final_subcategory", "Subcategory used correct", +1),
    ("secondary", "Secondary subcategory correct", +1),
    ("secondary_fraud", "Secondary correct (fraud tickets)", +1),
    ("wrong_not_escalated", "Wrong type, not escalated", -1), ("outcome", "Outcome matches gold", +1),
    ("draft_available", "Draft given iff it should be", +1), ("priority", "Priority correct", +1),
    ("amount", "Amount correct", +1), ("fee", "Fee correct (fee tickets)", +1),
    ("escalated", "Escalated", 0), ("flagged", "Flagged", 0), ("drafted", "Drafted (ready)", 0),
    ("drafts", "Drafts judged", 0), ("bad_drafts", "Bad drafts (judge)", -1),
    ("bad_ready", "Bad drafts marked ready", -1), ("mean_score", "Mean draft score (1-5)", +1),
    ("model_calls", "Model calls (pipeline)", -1),
] + [(f"judge_{k}", f"Judge: {k}", +1) for k in JUDGE_CHECKS]


def fmt(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, (tuple, list)):
        return f"{v[0]}/{v[1]}" if v[1] else "—"
    return str(v)


def num(v) -> float | None:
    if v is None:
        return None
    if isinstance(v, (tuple, list)):
        return v[0] if v[1] else None
    return float(v)


def verdict(delta: float | None, direction: int) -> str:
    if delta is None or direction == 0 or abs(delta) < 1e-9:
        return ""
    return "better" if delta * direction > 0 else "worse"


def scored(set_name: str, label: str) -> tuple[dict, list[dict], dict]:
    run = load_run(set_name, label)
    judged = judge_all(run)
    m, rows = score(run, judged)
    return m, rows, run["meta"]


def cmd_report(args) -> None:
    set_name = Path(args.set).stem
    label = args.label or args.config
    m, rows, meta = scored(set_name, label)
    out_dir = docs_dir(set_name)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "metrics").mkdir(exist_ok=True)
    (out_dir / "metrics" / f"{label}.json").write_text(json.dumps({"meta": meta, "metrics": m, "rows": rows},
                                                                   ensure_ascii=False, indent=1), encoding="utf-8")
    base = None
    if label != args.vs and run_path(set_name, args.vs).exists():
        bm, brows, _ = scored(set_name, args.vs)
        base = (bm, {r["id"]: r for r in brows})

    lines = [f"# {label} on {set_name}", "",
             f"Fixes on: {', '.join(meta.get('fixes') or []) or 'none'} · backend `{meta['backend']}` · "
             f"{meta['started']} · compared with `{args.vs}`", ""]
    head = "| Metric | " + (f"{args.vs} | " if base else "") + f"{label} |" + (" Change |" if base else "")
    lines += [head, "|" + "---|" * (head.count("|") - 1)]
    for key, name, d in LABELS:
        if base:
            a, b = num(base[0][key]), num(m[key])
            delta = None if a is None or b is None else b - a
            ch = "" if delta is None or abs(delta) < 1e-9 else f"{delta:+g} {verdict(delta, d)}".strip()
            lines.append(f"| {name} | {fmt(base[0][key])} | {fmt(m[key])} | {ch} |")
        else:
            lines.append(f"| {name} | {fmt(m[key])} |")

    if base and "+" in label and label == args.config:   # replicate labels (…-d1) skip this
        lines += interaction(set_name, label, m, base[0])

    if base:
        changed = []
        for r in rows:
            b = base[1].get(r["id"])
            if not b:
                continue
            diffs = []
            for k, name in [("sub", "subcategory"), ("outcome", "outcome"), ("priority", "priority")]:
                if r[k] != b[k]:
                    diffs.append(f"{name} {b[k]} → {r[k]}")
            if r["flags"] != b["flags"]:
                diffs.append(f"flags {b['flags']} → {r['flags']}")
            if r["draft"] != b["draft"]:
                sb = b["judge"]["score"] if b["judge"] and "score" in b["judge"] else "—"
                sa = r["judge"]["score"] if r["judge"] and "score" in r["judge"] else "—"
                diffs.append(f"draft changed (score {sb} → {sa})")
            if diffs:
                changed.append(f"| {r['id']} | {r['targets']} | {'; '.join(diffs)} |")
        lines += ["", f"## Tickets that changed ({len(changed)})", ""]
        lines += (["| Ticket | Targets | What changed |", "|---|---|---|"] + changed) if changed else ["None."]

    lines += ["", "## Every ticket", "", "| Ticket | Gold | Got | Outcome | Priority | Flags | Draft score | Judge notes |",
              "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        j = r["judge"] or {}
        lines.append(f"| {r['id']} | {r['gold_sub']} | {'✓' if r['sub_ok'] else '✗ ' + str(r['sub'])} | "
                     f"{r['outcome']}{'' if r['outcome_ok'] else ' ✗ (' + r['gold_outcome'] + ')'} | "
                     f"{r['priority']}{'' if r['priority_ok'] else ' ✗ (' + r['gold_priority'] + ')'} | "
                     f"{', '.join(r['flags'])} | {j.get('score', '—')}{' ⚠' if r['bad'] else ''} | "
                     f"{(j.get('problems') or '').replace('|', '/')} |")
    (out_dir / f"{label}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {(out_dir / f'{label}.md').relative_to(ROOT)}")
    write_summary(set_name)


def interaction(set_name: str, label: str, m: dict, bm: dict) -> list[str]:
    """Compare the combo with what the single fixes predict if their effects simply added up."""
    parts = label.split("+")
    singles = {}
    for p in parts:
        f = docs_dir(set_name) / "metrics" / f"{p}.json"
        if not f.exists():
            return ["", f"_No interaction check: {p} has not been reported on its own yet._"]
        singles[p] = json.loads(f.read_text(encoding="utf-8"))["metrics"]
    out = ["", "## Interaction with the single fixes", "",
           "Expected = baseline + the change each fix made on its own. A non-zero difference means the fixes "
           "affect each other.", "", "| Metric | Expected if independent | Observed | Difference |", "|---|---|---|---|"]
    for key, name, _ in LABELS:
        base = num(bm[key])
        if base is None or num(m[key]) is None or any(num(s[key]) is None for s in singles.values()):
            continue
        exp = base + sum(num(s[key]) - base for s in singles.values())
        diff = num(m[key]) - exp
        if abs(diff) > 1e-9 or any(abs(num(s[key]) - base) > 1e-9 for s in singles.values()):
            out.append(f"| {name} | {exp:g} | {num(m[key]):g} | {diff:+g} |")
    return out


def write_summary(set_name: str) -> None:
    d = docs_dir(set_name) / "metrics"
    found = {f.stem: json.loads(f.read_text(encoding="utf-8"))["metrics"] for f in d.glob("*.json")}
    order = sorted(found, key=lambda k: (not k.startswith("baseline"), k.count("+"), k))
    keys = ["final_subcategory", "wrong_not_escalated", "outcome", "draft_available", "priority", "fee", "escalated", "flagged",
            "bad_drafts", "bad_ready", "mean_score", "model_calls"]
    names = {k: n for k, n, _ in LABELS}
    lines = [f"# Summary: {set_name}", "", "Generated by `scripts/experiment.py summary`. One row per configuration "
             "(see the per-config pages for details).", "",
             "| Config | " + " | ".join(names[k] for k in keys) + " |", "|---" * (len(keys) + 1) + "|"]
    for c in order:
        lines.append(f"| [{c}]({c}.md) | " + " | ".join(fmt(found[c].get(k)) for k in keys) + " |")
    (docs_dir(set_name) / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def cmd_summary(args) -> None:
    write_summary(Path(args.set).stem)
    print((docs_dir(Path(args.set).stem) / "summary.md").read_text(encoding="utf-8"))


def cmd_pool(args) -> None:
    """Compare draft quality pooled over replicate runs (A vs B), e.g. three baseline
    draft replicates vs three replicates of a drafter fix. Classification is held fixed
    by the cache, so only the drafts differ."""
    set_name = Path(args.set).stem

    def pooled(labels):
        rows = []
        for lab in labels:
            _, rr, _ = scored(set_name, lab)
            rows += [r for r in rr if r["judge"] and "error" not in r["judge"]]
        n = len(rows)
        out = {"runs": len(labels), "drafts": n, "bad": sum(r["bad"] for r in rows),
               "mean_score": round(sum(r["judge"]["score"] for r in rows) / n, 3) if n else None}
        out.update({k: round(sum(bool(r["judge"].get(k)) for r in rows) / n, 3) if n else None for k in JUDGE_CHECKS})
        per = {}
        for r in rows:
            per.setdefault(r["id"], []).append(r["judge"]["score"])
        return out, {k: sum(v) / len(v) for k, v in per.items()}

    a, b = args.a.split(","), args.b.split(",")
    (ma, pa), (mb, pb) = pooled(a), pooled(b)
    lines = [f"# Pooled drafts: {args.name}", "", f"A = {', '.join(a)}  ", f"B = {', '.join(b)}", "",
             "| Metric | A | B | Change |", "|---|---|---|---|"]
    for k in ["runs", "drafts", "bad", "mean_score"] + JUDGE_CHECKS:
        d = None if ma[k] is None or mb[k] is None else round(mb[k] - ma[k], 3)
        lines.append(f"| {k} | {ma[k]} | {mb[k]} | {'' if not d else f'{d:+g}'} |")
    lines += ["", "Bad-draft share: A " + (f"{ma['bad'] / ma['drafts']:.1%}" if ma["drafts"] else "—")
              + ", B " + (f"{mb['bad'] / mb['drafts']:.1%}" if mb["drafts"] else "—"), "",
              "## Mean score per ticket (A → B)", "", "| Ticket | A | B |", "|---|---|---|"]
    for t in sorted(set(pa) | set(pb)):
        x, y = pa.get(t), pb.get(t)
        if x is None or y is None or abs(x - y) >= 0.5:
            lines.append(f"| {t} | {'—' if x is None else f'{x:.2f}'} | {'—' if y is None else f'{y:.2f}'} |")
    lines.append("\n(only tickets whose mean moved by 0.5 or more are listed)")
    out = docs_dir(set_name) / f"pooled-{args.name}.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:16]))


def cmd_judge_noise(args) -> None:
    set_name = Path(args.set).stem
    run = load_run(set_name, args.config)
    a, b = judge_all(run), judge_all(run, salt="\n\n(second review)")
    ids = [i for i in a if a[i] and b.get(i) and "error" not in a[i] and "error" not in b[i]]
    lines = [f"# Judge noise: {args.config} graded twice", "",
             f"The same {len(ids)} drafts, graded twice by the evaluator. Differences are the judge's own noise.", "",
             "| Check | Same verdict |", "|---|---|"]
    for k in JUDGE_CHECKS + ["bad"]:
        same = sum((bad(a[i]) == bad(b[i])) if k == "bad" else (a[i].get(k) == b[i].get(k)) for i in ids)
        lines.append(f"| {k} | {same}/{len(ids)} |")
    same_score = sum(a[i]["score"] == b[i]["score"] for i in ids)
    within1 = sum(abs(a[i]["score"] - b[i]["score"]) <= 1 for i in ids)
    lines += [f"| score identical | {same_score}/{len(ids)} |", f"| score within 1 | {within1}/{len(ids)} |"]
    (docs_dir(set_name) / "judge_noise.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("run", "report", "judge-noise", "summary", "pool"):
        p = sub.add_parser(name)
        if name == "pool":
            p.add_argument("--a", required=True, help="comma-separated run labels")
            p.add_argument("--b", required=True, help="comma-separated run labels")
            p.add_argument("--name", required=True)
        elif name != "summary":
            p.add_argument("config", help="baseline, or fix codes joined by +, e.g. F2+F3")
        p.add_argument("--set", default=str(DEFAULT_SET))
        p.add_argument("--label", help="name for this run (default: the config)")
        p.add_argument("--vs", default="baseline")
        p.add_argument("--workers", type=int, default=5)
        p.add_argument("--backend", default=os.getenv("LLM_BACKEND", "cli"))
        p.add_argument("--nocache", action="store_true", help="fresh model calls (noise check)")
        p.add_argument("--salt", help='fresh replies for some roles only, e.g. "drafter=d1"')
    args = ap.parse_args()
    {"run": cmd_run, "report": cmd_report, "judge-noise": cmd_judge_noise, "summary": cmd_summary,
     "pool": cmd_pool}[args.cmd](args)


if __name__ == "__main__":
    main()
