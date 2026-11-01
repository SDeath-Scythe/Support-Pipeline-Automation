#!/usr/bin/env node
// Smoke test of the viewer in a real browser (Chromium through Playwright).
//
//   node tests/ui/smoke.cjs                      run every pass, print a pass/fail list
//   node tests/ui/smoke.cjs --screens <dir>      also save screenshots there
//   node tests/ui/smoke.cjs --pass desk-light    run one pass (desk-light, desk-dark, phone-light, phone-dark)
//
// Each pass starts its own viewer (python app/server.py) with no API key in its environment,
// PIPELINE_MODE=off (no model is ever called: a pasted ticket goes straight to a person) and a fresh
// decision log in a temporary folder, then drives the agent inbox and the "كيف يشتغل" mode on the
// committed final run (saved/test2/final). The server is stopped in a finally block. Exit code 0 only
// if every check passed.

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
const EXPECT = { flagged: 9, escalated: 6, drafted: 65, total: 80, type: "78/80", priority: "79/80" };
const SECRET_ASK = " دزلنا الرمز اللي وصلك";

const args = process.argv.slice(2);
const argVal = (name) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : null; };
const SCREENS = argVal("--screens");
const ONLY = argVal("--pass");
if (SCREENS) fs.mkdirSync(SCREENS, { recursive: true });

const PASSES = [
  { name: "desk-light", viewport: { width: 1366, height: 850 }, scheme: "light", phone: false },
  { name: "desk-dark", viewport: { width: 1366, height: 850 }, scheme: "dark", phone: false },
  { name: "phone-light", viewport: { width: 360, height: 780 }, scheme: "light", phone: true },
  { name: "phone-dark", viewport: { width: 360, height: 780 }, scheme: "dark", phone: true },
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

async function startServer() {
  for (let attempt = 0; attempt < 5; attempt++) {
    const port = 20000 + Math.floor(Math.random() * 30000);
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "viewer-smoke-"));
    const decisions = path.join(dir, "decisions.jsonl");
    const env = { ...process.env, PIPELINE_MODE: "off", PORT: String(port), DECISIONS_FILE: decisions };
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
      if (allowRefusals > 0 && /Failed to load resource: the server responded with a status of (413|409)/.test(m.text())) { allowRefusals--; return; }
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
    await waitUntil(async () => (await statusN()) > s0 && (await text("#status")).includes(d.ticket_id), 5000, `the page to show ${what}`);
    return d;
  };
  const approveKey = () => (pass.phone ? page.click("#approveBtn") : page.keyboard.press("Control+Enter"));
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
    const kf = await p.evaluate(() => getComputedStyle(document.querySelector(".why-toggle kbd.kbd-ar")).fontFamily);
    check("TYPE-1: an Arabic key letter uses IBM Plex Sans Arabic", /IBM Plex Sans Arabic/.test(kf.split(",")[0]), kf);
    const bh = await p.evaluate(() => [document.getElementById("actionBar").getBoundingClientRect().height, parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--bar-h"))]);
    check("A11Y-1: --bar-h follows the action bar's real height", Math.abs(bh[0] - bh[1]) <= 2, JSON.stringify(bh));
    // L7: Ctrl+Enter on an escalation says what to do.
    await p.evaluate(() => document.activeElement?.blur());
    await p.keyboard.press("Control+Enter");
    await waitUntil(async () => (await t(p, "#status")).includes("متصعّدة"), 2000, "the escalation hint").catch(() => {});
    check("L7: Ctrl+Enter on an escalation says to forward or take it", (await t(p, "#status")).includes("حوّلها"), await t(p, "#status"));
    // A11Y-2: closing the why panel puts focus on its toggle, not on <body>.
    await p.focus("#whyClose");
    await p.keyboard.press("Enter");
    await sleep(150);
    check("A11Y-2: closing «ليش؟» moves focus to its toggle", /why-toggle/.test(await active(p)), await active(p));
    await p.keyboard.press("w");

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
        && (await t(p, "#titleChips")).includes((meta.teams[meta.subcategories[run.tickets.find((r) => r.ticket.id === flagged).result.recheck_alternative].team] || {}).label_ar || "?"),
      `${ticked} | ${await t(p, "#confirmBox")}`);
      await p.check('#choiceBox input[value="second"]');
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
    const tk = await pAct(() => p.keyboard.press("t"), "the take-over");
    check("M1: the second T records the take-over", tk.action === "took_over" && tk.ticket_id === m1, JSON.stringify(tk));
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
    const free = run.tickets.map((r) => r.ticket.id).filter((i) => !decidedIds().has(i)).at(-1);
    const post = (body) => p.evaluate(async (b) => {
      const token = document.querySelector('meta[name="viewer-token"]').content;
      const r = await fetch("/api/decision", { method: "POST", headers: { "X-Viewer-Token": token, "Content-Type": "application/json" }, body: JSON.stringify(b) });
      return [r.status, await r.json()];
    }, body);
    const base = { run: RUN, ticket_id: free, pipeline_outcome: "drafted", flags: [], reason_codes: [], seconds: 9, corrected: {} };
    allowRefusals = 2;   // the two 409s below are asked for
    const [st1] = await post({ ...base, action: "approved", draft_text: "هلا", final_text: "هلا، دزلنا الرمز اللي وصلك" });
    const [st2] = await post({ ...base, action: "took_over" });
    const [st3, j3] = await post({ ...base, action: "took_over" });
    check("SEC-1 / F8: the server refuses a secret request (409) and a second decision on one ticket (409)", st1 === 409 && st2 === 200 && st3 === 409 && j3.conflict === "decided", `${st1} ${st2} ${st3}`);
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
    check("A11Y-3: after «شغّلها» focus is on the new ticket and its end is announced", (await active(p)) === "ticketTitle"
      && (await t(p, "#status")).includes("خلصت المعالجة"), `${await active(p)} | ${await t(p, "#status")}`);
    check("L2: a ticket with no team: take over is the main action and «ناقص» says nothing read it",
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
    check(`tab counts 9 / 6 / 65 / 0 match the run (${JSON.stringify(counts)})`,
      counts.flagged === EXPECT.flagged && counts.escalated === EXPECT.escalated && counts.drafted === EXPECT.drafted && counts.done === 0
      && counts.flagged === fromRun.flagged && counts.escalated === fromRun.escalated && counts.drafted === fromRun.drafted, JSON.stringify({ counts, fromRun }));
    const tabWords = await page.evaluate(() => [...document.querySelectorAll("[role=tab] .tab-label")].map((x) => x.textContent));
    check("the four tabs: تحتاج تأكيد، متصعّدة، جاهزة، خلصت", tabWords.join("|") === "تحتاج تأكيد|متصعّدة|جاهزة|خلصت", tabWords.join("|"));
    check("counter «خلصت 0 من 80»", /خلصت\s*0\s*من\s*80/.test(await text("#queueTitle")), await text("#queueTitle"));
    check("saved-run note and the no-send badge are shown",
      (await page.isVisible("#savedNote")) && (await text(".no-send")).includes("ما ينرسل شي للزبون تلقائياً"));
    await shot(page, "inbox");
    if (pass.phone) await noHScroll("queue screen");

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
      const approvedId = decisions().at(-1).id;
      const d = await act(() => (pass.phone ? page.click("#toastUndo") : page.keyboard.press("Control+z")), "the undo");
      check("undo logs «undone» with undoes = the approve's id", d.action === "undone" && d.undoes === approvedId && d.ticket_id === k1, JSON.stringify(d));
      await waitUntil(async () => (await selected()) === k1, 3000, "the undone ticket to reopen");
      check("the undone ticket is back in «جاهزة» (65)", (await text("#tab-drafted .tab-count")).replace(/\D/g, "") === "65", await text("#tab-drafted .tab-count"));
      // approve it again: it is one of the tickets the reload must bring back
      await act(approveKey, "the second approve");
    }

    // 5. A flagged ticket: approve stays off until the box is ticked.
    let k2;
    {
      k2 = await openTab("flagged");
      check(`flagged ${k2}: approve is disabled and reads «تأكدت، اعتمد»`,
        (await page.getAttribute("#approveBtn", "aria-disabled")) === "true" && (await text("#approveBtn")).includes("تأكدت، اعتمد"), await text("#approveBtn"));
      check("flagged: the box names what to check", (await text("#confirmBox")).includes("تأكد من"), await text("#confirmBox"));
      const n0 = decisions().length;
      // a tap on the aria-disabled button (force: Playwright itself won't click an aria-disabled one)
      if (pass.phone) await page.click("#approveBtn", { force: true }); else await page.keyboard.press("Control+Enter");
      await sleep(400);
      check("flagged: approving before the tick does nothing", decisions().length === n0 && (await selected()) === k2);
      await shot(page, "flagged");
      await page.check("#ackBox");
      check("flagged: approve is enabled after the tick", (await page.getAttribute("#approveBtn", "aria-disabled")) === null);
      const d = await act(() => page.click("#approveBtn"), "the flagged approve");
      check(`flagged approve logs «approved» for ${k2}`, d.action === "approved" && d.ticket_id === k2 && d.pipeline_outcome === "flagged", JSON.stringify(d));
    }

    // 6. An edit that asks for the code blocks approval until it is gone; a harmless edit logs «edited».
    let k3;
    {
      k3 = await openTab("drafted");
      if (pass.phone) await page.click("#draft"); else await page.keyboard.press("e");
      check("the draft takes focus", await page.evaluate(() => document.activeElement?.id === "draft"));
      await page.evaluate(() => { const t = document.getElementById("draft"); t.setSelectionRange(t.value.length, t.value.length); });
      await page.keyboard.type(SECRET_ASK);
      await page.waitForSelector("#draftChecks .check-item.is-blocking", { timeout: 6000 });
      check("an edit asking for the code blocks approval", (await page.getAttribute("#approveBtn", "aria-disabled")) === "true"
        && (await text("#approveWhy")).includes(meta.check_ar.asks_secret.split(/[:،(]/)[0].trim()), await text("#approveWhy"));
      check("the label becomes «معدّلة منك»", (await text(".composer-label")).includes("معدّلة منك"), await text(".composer-label"));
      check("the phrase is highlighted in the draft", (await page.locator(".composer-mirror mark.finding.is-blocking").count()) === 1);
      const n0 = decisions().length;
      await page.keyboard.press("Control+Enter");   // from inside the draft
      await sleep(500);
      check("Ctrl+Enter inside a blocked draft does not approve", decisions().length === n0 && (await selected()) === k3);
      await shot(page, "blocked");
      await page.click("text=رجّع المسودة الأصلية");
      await waitUntil(async () => (await page.getAttribute("#approveBtn", "aria-disabled")) === null, 4000, "approve to be enabled again");
      check("restoring the draft enables approval", true);
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
      if (pass.phone) await noHScroll("escalated ticket");
      await shot(page, "escalated");
      const d = await act(() => (pass.phone ? page.click("#forwardBtn") : page.keyboard.press("f")), "the forward");
      check(`forward logs «forwarded» for ${k4}`, d.action === "forwarded" && d.ticket_id === k4 && d.pipeline_outcome === "escalated", JSON.stringify(d));
    }

    // 8. Reload: the decided tickets come back from the log.
    {
      await page.reload();
      await page.waitForSelector("#ticketTitle", { state: "attached", timeout: 15000 });
      await waitUntil(async () => /خلصت\s*4\s*من\s*80/.test(await text("#queueTitle")), 5000, "the counter after reload").catch(() => {});
      check("after a reload the counter is «خلصت 4 من 80»", /خلصت\s*4\s*من\s*80/.test(await text("#queueTitle")), await text("#queueTitle"));
      if (pass.phone) {
        if (await page.evaluate(() => document.body.dataset.screen === "ticket")) await page.locator("#agentMain .back-btn").first().click();
        await page.click("#tab-done");
      } else {
        await page.keyboard.press("4");
      }
      await sleep(150);
      const done = await page.evaluate(() => [...document.querySelectorAll("#queueList [role=option]")].map((o) => o.dataset.key).sort());
      check("the «خلصت» tab lists the four decided tickets", JSON.stringify(done) === JSON.stringify([k1, k2, k3, k4].sort()), done.join(","));
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
      await page.click("#modeProcess");
      await page.waitForSelector("#ovTitle", { timeout: 10000 });
      const stats = await text(".overview .stats");
      check(`overview: type ${EXPECT.type}, priority ${EXPECT.priority}`, stats.includes(EXPECT.type) && stats.includes(EXPECT.priority), stats.slice(0, 200));
      await shot(page, "process-overview");
      if (pass.phone) await noHScroll("process overview");
      await page.locator("table.grid tbody tr.click", { hasText: "t2-0001" }).first().click();   // drafted: classify and draft
      await page.waitForSelector(".trace .gold table", { timeout: 10000 });   // the replay has reached the result
      const io = await page.locator(".trace details.io").count();
      const gold = await text(".trace .gold .note");
      check(`trace shows the model input and output (${io} blocks), the rationale label and the gold table`, io >= 2
        && (await text(".trace")).includes("تفسير النموذج (إنكليزي)") && gold.includes("الجواب المتوقع") && !gold.includes("undefined"), gold);
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
      await page.waitForFunction(() => document.querySelector("#opt-live-1") && !document.querySelector("#opt-live-1.st-running"), null, { timeout: 15000 });
      check("the live ticket ends escalated", await page.evaluate(() => document.querySelector("#opt-live-1").classList.contains("st-escalated")));
      const offWord = meta.flag_ar.pipeline_off.split(/[:،]/)[0].trim();
      check(`the live ticket says why: «${offWord}»`, (await selected()) === "live-1" && (await text("#agentMain")).includes(offWord), (await text("#agentMain")).slice(0, 200));
      await shot(page, "live");
      // the first press offers the optional reasons, the second records
      const d = await act(async () => {
        if (pass.phone) { await page.click("#takeBtn"); await page.click("#takeBtn"); } else { await page.keyboard.press("t"); await page.keyboard.press("t"); }
      }, "the live take-over");
      check("taking over the live ticket logs run «live» with flag pipeline_off", d.run === "live" && d.ticket_id === "live-1" && d.action === "took_over"
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
      await noHScroll("after the flows");
      await page.locator("#agentMain .back-btn").first().click();
      check("phone: back returns to the queue", await page.isVisible("#queueList"));
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

// --- main ---

(async () => {
  const guard = setTimeout(() => { console.error("smoke: gave up after 6 minutes"); process.exit(2); }, 6 * 60 * 1000);
  let browser;
  try {
    browser = await chromium.launch();
    for (const pass of PASSES) {
      const t0 = Date.now();
      await runPass(browser, pass);
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
