"""What the viewer serves the new page (app/server.py, 1 Nov): static files, the strict CSP, local fonts,
POST /api/check, spans recomputed for older runs, and the check fields in /api/meta.

Every test runs a real server on a free port; no model is called.
"""

import hashlib
import http.client
import importlib.util
import json
import os
import re
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / "app" / "static" / "fonts"

_spec = importlib.util.spec_from_file_location("viewer_server_ui", ROOT / "app" / "server.py")
server = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(server)

from pipeline import draft as drf  # noqa: E402
from pipeline import draft_check  # noqa: E402
from pipeline.run import FLAG_AR  # noqa: E402

CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; font-src 'self'; img-src 'self' data:; "
       "connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
ASKS_SECRET = "دزلنا الرمز اللي وصلك حتى نكمل"
LIMIT = 4000


@pytest.fixture(autouse=True)
def no_model_calls(monkeypatch):
    from pipeline import llm

    def refuse(*a, **k):
        raise AssertionError("a model was called")

    for name in ("_call_api", "_call_cli", "_call_openai"):
        monkeypatch.setattr(llm, name, refuse)
    monkeypatch.delenv("PIPELINE_FIXES", raising=False)
    monkeypatch.setattr(server, "process", lambda *a, **k: pytest.fail("no live run in these tests"))


@pytest.fixture
def srv(monkeypatch, tmp_path):
    monkeypatch.setenv("DECISIONS_FILE", str(tmp_path / "decisions.jsonl"))
    httpd = server.make_server(port=0)
    threading.Thread(target=httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
    yield httpd
    httpd.shutdown()
    httpd.server_close()


def call(httpd, method, path, body=None, *, token=True, headers=None, raw=None):
    """One request with the path sent exactly as given (no normalising); returns (status, headers, body)."""
    conn = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=10)
    h = {"X-Viewer-Token": server.TOKEN} if token else {}
    if body is not None:
        raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
    if raw is not None:
        h["Content-Type"] = "application/json"
    h.update(headers or {})
    conn.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
    h.setdefault("Host", f"127.0.0.1:{httpd.server_address[1]}")
    for k, v in h.items():
        conn.putheader(k, v)
    if raw is not None:
        conn.putheader("Content-Length", str(len(raw)))
    conn.endheaders(raw)
    resp = conn.getresponse()
    out = resp.status, resp.headers, resp.read()
    conn.close()
    return out


def check(httpd, body, **kw):
    status, _, raw = call(httpd, "POST", "/api/check", body, **kw)
    return status, json.loads(raw)


# --- S1: /static/ ---

def test_fonts_css_and_every_font_it_names_are_served(srv):
    status, headers, body = call(srv, "GET", "/static/fonts/fonts.css", token=False)
    assert status == 200 and headers["Content-Type"] == "text/css; charset=utf-8"
    assert body == (FONTS / "fonts.css").read_bytes()
    css = body.decode("utf-8")
    names = re.findall(r"url\(\./([^)]+)\)", css)
    assert len(names) == 10 and len(set(names)) == 10
    for name in names:
        status, headers, font = call(srv, "GET", f"/static/fonts/{name}", token=False)
        assert status == 200 and headers["Content-Type"] == "font/woff2", name
        assert font == (FONTS / name).read_bytes() and font[:4] == b"wOF2", name
    for path in ("/static/fonts/OFL.txt", "/static/fonts/SOURCE.txt"):
        status, headers, _ = call(srv, "GET", path, token=False)
        assert status == 200 and headers["Content-Type"] == "text/plain; charset=utf-8"


def test_fonts_are_local_with_swap_and_unicode_ranges():
    css = (FONTS / "fonts.css").read_text(encoding="utf-8")
    faces = re.findall(r"@font-face \{(.*?)\}", css, re.DOTALL)
    got = {(re.search(r"font-family: '([^']+)'", f)[1], int(re.search(r"font-weight: (\d+)", f)[1]),
            re.search(r"url\(\./[a-z-]+?-(arabic|latin)-\d+-normal\.woff2\)", f)[1]) for f in faces}
    want = {("IBM Plex Sans Arabic", w, s) for w in (400, 500, 600, 700) for s in ("arabic", "latin")}
    want |= {("IBM Plex Mono", w, "latin") for w in (400, 500)}
    assert got == want and len(faces) == 10
    for f in faces:
        assert "font-display: swap;" in f and "unicode-range: U+" in f and "format('woff2')" in f
    arabic = [f for f in faces if "-arabic-arabic-" in f]
    assert all("U+0600-06FF" in f for f in arabic) and len(arabic) == 4
    assert "http" not in css.replace("https://", "").lower() and "//" not in re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)


def test_font_files_match_their_recorded_sha256_and_licence():
    rows = re.findall(r"^([0-9a-f]{64})  (\S+\.woff2)  <-  (https://cdn\.jsdelivr\.net/npm/@fontsource/\S+@5\.3\.0/\S+)$",
                      (FONTS / "SOURCE.txt").read_text(encoding="utf-8"), re.MULTILINE)
    assert len(rows) == 10
    on_disk = sorted(p.name for p in FONTS.glob("*.woff2"))
    assert sorted(name for _, name, _ in rows) == on_disk
    for digest, name, url in rows:
        assert hashlib.sha256((FONTS / name).read_bytes()).hexdigest() == digest, name
        assert url.endswith("/files/" + name)
    ofl = (FONTS / "OFL.txt").read_text(encoding="utf-8")
    assert ofl.count("SIL OPEN FONT LICENSE Version 1.1") == 2 and "IBM Corp." in ofl


@pytest.fixture
def static_tree(monkeypatch, tmp_path):
    """A static/ folder with one file of each allowed type, files that must not be served, and
    symlinks in and out of it."""
    static = tmp_path / "static"
    (static / "js").mkdir(parents=True)
    (static / "fonts").mkdir()
    files = {"js/app.js": b"export const x = 1;\n", "a.css": b"body{}", "fonts/f.woff2": b"wOF2....",
             "logo.svg": b"<svg xmlns='http://www.w3.org/2000/svg'/>", "notes.txt": b"hello",
             "index.html": b"<html>", ".hidden": b"secret", ".env.js": b"secret", "x.html": b"<html>",
             "x.py": b"print()", "x.json": b"{}", "app.js.map": b"{}", "UPPER.CSS": b"body{}", "noext": b"x"}
    for rel, data in files.items():
        (static / rel).write_bytes(data)
    (tmp_path / "server.py").write_text("SECRET = 1\n")
    (static / "out.js").symlink_to(tmp_path / "server.py")
    (static / "outdir").symlink_to(tmp_path)
    (static / "in.css").symlink_to(static / "a.css")
    (static / "loop.js").symlink_to(static / "loop.js")
    monkeypatch.setattr(server, "STATIC", static)
    return static


def test_each_allowed_type_has_its_exact_content_type(srv, static_tree):
    for path, ctype in (("js/app.js", "text/javascript; charset=utf-8"), ("a.css", "text/css; charset=utf-8"),
                        ("fonts/f.woff2", "font/woff2"), ("logo.svg", "image/svg+xml"),
                        ("notes.txt", "text/plain; charset=utf-8"), ("in.css", "text/css; charset=utf-8"),
                        ("a.css?v=2", "text/css; charset=utf-8")):
        status, headers, body = call(srv, "GET", "/static/" + path, token=False)
        assert status == 200 and headers["Content-Type"] == ctype, path
        assert body == (static_tree / path.split("?")[0]).read_bytes()
        assert headers["Content-Security-Policy"] == CSP and headers["X-Content-Type-Options"] == "nosniff"


@pytest.mark.parametrize("path", [
    "/static/../server.py", "/static/%2e%2e/server.py", "/static/fonts/../../server.py", "/static/.hidden",
    "/static/js/", "/static/js", "/static/", "/static", "/static//a.css", "/static/./a.css", "/static/js/../a.css",
    "/static/%2e%2e%2fserver.py", "/static/..%2fserver.py", "/static/.%2e/server.py", "/static/a%2ecss",
    "/static/fonts\\..\\..\\server.py", "/static/a.css%00.js", "/static/a%00.css", "/static/.env.js",
    "/static/index.html", "/static/x.html", "/static/x.py", "/static/x.json", "/static/app.js.map",
    "/static/UPPER.CSS", "/static/noext", "/static/out.js", "/static/outdir/server.py", "/static/loop.js",
    "/static/missing.js", "/static/js/missing.js", "/static/" + "a" * 300 + ".js", "/static/" + "a/" * 200 + "a.js",
    "/static/a.css/", "/static/~/a.css", "/static/%20a.css", "/static/a%20.css", "/static/..;/server.py",
])
def test_anything_else_under_static_is_404(srv, static_tree, path):
    status, headers, body = call(srv, "GET", path, token=False)
    assert status == 404, path
    assert headers["Content-Type"].startswith("application/json") and b"SECRET" not in body and b"wOF2" not in body


def test_static_file_never_resolves_outside_the_folder(static_tree):
    assert server.static_file("js/app.js") == ((static_tree / "js" / "app.js").resolve(), "text/javascript; charset=utf-8")
    for rel in ("../server.py", "out.js", "outdir/server.py", "loop.js", "", "js", "js/", ".hidden", "a\x00.css",
                "a\\b.css", "index.html", "x" * 10_000 + ".js"):
        assert server.static_file(rel) is None, rel[:40]


def test_static_needs_no_token_but_keeps_the_host_and_origin_checks(srv):
    port = srv.server_address[1]
    assert call(srv, "GET", "/static/fonts/fonts.css", token=False)[0] == 200
    assert call(srv, "GET", "/static/fonts/fonts.css")[0] == 200
    assert call(srv, "GET", "/static/fonts/fonts.css", token=False, headers={"Host": "evil.example"})[0] == 421
    assert call(srv, "GET", "/static/fonts/fonts.css", token=False,
                headers={"Origin": "http://evil.example"})[0] == 403
    assert call(srv, "GET", "/static/fonts/fonts.css", token=False,
                headers={"Origin": f"http://localhost:{port}"})[0] == 200
    assert call(srv, "POST", "/static/fonts/fonts.css", raw=b"{}")[0] == 404


# --- S2: CSP ---

def test_strict_csp_on_every_response(srv):
    responses = [call(srv, "GET", "/"), call(srv, "GET", "/static/fonts/fonts.css"), call(srv, "GET", "/static/x"),
                 call(srv, "GET", "/api/meta"), call(srv, "POST", "/api/check", {"draft": "", "allowed_text": ""}),
                 call(srv, "POST", "/api/check", {"draft": 1, "allowed_text": ""}),
                 call(srv, "GET", "/api/meta", token=False), call(srv, "GET", "/", headers={"Host": "x.example"})]
    assert {r[0] for r in responses} == {200, 400, 403, 404, 421}
    for status, headers, _ in responses:
        csp = headers["Content-Security-Policy"]
        assert csp == CSP, status
        assert "unsafe-inline" not in csp and "googleapis" not in csp and "gstatic" not in csp


# --- S4: POST /api/check ---

def test_check_finds_a_secret_request(srv):
    status, body = check(srv, {"draft": ASKS_SECRET, "allowed_text": "<ticket>\nالتحويل ما وصل\n</ticket>"})
    assert status == 200 and [f["kind"] for f in body["findings"]] == ["asks_secret"]
    f = body["findings"][0]
    assert ASKS_SECRET[f["start"]:f["end"]] == f["text"] and "الرمز" in f["text"]


def test_check_returns_exactly_what_the_pipeline_computes(srv, monkeypatch):
    allowed = "<ticket>\nحولت 50 الف ل 07701234567 وما وصل\n</ticket>\nKnown facts: none"
    for draft in ("هلا بيك، راح نرجعلك 75 الف خلال يومين. card", "هلا بيك، نشيك على التحويل.", ASKS_SECRET, ""):
        for sub in (None, "not_received", "app_bug"):
            body = {"draft": draft, "allowed_text": allowed, **({"subcategory": sub} if sub else {})}
            status, out = check(srv, body)
            assert status == 200
            assert out == {"findings": draft_check.findings(draft, allowed, drf.facts_text(sub))}
    status, out = check(srv, {"draft": "هلا بيك، راح نرجعلك 75 الف خلال يومين. card", "allowed_text": allowed,
                              "subcategory": None})
    assert status == 200 and [f["kind"] for f in out["findings"]] == ["stray_latin", "promise", "unknown_number"]


def test_check_allows_a_time_only_from_the_policy_facts(srv, monkeypatch):
    draft = "هلا بيك، الرد خلال ٢٤ ساعة."
    allowed = "<ticket>\nردوا علي خلال ٢٤ ساعة\n</ticket>"   # the customer wrote it: still a promise
    assert [f["kind"] for f in check(srv, {"draft": draft, "allowed_text": allowed,
                                           "subcategory": "not_received"})[1]["findings"]] == ["promise"]
    real = drf.load_yaml
    filled = {"company": {"support_hours_ar": None},
              "subcategories": {"not_received": {"response_time_ar": "خلال ٢٤ ساعة", "customer_should_send": []}}}
    monkeypatch.setattr(drf, "load_yaml", lambda name: filled if name == "policy.yaml" else real(name))
    assert check(srv, {"draft": draft, "allowed_text": allowed, "subcategory": "not_received"})[1]["findings"] == []
    assert [f["kind"] for f in check(srv, {"draft": draft, "allowed_text": allowed,
                                           "subcategory": "app_bug"})[1]["findings"]] == ["promise"]
    assert [f["kind"] for f in check(srv, {"draft": draft, "allowed_text": allowed})[1]["findings"]] == ["promise"]


def test_check_always_runs_hold_reason_and_sensitive_number(srv):
    """Adopted on 5 Nov: no flag turns them on or off."""
    draft = "هلا بيك، الموضوع تحت التحقيق بسبب اشتباه. رقم بطاقتك 4111 1111 1111 1111"
    allowed = "<ticket>\nبطاقتي 4111 1111 1111 1111 انقفلت\n</ticket>"
    found = check(srv, {"draft": draft, "allowed_text": allowed})[1]["findings"]
    assert [f["kind"] for f in found] == ["hold_reason", "sensitive_number"]
    assert not any(ch.isdigit() for ch in found[1]["text"])   # a code or card number comes back as *
    status, out = check(srv, {"draft": "هلا بيك، رفعنا بلاغ للقسم المختص", "allowed_text": ""})
    assert status == 200 and [f["kind"] for f in out["findings"]] == ["hold_reason"]


def test_check_limits_are_413_and_the_edges_pass(srv):
    ok = check(srv, {"draft": "ا" * (2 * LIMIT), "allowed_text": "ب" * (4 * LIMIT)})
    assert ok[0] == 200
    for body, field in (({"draft": "ا" * (2 * LIMIT + 1), "allowed_text": ""}, "draft"),
                        ({"draft": "", "allowed_text": "ب" * (4 * LIMIT + 1)}, "allowed_text")):
        status, out = check(srv, body)
        assert status == 413 and out["field"] == field and "حرف" in out["error"]
    status, _, _ = call(srv, "POST", "/api/check", raw=b'{"draft": "' + b"a" * 70_000 + b'", "allowed_text": ""}')
    assert status == 413


@pytest.mark.parametrize("body,field", [
    ({"allowed_text": ""}, "draft"),
    ({"draft": ""}, "allowed_text"),
    ({"draft": None, "allowed_text": ""}, "draft"),
    ({"draft": ["x"], "allowed_text": ""}, "draft"),
    ({"draft": "", "allowed_text": 5}, "allowed_text"),
    ({"draft": "", "allowed_text": "", "subcategory": "nope"}, "subcategory"),
    ({"draft": "", "allowed_text": "", "subcategory": "../app_bug"}, "subcategory"),
    ({"draft": "", "allowed_text": "", "subcategory": 3}, "subcategory"),
    ({"draft": "", "allowed_text": "", "subcategory": ["app_bug"]}, "subcategory"),
    ({"draft": "", "allowed_text": "", "team": "tech"}, "team"),
])
def test_check_bad_fields_are_400(srv, body, field):
    status, out = check(srv, body)
    assert status == 400 and out["field"] == field and any("؀" <= ch <= "ۿ" for ch in out["error"])


def test_check_has_the_same_guards_as_every_post(srv):
    port = srv.server_address[1]
    body = {"draft": ASKS_SECRET, "allowed_text": ""}
    assert check(srv, body, token=False)[0] == 403
    assert check(srv, body, headers={"X-Viewer-Token": "x"})[0] == 403
    assert check(srv, body, headers={"Host": "evil.example"})[0] == 421
    assert check(srv, body, headers={"Origin": "http://evil.example"})[0] == 403
    assert check(srv, body, headers={"Origin": f"http://localhost:{port}"})[0] == 200
    assert check(srv, body, headers={"Content-Type": "text/plain"})[0] == 415
    assert call(srv, "POST", "/api/check", raw=b"{not json")[0] == 400
    assert call(srv, "POST", "/api/check", raw=b'["x"]')[0] == 400
    assert call(srv, "POST", "/api/check", raw=b'{"draft": NaN, "allowed_text": ""}')[0] == 400
    assert call(srv, "POST", "/api/check", raw=b'{"draft": "\xff", "allowed_text": ""}')[0] == 400
    status, _, raw = call(srv, "POST", "/api/check", raw=b'{"draft": "\\ud83d", "allowed_text": ""}')
    assert status == 400 and json.loads(raw)["field"] == "draft"
    status, _, raw = call(srv, "POST", "/api/check", raw=b'{"draft": "", "allowed_text": "x\\udc00"}')
    assert status == 400 and json.loads(raw)["field"] == "allowed_text"
    assert call(srv, "GET", "/api/check")[0] == 404   # a POST only


def test_check_never_logs_or_stores_the_text(srv, tmp_path, capsys):
    secret = "دزلنا الرمز 482913 مالتك حتى نكمل، ورقم بطاقتك 4111111111111111"
    before = sorted(p for p in tmp_path.rglob("*"))
    for _ in range(3):
        assert check(srv, {"draft": secret, "allowed_text": secret, "subcategory": "login_otp"})[0] == 200
    assert check(srv, {"draft": secret * 1000, "allowed_text": ""})[0] == 413
    assert sorted(p for p in tmp_path.rglob("*")) == before   # no decision log, no file of any kind
    out = capsys.readouterr()
    assert "482913" not in out.out + out.err and "الرمز" not in out.out + out.err


# --- S5: spans recomputed for runs made before 1 Nov ---

def _draft_row(tid, reply, prompt, *, spans=None, result_checks="missing", outcome="drafted", sub="app_bug"):
    data = {"model": "m", "user_prompt": prompt, "reply": reply, "checks": []}
    if spans is not None:
        data["check_spans"] = spans
    result = {"outcome": outcome, "flags": [], "draft_ar": reply, "extraction": {"subcategory": sub}}
    if result_checks != "missing":
        result["draft_checks"] = result_checks
    return {"ticket": {"id": tid, "text": "نص"},
            "events": [{"stage": "received", "status": "done", "data": {"text": "نص"}, "ms": 0},
                       {"stage": "draft", "status": "running", "data": {"model": "m"}, "ms": 1},
                       {"stage": "draft", "status": "done", "data": data, "ms": 2},
                       {"stage": "result", "status": "done", "data": result, "ms": 3}],
            "result": result, "seconds": 1.0}


@pytest.fixture
def old_runs(monkeypatch, tmp_path):
    runs, saved = tmp_path / "runs", tmp_path / "docs" / "runs"
    prompt = "<ticket>\nالتطبيق يعلق\n</ticket>\nKnown facts: none"
    escalated = {"ticket": {"id": "t2-0004", "text": "نص"},
                 "events": [{"stage": "draft", "status": "skipped", "data": {"why": "x"}, "ms": 0}],
                 "result": {"outcome": "escalated", "flags": ["fraud"], "handoff_ar": "ملاحظة"}, "seconds": 1.0}
    run = {"meta": {"set": "tickets", "backend": "api"}, "tickets": [
        _draft_row("t2-0001", ASKS_SECRET, prompt),                                     # old: no spans anywhere
        _draft_row("t2-0002", "هلا بيك، نشيك.", prompt, spans=[], result_checks=[]),     # new: left alone
        _draft_row("t2-0003", ASKS_SECRET, prompt, result_checks=None),                 # null result checks
        escalated,
    ]}
    f = runs / "20261030-000000-tickets-api.json"
    f.parent.mkdir(parents=True)
    saved.mkdir(parents=True)
    f.write_text(json.dumps(run, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(server, "ROOT", tmp_path)
    monkeypatch.setattr(server, "RUNS", runs)
    monkeypatch.setattr(server, "SAVED", saved)
    monkeypatch.setattr(server, "PROBES", tmp_path / "data" / "probes")
    server._recomputed.clear()
    return f, run


def _strip_recomputed(run, original):
    """The run with every field S5 adds taken out again (a null draft_checks put back as it was)."""
    for row, orig in zip(run["tickets"], original["tickets"]):
        res = row.get("result", {})
        if res.pop("draft_checks_recomputed", False):
            res.pop("draft_checks")
            if "draft_checks" in orig["result"]:
                res["draft_checks"] = orig["result"]["draft_checks"]
        for ev in row["events"]:
            if ev["data"].pop("check_spans_recomputed", False):
                ev["data"].pop("check_spans")
    return run


def test_old_runs_get_spans_marked_recomputed_and_nothing_else_changes(srv, old_runs):
    f, original = old_runs
    status, _, raw = call(srv, "GET", "/api/run?name=20261030-000000-tickets-api")
    assert status == 200
    run = json.loads(raw)
    t1, t2, t3, t4 = run["tickets"]
    want = [{"kind": "asks_secret", **{k: v for k, v in draft_check.findings(ASKS_SECRET, "")[0].items() if k != "kind"}}]
    d1 = t1["events"][2]["data"]
    assert d1["check_spans"] == want and d1["check_spans_recomputed"] is True
    assert t1["result"]["draft_checks"] == want and t1["result"]["draft_checks_recomputed"] is True
    assert "check_spans" not in t1["events"][1]["data"] and "check_spans" not in t1["events"][3]["data"]
    assert "check_spans_recomputed" not in t2["events"][2]["data"] and "draft_checks_recomputed" not in t2["result"]
    assert t3["result"]["draft_checks"] == want and t3["result"]["draft_checks_recomputed"] is True
    assert "draft_checks" not in t4["result"] and all("check_spans" not in e["data"] for e in t4["events"])
    assert _strip_recomputed(run, original) == original
    assert json.loads(f.read_text(encoding="utf-8")) == original   # the file itself is never changed


def test_recomputed_spans_are_cached_until_the_file_or_the_flags_change(old_runs, monkeypatch):
    f, _ = old_runs
    calls = []
    real = server.recompute_checks
    monkeypatch.setattr(server, "recompute_checks", lambda t: calls.append(1) or real(t))
    a = server.with_current_gold(f)
    b = server.with_current_gold(f)
    assert len(calls) == 1 and a == b
    st = f.stat()
    os.utime(f, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000))
    server.with_current_gold(f)
    assert len(calls) == 2
    # a flag (none is open since 5 Nov: a stand-in) could change what the checks find
    monkeypatch.setitem(server.fixes.FIXES, "some_fix", "a stand-in flag for this test")
    monkeypatch.setenv("PIPELINE_FIXES", "some_fix")
    server.with_current_gold(f)
    assert len(calls) == 3


def test_committed_final_run_gets_spans_that_agree_with_its_saved_checks(srv):
    status, _, raw = call(srv, "GET", "/api/run?name=saved/test2/final")
    assert status == 200
    run = json.loads(raw)
    drafts = 0
    for row in run["tickets"]:
        done = [e for e in row["events"] if e["stage"] == "draft" and e["status"] == "done"]
        if not done:
            assert "draft_ar" not in row["result"] and "draft_checks" not in row["result"]
            continue
        drafts += 1
        data = done[0]["data"]
        assert data["check_spans_recomputed"] is True
        assert [s["kind"] for s in data["check_spans"]] == data["checks"], row["ticket"]["id"]
        assert row["result"]["draft_checks"] == data["check_spans"] and row["result"]["draft_checks_recomputed"]
        for s in data["check_spans"]:
            assert data["reply"][s["start"]:s["end"]] == s["text"]
    assert drafts == 74 and len(run["tickets"]) == 80


# --- the 5 Nov review: saved runs get the account_risk flag as run.py gives it now ---

def _risk_rows():
    prompt = "<ticket>\nحسابي انقفل\n</ticket>\nKnown facts: none"
    blocked = _draft_row("t2-0001", "هلا بيك، راح نحول طلبك لقسم الحسابات.", prompt, spans=[], result_checks=[],
                         sub="blocked_account")
    blocked["result"] = {**blocked["result"], "notes_ar": []}
    sim = _draft_row("t2-0002", "هلا بيك، راح نتابع.", prompt, spans=[], result_checks=[], outcome="flagged", sub="sim_change")
    sim["result"] = {**sim["result"], "flags": ["recheck_used_second", "draft:promise"], "notes_ar": ["n1", "n2"],
                     "recheck_alternative": "login_otp"}
    sim["events"][-1] = {**sim["events"][-1], "data": sim["result"]}
    escalated = {"ticket": {"id": "t2-0003", "text": "نص"}, "events": [],
                 "result": {"outcome": "escalated", "flags": ["recheck_disagreed"], "handoff_ar": "ملاحظة",
                            "extraction": {"subcategory": "sim_change"}}, "seconds": 1.0}
    other = _draft_row("t2-0004", "هلا بيك، راح نتابع.", prompt, spans=[], result_checks=[], sub="login_otp")
    already = _draft_row("t2-0005", "هلا بيك، راح نتابع.", prompt, spans=[], result_checks=[], outcome="flagged",
                         sub="blocked_account")
    already["result"] = {**already["result"], "flags": ["account_risk"]}
    already["events"][-1] = {**already["events"][-1], "data": already["result"]}
    return [blocked, sim, escalated, other, already]


def test_saved_runs_get_account_risk_marked_recomputed_and_nothing_else_changes(srv, old_runs):
    """A run made before 5 Nov showed a blocked account or a SIM change as ready (one key, no identity tick).
    The server now gives each drafted one the flag the way run.py does, in the result and its event."""
    f, _ = old_runs
    original = {"meta": {"set": "tickets", "backend": "api"}, "tickets": _risk_rows()}
    f.write_text(json.dumps(original, ensure_ascii=False), encoding="utf-8")
    status, _, raw = call(srv, "GET", "/api/run?name=20261030-000000-tickets-api")
    assert status == 200
    blocked, sim, escalated, other, already = json.loads(raw)["tickets"]
    for row in (blocked, sim):
        ev = row["events"][-1]["data"]
        assert row["result"]["outcome"] == ev["outcome"] == "flagged"
        assert row["result"]["account_risk_recomputed"] is True and ev["account_risk_recomputed"] is True
        assert row["result"]["draft_ar"] == ev["draft_ar"]
    assert blocked["result"]["flags"] == ["account_risk"] and blocked["result"]["notes_ar"] == [FLAG_AR["account_risk"]]
    # after the gate and re-check flags, before the draft checks: the order run.py adds them
    assert sim["result"]["flags"] == ["recheck_used_second", "account_risk", "draft:promise"]
    assert sim["result"]["notes_ar"] == ["n1", FLAG_AR["account_risk"], "n2"]
    original_rows = original["tickets"]
    assert escalated == original_rows[2] and other == original_rows[3] and already == original_rows[4]
    for row, orig in ((blocked, original_rows[0]), (sim, original_rows[1])):
        for d in (row["result"], row["events"][-1]["data"]):
            assert d.pop("account_risk_recomputed") is True
        assert {k: v for k, v in row["result"].items() if k not in ("outcome", "flags", "notes_ar")} == \
            {k: v for k, v in orig["result"].items() if k not in ("outcome", "flags", "notes_ar")}
    assert json.loads(f.read_text(encoding="utf-8")) == original   # the file itself is never changed


def test_committed_final_run_shows_the_six_account_risk_tickets_flagged(srv):
    status, _, raw = call(srv, "GET", "/api/run?name=saved/test2/final")
    run = json.loads(raw)
    by = {r["ticket"]["id"]: r["result"] for r in run["tickets"]}
    risky = sorted(i for i, r in by.items() if "account_risk" in r["flags"])
    assert risky == ["t2-0007", "t2-0016", "t2-0029", "t2-0048", "t2-0054", "t2-0080"]
    assert all(by[i]["outcome"] == "flagged" and by[i]["flags"] == ["account_risk"] and by[i]["draft_ar"]
               and by[i]["account_risk_recomputed"] for i in risky)
    assert by["t2-0009"]["flags"] == ["recheck_used_second"] and "account_risk_recomputed" not in by["t2-0009"]
    outcomes = [r["outcome"] for r in by.values()]
    assert (outcomes.count("flagged"), outcomes.count("escalated"), outcomes.count("drafted")) == (15, 6, 59)


def test_meta_names_the_account_risk_types(srv):
    meta = json.loads(call(srv, "GET", "/api/meta")[2])
    assert meta["account_risk_types"] == ["blocked_account", "sim_change"]
    assert all(t in meta["subcategories"] and not meta["subcategories"][t]["always_escalate"] for t in meta["account_risk_types"])


# --- S6: /api/meta ---

def test_meta_names_the_blocking_checks_and_explains_every_kind(srv):
    status, _, raw = call(srv, "GET", "/api/meta")
    meta = json.loads(raw)
    assert status == 200
    assert meta["blocking_checks"] == ["asks_secret", "hold_reason", "sensitive_number"]
    # the warnings behind flags have their wording too: a run saved with the flag on still shows them
    assert list(meta["check_ar"]) == list(draft_check.KINDS + draft_check.FLAG_KINDS)
    for kind, text in meta["check_ar"].items():
        assert text == FLAG_AR[f"draft:{kind}"] and "\n" not in text and any("؀" <= ch <= "ۿ" for ch in text)
    # every rule runs (hold_reason and sensitive_number since 5 Nov), so «ما لكينا» may name them all; with no
    # flag on, no warning under test runs, so it names none of them
    assert meta["checks_active"] == list(draft_check.KINDS) == ["stray_latin", "promise", "asks_secret", "unknown_number",
                                                                  "hold_reason", "sensitive_number"]
    assert meta["flag_ar"]["account_risk"].startswith("حساب مقفول أو تبديل شريحة: تأكد من هوية الزبون")
    assert meta["quiet_flags"] == ["instructions_in_ticket"]


@pytest.mark.parametrize("fixes, added", [
    ("claims_done,dialect_words", ["claims_done", "dialect_words"]),
    ("ask_missing,repeated_text", ["repeated_text", "ask_missing"]),
    ("amount_own_words", ["amount_not_in_ticket"]),
    ("secret_in_ticket", []),
])
def test_checks_active_adds_a_flagged_warning_only_while_its_flag_is_on(srv, monkeypatch, fixes, added):
    monkeypatch.setenv("PIPELINE_FIXES", fixes)
    meta = json.loads(call(srv, "GET", "/api/meta")[2])
    assert meta["checks_active"] == list(draft_check.KINDS) + added


# --- the shared facts helper (draft.py) ---

def test_one_facts_helper_for_the_prompt_the_pipeline_and_the_viewer(monkeypatch):
    from pipeline.schemas import Extraction
    ex = Extraction(category="transfers", subcategory="not_received", confidence=0.9)
    assert drf.known_facts(ex) == drf.policy_facts("not_received") == [] and drf.facts_text(None) == ""
    real = drf.load_yaml
    filled = {"company": {"support_hours_ar": "من السبت للخميس"},
              "subcategories": {"not_received": {"response_time_ar": "خلال ٢٤ ساعة", "customer_should_send": []}}}
    monkeypatch.setattr(drf, "load_yaml", lambda name: filled if name == "policy.yaml" else real(name))
    assert drf.facts_text("not_received") == "\n".join(drf.known_facts(ex)) == (
        "Support hours: من السبت للخميس\nExpected response time for this issue: خلال ٢٤ ساعة")
    assert drf.facts_text(None) == drf.facts_text("app_bug") == "Support hours: من السبت للخميس"
    assert "Known facts: " + "; ".join(drf.known_facts(ex)) in drf.user_prompt("…", ex, "transfers")


def test_the_pipeline_checks_its_draft_with_the_shared_helper(monkeypatch):
    from pipeline import run
    seen = []
    monkeypatch.setattr(run, "call", lambda role, system, user, attempt=0:
                        '{"category": "general", "subcategory": "app_bug", "confidence": 0.95}')
    monkeypatch.setattr(drf, "call", lambda role, system, user: "هلا بيك، نرد عليك خلال ساعة.")
    monkeypatch.setattr(drf, "facts_text", lambda sub: seen.append(sub) or "Support hours: خلال ساعة")
    result = run.process("التطبيق يفتح شاشة بيضاء")
    assert seen == ["app_bug"] and "draft:promise" not in result["flags"]
    monkeypatch.setattr(drf, "facts_text", lambda sub: "")
    assert "draft:promise" in run.process("التطبيق يفتح شاشة بيضاء")["flags"]


def test_main_refuses_an_unknown_fix_flag(monkeypatch, capsys):
    """checks_active (in /api/meta) reads PIPELINE_FIXES, so a typo stops the viewer at start, not the page."""
    monkeypatch.setenv("PIPELINE_FIXES", "hold_reasn")
    monkeypatch.delenv("REAL_DATA", raising=False)
    monkeypatch.delenv("LLM_BUDGET_USD", raising=False)
    monkeypatch.setattr(server, "make_server", lambda *a, **k: pytest.fail("the server must not start"))
    with pytest.raises(SystemExit) as stop:
        server.main()
    assert stop.value.code == 1 and "hold_reasn" in capsys.readouterr().err


@pytest.mark.parametrize("name", ["hold_reason", "sensitive_number", "escalate_account_risk"])
def test_main_refuses_an_adopted_flag_and_says_what_became_of_it(name, monkeypatch, capsys):
    monkeypatch.setenv("PIPELINE_FIXES", name)
    monkeypatch.delenv("REAL_DATA", raising=False)
    monkeypatch.delenv("LLM_BUDGET_USD", raising=False)
    monkeypatch.setattr(server, "make_server", lambda *a, **k: pytest.fail("the server must not start"))
    with pytest.raises(SystemExit) as stop:
        server.main()
    err = capsys.readouterr().err
    assert stop.value.code == 1 and name in err and "now the normal code" in err and "Remove it from PIPELINE_FIXES" in err


def test_recompute_skips_malformed_rows_and_events():
    prompt = "<ticket>\nx\n</ticket>"
    rows = ["not a row", {"events": "x", "result": None},
            {"events": [None, 3, "draft", {"stage": "draft", "status": "done", "data": None},
                        {"stage": "draft", "status": "done", "data": {"reply": 5, "user_prompt": prompt}},
                        {"stage": "draft", "status": "done", "data": {"reply": ASKS_SECRET, "user_prompt": prompt}}],
             "result": {"draft_ar": ASKS_SECRET, "extraction": "x"}}]
    out = server.recompute_checks(rows)
    assert list(out) == [2] and set(out[2]) == {5, "result"}
    assert [f["kind"] for f in out[2][5]] == ["asks_secret"] and out[2]["result"] == out[2][5]
