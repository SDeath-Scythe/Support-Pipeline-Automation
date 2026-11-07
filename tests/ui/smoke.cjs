#!/usr/bin/env node
// Smoke test of the viewer in a real browser (Chromium through Playwright).
//
//   node tests/ui/smoke.cjs                      run every pass, print a pass/fail list
//   node tests/ui/smoke.cjs --screens <dir>      also save screenshots there
//   node tests/ui/smoke.cjs --pass desk-light    run one pass (desk-light, desk-dark, phone-light, phone-dark,
//                                                fresh-clone)
//   node tests/ui/smoke.cjs --pass fresh-clone --demo docs/demo
//                                                retake the README screenshots (docs/demo/*.png)
//
// Each of the first four passes starts its own viewer (python app/server.py) with no API key in its
// environment, PIPELINE_MODE=off (no model is ever called: a pasted ticket goes straight to a person) and
// a fresh decision log in a temporary folder, then drives the agent inbox and the "كيف يشتغل" mode on
// the committed final run (saved/test2/final).
//
// The fresh-clone pass starts the viewer as a fresh clone would: no key, no PIPELINE_MODE, no LLM_BACKEND
// (so the viewer's default, the API) and no claude CLI. Live runs are then off and the page says so. It
// pastes no ticket, and the browser refuses /api/stream anyway, so no model can be reached. It looks at
// the first visit, decides all 80 tickets through the page (edits, a take-over, a correction, the rest
// approved or forwarded) for the session summary, and with --demo saves the screenshots of docs/demo/.
// A few of its checks feed the page a changed /api/meta or run file through a browser route (a cache-only
// viewer, a run with one escalation); the server itself is never changed. Since the 5 Nov review the
// server gives the committed run (made on 30 Oct) the account_risk flag as run.py does now, so the six
// blocked-account and SIM-change tickets are «تحتاج تأكيد» and the tab counts are 15 / 6 / 59.
//
// Since 5 Nov the inbox is calmer: «ليش؟» is a drawer, closed until the agent opens it; the queue head is
// the counter and its bar; a row is its priority, id and text (its status is in its name); the ticket has
// one summary line, its facts in one line under the message, a short checks line, and reasons only after
// an edit, a correction or a take-over. The checks marked «5 Nov calm» follow those defaults. The checks
// marked «5 Nov review» follow the review of that change: «ليش؟» takes its own column over 1000 px (a drawer
// over the ticket only at 721–1000 px), the tick sits under the draft, a take-over once armed is the one
// obvious action, the tips are real elements (a tap pins them, Escape hides them), and the phone's ticket
// screen keeps the header to one row.
//
// Servers are stopped in a finally block. Exit code 0 only if every check passed.

"use strict";

const { chromium } = require("playwright");
const { spawn } = require("child_process");
const fs = require("fs");
const http = require("http");
const os = require("os");
const path = require("path");

const ROOT = path.resolve(__dirname, "..", "..");
const PYTHON = process.env.PYTHON || "python";
const RUN = "saved/test2/final";
const EXPECT = { flagged: 15, escalated: 6, drafted: 59, total: 80, type: "78/80", priority: "79/80" };
const SECRET_ASK = " دزلنا الرمز اللي وصلك";
const LIVE_NO_KEY = "ماكو مفتاح API";   // «كيف يشتغل»'s cause when there is no key (labels.js LIVE_CAUSE_AR)

const args = process.argv.slice(2);
const argVal = (name) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : null; };
const SCREENS = argVal("--screens");
const DEMO = argVal("--demo");
const ONLY = argVal("--pass");
if (SCREENS) fs.mkdirSync(SCREENS, { recursive: true });
if (DEMO) fs.mkdirSync(DEMO, { recursive: true });

const PASSES = [
  { name: "desk-light", viewport: { width: 1366, height: 850 }, scheme: "light", phone: false },
  { name: "desk-dark", viewport: { width: 1366, height: 850 }, scheme: "dark", phone: false },
  { name: "phone-light", viewport: { width: 360, height: 780 }, scheme: "light", phone: true },
  { name: "phone-dark", viewport: { width: 360, height: 780 }, scheme: "dark", phone: true },
  // The README screenshots: 1280 × 800, and 390 × 844 for the phone.
  { name: "fresh-clone", viewport: { width: 1280, height: 800 }, phoneViewport: { width: 390, height: 844 }, fresh: true },
].filter((p) => !ONLY || p.name === ONLY);

const results = [];   // {pass, name, ok, detail}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// --- the server ---

function get(url) {
  return new Promise((resolve) => {
    const req = http.get(url, (res) => { res.resume(); resolve(res.statusCode); });
    req.on("error", () => resolve(0));
    req.setTimeout(2000, () => { req.destroy(); resolve(0); });
  });
}

/** fresh: start it as a fresh clone would (no PIPELINE_MODE, no LLM_BACKEND, no claude CLI), else with
 *  the kill switch on (PIPELINE_MODE=off). Never with a key. */
async function startServer({ fresh = false } = {}) {
  for (let attempt = 0; attempt < 5; attempt++) {
    const port = 20000 + Math.floor(Math.random() * 30000);
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "viewer-smoke-"));
    const decisions = path.join(dir, "decisions.jsonl");
    const env = { ...process.env, PIPELINE_MODE: "off", PORT: String(port), DECISIONS_FILE: decisions };
    if (fresh) {
      delete env.PIPELINE_MODE;
      delete env.LLM_BACKEND;
      env.CLAUDE_BIN = "/nonexistent/claude";
    }
    // No key reaches the viewer, so even a broken kill switch could not call the API. No real-data
    // mode or candidate flags either: this runs on the committed synthetic run with today's defaults.
    for (const k of ["SUPPORT_PIPELINE_API_KEY", "ANTHROPIC_API_KEY", "REAL_DATA", "PIPELINE_FIXES",
      "LLM_CACHE_ONLY", "LLM_CACHE_DIR", "LLM_PROFILE"]) delete env[k];
    const child = spawn(PYTHON, ["app/server.py"], { cwd: ROOT, env, stdio: ["ignore", "pipe", "pipe"] });
    let log = "";
    child.stdout.on("data", (d) => { log += d; });
    child.stderr.on("data", (d) => { log += d; });
    let exited = false;
    child.on("exit", () => { exited = true; });
    const base = `http://127.0.0.1:${port}/`;
    for (let i = 0; i < 100 && !exited; i++) {
      if ((await get(base)) === 200) return { port, base, child, decisions, dir, log: () => log };
      await sleep(100);
    }
    stopServer({ child, dir });
    if (!exited) throw new Error(`the viewer did not answer on port ${port}:\n${log}`);
  }
  throw new Error("the viewer would not start (five ports tried)");
}

async function stopServer(srv) {
  if (!srv?.child) return;
  const { child } = srv;
  if (child.exitCode === null && child.signalCode === null) {
    const gone = new Promise((r) => child.once("exit", r));
    child.kill("SIGTERM");
    await Promise.race([gone, sleep(3000)]);
    if (child.exitCode === null && child.signalCode === null) child.kill("SIGKILL");
  }
  try { fs.rmSync(srv.dir, { recursive: true, force: true }); } catch { /* temp folder */ }
}

function readDecisions(file) {
  try { return fs.readFileSync(file, "utf8").split("\n").filter(Boolean).map((l) => JSON.parse(l)); } catch { return []; }
}

async function waitUntil(fn, ms = 5000, what = "condition") {
  const end = Date.now() + ms;
  for (;;) {
    const v = await fn();
    if (v) return v;
    if (Date.now() > end) throw new Error(`timed out waiting for ${what}`);
    await sleep(50);
  }
}

// --- one pass ---

async function runPass(browser, pass) {
  const srv = await startServer();
  const host = `127.0.0.1:${srv.port}`;
  const problems = [];       // console errors, CSP violations, foreign requests: checked at the end
  let allowRefusals = 0;     // console lines Chromium prints for a refusal the test asked for itself
  const check = (name, ok, detail = "") => results.push({ pass: pass.name, name, ok: !!ok, detail: ok ? "" : String(detail) });
  const shot = async (page, name) => { if (SCREENS) await page.screenshot({ path: path.join(SCREENS, `${pass.name}-${name}.png`) }); };

  const ctx = await browser.newContext({ viewport: pass.viewport, colorScheme: pass.scheme, hasTouch: pass.phone, isMobile: false });
  async function watch(page, label) {
    page.on("console", (m) => {
      if (m.type() !== "error" && m.type() !== "warning") return;
      if (allowRefusals > 0 && /Failed to load resource: the server responded with a status of (400|409|413)/.test(m.text())) { allowRefusals--; return; }
      problems.push(`${label} console ${m.type()}: ${m.text()}`);
    });
    page.on("pageerror", (e) => problems.push(`${label} page error: ${e.message}`));
    page.on("request", (r) => {
      const u = r.url();
      if (u.startsWith("data:")) return;
      if (new URL(u).host !== host) problems.push(`${label} request to another host: ${u}`);
    });
    await page.addInitScript(() => {
      window.__csp = [];
      window.__statusN = 0;   // how many messages the status region has shown (a decision's toast is one)
      document.addEventListener("securitypolicyviolation", (e) => window.__csp.push(`${e.violatedDirective} ${e.blockedURI}`));
      document.addEventListener("DOMContentLoaded", () => new MutationObserver(() => { window.__statusN++; })
        .observe(document.getElementById("status"), { childList: true, subtree: true, characterData: true }));
    });
  }
  async function cspOf(page, label) {
    const v = await page.evaluate(() => window.__csp || []).catch(() => []);
    for (const x of v) problems.push(`${label} CSP violation: ${x}`);
  }

  const page = await ctx.newPage();
  await watch(page, "inbox");
  const selected = () => page.evaluate(() => document.querySelector('#queueList [aria-selected="true"]')?.dataset.key || null);
  const text = (sel) => page.locator(sel).first().textContent({ timeout: 2000 }).catch(() => "");
  const decisions = () => readDecisions(srv.decisions);
  const statusN = () => page.evaluate(() => window.__statusN || 0);
  /** Do something that records one decision; return it once it is in the log AND the page has shown
   *  its toast (so the next key press reaches the page's new state, not the old one). */
  const act = async (fn, what) => {
    const n0 = decisions().length;
    const s0 = await statusN();
    await fn();
    await waitUntil(() => decisions().length > n0, 5000, what);
    const d = decisions().at(-1);
    const shown = d.ticket_id.replace(/^live-\d{14}-/, "live-");   // a live run's id is shown short (T11)
    await waitUntil(async () => (await statusN()) > s0 && (await text("#status")).includes(shown), 5000, `the page to show ${what}`);
    return d;
  };
  const approveKey = () => (pass.phone ? page.click("#approveBtn") : page.keyboard.press("Control+Enter"));
  /** «كيف يشتغل»: on a phone's ticket screen the mode switch is on the queue screen (5 Nov review). */
  const toProcess = async () => {
    if (pass.phone && await page.evaluate(() => document.body.dataset.screen === "ticket")) await page.locator("#agentMain .back-btn").first().click();
    await page.click("#modeProcess");
  };
  const noHScroll = async (where) => {
    const [sw, iw] = await page.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth]);
    check(`no horizontal scroll at ${pass.viewport.width} px (${where})`, sw <= iw, `scrollWidth ${sw} > ${iw}`);
  };
  /** Open the first ticket of a tab: keys 1-4 on a desktop, a tap on the tab and the row on a phone. */
  async function openTab(tab) {
    const n = { flagged: "1", escalated: "2", drafted: "3", done: "4" }[tab];
    if (!pass.phone) {
      await page.keyboard.press(n);
      await waitUntil(() => page.evaluate((t) => document.getElementById(`tab-${t}`)?.getAttribute("aria-selected") === "true", tab), 3000, `tab ${tab}`);
      return selected();
    }
    if (await page.evaluate(() => document.body.dataset.screen === "ticket")) await page.locator("#agentMain .back-btn").first().click();
    await page.click(`#tab-${tab}`);
    const first = page.locator("#queueList [role=option]").first();
    if (!(await first.count())) return null;
    const key = await first.getAttribute("data-key");
    await first.click();
    await waitUntil(() => page.evaluate(() => document.body.dataset.screen === "ticket"), 3000, "the ticket screen");
    return key;
  }

  let meta = null;
  let run = null;

  /** Polish 2: the first-visit card. Shown on a first visit, read once, reachable by keyboard; «فهمت»
   *  hides it for good. On a phone it sits above the queue, so it never moves the ticket's action bar. */
  async function introChecks() {
    const where = await page.evaluate(() => {
      const c = document.getElementById("intro");
      const live = c.closest("[aria-live], [role=status], [role=alert], [role=log]");
      return { parent: c.parentElement.id, first: c.parentElement.firstElementChild === c, live: !!live,
        name: document.getElementById(c.getAttribute("aria-labelledby"))?.textContent,
        tabs: [...c.querySelectorAll("dt")].map((d) => d.textContent.trim()) };
    });
    check(`first visit: the intro card is shown ${pass.phone ? "above the queue" : "above the ticket"}, named and not a live region`,
      (await page.isVisible("#intro")) && where.parent === (pass.phone ? "agentNav" : "main") && where.first && !where.live
      && where.name === "أول مرة هنا؟", JSON.stringify(where));
    check("the intro explains the three working tabs in the tabs' own words and order (J8)", where.tabs.join("|") === "تحتاج تأكيد|متصعّدة|جاهزة"
      && (await text("#intro")).includes("ما ينرسل شي للزبون بدونك"), where.tabs.join("|"));
    // 5 Nov calm: the card is the sentence, the three-line legend and «فهمت»; its heading names it for a
    // screen reader only.
    const shape = await page.evaluate(() => {
      const c = document.getElementById("intro");
      return { kids: [...c.children].map((n) => n.tagName + (n.offsetWidth > 1 ? "" : "(hidden)")).join(","), rows: c.querySelectorAll("dd").length };
    });
    check("5 Nov calm: the intro is the sentence and the three-line legend (its heading for a screen reader only)",
      shape.kids === "H2(hidden),P,DL,BUTTON" && shape.rows === 3, JSON.stringify(shape));
    if (pass.phone) {
      await noHScroll("queue screen with the intro");
      // Opening a ticket: the card stays with the queue; the ticket screen and its action bar are as always.
      await page.locator("#queueList [role=option]").first().click();
      await waitUntil(() => page.evaluate(() => document.body.dataset.screen === "ticket"), 3000, "the ticket screen");
      const bar = await page.evaluate(() => [document.getElementById("actionBar").getBoundingClientRect().bottom, innerHeight,
        document.getElementById("intro").getBoundingClientRect().height]);
      check("phone: the intro does not move the ticket's action bar", Math.abs(bar[0] - bar[1]) <= 1 && bar[2] === 0, JSON.stringify(bar));
      await page.locator("#agentMain .back-btn").first().click();
      await page.focus("#helpBtn");   // the last control of the header: the card's button comes next
    } else {
      const node = await page.evaluateHandle(() => document.getElementById("intro"));
      await page.evaluate(() => document.activeElement?.blur());
      await page.keyboard.press("j");
      await page.keyboard.press("j");
      await sleep(150);
      check("the intro is drawn once (the same node after two ticket changes)", await page.evaluate((n) => n === document.getElementById("intro") && n.isConnected, node));
      await page.focus(".skip");
      await page.keyboard.press("Enter");   // the skip link lands on the ticket pane, the card first
    }
    await page.keyboard.press("Tab");
    check("the intro's «فهمت» is the next stop by keyboard", (await page.evaluate(() => document.activeElement?.id)) === "introOk",
      await page.evaluate(() => document.activeElement?.id || document.activeElement?.tagName));
    await shot(page, "first-visit");
    await page.keyboard.press("Enter");
    await sleep(100);
    const after = await page.evaluate(() => ({ hidden: document.getElementById("intro").hidden, active: document.activeElement?.id || "",
      saved: JSON.parse(localStorage.getItem("support-viewer-prefs-v2") || "{}").introSeen }));
    check("«فهمت» hides the card, remembers it, and focus goes on to the work", after.hidden && after.saved === true
      && (pass.phone ? after.active.startsWith("opt-") : after.active === "ticketTitle"), JSON.stringify(after));
  }

  // --- 14. the 1 Nov review fixes (each check names its finding) ---

  async function freshPage(label, setup = null) {
    const p = await ctx.newPage();
    await watch(p, label);
    if (setup) await setup(p);
    await p.goto(srv.base);
    await p.waitForSelector("#ticketTitle", { state: "attached", timeout: 15000 });
    await sleep(200);
    return p;
  }
  const t = (p, sel) => p.locator(sel).first().textContent({ timeout: 2000 }).catch(() => "");
  const active = (p) => p.evaluate(() => { const a = document.activeElement; return a ? (a.id || a.className || a.tagName) : null; });
  const decidedIds = () => new Set(decisions().filter((d) => d.run === RUN).map((d) => d.ticket_id));
  /** Open a ticket by id (desktop): the tab it is in, then its row. */
  async function openId(p, key) {
    for (const k of ["1", "2", "3", "4"]) {
      await p.evaluate(() => document.activeElement?.blur());
      await p.keyboard.press(k);
      await sleep(60);
      const row = p.locator(`#queueList [data-key="${key}"]`);
      if (await row.count()) { await row.click(); await sleep(120); return; }
    }
    throw new Error(`no row for ${key}`);
  }
  /** The next ready ticket nobody decided yet. */
  async function openFreshDraft(p, skip = []) {
    const used = decidedIds();
    const id = run.tickets.map((r) => r.ticket.id).find((i) => !used.has(i) && !skip.includes(i)
      && run.tickets.find((r) => r.ticket.id === i).result.outcome === "drafted");
    await openId(p, id);
    return id;
  }
  async function typeAtEnd(p, text) {
    await p.focus("#draft");
    await p.evaluate(() => { const x = document.getElementById("draft"); x.setSelectionRange(x.value.length, x.value.length); });
    await p.keyboard.type(text);
  }
  const checksSettled = (p) => waitUntil(async () => !(await p.locator("#draftChecks .checks-state").count()), 5000, "the draft check");

  async function reviewFixes() {
    const p = await freshPage("fixes");
    const pAct = async (fn, what) => {   // like act(), on this page
      const n0 = decisions().length;
      await fn();
      await waitUntil(() => decisions().length > n0, 5000, what);
      await sleep(150);
      return decisions().at(-1);
    };

    // M4: the first ticket is the most urgent open one (a P1 escalation), not the first flagged P2.
    check("M4: the inbox opens on a P1 escalation", (await p.getAttribute("#tab-escalated", "aria-selected")) === "true"
      && /P1/.test(await t(p, "#titleChips .prio")), await t(p, "#titleChips"));
    // L6 / COPY-4: the agent's picker lists saved and batch runs only, in Arabic.
    const opts = await p.evaluate(() => [...document.querySelectorAll("#source option")].map((o) => [o.value, o.textContent]));
    check("L6: the agent's source picker has no experiment runs", opts.length >= 1 && opts.every(([v]) => !v.startsWith("exp/"))
      && opts.some(([v, l]) => v === RUN && l.includes("الاختبار النهائي")), JSON.stringify(opts));
    // A11Y-9, TYPE-1, A11Y-1
    const names = await p.evaluate(() => [...document.querySelectorAll(".step-btns button")].map((b) => b.getAttribute("aria-label")));
    check("A11Y-9: the previous / next buttons' names carry K and J", /K/.test(names[0]) && /J/.test(names[1]), JSON.stringify(names));
    // (Since 5 Nov the key letters are in the «?» sheet, not on the ticket's buttons.)
    const kf = await p.evaluate(() => getComputedStyle(document.querySelector("#sheet kbd.kbd-ar")).fontFamily);
    check("TYPE-1: an Arabic key letter uses IBM Plex Sans Arabic", /IBM Plex Sans Arabic/.test(kf.split(",")[0]), kf);
    const bh = await p.evaluate(() => [document.getElementById("actionBar").getBoundingClientRect().height, parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--bar-h"))]);
    check("A11Y-1: --bar-h follows the action bar's real height", Math.abs(bh[0] - bh[1]) <= 2, JSON.stringify(bh));
    // L7: Ctrl+Enter on an escalation says what to do.
    await p.evaluate(() => document.activeElement?.blur());
    await p.keyboard.press("Control+Enter");
    await waitUntil(async () => (await t(p, "#status")).includes("متصعّدة"), 2000, "the escalation hint").catch(() => {});
    check("L7: Ctrl+Enter on an escalation says to forward or take it", (await t(p, "#status")).includes("حوّلها"), await t(p, "#status"));
    // 5 Nov calm: «ليش؟» is closed until the agent opens it. W opens it with focus on its title, and the
    // choice is remembered; Escape closes it (A11Y-1) and focus goes back to its toggle (A11Y-2); its close
    // button does the same. 5 Nov review: over 1000 px it is a column of its own and covers nothing of the
    // ticket; between 721 and 1000 px it is a drawer over the ticket, closed by another ticket and on load.
    const why = () => p.evaluate(() => {
      const w = document.getElementById("why").getBoundingClientRect();
      const covers = [".customer-text", ".handoff", "#draft", "#actionBar", ".no-send", ".title-tools"].filter((sel) => {
        const n = document.querySelector(sel);
        if (!n) return false;
        const r = n.getBoundingClientRect();
        return Math.min(r.right, w.right) > Math.max(r.left, w.left) && Math.min(r.bottom, w.bottom) > Math.max(r.top, w.top);
      });
      return { shown: getComputedStyle(document.getElementById("why")).display !== "none",
        pos: getComputedStyle(document.getElementById("why")).position, active: document.activeElement?.id || document.activeElement?.className,
        expanded: document.querySelector("#agentMain .why-toggle")?.getAttribute("aria-expanded"), covers,
        saved: JSON.parse(localStorage.getItem("support-viewer-prefs-v2") || "{}").whyOpen };
    });
    const w0 = await why();
    const linkColour = await p.evaluate(() => getComputedStyle(document.querySelector("#agentMain .why-toggle")).color
      === getComputedStyle(document.querySelector("#agentMain .link-btn, .link-btn") || document.querySelector("#agentMain .why-toggle")).color);
    check("5 Nov calm: «ليش؟» is closed by default (5 Nov review: its button in the link colour)", !w0.shown && w0.expanded === "false" && linkColour, JSON.stringify(w0));
    await p.focus("#ticketTitle");
    await p.keyboard.press("w");
    await sleep(150);
    const w1 = await why();
    check("5 Nov review: W opens «ليش؟» as a column beside the ticket, covering none of it; focus on its title, the toggle expanded, the choice remembered",
      w1.shown && w1.pos !== "fixed" && !w1.covers.length && w1.active === "whyTitle" && w1.expanded === "true" && w1.saved === true, JSON.stringify(w1));
    {
      const sweep = {};
      for (const [w, h] of [[1100, 800], [1280, 800], [1366, 768]]) {
        await p.setViewportSize({ width: w, height: h });
        await sleep(200);
        const x = await why();
        sweep[w] = x.shown && x.pos !== "fixed" ? x.covers : `shown ${x.shown}, ${x.pos}`;
      }
      check("5 Nov review: open at 1100, 1280 and 1366 px, «ليش؟» covers none of the message, the team note, the draft, the action bar, the lock line or the ticket's buttons",
        Object.values(sweep).every((v) => Array.isArray(v) && !v.length), JSON.stringify(sweep));
      await p.setViewportSize({ width: 900, height: 800 });
      await sleep(200);
      const narrow = await why();
      await p.focus("#ticketTitle");
      await p.keyboard.press("w");
      await sleep(150);
      const drawer = await why();
      await p.evaluate(() => document.activeElement?.blur());
      await p.keyboard.press("j");
      await sleep(200);
      const afterJ = await why();
      await p.setViewportSize(pass.viewport);
      await sleep(200);
      const wideAgain = await why();
      check("5 Nov review: at 900 px «ليش؟» is not reopened over the ticket; W opens it as a drawer; another ticket closes it; back over 1000 px the agent's choice reopens it as a column",
        !narrow.shown && drawer.shown && drawer.pos === "fixed" && !afterJ.shown && afterJ.expanded === "false" && wideAgain.shown && !wideAgain.covers.length,
        JSON.stringify({ narrow, drawer, afterJ, wideAgain }));
      await p.focus("#whyTitle");
    }
    await p.keyboard.press("Escape");
    await sleep(150);
    const w2 = await why();
    check("A11Y-1 / A11Y-2: Escape closes the drawer and focus goes back to its toggle", !w2.shown && /why-toggle/.test(w2.active)
      && w2.saved === false, JSON.stringify(w2));
    await p.click("#agentMain .why-toggle");
    await sleep(150);
    await p.focus("#whyClose");
    await p.keyboard.press("Enter");
    await sleep(150);
    check("A11Y-2: closing «ليش؟» with its button moves focus to its toggle", /why-toggle/.test(await active(p)) && !(await why()).shown, await active(p));
    // v1 preferences saved «ليش؟» open for everyone (the old default): they are carried over without it.
    {
      const c1 = await browser.newContext({ viewport: pass.viewport, colorScheme: pass.scheme });
      const pv = await c1.newPage();
      await watch(pv, "v1-prefs");
      await pv.addInitScript(() => localStorage.setItem("support-viewer-prefs-v1",
        JSON.stringify({ mode: "agent", singleKeys: true, whyOpen: true, source: null, introSeen: true })));
      await pv.goto(srv.base);
      await pv.waitForSelector("#ticketTitle", { state: "attached", timeout: 15000 });
      await sleep(200);
      const v = await pv.evaluate(() => ({ why: getComputedStyle(document.getElementById("why")).display, intro: document.getElementById("intro").hidden }));
      check("5 Nov calm: old (v1) preferences keep the dismissed intro but not the auto-saved «ليش؟» open", v.why === "none" && v.intro, JSON.stringify(v));
      await cspOf(pv, "v1-prefs");
      await c1.close();
      // 5 Nov review: the agent's own «open» comes back on load only where it is a column (over 1000 px).
      const shownAt = async (vp) => {
        const c = await browser.newContext({ viewport: vp, colorScheme: pass.scheme });
        const pw = await c.newPage();
        await watch(pw, `why-${vp.width}`);
        await pw.addInitScript(() => localStorage.setItem("support-viewer-prefs-v2",
          JSON.stringify({ mode: "agent", singleKeys: true, whyOpen: true, source: null, introSeen: true })));
        await pw.goto(srv.base);
        await pw.waitForSelector("#ticketTitle", { state: "attached", timeout: 15000 });
        await sleep(200);
        const d = await pw.evaluate(() => getComputedStyle(document.getElementById("why")).display);
        await cspOf(pw, `why-${vp.width}`);
        await c.close();
        return d;
      };
      const at900 = await shownAt({ width: 900, height: 800 });
      const atWide = await shownAt(pass.viewport);
      check("5 Nov review: an «ليش؟» the agent left open comes back on load as a column over 1000 px, never as a drawer at 900 px",
        at900 === "none" && atWide !== "none", JSON.stringify({ at900, atWide }));
    }

    // H1: a correction to fraud turns the ticket into an escalation: no draft, forward to the fraud team.
    const h1 = await openFreshDraft(p);
    await p.click("#fixToggle");
    await p.selectOption("#fixSub", "suspected_scam");
    await sleep(200);
    check(`H1: correcting ${h1} to fraud removes the draft and offers forward`, (await p.locator("#draft").count()) === 0
      && (await t(p, "#forwardBtn")).includes("الاحتيال") && (await t(p, "#agentMain .callout-bad")).includes("احتمال احتيال"),
      `${await t(p, "#forwardBtn")} | ${await t(p, "#agentMain .callout-bad")}`);
    await p.click("text=رجّع اللي قاله النظام");
    await sleep(200);
    check("H1: undoing the correction brings the draft back", (await p.locator("#draft").count()) === 1);
    // H1: the first model's answer on a disagreement: an earlier tick no longer counts.
    const flagged = run.tickets.find((r) => r.result.flags?.includes("recheck_used_second") && r.result.recheck_alternative && !decidedIds().has(r.ticket.id))?.ticket.id;
    if (flagged) {
      await openId(p, flagged);
      await p.check("#ackBox");
      await p.check('#choiceBox input[value="first"]');
      await sleep(200);
      const ticked = await p.evaluate(() => document.getElementById("ackBox").checked);
      check(`H1: choosing the first model's type on ${flagged} clears the tick and names the draft`, !ticked
        && (await t(p, "#confirmBox")).includes("انكتبت لنوع ثاني") && (await p.getAttribute("#approveBtn", "aria-disabled")) === "true"
        && (await t(p, "#sumBox .summary-line")).includes((meta.teams[meta.subcategories[run.tickets.find((r) => r.ticket.id === flagged).result.recheck_alternative].team] || {}).label_ar || "?"),
      `${ticked} | ${await t(p, "#confirmBox")}`);
      // 5 Nov review: the first model's answer here is a SIM change, so choosing it asks for the identity
      // check first, the line at the top says why, and the one tick names it; back to the re-check's
      // type (login_otp) it goes again.
      const alt = run.tickets.find((r) => r.ticket.id === flagged).result.recheck_alternative;
      const items = await p.evaluate(() => [...document.querySelectorAll("#confirmBox li")].map((x) => x.textContent));
      const tickNow = await t(p, ".confirm-check");
      const lineNow = await t(p, "#whyLine");
      await p.check('#choiceBox input[value="second"]');
      await sleep(200);
      const afterBox = await t(p, "#confirmBox");
      check(`choosing «${alt}» on ${flagged}: the identity check first, its line on top and in the tick; gone again with the re-check's type`,
        meta.account_risk_types.includes(alt) && items[0] === "تأكد من هوية الزبون حسب الإجراءات" && items.some((x) => x.includes("انكتبت لنوع ثاني"))
        && tickNow === "تأكدت من هوية الزبون وراجعت باقي النقاط" && lineNow.startsWith("تحتاج تأكيد: حساب مقفول أو تبديل شريحة.")
        && !afterBox.includes("هوية") && !(await t(p, "#whyLine")).includes("هوية"),
        `${alt} | ${JSON.stringify(items)} | ${tickNow} | ${lineNow} | ${afterBox}`);
      // Polish 5: the refusal («أشّر على …») goes with its ticket.
      await p.evaluate(() => document.activeElement?.blur());
      await p.keyboard.press("Control+Enter");
      await waitUntil(async () => (await t(p, "#status")).includes("أشّر على"), 3000, "the refusal").catch(() => {});
      const shownBefore = await p.evaluate(() => document.getElementById("toast").classList.contains("is-shown"));
      await p.keyboard.press("j");
      await sleep(200);
      check("polish 5: the refusal goes when another ticket opens", shownBefore
        && !(await p.evaluate(() => document.getElementById("toast").classList.contains("is-shown"))) && !(await t(p, "#ticketTitle")).includes(flagged),
        `${shownBefore} | ${await t(p, "#status")}`);
    }

    // M2: a ticked promise is logged as an acknowledged warning (kinds only), and the tick says so.
    const m2 = await openFreshDraft(p);
    await typeAtEnd(p, " وراح ترجعلك فلوسك خلال يومين.");
    await p.waitForSelector("#ackBox", { timeout: 5000 });
    await checksSettled(p);
    const tick = await t(p, ".confirm-check");
    check("M2: the tick on a promise does not claim there is none", tick.includes("راجعت الوعد") && !tick.includes("ما توعد"), tick);
    await p.check("#ackBox");
    const d2 = await pAct(() => p.click("#approveBtn"), "the acknowledged approve");
    check(`M2: the decision on ${m2} logs warnings_acknowledged ["promise"]`, d2.ticket_id === m2 && d2.action === "edited"
      && JSON.stringify(d2.warnings_acknowledged) === '["promise"]', JSON.stringify(d2));

    // M1 / F3: undo brings the edit back; take-over always needs a second press.
    const m1 = await openFreshDraft(p);
    await typeAtEnd(p, " ونعتذر على التأخير.");
    await checksSettled(p);
    await pAct(() => p.keyboard.press("Control+Enter"), "the edited approve");
    await p.evaluate(() => document.activeElement?.blur());
    await pAct(() => p.keyboard.press("Control+z"), "the undo");
    await waitUntil(async () => (await t(p, "#ticketTitle")).includes(m1), 3000, "the undone ticket");
    check(`M1: after undo, ${m1} still has the agent's edit`, (await t(p, ".composer-label")).includes("معدّلة منك")
      && (await p.inputValue("#draft")).includes("ونعتذر على التأخير"), await t(p, ".composer-label"));
    const n1 = decisions().length;
    await p.evaluate(() => document.activeElement?.blur());
    await p.keyboard.press("t");
    await sleep(400);
    check("M1: one T on an edited draft records nothing yet", decisions().length === n1, decisions().at(-1)?.action);
    const tk1 = await p.evaluate(() => { const d = document.getElementById("reasonBox"); return { open: d.open, summary: d.querySelector("summary")?.textContent.trim(),
      focus: document.activeElement?.classList.contains("reason-chip") }; });
    check("5 Nov calm: the first T opens the reasons as «ليش استلمتها؟ (اختياري)», focus on the first", tk1.open && tk1.summary === "ليش استلمتها؟ (اختياري)" && tk1.focus,
      JSON.stringify(tk1));
    const tk = await pAct(() => p.keyboard.press("t"), "the take-over");
    check("M1: the second T records the take-over", tk.action === "took_over" && tk.ticket_id === m1, JSON.stringify(tk));
    // 5 Nov review: once armed, recording the take-over is the one obvious action (and Ctrl+Enter's); approve
    // is gone from the bar. «رجوع» or Esc goes back, and a reason picked meanwhile goes with it.
    {
      const ta = await openFreshDraft(p);
      const n2 = decisions().length;
      await p.evaluate(() => document.activeElement?.blur());
      await p.keyboard.press("t");
      await sleep(200);
      const armedBar = await p.evaluate(() => ({ primary: document.querySelector("#actionBar .btn-primary")?.id, approve: !!document.getElementById("approveBtn"),
        back: !!document.getElementById("takeBack"), kbd: document.querySelector("#takeBtn kbd")?.textContent || "" }));
      await p.locator(".reason-chip").first().click();
      await p.keyboard.press("Escape");
      await sleep(200);
      const back = await p.evaluate(() => ({ approve: !!document.getElementById("approveBtn"), primary: document.querySelector("#actionBar .btn-primary")?.id,
        reasons: document.getElementById("reasonBox").tagName, active: document.activeElement?.id }));
      await p.evaluate(() => document.activeElement?.blur());
      await p.keyboard.press("t");
      await sleep(200);
      await p.locator(".reason-chip").nth(1).click();
      const tk2 = await pAct(() => p.keyboard.press("Control+Enter"), "the armed take-over by Ctrl+Enter");
      check(`5 Nov review: after T on ${ta}, «سجّل: استلمتها» is the primary (Ctrl+Enter) and approve is gone; Esc goes back with no reason left; Ctrl+Enter then records the take-over, never an approval`,
        armedBar.primary === "takeBtn" && !armedBar.approve && armedBar.back && /Enter/.test(armedBar.kbd)
        && back.approve && back.primary === "approveBtn" && back.reasons === "DIV" && back.active === "takeBtn"
        && decisions().length === n2 + 1 && tk2.action === "took_over" && tk2.ticket_id === ta
        && JSON.stringify(tk2.reason_codes) === JSON.stringify([meta.reason_codes[1]]), JSON.stringify({ armedBar, back, tk2 }));
    }
    // A11Y-2: closing the toast returns focus to the page, not <body>.
    await p.focus("#toastClose");
    await p.keyboard.press("Enter");
    await sleep(450);
    check("A11Y-2: closing the toast keeps focus in the page", (await active(p)) !== "BODY", await active(p));

    // M3: time adds up over visits (J away and K back), with the number of visits.
    const m3 = await openFreshDraft(p);
    await p.focus("#ticketTitle");
    await sleep(1300);
    await p.keyboard.press("j");
    await sleep(300);
    await p.keyboard.press("k");
    await sleep(200);
    const d3 = await pAct(() => p.keyboard.press("Control+Enter"), "the timed approve");
    check(`M3: seconds add up over visits (${d3.ticket_id}: ${d3.seconds} s, ${d3.visits} visits)`, d3.ticket_id === m3 && d3.seconds >= 1.2 && d3.visits === 2, JSON.stringify(d3));

    // 5 Nov review: where a blocking finding overlaps a warning (a card number is also an unknown number),
    // the phrase that stops the approval is the one drawn, whole.
    {
      const bl = await openFreshDraft(p);
      await typeAtEnd(p, " رقم بطاقتك 4111 1111 1111 1111");
      await p.waitForSelector("#draftChecks .check-item.is-blocking", { timeout: 6000 }).catch(() => {});
      await checksSettled(p);
      const marks = await p.evaluate(() => [...document.querySelectorAll(".composer-mirror mark.finding")].map((m) => [m.className, m.textContent]));
      check(`5 Nov review: on ${bl}, a card number typed into the draft is highlighted as blocking, whole, not as a warning`,
        marks.some(([c, x]) => c.includes("is-blocking") && /4111\s1111\s1111\s1111/.test(x))
        && !marks.some(([c, x]) => c.includes("is-warn") && x.includes("4111")) && (await p.getAttribute("#approveBtn", "aria-disabled")) === "true",
        JSON.stringify(marks));
      await p.click("text=رجّع المسودة الأصلية");
      await waitUntil(async () => (await p.getAttribute("#approveBtn", "aria-disabled")) === null, 4000, "the draft restored").catch(() => {});
    }

    // RTL-1: a phone written in spaced groups reads in its written order in the draft.
    if (!decidedIds().has("t2-0053")) {
      await openId(p, "t2-0053");
      const order = await p.evaluate(() => {
        const m = document.querySelector(".composer-mirror");
        const x = (needle) => { const w = document.createTreeWalker(m, NodeFilter.SHOW_TEXT); let n; while ((n = w.nextNode())) { const i = n.data.indexOf(needle); if (i >= 0) { const r = document.createRange(); r.setStart(n, i); r.setEnd(n, i + 4); return r.getBoundingClientRect().left; } } return null; };
        return [x("0791"), x("0226"), document.getElementById("draft").value.includes("0791\u00a0079\u00a00226")];
      });
      check("RTL-1: «0791 079 0226» keeps its order in the draft", order[0] != null && order[0] < order[1] && order[2], JSON.stringify(order));
    }

    // SEC-1: a check still running when Ctrl+Enter is pressed: nothing typed after it gets approved.
    await p.route("**/api/check", async (route) => { await sleep(1200); await route.continue().catch(() => {}); });
    const s1 = await openFreshDraft(p);
    await typeAtEnd(p, " شكراً");
    await p.keyboard.press("Control+Enter");
    await sleep(100);
    await p.keyboard.insertText(" دزلنا الرمز اللي وصلك");
    await waitUntil(() => decidedIds().has(s1), 6000, "the raced approve").catch(() => {});
    await p.unroute("**/api/check");
    if (decidedIds().has(s1)) {
      await openId(p, s1);
      check("SEC-1: text typed while the check ran is not in the approved reply", !(await t(p, ".decided-text")).includes("دزلنا"), await t(p, ".decided-text"));
    } else {
      check("SEC-1: text typed while the check ran is not in the approved reply", true);
    }
    // SEC-1 (server) and F8: the log refuses an approval that asks for the code, and a second decision.
    const free = run.tickets.filter((r) => r.result.outcome !== "escalated").map((r) => r.ticket.id).filter((i) => !decidedIds().has(i)).at(-1);
    const post = (body) => p.evaluate(async (b) => {
      const token = document.querySelector('meta[name="viewer-token"]').content;
      const r = await fetch("/api/decision", { method: "POST", headers: { "X-Viewer-Token": token, "Content-Type": "application/json" }, body: JSON.stringify(b) });
      return [r.status, await r.json()];
    }, body);
    const base = { run: RUN, ticket_id: free, pipeline_outcome: "drafted", flags: [], reason_codes: [], seconds: 9, corrected: {} };
    allowRefusals = 5;   // the refusals below (409 and 400) are asked for
    const [st1] = await post({ ...base, action: "edited", final_text: "هلا، دزلنا الرمز اللي وصلك" });
    const [st2] = await post({ ...base, action: "took_over" });
    const [st3, j3] = await post({ ...base, action: "took_over" });
    check("SEC-1 / F8: the server refuses a secret request (409) and a second decision on one ticket (409)", st1 === 409 && st2 === 200 && st3 === 409 && j3.conflict === "decided", `${st1} ${st2} ${st3}`);
    // T03 (user tests, 7 Nov): a ticket the run does not have, a draft it did not serve, and an escalation
    // approved by a hand-made request are refused; nothing is logged.
    const esc = run.tickets.find((r) => r.result.outcome === "escalated" && !decidedIds().has(r.ticket.id))?.ticket.id;
    const nLog = decisions().length;
    const [st4, j4] = await post({ ...base, ticket_id: "t2-9999", action: "took_over" });
    const [st5, j5] = await post({ ...base, ticket_id: esc, action: "edited", final_text: "هلا بيك" });
    const [st6, j6] = await post({ ...base, ticket_id: free, action: "took_over", draft_text: "مسودة ما انعرضت" });
    check("T03: the server refuses an unknown ticket (400), an approved escalation (409) and a draft it did not serve (400)",
      st4 === 400 && j4.field === "ticket_id" && st5 === 409 && j5.conflict === "escalated" && st6 === 400 && j6.field === "draft_text"
      && decisions().length === nLog, `${st4} ${j4.field} ${st5} ${j5.conflict} ${st6} ${j6.field}`);
    await sleep(100);
    allowRefusals = 0;

    // A11Y-5 / L7: with single keys off, «?» does nothing and the single-key hints go.
    await p.click("#helpBtn");
    await p.uncheck("#singleKeys");
    await p.click("#sheetClose");
    await p.evaluate(() => document.activeElement?.blur());
    await p.keyboard.press("Shift+Slash");
    await sleep(200);
    const sheetOpen = await p.evaluate(() => document.getElementById("sheet").open);
    const hints = await p.evaluate(() => [...document.querySelectorAll(".kbd-single")].filter((h) => h.offsetParent).length);
    check("A11Y-5: with single keys off, «?» does not open the sheet and the hints are hidden", !sheetOpen && hints === 0, `open=${sheetOpen} hints=${hints}`);
    await p.click("#helpBtn");
    await p.check("#singleKeys");
    await p.click("#sheetClose");

    // SEC-2 / A11Y-3 / L2: the pasted ticket: no autocomplete or spellcheck, cleared on cancel; after
    // «شغّلها» focus is on the new ticket and its end is announced; with no team, take over is the action.
    const na = await p.evaluate(() => { const x = document.getElementById("newText"); return [x.getAttribute("autocomplete"), x.spellcheck]; });
    await p.click("#newTicket");
    await p.fill("#newText", "رقمي 07701234567");
    await p.click("#newCancel");
    await p.click("#newTicket");
    check("SEC-2: the new-ticket box has no autocomplete or spellcheck and forgets cancelled text", na[0] === "off" && na[1] === false
      && (await p.inputValue("#newText")) === "", `${JSON.stringify(na)} «${await p.inputValue("#newText")}»`);
    await p.fill("#newText", "حولت خمسين الف لاخوي وما وصلت");
    await p.click("#newRun");
    await p.waitForFunction(() => document.querySelector('[id^="opt-live-"]') && !document.querySelector('[id^="opt-live-"].st-running'), null, { timeout: 15000 });
    await sleep(300);
    // T11: the server names the run (live-<UTC time>-<6 hex>); the page shows «live-» and the 6 hex digits.
    const liveKey = await p.evaluate(() => document.querySelector('[id^="opt-live-"]').dataset.key);
    const liveShown = await t(p, `[id="opt-${liveKey}"] .row-id`);
    check("T11: a pasted ticket has the server's id, shown short in its row and title", /^live-\d{14}-[0-9a-f]{6}$/.test(liveKey)
      && liveShown === `live-${liveKey.slice(-6)}` && (await t(p, "#ticketTitle")).includes(liveShown), `${liveKey} | ${liveShown}`);
    check("A11Y-3: after «شغّلها» focus is on the new ticket and its end is announced", (await active(p)) === "ticketTitle"
      && (await t(p, "#status")).includes("خلصت المعالجة"), `${await active(p)} | ${await t(p, "#status")}`);
    check("L2: a ticket with no team: take over is the main action and the summary says nothing read it",
      (await p.getAttribute("#takeBtn", "class")).includes("btn-primary") && (await t(p, "#sumBox")).includes("ما نعرف"), await t(p, "#sumBox"));
    await p.keyboard.press("f");
    await sleep(200);
    check("L2: forwarding a ticket with no team asks for the team first", (await active(p)) === "fixTeam", await active(p));

    // «كيف يشتغل»: the stage map, the scale, the legend, the skipped stage, the rows, the replay.
    await p.click("#modeProcess");
    await p.waitForSelector("#ovTitle", { timeout: 10000 });
    check("L5: the overview starts with the 8-step stage map", (await p.locator(".stage-strip .ss").count()) === 8);
    check("A11Y-7: the outcome bar has a legend with the counts", (await t(p, ".bar-legend")).includes(String(EXPECT.flagged)), await t(p, ".bar-legend"));
    check("A11Y-11: overview rows are not tab stops; the id is a button", (await p.locator("table.grid tbody tr[tabindex]").count()) === 0
      && (await p.locator("table.grid tbody .row-open").count()) === EXPECT.total);
    await p.locator("table.grid tbody tr", { hasText: "t2-0009" }).first().locator(".row-open").click();
    await sleep(300);
    await p.click("#modeAgent");   // F4: leave mid-replay, come back
    await sleep(1500);
    await p.click("#modeProcess");
    await p.waitForSelector("#pResult .result", { timeout: 5000 }).catch(() => {});
    const stages = await p.evaluate(() => [...document.querySelectorAll(".stage")].map((x) => x.className));
    check("F4: a replay cut short by a mode switch is drawn whole on return", stages.length === 7 && stages.every((c) => /done|skipped|error/.test(c))
      && (await p.locator("#pResult .result").count()) === 1, stages.join(","));
    const ticks = await p.evaluate(() => {
      const tr = document.querySelector(".scale .track").getBoundingClientRect();
      return [...document.querySelectorAll(".scale .ticks span")].map((x) => { const b = x.getBoundingClientRect(); return [x.textContent, (b.left + b.width / 2 - tr.left) / tr.width]; });
    });
    const six = ticks.find(([x]) => x === String(meta.thresholds.recheck_from));
    check("PROC-1: the 0.6 label sits at 0.6 of the scale", six && Math.abs(six[1] - meta.thresholds.recheck_from) < 0.02, JSON.stringify(ticks));
    await p.locator("#pList .prow", { hasText: "t2-0001" }).first().click();
    await p.waitForSelector("#pResult .result", { timeout: 8000 });
    const op = await p.evaluate(() => [...document.querySelectorAll(".stage.skipped")].map((x) => getComputedStyle(x).opacity));
    check("A11Y-4: a skipped stage keeps full contrast", op.length > 0 && op.every((o) => o === "1"), op.join(","));
    await p.click("#modeAgent");
    await cspOf(p, "fixes");
    await p.close();

    // SEC-3 / SEC-4: a run file with a direction override in the text and a flag named "constructor".
    const p2 = await freshPage("crafted", (x) => x.route(`**/api/run?name=${encodeURIComponent(RUN)}`, async (route) => {
      const r = await route.fetch();
      const j = await r.json();
      j.tickets[1].ticket.text = "المبلغ \u202E0005 DQI\u202C ما وصل";
      j.tickets.find((x2) => x2.result.outcome === "escalated").result.flags.push("constructor", "__proto__");
      await route.fulfill({ response: r, json: j });
    }));
    await openId(p2, run.tickets[1].ticket.id);
    const ct = await p2.evaluate(() => document.querySelector(".customer-text").textContent);
    check("SEC-3: direction controls are dropped from the customer text, and the page says so", !/[\u202A-\u202E\u2066-\u2069]/.test(ct)
      && (await t(p2, ".customer")).includes("اتجاه"), JSON.stringify(ct));
    check("SEC-4: a flag named «constructor» does not break the inbox", (await p2.locator("#queueList [role=option]").count()) > 0);
    await p2.close();
  }

  async function phoneFixes() {
    const p = await freshPage("phone-fixes");
    if (await p.evaluate(() => document.body.dataset.screen === "ticket")) await p.locator("#agentMain .back-btn").first().click();
    check("A11Y-5: the shortcut sheet's button is shown on a phone", await p.isVisible("#helpBtn"));
    await p.focus(".skip");
    await p.keyboard.press("Enter");
    await sleep(150);
    check("A11Y-6: on the phone queue the skip link goes to the queue", /^opt-/.test(await active(p)) && (await p.locator("h1").count()) === 1, await active(p));
    await p.locator("#queueList [role=option]").first().click();
    await sleep(300);
    const bh = await p.evaluate(() => [document.getElementById("actionBar").getBoundingClientRect().height, parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--bar-h"))]);
    check("A11Y-1: --bar-h follows the phone action bar", Math.abs(bh[0] - bh[1]) <= 2, JSON.stringify(bh));
    await cspOf(p, "phone-fixes");
    await p.close();
  }

  try {
    // 1. The inbox opens on the final run, with the four tabs and their counts.
    await page.goto(srv.base);
    await page.waitForSelector("#ticketTitle", { state: "attached", timeout: 15000 });
    [meta, run] = await page.evaluate(async (name) => {
      const token = document.querySelector('meta[name="viewer-token"]').content;
      const j = (u) => fetch(u, { headers: { "X-Viewer-Token": token } }).then((r) => r.json());
      return Promise.all([j("/api/meta"), j(`/api/run?name=${encodeURIComponent(name)}`)]);
    }, RUN);
    check("opens on saved/test2/final", (await page.$eval("#source", (s) => s.value)) === RUN, await page.$eval("#source", (s) => s.value));
    const counts = await page.evaluate(() => Object.fromEntries(["flagged", "escalated", "drafted", "done"].map(
      (t) => [t, Number(document.querySelector(`#tab-${t} .tab-count`)?.textContent.replace(/\D/g, ""))])));
    const fromRun = { flagged: 0, escalated: 0, drafted: 0 };
    for (const r of run.tickets) fromRun[r.result.outcome]++;
    check(`tab counts 15 / 6 / 59 / 0 match the run (${JSON.stringify(counts)})`,
      counts.flagged === EXPECT.flagged && counts.escalated === EXPECT.escalated && counts.drafted === EXPECT.drafted && counts.done === 0
      && counts.flagged === fromRun.flagged && counts.escalated === fromRun.escalated && counts.drafted === fromRun.drafted, JSON.stringify({ counts, fromRun }));
    const tabWords = await page.evaluate(() => [...document.querySelectorAll("[role=tab] .tab-label")].map((x) => x.textContent));
    check("the four tabs: تحتاج تأكيد، متصعّدة، جاهزة، خلصت", tabWords.join("|") === "تحتاج تأكيد|متصعّدة|جاهزة|خلصت", tabWords.join("|"));
    check("counter «خلصت 0 من 80»", /خلصت\s*0\s*من\s*80/.test(await text("#queueTitle")), await text("#queueTitle"));
    // 5 Nov calm: the saved run is said once, in the source picker's own text (no pill); the picker has no
    // label on screen and keeps its name; the one lock line by the action bar says nothing is sent.
    const src = await page.evaluate(() => {
      const sel = document.getElementById("source");
      const lab = sel.labels?.[0];
      return { text: sel.selectedOptions[0]?.textContent || "", labelShown: [...(lab?.querySelectorAll("span") || [])].some((x) => x.offsetWidth > 1),
        pill: !!document.getElementById("savedNote"),
        // anywhere else in the header (the picker's options aside)
        elsewhere: [...document.querySelectorAll("header *")].filter((n) => !n.closest("select") && n.children.length === 0 && /محفوظ/.test(n.textContent)).length };
    });
    check("5 Nov calm: «تشغيل محفوظ» is said once, in the picker's text; the picker is named «المصدر» with no label on screen; no saved-run pill; the no-send line is shown",
      src.text.startsWith("تشغيل محفوظ: ") && (await page.getByRole("combobox", { name: "المصدر", exact: true }).count()) === 1
      && !src.labelShown && !src.pill && src.elsewhere === 0
      && (await text(".no-send")).includes("ما ينرسل شي للزبون تلقائياً"), JSON.stringify(src));
    // Polish 4, then 5 Nov calm: the head is the decided count and its bar; what the system did with the
    // run is in «كيف يشتغل» (step 10), and an urgent ticket in another tab is a dot on that tab (step 5).
    const head = await page.evaluate(() => [...document.querySelector(".queue-head").children].map((n) => n.className).join("|"));
    check("5 Nov calm: the queue head is «خلصت 0 من 80» and its bar only (no run note, no urgent sentence)",
      head === "queue-title|progress" && !(await page.locator("#agentQueue #runNote, #agentQueue .urgent-hint").count()), head);
    await introChecks();
    await shot(page, "inbox");
    if (pass.phone) await noHScroll("queue screen");
    const pageFits = () => page.evaluate(() => [document.scrollingElement.scrollHeight, innerHeight]);
    if (!pass.phone) {
      const [sh, ih] = await pageFits();
      check("agent mode: the page itself does not scroll, only its panes (J6)", sh <= ih, `${sh} > ${ih}`);
    }
    // 5 Nov calm: a row is its priority, its id and the customer's words. The tab says the status, so a row
    // says it in its name only (read first); the team is on the ticket.
    {
      const tabWord = await page.evaluate(() => document.querySelector("[role=tab][aria-selected=true] .tab-label").textContent);
      const rows = await page.locator("#queueList [role=option]").count();
      const named = await page.getByRole("option", { name: new RegExp(`^${tabWord}\\s*،`) }).count();
      const shown = await page.evaluate(() => [...document.querySelectorAll("#queueList [role=option]")].map((r) => ({
        team: r.querySelectorAll(".row-team").length, status: r.querySelectorAll(".row-status").length,
        word: !!r.querySelector(".sr-only .row-word"), pill: r.querySelectorAll(".prio").length,
        id: !!r.querySelector(".row-id"), text: !!r.querySelector(".row-text")?.textContent.trim() })));
      check(`5 Nov calm: each «${tabWord}» row shows its priority, id and words, no team or status word, and its name starts with «${tabWord}» (${rows} rows)`,
        rows > 0 && named === rows && shown.every((x) => !x.team && !x.status && x.word && x.pill === 1 && x.id && x.text),
        JSON.stringify({ rows, named, shown: shown.slice(0, 2) }));
    }

    // 2. No gold labels, model ids or marks anywhere in agent mode.
    {
      const models = Object.values(meta.models || {});
      const keys = Object.keys(meta.subcategories);
      const gold = Object.fromEntries(run.tickets.map((r) => [r.ticket.id, r.ticket]));
      const scan = async () => page.evaluate(() => ["agentNav", "agentMain", "whyBody", "banners", "toast"]
        .map((id) => document.getElementById(id)?.textContent || "").join("\n") + "\n" + document.querySelector("header").textContent);
      const badIn = (t, id) => {
        const hits = [];
        const word = (w) => new RegExp(`(^|[^A-Za-z0-9_])${w}([^A-Za-z0-9_]|$)`).test(t);
        for (const s of ["claude-", "✓", "✔", "✗", "✘", "difficulty", "edge_case", "review_reason", "generator_model", "dialect", "confidence", "tokens", "cost_usd"]) if (t.includes(s)) hits.push(s);
        for (const m of models) if (t.includes(m)) hits.push(m);
        for (const w of ["haiku", "sonnet", "opus", "backend", "baghdadi", "voice_note_style"]) if (word(w)) hits.push(w);
        for (const k of keys) if (word(k)) hits.push(k);
        const g = gold[id];
        if (g?.subcategory && word(g.subcategory)) hits.push(`gold ${g.subcategory}`);
        return [...new Set(hits)];
      };
      let seen = 0;
      const bad = [];
      for (const tab of ["flagged", "escalated", "drafted"]) {
        const ids = run.tickets.filter((r) => r.result.outcome === tab).map((r) => r.ticket.id);
        const limit = pass.name === "desk-light" ? ids.length : 3;   // every ticket once, a sample in the other passes
        await openTab(tab);
        for (let i = 0; i < limit; i++) {
          const id = await selected();
          const hits = badIn(await scan(), id);
          if (hits.length) bad.push(`${id}: ${hits.join(", ")}`);
          seen++;
          await page.keyboard.press("j");   // the next ticket (on a phone's ticket screen too)
          await sleep(20);
        }
      }
      check(`no gold labels, model ids or check marks in agent mode (${seen} tickets scanned)`, bad.length === 0, bad.slice(0, 5).join(" | "));
    }

    // 3. Approve with Ctrl+Enter (a tap on a phone): logged, focus moves to the next ticket.
    let k1;
    {
      k1 = await openTab("drafted");
      check(`ready ticket ${k1}: approve is enabled`, (await page.getAttribute("#approveBtn", "aria-disabled")) === null);
      // 5 Nov calm: what the system understood is one line, type · team; no grid of fields, no key chips
      // under the title; the pencil that corrects it is named.
      {
        const sum = await page.evaluate(() => ({ line: document.querySelector("#sumBox .summary-line").textContent.replace(/\s+/g, " ").trim(),
          dts: document.querySelectorAll("#sumBox dt").length, notes: [...document.querySelectorAll("#sumBox .summary-note")].map((n) => n.textContent),
          chips: document.querySelectorAll("#titleChips kbd").length, fix: document.getElementById("fixToggle")?.getAttribute("aria-label") }));
        const r1 = run.tickets.find((r) => r.ticket.id === k1).result;
        const sub = r1.extraction?.subcategory;
        const want = sub ? `${meta.subcategories[sub].label} · ${meta.teams[r1.team].label_ar}` : "?";
        check(`5 Nov calm: ${k1}'s summary is one line «${want}», no fields grid or key chips, the pencil named`,
          sum.line === want && !sum.dts && !sum.chips && sum.fix === "صحّح النوع أو القسم أو الأولوية" && sum.notes.every((n) => !n.includes("واثق")),
          JSON.stringify(sum));
      }
      if (pass.phone) await noHScroll("ticket with a draft");
      await shot(page, "drafted");
      // on a desktop, from the queue row (where J / K leave the focus): the listbox must not swallow it
      if (!pass.phone) await page.focus('#queueList [aria-selected="true"]');
      const d = await act(approveKey, "the approve decision");
      check(`approve (${pass.phone ? "a tap" : "Ctrl+Enter from the queue row"}) logs «approved» for ${k1}`, d.action === "approved" && d.ticket_id === k1 && d.run === RUN && d.pipeline_outcome === "drafted", JSON.stringify(d));
      await waitUntil(async () => (await selected()) !== k1, 3000, "the next ticket");
      const focus = await page.evaluate(() => document.activeElement?.id);
      check("focus moves to the next ticket's heading", focus === "ticketTitle", focus);
      check("toast «انعتمدت … · الباقي 79»", /انعتمدت/.test(await text("#status")) && (await text("#status")).includes(k1) && /الباقي\s*79/.test(await text("#status")), await text("#status"));
      check("counter «خلصت 1 من 80»", /خلصت\s*1\s*من\s*80/.test(await text("#queueTitle")), await text("#queueTitle"));
    }

    // 4. Undo with Ctrl+Z (the toast's button on a phone): logged as «undone» naming that decision.
    {
      if (pass.phone) {
        const kd = await page.evaluate(() => getComputedStyle(document.querySelector("#toastUndo kbd")).display);
        check("phone: the toast's «تراجع» has no Ctrl+Z hint (J9)", kd === "none", kd);
      }
      const approvedId = decisions().at(-1).id;
      const d = await act(() => (pass.phone ? page.click("#toastUndo") : page.keyboard.press("Control+z")), "the undo");
      check("undo logs «undone» with undoes = the approve's id", d.action === "undone" && d.undoes === approvedId && d.ticket_id === k1, JSON.stringify(d));
      await waitUntil(async () => (await selected()) === k1, 3000, "the undone ticket to reopen");
      check(`the undone ticket is back in «جاهزة» (${EXPECT.drafted})`, (await text("#tab-drafted .tab-count")).replace(/\D/g, "") === String(EXPECT.drafted), await text("#tab-drafted .tab-count"));
      // approve it again: it is one of the tickets the reload must bring back
      await act(approveKey, "the second approve");
    }

    // 5. A flagged ticket: approve stays off until the box is ticked.
    let k2;
    {
      k2 = await openTab("flagged");
      // 5 Nov calm: P1s wait in «متصعّدة» and «جاهزة», only P2s here: a dot on those two tabs, in their names.
      {
        const marks = await page.evaluate(() => Object.fromEntries([...document.querySelectorAll("[role=tab]")].map((b) => [b.dataset.tab, b.querySelector(".tab-urgent")?.textContent || ""])));
        // (On a phone the queue is hidden behind the ticket screen: the names are read there all the same.)
        const named = await page.getByRole("tab", { name: /متصعّدة.*فيها تذكرة عاجلة/, includeHidden: true }).count();
        check("5 Nov calm / review: from «تحتاج تأكيد» (P2s), a tiny «P1» on «متصعّدة» and «جاهزة» (P1s wait there), named «فيها تذكرة عاجلة»; none here",
          marks.escalated === "P1" && marks.drafted === "P1" && !marks.flagged && !marks.done && named === 1, JSON.stringify({ marks, named }));
      }
      check(`flagged ${k2}: approve is disabled and reads «تأكدت، اعتمد»`,
        (await page.getAttribute("#approveBtn", "aria-disabled")) === "true" && (await text("#approveBtn")).includes("تأكدت، اعتمد"), await text("#approveBtn"));
      check("flagged: the box names what to check", (await text("#confirmBox")).includes("تأكد من"), await text("#confirmBox"));
      {
        const lay = await page.evaluate(() => {
          const d = document.getElementById("draft").getBoundingClientRect(), c = document.getElementById("confirmBox").getBoundingClientRect();
          const w = document.getElementById("approveWhy");
          return { below: c.top >= d.bottom,
            muted: !!w?.classList.contains("is-muted"), icon: !!w?.querySelector("svg"), words: w?.textContent || "" };
        });
        check("5 Nov review: the tick sits under the draft (read, tick, approve), and approve's reason, only the tick, is quiet with no warning icon",
          lay.below && lay.muted && !lay.icon && lay.words.includes("تحت المسودة"), JSON.stringify(lay));
      }
      const n0 = decisions().length;
      // a tap on the aria-disabled button (force: Playwright itself won't click an aria-disabled one)
      if (pass.phone) await page.click("#approveBtn", { force: true }); else await page.keyboard.press("Control+Enter");
      await sleep(400);
      check("flagged: approving before the tick does nothing", decisions().length === n0 && (await selected()) === k2);
      const toastOn = () => page.evaluate(() => document.getElementById("toast").classList.contains("is-shown"));
      check("flagged: the refusal says what to tick", (await toastOn()) && (await text("#status")).includes("أشّر على"), await text("#status"));
      await shot(page, "flagged");
      await page.check("#ackBox");
      check("flagged: approve is enabled after the tick", (await page.getAttribute("#approveBtn", "aria-disabled")) === null);
      // J8, then 5 Nov calm: the row's name says «تحتاج تأكيد», like its tab; the word is not on screen.
      const rowNamed = await page.getByRole("option", { name: /^تحتاج تأكيد\s*،/, includeHidden: true }).and(page.locator(`#opt-${k2}`)).count();
      const nameOnly = await page.evaluate((k) => !!document.querySelector(`#opt-${k} .sr-only .row-word`) && !document.querySelector(`#opt-${k} .row-status`), k2);
      check("a flagged row's name starts with «تحتاج تأكيد», like its tab (J8; 5 Nov calm: not on screen)", rowNamed === 1 && nameOnly, `${rowNamed} ${nameOnly}`);
      check("flagged: the refusal goes as soon as the box is ticked (polish 5)", !(await toastOn()) && !(await page.locator("#approveWhy").count()),
        await text("#status"));
      const d = await act(() => page.click("#approveBtn"), "the flagged approve");
      check(`flagged approve logs «approved» for ${k2}`, d.action === "approved" && d.ticket_id === k2 && d.pipeline_outcome === "flagged", JSON.stringify(d));
      // 5 Nov review: the first flagged ticket is a SIM change (account_risk); the log keeps the identity tick.
      const k2Flags = run.tickets.find((r) => r.ticket.id === k2)?.result.flags || [];
      check(`flagged ${k2} [${k2Flags.join(", ")}]: the log line keeps the identity tick (warnings_acknowledged «account_risk»)`,
        k2Flags.includes("account_risk") && JSON.stringify(d.flags) === '["account_risk"]'
        && JSON.stringify(d.warnings_acknowledged) === '["account_risk"]', JSON.stringify(d));
      // A P1 escalation waits, more urgent than every flagged P2: the inbox moves there and says why.
      check("after the flagged approve the toast says the inbox moved to «متصعّدة» for an urgent ticket (polish 3)",
        (await text("#status")).includes("انتقلنا لـ«متصعّدة»: فيها تذكرة عاجلة")
        && (await page.getAttribute("#tab-escalated", "aria-selected")) === "true", await text("#status"));
      // J9: the decision's toast (and its undo) stays with the inbox: «كيف يشتغل» opens without it.
      await toProcess();
      await page.waitForSelector("#ovTitle", { timeout: 10000 });
      check("the decision's toast goes when «كيف يشتغل» opens (J9)", !(await toastOn()), await text("#status"));
      await page.click("#modeAgent");
      await page.waitForSelector("#ticketTitle", { state: "attached", timeout: 10000 });
    }

    // 6. An edit that asks for the code blocks approval until it is gone; a harmless edit logs «edited».
    let k3;
    {
      k3 = await openTab("drafted");
      // 5 Nov calm: all checks passed: a few words, the list of checks in their tip (hover or focus; a tap
      // pins it). No reasons yet. The action bar's one key hint is Ctrl+Enter, and no sentence explains it.
      {
        const clean = (await page.locator("#draftChecks").innerText()).trim();
        const tip = await text("#checksTip");
        if (pass.phone) await page.click(".checks-ok"); else await page.hover(".checks-ok");
        const tipShown = await page.isVisible("#checksTip");
        if (pass.phone) await page.click(".checks-ok"); else await page.mouse.move(1, 1);
        check("5 Nov calm: all checks passed: «ما بيها مشكلة», and the list of checks only in its tip",
          clean === "ما بيها مشكلة" && tip.startsWith("فحصنا المسودة وما لكينا:") && tip.includes("طلب رمز أو كلمة سر") && tipShown
          && (await page.getAttribute(".checks-ok", "aria-describedby")) === "checksTip", `${clean} | ${tip} | ${tipShown}`);
        if (!pass.phone) {
          await sleep(350);
          await page.hover(".checks-ok");
          await page.keyboard.press("Escape");
          await sleep(50);
          const escHidden = !(await page.isVisible("#checksTip"));
          await page.mouse.move(1, 1);
          await sleep(350);
          await page.hover(".checks-ok");
          const tb = await page.locator("#checksTip").boundingBox();
          await page.mouse.move(tb.x + tb.width / 2, tb.y + tb.height / 2, { steps: 6 });
          await sleep(100);
          const stays = await page.isVisible("#checksTip");
          await page.mouse.move(1, 1);
          await sleep(350);
          check("5 Nov review: the checks' tip goes with Escape, and stays while the pointer moves onto it (WCAG 1.4.13)", escHidden && stays,
            JSON.stringify({ escHidden, stays }));
        }
        const rb = await page.evaluate(() => { const d = document.getElementById("reasonBox"); return { tag: d?.tagName, hidden: d?.hidden }; });
        const bar = await page.evaluate(() => ({ kbds: [...document.querySelectorAll("#actionBar kbd")].map((k) => k.closest("button")?.id || "?"),
          hint: !!document.getElementById("draftHint") }));
        check("5 Nov calm: no reasons before an edit; the action bar's only key hint is approve's Ctrl+Enter; no Esc / Ctrl+Enter sentence",
          rb.tag === "DIV" && rb.hidden && JSON.stringify([...new Set(bar.kbds)]) === '["approveBtn"]' && !bar.hint, JSON.stringify({ rb, bar }));
      }
      if (pass.phone) await page.click("#draft"); else await page.keyboard.press("e");
      check("the draft takes focus", await page.evaluate(() => document.activeElement?.id === "draft"));
      await page.evaluate(() => { const t = document.getElementById("draft"); t.setSelectionRange(t.value.length, t.value.length); });
      await page.keyboard.type(SECRET_ASK);
      await page.waitForSelector("#draftChecks .check-item.is-blocking", { timeout: 6000 });
      check("an edit asking for the code blocks approval", (await page.getAttribute("#approveBtn", "aria-disabled")) === "true"
        && (await text("#approveWhy")).includes(meta.check_ar.asks_secret.split(/[:،(]/)[0].trim()), await text("#approveWhy"));
      check("the label becomes «معدّلة منك»", (await text(".composer-label")).includes("معدّلة منك"), await text(".composer-label"));
      check("the phrase is highlighted in the draft", (await page.locator(".composer-mirror mark.finding.is-blocking").count()) === 1);
      // 5 Nov calm: the edit brings the optional reasons, as one closed line.
      const rb = await page.evaluate(() => { const d = document.getElementById("reasonBox"); return { tag: d.tagName, open: d.open,
        summary: d.querySelector("summary")?.textContent.trim(), chipsShown: [...d.querySelectorAll(".reason-chip")].some((c) => c.checkVisibility()) }; });
      check("5 Nov calm: after an edit the reasons are one closed line «ليش غيّرتها؟ (اختياري)»",
        rb.tag === "DETAILS" && !rb.open && rb.summary === "ليش غيّرتها؟ (اختياري)" && !rb.chipsShown, JSON.stringify(rb));
      const n0 = decisions().length;
      await page.keyboard.press("Control+Enter");   // from inside the draft
      await sleep(500);
      check("Ctrl+Enter inside a blocked draft does not approve", decisions().length === n0 && (await selected()) === k3);
      await shot(page, "blocked");
      const refused = await page.evaluate(() => document.getElementById("toast").classList.contains("is-shown")
        && document.getElementById("status").textContent.includes("رمز"));
      await page.click("text=رجّع المسودة الأصلية");
      await waitUntil(async () => (await page.getAttribute("#approveBtn", "aria-disabled")) === null, 4000, "approve to be enabled again");
      check("restoring the draft enables approval, and the reasons go with the edit (5 Nov calm)",
        await page.evaluate(() => document.getElementById("reasonBox").hidden));
      check("the refusal about the code goes once the request is gone (polish 5)", refused
        && !(await page.evaluate(() => document.getElementById("toast").classList.contains("is-shown"))), await text("#status"));
      // a harmless edit: «edited», with a count of changed characters and no text in the log
      await page.click("#draft");
      await page.evaluate(() => { const t = document.getElementById("draft"); t.setSelectionRange(t.value.length, t.value.length); });
      await page.keyboard.type(" شكراً لصبرك");
      await waitUntil(async () => (await page.getAttribute("#approveBtn", "aria-disabled")) === null
        && !(await page.locator("#draftChecks .checks-state").count()), 4000, "the edit to be checked");
      const d = await act(approveKey, "the edited approve");
      const raw = fs.readFileSync(srv.decisions, "utf8");
      check(`an edited draft logs «edited» with edit_chars and no text (${k3})`, d.action === "edited" && d.ticket_id === k3 && d.edit_chars > 0
        && !raw.includes("شكراً لصبرك") && !raw.includes("دزلنا"), JSON.stringify(d));
    }

    // 7. An escalated ticket has no draft; forward works.
    let k4;
    {
      k4 = await openTab("escalated");
      check(`escalated ${k4}: no draft box`, (await page.locator("#agentMain textarea").count()) === 0);
      check("escalated: the team note is shown, with the fraud banner", (await page.isVisible("#handoffTitle")) && (await text("#agentMain .callout-bad")).includes("احتمال احتيال"), await text("#agentMain .callout-bad"));
      check("5 Nov review: the team note's title is «ملاحظة للقسم» (the team is in the summary line and on forward)",
        (await text("#handoffTitle")) === "ملاحظة للقسم" && (await text("#forwardBtn")).includes("قسم"), `${await text("#handoffTitle")} | ${await text("#forwardBtn")}`);
      const handoff = run.tickets.find((r) => r.ticket.id === k4).result.handoff_ar || "";
      if (/^الخلاصة:/m.test(handoff)) {
        check("escalated: «الخلاصة» is marked as written by a model, the rest by rules (J2)", (await text(".handoff .dt-tag")) === "كتبها نموذج"
          && (await text(".handoff .hint")).includes("بس «الخلاصة» كتبها نموذج"), await text(".handoff .hint"));
      }
      if (pass.phone) await noHScroll("escalated ticket");
      await shot(page, "escalated");
      const d = await act(() => (pass.phone ? page.click("#forwardBtn") : page.keyboard.press("f")), "the forward");
      check(`forward logs «forwarded» for ${k4}`, d.action === "forwarded" && d.ticket_id === k4 && d.pipeline_outcome === "escalated", JSON.stringify(d));
      check("after a forward the tab counts the 5 still open (the run's note, in «كيف يشتغل», still says 6: step 10)",
        (await text("#tab-escalated .tab-count")).replace(/\D/g, "") === "5", await text("#tab-escalated .tab-count"));
    }

    // 8. Reload: the decided tickets come back from the log.
    {
      await page.reload();
      await page.waitForSelector("#ticketTitle", { state: "attached", timeout: 15000 });
      await waitUntil(async () => /خلصت\s*4\s*من\s*80/.test(await text("#queueTitle")), 5000, "the counter after reload").catch(() => {});
      check("after a reload the counter is «خلصت 4 من 80»", /خلصت\s*4\s*من\s*80/.test(await text("#queueTitle")), await text("#queueTitle"));
      check("after a reload the dismissed intro stays hidden", await page.evaluate(() => document.getElementById("intro").hidden));
      if (pass.phone) {
        if (await page.evaluate(() => document.body.dataset.screen === "ticket")) await page.locator("#agentMain .back-btn").first().click();
        await page.click("#tab-done");
      } else {
        await page.keyboard.press("4");
      }
      await sleep(150);
      const done = await page.evaluate(() => [...document.querySelectorAll("#queueList [role=option]")].map((o) => o.dataset.key).sort());
      check("the «خلصت» tab lists the four decided tickets", JSON.stringify(done) === JSON.stringify([k1, k2, k3, k4].sort()), done.join(","));
      const dn = await page.evaluate(() => [...document.querySelectorAll("#queueList [role=option]")].map((o) => ({ icon: !!o.querySelector(".row-decision svg"), title: o.querySelector(".row-decision")?.title })));
      const namedDone = await page.getByRole("option", { name: /^(انعتمدت|انعدّلت وانعتمدت|استلمتها|تحوّلت)\s*،/ }).count();
      check("5 Nov calm: in «خلصت» each row shows what was done as a small icon, named (its title, and the start of the row's name)",
        dn.length === 4 && dn.every((x) => x.icon && ["انعتمدت", "انعدّلت وانعتمدت", "استلمتها", "تحوّلت"].includes(x.title)) && namedDone === 4,
        JSON.stringify({ dn, namedDone }));
    }

    // 9. Keyboard: J and K move the selection.
    {
      await openTab("drafted");
      const a = await selected();
      await page.keyboard.press("j");
      const b = await selected();
      await page.keyboard.press("k");
      const c = await selected();
      check(`J moves to the next ticket and K back (${a} → ${b} → ${c})`, a && b && a !== b && c === a);
    }

    // 10. "كيف يشتغل": the overview numbers and a trace with the model's input and output.
    {
      await toProcess();
      await page.waitForSelector("#ovTitle", { timeout: 10000 });
      const stats = await text(".overview .stats");
      check(`overview: type ${EXPECT.type}, priority ${EXPECT.priority}`, stats.includes(EXPECT.type) && stats.includes(EXPECT.priority), stats.slice(0, 200));
      // Polish 4 (moved on 5 Nov): what the system did with the whole run, in the overview. 5 Nov calm: the
      // side list has the controls and the tickets; the live status and the model ids are said once, above.
      const pnav = await page.evaluate(() => ({ models: document.getElementById("processNav").textContent.includes("claude-"),
        live: document.querySelectorAll("#processNav .live-line").length, meta: !!document.getElementById("pMeta") }));
      check("the overview says what the system did with the run: «بهالتشغيل النظام صعّد 6 تذاكر، كلها احتمال احتيال.»",
        (await text("#runNote")) === "بهالتشغيل النظام صعّد 6 تذاكر، كلها احتمال احتيال.", await text("#runNote"));
      check("5 Nov calm: «كيف يشتغل»'s side list has no model ids or live-status line; the overview header says it once",
        !pnav.models && !pnav.live && !pnav.meta && (await page.locator(".overview .live-line").count()) === 1, JSON.stringify(pnav));
      if (!pass.phone) {
        const [sh, ih] = await pageFits();
        check("process mode: the page itself does not scroll (no caption escapes its pane) (J6)", sh <= ih, `${sh} > ${ih}`);
      }
      await page.waitForSelector(".decisions-sum .stats", { timeout: 5000 }).catch(() => {});
      const tiles = await text(".decisions-sum .stats");
      check("the decision tiles read with any number («تذاكر انحسمت», «قرارات أسرع …») (J8)", tiles.includes("تذاكر انحسمت")
        && tiles.includes("قرارات أسرع") && !tiles.includes("تذكرة انحسمت"), tiles);
      await shot(page, "process-overview");
      if (pass.phone) await noHScroll("process overview");
      await page.locator("table.grid tbody tr.click", { hasText: "t2-0001" }).first().click();   // drafted: classify and draft
      await page.waitForSelector(".trace .gold table", { timeout: 10000 });   // the replay has reached the result
      const io = await page.locator(".trace details.io").count();
      const gold = await text(".trace .gold .note");
      check(`trace shows the model input and output (${io} blocks), the rationale label and the gold table`, io >= 2
        && (await text(".trace")).includes("تفسير النموذج (إنكليزي)") && gold.includes("الجواب المتوقع") && !gold.includes("undefined"), gold);
      // Polish 6: a stage shows its own time (since the event before it), not the time since the start.
      const evs = run.tickets.find((r) => r.ticket.id === "t2-0001").events;
      const want = {};
      evs.forEach((e, i) => { if (e.status === "done" && e.stage !== "result") want[e.stage] = e.ms - (i ? evs[i - 1].ms : 0); });
      const shown = await page.evaluate(() => Object.fromEntries([...document.querySelectorAll(".stage")].map((x) => [x.id.slice(3), x.querySelector(".state").textContent])));
      const label = (ms) => (ms < 50 ? "خذت أقل من 0.1 ث" : `خذت ${(ms / 1000).toFixed(1)} ث`);
      const wrong = Object.entries(want).filter(([st, ms]) => shown[st] !== label(ms));
      check(`trace: each stage shows its own time (classify ${shown.classify}, gate ${shown.gate}), the total says «بالمجموع»`,
        wrong.length === 0 && want.gate < 50 && (await text(".trace > .note")).includes("بالمجموع"), JSON.stringify({ wrong, shown }));
      await shot(page, "process-trace");
      if (pass.phone) await noHScroll("process trace");
      await cspOf(page, "process");
      await page.click("#modeAgent");
      await page.waitForSelector("#ticketTitle", { state: "attached", timeout: 10000 });
    }

    // 11. A pasted ticket, live: with PIPELINE_MODE=off it goes to a person (pipeline_off).
    {
      if (pass.phone && await page.evaluate(() => document.body.dataset.screen === "ticket")) await page.locator("#agentMain .back-btn").first().click();
      await page.click("#newTicket");
      await page.fill("#newText", "حولت خمسين الف لاخوي من البارحة وما وصلت، رقم العملية 4471-9032");
      await page.click("#newRun");
      await page.waitForFunction(() => document.querySelector('[id^="opt-live-"]') && !document.querySelector('[id^="opt-live-"].st-running'), null, { timeout: 15000 });
      const liveKey = await page.evaluate(() => document.querySelector('[id^="opt-live-"]').dataset.key);
      check("the live ticket ends escalated", await page.evaluate(() => document.querySelector('[id^="opt-live-"]').classList.contains("st-escalated")));
      const offWord = meta.flag_ar.pipeline_off.split(/[:،]/)[0].trim();
      check(`the live ticket says why: «${offWord}»`, (await selected()) === liveKey && (await text("#agentMain")).includes(offWord), (await text("#agentMain")).slice(0, 200));
      await shot(page, "live");
      // the first press offers the optional reasons, the second records
      const d = await act(async () => {
        if (pass.phone) { await page.click("#takeBtn"); await page.click("#takeBtn"); } else { await page.keyboard.press("t"); await page.keyboard.press("t"); }
      }, "the live take-over");
      check("taking over the live ticket logs run «live» with flag pipeline_off", d.run === "live" && d.ticket_id === liveKey && d.action === "took_over"
        && d.pipeline_outcome === "escalated" && (d.flags || []).includes("pipeline_off"), JSON.stringify(d));
    }

    // 12. A 4,100-character ticket: refused with the Arabic message, by the page and by the server.
    {
      const long = "حولت فلوس لاخوي وما وصلت ".repeat(200).slice(0, 4100).replace(/\s$/, "ت");
      let streams = 0;
      const count = (r) => { if (r.url().endsWith("/api/stream")) streams++; };
      page.on("request", count);
      if (pass.phone && await page.evaluate(() => document.body.dataset.screen === "ticket")) await page.locator("#agentMain .back-btn").first().click();
      await page.click("#newTicket");
      await page.fill("#newText", long);
      check("the counter shows 4,100 against the 4,000 limit", (await text("#newCount")).includes("4,100") && (await text("#newCount")).includes("4,000"), await text("#newCount"));
      await page.click("#newRun");
      await page.waitForFunction(() => document.getElementById("newError").textContent.length > 0, null, { timeout: 3000 });
      check("the page refuses it in Arabic and sends nothing", (await text("#newError")).includes("أطول من الحد المسموح") && streams === 0, `${await text("#newError")} (${streams} requests)`);
      await page.keyboard.press("Escape");
      page.off("request", count);

      // The server's own 413: the page's limit is raised in /api/meta, so the text reaches the server.
      const p2 = await ctx.newPage();
      await watch(p2, "server-413");
      await p2.route("**/api/meta", async (route) => {
        const r = await route.fetch();
        const j = await r.json();
        j.limits.max_ticket_chars = 10000;
        await route.fulfill({ response: r, json: j });
      });
      await p2.goto(srv.base);
      await p2.waitForSelector("#ticketTitle", { state: "attached", timeout: 15000 });
      if (pass.phone && await p2.evaluate(() => document.body.dataset.screen === "ticket")) await p2.locator("#agentMain .back-btn").first().click();
      await p2.click("#newTicket");
      await p2.fill("#newText", long);
      allowRefusals = 1;
      const resp = p2.waitForResponse((r) => r.url().endsWith("/api/stream"));
      await p2.click("#newRun");
      const status = (await resp).status();
      await p2.waitForFunction(() => document.getElementById("newError").textContent.length > 0, null, { timeout: 3000 });
      const msg = await p2.locator("#newError").textContent();
      check(`the server answers 413 and the dialog shows its Arabic message («${msg}»)`,
        status === 413 && msg.includes("أطول من الحد المسموح") && msg.includes(String(meta.limits.max_ticket_chars)) && (await p2.isVisible("#newDialog")), `${status} ${msg}`);
      await shot(p2, "413");
      await cspOf(p2, "server-413");
      await p2.close();
      await sleep(100);
      allowRefusals = 0;
    }

    // 13. Phone width: no horizontal scroll, the action bar fixed at the bottom, back to the queue.
    if (pass.phone) {
      await openTab("drafted");
      const pos = await page.evaluate(() => getComputedStyle(document.getElementById("actionBar")).position);
      check("phone: the action bar is fixed at the bottom", pos === "fixed", pos);
      const head = await page.evaluate(() => ({ h: Math.round(document.getElementById("topbar").getBoundingClientRect().height),
        modes: document.querySelector(".modes").checkVisibility(), picker: document.getElementById("sourceField").checkVisibility() }));
      await noHScroll("after the flows");
      await page.locator("#agentMain .back-btn").first().click();
      check("phone: back returns to the queue", await page.isVisible("#queueList"));
      const qhead = await page.evaluate(() => ({ modes: document.querySelector(".modes").checkVisibility(), picker: document.getElementById("sourceField").checkVisibility() }));
      check("5 Nov review: the phone's ticket screen has a one-row header; the mode switch and the picker are on the queue screen",
        head.h <= 64 && !head.modes && !head.picker && qhead.modes && qhead.picker, JSON.stringify({ head, qhead }));
    } else {
      await noHScroll("desktop");
    }
    await cspOf(page, "inbox");

    // 14. The fixes from the 1 Nov review, on a fresh page of the same server (desktop passes); the
    // phone passes check the phone-only ones.
    if (pass.phone) await phoneFixes(); else await reviewFixes();
  } catch (e) {
    check("the pass ran to its end", false, e.stack || e.message);
  } finally {
    await ctx.close().catch(() => {});
    await stopServer(srv);
  }
  check("no console errors, CSP violations or requests to another host", problems.length === 0, problems.slice(0, 8).join(" | "));
}

// --- the fresh-clone pass: the first visit, the honest no-key state, the README screenshots ---

async function runFresh(browser, pass) {
  const srv = await startServer({ fresh: true });
  const host = `127.0.0.1:${srv.port}`;
  const problems = [];
  let streams = 0;
  const check = (name, ok, detail = "") => results.push({ pass: pass.name, name, ok: !!ok, detail: ok ? "" : String(detail) });
  const demo = async (p, name) => { if (DEMO) await p.screenshot({ path: path.join(DEMO, `${name}.png`) }); };
  const t = (p, sel) => p.locator(sel).first().textContent({ timeout: 2000 }).catch(() => "");
  const shown = (p) => p.evaluate(() => document.getElementById("toast").classList.contains("is-shown"));
  const decisions = () => readDecisions(srv.decisions);
  const contexts = [];
  async function open(viewport, scheme, label, init = null, setup = null) {
    const ctx = await browser.newContext({ viewport, colorScheme: scheme, hasTouch: viewport.width < 500 });
    contexts.push(ctx);
    const p = await ctx.newPage();
    p.on("console", (m) => { if (m.type() === "error" || m.type() === "warning") problems.push(`${label} console ${m.type()}: ${m.text()}`); });
    p.on("pageerror", (e) => problems.push(`${label} page error: ${e.message}`));
    p.on("request", (r) => {
      const u = r.url();
      if (u.startsWith("data:")) return;
      if (new URL(u).host !== host) problems.push(`${label} request to another host: ${u}`);
      if (u.endsWith("/api/stream")) streams++;
    });
    // Belt and braces: this pass never starts a live run, and the browser could not send one.
    await p.route("**/api/stream", (route) => route.abort());
    await p.addInitScript(() => {
      window.__csp = [];
      document.addEventListener("securitypolicyviolation", (e) => window.__csp.push(`${e.violatedDirective} ${e.blockedURI}`));
    });
    if (init) await p.addInitScript(init);
    if (setup) await setup(p);
    await p.goto(srv.base);
    await p.waitForSelector("#ticketTitle", { state: "attached", timeout: 15000 });
    await p.evaluate(() => document.fonts.ready.then(() => true));
    await sleep(250);
    return p;
  }
  async function done(p, label) {
    for (const x of await p.evaluate(() => window.__csp || []).catch(() => [])) problems.push(`${label} CSP violation: ${x}`);
  }
  /** Open a ticket by id on a desktop page: its tab (keys 1-4), then its row. */
  async function openId(p, key) {
    for (const k of ["1", "2", "3", "4"]) {
      await p.evaluate(() => document.activeElement?.blur());
      await p.keyboard.press(k);
      await sleep(60);
      const row = p.locator(`#queueList [data-key="${key}"]`);
      if (await row.count()) {
        await row.click();
        await sleep(150);
        await p.evaluate(() => { document.getElementById("main").scrollTop = 0; });
        return;
      }
    }
    throw new Error(`no row for ${key}`);
  }
  const DRAFTED = "t2-0002", FLAGGED = "t2-0009", ESCALATED = "t2-0025";   // a P1 draft with facts, a disagreement, fraud

  try {
    const log = srv.log();
    check("start-up line: the viewer runs on the API backend by default", log.includes("backend: api, the viewer's default"), log);
    check("start-up line: with no key, live runs are off and it says why", log.includes("live runs off: no API key"), log);

    // 1. Desktop, first visit.
    const p = await open(pass.viewport, "light", "fresh");
    const meta = await p.evaluate(async () => {
      const token = document.querySelector('meta[name="viewer-token"]').content;
      return fetch("/api/meta", { headers: { "X-Viewer-Token": token } }).then((r) => r.json());
    });
    check("/api/meta: the API backend, full mode, live runs off for want of a key", meta.backend === "api" && meta.mode === "full"
      && meta.live.available === false && meta.live.cause === "no_key", JSON.stringify({ backend: meta.backend, mode: meta.mode, live: meta.live }));
    check("no kill-switch banner (PIPELINE_MODE is not set)", await p.evaluate(() => document.getElementById("banners").hidden));
    check("T17: REAL_DATA unset: the header says «وضع التطوير», quietly (not on a phone: no room)", meta.real_data === false && await p.isVisible("#devBadge")
      && (await t(p, "#devBadge")) === "وضع التطوير", String(meta.real_data));
    check("the new-ticket button is visibly off (dashed) and says why (J7)", (await p.getAttribute("#newTicket", "class")).includes("is-unavailable")
      && (await t(p, "#newTicketWhy")) === meta.live.reason_ar && (await p.getAttribute("#newTicket", "title")) === meta.live.reason_ar
      && (await p.evaluate(() => getComputedStyle(document.getElementById("newTicket")).borderStyle)) === "dashed", await t(p, "#newTicketWhy"));
    check("first visit: the intro card is at the top of the ticket pane", (await p.isVisible("#intro"))
      && await p.evaluate(() => document.getElementById("main").firstElementChild.id === "intro"));
    await demo(p, "inbox-first-visit");
    await p.click("#newTicket");
    check("the new-ticket dialog says live runs are off and what turns them on, with no box to type in (J7)",
      (await t(p, "#newNote")).startsWith(meta.live.reason_ar) && (await t(p, "#newNote")).includes("مفتاح API")
      && await p.isDisabled("#newRun") && !(await p.isVisible("#newText")) && !(await p.isVisible("#newCount")), await t(p, "#newNote"));
    await p.keyboard.press("Escape");
    await p.click("#introOk");
    check("«فهمت» hides the card", await p.evaluate(() => document.getElementById("intro").hidden));
    const fits = (pg) => pg.evaluate(() => document.scrollingElement.scrollHeight <= innerHeight);

    // 2. The ticket kinds, for the screenshots.
    await openId(p, DRAFTED);
    check(`${DRAFTED}: a draft, approve on`, (await p.locator("#draft").count()) === 1 && (await p.getAttribute("#approveBtn", "aria-disabled")) === null);
    // 5 Nov calm: no fact boxes. The facts are one quiet line under the message; a value lights its
    // underline and the underline its value; the amount written in words («مليونين») has a small marker
    // whose tip says it was not found as written, and no sentence says so on screen.
    {
      const facts = await p.evaluate(() => {
        const c = document.querySelector(".customer");
        const line = c.querySelector(".facts");
        const b = line?.querySelector(".fact-btn");
        const st = b ? getComputedStyle(b) : null;
        return { under: !!line && line.previousElementSibling === c.querySelector(".customer-text"),
          items: line ? [...line.children].map((li) => li.textContent.replace(/\s+/g, " ").trim()) : [],
          boxed: st ? parseFloat(st.borderTopWidth) > 0 || st.backgroundColor !== "rgba(0, 0, 0, 0)" : null,
          sentence: c.innerText.includes("ما لكيناه"), tip: c.querySelector(".fact-tip")?.getAttribute("aria-label"),
          described: document.getElementById(c.querySelector(".fact-tip")?.getAttribute("aria-describedby") || "-")?.textContent || "" };
      });
      await p.hover(".customer .fact-btn");
      const lit = await p.evaluate(() => document.querySelectorAll(".customer-text [data-fact].is-hot").length);
      await p.hover(".customer-text [data-fact]");
      const back = await p.evaluate(() => document.querySelectorAll(".customer .fact-btn.is-hot").length);
      await p.hover(".customer .fact-tip");
      await sleep(150);
      // 5 Nov review: the tip is a real element (role=tooltip), under the facts line, never over the message;
      // it says what to do; Escape hides it with the pointer still on the marker (WCAG 1.4.13).
      const tipBox = await p.evaluate(() => {
        const tip = document.querySelector(".customer .facts [role=tooltip]");
        const r = tip?.getBoundingClientRect(), msg = document.querySelector(".customer-text").getBoundingClientRect();
        return tip ? { text: tip.textContent, shown: getComputedStyle(tip).visibility === "visible", underMessage: r.top >= msg.bottom } : null;
      });
      await p.keyboard.press("Escape");
      const escHidden = await p.evaluate(() => getComputedStyle(document.querySelector(".customer .facts [role=tooltip]")).visibility === "hidden");
      await p.mouse.move(640, 2);
      check(`5 Nov calm: ${DRAFTED}'s facts are one line under the message, no boxes; value and underline light each other; the amount not found has a marker with its tip, no sentence`,
        facts.under && facts.items.length >= 2 && facts.items[0].startsWith("رقم العملية") && facts.boxed === false && lit === 1 && back === 1
        && !facts.sentence && facts.tip === "ما لكيناه بالنص بنفس الشكل" && tipBox?.shown && tipBox.text.includes("ما لكيناه بالنص بنفس الشكل"),
        JSON.stringify({ ...facts, lit, back, tipBox }));
      check("5 Nov review: the marker's tip is under the facts line, says what to do (its description), and goes with Escape",
        tipBox?.underMessage && tipBox.text.includes("قارنه بالرسالة") && facts.described.includes("قارنه بالرسالة") && escHidden, JSON.stringify({ tipBox, escHidden, described: facts.described }));
    }
    await demo(p, "inbox-desktop");
    await openId(p, FLAGGED);
    check(`${FLAGGED}: the two models' answers are shown to choose from`, (await p.locator("#choiceBox input[type=radio]").count()) === 2
      && await p.isVisible("#choiceBox"));
    // 5 Nov review: said once each: the banner says they disagreed, the choice asks the type, the tick
    // (under the draft) confirms it.
    {
      const f9 = await p.evaluate(() => ({ banner: document.getElementById("whyLine")?.textContent, legend: document.querySelector("#choiceBox legend")?.textContent,
        opts: [...document.querySelectorAll("#choiceBox .choice-opt")].map((o) => Math.round(o.getBoundingClientRect().height)) }));
      check(`5 Nov review: ${FLAGGED}'s banner «…النموذجين اختلفوا بنوع المشكلة.», the choice «ياهو النوع الصح؟», one line per answer`,
        f9.banner === "تحتاج تأكيد: النموذجين اختلفوا بنوع المشكلة." && f9.legend === "ياهو النوع الصح؟" && f9.opts.length === 2 && f9.opts.every((h) => h <= 44),
        JSON.stringify(f9));
    }
    await demo(p, "inbox-flagged");
    // 5 Nov review: on every flagged ticket at 1280 x 800, the draft's first two lines show above the action bar
    // (the tick is under the draft), and a field the banner names is not said again above the message.
    {
      const served = await p.evaluate(async (name) => {
        const token = document.querySelector('meta[name="viewer-token"]').content;
        const j = await fetch(`/api/run?name=${encodeURIComponent(name)}`, { headers: { "X-Viewer-Token": token } }).then((r) => r.json());
        return j.tickets.filter((r) => r.result.outcome === "flagged").map((r) => r.ticket.id);
      }, RUN);
      const under = [];
      for (const id of served) {
        await openId(p, id);
        const m = await p.evaluate(() => {
          const d = document.getElementById("draft").getBoundingClientRect(), bar = document.getElementById("actionBar").getBoundingClientRect();
          const lh = parseFloat(getComputedStyle(document.getElementById("draft")).lineHeight);
          const c = document.getElementById("confirmBox").getBoundingClientRect();
          return { two: d.top + 14 + 2 * lh <= bar.top + 1, tickBelow: c.top >= d.bottom };
        });
        if (!m.two || !m.tickBelow) under.push(`${id} ${JSON.stringify(m)}`);
      }
      await openId(p, "t2-0017");
      const t17 = await p.evaluate(() => ({ banner: document.getElementById("whyLine")?.textContent || "",
        notes: [...document.querySelectorAll("#sumBox .summary-note")].map((n) => [n.className, n.textContent, getComputedStyle(n).fontWeight]) }));
      check(`5 Nov review: the ${served.length} flagged tickets at 1280 x 800 show the draft's first two lines above the bar, the tick under the draft`,
        served.length === 15 && !under.length, under.join(" | "));
      check("5 Nov review: t2-0017 names «رقم العملية» in its banner only; its agreed re-check is a quiet line, not a warning",
        t17.banner.includes("رقم العملية ناقص") && t17.notes.every(([, x]) => !x.includes("رقم العملية"))
        && t17.notes.some(([c, x, w]) => x === "النوع انراجع بنموذج ثاني، واتفقوا" && c.includes("muted") && Number(w) < 500), JSON.stringify(t17));
    }
    await openId(p, ESCALATED);
    check(`${ESCALATED}: no draft, the team note and forward`, (await p.locator("#draft").count()) === 0 && await p.isVisible("#handoffTitle")
      && await p.isVisible("#forwardBtn"));
    await demo(p, "inbox-escalated");

    // 3. «كيف يشتغل»: the overview, and a trace with each stage's own time.
    await p.click("#modeProcess");
    await p.waitForSelector("#ovTitle", { timeout: 10000 });
    await sleep(300);
    check("«كيف يشتغل» says live runs are off: no API key", (await t(p, ".overview .live-line")).includes(LIVE_NO_KEY), await t(p, ".overview .live-line"));
    check("process mode: the page itself does not scroll (J6)", await fits(p));
    const lede = await t(p, ".overview .lede");
    check("the overview gives the run's elapsed time as such, with the tickets run at once (J5)", lede.includes("التشغيل كله خذ")
      && lede.includes("5 تذاكر سوة") && !lede.includes("بالمجموع"), lede);
    // J8e: the model pair reads the same way (classifier / drafter) wherever it is. Since 5 Nov it is said
    // once, in the overview's lede (the live line repeats it only for other models), not in the side list.
    const order = await p.evaluate(() => [".overview .lede", ".overview .live-line"].map((sel) => {
      const x = (needle) => { const w = document.createTreeWalker(document.querySelector(sel), NodeFilter.SHOW_TEXT); let n;
        while ((n = w.nextNode())) { const i = n.data.indexOf(needle); if (i >= 0) { const r = document.createRange(); r.setStart(n, i); r.setEnd(n, i + 3); return r.getBoundingClientRect().left; } } return null; };
      const [a, b] = [x("claude-haiku"), x("claude-sonnet")];
      return sel.includes("live") && a == null && b == null ? "not repeated" : a != null && b != null && a < b;
    }));
    const sideModels = await p.evaluate(() => document.getElementById("processNav").textContent.includes("claude-"));
    check("the model pair reads classifier / drafter, once, in the overview's header; none in the side list (J8)", order[0] === true && order[1] !== false && !sideModels,
      JSON.stringify({ order, sideModels }));
    await demo(p, "process-overview");
    await p.locator("table.grid tbody tr", { hasText: FLAGGED }).first().locator(".row-open").click();
    await p.waitForSelector(".trace .gold table", { timeout: 10000 });
    const times = await p.evaluate(() => Object.fromEntries([...document.querySelectorAll(".stage")].map((x) => [x.id.slice(3), x.querySelector(".state").textContent])));
    check(`trace of ${FLAGGED}: the rule-only gate shows its own time, not the time since the start`, times.gate === "خذت أقل من 0.1 ث"
      && /^خذت \d+\.\d ث$/.test(times.recheck || ""), JSON.stringify(times));
    await p.evaluate(() => {
      const m = document.getElementById("main");
      m.scrollTop += document.getElementById("st-classify").getBoundingClientRect().top - m.getBoundingClientRect().top - 16;
    });
    await sleep(150);
    await demo(p, "process-trace");
    // J3: the cleaned text reads a spaced reference in the order it was written, like the ticket above it.
    await p.locator("#pList .prow", { hasText: DRAFTED }).first().click();
    await p.waitForSelector(".trace .gold table", { timeout: 10000 });
    const ref = await p.evaluate(() => [".slip", ".cleaned"].map((sel) => {
      const x = (needle) => { const w = document.createTreeWalker(document.querySelector(sel), NodeFilter.SHOW_TEXT); let n;
        while ((n = w.nextNode())) { const i = n.data.indexOf(needle); if (i >= 0) { const r = document.createRange(); r.setStart(n, i); r.setEnd(n, i + needle.length); return r.getBoundingClientRect().left; } } return null; };
      return [x("9776"), x("593217")];
    }));
    check(`trace of ${DRAFTED}: «9776 593217» reads in the written order in the ticket and in the cleaned text (J3)`,
      ref.every(([a, b]) => a != null && b != null && a < b), JSON.stringify(ref));
    // RR-2: an escalation's last second is the team note's «الخلاصة» (a model call): the result box says so.
    await p.locator("#pList .prow", { hasText: ESCALATED }).first().click();
    await p.waitForSelector(".trace .gold table", { timeout: 10000 });
    const res = await t(p, "#pResult .result");
    check(`trace of ${ESCALATED}: the result box gives the summary call and its own time (RR-2)`,
      res.includes("«الخلاصة» بالملاحظة كتبها نموذج التصنيف") && /خذت 1\.\d ث/.test(res), res.slice(0, 300));
    // 4. Storage blocked (a private window, a policy): the page works, the card shows and closes.
    const pb = await open(pass.viewport, "light", "no-storage", () => {
      Object.defineProperty(window, "localStorage", { configurable: true, get() { throw new DOMException("blocked", "SecurityError"); } });
    });
    const okB = (await pb.isVisible("#intro")) && (await pb.locator("#queueList [role=option]").count()) > 0;
    await pb.focus("#introOk");
    await pb.setViewportSize(pass.phoneViewport);
    await sleep(250);
    const toPhone = await pb.evaluate(() => document.activeElement?.id || document.activeElement?.tagName);
    await pb.locator("#agentMain .back-btn").first().click();   // the phone's queue screen: the card shows there
    await pb.focus("#introOk");
    await pb.setViewportSize(pass.viewport);
    await sleep(250);
    const toDesk = await pb.evaluate(() => document.activeElement?.id || document.activeElement?.tagName);
    check("crossing 720 px with «فهمت» focused: focus stays on it, or on the ticket heading when the card is hidden (RR-1)",
      toPhone === "ticketTitle" && toDesk === "introOk", `${toPhone} | ${toDesk}`);
    await pb.click("#introOk");
    check("with storage blocked the inbox works, and the card shows and closes", okB && await pb.evaluate(() => document.getElementById("intro").hidden));
    await done(pb, "no-storage");

    // 4b. Pages fed a changed /api/meta or run (routes in this browser only; the server is as above).
    // J4: the author's cache-only demo is labelled as a replay: a banner, the dialog, the stage times.
    const json = (pattern, edit) => (pg) => pg.route(pattern, async (r) => {
      const res = await r.fetch();
      const j = await res.json();
      edit(j);
      await r.fulfill({ response: res, json: j });
    });
    const pc = await open(pass.viewport, "light", "cache-only", null, async (pg) => {
      await json("**/api/meta", (j) => { j.cache_only = true; j.live = { available: true, reason_ar: null }; })(pg);
      await json("**/api/run?name=*", (j) => j.tickets.forEach((r) => r.events.forEach((e) => { if (e.data?.usage) e.data.usage.cached = true; })))(pg);
    });
    await pc.click("#introOk");
    const banner = await t(pc, "#banners");
    await pc.click("#newTicket");
    const cacheNote = await t(pc, "#newNote");
    await pc.keyboard.press("Escape");
    await pc.click("#modeProcess");
    await pc.waitForSelector("#ovTitle", { timeout: 10000 });
    const liveLine = await t(pc, ".overview .live-line");   // the overview's header says it (5 Nov: not the side list)
    await pc.locator("table.grid tbody tr", { hasText: DRAFTED }).first().locator(".row-open").click();
    await pc.waitForSelector(".trace .gold table", { timeout: 10000 });
    const cls = await t(pc, "#st-classify .state");
    check("cache-only: a banner, the dialog and the overview's header say it replays stored replies, and each model stage «من الكاش» (J4)",
      banner.includes("إعادة من الكاش") && cacheNote.includes("إعادة من الكاش") && liveLine.includes("إعادة من الكاش")
      && cls.includes("من الكاش") && !(await t(pc, "#st-gate .state")).includes("الكاش"), `${banner} | ${cacheNote} | ${cls}`);
    check("T17: replaying the cache, the dialog does not say the text goes abroad (nothing is sent)", !cacheNote.includes("برا العراق"), cacheNote);
    await done(pc, "cache-only");
    // T17: live runs on and real (REAL_DATA=1): the dialog says the text goes to a model provider abroad;
    // no development badge.
    const pl = await open(pass.viewport, "light", "live-on", null,
      json("**/api/meta", (j) => { j.live = { available: true, reason_ar: null }; j.real_data = true; }));
    await pl.click("#introOk");
    await pl.click("#newTicket");
    const liveNote = await t(pl, "#newNote");
    check("T17: with live runs on, the dialog says the text goes to an outside model provider abroad; REAL_DATA=1 has no badge",
      liveNote.includes("مزوّد نموذج خارجي برا العراق") && liveNote.includes("المسموح بإرسالها") && !(await pl.isVisible("#devBadge")), liveNote);
    await pl.keyboard.press("Escape");
    await done(pl, "live-on");
    // RR-3: the run note with one escalation, and with a reason only some of them share.
    const keepEsc = (keep, extra) => json("**/api/run?name=*", (j) => {
      let n = 0;
      j.tickets = j.tickets.filter((r) => r.result.outcome !== "escalated" || ++n <= keep);
      if (extra) j.tickets.filter((r) => r.result.outcome === "escalated").slice(0, 2).forEach((r) => r.result.flags.push(extra));
    });
    // (The note is in «كيف يشتغل»'s overview since 5 Nov.)
    const noteOf = async (pg) => {
      await pg.click("#modeProcess");
      await pg.waitForSelector("#runNote", { timeout: 10000 });
      return t(pg, "#runNote");
    };
    const p1 = await open(pass.viewport, "light", "one-escalation", null, keepEsc(1));
    const one = await noteOf(p1);
    await done(p1, "one-escalation");
    // A second reason a fraud escalation can carry: a gate flag from the first model, before a re-check
    // that said fraud (account_risk was used here until 5 Nov, when it stopped being an escalation).
    const p6 = await open(pass.viewport, "light", "mixed-reasons", null, keepEsc(6, "ref_not_in_text"));
    const mixed = await noteOf(p6);
    await done(p6, "mixed-reasons");
    check("the run note: «صعّد تذكرة وحدة: احتمال احتيال.» and «كلها …، ومنها 2 …» (RR-3)",
      one === "بهالتشغيل النظام صعّد تذكرة وحدة: احتمال احتيال." && mixed.startsWith("بهالتشغيل النظام صعّد 6 تذاكر، كلها احتمال احتيال، ومنها 2 "),
      `${one} | ${mixed}`);
    // 5 Nov: a blocked account or a SIM change keeps its draft, flagged account_risk, and approve waits
    // for «تأكدت من هوية الزبون». The committed run predates the rule; the server gives it the flag as
    // run.py does now (5 Nov review: before, a browser route had to), marked account_risk_recomputed.
    // Nothing is approved here: the decision log is the one the 80 decisions below are counted in.
    const pr = await open(pass.viewport, "light", "account-risk");
    const served = await pr.evaluate(async (name) => {
      const token = document.querySelector('meta[name="viewer-token"]').content;
      const j = await fetch(`/api/run?name=${encodeURIComponent(name)}`, { headers: { "X-Viewer-Token": token } }).then((r) => r.json());
      const rows = j.tickets.filter((r) => (r.result.flags || []).includes("account_risk"));
      return { ids: rows.map((r) => r.ticket.id), marked: rows.filter((r) => r.result.account_risk_recomputed && r.result.draft_ar).length };
    }, RUN);
    const risky = new Set(served.ids);
    await pr.click("#introOk");
    const rk = served.ids[0];
    await openId(pr, rk);
    const callout = await t(pr, "#agentMain .callout-warn");
    const ask = await t(pr, "#confirmTitle");
    const tickWords = await t(pr, ".confirm-check");
    const offBefore = await pr.getAttribute("#approveBtn", "aria-disabled");
    const whyStep = await t(pr, "#whyBody");
    check(`account_risk (${risky.size} tickets, ${rk} opened): «تحتاج تأكيد» with its draft, no forward, the identity line and «ليش؟» says why`,
      risky.size === 6 && served.marked === 6 && !risky.has("t2-0009") && (await t(pr, `#opt-${rk} .row-word`)) === "تحتاج تأكيد"
      && (await pr.getAttribute("#tab-flagged", "aria-selected")) === "true"
      && (await pr.locator("#draft").count()) === 1 && (await pr.locator("#forwardBtn").count()) === 0
      && callout === "تحتاج تأكيد: حساب مقفول أو تبديل شريحة. تأكد من هوية الزبون حسب الإجراءات قبل لا تعتمد، ولا تكتب بالرد إنه صار أي تغيير على الحساب."
      && whyStep.includes("علّمناها للتأكيد لأن نوعها «") && whyStep.includes("حسب الإجراءات قبل لا تعتمد"),
      `${[...risky].join(",")} | ${served.marked} | ${callout} | ${whyStep.slice(-200)}`);
    await pr.evaluate(() => document.activeElement?.blur());
    await pr.keyboard.press("Control+Enter");
    await waitUntil(async () => (await t(pr, "#status")).includes("أشّر على"), 3000, "the refusal").catch(() => {});
    const refusedWith = await t(pr, "#status");
    await pr.check("#ackBox");
    await sleep(100);
    check("account_risk: approve stays off until «تأكدت من هوية الزبون» is ticked, then it is on",
      ask === "تأكد من هوية الزبون حسب الإجراءات" && tickWords === "تأكدت من هوية الزبون" && offBefore === "true"
      && refusedWith.includes("«تأكدت من هوية الزبون»") && (await pr.getAttribute("#approveBtn", "aria-disabled")) === null
      && decisions().length === 0, `${ask} | ${tickWords} | ${offBefore} | ${refusedWith} | ${decisions().length}`);
    // «كيف يشتغل» scores the six against the rule (the gold files predate it) and says so.
    await pr.click("#modeProcess");
    await pr.waitForSelector("#ovTitle", { timeout: 10000 });
    const outcomeStat = await pr.evaluate(() => [...document.querySelectorAll(".overview .stat")].find((x) => x.querySelector("span")?.textContent === "النتيجة صحيحة")?.querySelector("b")?.textContent);
    const ruleNote = await t(pr, "#ruleNote");
    await pr.locator("table.grid tbody tr", { hasText: rk }).first().locator(".row-open").click();
    await pr.waitForSelector(".trace .gold table", { timeout: 10000 });
    const goldRow = await pr.evaluate(() => [...document.querySelectorAll(".trace .gold tbody tr")].find((r) => r.querySelector("th")?.textContent === "النتيجة")?.textContent || "");
    const resBox = await t(pr, "#pResult .result");
    check(`«كيف يشتغل»: outcome 74/80 by the 5 Nov rule, said in the overview, and ${rk}'s expected «تحتاج تأكيد» with ✓ and the note`,
      outcomeStat === "74/80" && ruleNote.includes("6 تذاكر حساب مقفول أو تبديل شريحة") && ruleNote.includes("انعلّمت هسه بنفس القاعدة")
      && goldRow.includes("تحتاج تأكيد (قاعدة 5 تشرين الثاني)") && goldRow.includes("✓") && !goldRow.includes("✗")
      && resBox.includes("أقدم من قاعدة 5 تشرين الثاني"), `${outcomeStat} | ${ruleNote} | ${goldRow} | ${resBox.slice(0, 300)}`);
    await done(pr, "account-risk");

    // 5. The phone (390 px): the card is above the queue; a ticket opens with its action bar in place.
    const pp = await open(pass.phoneViewport, "light", "phone");
    check("phone: the intro card is above the queue", (await pp.isVisible("#intro"))
      && await pp.evaluate(() => document.getElementById("intro").parentElement.id === "agentNav"));
    const [sw, iw] = await pp.evaluate(() => [document.documentElement.scrollWidth, innerWidth]);
    check("phone: no sideways scroll with the card", sw <= iw, `${sw} > ${iw}`);
    await pp.click("#introOk");
    await pp.click("#tab-drafted");
    await pp.locator(`#queueList [data-key="${DRAFTED}"]`).click();
    await waitUntil(() => pp.evaluate(() => document.body.dataset.screen === "ticket"), 3000, "the phone ticket screen");
    await sleep(200);
    const bar = await pp.evaluate(() => [document.getElementById("actionBar").getBoundingClientRect().bottom, innerHeight]);
    check("phone: the action bar sits at the bottom", Math.abs(bar[0] - bar[1]) <= 1, JSON.stringify(bar));
    // For the image: the end of the customer's message, the draft and the action bar on one screen.
    const seen = await pp.evaluate(() => {
      const c = document.querySelector(".composer").getBoundingClientRect();
      const top = document.getElementById("actionBar").getBoundingClientRect().top;
      scrollBy(0, c.height <= top - 140 ? c.bottom - (top - 12) : c.top - 140);
      const head = document.querySelector(".composer-label").getBoundingClientRect(), box = document.getElementById("draft").getBoundingClientRect();
      return [head.top >= 0 && head.bottom <= document.getElementById("actionBar").getBoundingClientRect().top, box.top < document.getElementById("actionBar").getBoundingClientRect().top - 60];
    });
    await sleep(150);
    check("phone: the draft's heading and text show above the action bar (J10)", seen.every(Boolean), JSON.stringify(seen));
    await demo(pp, "inbox-phone");
    // 5 Nov review: a tap on the «؟» marker shows its tip (pinned); keyboard focus on it scrolls nothing sideways.
    {
      await pp.evaluate(() => scrollTo(0, 0));
      const tipOn = () => pp.evaluate(() => getComputedStyle(document.querySelector(".customer .facts [role=tooltip]")).visibility === "visible");
      await pp.locator(".customer .fact-tip").tap();
      await sleep(150);
      const tapped = await tipOn();
      const sw1 = await pp.evaluate(() => document.documentElement.scrollWidth <= innerWidth);
      await pp.locator(".customer .fact-tip").tap();
      await sleep(350);
      const untapped = !(await tipOn());
      await pp.focus(".customer .fact-btn");
      await pp.keyboard.press("Tab");
      await sleep(150);
      const focused = await tipOn();
      const sw2 = await pp.evaluate(() => [document.documentElement.scrollWidth, innerWidth]);
      check("5 Nov review: phone: a tap on «؟» shows its tip and a second tap hides it; keyboard focus shows it with no sideways scroll",
        tapped && sw1 && untapped && focused && sw2[0] <= sw2[1], JSON.stringify({ tapped, sw1, untapped, focused, sw2 }));
    }
    await done(pp, "phone");

    // 6. Dark.
    const pd = await open(pass.viewport, "dark", "dark");
    await pd.click("#introOk");
    await openId(pd, DRAFTED);
    await demo(pd, "inbox-dark");
    await done(pd, "dark");

    // 7. Decide all 80 through the page: two edits, a take-over and a priority correction with their
    // reasons, every other draft approved (ticked first where it asks) and every escalation forwarded.
    // A script decides in well under 3 s each: the summary itself says these are not an opinion.
    await p.click("#modeAgent");   // back from «كيف يشتغل» only now: the clock was paused meanwhile
    await p.waitForSelector("#ticketTitle", { state: "attached" });
    await p.evaluate(() => document.getElementById("main").focus());
    let edits = 0, took = 0, fixed = 0, moved = 0, ranOut = 0;
    for (let guard = 0; guard < 200; guard++) {
      if (await p.locator("#doneTitle").count()) break;
      const st = await p.evaluate(() => ({ fwd: !!document.getElementById("forwardBtn"), ack: !!document.getElementById("ackBox"),
        draft: !!document.getElementById("draft"), key: document.querySelector("#queueList [aria-selected=true]")?.dataset.key }));
      const n0 = decisions().length;
      if (st.fwd) {
        await p.click("#forwardBtn");
      } else if (st.draft && !st.ack && edits < 2) {
        edits++;
        await p.focus("#draft");
        await p.evaluate(() => { const x = document.getElementById("draft"); x.setSelectionRange(x.value.length, x.value.length); });
        await p.keyboard.type(" وشكراً لصبرك.");
        await p.evaluate(() => { document.getElementById("reasonBox").open = true; });
        await p.locator(".reason-chip", { hasText: "الأسلوب ما يناسب" }).click();
        await waitUntil(async () => !(await p.locator("#draftChecks .checks-state").count())
          && (await p.getAttribute("#approveBtn", "aria-disabled")) === null, 5000, "the edit to be checked");
        await p.click("#approveBtn");
      } else if (st.draft && !st.ack && took < 1) {
        took++;
        await p.click("#takeBtn");
        await p.locator(".reason-chip", { hasText: "ناقصة سؤال للزبون" }).click();
        await p.click("#takeBtn");
      } else if (st.draft && !st.ack && fixed < 1) {
        fixed++;
        await p.click("#fixToggle");
        await p.selectOption("#fixPrio", (await p.inputValue("#fixPrio")) === "P1" ? "P2" : "P1");
        await p.evaluate(() => { document.getElementById("reasonBox").open = true; });
        await p.locator(".reason-chip", { hasText: "الأولوية غلط" }).click();
        await p.click("#approveBtn");
      } else {
        if (st.ack) await p.check("#ackBox");
        await p.click("#approveBtn");
      }
      await waitUntil(() => decisions().length > n0, 5000, `the decision on ${st.key}`);
      await waitUntil(async () => (await t(p, "#status")).includes(st.key), 3000, "its toast");
      if ((await t(p, "#status")).includes("انتقلنا")) moved++;
      if ((await t(p, "#status")).includes("ماكو بعد تذاكر «")) ranOut++;
    }
    await p.waitForSelector("#doneTitle", { timeout: 5000 });
    await p.click("#toastClose").catch(() => {});
    await sleep(300);
    const sum = await t(p, ".all-done");
    check("all 80 decided through the page: the session summary counts them", decisions().length === 80
      && (await t(p, "#queueTitle")).replace(/\s+/g, " ").includes("خلصت 80 من 80") && sum.includes("قررت على 80 تذكرة")
      && sum.includes("انحسمت بأقل من 3 ثواني"), `${decisions().length} | ${sum.slice(0, 160)}`);
    check(`each move to another tab was said in the toast (${moved} times)`, moved >= 2, String(moved));
    // T28 (user tests, 7 Nov): each approved flagged ticket logs the points ticked for it, the missing
    // field and the type after a disagreement included, as kinds.
    const points = decisions().filter((d) => ["approved", "edited"].includes(d.action) && d.pipeline_outcome === "flagged");
    const unlogged = points.filter((d) => d.flags.some((f) => (f === "recheck_used_second" || f.startsWith("missing:"))
      && !d.warnings_acknowledged.includes(f)));
    check(`T28: ${points.length} approved flagged tickets log every point ticked (missing field, type)`,
      points.length > 0 && unlogged.length === 0, JSON.stringify(unlogged.slice(0, 3)));
    check(`a tab that ran out was said with «ماكو بعد», «خلصت» kept for decisions (${ranOut} times) (J8)`, ranOut >= 1
      && !(await t(p, "#status")).includes("خلصت تذاكر"), String(ranOut));
    await demo(p, "inbox-done");
    // 5 Nov review: a decided blocked account or SIM change says the identity was confirmed, as its log line does.
    {
      const rid = "t2-0007";
      await openId(p, rid);
      const dRec = decisions().find((d) => d.ticket_id === rid && d.action !== "undone");
      check(`the decided ${rid} says «تأكدت من هوية الزبون قبل الاعتماد.», and its log line keeps the tick`,
        (await t(p, ".decided")).includes("تأكدت من هوية الزبون قبل الاعتماد.") && (dRec?.warnings_acknowledged || []).includes("account_risk"),
        `${await t(p, ".decided")} | ${JSON.stringify(dRec)}`);
      const todo = await p.evaluate(() => ({ line: !!document.getElementById("whyLine"), ask: [...document.querySelectorAll("#sumBox .summary-note")].some((n) => n.textContent.includes("المفروض تسأل")) }));
      await openId(p, DRAFTED);
      const todo2 = await p.evaluate(() => [...document.querySelectorAll("#sumBox .summary-note")].some((n) => n.textContent.includes("المفروض تسأل")));
      check(`5 Nov review: decided tickets keep no to-do line (${rid}: no «تحتاج تأكيد» banner; ${DRAFTED}: no «المسودة المفروض تسأل عن»)`,
        !todo.line && !todo.ask && !todo2, JSON.stringify({ todo, todo2 }));
    }
    await done(p, "fresh");
    check("no live run was started (no request to /api/stream)", streams === 0, String(streams));
  } catch (e) {
    check("the pass ran to its end", false, e.stack || e.message);
  } finally {
    for (const c of contexts) await c.close().catch(() => {});
    await stopServer(srv);
  }
  check("no console errors, CSP violations or requests to another host", problems.length === 0, problems.slice(0, 8).join(" | "));
}

// --- main ---

(async () => {
  const guard = setTimeout(() => { console.error("smoke: gave up after 6 minutes"); process.exit(2); }, 6 * 60 * 1000);
  let browser;
  try {
    browser = await chromium.launch();
    for (const pass of PASSES) {
      const t0 = Date.now();
      await (pass.fresh ? runFresh(browser, pass) : runPass(browser, pass));
      const mine = results.filter((r) => r.pass === pass.name);
      console.log(`\n${pass.name} (${((Date.now() - t0) / 1000).toFixed(1)} s): ${mine.filter((r) => r.ok).length}/${mine.length} passed`);
      for (const r of mine) console.log(`  ${r.ok ? "ok  " : "FAIL"} ${r.name}${r.ok ? "" : `\n         ${r.detail.split("\n").slice(0, 6).join("\n         ")}`}`);
    }
  } finally {
    await browser?.close().catch(() => {});
    clearTimeout(guard);
  }
  const failed = results.filter((r) => !r.ok);
  console.log(`\n${results.length - failed.length}/${results.length} checks passed${failed.length ? `, ${failed.length} FAILED` : ""}.`);
  process.exit(failed.length || !results.length ? 1 : 0);
})().catch((e) => { console.error("smoke: script error", e); process.exit(1); });
