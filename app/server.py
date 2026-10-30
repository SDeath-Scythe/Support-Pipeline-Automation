"""Pipeline viewer: watch tickets go through every stage, live.

    python app/server.py            # then open http://localhost:8000
    LLM_BACKEND=api python app/server.py

Standard library only. Streams pipeline events to the browser with Server-Sent Events.
"""

from __future__ import annotations

import json
import os
import queue
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pipeline import classify as cls  # noqa: E402
from pipeline import draft as drf  # noqa: E402
from pipeline.config import models, taxonomy  # noqa: E402
from pipeline.config import thresholds as load_thresholds  # noqa: E402
from pipeline.llm import backend, model_for  # noqa: E402
from pipeline.run import process  # noqa: E402

STATIC = Path(__file__).parent / "static"
PROBES = ROOT / "data" / "probes"
RUNS = ROOT / "runs"


# Dataset splits the viewer may show. heldout and heldout2 stay sealed: their text is not shown here.
SPLITS = ("dev", "mvp_test", "test2")


def ticket_sets() -> list[str]:
    return [s for s in SPLITS if (ROOT / "data" / s / "tickets.jsonl").exists()] + sorted(p.stem for p in PROBES.glob("*.jsonl"))


def load_tickets(name: str) -> list[dict]:
    name = Path(name).name
    path = ROOT / "data" / name / "tickets.jsonl" if name in SPLITS else PROBES / f"{name}.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def list_runs() -> list[dict]:
    """Saved batch runs (runs/*.json) and experiment runs (runs/exp/<set>/<config>.json)."""
    out = []
    files = sorted(RUNS.glob("*.json"), reverse=True) + sorted(RUNS.glob("exp/*/*.json"))
    for f in files:
        try:
            meta = json.loads(f.read_text(encoding="utf-8"))["meta"]
        except (ValueError, KeyError):
            continue
        name = f.relative_to(RUNS).with_suffix("").as_posix()
        if name.startswith("exp/"):   # every split's file is tickets.jsonl: name the run after its folder
            meta = {**meta, "set": f.parent.name}
        out.append({"name": name, "experiment": name.startswith("exp/"), **meta})
    return out


def with_current_gold(f: Path) -> dict:
    """A saved run with each ticket's gold label taken from its set file as it is now, so a label
    corrected after the run (e.g. the author's t2-0033) is scored the same way as in the reports."""
    run = json.loads(f.read_text(encoding="utf-8"))
    if f.parent.parent == RUNS / "exp":
        name = f.parent.name
        run["meta"] = {**run.get("meta", {}), "set": name}
        src = ROOT / "data" / name / "tickets.jsonl" if (ROOT / "data" / name).is_dir() else PROBES / f"{name}.jsonl"
        if src.exists():
            gold = {d["id"]: d for d in map(json.loads, src.read_text(encoding="utf-8").splitlines()) if d}
            run["tickets"] = [{**row, "ticket": gold[row["ticket"]["id"]]} for row in run["tickets"]
                              if row["ticket"].get("id") in gold]
    return run


def run_file(name: str) -> Path | None:
    """The run file for a name from list_runs(), refusing anything outside runs/ or in the cache."""
    f = (RUNS / f"{name}.json").resolve()
    runs = RUNS.resolve()
    if runs not in f.parents or (runs / "cache") in f.parents or not f.is_file():
        return None
    return f


def meta() -> dict:
    tax = taxonomy()
    return {
        "backend": backend(),
        "models": {role: model_for(role) for role in models()},
        "thresholds": load_thresholds()["confidence"],
        "subcategories": {k: {"label": s.label_ar, "category": s.category,
                              "category_label": tax.categories_ar[s.category]} for k, s in tax.subcategories.items()},
        "teams": tax.teams,
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # keep the terminal quiet
        pass

    def _send(self, body: bytes, ctype: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, status: int = 200) -> None:
        self._send(json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8", status)

    def do_GET(self) -> None:  # noqa: N802
        url = urlparse(self.path)
        q = parse_qs(url.query)
        if url.path in ("/", "/index.html"):
            return self._send((STATIC / "index.html").read_bytes(), "text/html; charset=utf-8")
        if url.path == "/api/sets":
            return self._json(ticket_sets())
        if url.path == "/api/tickets":
            return self._json(load_tickets((q.get("set") or ["edge_cases"])[0]))
        if url.path == "/api/runs":
            return self._json(list_runs())
        if url.path == "/api/run":
            f = run_file((q.get("name") or [""])[0])
            if f is None:
                return self._json({"error": "No such run"}, 404)
            return self._json(with_current_gold(f))
        if url.path == "/api/meta":
            return self._json(meta())
        if url.path == "/api/prompts":
            return self._json({"classifier": cls.system_prompt(), "drafter": drf.system_prompt()})
        if url.path == "/api/stream":
            text = (q.get("text") or [""])[0].strip()
            if not text:
                return self._json({"error": "Send a ticket as ?text=..."}, 400)
            return self._stream(text)
        self._json({"error": "Not found"}, 404)

    def _stream(self, text: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()

        events: queue.Queue = queue.Queue()
        worker = threading.Thread(target=lambda: (process(text, events.put), events.put(None)), daemon=True)
        worker.start()
        while True:
            event = events.get()
            if event is None:
                payload = "event: end\ndata: {}\n\n"
            else:
                payload = f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            try:
                self.wfile.write(payload.encode("utf-8"))
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                return  # browser closed the page; the worker finishes on its own
            if event is None:
                return


def main() -> None:
    port = int(os.getenv("PORT", "8000"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Pipeline viewer on http://localhost:{port}  (backend: {backend()}, Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
