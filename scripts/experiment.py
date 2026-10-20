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
    return json.loads(run_path(set_name, label).read_text(encoding="utf-8"))


# ---------------------------------------------------------------- run

def cmd_run(args) -> None:
    src = Path(args.set)
    label = args.label or args.config
    env = {**os.environ, "PIPELINE_FIXES": ",".join(flags_for(args.config)), "LLM_BACKEND": args.backend}
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
    facts = "none"
    for line in (dr or {}).get("data", {}).get("user_prompt", "").splitlines():
        if line.startswith("Known facts:"):
            facts = line.removeprefix("Known facts:").strip()
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
        rows.append({
            "id": g["id"], "targets": g.get("targets", ""),
            "gold_sub": g["subcategory"], "sub": ex.get("subcategory"),
            "sub_ok": ex.get("subcategory") == g["subcategory"],
            "gold_outcome": g["outcome"], "outcome": r["outcome"], "outcome_ok": r["outcome"] == g["outcome"],
            "draft_avail_ok": has_draft == (g["outcome"] != "escalated"),
            "gold_priority": g["priority"], "priority": r.get("priority"), "priority_ok": r.get("priority") == g["priority"],
            "amount_ok": None if "amount_iqd" not in g else ex.get("amount_iqd") == g["amount_iqd"],
            "fee_ok": None if g.get("fee_iqd") is None else ex.get("fee_iqd") == g["fee_iqd"],
            "ref_ok": None if "reference" not in g else
                      (_key(ex["reference"]) if ex.get("reference") else None) == (_key(g["reference"]) if g["reference"] else None),
            "flags": r.get("flags", []),
            "calls": (cl is not None and cl["status"] == "done") + (rc is not None and rc["status"] == "done")
                     + (dr is not None and dr["status"] == "done" and not dr["data"].get("template")),
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
        "subcategory": rate("sub_ok"), "outcome": rate("outcome_ok"), "draft_available": rate("draft_avail_ok"),
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
    ("subcategory", "Subcategory correct", +1), ("outcome", "Outcome matches gold", +1),
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

    if base and "+" in label:
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
    keys = ["subcategory", "outcome", "draft_available", "priority", "fee", "escalated", "flagged",
            "bad_drafts", "bad_ready", "mean_score", "model_calls"]
    names = {k: n for k, n, _ in LABELS}
    lines = [f"# Summary: {set_name}", "", "Generated by `scripts/experiment.py summary`. One row per configuration "
             "(see the per-config pages for details).", "",
             "| Config | " + " | ".join(names[k] for k in keys) + " |", "|---" * (len(keys) + 1) + "|"]
    for c in order:
        lines.append(f"| [{c}]({c}.md) | " + " | ".join(fmt(found[c][k]) for k in keys) + " |")
    (docs_dir(set_name) / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def cmd_summary(args) -> None:
    write_summary(Path(args.set).stem)
    print((docs_dir(Path(args.set).stem) / "summary.md").read_text(encoding="utf-8"))


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
    for name in ("run", "report", "judge-noise", "summary"):
        p = sub.add_parser(name)
        if name != "summary":
            p.add_argument("config", help="baseline, or fix codes joined by +, e.g. F2+F3")
        p.add_argument("--set", default=str(DEFAULT_SET))
        p.add_argument("--label", help="name for this run (default: the config)")
        p.add_argument("--vs", default="baseline")
        p.add_argument("--workers", type=int, default=5)
        p.add_argument("--backend", default=os.getenv("LLM_BACKEND", "cli"))
        p.add_argument("--nocache", action="store_true", help="fresh model calls (noise check)")
    args = ap.parse_args()
    {"run": cmd_run, "report": cmd_report, "judge-noise": cmd_judge_noise, "summary": cmd_summary}[args.cmd](args)


if __name__ == "__main__":
    main()
