"""Pipeline viewer: watch tickets go through every stage, live, and record what the agent decides.

    python app/server.py                  # then open http://localhost:8000
    LLM_BACKEND=cli python app/server.py  # live runs through this computer's Claude Code login (development)

The viewer runs new tickets on the API backend unless LLM_BACKEND says otherwise (config/models.yaml
defaults to cli for the scripts): with no key, live runs are off and the page says so; with a key
they run the measured configuration under the spending cap (budget_usd, LLM_BUDGET_USD).

Standard library only. Streams pipeline events to the browser with Server-Sent Events.

Local only, by design. It binds 127.0.0.1 and answers only requests whose Host (and Origin, when
sent) is this machine, so another web page, or a DNS name re-pointed at 127.0.0.1, cannot drive it.
Every /api/ call must carry the token the page is served with. A live run spends money, so it is a
POST, one at a time, and stops calling models once the browser goes away. No request is logged:
URLs and bodies can carry ticket text.

The page is index.html at /, plus its scripts, styles and fonts under /static/ (an allow-list of file
types, nothing outside app/static). The Content-Security-Policy allows nothing inline and nothing from
another site, so a ticket or a model reply that gets into the page as markup still can't run a script.
"""

from __future__ import annotations

import difflib
import getpass
import hashlib
import hmac
import json
import os
import queue
import re
import secrets
import selectors
import shutil
import socket
import sys
import threading
import time
import traceback
import uuid
from collections import OrderedDict
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pipeline import classify as cls  # noqa: E402
from pipeline import draft as drf  # noqa: E402
from pipeline import draft_check, fixes, handoff  # noqa: E402
from pipeline.clean import clean  # noqa: E402
from pipeline.config import CONFIG_DIR, limits, models, pipeline_mode, taxonomy  # noqa: E402
from pipeline.config import thresholds as load_thresholds  # noqa: E402
from pipeline.llm import (BackendError, api_key, assert_real_data_safe, backend, budget_usd, cache_only,  # noqa: E402
                          model_for, real_data)
from pipeline.run import ACCOUNT_RISK, FLAG_AR, QUIET_FLAGS, process  # noqa: E402

STATIC = Path(__file__).parent / "static"
PROBES = ROOT / "data" / "probes"
RUNS = ROOT / "runs"
SAVED = ROOT / "docs" / "runs"   # committed runs (docs/runs/<set>/<label>.json): replay from a fresh clone, no key


# Dataset splits the viewer may show. heldout and heldout2 stay sealed: their text is not shown here.
SPLITS = ("dev", "mvp_test", "test2")

# Ticket ids of the sealed sets. A batch run saved at the top of runs/ names its set after the file
# ("tickets" for every split), so its ids are what show it came from a sealed set.
SEALED_IDS = ("hold-", "h2-")

# A random token per process. The page gets it in a <meta> tag; a page from any other site can't
# read it (same-origin policy), so it can't make /api/ calls.
TOKEN = secrets.token_urlsafe(32)
LOOPBACK = ("localhost", "127.0.0.1", "[::1]")

# Nothing inline (no <script> or <style> blocks, style="" or onclick=) and nothing from another site:
# scripts, styles and fonts come from /static/ only.
CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; font-src 'self'; img-src 'self' data:; "
       "connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")

SECURITY_HEADERS = {
    "Content-Security-Policy": CSP,
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cache-Control": "no-store",
}

ERR_AR = {
    "host": "هذا العنوان مو مسموح: افتح الصفحة من localhost",
    "origin": "الطلب جاي من صفحة ثانية: مرفوض",
    "token": "مفتاح الصفحة ناقص أو غلط: حدّث الصفحة وجرب مرة ثانية",
    "not_found": "ما لقينا هذا الطلب",
    "no_run": "ما لقينا هذا التشغيل",
    "method": "تشغيل التذكرة لازم يكون بطلب POST",
    "content_type": "لازم يكون الطلب JSON",
    "length": "الطلب ناقصه طوله (Content-Length)",
    "too_big": "الطلب أكبر من الحد المسموح",
    "bad_json": "الطلب مو JSON صحيح",
    "empty": "اكتب نص التذكرة أول",
    "bad_text": "نص التذكرة بيه رموز مو صحيحة: انسخه مرة ثانية",
    "too_long": "التذكرة أطول من الحد المسموح ({limit} حرف)",
    "busy": "اكو تذكرة دتنعالج هسه، انتظر لما تخلص",
    "field": "قيمة غلط بالحقل: {field}",
    "text_too_long": "النص أطول من الحد المسموح ({limit} حرف)",
    "run_param": "حدد التشغيل (run)",
    "internal": "صار خطأ داخلي، جرب مرة ثانية",
    # 409: the decision clashes with what the log already holds (another tab decided it, or the reply
    # still has something that blocks an approval).
    "decided": "هالتذكرة انحسمت قبل، بصفحة ثانية على الأغلب. حدّث القائمة",
    "undo_stale": "هالقرار مو آخر قرار على التذكرة، فما ينلغى. حدّث القائمة",
    "blocked": "{why}، فما ينعتمد. صلّح الرد أول",
    "identity": "ما أشّرت على «تأكدت من هوية الزبون»، فما ينعتمد",
    "escalated": "هالتذكرة متصعّدة، فما ينعتمد إلها رد: حوّلها أو استلمها",
}

# The agent's decision on a ticket (POST /api/decision), and why a draft needed changing.
DECISION_ACTIONS = ("approved", "edited", "took_over", "forwarded", "undone")
DECISION_ACTIONS_AR = {"approved": "اعتمد الرد", "edited": "عدّل الرد واعتمده", "took_over": "استلمها بنفسه",
                       "forwarded": "حوّلها لقسم ثاني", "undone": "تراجع عن القرار"}
REASON_CODES = ("wrong_type", "wrong_team", "wrong_priority", "tone", "dialect", "asks_unneeded", "promise",
                "false_claim", "wrong_number", "missing_question", "shop_or_agent_name", "duplicate",
                "instructions", "other")
REASON_CODES_AR = {"wrong_type": "نوع المشكلة غلط", "wrong_team": "القسم غلط", "wrong_priority": "الأولوية غلط",
                   "tone": "الأسلوب ما يناسب", "dialect": "اللهجة مو مضبوطة", "asks_unneeded": "يطلب شي ما نحتاجه",
                   "promise": "يوعد بشي ما نكدر نضمنه", "false_claim": "يقول شي ما صار", "wrong_number": "بيه رقم غلط",
                   "missing_question": "ناقصة سؤال للزبون", "shop_or_agent_name": "ما سأل عن اسم المحل أو الوكيل",
                   "duplicate": "تذكرة مكررة", "instructions": "التذكرة بيها أوامر للنظام",
                   "other": "شي ثاني"}
OUTCOMES = ("drafted", "flagged", "escalated")
PRIORITIES = ("P1", "P2", "P3")
DECISION_FIELDS = {"run", "ticket_id", "action", "pipeline_outcome", "flags", "reason_codes", "seconds",
                   "draft_text", "final_text", "corrected", "undoes", "visits", "warnings_acknowledged"}
_TICKET_ID = re.compile(r"[A-Za-z0-9_.:-]{1,64}")
_FLAG = re.compile(r"[A-Za-z0-9_.:-]{1,64}")
_DECISION_ID = re.compile(r"[0-9a-f]{32}")

# The draft checks that stop an approval: the agent fixes the draft first (POST /api/check says when it
# is clean). The other kinds are warnings the agent reads and decides on.
BLOCKING_CHECKS = ("asks_secret", "hold_reason", "sensitive_number")
CHECK_FIELDS = {"draft", "allowed_text", "subcategory"}
# Why the server refuses an approval whose reply still has a blocking check (409; the page blocks it first).
BLOCKED_AR = {"asks_secret": "الرد يطلب رمز أو كلمة سر من الزبون",
              "hold_reason": "الرد يذكر تحقيق أو اشتباه أو بلاغ",
              "sensitive_number": "الرد يكرر رقم بطاقة أو رمز"}
# What an agent can tick "I checked it" for and approve anyway, logged as kinds, never text: the draft
# warnings that do not block, a draft written for another type than the one the agent chose, the
# pipeline's own points (its flags: account_risk is the customer's identity, confirmed by the
# institution's own procedure; recheck_used_second the type), a missing field the reply asks for
# (missing:<field>), one the agent marks as not needed (missing:<field>:not_needed), and a second request
# in a drafted ticket that no team is routed to (second_request: the agent read what the reply says of
# it). An allow-list. A draft warning behind a flag (draft_check.FLAG_KINDS; none since the 7 Nov ones
# were adopted) is in it whether or not its flag is on now: a run saved with the flag on still has it. A
# quiet flag (run.QUIET_FLAGS) is shown, never ticked, so it is not.
_ACK_FIELDS = tuple(drf.FIELD_AR)
ACK_KINDS = tuple(dict.fromkeys(
    [k for k in draft_check.KINDS + draft_check.FLAG_KINDS if k not in BLOCKING_CHECKS]
    + ["draft_for_other_type", "second_request"]
    + [f for f in FLAG_AR if not f.startswith("draft:") and f not in QUIET_FLAGS]
    + [f"missing:{f}" for f in _ACK_FIELDS] + [f"missing:{f}:not_needed" for f in _ACK_FIELDS]))

# Files under /static/: these types only, each with its exact content type. index.html is served at /.
STATIC_TYPES = {
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".woff2": "font/woff2",
    ".svg": "image/svg+xml",
    ".txt": "text/plain; charset=utf-8",
}
_STATIC_PART = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,99}")   # no dot first: no "..", no hidden file
_STATIC_MAX_PATH = 256

POLL_S = 0.25          # how often a live stream checks whether the browser is still there
DRAIN_CAP = 1 << 20    # an unread request body up to this size is read before refusing it


def ticket_sets() -> list[str]:
    return [s for s in SPLITS if (ROOT / "data" / s / "tickets.jsonl").exists()] + sorted(p.stem for p in PROBES.glob("*.jsonl"))


def load_tickets(name: str) -> list[dict]:
    """A listed set's tickets; any other name (a sealed split, a path) gets nothing."""
    if name not in ticket_sets():
        return []
    path = ROOT / "data" / name / "tickets.jsonl" if name in SPLITS else PROBES / f"{name}.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


# --- static files ---

def static_file(rel: str) -> tuple[Path, str] | None:
    """The file that /static/<rel> names, and its content type; None for anything else. rel is the URL
    path as sent (never percent-decoded): each part must be a plain name that doesn't start with a dot,
    so "..", "%2e%2e", a hidden file, a backslash, a NUL and an empty part ("js/", "//") are all None.
    The file must have an allowed type, exist, and still be inside app/static once symlinks are
    followed. A folder is never listed."""
    if len(rel) > _STATIC_MAX_PATH:
        return None
    parts = rel.split("/")
    if not all(_STATIC_PART.fullmatch(p) for p in parts):
        return None
    ctype = STATIC_TYPES.get(Path(parts[-1]).suffix)   # exact: ".CSS" or ".js.map" is not served
    if ctype is None:
        return None
    root = STATIC.resolve()
    try:
        f = root.joinpath(*parts).resolve(strict=True)
    except (OSError, RuntimeError):   # missing, or a symlink loop
        return None
    if not f.is_relative_to(root) or not f.is_file():
        return None
    return f, ctype


# --- saved runs ---

def _sealed(set_name) -> bool:
    return str(set_name or "").lower().startswith("heldout")


def _has_sealed_ids(rows) -> bool:
    return any(isinstance(r, dict) and isinstance(r.get("ticket"), dict)
               and str(r["ticket"].get("id", "")).startswith(SEALED_IDS) for r in rows)


def _candidates() -> list[tuple[str, Path, bool]]:
    """(name, file, named after its folder) for committed runs (docs/runs/<set>/<label>.json), saved
    batch runs (runs/*.json) and experiment runs (runs/exp/<set>/<config>.json). Nothing else under
    runs/ is a candidate: the cache, generation files and judge files never reach the page."""
    saved = [("saved/" + f.relative_to(SAVED).with_suffix("").as_posix(), f, True) for f in sorted(SAVED.glob("*/*.json"))]
    batch = [(f.relative_to(RUNS).with_suffix("").as_posix(), f, False) for f in sorted(RUNS.glob("*.json"), reverse=True)]
    exp = [(f.relative_to(RUNS).with_suffix("").as_posix(), f, True) for f in sorted(RUNS.glob("exp/*/*.json"))]
    return saved + batch + exp


_summaries: dict[Path, tuple[tuple[int, int], dict | None]] = {}
_summaries_lock = threading.Lock()


def _summary(f: Path) -> dict | None:
    """{"meta", "sealed_ids"} if the file is a run (top-level "meta" and "tickets"), else None.
    Kept until the file changes: the experiment runs alone are ~24 MB, and every /api/run lists them."""
    try:
        st = f.stat()
    except OSError:
        return None
    stamp = (st.st_mtime_ns, st.st_size)
    with _summaries_lock:
        hit = _summaries.get(f)
    if hit and hit[0] == stamp:
        return hit[1]
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = None
    ok = isinstance(data, dict) and isinstance(data.get("meta"), dict) and isinstance(data.get("tickets"), list)
    summary = {"meta": data["meta"], "sealed_ids": _has_sealed_ids(data["tickets"]), "n": len(data["tickets"])} if ok else None
    with _summaries_lock:
        _summaries[f] = (stamp, summary)
    return summary


def _index() -> list[tuple[dict, Path]]:
    """Every run the page may show, with its file. A sealed set's folder is never opened."""
    out = []
    for name, f, by_folder in _candidates():
        if by_folder and _sealed(f.parent.name):
            continue
        s = _summary(f)
        if s is None or s["sealed_ids"]:
            continue
        meta = {**s["meta"], "set": f.parent.name} if by_folder else s["meta"]   # every split's file is tickets.jsonl
        if _sealed(meta.get("set")):
            continue
        out.append(({**meta, "name": name, "experiment": by_folder, "n": s.get("n")}, f))
    return out


def list_runs() -> list[dict]:
    return [entry for entry, _ in _index()]


def run_file(name: str) -> Path | None:
    """The file behind a name list_runs() lists, else None: the name is looked up, never used as a
    path, so a sealed set, a traversal, a NUL or a 10,000-character name all come back None."""
    try:
        return next((f for entry, f in _index() if entry["name"] == name), None)
    except (OSError, ValueError):
        return None


def _gold_file(name: str) -> Path | None:
    if _sealed(name):
        return None
    src = ROOT / "data" / name / "tickets.jsonl" if (ROOT / "data" / name).is_dir() else PROBES / f"{name}.jsonl"
    return src if src.exists() else None


_recomputed: dict[Path, tuple[tuple, dict]] = {}   # kept like _summaries: until the file (or what the checks read) changes


def _draft_subcategory(result: dict) -> str | None:
    """The issue type the draft was written for (after a re-check swap, the re-check's), if it is
    still in the taxonomy: its policy facts are what the draft was checked against."""
    ex = result.get("extraction")
    sub = ex.get("subcategory") if isinstance(ex, dict) else None
    return sub if isinstance(sub, str) and sub in taxonomy().subcategories else None


def recompute_checks(tickets: list) -> dict[int, dict]:
    """For runs made before 1 Nov, which saved no spans: per ticket (by its index in the file), the
    draft "done" events that have no check_spans ({event index: findings}) and, when result.draft_checks
    is missing or null, the result's (key "result"). Computed exactly as run.py does now:
    draft_check.findings(reply, user_prompt, facts) with the policy facts for the draft's issue type.
    A ticket with no draft, or no drafter prompt to check against, gets nothing."""
    out: dict[int, dict] = {}
    facts_by_sub: dict[str | None, str] = {}
    for i, row in enumerate(tickets):
        if not isinstance(row, dict):
            continue
        result = row.get("result") if isinstance(row.get("result"), dict) else {}
        events = row.get("events") if isinstance(row.get("events"), list) else []
        sub = _draft_subcategory(result)
        if sub not in facts_by_sub:
            facts_by_sub[sub] = drf.facts_text(sub)
        facts = facts_by_sub[sub]
        patch: dict = {}
        prompt = None
        for j, ev in enumerate(events):
            data = ev.get("data") if isinstance(ev, dict) else None
            if not (isinstance(data, dict) and ev.get("stage") == "draft" and ev.get("status") == "done"):
                continue
            reply, user = data.get("reply"), data.get("user_prompt")
            if not (isinstance(reply, str) and isinstance(user, str)):
                continue
            prompt = user
            if "check_spans" not in data:
                patch[j] = draft_check.findings(reply, user, facts)
        if result.get("draft_checks") is None and isinstance(result.get("draft_ar"), str) and prompt is not None:
            patch["result"] = draft_check.findings(result["draft_ar"], prompt, facts)
        if patch:
            out[i] = patch
    return out


def _with_checks(f: Path, run: dict, stamp: tuple | None) -> None:
    """Add the recomputed spans (see recompute_checks) to a run as read from f, marking each one
    recomputed. Nothing else changes. The spans are kept until the file, the policy facts or the
    active check flags change."""
    tickets = run.get("tickets")
    if not isinstance(tickets, list):
        return
    try:
        pst = (CONFIG_DIR / "policy.yaml").stat()
        policy_stamp = (pst.st_mtime_ns, pst.st_size)
    except OSError:
        policy_stamp = None
    key = (stamp, policy_stamp, fixes.active())
    with _summaries_lock:
        hit = _recomputed.get(f)
    if stamp is not None and hit and hit[0] == key:
        patches = hit[1]
    else:
        patches = recompute_checks(tickets)
        if stamp is not None:
            with _summaries_lock:
                _recomputed[f] = (key, patches)
    for i, patch in patches.items():
        row = tickets[i]
        for j, spans in patch.items():
            if j == "result":
                row["result"] = {**row["result"], "draft_checks": spans, "draft_checks_recomputed": True}
            else:
                ev = row["events"][j]
                ev["data"] = {**ev["data"], "check_spans": spans, "check_spans_recomputed": True}


def _gets_account_risk(result) -> bool:
    """A saved result that run.py would flag account_risk today but that has no such flag (runs made
    before 5 Nov): a draft was written (draft_ar) for a blocked account or a SIM change, the type the
    draft was written for (after a re-check swap, the re-check's). An escalation never gets it."""
    if not isinstance(result, dict) or result.get("outcome") not in ("drafted", "flagged"):
        return False
    flags = result.get("flags")
    ex = result.get("extraction")
    return (isinstance(result.get("draft_ar"), str) and isinstance(flags, list) and "account_risk" not in flags
            and isinstance(ex, dict) and ex.get("subcategory") in ACCOUNT_RISK)


def _with_account_risk(result: dict) -> dict:
    """The result as run.py ends it now: account_risk after the gate and re-check flags and before the
    draft checks (the order run.py adds them), its note at the same place, outcome flagged, and
    account_risk_recomputed so the page can say the run is older than the rule."""
    flags = list(result["flags"])
    at = next((i for i, f in enumerate(flags) if isinstance(f, str) and f.startswith("draft:")), len(flags))
    flags.insert(at, "account_risk")
    out = {**result, "outcome": "flagged", "flags": flags, "account_risk_recomputed": True}
    notes = result.get("notes_ar")
    if isinstance(notes, list) and len(notes) == len(result["flags"]):
        out["notes_ar"] = notes[:at] + [FLAG_AR["account_risk"]] + notes[at:]
    return out


def apply_account_risk(tickets: list) -> int:
    """Runs made before 5 Nov: each drafted ticket that run.py would flag account_risk today gets the flag
    (outcome flagged, marked account_risk_recomputed), in its result and in its "result" event, the way
    recompute_checks adds the draft checks. Without it the viewer would show a blocked account or a SIM
    change as ready, approved with one key and no identity tick. The draft, team, priority and checks are
    unchanged. Returns how many tickets it changed."""
    n = 0
    for row in tickets:
        if not isinstance(row, dict) or not _gets_account_risk(row.get("result")):
            continue
        row["result"] = _with_account_risk(row["result"])
        n += 1
        events = row.get("events") if isinstance(row.get("events"), list) else []
        for j in range(len(events) - 1, -1, -1):
            ev = events[j]
            if isinstance(ev, dict) and ev.get("stage") == "result" and ev.get("status") == "done" \
                    and _gets_account_risk(ev.get("data")):
                events[j] = {**ev, "data": _with_account_risk(ev["data"])}
                break
    return n


def with_current_gold(f: Path) -> dict:
    """A saved run with each ticket's gold label taken from its set file as it is now, so a label
    corrected after the run (e.g. the author's t2-0033) is scored the same way as in the reports.
    A sealed set's file is never read. Drafts from runs made before 1 Nov get their check spans
    (recompute_checks), and runs made before 5 Nov the account_risk flag (apply_account_risk)."""
    before = f.stat()
    raw = f.read_text(encoding="utf-8")
    after = f.stat()
    run = json.loads(raw)
    stamp = (after.st_mtime_ns, after.st_size)
    if isinstance(run, dict):   # a file rewritten while it was read is checked but not kept
        _with_checks(f, run, stamp if stamp == (before.st_mtime_ns, before.st_size) else None)
        if isinstance(run.get("tickets"), list):
            apply_account_risk(run["tickets"])
    if f.parent.parent in (RUNS / "exp", SAVED):
        name = f.parent.name
        run["meta"] = {**run.get("meta", {}), "set": name}
        src = _gold_file(name)
        if src is not None:
            gold = {d["id"]: d for d in (json.loads(line) for line in src.read_text(encoding="utf-8").splitlines()
                                         if line.strip())}
            run["tickets"] = [{**row, "ticket": gold[row["ticket"]["id"]]} for row in run["tickets"]
                              if row["ticket"].get("id") in gold]
    return run


# --- meta ---

# The same causes in English, for the start-up line in the terminal.
LIVE_OFF_EN = {"pipeline_off": "PIPELINE_MODE=off", "bad_backend": "unknown LLM_BACKEND",
               "no_key": "no API key; set SUPPORT_PIPELINE_API_KEY",
               "no_cli": "no claude CLI; for the API unset LLM_BACKEND and set SUPPORT_PIPELINE_API_KEY"}

# The viewer's backend when LLM_BACKEND is not set. config/models.yaml says cli: free development runs on
# the author's Claude plan, for the scripts. The viewer is what a reader starts, so it runs the measured
# configuration instead: on someone else's computer, cli would run pasted tickets on their own Claude
# Code login, with a setup no number in this project was measured on.
VIEWER_BACKEND = "api"


def default_viewer_backend(environ=None) -> bool:
    """Set LLM_BACKEND to VIEWER_BACKEND in `environ` (os.environ) when it is unset or blank. An explicit
    LLM_BACKEND (cli, or a wrong value that start-up then refuses) is left as it is. True if it set it."""
    env = os.environ if environ is None else environ
    if (env.get("LLM_BACKEND") or "").strip():
        return False
    env["LLM_BACKEND"] = VIEWER_BACKEND
    return True


def live_status() -> dict:
    """Whether the page can run a new ticket, and if not, why (in Arabic, for the page)."""
    if pipeline_mode() == "off":
        return {"available": False, "reason_ar": "النظام موقف، فالتذاكر الجديدة يستلمها موظف بدون نموذج.",
                "cause": "pipeline_off"}
    # The agent gets one plain sentence; "cause" names the setting for «كيف يشتغل» and the logs.
    not_here = "التشغيل المباشر مو مفعّل على هذا الجهاز. تكدر تشتغل على التشغيلات المحفوظة بس."
    try:
        name = backend()
    except BackendError:
        return {"available": False, "reason_ar": not_here, "cause": "bad_backend"}
    if name == "api" and not api_key():
        return {"available": False, "reason_ar": not_here, "cause": "no_key"}
    if name == "cli" and not shutil.which(os.getenv("CLAUDE_BIN") or "claude"):
        return {"available": False, "reason_ar": not_here, "cause": "no_cli"}
    return {"available": True, "reason_ar": None}


def meta() -> dict:
    tax = taxonomy()
    return {
        "backend": backend(),
        "models": {role: model_for(role) for role in models()},
        "thresholds": load_thresholds()["confidence"],
        # team and default_priority let the page show what another answer (the first model's, or the
        # agent's correction) would be routed to: priority_rules is the one rule that raises it (route.py).
        "subcategories": {k: {"label": s.label_ar, "category": s.category,
                              "category_label": tax.categories_ar[s.category],
                              "team": s.team, "default_priority": s.default_priority,
                              # never drafted: a person takes it (the page re-gates an agent's correction)
                              "always_escalate": s.always_escalate}
                          for k, s in tax.subcategories.items()},
        "priority_rules": load_thresholds()["priority"],
        "teams": tax.teams,
        "live": live_status(),
        # LLM_CACHE_ONLY=1: a pasted ticket gets the stored model replies, with no call (the page says so).
        "cache_only": cache_only(),
        "limits": limits(),
        "mode": pipeline_mode(),
        "real_data": real_data(),
        "flag_ar": FLAG_AR,
        "decision_actions": list(DECISION_ACTIONS),
        "decision_actions_ar": DECISION_ACTIONS_AR,
        "reason_codes": list(REASON_CODES),
        "reason_codes_ar": REASON_CODES_AR,
        "ack_kinds": list(ACK_KINDS),
        "blocking_checks": list(BLOCKING_CHECKS),
        # A blocked account or a SIM change (run.py ACCOUNT_RISK): the page asks for the identity tick
        # when the agent's own correction makes a ticket one of these, as the pipeline's flag does.
        "account_risk_types": list(ACCOUNT_RISK),
        # Flags the page shows as a muted note, never as a point to tick (run.py QUIET_FLAGS).
        "quiet_flags": list(QUIET_FLAGS),
        "check_ar": CHECK_AR,
        "checks_active": checks_active(),
    }


def checks_active() -> list[str]:
    """The draft_check kinds that run now, for the page's "nothing found" line: every KINDS rule
    (hold_reason and sensitive_number since 5 Nov, the five user-test warnings since 7 Nov, when they
    stopped being flags), and each warning behind a flag (FLAG_KINDS) while its flag is on."""
    return list(draft_check.kinds_on())


# One line per draft_check kind, for the page to show beside a highlighted span (the flag wording). The
# warnings behind flags too: a run saved with the flag on is still shown with them.
CHECK_AR = {kind: FLAG_AR[f"draft:{kind}"] for kind in draft_check.KINDS + draft_check.FLAG_KINDS}


# --- checking a draft the agent edits ---

class TooLong(ValueError):
    """A /api/check text over its limit (413)."""

    def __init__(self, field: str, limit: int):
        super().__init__(field)
        self.field, self.limit = field, limit


def check_request(body: dict) -> tuple[str, str, str | None]:
    """(draft, allowed_text, subcategory) from a POST /api/check body. Raises BadField (400) or TooLong
    (413). The draft may be up to twice the ticket limit (room for any reply, as in the decision log);
    allowed_text, the drafter's whole prompt, up to four times."""
    unknown = set(body) - CHECK_FIELDS
    if unknown:
        raise BadField(sorted(unknown)[0])
    limit = limits()["max_ticket_chars"]
    out = []
    for key, most in (("draft", 2 * limit), ("allowed_text", 4 * limit)):
        value = body.get(key)
        if not isinstance(value, str):
            raise BadField(key)
        if len(value) > most:
            raise TooLong(key, most)
        try:
            value.encode("utf-8")   # a lone surrogate ("\ud83d") can't be checked or shown
        except UnicodeEncodeError:
            raise BadField(key) from None
        out.append(value)
    sub = body.get("subcategory")
    if sub is not None and (not isinstance(sub, str) or sub not in taxonomy().subcategories):
        raise BadField("subcategory")
    return out[0], out[1], sub


# --- the decision log ---

class BadField(ValueError):
    """A decision field that failed validation; its name (never its value) goes back to the page."""


_decisions_lock = threading.Lock()


def decisions_file() -> Path:
    return Path(os.getenv("DECISIONS_FILE") or RUNS / "decisions.jsonl")


def reviewer() -> str:
    try:
        return os.getenv("REVIEWER") or getpass.getuser()
    except Exception:  # noqa: BLE001 - no login name in some containers
        return "unknown"


# Key for the reply hashes in the decision log. Keyed, so a short edit (a phone number the agent typed)
# can't be found by hashing guesses against a known draft. Set DECISIONS_HASH_KEY to keep hashes
# comparable across restarts; otherwise each run of the viewer has its own key.
_HASH_KEY = (os.getenv("DECISIONS_HASH_KEY") or secrets.token_hex(32)).encode("utf-8")


def _sha256(text: str | None) -> str | None:
    return None if text is None else hmac.new(_HASH_KEY, text.encode("utf-8"), hashlib.sha256).hexdigest()


_DIFF_CELLS = 2_000_000   # above this many character pairs the exact diff is too slow for a request


def edit_chars(draft: str | None, final: str | None) -> int:
    """Characters the person changed between the draft and what they sent: 0 for an approval as
    drafted (or when nothing was sent), the whole reply when there was no draft. From difflib's
    opcodes, counting the longer side of each change, on the part between the shared start and end
    (difflib is quadratic: two 8,000-character rewrites took 13 s). A change too large for that
    counts the longer side whole."""
    if final is None or draft == final:
        return 0
    a, b = draft or "", final
    head = len(os.path.commonprefix([a, b]))
    a, b = a[head:], b[head:]
    tail = len(os.path.commonprefix([a[::-1], b[::-1]]))
    a, b = a[:len(a) - tail], b[:len(b) - tail]
    if len(a) * len(b) > _DIFF_CELLS:
        return max(len(a), len(b))
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    return sum(max(i2 - i1, j2 - j1) for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != "equal")


def _text_field(body: dict, key: str) -> str | None:
    value = body.get(key)
    # Twice the ticket limit is room for any reply, and keeps the diff fast.
    if value is not None and (not isinstance(value, str) or len(value) > 2 * limits()["max_ticket_chars"]):
        raise BadField(key)
    return value


def _corrected(raw) -> dict:
    """The agent's corrections, checked against the taxonomy. A null value means no correction."""
    if raw is None:
        return {}
    if not isinstance(raw, dict) or set(raw) - {"subcategory", "team", "priority"}:
        raise BadField("corrected")
    tax = taxonomy()
    allowed = {"subcategory": tax.subcategories, "team": tax.teams, "priority": PRIORITIES}
    out = {k: v for k, v in raw.items() if v is not None}
    for k, v in out.items():
        if not isinstance(v, str) or v not in allowed[k]:
            raise BadField(f"corrected.{k}")
    return out


def served_facts(result, events=None) -> dict:
    """What the page was served for one ticket, the way it reads it: outcome (escalated when there is no
    result), flags, the type the draft was written for, team, priority, and a keyed hash of the draft
    (result.draft_ar, else the last finished draft's reply). Never the text."""
    res = result if isinstance(result, dict) else {}
    draft = res.get("draft_ar")
    if not isinstance(draft, str):
        done = [e.get("data") for e in events or [] if isinstance(e, dict) and e.get("stage") == "draft"
                and e.get("status") == "done" and isinstance(e.get("data"), dict)]
        draft = done[-1].get("reply") if done else None
    ex = res.get("extraction")
    flags = res.get("flags") if isinstance(res.get("flags"), list) else []
    return {"outcome": res.get("outcome") if res.get("outcome") in OUTCOMES else "escalated",
            "flags": [f for f in flags if isinstance(f, str) and _FLAG.fullmatch(f)][:32],
            "subcategory": ex.get("subcategory") if isinstance(ex, dict) else None,
            "team": res.get("team"), "priority": res.get("priority"),
            "draft_sha256": _sha256(draft) if isinstance(draft, str) else None}


def served_ticket(run: str, ticket_id: str) -> dict | None:
    """The served facts of one ticket (served_facts): a live run's from this process's registry (none for
    an id it did not stream), a saved run's from the run as /api/run serves it. None if not served."""
    if run == "live":
        with _live_lock:
            entry = _live.get(ticket_id)
            return dict(entry) if entry else None
    f = run_file(run)
    data = with_current_gold(f) if f is not None else {}
    rows = data.get("tickets") if isinstance(data.get("tickets"), list) else []
    row = next((r for r in rows if isinstance(r, dict) and isinstance(r.get("ticket"), dict)
                and r["ticket"].get("id") == ticket_id), None)
    if row is None:
        return None
    return {**served_facts(row.get("result"), row.get("events")), "ticket_sha256": None}


def _never_drafted(sub) -> bool:
    s = taxonomy().subcategories.get(sub) if isinstance(sub, str) else None
    return bool(s and s.always_escalate)


def decision_record(body: dict) -> dict:
    """The log line for one decision. It keeps keyed hashes (HMAC-SHA256, see _HASH_KEY) of the draft
    and the final reply, and how many characters changed, but never the text itself: the log is for
    measuring the pipeline, and a reply can carry a customer's details. The outcome, flags and draft
    hash are the ones the server served for the ticket (served_ticket), not the request's: a ticket it
    did not serve is refused (400 ticket_id), and so is a draft_text other than the served draft, or an
    approval (unedited) whose reply is not that draft."""
    unknown = set(body) - DECISION_FIELDS
    if unknown:
        raise BadField(sorted(unknown)[0])
    run = body.get("run")
    if not isinstance(run, str) or not (run == "live" or any(e["name"] == run for e, _ in _index())):
        raise BadField("run")
    ticket_id = body.get("ticket_id")
    if not isinstance(ticket_id, str) or not _TICKET_ID.fullmatch(ticket_id):
        raise BadField("ticket_id")
    action = body.get("action")
    if action not in DECISION_ACTIONS:
        raise BadField("action")
    outcome = body.get("pipeline_outcome")
    if outcome not in OUTCOMES:
        raise BadField("pipeline_outcome")
    flags = body.get("flags", [])
    if not isinstance(flags, list) or len(flags) > 32 or not all(isinstance(f, str) and _FLAG.fullmatch(f) for f in flags):
        raise BadField("flags")
    codes = body.get("reason_codes", [])
    if not isinstance(codes, list) or not all(isinstance(c, str) and c in REASON_CODES for c in codes):
        raise BadField("reason_codes")
    seconds = body.get("seconds")
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not 0 <= seconds <= 36000:
        raise BadField("seconds")
    undoes = body.get("undoes")   # an undo names the decision it takes back, on the same ticket
    if (action == "undone") != (undoes is not None) or (undoes is not None and not (
            isinstance(undoes, str) and _DECISION_ID.fullmatch(undoes)
            and any(d.get("id") == undoes and d.get("ticket_id") == ticket_id for d in read_decisions(run)))):
        raise BadField("undoes")
    visits = body.get("visits")   # how many times the ticket was opened before this decision
    if visits is not None and (isinstance(visits, bool) or not isinstance(visits, int) or not 1 <= visits <= 10000):
        raise BadField("visits")
    acked = body.get("warnings_acknowledged", [])
    if not isinstance(acked, list) or not all(isinstance(k, str) and k in ACK_KINDS for k in acked):
        raise BadField("warnings_acknowledged")
    draft, final = _text_field(body, "draft_text"), _text_field(body, "final_text")
    if action in ("approved", "edited") and not isinstance(final, str):
        raise BadField("final_text")   # an approval names the reply, so the checks below can read it
    corrected = _corrected(body.get("corrected"))
    served = served_ticket(run, ticket_id)
    if served is None:
        raise BadField("ticket_id")
    if served["outcome"] is None:   # a live run with no result yet: the page shows it cut short
        served = {**served, "outcome": "escalated", "flags": [f for f in flags if f in LIVE_CUT_SHORT]}
    if draft and _sha256(draft) != served["draft_sha256"]:
        raise BadField("draft_text")
    if action == "approved" and served["draft_sha256"] and _sha256(final) != served["draft_sha256"]:
        raise BadField("final_text")   # (with no draft served, append_decision refuses it: 409 escalated)
    return {
        "id": uuid.uuid4().hex,
        "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "reviewer": reviewer(),
        "run": run, "ticket_id": ticket_id, "action": action, "pipeline_outcome": served["outcome"],
        "flags": served["flags"], "reason_codes": list(dict.fromkeys(codes)), "seconds": seconds,
        "corrected": corrected, "undoes": undoes, "visits": visits,
        "warnings_acknowledged": list(dict.fromkeys(acked)),
        "models": {role: model_for(role) for role in models()},
        "prompt_sha256": {"classifier": _sha256(cls.system_prompt()), "drafter": _sha256(drf.system_prompt())},
        "draft_sha256": served["draft_sha256"],
        "final_sha256": _sha256(final),
        "edit_chars": edit_chars(draft, final),
        "ticket_sha256": served["ticket_sha256"],   # live runs: the cleaned ticket text, keyed
        # Kept for the checks in append_decision; never written to the log.
        "_final": final,
        "_never_drafted": _never_drafted(served["subcategory"]) or _never_drafted(corrected.get("subcategory")),
    }


class Conflict(ValueError):
    """A decision the log can't take (409): its key in ERR_AR, and the text for {why} if any."""

    def __init__(self, key: str, why: str = ""):
        super().__init__(key)
        self.key, self.why = key, why


def blocking_in(reply: str | None) -> list[str]:
    """The blocking draft checks in a reply (BLOCKING_CHECKS). They don't read the drafter's prompt, so
    the server can run them on any reply, the same rules as POST /api/check."""
    if not reply:
        return []
    return [f["kind"] for f in draft_check.findings(reply, "", "") if f["kind"] in BLOCKING_CHECKS]


def standing(records: list[dict]) -> dict[str, dict]:
    """The decision that stands on each ticket: the latest one not undone (the page computes the same)."""
    undone = {d.get("undoes") for d in records if d.get("action") == "undone"}
    out: dict[str, dict] = {}
    for d in records:
        if d.get("action") == "undone" or d.get("id") in undone:
            continue
        out[d.get("ticket_id")] = d
    return out


def needs_identity(record: dict) -> bool:
    """An approval needs «تأكدت من هوية الزبون» (warnings_acknowledged "account_risk") when the ticket is
    a blocked account or a SIM change: the flags the server served for it (the record's, see
    decision_record: a request that leaves the flag out is not believed), or the type the agent
    corrected it to."""
    return "account_risk" in record.get("flags", []) or (record.get("corrected") or {}).get("subcategory") in ACCOUNT_RISK


def append_decision(record: dict) -> None:
    """One line, one write: concurrent decisions never interleave. A new log is readable by its owner
    only (0600). Under the same lock, four checks (Conflict, 409):
    - an approval of a ticket served as an escalation, or of a type that is never drafted (fraud), as
      served or as the agent corrected it: it can only be forwarded or taken over;
    - an approval whose reply still asks for a code, names an investigation or repeats a card number
      (the page blocks it first; this stops a stale check or a hand-made request);
    - an approval of a blocked account or a SIM change without the identity tick (needs_identity);
    - a second decision on a ticket that already has one standing (another tab decided it), or an undo
      of a decision that no longer stands. Live tickets too: each live run has its own id."""
    final = record.pop("_final", None)
    never_drafted = record.pop("_never_drafted", False)
    if record["action"] in ("approved", "edited"):
        if record["pipeline_outcome"] == "escalated" or never_drafted:
            raise Conflict("escalated")
        found = blocking_in(final)
        if found:
            raise Conflict("blocked", BLOCKED_AR[found[0]])
        if "account_risk" not in record["warnings_acknowledged"] and needs_identity(record):
            raise Conflict("identity")
    line = json.dumps(record, ensure_ascii=False) + "\n"
    path = decisions_file()
    with _decisions_lock:
        now = standing(_read_decisions_unlocked(record["run"])).get(record["ticket_id"])
        if record["action"] == "undone" and (now is None or now.get("id") != record["undoes"]):
            raise Conflict("undo_stale")
        if record["action"] != "undone" and now is not None:
            raise Conflict("decided")
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        with open(fd, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()


def read_decisions(run: str) -> list[dict]:
    """The decisions logged for one run, oldest first. A line that isn't JSON is skipped."""
    with _decisions_lock:
        return _read_decisions_unlocked(run)


def _read_decisions_unlocked(run: str) -> list[dict]:
    try:
        lines = decisions_file().read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    out = []
    for line in lines:
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if isinstance(d, dict) and d.get("run") == run:
            out.append(d)
    return out


# --- live runs ---

# The live runs this process streamed, by the id the server gave each (live_started): what it served
# (served_facts) and a keyed hash of the cleaned ticket text, for the decision log's checks. Never the
# text. In memory only, the newest LIVE_KEEP; a restarted viewer knows none (and has a new page token).
LIVE_KEEP = 1000
_live: OrderedDict[str, dict] = OrderedDict()
_live_lock = threading.Lock()
# What the page shows for a live run whose stream was cut short (no result): the flags a take-over or a
# forward of it may carry while the server still waits for the result.
LIVE_CUT_SHORT = ("cancelled", "connection_lost")


def live_started(text: str) -> str:
    """Register a new live run and return its id: live-<UTC yyyymmddHHMMSS>-<6 hex>."""
    run_id = f"live-{datetime.now(timezone.utc):%Y%m%d%H%M%S}-{secrets.token_hex(3)}"
    entry = {**served_facts(None), "outcome": None, "ticket_sha256": _sha256(clean(text))}
    with _live_lock:
        _live[run_id] = entry
        while len(_live) > LIVE_KEEP:
            _live.popitem(last=False)
    return run_id


def live_served(run_id: str, event: dict, events: list) -> None:
    """Keep what a live run served once its result is out (events: its earlier events, for the draft)."""
    if event.get("stage") != "result" or event.get("status") != "done":
        return
    facts = served_facts(event.get("data"), events)
    with _live_lock:
        if run_id in _live:
            _live[run_id].update(facts)


def _log_exception(where: str) -> None:
    """The current exception on stderr, never on the page. Under REAL_DATA=1 only its type and
    stack: the message can quote a ticket or a model reply."""
    kind, _, tb = sys.exc_info()
    if real_data():
        print(f"{where} failed: {kind.__name__}\n{''.join(traceback.format_tb(tb))}", file=sys.stderr)
    else:
        print(f"{where} failed:", file=sys.stderr)
        traceback.print_exc()


def _internal_error_result(started: float) -> dict:
    """The result event for a run that crashed before it sent one: escalated, with no detail of
    the error (that goes to stderr only)."""
    flags = ["internal_error"]
    try:
        note = handoff.note(None, flags)
    except Exception:  # noqa: BLE001 - the result must go out even without a note
        note = None
    data = {"outcome": "escalated", "flags": flags, "notes_ar": [FLAG_AR.get(f, f) for f in flags]}
    if note:
        data["handoff_ar"] = note
    return {"stage": "result", "status": "done", "data": data, "ms": int((time.time() - started) * 1000)}


def _work(text: str, events: queue.Queue, gone: threading.Event, slot: threading.Lock, run_id: str = "") -> None:
    """Run one live ticket on its own thread. Always ends the stream (None) with a result before
    it, and frees the live slot only when the pipeline has really stopped calling models. What the
    result served goes to the live registry (live_served) before the page can see it."""
    started = time.time()
    sent_result = False
    seen: list[dict] = []   # this run's events, for the draft's hash; dropped when the run ends

    def emit(event: dict) -> None:
        nonlocal sent_result
        sent_result = sent_result or event.get("stage") == "result"
        if isinstance(event, dict):
            live_served(run_id, event, seen)
            seen.append(event)
        events.put(event)

    try:
        process(text, emit, should_stop=gone.is_set)
    except Exception:  # noqa: BLE001 - process() should never raise; if it does, the stream still ends
        _log_exception("live run")
        if not sent_result:
            emit(_internal_error_result(started))
    finally:
        events.put(None)
        slot.release()


class ViewerServer(ThreadingHTTPServer):
    """The viewer's HTTP server: one live run at a time."""

    request_queue_size = 32   # a page opens several connections at once; the default backlog is 5

    def __init__(self, address, handler):
        super().__init__(address, handler)
        self.live_slot = threading.Lock()


_FALLBACK_SLOT = threading.Lock()   # for a plain ThreadingHTTPServer built around Handler


class Handler(BaseHTTPRequestHandler):
    server_version = "PipelineViewer"
    sys_version = ""
    timeout = 60              # a client that stops sending mid-request frees its thread
    _responded = False
    _body_read = False

    def version_string(self) -> str:   # no Python version in the Server header
        return self.server_version

    def log_message(self, fmt, *args):  # no request log: URLs and bodies can carry ticket text
        pass

    def end_headers(self) -> None:
        for name, value in SECURITY_HEADERS.items():
            self.send_header(name, value)
        super().end_headers()

    def send_response(self, code, message=None) -> None:
        self._responded = True
        super().send_response(code, message)

    # --- responses ---

    def _drain(self) -> None:
        """Read an unread request body before refusing it, so the browser gets the refusal rather
        than a reset connection."""
        self._body_read = True
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if 0 < n <= DRAIN_CAP:
                self.rfile.read(n)
        except (OSError, ValueError):
            pass

    def _send(self, body: bytes, ctype: str, status: int = 200, **headers: str) -> None:
        if self.command == "POST" and not self._body_read:
            self._drain()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for name, value in headers.items():
            self.send_header(name.replace("_", "-"), value)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, status: int = 200, **headers: str) -> None:
        self._send(json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8",
                   status, **headers)

    def _error(self, key: str, status: int, **fmt) -> None:
        self._json({"error": ERR_AR[key].format(**fmt)}, status)

    # --- checks every request passes ---

    def _guard(self, path: str) -> bool:
        """Host, Origin and token checks; sends the refusal and returns False if one fails."""
        port = self.server.server_address[1]
        host = (self.headers.get("Host") or "").strip().lower()
        origin = self.headers.get("Origin")
        sent = self.headers.get("X-Viewer-Token") or ""
        if host not in {f"{h}:{port}" for h in LOOPBACK}:
            return self._refuse("host", 421)   # DNS rebinding: a foreign name pointed at 127.0.0.1
        if origin is not None and origin.strip().lower() not in {f"http://{h}:{port}" for h in LOOPBACK}:
            return self._refuse("origin", 403)
        if path.startswith("/api/") and not hmac.compare_digest(sent.encode("utf-8", "replace"),
                                                                TOKEN.encode("utf-8")):
            return self._refuse("token", 403)
        return True

    def _refuse(self, key: str, status: int) -> bool:
        """Refuse a caller that isn't the page, without reading its body (a slow sender would hold the
        thread), and close the connection."""
        self._body_read = True
        self.close_connection = True
        self._json({"error": ERR_AR[key]}, status, Connection="close")
        return False

    def _handle(self, route) -> None:
        url = urlparse(self.path)
        try:
            if self._guard(url.path):
                route(url)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:  # noqa: BLE001 - the detail goes to stderr, never to the page
            _log_exception(f"viewer {self.command}")   # no path: it can carry anything
            if not self._responded:
                self._error("internal", 500)

    def do_GET(self) -> None:  # noqa: N802
        self._handle(self._get)

    def do_POST(self) -> None:  # noqa: N802
        self._handle(self._post)

    # --- routes ---

    def _get(self, url) -> None:
        q = parse_qs(url.query)

        def arg(key: str, default: str = "") -> str:
            return (q.get(key) or [default])[0]

        if url.path in ("/", "/index.html"):
            page = (STATIC / "index.html").read_text(encoding="utf-8")
            page = page.replace("<head>", f'<head>\n<meta name="viewer-token" content="{TOKEN}">', 1)
            return self._send(page.encode("utf-8"), "text/html; charset=utf-8")
        if url.path.startswith("/static/"):   # no token: a <script src> or a font can't send one
            found = static_file(url.path[len("/static/"):])
            return self._error("not_found", 404) if found is None else self._send(found[0].read_bytes(), found[1])
        if url.path == "/api/sets":
            return self._json(ticket_sets())
        if url.path == "/api/tickets":
            return self._json(load_tickets(arg("set", "edge_cases")))
        if url.path == "/api/runs":
            return self._json(list_runs())
        if url.path == "/api/run":
            f = run_file(arg("name"))
            return self._error("no_run", 404) if f is None else self._json(with_current_gold(f))
        if url.path == "/api/meta":
            return self._json(meta())
        if url.path == "/api/prompts":
            return self._json({"classifier": cls.system_prompt(), "drafter": drf.system_prompt()})
        if url.path == "/api/decisions":
            run = arg("run")
            return self._json({"decisions": read_decisions(run)}) if run else self._error("run_param", 400)
        if url.path == "/api/stream":   # a GET must never start a paid run
            return self._json({"error": ERR_AR["method"]}, 405, Allow="POST")
        self._error("not_found", 404)

    def _post(self, url) -> None:
        if url.path == "/api/stream":
            return self._post_stream()
        if url.path == "/api/decision":
            return self._post_decision()
        if url.path == "/api/check":
            return self._post_check()
        self._error("not_found", 404)

    def _read_json(self) -> dict | None:
        """The request's JSON object, or None after sending the refusal (411, 413, 415 or 400)."""
        try:
            n = int(self.headers.get("Content-Length", ""))
        except ValueError:
            n = -1
        if n < 0 or "Transfer-Encoding" in self.headers:
            self._error("length", 411)
            return None
        if n > limits()["max_request_bytes"]:
            self._error("too_big", 413)
            return None
        if self.headers.get_content_type() != "application/json":
            self._error("content_type", 415)
            return None
        raw = self.rfile.read(n)
        self._body_read = True
        try:
            body = json.loads(raw.decode("utf-8"), parse_constant=_no_constant)
        except ValueError:   # includes bad UTF-8 and NaN / Infinity
            body = None
        if not isinstance(body, dict):
            self._error("bad_json", 400)
            return None
        return body

    def _post_stream(self) -> None:
        body = self._read_json()
        if body is None:
            return
        text = body.get("text")
        text = text.strip() if isinstance(text, str) else ""
        if not text:
            return self._error("empty", 400)
        try:
            text.encode("utf-8")       # JSON allows a lone surrogate ("\\ud83d"); it can't be streamed or saved
        except UnicodeEncodeError:
            return self._error("bad_text", 400)
        limit = limits()["max_ticket_chars"]
        if len(text) > limit:
            return self._error("too_long", 413, limit=limit)
        slot = getattr(self.server, "live_slot", _FALLBACK_SLOT)
        if not slot.acquire(blocking=False):
            return self._error("busy", 429)
        events: queue.Queue = queue.Queue()
        gone = threading.Event()
        # The run's id comes first: the page keys the ticket by it, and the decision log checks against it.
        run_id = live_started(text)
        events.put({"live_id": run_id})
        try:
            # Started before the 200 goes out: if no thread can start, the slot is freed and the page
            # gets a plain 500 instead of a stream that never ends.
            threading.Thread(target=_work, args=(text, events, gone, slot, run_id), daemon=True).start()
        except BaseException:
            slot.release()
            raise
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Connection", "close")
            self.end_headers()
        except BaseException:
            gone.set()
            raise
        self._pump(events, gone)

    def _pump(self, events: queue.Queue, gone: threading.Event) -> None:
        """Stream the run's events as they come. If the browser goes away, or the stream fails for any
        reason, tell the pipeline to stop (it checks before each model call) and return; the worker
        frees the live slot when it ends."""
        ended = False
        try:
            while True:
                try:
                    event = events.get(timeout=POLL_S)
                except queue.Empty:
                    if self._client_gone():
                        return
                    continue
                payload = ("event: end\ndata: {}\n\n" if event is None
                           else f"data: {json.dumps(event, ensure_ascii=False, default=str)}\n\n")
                try:
                    self.wfile.write(payload.encode("utf-8", "replace"))
                    self.wfile.flush()
                except OSError:
                    return
                if event is None:
                    ended = True
                    return
        finally:
            if not ended:
                gone.set()

    def _client_gone(self) -> bool:
        """True once the browser has closed the connection. It sends nothing more on an event stream,
        so a readable socket with nothing left to read has at least closed its sending side. A client
        that only half-closed still reads: a keep-alive comment line is written, and only a failed write
        (now, or once the peer's reset arrives) counts as gone. A check that can't tell says "still
        there"; a failed event write ends the stream anyway."""
        try:
            with selectors.DefaultSelector() as sel:   # no FD_SETSIZE limit, unlike select.select
                sel.register(self.connection, selectors.EVENT_READ)
                if not sel.select(0) or self.connection.recv(1, socket.MSG_PEEK) != b"":
                    return False
        except ConnectionError:
            return True
        except (OSError, ValueError):
            return False
        try:
            self.wfile.write(b": ping\n\n")
            self.wfile.flush()
            return False
        except OSError:
            return True

    def _post_check(self) -> None:
        """The draft checks on a draft the agent is editing, the same rules and facts as the pipeline.
        Nothing is logged or kept: the draft can carry the customer's details."""
        body = self._read_json()
        if body is None:
            return
        try:
            draft, allowed, sub = check_request(body)
        except TooLong as e:
            return self._json({"error": ERR_AR["text_too_long"].format(limit=e.limit), "field": e.field}, 413)
        except BadField as e:
            return self._json({"error": ERR_AR["field"].format(field=e), "field": str(e)}, 400)
        self._json({"findings": draft_check.findings(draft, allowed, drf.facts_text(sub))})

    def _post_decision(self) -> None:
        body = self._read_json()
        if body is None:
            return
        try:
            record = decision_record(body)
            append_decision(record)
        except BadField as e:
            return self._json({"error": ERR_AR["field"].format(field=e), "field": str(e)}, 400)
        except Conflict as e:
            return self._json({"error": ERR_AR[e.key].format(why=e.why), "conflict": e.key}, 409)
        self._json({"ok": True, "id": record["id"]})


def _no_constant(name: str):
    raise ValueError(f"{name} is not allowed")


def make_server(port: int = 8000, host: str = "127.0.0.1") -> ViewerServer:
    return ViewerServer((host, port), Handler)


def main() -> None:
    defaulted = default_viewer_backend()   # before anything reads the backend
    try:
        backend()                # an unknown LLM_BACKEND stops here, with one line and no traceback
        assert_real_data_safe()
        mode = pipeline_mode()   # a bad PIPELINE_MODE, budget, limits block or PIPELINE_FIXES stops here,
        budget_usd()             # not on the first ticket or the page's first /api/meta
        limits()
        fixes.active()
    except (BackendError, ValueError) as e:
        print(f"Not starting the viewer: {e}", file=sys.stderr)
        sys.exit(1)
    want = os.getenv("PORT", "8000")
    try:
        server = make_server(int(want))
    except OSError as e:   # most often another program on the port: say so, without a traceback
        print(f"Not starting the viewer: port {want} is not free ({e.strerror}). "
              f"Pick another one, for example: PORT=8001 python app/server.py", file=sys.stderr)
        sys.exit(1)
    port = server.server_address[1]
    live = live_status()
    if not live["available"]:
        live_word = f"live runs off: {LIVE_OFF_EN.get(live.get('cause'), live.get('cause'))}"
    elif backend() == "cli":   # a pasted ticket would run on this computer's Claude Code login
        live_word = "live runs on, through the claude CLI and its login"
    else:
        cap = budget_usd()   # :g keeps a small cap readable ($0.001, not $0.00)
        live_word = (f"live runs on, API spending capped at ${cap:g} for this viewer" if cap
                     else "live runs on, with no spending cap (LLM_BUDGET_USD=0)")
    if live["available"] and cache_only():
        live_word += "; replaying the response cache only (LLM_CACHE_ONLY=1), so no model is called"
    which = f"{backend()}, the viewer's default" if defaulted else f"{backend()}, from LLM_BACKEND"
    print(f"Pipeline viewer on http://localhost:{port}  (backend: {which}; mode: {mode}; Ctrl+C to stop)\n"
          f"  {live_word}. Saved runs replay with no key.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
