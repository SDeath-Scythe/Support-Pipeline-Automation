"""The page itself (app/static, 1 Nov): it must keep working under the strict CSP and never turn ticket or
model text into markup, and /api/meta must give it what it needs to show where another answer would go.

These read the files and run a real server on a free port; no model is called and no browser is needed.
"""

import html.parser
import http.client
import importlib.util
import json
import re
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app" / "static"
JS = sorted((STATIC / "js").glob("*.js"))
CSS = sorted((STATIC / "css").glob("*.css"))

_spec = importlib.util.spec_from_file_location("viewer_server_page", ROOT / "app" / "server.py")
server = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(server)

from pipeline.config import taxonomy, thresholds  # noqa: E402


@pytest.fixture(autouse=True)
def no_model_calls(monkeypatch):
    from pipeline import llm

    def refuse(*a, **k):
        raise AssertionError("a model was called")

    for name in ("_call_api", "_call_cli", "_call_openai"):
        monkeypatch.setattr(llm, name, refuse)
    monkeypatch.delenv("PIPELINE_FIXES", raising=False)


@pytest.fixture
def srv(monkeypatch, tmp_path):
    monkeypatch.setenv("DECISIONS_FILE", str(tmp_path / "decisions.jsonl"))
    httpd = server.make_server(port=0)
    threading.Thread(target=httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
    yield httpd
    httpd.shutdown()
    httpd.server_close()


def get(httpd, path, token=True):
    conn = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=10)
    headers = {"Host": f"127.0.0.1:{httpd.server_address[1]}"}
    if token:
        headers["X-Viewer-Token"] = server.TOKEN
    conn.request("GET", path, headers=headers)
    r = conn.getresponse()
    out = r.status, r.headers, r.read()
    conn.close()
    return out


class _Markup(html.parser.HTMLParser):
    """Collects what the CSP would block in index.html: inline scripts and styles, style attributes,
    inline event handlers, and every URL the page loads."""

    def __init__(self):
        super().__init__()
        self.inline_script = self.inline_style = 0
        self.style_attrs, self.handlers, self.urls, self.scripts = [], [], [], []
        self._in = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for k, v in attrs:
            if k == "style":
                self.style_attrs.append(tag)
            if k.startswith("on"):
                self.handlers.append(f"{tag} {k}")
            if k in ("src", "href") and v and not v.startswith("#"):
                self.urls.append(v)
        if tag == "script":
            self.scripts.append(a)
            self._in = "script" if "src" not in a else None
        if tag == "style":
            self._in = "style"

    def handle_endtag(self, tag):
        self._in = None

    def handle_data(self, data):
        if self._in == "script" and data.strip():
            self.inline_script += 1
        if self._in == "style" and data.strip():
            self.inline_style += 1


def test_index_html_has_nothing_the_csp_blocks():
    page = (STATIC / "index.html").read_text(encoding="utf-8")
    m = _Markup()
    m.feed(page)
    assert m.inline_script == 0 and m.inline_style == 0
    assert m.style_attrs == [] and m.handlers == []
    assert m.scripts == [{"type": "module", "src": "/static/js/main.js"}]
    assert all(u.startswith("/static/") for u in m.urls), m.urls   # nothing from another site
    assert "<head>" in page                                         # where the server puts the token
    assert re.search(r'<html lang="ar" dir="rtl">', page)


def test_scripts_never_build_markup_from_strings_or_reach_another_site():
    banned = re.compile(r"\.innerHTML|\.outerHTML|insertAdjacentHTML|document\.write|\beval\(|new Function|"
                        r"setAttribute\(\s*[\"']style|\.style\.cssText|localStorage\.setItem\((?!PREF_KEY)")
    for f in JS:
        src = f.read_text(encoding="utf-8")
        assert not banned.search(src), f"{f.name}: {banned.search(src).group(0)}"
        # The only absolute URL is the SVG namespace, which is never fetched.
        urls = [u for u in re.findall(r"https?://[^\s\"'`)]+", src) if u != "http://www.w3.org/2000/svg"]
        assert urls == [], f"{f.name}: {urls}"


def test_stylesheets_load_nothing_from_another_site():
    for f in [*CSS, STATIC / "fonts" / "fonts.css"]:
        src = f.read_text(encoding="utf-8")
        assert not re.search(r"@import\s+url\(\s*['\"]?https?:|url\(\s*['\"]?https?:|//fonts\.", src), f.name


def test_only_preferences_go_to_local_storage():
    """Ticket text, drafts and edits stay in memory: the one stored key holds five preferences."""
    util = (STATIC / "js" / "util.js").read_text(encoding="utf-8")
    assert util.count("localStorage.setItem") == 1
    assert "JSON.stringify({ mode, singleKeys, whyOpen, source, introSeen })" in util
    for f in JS:
        src = f.read_text(encoding="utf-8")
        assert "sessionStorage" not in src and "indexedDB" not in src and "document.cookie" not in src, f.name
        if f.name != "util.js":
            assert "localStorage." not in src, f.name


def test_every_file_the_page_loads_is_served_with_its_type(srv):
    page = (STATIC / "index.html").read_text(encoding="utf-8")
    m = _Markup()
    m.feed(page)
    wanted = set(m.urls)
    for f in JS:   # module imports are relative: "./x.js"
        for rel in re.findall(r"from \"\./([\w.-]+\.js)\"", f.read_text(encoding="utf-8")):
            wanted.add(f"/static/js/{rel}")
    assert "/static/js/inbox.js" in wanted and "/static/css/app.css" in wanted
    types = {".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8"}
    for url in sorted(wanted):
        status, headers, _ = get(srv, url, token=False)
        assert status == 200, url
        assert headers["Content-Type"] == types[Path(url).suffix], url


def test_meta_says_where_each_issue_type_goes(srv):
    status, _, raw = get(srv, "/api/meta")
    meta = json.loads(raw)
    tax = taxonomy()
    assert status == 200
    assert set(meta["subcategories"]) == set(tax.subcategories)
    for key, s in meta["subcategories"].items():
        assert s["team"] == tax.subcategories[key].team and s["team"] in meta["teams"]
        assert s["default_priority"] == tax.subcategories[key].default_priority
    assert meta["subcategories"]["app_bug"]["team"] == "tech"     # a subcategory's own team wins
    assert meta["priority_rules"] == thresholds()["priority"]
