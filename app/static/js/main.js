// Start-up and the parts every mode shares: the header (mode switch, source, new ticket, shortcuts),
// the banners, and the wiring between the agent inbox, the process view and live runs.

import { NetworkError, ServerError, getJSON, onTrouble } from "./api.js";
import * as inbox from "./inbox.js";
import { initKeys } from "./keyboard.js";
import { CACHE_AR, cancelLive, initNewTicket, liveState, rerun, setLiveHooks } from "./live.js";
import * as proc from "./process.js";
import { OUTCOME_SHORT } from "./labels.js";
import { S, correctedFor, findItem, mostUrgent, pauseClock, restoreDecisions, startClock, tabOf, uid } from "./state.js";
import { clearBanner, hideToast, initToast, setBanner, showToast } from "./ui.js";
import { dict, el, isPhone, loadPrefs, savePrefs, ticketId, ticketsText } from "./util.js";

const $ = (id) => document.getElementById(id);
const save = () => savePrefs(S.prefs);
// «ليش؟» starts closed. It opens on load only if the agent opened it and left it open, and only where it
// is a column of its own beside the ticket (over 1000 px): never as a drawer over the ticket, never on a
// phone, where it is a section under the ticket.
const whyOnLoad = () => !!S.prefs.whyOpen && matchMedia("(min-width: 1001px)").matches;

async function init() {
  S.prefs = loadPrefs();
  S.mode = "agent";   // every visit starts in the inbox (the mode is not kept)
  initToast();
  onTrouble(trouble);
  inbox.setWhyOpen(whyOnLoad());
  document.body.classList.toggle("keys-off", !S.prefs.singleKeys);
  document.body.dataset.screen = "queue";
  watchSizes();
  initIntro();
  setMode(S.mode, { quiet: true });
  S.agent.loading = true;
  inbox.renderQueue();
  inbox.renderTicket();
  try {
    const [meta, runs, sets] = await Promise.all(["/api/meta", "/api/runs", "/api/sets"].map((u) => getJSON(u)));
    // Maps read with keys that come from run files: no inherited keys (a flag "constructor" is unknown).
    for (const k of ["flag_ar", "teams", "subcategories", "check_ar", "reason_codes_ar", "decision_actions_ar"]) meta[k] = dict(meta[k]);
    S.meta = meta;
    S.runs = runs;
    S.sets = sets;
  } catch (e) {
    S.agent.loading = false;
    S.agent.error = e instanceof ServerError ? e.message : "انقطع الاتصال بالخادم: تأكد إنه شغّال.";
    $("agentQueue").replaceChildren();
    $("agentMain").replaceChildren(el("div", { class: "empty-state" }, el("h2", { class: "empty-title", text: "ما كدرنا نفتح الصفحة" }),
      el("p", { text: S.agent.error }), el("button", { type: "button", class: "btn", text: "جرب مرة ثانية", onclick: () => location.reload() })));
    return;
  }
  wire();
  modeBanners();
  buildSourcePicker();
  await loadAgentSource($("source").value || null);
  if (S.mode === "process") await proc.renderProcess();
}

function wire() {
  inbox.setInboxHooks({
    toProcess: (it) => toProcess(it),
    newTicket: () => openNew(),
    rerun: async (it) => {
      try {
        S.live = S.live.filter((x) => x !== it);
        await rerun(it);
      } catch (e) {
        S.live.push(it);
        showToast(e instanceof ServerError ? e.message : "ما انشغلت التذكرة.");
      }
    },
    cancelLive: (it) => cancelLive(it),
    reload: () => loadAgentSource($("source").value),
    savePrefs: save,
  });
  proc.setProcessHooks({ toAgent: (id) => toAgent(id), savePrefs: save, loadOnPick: (sel, load) => loadOnPick(sel, load) });
  setLiveHooks({
    started: (it) => {
      if (S.mode === "agent") {
        inbox.open(it.key, { user: true, focus: "heading" });
      } else {
        proc.showLive(it);
        inbox.renderQueue();
      }
      updateNewButton();
    },
    updated: (it) => {
      inbox.liveUpdated(it);
      const last = it.events.at(-1);
      if (last) proc.liveEvent(it, last);
      if (it.status !== "running") {
        updateNewButton();
        proc.refreshList();
        // Said once when it ends (never per stage), also when it is the open ticket: a screen-reader
        // user who pressed «شغّلها» learns how it ended.
        const word = it.status === "done" ? "خلصت المعالجة" : "انقطعت المعالجة";
        const out = OUTCOME_SHORT[it.result?.outcome] || (it.status === "done" ? "" : "متصعّدة");
        showToast([`${word}: `, ticketId(it.key), out ? ` · ${out}` : ""]);
      }
    },
    budget: (msg) => { inbox.setBudgetBanner(msg); updateNewButton(); },
  });

  const openNew = initNewTicket();
  $("newTicket").addEventListener("click", openNew);
  updateNewButton();

  $("modeAgent").addEventListener("click", () => setMode("agent"));
  // A live ticket open in the inbox: «كيف يشتغل» opens on its trace (its side list names the live tickets).
  $("modeProcess").addEventListener("click", async () => {
    const it = S.mode === "agent" ? findItem(S.agent.openKey) : null;
    await setMode("process");
    if (it?.live && S.mode === "process") proc.showLiveFromInbox(it);
  });

  const openSheet = initKeys({
    next: () => inbox.move(1),
    prev: () => inbox.move(-1),
    approve: () => inbox.approve(),
    focusDraft: () => inbox.focusDraft(),
    leave: () => inbox.leaveDraft(),
    takeOver: () => inbox.takeOver(),
    disarm: () => inbox.disarm({ focus: true }),
    forward: () => inbox.forward(),
    toggleWhy: () => inbox.toggleWhy(),
    toggleTick: () => inbox.toggleTick(),
    toggleFix: () => inbox.toggleFix(),
    closeFix: (target) => inbox.closeFix(target),
    closeWhy: () => inbox.toggleWhy(false),
    whyIsDrawer: () => inbox.whyIsDrawer(),
    undo: () => inbox.undoLast(),
    tab: (n) => inbox.setTab(["flagged", "escalated", "drafted", "done"][n], { openFirst: true }),
    save: () => { document.body.classList.toggle("keys-off", !S.prefs.singleKeys); save(); },
  });
  $("helpBtn").addEventListener("click", openSheet);
  // Closing the panel from its own button: focus goes to the ticket's «ليش؟» toggle (inbox.toggleWhy).
  $("whyClose").addEventListener("click", () => inbox.toggleWhy(false));

  // The skip link: on the phone's queue screen the ticket is hidden, so it goes to the queue instead.
  document.querySelector(".skip").addEventListener("click", (e) => {
    e.preventDefault();
    const target = isPhone() && document.body.dataset.screen === "queue" && S.mode === "agent"
      ? ($("queueList")?.querySelector('[tabindex="0"]') || $("agentQueue")) : $("main");
    target?.focus();
  });

  // An edited draft, a correction or picked reasons on a ticket that was not decided: warn before the
  // page goes (they live in memory only). They are kept per run, so one on a run that is not on screen
  // counts as undecided.
  addEventListener("beforeunload", (e) => {
    const shown = new Map([...S.live, ...S.agent.items].map((it) => [uid(it), it]));
    const undecided = (u) => !shown.has(u) || !S.decisions.has(shown.get(u).key);
    const open = [...S.edits.keys()].some(undecided)
      || [...S.corrections.keys()].some((u) => undecided(u) && (!shown.has(u) || Object.keys(correctedFor(shown.get(u))).length > 0))
      || [...S.reasons].some(([u, set]) => set.size > 0 && undecided(u));
    if (open) { e.preventDefault(); e.returnValue = ""; }
  });
  // The agent's time on a ticket stops while the page is hidden.
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) pauseClock();
    else if (S.mode === "agent") startClock(findItem(S.agent.openKey), { visit: false });
  });
  // Crossing the phone width only changes the layout (CSS); re-rendering would throw away the draft's
  // check state and the focus. On a phone the open ticket stays on screen.
  matchMedia("(max-width: 720px)").addEventListener("change", () => {
    document.body.dataset.screen = S.agent.openKey ? "ticket" : "queue";
    inbox.setWhyOpen(whyOnLoad());
  });
  // The phone's back gesture (or «القائمة») from a ticket: the queue. Forward again from the queue: that
  // ticket. (Entries from before a reload can hold a ticket too: back from a ticket is always the queue.)
  addEventListener("popstate", () => {
    if (!isPhone() || S.mode !== "agent") return;
    const key = history.state?.ticket;
    if (document.body.dataset.screen === "ticket") inbox.showQueue();
    else if (key && findItem(key)) {
      document.body.dataset.screen = "ticket";
      inbox.open(key, { focus: "heading" });
    }
  });
  // Across 1000 px «ليش؟» turns from a column into a drawer over the ticket (or back): it follows the
  // agent's choice where it is a column, and closes where it would cover the ticket.
  matchMedia("(min-width: 1001px)").addEventListener("change", () => inbox.setWhyOpen(whyOnLoad()));
}

/**
 * The first-visit card («أول مرة هنا؟»): what the page is and what each tab asks. Shown until «فهمت»,
 * remembered in the preferences (when storage is blocked it shows again on the next visit, nothing
 * breaks). It sits above the ticket; on a phone, where the queue is the first screen, above the queue.
 * One node, moved between the two places (never drawn twice, so it is read once).
 */
function initIntro() {
  const card = $("intro");
  // Crossing 720 px drops the focus of a control in the card to <body>: the new width can hide the pane
  // it is in before this code runs, and moving the node blurs it too. Remember what lost it, just now.
  let left = null;
  card.addEventListener("focusout", (e) => { left = { node: e.target, at: performance.now() }; });
  document.addEventListener("focusin", () => { left = null; });
  const place = () => {
    const host = isPhone() ? $("agentNav") : $("main");
    if (card.parentElement === host) return;
    const a = document.activeElement;
    const had = card.contains(a) ? a : (!a || a === document.body) && left && performance.now() - left.at < 1000 ? left.node : null;
    host.prepend(card);
    // Give it back once the layout has followed the width (the other listener picks the phone screen).
    // On a phone's ticket screen the card is hidden with the queue: the ticket's heading takes it.
    if (had) setTimeout(() => (card.offsetParent ? had : $("ticketTitle") || $("main")).focus(), 0);
  };
  place();
  matchMedia("(max-width: 720px)").addEventListener("change", place);
  card.hidden = !!S.prefs.introSeen;
  // From the «?» sheet: the card again, where the work is (the inbox; on a phone, its queue screen).
  $("introAgain").addEventListener("click", async () => {
    S.prefs.introSeen = false;
    save();
    $("sheet").close();
    if (S.mode !== "agent") await setMode("agent");
    if (isPhone()) document.body.dataset.screen = "queue";
    card.hidden = false;
    card.scrollIntoView({ block: "nearest" });
    $("introOk").focus({ preventScroll: true });
  });
  $("introOk").addEventListener("click", () => {
    S.prefs.introSeen = true;
    save();
    card.hidden = true;
    // Focus goes on to the work, never to <body>: the open ticket, or on a phone's queue screen the list.
    const onQueue = isPhone() && document.body.dataset.screen === "queue";
    const next = onQueue ? $("queueList")?.querySelector('[tabindex="0"]') || $(`tab-${S.agent.tab}`) : $("ticketTitle");
    (next || $("main")).focus();
  });
}

/** The action bar's real height (it wraps on narrow screens) and the header's, as CSS variables: the
 *  scroll padding that keeps focus above the bar, the drawer's top and the toast follow them. */
function watchSizes() {
  if (typeof ResizeObserver !== "function") return;
  const root = document.documentElement;
  const top = () => {
    const h = $("topbar").getBoundingClientRect().height + ($("banners").hidden ? 0 : $("banners").getBoundingClientRect().height);
    root.style.setProperty("--top-h", `${Math.round(h)}px`);
  };
  const ro = new ResizeObserver(top);
  ro.observe($("topbar"));
  ro.observe($("banners"));
  let bar = null;
  const barRO = new ResizeObserver(() => {
    const h = bar?.isConnected ? bar.getBoundingClientRect().height : 0;
    if (h) root.style.setProperty("--bar-h", `${Math.ceil(h)}px`);
  });
  // The bar is rebuilt with every ticket: observe the current one.
  new MutationObserver(() => {
    const b = $("actionBar");
    if (b === bar) return;
    if (bar) barRO.unobserve(bar);
    bar = b;
    if (bar) barRO.observe(bar);
  }).observe($("agentMain"), { childList: true, subtree: true });
}

function updateNewButton() {
  const st = liveState();
  const b = $("newTicket");
  b.setAttribute("aria-describedby", "newTicketWhy");
  b.classList.toggle("is-unavailable", !st.ok);
  $("newTicketWhy").textContent = st.ok ? (S.liveBusy ? "اكو تذكرة دتنعالج هسه." : "") : st.reason;
  b.title = st.ok ? "" : st.reason;   // the pointer's hint; a screen reader gets it from aria-describedby
}

function modeBanners() {
  // Not real data (REAL_DATA unset): a quiet word in the header, not a banner.
  $("devBadge").hidden = S.meta.real_data !== false;
  if (S.meta.mode === "off") setBanner("mode", { kind: "warn", title: "النظام موقف:", text: "أي تذكرة جديدة تروح لموظف بدون نموذج." });
  else if (S.meta.mode === "classify_only") setBanner("mode", { kind: "warn", title: "المسودات موقفة.", text: "النظام يصنّف التذاكر ويوجّهها بس، والرد على الموظف." });
  if (S.meta.cache_only && S.meta.live.available) setBanner("cache", { kind: "info", title: "إعادة من الكاش.", text: CACHE_AR });
}

/**
 * A select that loads something when it changes, without loading on every arrow key (WCAG 3.2.2): a
 * pick with the mouse loads at once; a value reached with the keyboard loads on Enter or when the
 * select loses focus.
 */
function loadOnPick(sel, load) {
  let keyed = false, pending = false;
  sel.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && pending) { e.preventDefault(); pending = false; load(sel.value); return; }
    keyed = e.key !== "Enter" && e.key !== "Tab";
  });
  sel.addEventListener("pointerdown", () => { keyed = false; });
  sel.addEventListener("change", () => {
    if (keyed) { pending = true; return; }
    pending = false;
    load(sel.value);
  });
  sel.addEventListener("blur", () => { if (pending) { pending = false; load(sel.value); } });
}

// The agent picks among the runs meant to be worked: the committed final run and batch runs. Experiment
// runs (with their configuration names) are in «كيف يشتغل». The picker is small and unlabelled on screen
// (its name is «المصدر»); its text is where the page says, once, that this is a saved run. The queue's
// heading gives a saved run's count.
const SET_AR = dict({ test2: "الاختبار النهائي", mvp_test: "اختبار الـ MVP", dev: "مجموعة التطوير" });
function buildSourcePicker() {
  const sel = $("source");
  const work = S.runs.filter((r) => r.name.startsWith("saved/") || !r.experiment);
  const label = (r) => {
    if (r.name.startsWith("saved/")) return `تشغيل محفوظ: ${SET_AR[r.set] || r.set}`;
    return `دفعة ${(r.started || "").replace("T", " ").slice(0, 16)}${typeof r.n === "number" ? ` (${ticketsText(r.n)})` : ""}`;
  };
  const g1 = el("optgroup", { label: "تشغيلات محفوظة" });
  const g2 = el("optgroup", { label: "تشغيلات دفعة" });
  for (const r of work) (r.name.startsWith("saved/") ? g1 : g2).append(el("option", { value: r.name, text: label(r) }));
  for (const g of [g1, g2]) if (g.children.length) sel.append(g);
  const names = work.map((r) => r.name);
  const newest = [...work].sort((a, b) => (b.started || "").localeCompare(a.started || ""))[0];
  const pick = names.includes(S.prefs.source) ? S.prefs.source
    : names.includes("saved/test2/final") ? "saved/test2/final" : newest?.name;
  if (pick) sel.value = pick;
  sel.disabled = !work.length;
  loadOnPick(sel, async (v) => { await loadAgentSource(v); S.prefs.source = v; save(); });
}

/** Open a run in the inbox (from the picker, or from «كيف يشتغل» for an experiment run). */
async function loadAgentSource(name) {
  pauseClock();
  hideToast();   // its «تراجع» belongs to the run that is going away
  S.agent.source = name || null;
  S.agent.loading = true;
  S.agent.error = null;
  S.agent.items = [];
  S.agent.openKey = null;
  S.agent.urgentTab = null;
  S.agent.cameFrom = null;
  for (const k of [...S.decisions.keys()]) if (!k.startsWith("live-")) S.decisions.delete(k);
  // Ctrl+Z undoes only decisions on the run on screen (and live tickets).
  S.session = S.session.filter((e) => e.run === "live");
  inbox.renderQueue();
  inbox.renderTicket();
  inbox.renderWhy();
  if (!name) {
    S.agent.loading = false;
    renderAgent();
    return;
  }
  try {
    const [run, decided] = await Promise.all([getJSON(`/api/run?name=${encodeURIComponent(name)}`), restoreDecisions(name)]);
    if (S.agent.source !== name) return;   // the agent picked another source meanwhile
    S.agent.run = run;
    S.agent.items = run.tickets.map((row, i) => ({
      key: row.ticket.id, run: name, order: i, ticket: { id: row.ticket.id, text: row.ticket.text },
      events: row.events || [], result: row.result, seconds: row.seconds, status: "done",
    }));
    for (const it of S.agent.items) if (decided.has(it.key)) S.decisions.set(it.key, decided.get(it.key));
  } catch (e) {
    S.agent.error = e instanceof ServerError ? e.message : "انقطع الاتصال بالخادم.";
  }
  S.agent.loading = false;
  // The most urgent open ticket first (P1 escalations before P2 checks), whatever its tab.
  const first = mostUrgent();
  S.agent.tab = first ? tabOf(first) : "done";
  S.agent.openKey = first ? first.key : null;
  if (S.mode === "agent") startClock(first);
  renderAgent();
}

function renderAgent() {
  inbox.renderQueue();
  inbox.renderTicket();
  inbox.renderWhy();
}

async function setMode(mode, { quiet = false } = {}) {
  if (mode !== "agent" && mode !== "process") mode = "agent";
  if (S.mode !== mode) {
    proc.stopProcess();
    hideToast();   // its «تراجع» acts on the inbox, which is not on screen in the other mode
    // Both modes share the pane: the other mode's scroll would open this one part way down.
    $("main").scrollTop = 0;
    document.scrollingElement.scrollTop = 0;
  }
  if (mode !== "agent") pauseClock();
  S.mode = mode;
  document.body.dataset.mode = mode;
  $("modeAgent").setAttribute("aria-pressed", String(mode === "agent"));
  $("modeProcess").setAttribute("aria-pressed", String(mode === "process"));
  $("agentNav").hidden = mode !== "agent";
  $("processNav").hidden = mode !== "process";
  $("agentMain").hidden = mode !== "agent";
  $("processMain").hidden = mode !== "process";
  $("nav").setAttribute("aria-label", mode === "agent" ? "قائمة التذاكر" : "التشغيلات والتذاكر");
  $("sourceField").hidden = mode !== "agent";
  document.title = mode === "agent" ? "صندوق التذاكر" : "كيف يشتغل النظام";
  if (S.meta && mode === "process") await proc.renderProcess();
  if (S.meta && mode === "agent") {
    renderAgent();
    inbox.rowInView(findItem(S.agent.openKey));   // a live ticket that finished meanwhile is the open one
    if (!quiet) startClock(findItem(S.agent.openKey));
  }
}

async function toProcess(it) {
  await setMode("process");
  if (it.live) proc.showLive(it);
  else await proc.focusRunTicket(it.run, it.key);
  $("traceTitle")?.focus();
}

async function toAgent(id) {
  await setMode("agent");
  inbox.open(id, { user: true, focus: "heading" });
}

function trouble(err) {
  if (err instanceof NetworkError) {
    showToast("انقطع الاتصال بالخادم.");
    setBanner("net", { kind: "bad", title: "انقطع الاتصال بالخادم.", text: "تأكد إن الخادم شغّال. القرارات اللي ما انحفظت تبقى بالقائمة.",
      action: { label: "جرب مرة ثانية", run: async () => {
        try { await getJSON("/api/meta"); clearBanner("net"); showToast("رجع الاتصال."); } catch { /* still down */ }
      } } });
  } else if (err instanceof ServerError && err.status === 403) {
    showToast("مفتاح الصفحة تغيّر: حدّث الصفحة.");
    setBanner("token", { kind: "bad", title: "مفتاح الصفحة تغيّر.", text: "الخادم انعاد تشغيله على الأغلب: حدّث الصفحة.",
      action: { label: "حدّث الصفحة", run: () => location.reload() } });
  }
}

init();
