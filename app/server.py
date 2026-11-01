"""Pipeline viewer: watch tickets go through every stage, live, and record what the agent decides.

    python app/server.py            # then open http://localhost:8000
    LLM_BACKEND=api python app/server.py

Standard library only. Streams pipeline events to the browser with Server-Sent Events.

Local only, by design. It binds 127.0.0.1 and answers only requests whose Host (and Origin, when
sent) is this machine, so another web page, or a DNS name re-pointed at 127.0.0.1, cannot drive it.
Every /api/ call must carry the token the page is served with. A live run spends money, so it is a
POST, one at a time, and stops calling models once the browser goes away. No request is logged:
URLs and bodies can carry ticket text.
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
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pipeline import classify as cls  # noqa: E402
from pipeline import draft as drf  # noqa: E402
from pipeline import handoff  # noqa: E402
from pipeline.config import limits, models, pipeline_mode, taxonomy  # noqa: E402
from pipeline.config import thresholds as load_thresholds  # noqa: E402
from pipeline.llm import (BackendError, api_key, assert_real_data_safe, backend, budget_usd, model_for,  # noqa: E402
                          real_data)
from pipeline.run import FLAG_AR, process  # noqa: E402

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

SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; "
        "frame-ancestors 'none'; form-action 'none'"),
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
    "busy": "فيه تذكرة تنعالج هسه، انتظر تخلص",
    "field": "قيمة غلط بالحقل: {field}",
    "run_param": "حدد التشغيل (run)",
    "internal": "صار خطأ داخلي، جرب مرة ثانية",
}

# The agent's decision on a ticket (POST /api/decision), and why a draft needed changing.
DECISION_ACTIONS = ("approved", "edited", "took_over", "forwarded", "undone")
DECISION_ACTIONS_AR = {"approved": "اعتمد الرد", "edited": "عدّل الرد واعتمده", "took_over": "استلمها بنفسه",
                       "forwarded": "حوّلها لقسم ثاني", "undone": "تراجع عن القرار"}
REASON_CODES = ("wrong_type", "wrong_team", "wrong_priority", "tone", "asks_unneeded", "promise",
                "wrong_number", "missing_question", "shop_or_agent_name", "other")
REASON_CODES_AR = {"wrong_type": "نوع المشكلة غلط", "wrong_team": "القسم غلط", "wrong_priority": "الأولوية غلط",
                   "tone": "الأسلوب ما يناسب", "asks_unneeded": "يطلب شي ما نحتاجه",
                   "promise": "يوعد بشي ما نكدر نضمنه", "wrong_number": "بيه رقم غلط",
                   "missing_question": "ناقصه سؤال للزبون", "shop_or_agent_name": "ما سأل عن اسم المحل أو الوكيل",
                   "other": "شي ثاني"}
OUTCOMES = ("drafted", "flagged", "escalated")
PRIORITIES = ("P1", "P2", "P3")
DECISION_FIELDS = {"run", "ticket_id", "action", "pipeline_outcome", "flags", "reason_codes", "seconds",
                   "draft_text", "final_text", "corrected", "undoes"}
_TICKET_ID = re.compile(r"[A-Za-z0-9_.:-]{1,64}")
_FLAG = re.compile(r"[A-Za-z0-9_.:-]{1,64}")
_DECISION_ID = re.compile(r"[0-9a-f]{32}")

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
    summary = {"meta": data["meta"], "sealed_ids": _has_sealed_ids(data["tickets"])} if ok else None
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
        out.append(({**meta, "name": name, "experiment": by_folder}, f))
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


def with_current_gold(f: Path) -> dict:
    """A saved run with each ticket's gold label taken from its set file as it is now, so a label
    corrected after the run (e.g. the author's t2-0033) is scored the same way as in the reports.
    A sealed set's file is never read."""
    run = json.loads(f.read_text(encoding="utf-8"))
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

def live_status() -> dict:
    """Whether the page can run a new ticket, and if not, why (in Arabic, for the page)."""
    if pipeline_mode() == "off":
        return {"available": False, "reason_ar": "النظام موقف (PIPELINE_MODE=off): التذاكر الجديدة يستلمها موظف يدوياً"}
    try:
        name = backend()
    except BackendError:
        return {"available": False, "reason_ar": "إعداد LLM_BACKEND غلط: التشغيل المباشر موقف"}
    if name == "api" and not api_key():
        return {"available": False, "reason_ar": "ماكو مفتاح API: تكدر تشوف التشغيلات المحفوظة بس"}
    if name == "cli" and not shutil.which(os.getenv("CLAUDE_BIN") or "claude"):
        return {"available": False, "reason_ar": "أداة claude مو موجودة على هذا الجهاز: تكدر تشوف التشغيلات المحفوظة بس"}
    return {"available": True, "reason_ar": None}


def meta() -> dict:
    tax = taxonomy()
    return {
        "backend": backend(),
        "models": {role: model_for(role) for role in models()},
        "thresholds": load_thresholds()["confidence"],
        "subcategories": {k: {"label": s.label_ar, "category": s.category,
                              "category_label": tax.categories_ar[s.category]} for k, s in tax.subcategories.items()},
        "teams": tax.teams,
        "live": live_status(),
        "limits": limits(),
        "mode": pipeline_mode(),
        "real_data": real_data(),
        "flag_ar": FLAG_AR,
        "decision_actions": list(DECISION_ACTIONS),
        "decision_actions_ar": DECISION_ACTIONS_AR,
        "reason_codes": list(REASON_CODES),
        "reason_codes_ar": REASON_CODES_AR,
    }


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


def decision_record(body: dict) -> dict:
    """The log line for one decision. It keeps keyed hashes (HMAC-SHA256, see _HASH_KEY) of the draft
    and the final reply, and how many characters changed, but never the text itself: the log is for
    measuring the pipeline, and a reply can carry a customer's details."""
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
    draft, final = _text_field(body, "draft_text"), _text_field(body, "final_text")
    return {
        "id": uuid.uuid4().hex,
        "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "reviewer": reviewer(),
        "run": run, "ticket_id": ticket_id, "action": action, "pipeline_outcome": outcome,
        "flags": flags, "reason_codes": list(dict.fromkeys(codes)), "seconds": seconds,
        "corrected": _corrected(body.get("corrected")), "undoes": undoes,
        "models": {role: model_for(role) for role in models()},
        "prompt_sha256": {"classifier": _sha256(cls.system_prompt()), "drafter": _sha256(drf.system_prompt())},
        "draft_sha256": _sha256(draft),
        "final_sha256": _sha256(final),
        "edit_chars": edit_chars(draft, final),
    }


def append_decision(record: dict) -> None:
    """One line, one write: concurrent decisions never interleave. A new log is readable by its owner
    only (0600)."""
    line = json.dumps(record, ensure_ascii=False) + "\n"
    path = decisions_file()
    with _decisions_lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        with open(fd, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()


def read_decisions(run: str) -> list[dict]:
    """The decisions logged for one run, oldest first. A line that isn't JSON is skipped."""
    with _decisions_lock:
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


def _work(text: str, events: queue.Queue, gone: threading.Event, slot: threading.Lock) -> None:
    """Run one live ticket on its own thread. Always ends the stream (None) with a result before
    it, and frees the live slot only when the pipeline has really stopped calling models."""
    started = time.time()
    sent_result = False

    def emit(event: dict) -> None:
        nonlocal sent_result
        sent_result = sent_result or event.get("stage") == "result"
        events.put(event)

    try:
        process(text, emit, should_stop=gone.is_set)
    except Exception:  # noqa: BLE001 - process() should never raise; if it does, the stream still ends
        _log_exception("live run")
        if not sent_result:
            events.put(_internal_error_result(started))
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
        try:
            # Started before the 200 goes out: if no thread can start, the slot is freed and the page
            # gets a plain 500 instead of a stream that never ends.
            threading.Thread(target=_work, args=(text, events, gone, slot), daemon=True).start()
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

    def _post_decision(self) -> None:
        body = self._read_json()
        if body is None:
            return
        try:
            record = decision_record(body)
        except BadField as e:
            return self._json({"error": ERR_AR["field"].format(field=e), "field": str(e)}, 400)
        append_decision(record)
        self._json({"ok": True, "id": record["id"]})


def _no_constant(name: str):
    raise ValueError(f"{name} is not allowed")


def make_server(port: int = 8000, host: str = "127.0.0.1") -> ViewerServer:
    return ViewerServer((host, port), Handler)


def main() -> None:
    try:
        assert_real_data_safe()
        mode = pipeline_mode()   # a bad PIPELINE_MODE, budget or limits block stops here, not on the first ticket
        budget_usd()
        limits()
    except (BackendError, ValueError) as e:
        print(f"Not starting the viewer: {e}", file=sys.stderr)
        sys.exit(1)
    server = make_server(int(os.getenv("PORT", "8000")))
    port = server.server_address[1]
    print(f"Pipeline viewer on http://localhost:{port}  (backend: {backend()}, mode: {mode}, Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
