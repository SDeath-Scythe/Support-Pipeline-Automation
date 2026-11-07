"""The viewer's HTTP surface (app/server.py): who may call it, what it accepts, what it never shows.

Every test runs a real server on a free port with the pipeline replaced by a stub: no model is called.
"""

import hashlib
import hmac
import http.client
import importlib.util
import json
import os
import random
import re
import socket
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location("viewer_server", ROOT / "app" / "server.py")
server = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(server)

CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; font-src 'self'; img-src 'self' data:; "
       "connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")


def _event(stage, data=None, status="done"):
    return {"stage": stage, "status": status, "data": data or {}, "ms": 0}


def stub_process(text, emit=lambda e: None, should_stop=None):
    """Stands in for pipeline.run.process: a few events, no model call."""
    emit(_event("received", {"chars": len(text)}))
    emit(_event("classify", {"model": "stub"}, "running"))
    result = {"outcome": "drafted", "flags": [], "draft_ar": "رد تجريبي"}
    emit(_event("result", result))
    return result


@pytest.fixture(autouse=True)
def no_model_calls(monkeypatch):
    """Belt and braces: any model call in these tests fails loudly instead of reaching a model."""
    from pipeline import llm

    def refuse(*a, **k):
        raise AssertionError("a model was called")

    for name in ("_call_api", "_call_cli", "_call_openai"):
        monkeypatch.setattr(llm, name, refuse)


@pytest.fixture
def srv(monkeypatch, tmp_path):
    monkeypatch.setenv("DECISIONS_FILE", str(tmp_path / "decisions.jsonl"))
    monkeypatch.setenv("REVIEWER", "agent-1")
    monkeypatch.setattr(server, "process", stub_process)
    httpd = server.make_server(port=0)
    threading.Thread(target=httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
    yield httpd
    httpd.shutdown()
    httpd.server_close()


def call(httpd, method, path, body=None, *, token=True, headers=None, raw=None):
    """One request; returns (status, headers, body bytes)."""
    conn = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=10)
    h = {"X-Viewer-Token": server.TOKEN} if token else {}
    if body is not None:
        raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
        h["Content-Type"] = "application/json"
    h.update(headers or {})
    conn.request(method, path, body=raw, headers=h)
    resp = conn.getresponse()
    out = resp.status, resp.headers, resp.read()
    conn.close()
    return out


def sse(body: bytes) -> tuple[list[dict], bool]:
    """The data events of an event stream, and whether it closed with 'event: end'."""
    blocks = body.decode("utf-8").split("\n\n")
    events = [json.loads(b[len("data: "):]) for b in blocks if b.startswith("data: ")]
    return events, any(b.startswith("event: end") for b in blocks)


def wait_until(cond, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if cond():
            return True
        time.sleep(0.02)
    return False


# --- who may call ---

def test_wrong_host_is_refused_421(srv):
    port = srv.server_address[1]
    for host in ("evil.example", f"evil.example:{port}", f"localhost:{port + 1}", "localhost"):
        status, _, body = call(srv, "GET", "/api/meta", headers={"Host": host})
        assert status == 421, host
        assert "localhost" in json.loads(body)["error"]
    status, _, body = call(srv, "GET", "/", headers={"Host": "rebound.example"})
    assert status == 421 and server.TOKEN.encode() not in body   # a rebinding page never sees the token
    for host in (f"localhost:{port}", f"127.0.0.1:{port}", f"[::1]:{port}", f"LOCALHOST:{port}"):
        assert call(srv, "GET", "/api/meta", headers={"Host": host})[0] == 200, host


def test_foreign_origin_is_refused_403(srv):
    port = srv.server_address[1]
    for origin in ("http://evil.example", "null", f"http://localhost:{port + 1}", f"https://localhost:{port}"):
        status, _, body = call(srv, "GET", "/api/meta", headers={"Origin": origin})
        assert status == 403, origin
        assert json.loads(body)["error"]
    for origin in (f"http://localhost:{port}", f"http://127.0.0.1:{port}", f"http://[::1]:{port}"):
        assert call(srv, "GET", "/api/meta", headers={"Origin": origin})[0] == 200, origin


def test_api_needs_the_page_token(srv, monkeypatch):
    calls = []
    monkeypatch.setattr(server, "process", lambda *a, **k: calls.append(a))
    for path in ("/api/meta", "/api/sets", "/api/runs", "/api/prompts", "/api/tickets?set=edge_cases",
                 "/api/decisions?run=live"):
        status, _, body = call(srv, "GET", path, token=False)
        assert status == 403, path
        assert any("؀" <= ch <= "ۿ" for ch in json.loads(body)["error"])   # Arabic, for the page
        assert call(srv, "GET", path, token=False, headers={"X-Viewer-Token": server.TOKEN[:-1] + "x"})[0] == 403
        assert call(srv, "GET", path)[0] == 200, path
    status, _, _ = call(srv, "POST", "/api/stream", {"text": "التحويل ما وصل"}, token=False)
    assert status == 403 and calls == []


def test_page_carries_the_token_right_after_head(srv):
    status, headers, body = call(srv, "GET", "/", token=False)
    assert status == 200 and headers["Content-Type"].startswith("text/html")
    assert f'<head>\n<meta name="viewer-token" content="{server.TOKEN}">' in body.decode("utf-8")
    assert call(srv, "GET", "/index.html", token=False)[0] == 200


def test_get_stream_never_starts_a_run_405(srv, monkeypatch):
    calls = []
    monkeypatch.setattr(server, "process", lambda *a, **k: calls.append(a))
    status, headers, _ = call(srv, "GET", "/api/stream?text=%D8%AA%D8%AD%D9%88%D9%8A%D9%84")
    assert status == 405 and headers["Allow"] == "POST"
    assert calls == []


# --- what a live run accepts ---

def test_live_run_streams_events_then_end(srv, monkeypatch):
    seen = {}

    def spy(text, emit=lambda e: None, should_stop=None):
        seen.update(text=text, should_stop=should_stop)
        return stub_process(text, emit, should_stop)

    monkeypatch.setattr(server, "process", spy)
    status, headers, body = call(srv, "POST", "/api/stream", {"text": "  حولت فلوس وما وصلت  "})
    assert status == 200 and headers["Content-Type"].startswith("text/event-stream")
    events, ended = sse(body)
    # The server's id for the run comes first: live-<UTC yyyymmddHHMMSS>-<6 hex>.
    assert re.fullmatch(r"live-\d{14}-[0-9a-f]{6}", events[0]["live_id"]) and set(events[0]) == {"live_id"}
    assert [e["stage"] for e in events[1:]] == ["received", "classify", "result"] and ended
    assert seen["text"] == "حولت فلوس وما وصلت" and callable(seen["should_stop"]) and seen["should_stop"]() is False


def test_oversize_body_is_refused_413(srv, monkeypatch):
    calls = []
    monkeypatch.setattr(server, "process", lambda *a, **k: calls.append(a))
    big = server.limits()["max_request_bytes"] + 1
    raw = json.dumps({"text": "x" * big}).encode()
    status, _, body = call(srv, "POST", "/api/stream", raw=raw, headers={"Content-Type": "application/json"})
    assert status == 413 and json.loads(body)["error"]
    assert calls == []


def test_ticket_over_the_char_limit_is_refused_413(srv):
    limit = server.limits()["max_ticket_chars"]
    status, _, body = call(srv, "POST", "/api/stream", {"text": "ح" * (limit + 1)})
    assert status == 413
    assert str(limit) in json.loads(body)["error"]
    assert call(srv, "POST", "/api/stream", {"text": "ح" * limit})[0] == 200


def test_bad_stream_requests_are_refused(srv):
    assert call(srv, "POST", "/api/stream", {"text": "   "})[0] == 400
    assert call(srv, "POST", "/api/stream", {"text": 5})[0] == 400
    assert call(srv, "POST", "/api/stream", {})[0] == 400
    assert call(srv, "POST", "/api/stream", raw=b"[1, 2]", headers={"Content-Type": "application/json"})[0] == 400
    assert call(srv, "POST", "/api/stream", raw=b"{not json", headers={"Content-Type": "application/json"})[0] == 400
    assert call(srv, "POST", "/api/stream", raw=b'{"text": NaN}', headers={"Content-Type": "application/json"})[0] == 400
    # A plain HTML form can only send these types: refused before anything runs.
    assert call(srv, "POST", "/api/stream", raw=b'{"text": "a"}', headers={"Content-Type": "text/plain"})[0] == 415
    assert call(srv, "POST", "/api/nothing", {"text": "a"})[0] == 404


def test_a_lone_surrogate_is_refused_400(srv, monkeypatch):
    """JSON allows "\\ud83d"; the stream used to die on the first event, with no end and no cancel."""
    calls = []
    monkeypatch.setattr(server, "process", lambda *a, **k: calls.append(a))
    status, _, body = call(srv, "POST", "/api/stream", raw=b'{"text": "\\ud83d \\u0627\\u0644\\u0631\\u0645\\u0632"}',
                           headers={"Content-Type": "application/json"})
    assert status == 400 and json.loads(body)["error"] and calls == []


def _watching(seen):
    """A run that sends one event, then waits up to 1.5 s for should_stop before its result."""
    def run(text, emit=lambda e: None, should_stop=None):
        emit(_event("received"))
        seen["stopped"] = wait_until(should_stop, timeout=1.5)
        emit(_event("result", {"outcome": "drafted", "flags": []}))
    return run


def test_a_stream_that_fails_for_any_reason_stops_the_run(srv, monkeypatch):
    seen = {}

    def run(text, emit=lambda e: None, should_stop=None):
        loop = {}
        loop["self"] = loop
        emit(_event("received", loop))                     # can't be serialised: not an OSError
        seen["stopped"] = wait_until(should_stop, timeout=5)

    monkeypatch.setattr(server, "process", run)
    call(srv, "POST", "/api/stream", {"text": "تذكرة"})
    assert wait_until(lambda: "stopped" in seen, timeout=8) and seen["stopped"] is True


def test_a_worker_that_cannot_start_frees_the_live_slot(srv, monkeypatch):
    real, failed = threading.Thread, []

    class FirstWorkerFails(real):
        def start(self):
            if getattr(self, "_target", None) is server._work and not failed:
                failed.append(1)
                raise RuntimeError("can't start new thread")
            super().start()

    monkeypatch.setattr(threading, "Thread", FirstWorkerFails)
    status, _, body = call(srv, "POST", "/api/stream", {"text": "تذكرة"})
    assert failed and status == 500 and json.loads(body)["error"]      # not a 200 stream that never ends
    status, _, body = call(srv, "POST", "/api/stream", {"text": "تذكرة"})
    assert status == 200 and sse(body)[1]                               # the slot was freed


def test_a_half_closed_client_still_gets_its_result(srv, monkeypatch):
    """shutdown(SHUT_WR) after the request is not a hang-up: the client still reads."""
    seen = {}
    monkeypatch.setattr(server, "process", _watching(seen))
    sock = socket.create_connection(("127.0.0.1", srv.server_address[1]), timeout=10)
    body = json.dumps({"text": "تذكرة"}).encode()
    sock.sendall(b"POST /api/stream HTTP/1.1\r\nHost: 127.0.0.1:%d\r\nContent-Type: application/json\r\n"
                 b"X-Viewer-Token: %s\r\nContent-Length: %d\r\n\r\n%s"
                 % (srv.server_address[1], server.TOKEN.encode(), len(body), body))
    sock.shutdown(socket.SHUT_WR)
    got = b""
    while chunk := sock.recv(65536):
        got += chunk
    sock.close()
    events, ended = sse(got.split(b"\r\n\r\n", 1)[1])
    assert seen["stopped"] is False and ended and events[-1]["stage"] == "result"


def test_a_socket_above_fd_1024_is_not_taken_for_a_hang_up(srv, monkeypatch):
    """select.select() raises for a descriptor >= 1024, which was read as "the browser left"."""
    import resource

    soft, _ = resource.getrlimit(resource.RLIMIT_NOFILE)
    if soft < 1300:
        pytest.skip("needs more than 1,300 open files")
    held = [os.open(os.devnull, os.O_RDONLY) for _ in range(1100)]
    try:
        seen = {}
        monkeypatch.setattr(server, "process", _watching(seen))
        status, _, body = call(srv, "POST", "/api/stream", {"text": "تذكرة"})
        assert status == 200 and sse(body)[1] and seen["stopped"] is False
    finally:
        for fd in held:
            os.close(fd)


def test_a_foreign_caller_is_refused_without_reading_its_body(srv):
    """A refusal used to read up to 1 MB first: a slow sender held the thread."""
    sock = socket.create_connection(("127.0.0.1", srv.server_address[1]), timeout=3)
    sock.sendall(b"POST /api/stream HTTP/1.1\r\nHost: evil.example\r\nContent-Type: application/json\r\n"
                 b"Content-Length: 1000000\r\n\r\n{")
    head = sock.recv(4096)
    sock.close()
    assert head.startswith(b"HTTP/1.0 421") or head.startswith(b"HTTP/1.1 421")
    assert b"Connection: close" in head


def test_only_one_live_run_at_a_time_429(srv, monkeypatch):
    started, release = threading.Event(), threading.Event()

    def slow(text, emit=lambda e: None, should_stop=None):
        emit(_event("received"))
        started.set()
        release.wait(10)
        emit(_event("result", {"outcome": "drafted", "flags": []}))

    monkeypatch.setattr(server, "process", slow)
    first = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=10)
    first.request("POST", "/api/stream", body=json.dumps({"text": "الأولى"}).encode(),
                  headers={"Content-Type": "application/json", "X-Viewer-Token": server.TOKEN})
    resp = first.getresponse()
    assert resp.status == 200 and started.wait(5)

    status, _, body = call(srv, "POST", "/api/stream", {"text": "الثانية"})
    assert status == 429 and json.loads(body)["error"] == "اكو تذكرة دتنعالج هسه، انتظر لما تخلص"

    release.set()
    events, ended = sse(resp.read())
    first.close()
    assert events[-1]["stage"] == "result" and ended
    assert wait_until(lambda: call(srv, "POST", "/api/stream", {"text": "الثالثة"})[0] == 200)


def test_a_crashing_pipeline_still_ends_the_stream(srv, monkeypatch, capsys):
    def boom(text, emit=lambda e: None, should_stop=None):
        emit(_event("received"))
        raise RuntimeError("secret detail 07701234567 /home/user/path")

    monkeypatch.setattr(server, "process", boom)
    status, _, body = call(srv, "POST", "/api/stream", {"text": "تذكرة"})
    events, ended = sse(body)
    assert status == 200 and ended
    result = events[-1]
    assert result["stage"] == "result" and result["data"]["outcome"] == "escalated"
    assert result["data"]["flags"] == ["internal_error"]
    assert b"secret detail" not in body and b"07701234567" not in body and b"RuntimeError" not in body
    assert "secret detail" in capsys.readouterr().err   # the traceback goes to stderr only
    # The live slot was freed.
    monkeypatch.setattr(server, "process", stub_process)
    assert call(srv, "POST", "/api/stream", {"text": "تذكرة"})[0] == 200


def test_crash_log_under_real_data_has_no_message(srv, monkeypatch, capsys):
    monkeypatch.setenv("REAL_DATA", "1")
    card = "4111" * 4   # built, so the traceback's quoted source line doesn't contain it

    def boom(text, emit=lambda e: None, should_stop=None):
        raise ValueError("customer said " + card)

    monkeypatch.setattr(server, "process", boom)
    status, _, body = call(srv, "POST", "/api/stream", {"text": "تذكرة"})
    assert status == 200 and sse(body)[1]
    err = capsys.readouterr().err
    assert "ValueError" in err and card not in err


def test_closing_the_page_stops_the_run(srv, monkeypatch):
    started, stopped = threading.Event(), threading.Event()

    def long_run(text, emit=lambda e: None, should_stop=None):
        emit(_event("received"))
        started.set()
        if wait_until(should_stop, timeout=10):
            stopped.set()
        emit(_event("result", {"outcome": "escalated", "flags": ["cancelled"]}))

    monkeypatch.setattr(server, "process", long_run)
    sock = socket.create_connection(("127.0.0.1", srv.server_address[1]), timeout=10)
    body = json.dumps({"text": "تذكرة"}).encode()
    sock.sendall(b"POST /api/stream HTTP/1.1\r\nHost: 127.0.0.1:%d\r\nContent-Type: application/json\r\n"
                 b"X-Viewer-Token: %s\r\nContent-Length: %d\r\n\r\n%s"
                 % (srv.server_address[1], server.TOKEN.encode(), len(body), body))
    assert b"200" in sock.recv(4096).split(b"\r\n", 1)[0]
    assert started.wait(5)
    sock.close()
    assert stopped.wait(5), "should_stop never turned True after the browser went away"
    monkeypatch.setattr(server, "process", stub_process)
    assert wait_until(lambda: call(srv, "POST", "/api/stream", {"text": "تذكرة"})[0] == 200)


# --- what it never shows ---

def _run(set_name="tickets", ids=("t2-0001",)):
    return {"meta": {"set": set_name, "backend": "api", "started": "2026-11-01T10:00:00"},
            "tickets": [{"ticket": {"id": i, "text": "نص"}, "events": [], "result": {"outcome": "drafted"}}
                        for i in ids]}


@pytest.fixture
def fake_runs(monkeypatch, tmp_path):
    """A runs/ and docs/runs/ tree with sealed, non-run and normal files."""
    runs, saved, data = tmp_path / "runs", tmp_path / "docs" / "runs", tmp_path / "data"
    files = {
        runs / "exp" / "dev" / "rec.json": _run(ids=("dev-0001",)),
        runs / "exp" / "heldout" / "mvp.json": _run(ids=("hold-0001",)),
        runs / "exp" / "heldout2" / "mvp.json": _run(ids=("h2-0001",)),
        runs / "exp" / "HeldOut_x" / "mvp.json": _run(ids=("dev-0002",)),
        runs / "20261101-100000-tickets-api.json": _run(ids=("h2-0001", "h2-0002")),   # a batch run of heldout2
        runs / "20261101-110000-tickets-api.json": _run(ids=("t2-0001",)),
        runs / "20261101-120000-heldout2-api.json": _run(set_name="heldout2", ids=("x-1",)),
        runs / "judge_x.json": {"recF16": {"dev-0001": 0.9}},
        runs / "meta_only.json": {"meta": {"set": "dev"}},
        runs / "generation" / "heldout2-s1" / "batch.json": _run(ids=("h2-0003",)),
        runs / "cache" / "abc.json": _run(),
        saved / "test2" / "final.json": _run(ids=("t2-0001",)),
        saved / "heldout2" / "final.json": _run(ids=("h2-0001",)),
    }
    for f, obj in files.items():
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    (runs / "broken.json").write_text("{not json", encoding="utf-8")
    for split, tid in (("dev", "dev-0001"), ("heldout", "hold-0001"), ("heldout2", "h2-0001")):
        (data / split).mkdir(parents=True)
        (data / split / "tickets.jsonl").write_text(json.dumps({"id": tid, "text": "gold", "subcategory": "x"}) + "\n",
                                                   encoding="utf-8")
    monkeypatch.setattr(server, "ROOT", tmp_path)
    monkeypatch.setattr(server, "RUNS", runs)
    monkeypatch.setattr(server, "SAVED", saved)
    monkeypatch.setattr(server, "PROBES", data / "probes")
    return tmp_path


def test_sealed_and_non_run_files_are_never_listed_or_served(srv, fake_runs):
    names = {r["name"] for r in server.list_runs()}
    assert names == {"saved/test2/final", "20261101-110000-tickets-api", "exp/dev/rec"}
    status, _, body = call(srv, "GET", "/api/runs")
    assert status == 200 and {r["name"] for r in json.loads(body)} == names
    for name in ("exp/heldout/mvp", "exp/heldout2/mvp", "exp/HeldOut_x/mvp", "20261101-100000-tickets-api",
                 "20261101-120000-heldout2-api", "judge_x", "meta_only", "broken", "generation/heldout2-s1/batch",
                 "cache/abc", "saved/heldout2/final"):
        assert server.run_file(name) is None, name
        assert call(srv, "GET", f"/api/run?name={name}")[0] == 404, name
    status, _, body = call(srv, "GET", "/api/run?name=exp/dev/rec")
    assert status == 200 and json.loads(body)["tickets"][0]["ticket"]["text"] == "gold"


def test_gold_labels_are_never_read_from_a_sealed_set(fake_runs, monkeypatch):
    opened = []
    real = Path.read_text
    monkeypatch.setattr(Path, "read_text", lambda self, *a, **k: (opened.append(self), real(self, *a, **k))[1])
    run = server.with_current_gold(fake_runs / "runs" / "exp" / "heldout" / "mvp.json")
    assert run["tickets"][0]["ticket"]["text"] == "نص"   # left as saved, not joined with the sealed file
    assert not any("data" in p.parts and p.parent.name.startswith("heldout") for p in opened)
    assert server._gold_file("heldout") is None and server._gold_file("heldout2") is None


def test_malformed_run_names_are_404(srv, fake_runs):
    for name in ("../../etc/passwd", "saved/../../../etc/passwd", "exp/dev/../../cache/abc", "exp%2Fdev%2F..%2Frec",
                 "a%00b", "exp/dev/rec%00", "x" * 5000, "/etc/passwd", "", "saved/", "exp/dev/rec.json"):
        assert call(srv, "GET", f"/api/run?name={name}")[0] == 404, name[:40]
    assert server.run_file("a\x00b") is None and server.run_file("x" * 100_000) is None


def test_real_repo_never_lists_a_sealed_run():
    assert not any("heldout" in r["name"].lower() or str(r.get("set", "")).lower().startswith("heldout")
                   for r in server.list_runs())


def test_unlisted_ticket_sets_are_empty():
    assert server.load_tickets("heldout") == [] and server.load_tickets("heldout2") == []
    assert server.load_tickets("../heldout/tickets") == [] and server.load_tickets("a\x00b") == []
    assert server.load_tickets("x" * 5000) == []


# --- every response ---

def test_security_headers_on_every_response(srv):
    port = srv.server_address[1]
    responses = [call(srv, "GET", "/"), call(srv, "GET", "/api/meta"), call(srv, "GET", "/nope"),
                 call(srv, "GET", "/api/meta", token=False), call(srv, "GET", "/", headers={"Host": "x.example"}),
                 call(srv, "GET", "/api/stream"), call(srv, "PUT", "/api/stream"),
                 call(srv, "POST", "/api/stream", {"text": "تذكرة"}),
                 call(srv, "GET", "/api/meta", headers={"Origin": f"http://evil:{port}"})]
    assert {r[0] for r in responses} == {200, 404, 403, 421, 405, 501}
    for status, headers, _ in responses:
        assert headers["Content-Security-Policy"] == CSP, status
        assert headers["X-Frame-Options"] == "DENY"
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["Referrer-Policy"] == "no-referrer"
        assert headers["Cross-Origin-Opener-Policy"] == "same-origin"
        assert headers["Cache-Control"] == "no-store"
        assert "python" not in headers["Server"].lower()


def test_meta_says_whether_live_runs_are_possible(srv, monkeypatch):
    for var in ("ANTHROPIC_API_KEY", "SUPPORT_PIPELINE_API_KEY", "PIPELINE_MODE", "REAL_DATA", "LLM_PROFILE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("LLM_BACKEND", "api")
    meta = json.loads(call(srv, "GET", "/api/meta")[2])
    for key in ("backend", "models", "thresholds", "subcategories", "teams", "live", "limits", "mode",
                "real_data", "flag_ar", "decision_actions", "reason_codes"):
        assert key in meta, key
    assert meta["live"]["available"] is False and meta["live"]["reason_ar"]
    assert meta["limits"] == server.limits() and meta["mode"] == "full" and meta["real_data"] is False
    assert meta["decision_actions"] == ["approved", "edited", "took_over", "forwarded", "undone"]
    assert "other" in meta["reason_codes"] and meta["flag_ar"]["fraud"]

    monkeypatch.setenv("SUPPORT_PIPELINE_API_KEY", "not-a-real-key")
    assert json.loads(call(srv, "GET", "/api/meta")[2])["live"] == {"available": True, "reason_ar": None}
    monkeypatch.setenv("PIPELINE_MODE", "off")
    live = json.loads(call(srv, "GET", "/api/meta")[2])["live"]
    assert live["available"] is False and live["cause"] == "pipeline_off" and "موقف" in live["reason_ar"]

    monkeypatch.setenv("PIPELINE_MODE", "full")
    monkeypatch.setenv("LLM_BACKEND", "cli")
    monkeypatch.setenv("CLAUDE_BIN", "/nonexistent/claude")
    assert json.loads(call(srv, "GET", "/api/meta")[2])["live"]["available"] is False


def test_main_refuses_unsafe_real_data_setup(monkeypatch, capsys):
    monkeypatch.setenv("REAL_DATA", "1")
    monkeypatch.setenv("LLM_BACKEND", "cli")
    monkeypatch.setattr(server, "make_server", lambda *a, **k: pytest.fail("the server must not start"))
    with pytest.raises(SystemExit) as stop:
        server.main()
    assert stop.value.code == 1
    assert "REAL_DATA" in capsys.readouterr().err


# --- the decision log ---

DRAFT = "هلا بيك، نعتذر عن التأخير، راح نتابع التحويل ويانه"
FINAL = "هلا بيك، نعتذر عن التأخير. ممكن ترسل رقم المستلم حتى نتابع التحويل؟"


def _decision(**over):
    body = {"run": "live", "ticket_id": "n1", "action": "edited", "pipeline_outcome": "drafted",
            "flags": ["draft:promise"], "reason_codes": ["promise", "missing_question"], "seconds": 42.5,
            "draft_text": DRAFT, "final_text": FINAL, "corrected": {"priority": "P1"}, "undoes": None}
    body.update(over)
    return body


# What the stub pipeline serves for a pasted ticket unless a test says otherwise.
SERVED = {"outcome": "drafted", "flags": ["draft:promise"], "draft_ar": DRAFT, "team": "transfers", "priority": "P2",
          "extraction": {"subcategory": "not_received"}}


@pytest.fixture
def live(srv, monkeypatch):
    """Paste a ticket: a stub pipeline ends it with SERVED (changed by `over`). Returns the server's id."""
    def make(text="حولت فلوس وما وصلت", **over):
        result = {**SERVED, **over}

        def run(t, emit=lambda e: None, should_stop=None):
            emit(_event("received", {"chars": len(t)}))
            emit(_event("result", result))

        monkeypatch.setattr(server, "process", run)
        for _ in range(250):   # the last run's worker frees the live slot just after its stream ends
            status, _, body = call(srv, "POST", "/api/stream", {"text": text})
            if status != 429:
                break
            time.sleep(0.02)
        events, ended = sse(body)
        assert status == 200 and ended
        return events[0]["live_id"]
    return make


def test_decision_is_logged_with_hashes_and_never_the_text(srv, tmp_path, live):
    n1 = live(text="  حولت ٥٠ الف وما وصلت  ")
    status, _, body = call(srv, "POST", "/api/decision", _decision(ticket_id=n1))
    assert status == 200
    reply = json.loads(body)
    assert reply["ok"] is True and len(reply["id"]) == 32

    log = (tmp_path / "decisions.jsonl").read_text(encoding="utf-8")
    assert DRAFT not in log and FINAL not in log
    assert "هلا بيك" not in log and "نعتذر" not in log   # not even a fragment
    lines = log.splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["id"] == reply["id"] and rec["ts"].endswith("Z") and rec["reviewer"] == "agent-1"
    assert rec["run"] == "live" and rec["ticket_id"] == n1 and rec["action"] == "edited"
    assert rec["pipeline_outcome"] == "drafted" and rec["flags"] == ["draft:promise"]
    assert rec["reason_codes"] == ["promise", "missing_question"] and rec["seconds"] == 42.5
    assert rec["corrected"] == {"priority": "P1"} and rec["undoes"] is None
    # Keyed hashes: they link a decision to its draft, but a short edit can't be guessed from them.
    assert rec["draft_sha256"] == hmac.new(server._HASH_KEY, DRAFT.encode(), hashlib.sha256).hexdigest()
    assert rec["final_sha256"] == hmac.new(server._HASH_KEY, FINAL.encode(), hashlib.sha256).hexdigest()
    assert rec["final_sha256"] != hashlib.sha256(FINAL.encode()).hexdigest()
    assert rec["edit_chars"] > 0
    # The pasted ticket as the pipeline cleaned it (Arabic digits made Latin), keyed the same way.
    cleaned = server.clean("حولت ٥٠ الف وما وصلت")
    assert "50" in cleaned and rec["ticket_sha256"] == hmac.new(server._HASH_KEY, cleaned.encode(), hashlib.sha256).hexdigest()
    assert set(rec["prompt_sha256"]) == {"classifier", "drafter"} and rec["models"]["classifier"]
    assert not {"draft_text", "final_text", "text"} & rec.keys()

    # An undo must name a decision on the same ticket.
    status, _, body = call(srv, "POST", "/api/decision", _decision(action="undone", undoes=reply["id"], ticket_id=live()))
    assert status == 400 and json.loads(body)["field"] == "undoes"
    # Undo it: a second line pointing at the first.
    status, _, body = call(srv, "POST", "/api/decision", _decision(ticket_id=n1, action="undone", undoes=reply["id"],
                                                                   draft_text=None, final_text=None))
    assert status == 200
    lines = (tmp_path / "decisions.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2 and json.loads(lines[1])["undoes"] == reply["id"]


@pytest.mark.parametrize("over, field", [
    ({"action": "sent"}, "action"),
    ({"reason_codes": ["promise", "made_up"]}, "reason_codes"),
    ({"reason_codes": "promise"}, "reason_codes"),
    ({"ticket_id": "../t1"}, "ticket_id"),
    ({"ticket_id": "t" * 65}, "ticket_id"),
    ({"ticket_id": ""}, "ticket_id"),
    ({"run": "exp/heldout/mvp"}, "run"),
    ({"run": "not-a-run"}, "run"),
    ({"pipeline_outcome": "sent"}, "pipeline_outcome"),
    ({"seconds": -1}, "seconds"),
    ({"seconds": 36001}, "seconds"),
    ({"seconds": True}, "seconds"),
    ({"seconds": "10"}, "seconds"),
    ({"flags": ["<script>"]}, "flags"),
    ({"corrected": {"subcategory": "made_up"}}, "corrected.subcategory"),
    ({"corrected": {"team": "nobody"}}, "corrected.team"),
    ({"corrected": {"priority": "P0"}}, "corrected.priority"),
    ({"corrected": {"amount": 5}}, "corrected"),
    ({"action": "undone", "undoes": None}, "undoes"),
    ({"undoes": "0" * 32}, "undoes"),
    ({"action": "undone", "undoes": "0" * 32}, "undoes"),   # no such decision in the log
    ({"action": "undone", "undoes": "not-an-id"}, "undoes"),
    ({"draft_text": 5}, "draft_text"),
    ({"text": "نص التذكرة"}, "text"),
])
def test_invalid_decisions_are_refused_400(srv, tmp_path, over, field):
    status, _, body = call(srv, "POST", "/api/decision", _decision(**over))
    assert status == 400
    assert json.loads(body)["field"] == field
    assert not (tmp_path / "decisions.jsonl").exists()


@pytest.mark.parametrize("over, field", [
    ({"visits": 0}, "visits"),
    ({"visits": True}, "visits"),
    ({"visits": "2"}, "visits"),
    ({"warnings_acknowledged": ["asks_secret"]}, "warnings_acknowledged"),   # a blocking check can't be ticked away
    ({"warnings_acknowledged": ["made_up"]}, "warnings_acknowledged"),
    ({"warnings_acknowledged": "promise"}, "warnings_acknowledged"),
    ({"final_text": None}, "final_text"),                                  # an approval names its reply
    ({"action": "approved", "final_text": None}, "final_text"),
])
def test_new_decision_fields_are_checked(srv, tmp_path, over, field):
    status, _, body = call(srv, "POST", "/api/decision", _decision(**over))
    assert status == 400 and json.loads(body)["field"] == field
    assert not (tmp_path / "decisions.jsonl").exists()


def test_visits_and_acknowledged_warnings_are_logged_as_kinds(srv, tmp_path, live):
    status, _, _ = call(srv, "POST", "/api/decision",
                        _decision(ticket_id=live(), visits=3, warnings_acknowledged=["promise", "promise", "draft_for_other_type"]))
    assert status == 200
    rec = json.loads((tmp_path / "decisions.jsonl").read_text(encoding="utf-8"))
    assert rec["visits"] == 3 and rec["warnings_acknowledged"] == ["promise", "draft_for_other_type"]
    assert "_final" not in rec and FINAL not in json.dumps(rec, ensure_ascii=False)


@pytest.mark.parametrize("reply", ["دزلنا الرمز اللي وصلك حتى نتابع", "شنو الرمز اللي وصلك؟"])
@pytest.mark.parametrize("action", ["approved", "edited"])
def test_an_approval_that_asks_for_a_code_is_refused_409(srv, tmp_path, live, reply, action):
    """SEC-1 (1 Nov review): a stale /api/check answer let the page post a reply that asks for the code.
    The server runs the blocking checks itself; nothing is logged."""
    n1 = live(draft_ar=reply)
    status, _, body = call(srv, "POST", "/api/decision", _decision(ticket_id=n1, action=action, draft_text=reply, final_text=reply))
    assert status == 409
    j = json.loads(body)
    assert j["conflict"] == "blocked" and "رمز" in j["error"] and reply not in j["error"]
    assert not (tmp_path / "decisions.jsonl").exists()
    # taking it over or forwarding it is still recorded (no reply goes anywhere)
    assert call(srv, "POST", "/api/decision", _decision(ticket_id=n1, action="took_over", draft_text=reply, final_text=None))[0] == 200


@pytest.mark.parametrize("reply, why", [
    ("هلا بيك، حسابك تحت التحقيق حالياً", "تحقيق"),
    ("هلا بيك، رفعنا بلاغ للقسم المختص وراح يتابعون", "بلاغ"),     # stays flagged (5 Nov)
    ("هلا بيك، شفنا بطاقتك 4111 1111 1111 1111 وراح نتابع", "رقم بطاقة"),
    ("هلا بيك، الرمز اللي وصلك هو 5521 لا تشاركه", "رمز"),
])
@pytest.mark.parametrize("action", ["approved", "edited"])
def test_an_approval_that_tips_off_or_repeats_a_number_is_refused_409(srv, tmp_path, monkeypatch, live, reply, why, action):
    """hold_reason and sensitive_number block an approval with no flag set (adopted on 5 Nov), at the
    server as on the page; nothing is logged and the reply's text is not echoed."""
    monkeypatch.delenv("PIPELINE_FIXES", raising=False)
    n1 = live(draft_ar=reply)
    status, _, body = call(srv, "POST", "/api/decision", _decision(ticket_id=n1, action=action, draft_text=reply, final_text=reply))
    assert status == 409
    j = json.loads(body)
    assert j["conflict"] == "blocked" and why in j["error"] and reply not in j["error"]
    assert not (tmp_path / "decisions.jsonl").exists()
    assert call(srv, "POST", "/api/decision", _decision(ticket_id=n1, action="took_over", draft_text=reply, final_text=None))[0] == 200


def test_a_second_decision_on_a_saved_run_ticket_is_refused_409(srv, fake_runs):
    """F8 (1 Nov review): two tabs could both approve one ticket; an undo in one then showed it open."""
    first = _decision(run="exp/dev/rec", ticket_id="dev-0001", action="edited", draft_text=None, final_text=FINAL)
    status, _, body = call(srv, "POST", "/api/decision", first)
    assert status == 200
    a = json.loads(body)["id"]
    status, _, body = call(srv, "POST", "/api/decision", first)
    assert status == 409 and json.loads(body)["conflict"] == "decided"
    # undo the standing one: allowed once, then it no longer stands
    undo = _decision(run="exp/dev/rec", ticket_id="dev-0001", action="undone", undoes=a, draft_text=None, final_text=None)
    assert call(srv, "POST", "/api/decision", undo)[0] == 200
    status, _, body = call(srv, "POST", "/api/decision", undo)
    assert status == 409 and json.loads(body)["conflict"] == "undo_stale"
    # decided again after the undo
    assert call(srv, "POST", "/api/decision", first)[0] == 200
    assert [d["action"] for d in server.read_decisions("exp/dev/rec")] == ["edited", "undone", "edited"]


def test_the_identity_tick_is_logged_as_a_kind(srv, tmp_path, live):
    """5 Nov review: «تأكدت من هوية الزبون» was refused as an acknowledged kind, so the log could not show it."""
    n1 = live(flags=["account_risk"], outcome="flagged")
    status, _, _ = call(srv, "POST", "/api/decision", _decision(ticket_id=n1, flags=["account_risk"], warnings_acknowledged=["account_risk"]))
    assert status == 200
    rec = json.loads((tmp_path / "decisions.jsonl").read_text(encoding="utf-8"))
    assert rec["flags"] == ["account_risk"] and rec["warnings_acknowledged"] == ["account_risk"]


@pytest.mark.parametrize("served, over", [
    (["account_risk"], {}),                                                         # the pipeline's flag
    (["account_risk", "draft:promise"], {"warnings_acknowledged": ["promise"]}),
    (["account_risk"], {"flags": []}),                                              # left out of the request
    ([], {"corrected": {"subcategory": "sim_change"}}),                             # the agent's correction
    (["recheck_used_second"], {"corrected": {"subcategory": "blocked_account", "team": "accounts"},
                               "warnings_acknowledged": ["recheck_used_second"]}),
])
@pytest.mark.parametrize("action", ["approved", "edited"])
def test_an_approval_of_a_blocked_account_or_a_sim_change_without_the_identity_tick_is_refused_409(
        srv, tmp_path, live, served, over, action):
    """5 Nov review: a hand-made request (or a stale page) could approve without the identity tick. Nothing
    is logged; with the tick it is; taking the ticket over needs none (no reply is approved). The flag is
    the one the server served, whatever the request says (user tests, 7 Nov)."""
    final = {"final_text": DRAFT} if action == "approved" else {}
    ids = [live(flags=served, outcome="flagged" if served else "drafted") for _ in range(3)]
    status, _, body = call(srv, "POST", "/api/decision", _decision(ticket_id=ids[0], action=action, **final, **over))
    assert status == 409
    j = json.loads(body)
    assert j["conflict"] == "identity" and "«تأكدت من هوية الزبون»" in j["error"]
    assert not (tmp_path / "decisions.jsonl").exists()
    ticked = {**over, "warnings_acknowledged": [*over.get("warnings_acknowledged", []), "account_risk"]}
    assert call(srv, "POST", "/api/decision", _decision(ticket_id=ids[1], action=action, **final, **ticked))[0] == 200
    assert call(srv, "POST", "/api/decision", _decision(ticket_id=ids[2], action="took_over", final_text=None, **over))[0] == 200


def _saved_draft(ticket_id, run="saved/test2/final"):
    rows = server.with_current_gold(server.run_file(run))["tickets"]
    return next(r for r in rows if r["ticket"]["id"] == ticket_id)["result"].get("draft_ar")


def test_a_saved_run_ticket_needs_the_tick_even_when_the_request_leaves_the_flag_out(srv, tmp_path):
    """On a saved run the server reads the ticket itself: t2-0007 (a SIM change, drafted on 30 Oct, served
    with account_risk since 5 Nov) is refused without the tick whatever flags the request sends."""
    body = _decision(run="saved/test2/final", ticket_id="t2-0007", action="approved", pipeline_outcome="drafted",
                     flags=[], reason_codes=[], corrected={}, draft_text=_saved_draft("t2-0007"), final_text=_saved_draft("t2-0007"))
    status, _, raw = call(srv, "POST", "/api/decision", body)
    assert status == 409 and json.loads(raw)["conflict"] == "identity"
    risky = {r["ticket"]["id"] for r in server.with_current_gold(server.run_file("saved/test2/final"))["tickets"]
             if "account_risk" in r["result"]["flags"]}
    assert risky == {"t2-0007", "t2-0016", "t2-0029", "t2-0048", "t2-0054", "t2-0080"}
    assert all("account_risk" in server.served_ticket("saved/test2/final", i)["flags"] for i in risky)
    ready = {**body, "ticket_id": "t2-0002", "draft_text": _saved_draft("t2-0002"), "final_text": _saved_draft("t2-0002")}
    assert call(srv, "POST", "/api/decision", ready)[0] == 200    # a ready one needs none
    assert call(srv, "POST", "/api/decision", {**body, "warnings_acknowledged": ["account_risk"]})[0] == 200
    rec = server.read_decisions("saved/test2/final")[-1]
    assert rec["flags"] == ["account_risk"] and rec["pipeline_outcome"] == "flagged"   # as served, not as sent


SAVED = "saved/test2/final"


def _saved_body(ticket_id, **over):
    draft = _saved_draft(ticket_id)
    return {**_decision(run=SAVED, ticket_id=ticket_id, action="approved", pipeline_outcome="drafted", flags=[],
                        reason_codes=[], corrected={}, draft_text=draft, final_text=draft), **over}


@pytest.mark.parametrize("ticket_id", ["t2-0025", "t2-0045"])   # fraud escalations, no draft
@pytest.mark.parametrize("action", ["approved", "edited"])
def test_an_escalated_ticket_cannot_be_approved_whatever_the_request_says_409(srv, tmp_path, ticket_id, action):
    """User tests, 7 Nov (T03): t2-0025 was logged as approved / drafted / no flags because the request said so.
    The outcome and flags are the served ones; an escalation is only forwarded or taken over."""
    status, _, raw = call(srv, "POST", "/api/decision", _saved_body(ticket_id, action=action, draft_text=None, final_text=FINAL))
    assert status == 409 and json.loads(raw)["conflict"] == "escalated"
    assert not (tmp_path / "decisions.jsonl").exists()
    assert call(srv, "POST", "/api/decision", _saved_body(ticket_id, action="forwarded", draft_text=None, final_text=None))[0] == 200
    rec = server.read_decisions(SAVED)[-1]
    assert rec["pipeline_outcome"] == "escalated" and rec["flags"] == ["fraud"] and rec["draft_sha256"] is None


@pytest.mark.parametrize("action", ["approved", "edited"])
def test_a_correction_to_a_type_that_is_never_drafted_cannot_be_approved_409(srv, tmp_path, live, action):
    n1 = live()
    final = DRAFT if action == "approved" else FINAL
    body = _decision(ticket_id=n1, action=action, final_text=final, corrected={"subcategory": "suspected_scam"})
    status, _, raw = call(srv, "POST", "/api/decision", body)
    assert status == 409 and json.loads(raw)["conflict"] == "escalated"
    assert call(srv, "POST", "/api/decision", {**body, "action": "took_over", "final_text": None})[0] == 200


def test_a_ticket_or_a_draft_the_server_did_not_serve_is_refused_400(srv, tmp_path, live):
    """User tests, 7 Nov (T03): t2-9999 and live-1 were logged though no such ticket was served."""
    for body in ({**_saved_body("t2-0002"), "ticket_id": "t2-9999"}, _decision(ticket_id="live-1"),
                 _decision(run=SAVED, ticket_id=live())):      # a live id is not a saved run's ticket
        status, _, raw = call(srv, "POST", "/api/decision", body)
        assert status == 400 and json.loads(raw)["field"] == "ticket_id"
    n1 = live()
    for over, field in (({"draft_text": "مسودة ثانية"}, "draft_text"),                       # not the served draft
                        ({"action": "approved", "final_text": FINAL}, "final_text")):     # an edit called an approval
        status, _, raw = call(srv, "POST", "/api/decision", _decision(ticket_id=n1, **over))
        assert status == 400 and json.loads(raw)["field"] == field
    assert not (tmp_path / "decisions.jsonl").exists()


def test_a_live_decision_is_checked_against_what_was_served(srv, tmp_path, live):
    """The live registry: outcome, flags and the draft's hash are the ones the run served; the request's
    are not believed. A forward of a live escalation gets its served flags too."""
    n1 = live(outcome="flagged", flags=["missing:reference", "draft:promise"])
    status, _, _ = call(srv, "POST", "/api/decision", _decision(ticket_id=n1, pipeline_outcome="drafted", flags=[],
                                                                  warnings_acknowledged=["missing:reference", "promise"]))
    assert status == 200
    rec = server.read_decisions("live")[-1]
    assert rec["pipeline_outcome"] == "flagged" and rec["flags"] == ["missing:reference", "draft:promise"]
    assert rec["draft_sha256"] == hmac.new(server._HASH_KEY, DRAFT.encode(), hashlib.sha256).hexdigest()
    e1 = live(outcome="escalated", flags=["fraud"], draft_ar=None, extraction={"subcategory": "suspected_scam"})
    status, _, raw = call(srv, "POST", "/api/decision", _decision(ticket_id=e1, draft_text=None, pipeline_outcome="drafted", flags=[]))
    assert status == 409 and json.loads(raw)["conflict"] == "escalated"
    assert call(srv, "POST", "/api/decision", _decision(ticket_id=e1, action="forwarded", draft_text=None, final_text=None))[0] == 200
    assert server.read_decisions("live")[-1]["flags"] == ["fraud"]


def test_a_live_run_cut_short_can_be_taken_over_but_not_approved(srv, live):
    """A run whose result has not come yet (the agent cancelled it): the page shows it escalated."""
    run_id = server.live_started("تذكرة")
    body = _decision(ticket_id=run_id, draft_text=None, flags=["cancelled", "fraud"])
    assert json.loads(call(srv, "POST", "/api/decision", body)[2])["conflict"] == "escalated"
    assert call(srv, "POST", "/api/decision", {**body, "action": "took_over", "final_text": None})[0] == 200
    rec = server.read_decisions("live")[-1]
    assert rec["pipeline_outcome"] == "escalated" and rec["flags"] == ["cancelled"]


def test_a_second_decision_on_a_live_ticket_is_refused_409(srv, live):
    """User tests, 7 Nov (T11): every live ticket was «live-1». Now each run has its own id from the
    server, so a second decision on one is refused like on a saved run."""
    a, b = live(), live()
    assert a != b
    took = _decision(ticket_id=a, action="took_over", final_text=None)
    assert call(srv, "POST", "/api/decision", took)[0] == 200
    status, _, raw = call(srv, "POST", "/api/decision", took)
    assert status == 409 and json.loads(raw)["conflict"] == "decided"
    assert call(srv, "POST", "/api/decision", {**took, "ticket_id": b})[0] == 200


def test_the_live_registry_keeps_hashes_only_and_a_bounded_number(srv, live, monkeypatch):
    monkeypatch.setattr(server, "LIVE_KEEP", 3)
    ids = [live(text=f"تذكرة رقم {i}") for i in range(5)]
    with server._live_lock:
        kept = dict(server._live)
    assert list(kept)[-3:] == ids[-3:] and ids[0] not in kept and len(kept) <= 3
    assert "تذكرة" not in json.dumps(kept, ensure_ascii=False) and DRAFT not in json.dumps(kept, ensure_ascii=False)


def test_every_confirm_kind_the_page_ticks_is_accepted_and_nothing_free_form(srv, live):
    """User tests, 7 Nov (T28): a missing reference and the type after a disagreement were ticked but not
    logged. The kinds are an allow-list; /api/meta gives it to the page."""
    kinds = json.loads(call(srv, "GET", "/api/meta")[2])["ack_kinds"]
    assert kinds == list(server.ACK_KINDS)
    for k in ("missing:reference", "missing:amount", "missing:date", "missing:reference:not_needed", "recheck_used_second",
              "invalid_category", "ref_not_in_text", "account_risk", "promise", "draft_for_other_type", "second_request"):
        assert k in kinds, k
    for k in ("asks_secret", "hold_reason", "sensitive_number", "draft:promise", "missing:anything", "missing:reference:x"):
        assert k not in kinds, k
    acked = ["missing:reference", "recheck_used_second", "missing:amount:not_needed"]
    assert call(srv, "POST", "/api/decision", _decision(ticket_id=live(), warnings_acknowledged=acked))[0] == 200
    assert server.read_decisions("live")[-1]["warnings_acknowledged"] == acked
    status, _, raw = call(srv, "POST", "/api/decision", _decision(ticket_id=live(), warnings_acknowledged=["missing:pin"]))
    assert status == 400 and json.loads(raw)["field"] == "warnings_acknowledged"


def test_a_second_request_the_page_asks_about_is_logged_as_a_kind(srv, live):
    """User tests, 7 Nov (T07, page part): a drafted ticket with a second request asks the agent to read
    what the reply says of it; the tick is logged as second_request, never as text."""
    acked = ["second_request", "missing:reference:not_needed"]
    assert call(srv, "POST", "/api/decision", _decision(ticket_id=live(), warnings_acknowledged=acked))[0] == 200
    assert server.read_decisions("live")[-1]["warnings_acknowledged"] == acked
    for bad in ("second_request:x", "second_request_note"):
        status, _, raw = call(srv, "POST", "/api/decision", _decision(ticket_id=live(), warnings_acknowledged=[bad]))
        assert status == 400 and json.loads(raw)["field"] == "warnings_acknowledged"


def test_reason_codes_include_the_ones_user_tests_asked_for(srv, live):
    meta = json.loads(call(srv, "GET", "/api/meta")[2])
    for code in ("duplicate", "dialect", "false_claim", "instructions"):
        assert code in meta["reason_codes"] and meta["reason_codes_ar"][code]
    assert meta["reason_codes_ar"]["missing_question"] == "ناقصة سؤال للزبون"
    assert call(srv, "POST", "/api/decision", _decision(ticket_id=live(), reason_codes=["dialect", "false_claim"]))[0] == 200


def test_standing_matches_the_page(srv):
    recs = [{"id": "a", "ticket_id": "t", "action": "approved"}, {"id": "u", "ticket_id": "t", "action": "undone", "undoes": "a"},
            {"id": "b", "ticket_id": "t", "action": "edited"}, {"id": "c", "ticket_id": "s", "action": "forwarded"}]
    assert {k: v["id"] for k, v in server.standing(recs).items()} == {"t": "b", "s": "c"}
    assert server.standing(recs[:2]) == {}


def test_meta_says_which_types_are_never_drafted(srv):
    meta = json.loads(call(srv, "GET", "/api/meta")[2])
    never = {k for k, s in meta["subcategories"].items() if s["always_escalate"]}
    assert never == {"suspected_scam", "unauthorized_charge"}


def test_decision_needs_token_and_json(srv, tmp_path):
    assert call(srv, "POST", "/api/decision", _decision(), token=False)[0] == 403
    raw = json.dumps(_decision()).encode()
    assert call(srv, "POST", "/api/decision", raw=raw, headers={"Content-Type": "text/plain"})[0] == 415
    assert not (tmp_path / "decisions.jsonl").exists()


def test_decisions_are_filtered_by_run(srv, fake_runs, live):
    ids = []
    n1, n2 = live(), live()
    for run, tid in (("live", n1), ("exp/dev/rec", "dev-0001"), ("live", n2)):
        draft = DRAFT if run == "live" else None
        status, _, body = call(srv, "POST", "/api/decision", _decision(run=run, ticket_id=tid, draft_text=draft))
        assert status == 200
        ids.append(json.loads(body)["id"])
    got = json.loads(call(srv, "GET", "/api/decisions?run=live")[2])["decisions"]
    assert [d["ticket_id"] for d in got] == [n1, n2] and [d["id"] for d in got] == [ids[0], ids[2]]
    other = json.loads(call(srv, "GET", "/api/decisions?run=exp/dev/rec")[2])["decisions"]
    assert [d["id"] for d in other] == [ids[1]]
    assert json.loads(call(srv, "GET", "/api/decisions?run=nothing")[2]) == {"decisions": []}
    assert call(srv, "GET", "/api/decisions")[0] == 400


def test_concurrent_decisions_never_interleave(srv, tmp_path, live):
    ids = [live() for _ in range(20)]

    def post(i):
        call(srv, "POST", "/api/decision", _decision(ticket_id=ids[i]))

    threads = [threading.Thread(target=post, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    lines = (tmp_path / "decisions.jsonl").read_text(encoding="utf-8").splitlines()
    assert sorted(json.loads(line)["ticket_id"] for line in lines) == sorted(ids)


def test_decision_log_is_readable_by_its_owner_only(srv, tmp_path, live):
    assert call(srv, "POST", "/api/decision", _decision(ticket_id=live()))[0] == 200
    if os.name == "posix":
        assert (tmp_path / "decisions.jsonl").stat().st_mode & 0o777 == 0o600


def test_edit_chars_is_fast_on_long_rewrites():
    """difflib is quadratic: two 8,000-character rewrites took 13 s of CPU per POST."""
    rnd = random.Random(1)
    a = "".join(rnd.choice("بت") for _ in range(8000))
    b = "".join(rnd.choice("بت") for _ in range(8000))
    t0 = time.time()
    assert server.edit_chars(a, b) > 0
    assert time.time() - t0 < 1.0
    # A shared start and end is not counted, and a small edit in a long reply is still exact.
    long = "هلا بيك " * 500
    assert server.edit_chars(long + "راح نتابع" + long, long + "راح نشيك" + long) == 4


def test_main_refuses_a_bad_budget(monkeypatch, capsys):
    monkeypatch.setenv("LLM_BUDGET_USD", "nan")
    monkeypatch.delenv("REAL_DATA", raising=False)
    monkeypatch.setenv("LLM_BACKEND", "api")   # main() sets the viewer's default when it is unset
    monkeypatch.setattr(server, "make_server", lambda *a, **k: pytest.fail("the server must not start"))
    with pytest.raises(SystemExit) as stop:
        server.main()
    assert stop.value.code == 1 and "LLM_BUDGET_USD" in capsys.readouterr().err


def test_viewer_backend_default_is_the_api_unless_llm_backend_is_set():
    env = {}
    assert server.default_viewer_backend(env) is True and env["LLM_BACKEND"] == "api"
    env = {"LLM_BACKEND": "  "}   # blank counts as unset (backend() would refuse it)
    assert server.default_viewer_backend(env) is True and env["LLM_BACKEND"] == "api"
    for given in ("cli", "api", "nonsense"):   # an explicit value is kept; a wrong one is refused at start-up
        env = {"LLM_BACKEND": given}
        assert server.default_viewer_backend(env) is False and env == {"LLM_BACKEND": given}


class _NoServe:
    """make_server() stand-in: start-up prints its line, then serve_forever() returns at once."""
    server_address = ("127.0.0.1", 8123)

    def serve_forever(self):
        raise KeyboardInterrupt


def _start_viewer(monkeypatch, capsys, **env):
    # setenv first: monkeypatch then restores even a variable main() sets that was not there before.
    for k in ("LLM_BACKEND", "SUPPORT_PIPELINE_API_KEY", "ANTHROPIC_API_KEY", "PIPELINE_MODE", "LLM_BUDGET_USD",
              "REAL_DATA", "LLM_CACHE_DIR", "LLM_CACHE_ONLY", "LLM_PROFILE", "PIPELINE_FIXES"):
        monkeypatch.setenv(k, "x")
        monkeypatch.delenv(k)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setattr(server, "make_server", lambda *a, **k: _NoServe())
    server.main()
    return capsys.readouterr().out, os.environ.get("LLM_BACKEND")


def test_viewer_starts_on_the_api_backend_with_live_runs_off_and_no_key(monkeypatch, capsys):
    out, chosen = _start_viewer(monkeypatch, capsys)
    assert chosen == "api"
    assert "backend: api, the viewer's default" in out
    assert "live runs off: no API key; set SUPPORT_PIPELINE_API_KEY" in out
    assert server.live_status()["available"] is False and server.live_status()["cause"] == "no_key"
    assert server.meta()["backend"] == "api"


def test_viewer_with_a_key_runs_live_on_the_api_under_the_cap(monkeypatch, capsys):
    out, chosen = _start_viewer(monkeypatch, capsys, SUPPORT_PIPELINE_API_KEY="placeholder-not-a-real-key")
    assert chosen == "api" and server.live_status()["available"] is True
    assert f"live runs on, API spending capped at ${server.budget_usd():g} for this viewer" in out
    assert "LLM_CACHE_ONLY" not in out and server.meta()["cache_only"] is False


def test_viewer_says_when_it_replays_the_cache_and_keeps_a_small_cap_readable(monkeypatch, capsys):
    # The author's demo: a placeholder key, cache only, a $0.001 cap. Nothing is called (make_server is stubbed).
    out, _ = _start_viewer(monkeypatch, capsys, SUPPORT_PIPELINE_API_KEY="placeholder-not-a-real-key",
                           LLM_BACKEND="api", LLM_CACHE_ONLY="1", LLM_CACHE_DIR="runs/cache", LLM_BUDGET_USD="0.001")
    assert "API spending capped at $0.001 for this viewer" in out   # not "$0.00"
    assert "replaying the response cache only (LLM_CACHE_ONLY=1), so no model is called" in out
    assert server.meta()["cache_only"] is True


def test_viewer_refuses_an_unknown_backend_in_one_line(monkeypatch, capsys):
    monkeypatch.setattr(server, "make_server", lambda *a, **k: pytest.fail("the server must not start"))
    for k in ("REAL_DATA", "PIPELINE_MODE", "LLM_BUDGET_USD"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("LLM_BACKEND", "nonsense")
    with pytest.raises(SystemExit) as stop:
        server.main()
    err = capsys.readouterr().err
    assert stop.value.code == 1 and "Not starting the viewer: Unknown LLM backend 'nonsense'" in err
    assert "Traceback" not in err


def test_viewer_keeps_an_explicit_cli_backend(monkeypatch, capsys):
    out, chosen = _start_viewer(monkeypatch, capsys, LLM_BACKEND="cli", CLAUDE_BIN="/nonexistent/claude")
    assert chosen == "cli"
    assert "backend: cli, from LLM_BACKEND" in out and "live runs off: no claude CLI" in out


def test_edit_chars_counts_changed_characters():
    assert server.edit_chars("نفس الرد", "نفس الرد") == 0
    assert server.edit_chars("رد", None) == 0
    assert server.edit_chars(None, "رد جديد") == len("رد جديد")
    assert server.edit_chars("راح نرجع فلوسك", "راح نتابع طلبك") > 0
    assert server.edit_chars("abc", "abd") == 1
