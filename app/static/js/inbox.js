// "وضع الموظف": the agent inbox. A queue by status and priority, one ticket in the centre with its facts
// and draft, and a "why" panel. Friction follows risk: a ready draft is one key, a flagged one needs a
// tick, a draft that asks for a secret can't be approved until it is fixed, an escalation has no draft.
// No gold labels, model ids, scores, costs or English here: those are in "كيف يشتغل".

import { NetworkError, ServerError } from "./api.js";
import { buildComposer, isBlocking, originalDraft } from "./composer.js";
import { factList, factsOf, textWithFacts } from "./facts.js";
import {
  ACTION_WORD, BECAUSE_AR, BLOCK_AR, CHECK_SHORT_AR, CONFIRM_AR, CONFIRM_OTHER, FIELD_AR, PRIORITY_AR, STAGE_DOING,
  STAGE_ORDER, STATUS, TABS, WHY_AR,
} from "./labels.js";
import {
  QUICK_S, S, allItems, decide, draftDone, effective, errorEvent, escalatesNow, ev, extractionOf, findItem, flagsOf,
  itemsInTab, mostUrgent, openItems, outcomeOf, pauseClock, priorityRank, refreshDecisions, routeFor, runningItems,
  startClock, subOf, summarize, tabOf, uid, undo,
} from "./state.js";
import { setBanner, showToast } from "./ui.js";
import {
  MOD, add, countAr, digitRuns, dict, el, fmtSeconds, icon, isPhone, kbd, ltr, median, mono, num, plainText, richText,
  ticketsAr,
} from "./util.js";

const hooks = { toProcess: null, newTicket: null, rerun: null, cancelLive: null, reload: null };
export function setInboxHooks(h) { Object.assign(hooks, h); }

const $ = (id) => document.getElementById(id);
let composer = null;
let deciding = false;
let takeOverArmed = false;
let fixOpenFor = null;   // uid of the ticket whose «صحّح» panel is open
let shownKey = null;     // the ticket drawn last: a different one starts at the top of the pane

// --- words ---

const teamAr = (t) => (t && S.meta.teams[t]?.label_ar) || t || "";
const subAr = (k) => (k && S.meta.subcategories[k]?.label) || k || "";
/** "حوّلها لقسم الاحتيال", "حوّلها للطابور العام". */
const toTeam = (label) => (!label ? "للقسم" : label.startsWith("ال") ? `لل${label.slice(2)}` : `ل${label}`);
// Flags this page adds itself (a live run whose stream broke) have no server wording.
const PAGE_FLAG_AR = dict({ connection_lost: "انقطع الاتصال" });
/** A flag's wording up to its first ":" or "،": «احتمال احتيال», «صار خطأ بالنموذج». */
const flagShort = (f) => String(S.meta.flag_ar[f] || PAGE_FLAG_AR[f] || f).split(/[:،]/)[0].trim();
/** A flag as one sentence with no colon in it (WHY_AR, else the server's wording joined with «، »). */
const flagSentence = (f) => WHY_AR[f] || `${String(S.meta.flag_ar[f] || PAGE_FLAG_AR[f] || f).replace(/\s*:\s*/g, "، ")}.`;
/** The shortcut letters, only while single-key shortcuts are on: « (T / ف)». */
const keys = (latin, ar) => (S.prefs.singleKeys ? ` (${latin} / ${ar})` : "");
function prioNode(p) {
  return p ? el("span", { class: `prio prio-${p.toLowerCase()}` }, ltr(p), ` · ${PRIORITY_AR[p] || ""}`)
    : el("span", { class: "prio prio-none", text: "بدون أولوية" });
}
const firstWords = (t) => plainText(t).text.replace(/\s+/g, " ").slice(0, 140);
const tabLabel = (id) => TABS.find((t) => t.id === id)?.label || "";

function liveStageWord(it) {
  const last = it.events.at(-1);
  if (!last) return STAGE_DOING.received;
  if (last.status === "running") return STAGE_DOING[last.stage] || "…";
  if (last.stage === "gate") return last.data?.decision === "recheck" ? STAGE_DOING.recheck : STAGE_DOING.route;
  const next = STAGE_ORDER[STAGE_ORDER.indexOf(last.stage) + 1];
  return STAGE_DOING[next] || STAGE_DOING[last.stage] || "…";   // after the result: «يخلص…» until the stream ends
}

/** The type the draft was written for differs from the one the agent now gives the ticket. */
function retargeted(it) {
  const e = effective(it);
  return !!draftDone(it) && (e.subcategory !== subOf(it) || (e.team || null) !== (it.result?.team || null));
}

/** What the agent should do first, in one line: the why of anything not ready. */
function whyLine(it) {
  const r = it.result || {};
  const err = errorEvent(it);
  const box = (kind, title, text) => el("p", { class: `callout callout-${kind}`, dir: "rtl" },
    icon(kind === "bad" ? "escalated" : "check"), el("span", {}, title ? el("strong", { text: title }) : null, title && text ? " " : null, text));
  if (it.status === "lost") return box("bad", "انقطع الاتصال قبل ما تخلص المعالجة.", "التذكرة عندك، اقراها وقرر أو شغّلها مرة ثانية.");
  if (it.status === "cancelled") return box("bad", "انلغت المعالجة قبل ما تكمل.", "التذكرة عندك، اقراها وقرر.");
  if (err) return box("bad", `صار خطأ: ${err.data?.error || ""}`, "التذكرة راحت لموظف بدون مسودة.");
  // The agent's correction made it a type that is never drafted: no reply, whatever the pipeline wrote.
  if (r.outcome !== "escalated" && escalatesNow(it)) {
    return box("bad", "احتمال احتيال: ماكو رد للزبون.", "صحّحت النوع لنوع ما ينكتبله رد، فالمسودة ما تنعتمد. حوّلها للقسم أو استلمها بنفسك.");
  }
  if (r.outcome === "flagged") {
    const said = (r.flags || []).filter((f) => !f.startsWith("draft:")).map(flagSentence);
    return box("warn", "تحتاج تأكيد:", said.join(" ") || "بالمسودة شي لازم تراجعه، شوف الفحص تحت المسودة.");
  }
  if (r.outcome === "escalated") {
    if ((r.flags || []).includes("fraud")) return box("bad", "احتمال احتيال: ماكو رد للزبون.", "اقرا الملاحظة وحوّلها، أو استلمها بنفسك.");
    return box("bad", "متصعّدة:", (r.flags || []).map(flagSentence).join(" ") || "يستلمها موظف بدون مسودة.");
  }
  return null;
}

/** The gate's confidence as a category with what was done about it (never a decimal here). */
function confidence(it) {
  const g = ev(it, "gate");
  if (!g || g.status !== "done") return null;
  const d = g.data || {};
  if (d.decision === "escalate") return { cls: "bad", word: "متصعّد" };
  if (d.decision === "recheck") {
    const r = ev(it, "recheck");
    const sure = d.confidence >= S.meta.thresholds.pass_above;
    const word = sure ? "نوع حساس: انراجع بنموذج ثاني" : "مو متأكد: انراجع بنموذج ثاني";
    const after = r?.status === "done" ? (r.data.agree ? "، واتفقوا" : "، واختلفوا") : "";
    return { cls: "warn", word: word + after };
  }
  return { cls: "ok", word: "واثق" };
}

// A bill type the customer already named (the drafter is always told to ask for it: F11 has no field).
const BILL_NAMED = /كهرب|ماي|الماء|مي\b|انترنت|إنترنت|النت|غاز|موبايل|تلفون|هاتف|اشتراك|كارت/;
/** What the ticket is missing, or null when nothing read it (no extraction at all). */
function missingOf(it) {
  if (!extractionOf(it)) return null;
  const text = it.ticket.text || "";
  const out = [];
  for (const f of it.result?.flags || []) if (f.startsWith("missing:")) out.push(FIELD_AR[f.slice(8)] || f.slice(8));
  for (const f of draftDone(it)?.ask_for || []) {
    if (f === "bill_type" && BILL_NAMED.test(text)) continue;
    out.push(FIELD_AR[f] || f);
  }
  const line = (it.result?.handoff_ar || "").split("\n").find((l) => l.startsWith("ناقص:"));
  if (line) out.push(...line.slice(5).split("،").map((s) => s.trim()).filter(Boolean));
  return [...new Set(out)];
}

// --- scrolling: the sticky action bar must never cover the caret or a check's answer ---

const scroller = () => (isPhone() ? document.scrollingElement : $("main"));
/** Run fn (which may grow or shrink something above `anchor`) and scroll so `anchor` stays where it was. */
function keepPlace(anchor, fn) {
  const before = anchor?.isConnected ? anchor.getBoundingClientRect().top : null;
  fn();
  if (before == null || !anchor.isConnected) return;
  const delta = anchor.getBoundingClientRect().top - before;
  if (Math.abs(delta) > 1) scroller()?.scrollBy(0, delta);
}
/** While the agent types, keep the caret's line above the action bar. */
function keepCaretInView() {
  if (!composer || document.activeElement !== composer.textarea) return;
  const caret = composer.caretRect();
  const bar = $("actionBar")?.getBoundingClientRect();
  if (!caret || !bar) return;
  const over = caret.bottom + 12 - bar.top;
  if (over > 0) scroller()?.scrollBy(0, over);
}

// --- the queue ---

export function renderQueue({ focusRow = false } = {}) {
  const box = $("agentQueue");
  if (S.agent.loading) return box.replaceChildren(queueSkeleton());
  const items = allItems();
  const decided = items.filter((i) => S.decisions.has(i.key)).length;
  const esc = items.filter((i) => outcomeOf(i) === "escalated");
  const reasons = new Map();
  for (const it of esc) for (const f of flagsOf(it)) reasons.set(flagShort(f), (reasons.get(flagShort(f)) || 0) + 1);
  const remaining = openItems().length;
  const bar = el("span", { class: "progress-fill" });
  bar.style.width = `${items.length ? (100 * decided) / items.length : 0}%`;

  const head = el("div", { class: "queue-head" },
    el("h2", { id: "queueTitle", class: "queue-title" }, "خلصت ", num(decided), " من ", num(items.length)),
    el("div", { class: "progress", "aria-hidden": "true" }, bar),
    el("ul", { class: "throughput", "aria-label": "شغل الجلسة" },
      el("li", {}, el("span", { class: "tp-k", text: "انحسمت" }), num(decided)),
      el("li", {}, el("span", { class: "tp-k", text: "باقي" }), num(remaining)),
      el("li", {}, el("span", { class: "tp-k", text: "متصعّدة" }), num(esc.length),
        reasons.size ? el("span", { class: "tp-why" }, " (", [...reasons].map(([w, n], i) => [i ? "، " : "", `${w} `, num(n)]), ")") : null)),
    urgentHint());

  const counts = { done: decided };
  for (const t of ["flagged", "escalated", "drafted"]) counts[t] = itemsInTab(t).length;
  const tabs = el("div", { role: "tablist", class: "tabs", "aria-label": "حالة التذاكر" },
    TABS.map((t, i) => el("button", {
      type: "button", role: "tab", id: `tab-${t.id}`, class: "tab", "aria-selected": String(S.agent.tab === t.id),
      "aria-controls": "queuePanel", tabindex: S.agent.tab === t.id ? "0" : "-1", dataset: { tab: t.id },
    }, el("span", { class: "tab-label", text: t.label }), el("span", { class: "tab-count" }, num(counts[t.id])), kbd(String(i + 1)))));
  tabs.addEventListener("click", (e) => { const b = e.target.closest("[role=tab]"); if (b) setTab(b.dataset.tab, { openFirst: true }); });
  tabs.addEventListener("keydown", onTabsKey);

  const list = [...runningItems(), ...itemsInTab(S.agent.tab)];
  const active = list.find((x) => x.key === S.agent.openKey) || list[0];
  const lb = el("ul", { role: "listbox", id: "queueList", class: "queue", "aria-label": `تذاكر «${tabLabel(S.agent.tab)}»` },
    list.map((it) => row(it, it === active)));
  lb.addEventListener("click", (e) => { const o = e.target.closest("[role=option]"); if (o) open(o.dataset.key, { user: true }); });
  lb.addEventListener("keydown", onListKey);

  const empty = list.length ? null : el("div", { class: "queue-empty" },
    el("p", { text: S.agent.tab === "done" ? "ما قررت على أي تذكرة بعد." : `ماكو تذاكر «${tabLabel(S.agent.tab)}» هسه.` }),
    nextTabHint());
  // A re-render (a live ticket's next stage, a decision) must not drop the agent's place in the queue.
  const had = box.contains(document.activeElement) ? document.activeElement.id : null;
  box.replaceChildren(head, tabs, el("div", { role: "tabpanel", id: "queuePanel", "aria-labelledby": `tab-${S.agent.tab}` }, lb, empty));
  if (focusRow || (had && !$(had))) (lb.querySelector('[tabindex="0"]') || $(`tab-${S.agent.tab}`))?.focus();
  else if (had) $(had).focus();
}

/** «اكو 6 عاجلة (P1) بـ«متصعّدة»»: a more urgent open ticket waits in another tab. */
function urgentHint() {
  const best = mostUrgent(S.agent.tab);
  if (!best || tabOf(best) === S.agent.tab) return null;
  const here = itemsInTab(S.agent.tab).filter((it) => !S.decisions.has(it.key))[0];
  if (here && priorityRank(here) <= priorityRank(best)) return null;
  const t = tabOf(best);
  const n = itemsInTab(t).filter((it) => priorityRank(it) === priorityRank(best)).length;
  const p = effective(best).priority;
  return el("button", { type: "button", class: "link-btn urgent-hint", onclick: () => setTab(t, { openFirst: true }) },
    icon("escalated"), "اكو ", num(n), ` ${p ? PRIORITY_AR[p] : "بدون أولوية"} بـ«${tabLabel(t)}»`);
}

function nextTabHint() {
  const other = ["flagged", "escalated", "drafted"].find((t) => t !== S.agent.tab && itemsInTab(t).length);
  return other ? el("button", { type: "button", class: "link-btn", onclick: () => setTab(other, { openFirst: true }) },
    `روح لـ«${tabLabel(other)}» (`, num(itemsInTab(other).length), ")") : null;
}

function row(it, active) {
  const d = S.decisions.get(it.key);
  const out = outcomeOf(it);
  let st;
  if (d) st = { icon: "done", word: ACTION_WORD[d.action] || "خلصت", cls: "done" };
  else if (it.status === "running") st = { icon: "running", word: liveStageWord(it), cls: "running" };
  else if (it.status === "lost" || it.status === "cancelled") st = { ...STATUS.lost, cls: "lost" };
  else st = { ...(STATUS[out] || STATUS.escalated), cls: STATUS[out] ? out : "escalated" };
  const e = effective(it);
  const open = it.key === S.agent.openKey;
  return el("li", {
    role: "option", id: `opt-${it.key}`, class: `row st-${st.cls}`, "aria-selected": String(open),
    "aria-current": open ? "true" : null, tabindex: active ? "0" : "-1", dataset: { key: it.key },
  },
  el("span", { class: "row-status" }, icon(st.icon), el("span", { class: "row-word", text: st.word })),
  el("span", { class: "row-body" },
    el("span", { class: "row-meta" }, mono(it.key), e.priority || it.status !== "running" ? prioNode(e.priority) : null,
      e.team ? el("span", { class: "row-team", text: teamAr(e.team) }) : null),
    el("span", { class: "row-text", dir: "rtl" }, digitRuns(firstWords(it.ticket.text)))));
}

function onListKey(e) {
  // Ctrl/Cmd+Enter is "approve and next" (keyboard.js), even with focus on a row after J / K.
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  const opts = [...e.currentTarget.querySelectorAll("[role=option]")];
  const i = opts.indexOf(document.activeElement);
  let j = null;
  if (e.key === "ArrowDown") j = Math.min(opts.length - 1, i + 1);
  else if (e.key === "ArrowUp") j = Math.max(0, i - 1);
  else if (e.key === "Home") j = 0;
  else if (e.key === "End") j = opts.length - 1;
  else if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    if (opts[i]) open(opts[i].dataset.key, { user: true, focus: "heading" });
    return;
  }
  if (j === null || !opts[j]) return;
  e.preventDefault();
  e.stopPropagation();
  open(opts[j].dataset.key, { focusRow: true });
}

function onTabsKey(e) {
  const ids = TABS.map((t) => t.id);
  const i = ids.indexOf(S.agent.tab);
  // Right to left: the next tab is to the left.
  const j = e.key === "ArrowLeft" ? (i + 1) % ids.length : e.key === "ArrowRight" ? (i + ids.length - 1) % ids.length
    : e.key === "Home" ? 0 : e.key === "End" ? ids.length - 1 : null;
  if (j === null) return;
  e.preventDefault();
  setTab(ids[j], { openFirst: true, focusTab: true });
}

export function setTab(id, { openFirst = false, focusTab = false } = {}) {
  S.agent.tab = id;
  const list = itemsInTab(id);
  if (openFirst && !list.some((x) => x.key === S.agent.openKey)) {
    S.agent.openKey = list[0]?.key ?? null;
    startClock(findItem(S.agent.openKey));
    renderTicket();
    renderWhy();
  }
  renderQueue();
  if (focusTab) $(`tab-${id}`)?.focus();
}

/** Open a ticket. user: the agent picked it (on a phone, the ticket screen opens). */
export function open(key, { user = false, focus = null, focusRow = false } = {}) {
  const it = findItem(key);
  if (!it) return;
  if (S.agent.openKey !== key || !S.timing) startClock(it);
  S.agent.openKey = key;
  const t = tabOf(it);
  if (t !== "running" && t !== S.agent.tab) S.agent.tab = t;
  renderQueue({ focusRow });
  renderTicket();
  renderWhy();
  // On a phone the queue gives way to the ticket: focus (and scroll) moves to its heading.
  if (user && isPhone()) { document.body.dataset.screen = "ticket"; focus = "heading"; }
  if (focus === "heading") $("ticketTitle")?.focus();
}

function backToQueue() {
  document.body.dataset.screen = "queue";
  renderQueue({ focusRow: true });
}

/** J / K: the next or previous ticket in the list as shown. */
export function move(delta) {
  const list = [...runningItems(), ...itemsInTab(S.agent.tab)];
  if (!list.length) return;
  const i = list.findIndex((x) => x.key === S.agent.openKey);
  const n = list[i < 0 ? 0 : Math.max(0, Math.min(list.length - 1, i + delta))];
  const queueShown = !isPhone() || document.body.dataset.screen !== "ticket";
  if (n) open(n.key, { focusRow: queueShown, focus: queueShown ? null : "heading" });
}

// --- the ticket ---

export function renderTicket() {
  composer?.dispose();
  composer = null;
  takeOverArmed = false;
  const main = $("agentMain");
  // A different ticket (or none) opens at its top; the same one, drawn again, keeps its place.
  const key = S.agent.loading || S.agent.error ? null : (findItem(S.agent.openKey)?.key ?? null);
  if (key !== shownKey && !isPhone()) $("main").scrollTop = 0;
  shownKey = key;
  if (S.agent.loading) return main.replaceChildren(ticketSkeleton());
  if (S.agent.error) return main.replaceChildren(errorState(S.agent.error));
  const items = allItems();
  if (!items.length) return main.replaceChildren(emptyQueue());
  const it = findItem(S.agent.openKey);
  if (!it) {
    const back = el("button", { type: "button", class: "btn btn-quiet back-btn", onclick: backToQueue }, icon("back"), "القائمة");
    if (!openItems().length && !runningItems().length) return main.replaceChildren(back, allDone());
    return main.replaceChildren(back, el("div", { class: "empty-state" },
      el("h2", { class: "empty-title", text: "ماكو تذكرة مفتوحة" }),
      el("p", { text: "اختار تذكرة من القائمة." }), nextTabHint()));
  }
  main.replaceChildren(ticketView(it));
}

function titleChips(it) {
  const e = effective(it);
  return el("div", { id: "titleChips", class: "title-chips" }, it.status === "running" ? null : prioNode(e.priority),
    e.team ? el("span", { class: "chip", text: teamAr(e.team) }) : null,
    el("button", { type: "button", class: "btn btn-quiet btn-small why-toggle", "aria-controls": "why",
      "aria-expanded": String(document.body.classList.contains("why-open")), onclick: () => toggleWhy() },
    icon("panel"), "ليش؟", kbd("W", "ص")),
    el("span", { class: "step-btns", role: "group", "aria-label": "التنقل بين التذاكر" },
      // The visible text is the key hint, so the name carries it too (WCAG 2.5.3).
      el("button", { type: "button", class: "btn btn-quiet btn-small", "aria-label": "التذكرة اللي قبلها (K / ن)", title: "التذكرة اللي قبلها (K / ن)", onclick: () => move(-1) }, icon("up"), kbd("K", "ن")),
      el("button", { type: "button", class: "btn btn-quiet btn-small", "aria-label": "التذكرة الجاية (J / ت)", title: "التذكرة الجاية (J / ت)", onclick: () => move(1) }, icon("down"), kbd("J", "ت"))));
}

function ticketView(it) {
  const decided = S.decisions.get(it.key);
  const out = outcomeOf(it);
  const running = it.status === "running";
  const art = el("article", { class: `ticket o-${running ? "running" : escalatesNow(it) ? "escalated" : out}`, "aria-labelledby": "ticketTitle" });
  const back = el("button", { type: "button", class: "btn btn-quiet back-btn", onclick: backToQueue }, icon("back"), "القائمة");
  add(art, el("div", { class: "ticket-bar" }, back,
    el("h2", { id: "ticketTitle", class: "ticket-title", tabindex: "-1" }, "تذكرة ", mono(it.key)),
    titleChips(it)));

  if (running) {
    add(art, el("p", { class: "callout callout-info" }, icon("running", "spin"), el("span", { text: "التذكرة تنعالج هسه. تكدر تشتغل على غيرها وترجعلها." })),
      liveSteps(it), customerSection(it), el("div", { class: "skeleton-block", "aria-hidden": "true" }), actionBar(it));
    return art;
  }
  const line = whyLine(it);
  if (line) add(art, line);
  add(art, summaryBox(it));
  if (decided) {
    add(art, customerSection(it), decidedSection(it, decided), actionBar(it));
    return art;
  }
  if (escalatesNow(it)) {
    add(art, handoffSection(it), customerSection(it), reasonsBox(it), actionBar(it));
    return art;
  }
  add(art, customerSection(it), choiceBox(it), el("div", { id: "confirmBox", tabindex: "-1" }));
  composer = buildComposer(it, () => refreshGate(it));
  add(art, composer.node, reasonsBox(it), actionBar(it));
  queueMicrotask(() => refreshGate(it, { first: true }));
  return art;
}

function liveSteps(it) {
  const names = { received: "الاستلام", clean: "التنظيف", classify: "التصنيف", gate: "بوابة الثقة", recheck: "المراجعة الثانية", route: "التوجيه", draft: "المسودة" };
  const state = (s) => {
    const list = it.events.filter((x) => x.stage === s);
    const last = list.at(-1);
    return last ? last.status : "pending";
  };
  const word = dict({ done: "خلصت", running: "هسه", skipped: "ما احتاجت", error: "خطأ", pending: "" });
  return el("ol", { id: "liveSteps", class: "live-steps", "aria-label": "مراحل المعالجة" },
    Object.entries(names).map(([s, n]) => {
      const st = state(s);
      return el("li", { class: `ls ls-${st}` }, icon(st === "done" ? "ready" : st === "running" ? "running" : st === "error" ? "escalated" : "next", st === "running" ? "spin" : ""),
        el("span", { text: n }), word[st] ? el("span", { class: "ls-word", text: word[st] }) : null);
    }));
}

function summaryBox(it) {
  const e = effective(it);
  const c = S.corrections.get(uid(it)) || {};
  const conf = confidence(it);
  const miss = missingOf(it);
  const fixed = (k) => (c[k] && c[k] !== (k === "subcategory" ? subOf(it) : it.result?.[k]) ? el("span", { class: "fixed-tag", text: "صحّحتها" }) : null);
  const open = fixOpenFor === uid(it);
  const toggle = el("button", { type: "button", id: "fixToggle", class: "link-btn", "aria-expanded": String(open), "aria-controls": "fixPanel",
    onclick: () => {
      fixOpenFor = open ? null : uid(it);
      refreshSummary(it);
      (open ? $("fixToggle") : $("fixSub"))?.focus();   // closing: focus stays on the (new) toggle
    } },
  icon("edit"), "صحّح");
  return el("div", { id: "sumBox", class: "summary" },
    el("dl", { class: "summary-line" },
      el("div", {}, el("dt", { text: "النوع" }), el("dd", {}, e.subcategory ? subAr(e.subcategory) : "ما انعرف", fixed("subcategory"))),
      el("div", {}, el("dt", { text: "القسم" }), el("dd", {}, e.team ? teamAr(e.team) : "ما انحدد", fixed("team"))),
      el("div", {}, el("dt", { text: "الأولوية" }), el("dd", {}, prioNode(e.priority), fixed("priority"))),
      el("div", {}, el("dt", { text: "ناقص" }), el("dd", { text: miss == null ? "ما نعرف، النظام ما قرا التذكرة" : miss.length ? miss.join("، ") : "ما ناقص شي" })),
      conf ? el("div", {}, el("dt", { text: "الثقة" }), el("dd", { class: `conf conf-${conf.cls}` }, el("span", { class: "conf-dot", "aria-hidden": "true" }), conf.word)) : null),
    // After a decision the corrections are part of it (shown under it); they can't change any more.
    S.decisions.has(it.key) ? null : toggle, open && !S.decisions.has(it.key) ? fixPanel(it) : null);
}

function refreshSummary(it) {
  $("sumBox")?.replaceWith(summaryBox(it));
}

/** Open «صحّح» with the team select focused (forwarding a ticket the system gave no team). */
function askForTeam(it) {
  fixOpenFor = uid(it);
  refreshSummary(it);
  $("fixTeam")?.focus();
  showToast("اختار القسم أول، وبعدين حوّلها.");
}

function fixPanel(it) {
  const e = effective(it);
  const set = (patch) => {
    S.corrections.set(uid(it), { ...effective(it), ...patch });
    refreshAfterCorrection(it);
  };
  const subSel = el("select", { id: "fixSub" }, el("option", { value: "", text: "—" }));
  const groups = new Map();
  for (const [k, s] of Object.entries(S.meta.subcategories)) {
    if (!groups.has(s.category_label)) groups.set(s.category_label, el("optgroup", { label: s.category_label }));
    groups.get(s.category_label).append(el("option", { value: k, text: s.label }));
  }
  subSel.append(...groups.values());
  subSel.value = e.subcategory || "";
  subSel.addEventListener("change", () => {
    const r = routeFor(subSel.value, extractionOf(it));
    set({ subcategory: subSel.value || null, ...(r.team ? r : {}) });
    $("fixSub")?.focus();
  });
  const teamSel = el("select", { id: "fixTeam" }, el("option", { value: "", text: "—" }),
    Object.entries(S.meta.teams).map(([k, t]) => el("option", { value: k, text: t.label_ar })));
  teamSel.value = e.team || "";
  teamSel.addEventListener("change", () => { set({ team: teamSel.value || null }); $("fixTeam")?.focus(); });
  const prSel = el("select", { id: "fixPrio" }, el("option", { value: "", text: "—" }),
    ["P1", "P2", "P3"].map((p) => el("option", { value: p, text: `${p} · ${PRIORITY_AR[p]}` })));
  prSel.value = e.priority || "";
  prSel.addEventListener("change", () => { set({ priority: prSel.value || null }); $("fixPrio")?.focus(); });
  return el("div", { id: "fixPanel", class: "fix-panel" },
    el("p", { class: "hint", text: "التصحيح ينحفظ ويا قرارك، حتى نعرف وين يغلط النظام. تغيير النوع يغيّر القسم والأولوية حسب القواعد." }),
    el("div", { class: "fix-fields" },
      el("label", {}, el("span", { text: "النوع" }), subSel),
      el("label", {}, el("span", { text: "القسم" }), teamSel),
      el("label", {}, el("span", { text: "الأولوية" }), prSel)),
    el("button", { type: "button", class: "link-btn", text: "رجّع اللي قاله النظام",
      onclick: () => { S.corrections.delete(uid(it)); refreshAfterCorrection(it); $("fixSub")?.focus(); } }));
}

/** After a correction: the summary, the chips and the gate follow it. A correction to a type that is
 *  never drafted (or back) changes what the ticket is, so the whole view is drawn again. */
function refreshAfterCorrection(it) {
  const wasEscalated = $("agentMain").querySelector(".ticket")?.classList.contains("o-escalated");
  if (wasEscalated !== escalatesNow(it)) {
    const focused = document.activeElement?.id;
    renderTicket();
    renderQueue();
    renderWhy();
    if (focused) $(focused)?.focus();
    return;
  }
  refreshSummary(it);
  $("titleChips")?.replaceWith(titleChips(it));
  $("choiceBox")?.replaceWith(choiceBox(it));
  refreshGate(it);
  renderQueue();
  renderWhy();
}

function customerSection(it) {
  // Direction controls are dropped: the agent reads the order the model and the rules read.
  const raw = plainText(it.ticket.text || ev(it, "received")?.data?.text || "");
  const text = raw.text;
  const ex = extractionOf(it);
  const facts = factsOf(ex, text, subOf(it));
  const body = el("p", { class: "customer-text", dir: "rtl", lang: "ar" }, textWithFacts(text, facts));
  const sec = el("section", { class: "customer", "aria-labelledby": "custTitle" }, el("h3", { id: "custTitle", class: "section-title", text: "رسالة الزبون" }));
  if (facts.length) sec.append(factList(facts, body));
  else if (!ex && it.status !== "running") sec.append(el("p", { class: "hint", text: "النظام ما قرا التذكرة، فاقراها كاملة." }));
  if (raw.hidden) {
    sec.append(el("p", { class: "hint hint-warn" }, icon("check"),
      `بالنص ${raw.hidden === 1 ? "رمز اتجاه مخفي واحد" : raw.hidden === 2 ? "رمزين اتجاه مخفيين" : `${raw.hidden} رموز اتجاه مخفية`} يغيّر ترتيب الكتابة. شلناها، فالنص هنا بالترتيب اللي قراه النظام.`));
  }
  sec.append(body);
  return sec;
}

/** Two models disagreed on the type: both answers, the re-check's chosen, each with where it would go. */
function choiceBox(it) {
  const alt = it.result?.recheck_alternative;
  if (!alt || !(it.result.flags || []).includes("recheck_used_second")) return el("div", { id: "choiceBox" });
  const second = subOf(it);
  const r1 = routeFor(alt, extractionOf(it));
  const pickedFirst = effective(it).subcategory === alt;
  const opt = (value, sub, team, prio, who, checked) => el("label", { class: "choice-opt" },
    el("input", { type: "radio", name: "pick", value, checked }),
    el("span", { class: "choice-body" },
      el("span", { class: "choice-sub", text: subAr(sub) }),
      el("span", { class: "choice-meta" }, teamAr(team), " · ", prioNode(prio)),
      el("span", { class: "choice-who", text: who })));
  const fs = el("fieldset", { id: "choiceBox", class: "choice" },
    el("legend", { text: "النموذجين اختلفوا بنوع المشكلة. ياهو الصح؟" }),
    opt("second", second, it.result.team, it.result.priority, "المراجعة الثانية (المسودة مكتوبة على جوابها)", !pickedFirst),
    opt("first", alt, r1.team, r1.priority, "النموذج الأول", pickedFirst));
  fs.addEventListener("change", (e) => {
    const v = e.target.value;
    const u = uid(it);
    if (v === "first") S.corrections.set(u, { ...(S.corrections.get(u) || {}), subcategory: alt, team: r1.team, priority: r1.priority });
    else S.corrections.set(u, { ...(S.corrections.get(u) || {}), subcategory: second, team: it.result.team, priority: it.result.priority });
    refreshAfterCorrection(it);
    $("choiceBox")?.querySelector(`input[value="${v}"]`)?.focus();
  });
  return fs;
}

/** What the agent must check before approving: the flag's one thing, any warning in the draft, and a
 *  draft written for another type than the one the agent chose. {list: [{id, ask, done}], key} */
function confirmTargets(it, st) {
  const list = [];
  const push = (id, words) => { if (!list.some((x) => x.ask === words.ask)) list.push({ id, ...words }); };
  for (const f of it.result?.flags || []) if (!f.startsWith("draft:")) push(f, CONFIRM_AR[f] || CONFIRM_OTHER);
  for (const f of st.findings) if (!isBlocking(f.kind)) push(`draft:${f.kind}`, CONFIRM_AR[`draft:${f.kind}`] || { ask: S.meta.check_ar?.[f.kind] ?? f.kind, done: "قريت التنبيه" });
  if (retargeted(it)) push("draft_for_other_type", CONFIRM_AR.draft_for_other_type);
  return { list, key: list.map((x) => x.id).join("|") };
}

/** The warning kinds the agent ticked and approves anyway (the decision log keeps them, never text). */
function acknowledged(t) {
  return t.list.map((x) => x.id).filter((id) => id.startsWith("draft:") || id === "draft_for_other_type")
    .map((id) => id.replace(/^draft:/, ""));
}

function approval(it) {
  if (!composer) return { ok: false, reason: "" };
  const st = composer.state();
  const t = confirmTargets(it, st);
  const blocking = st.findings.filter((f) => isBlocking(f.kind));
  const acked = t.list.length === 0 || S.acks.get(uid(it)) === t.key;
  if (!st.text.trim()) return { ok: false, reason: "المسودة فاضية: اكتب الرد أو استلمها بنفسك.", targets: t };
  if (blocking.length) {
    return { ok: false, blocked: true, targets: t,
      reason: [...new Set(blocking.map((f) => BLOCK_AR[f.kind] || S.meta.check_ar?.[f.kind] || f.kind))].join(" ") };
  }
  if (st.check === "error") return { ok: false, reason: "التعديل ما انفحص، جرب الفحص مرة ثانية.", targets: t };
  if (!acked) {
    const tick = t.list.length > 1 ? "راجعت كل النقاط فوق" : t.list[0].done;
    return { ok: false, needsAck: true, reason: `أشّر على «${tick}» فوق المسودة أول.`, targets: t };
  }
  return { ok: true, targets: t, pending: !st.current };
}

function refreshGate(it, { first = false } = {}) {
  if (!composer || S.agent.openKey !== it.key) return;
  const st = composer.state();
  const t = confirmTargets(it, st);
  const u = uid(it);
  if (S.acks.has(u) && S.acks.get(u) !== t.key) S.acks.delete(u);   // the thing to confirm changed: tick again
  const box = $("confirmBox");
  if (box) {
    const hadFocus = box.contains(document.activeElement) ? document.activeElement.id || "confirmBox" : null;
    const many = t.list.length > 1;
    const next = t.list.length ? el("div", { id: "confirmBox", class: "confirm", tabindex: "-1", role: "group", "aria-labelledby": "confirmTitle" },
      el("p", { id: "confirmTitle", class: "confirm-title" }, icon("check"),
        many ? el("strong", { text: "قبل لا تعتمد:" }) : el("strong", { text: t.list[0].ask })),
      many ? el("ul", { class: "confirm-list" }, t.list.map((x) => el("li", { text: x.ask }))) : null,
      el("label", { class: "confirm-check" },
        el("input", { type: "checkbox", id: "ackBox", checked: S.acks.get(u) === t.key,
          onchange: (e) => { if (e.target.checked) S.acks.set(u, t.key); else S.acks.delete(u); refreshActions(it); } }),
        el("span", { text: many ? "راجعت كل النقاط فوق" : t.list[0].done }))) : el("div", { id: "confirmBox", tabindex: "-1" });
    // The box sits above the draft: keep the draft (and the caret in it) where it was on screen.
    // Not when the ticket is first drawn: that would scroll its heading away on every open.
    if (first) box.replaceWith(next);
    else keepPlace(composer.node, () => box.replaceWith(next));
    if (hadFocus) $(hadFocus)?.focus();
  }
  refreshActions(it);
  keepCaretInView();
  // Keep the reasons open once the draft is edited.
  if (st.edited) { const d = $("reasonBox"); if (d && !d.open) d.open = true; }
}

function refreshActions(it) {
  const old = $("actionBar");
  if (!old) return;
  const hadFocus = old.contains(document.activeElement) ? document.activeElement.id : null;
  old.replaceWith(actionBar(it));
  if (hadFocus) $(hadFocus)?.focus();
}

function handoffSection(it) {
  const note = it.result?.handoff_ar || "";
  const lines = note.split("\n").map((l) => l.trim()).filter(Boolean);
  const dl = el("dl", { class: "handoff-list" }, lines.map((l) => {
    const i = l.indexOf(":");
    return i > 0 && i < 20 ? el("div", {}, el("dt", { text: l.slice(0, i) }), el("dd", { dir: "rtl" }, richText(l.slice(i + 1).trim())))
      : el("div", {}, el("dd", { dir: "rtl" }, richText(l)));
  }));
  const team = effective(it).team;
  return el("section", { class: "handoff", "aria-labelledby": "handoffTitle" },
    el("h3", { id: "handoffTitle", class: "section-title" }, "ملاحظة للقسم", team ? ` (${teamAr(team)})` : ""),
    lines.length ? dl : el("p", { class: "hint", text: "ماكو ملاحظة، اقرا التذكرة كاملة." }),
    lines.length ? el("p", { class: "hint", text: "الملاحظة مكتوبة بالقواعد من اللي طلع بالتذكرة. ما بيها رد للزبون." }) : null);
}

function reasonsBox(it) {
  const u = uid(it);
  const chosen = S.reasons.get(u) || new Set();
  const edited = S.edits.has(u);
  const d = el("details", { id: "reasonBox", class: "reasons", open: edited || takeOverArmed || chosen.size > 0 },
    el("summary", {}, "سبب التعديل أو الاستلام ", el("span", { class: "muted", text: "(اختياري)" }),
      chosen.size ? el("span", { class: "reason-count" }, " · ", num(chosen.size)) : null),
    el("div", { class: "reason-chips", role: "group", "aria-label": "الأسباب" },
      S.meta.reason_codes.map((c) => el("button", { type: "button", class: "reason-chip", "aria-pressed": String(chosen.has(c)),
        onclick: (e) => {
          const set = S.reasons.get(u) || new Set();
          if (set.has(c)) set.delete(c); else set.add(c);
          S.reasons.set(u, set);
          e.currentTarget.setAttribute("aria-pressed", String(set.has(c)));
        } }, S.meta.reason_codes_ar[c] || c))));
  return d;
}

const charsAr = (n) => countAr(n, { one: "حرف واحد تغيّر", two: "حرفين تغيّروا", few: "حروف تغيّرت", many: "حرف تغيّر" });

function decidedSection(it, d) {
  const final = S.finalText.get(uid(it));
  const orig = originalDraft(it).text;
  const reasons = (d.reason_codes || []).map((c) => S.meta.reason_codes_ar[c] || c);
  const corr = d.corrected || {};
  const corrText = [corr.subcategory && `النوع: ${subAr(corr.subcategory)}`, corr.team && `القسم: ${teamAr(corr.team)}`,
    corr.priority && `الأولوية: ${corr.priority}`].filter(Boolean);
  let body = null;
  if (final != null && d.action !== "took_over") body = [el("p", { class: "decided-k", text: "الرد اللي اعتمدته:" }), el("blockquote", { class: "decided-text", dir: "rtl" }, digitRuns(final))];
  else if (d.action === "approved" && orig) body = [el("p", { class: "decided-k", text: "المسودة انعتمدت كما هي:" }), el("blockquote", { class: "decided-text", dir: "rtl" }, digitRuns(orig))];
  else if (d.action === "edited") body = el("p", { class: "hint" }, "انعدّلت قبل الاعتماد", d.edit_chars != null ? [" (", charsAr(d.edit_chars), ")"] : "", ". السجل يحفظ بصمة الرد بس، مو نصه.");
  return el("section", { class: "decided", "aria-labelledby": "decidedTitle" },
    el("h3", { id: "decidedTitle", class: "decided-title" }, icon("done"), ACTION_WORD[d.action] || "خلصت", " · ", fmtSeconds(d.seconds)),
    body,
    reasons.length ? el("p", { class: "hint" }, "الأسباب: ", reasons.join("، ")) : null,
    corrText.length ? el("p", { class: "hint" }, "صحّحت: ", corrText.join("، ")) : null);
}

function actionBar(it) {
  const bar = el("div", { id: "actionBar", class: "actionbar", role: "group", "aria-label": "القرار" });
  const badge = el("p", { class: "no-send" }, icon("lock"), "ما ينرسل شي للزبون تلقائياً");
  const d = S.decisions.get(it.key);
  const take = (primary = false) => el("button", { type: "button", id: "takeBtn", class: primary ? "btn btn-primary" : "btn", onclick: () => takeOver() },
    icon("user"), takeOverArmed ? "سجّل: استلمتها" : "استلمها بنفسي", kbd("T", "ف"));
  if (d) {
    add(bar, el("button", { type: "button", id: "undoBtn", class: "btn", onclick: () => undoKey(it.key) }, icon("undo"), "تراجع"), badge);
    return bar;
  }
  if (it.status === "running") {
    add(bar, el("button", { type: "button", id: "cancelLive", class: "btn", onclick: () => hooks.cancelLive?.(it) }, icon("close"), "وقّف المعالجة"), badge);
    return bar;
  }
  if (it.status === "lost" || it.status === "cancelled") {
    add(bar, el("button", { type: "button", id: "rerunBtn", class: "btn btn-primary", onclick: () => hooks.rerun?.(it) }, "شغّلها مرة ثانية"), take(), badge);
    return bar;
  }
  if (escalatesNow(it)) {
    const team = effective(it).team;
    // No team (the system never read it): taking it is the main action; forwarding asks for a team first.
    const fwd = el("button", { type: "button", id: "forwardBtn", class: team ? "btn btn-primary" : "btn", onclick: () => forward() },
      icon("send"), team ? `حوّلها ${toTeam(teamAr(team))}` : "حوّلها لقسم…", kbd("F", "ب"));
    add(bar, team ? [fwd, take()] : [take(true), fwd], badge);
    return bar;
  }
  const a = approval(it);
  const label = a.needsAck ? "تأكدت، اعتمد" : "اعتمد وانتقل";
  add(bar,
    el("button", { type: "button", id: "approveBtn", class: "btn btn-primary", "aria-disabled": a.ok ? null : "true",
      "aria-describedby": a.ok ? null : "approveWhy", onclick: () => approve() }, icon("ready"), label, kbd(`${MOD}+Enter`)),
    take(), badge,
    a.ok ? null : el("p", { id: "approveWhy", class: `approve-why ${a.blocked ? "is-bad" : ""}` }, icon(a.blocked ? "lock" : "check"), a.reason));
  return bar;
}

// --- decisions ---

function current() {
  const it = findItem(S.agent.openKey);
  return it && !S.decisions.has(it.key) && it.status !== "running" ? it : null;
}

async function failed(e, it) {
  if (e instanceof ServerError && e.status === 409) {
    showToast(`ما انحفظ القرار: ${e.message}`);
    // Another tab decided this ticket meanwhile: show what the log holds now.
    try { await refreshDecisions(); } catch { /* the toast already says it */ }
    if (it && S.decisions.has(it.key)) { renderQueue(); renderTicket(); renderWhy(); }
    return;
  }
  showToast(e instanceof ServerError ? `ما انحفظ القرار: ${e.message}` : e instanceof NetworkError
    ? "ما انحفظ القرار: انقطع الاتصال بالخادم." : "ما انحفظ القرار.");
}

/** Where the agent's attention should go when approve is refused: the choice, else the thing to check. */
function focusWhatToCheck() {
  const radio = $("choiceBox")?.querySelector("input:checked");
  if (radio) return radio.focus();
  $("confirmBox")?.focus();
}

export async function approve() {
  const it = findItem(S.agent.openKey);
  if (!it || deciding) return;
  if (S.decisions.has(it.key)) return showToast(`هاي انحسمت. تكدر تتراجع (${MOD}+Z).`);
  if (it.status === "running") return;
  if (escalatesNow(it)) {
    return showToast(effective(it).team ? `هاي متصعّدة: حوّلها${keys("F", "ب")} أو استلمها${keys("T", "ف")}.`
      : `هاي متصعّدة: استلمها${keys("T", "ف")}، أو اختار القسم وحوّلها.`);
  }
  if (!composer) return;
  const at = itemsInTab(S.agent.tab).findIndex((x) => x.key === it.key);
  deciding = true;
  composer.lock(true);   // nothing typed while the check and the save run can slip past them
  try {
    await composer.checkNow();
    refreshGate(it);
    const a = approval(it);
    const st = composer.state();
    if (!a.ok || !st.current) {
      showToast(a.ok ? "التعديل ما انفحص بعد، جرب مرة ثانية." : a.reason);
      if (a.needsAck) focusWhatToCheck();
      return;
    }
    const record = await decide(it, st.edited ? "edited" : "approved",
      { draft_text: st.original.text, final_text: st.text, acknowledged: acknowledged(a.targets) });
    after(it, record, at);
  } catch (e) {
    await failed(e, it);
  } finally {
    deciding = false;
    composer?.lock(false);
  }
}

export async function takeOver() {
  const it = current();
  if (!it || deciding) return;
  if (!takeOverArmed) {   // first press: offer the reasons (optional), second press records
    takeOverArmed = true;
    const box = $("reasonBox");
    if (box) box.open = true;
    refreshActions(it);
    box?.querySelector(".reason-chip")?.focus();
    showToast(`السبب اختياري. بعدين اضغط «سجّل: استلمتها»${S.prefs.singleKeys ? " أو T / ف مرة ثانية" : ""}.`);
    return;
  }
  const at = itemsInTab(S.agent.tab).findIndex((x) => x.key === it.key);
  deciding = true;
  try {
    const st = composer?.state();
    const record = await decide(it, "took_over", { draft_text: st ? st.original.text : null, final_text: null });
    after(it, record, at);
  } catch (e) {
    await failed(e, it);
  } finally {
    deciding = false;
  }
}

export async function forward() {
  const it = current();
  if (!it || deciding || !escalatesNow(it)) return;
  if (!effective(it).team) return askForTeam(it);
  const at = itemsInTab(S.agent.tab).findIndex((x) => x.key === it.key);
  deciding = true;
  try {
    const record = await decide(it, "forwarded");
    after(it, record, at);
  } catch (e) {
    await failed(e, it);
  } finally {
    deciding = false;
  }
}

/** After a decision: the next ticket in this tab, unless a more urgent one waits in another tab. */
function after(it, record, at) {
  const tab = S.agent.tab;
  // The edit, reasons and corrections stay (undo brings them back); the tick does not.
  S.acks.delete(uid(it));
  takeOverArmed = false;
  const list = itemsInTab(tab);
  const cand = at >= 0 ? list[Math.min(at, list.length - 1)] || null : list[0] || null;
  const best = mostUrgent(tab);
  const next = cand && (!best || priorityRank(cand) <= priorityRank(best)) ? cand : best;
  S.agent.tab = next ? tabOf(next) : "done";   // all decided: the list beside the summary
  const remaining = openItems().length;
  const entry = { id: record.id, key: it.key, run: it.run };
  const msg = record.action === "forwarded"
    ? ["تحوّلت ", mono(it.key), ` ${toTeam(teamAr(effective(it).team))}`, " · الباقي ", num(remaining)]
    : [`${ACTION_WORD[record.action]} `, mono(it.key), " · الباقي ", num(remaining)];
  showToast(msg, () => undoKey(it.key, entry));
  S.agent.openKey = next ? next.key : null;
  startClock(next);
  renderQueue();
  renderTicket();
  renderWhy();
  (next ? $("ticketTitle") : $("doneTitle"))?.focus();
}

export async function undoKey(key, entry = null) {
  let it;
  try {
    it = await undo(key, entry);
  } catch (e) {
    showToast(e instanceof ServerError ? `ما صار التراجع: ${e.message}` : "ما صار التراجع: انقطع الاتصال بالخادم.");
    if (e instanceof ServerError && e.status === 409) {
      try { await refreshDecisions(); renderQueue(); renderTicket(); renderWhy(); } catch { /* the toast says it */ }
    }
    return;
  }
  if (!it) {
    showToast("ماكو قرار بهالجلسة تتراجع عنه على هالتشغيل.");
    return;
  }
  S.agent.tab = tabOf(it);
  open(key, { focus: "heading" });
  showToast(["رجعت ", mono(key), " للقائمة"]);
}

/** Ctrl/Cmd+Z: take back the last decision made in this page (on the run on screen, or a live ticket). */
export function undoLast() {
  const last = S.session.at(-1);
  if (!last) return showToast("ماكو قرار بهالجلسة تتراجع عنه.");
  undoKey(last.key, last);
}

export function focusDraft() {
  const ta = $("draft");
  if (ta) { ta.focus(); return true; }
  return false;
}
export function leaveDraft() {
  $("ticketTitle")?.focus();
}

/** Between 721 and 1000 px the why panel is a drawer over the ticket, not a column under it. */
export const whyIsDrawer = () => matchMedia("(min-width: 721px) and (max-width: 1000px)").matches;

export function toggleWhy(force) {
  const on = force ?? !document.body.classList.contains("why-open");
  const inside = $("why")?.contains(document.activeElement);
  document.body.classList.toggle("why-open", on);
  S.prefs.whyOpen = on;
  hooks.savePrefs?.();
  document.querySelectorAll(".why-toggle").forEach((b) => b.setAttribute("aria-expanded", String(on)));
  if (on && isPhone()) $("why")?.scrollIntoView({ block: "start" });
  if (on && whyIsDrawer()) $("whyTitle")?.focus();
  // Closing it from inside (its own button, Escape): focus goes back to its toggle, never to <body>.
  if (!on && inside) (document.querySelector("#agentMain .why-toggle") || $("ticketTitle"))?.focus();
}

// --- the why panel ---

const because = (it) => {
  for (const f of flagsOf(it)) if (BECAUSE_AR[f]) return BECAUSE_AR[f];
  const f = flagsOf(it)[0];
  return f ? flagShort(f) : "المعالجة انقطعت";
};

export function renderWhy() {
  const body = $("whyBody");
  const it = findItem(S.agent.openKey);
  if (!it) return body.replaceChildren(el("p", { class: "hint", text: "افتح تذكرة حتى تشوف كيف انحسمت." }));
  if (it.status === "running") return body.replaceChildren(el("p", { class: "hint", text: "التذكرة تنعالج هسه. الشرح يطلع لما تخلص." }));
  const steps = [];
  const step = (title, ...text) => steps.push(el("li", {}, el("strong", { text: title }), el("span", {}, ...text)));
  const clean = ev(it, "clean");
  const changes = Object.values(clean?.data?.changes || {}).reduce((a, n) => a + n, 0);
  step("الاستلام", changes ? "توحّدت الأرقام والمسافات بالنص." : "النص وصل مثل ما هو.");
  const cl = ev(it, "classify");
  if (!cl || cl.status === "skipped") {
    step("التصنيف", `ما انرسلت لنموذج لأن ${because(it)}.`);
  } else if (cl.status === "error") {
    step("التصنيف", "صار خطأ، فراحت لموظف.");
  } else {
    step("التصنيف", "النموذج الأول قال: ", el("b", { text: subAr(cl.data.extraction?.subcategory) }), ".");
    const g = ev(it, "gate");
    if (g?.status === "done") {
      const gf = (g.data.flags || []).map(flagShort);
      const sure = g.data.confidence >= S.meta.thresholds.pass_above;
      const why = g.data.decision === "escalate" ? "تصعّدت لموظف"
        : g.data.decision === "recheck" ? `${sure ? "النوع حساس" : "مو متأكد"}، فراحت لنموذج ثاني يصنّفها بدون ما يشوف الجواب الأول`
          : "واثق، فكمّلت";
      step("بوابة الثقة", why, gf.length ? ` (${gf.join("، ")})` : "", ".");
    }
    const r = ev(it, "recheck");
    if (r?.status === "done") {
      if (r.data.agree) step("المراجعة الثانية", "اتفقت ويا الأول.");
      else if ((it.result?.flags || []).includes("recheck_used_second")) step("المراجعة الثانية", "قالت ", el("b", { text: subAr(r.data.second) }), "، فاعتمدنا جوابها وعلّمنا التذكرة للتأكيد.");
      else step("المراجعة الثانية", "قالت ", el("b", { text: subAr(r.data.second) }), "، فتصعّدت لموظف.");
    } else if (r?.status === "error") step("المراجعة الثانية", "صار خطأ، فراحت لموظف.");
  }
  const rt = ev(it, "route");
  if (rt?.status === "done") {
    const sub = subOf(it);
    const def = S.meta.subcategories[sub]?.default_priority;
    const raised = def && rt.data.priority !== def;
    if (raised) step("التوجيه", `${rt.data.team_ar} من نوع المشكلة، والأولوية `, ltr(rt.data.priority), " ارتفعت درجة لأن المبلغ كبير؛ كلام الزبون ما يغيّر الأولوية.");
    else step("التوجيه", "القسم والأولوية ", ltr(rt.data.priority), " انحددوا من نوع المشكلة؛ كلام الزبون ما يغيّر الأولوية.");
  }
  const dr = ev(it, "draft");
  if (dr?.status === "done") {
    const f = originalDraft(it).findings;
    const text = it.ticket.text || "";
    // What the drafter was told to ask for (it may have left one out: read the draft).
    const ask = (dr.data.ask_for || []).filter((x) => !(x === "bill_type" && BILL_NAMED.test(text))).map((x) => FIELD_AR[x] || x);
    step("المسودة", ask.length ? `المفروض تطلب من الزبون: ${ask.join("، ")}. ` : "ما تحتاج تطلب شي من الزبون. ",
      f.length ? `الفحص لكى: ${f.map((x) => CHECK_SHORT_AR[x.kind] || x.kind).join("، ")}.` : `الفحص ما لكى: ${(S.meta.checks_active || []).map((k) => CHECK_SHORT_AR[k] || k).join("، ")}.`);
  } else if (dr?.status === "skipped") {
    step("المسودة", `ما انكتبت لأن ${because(it)}.`);
  } else if (dr?.status === "error") step("المسودة", "صار خطأ، فراحت لموظف.");
  body.replaceChildren(...[
    el("ol", { class: "why-steps" }, steps),
    it.live ? el("p", { class: "hint", text: "التذاكر الجديدة ما تنحفظ: إذا حدّثت الصفحة تروح من القائمة." }) : null,
    el("button", { type: "button", class: "link-btn", onclick: () => hooks.toProcess?.(it) }, "شوف كل المراحل بوضع «كيف يشتغل»"),
  ].filter(Boolean));
}

// --- states ---

function queueSkeleton() {
  return el("div", { class: "skeleton-queue", "aria-busy": "true", "aria-label": "يحمّل القائمة" },
    Array.from({ length: 7 }, () => el("div", { class: "skeleton-row" })));
}
function ticketSkeleton() {
  return el("div", { class: "skeleton-ticket", "aria-busy": "true" }, el("p", { class: "sr-only", text: "يحمّل…" }),
    el("div", { class: "skeleton-line w40" }), el("div", { class: "skeleton-line w70" }), el("div", { class: "skeleton-block" }), el("div", { class: "skeleton-block tall" }));
}
function errorState(msg) {
  return el("div", { class: "empty-state" }, el("h2", { class: "empty-title", text: "ما كدرنا نحمّل التشغيل" }),
    el("p", { text: msg }), el("button", { type: "button", class: "btn", text: "جرب مرة ثانية", onclick: () => hooks.reload?.() }));
}
function emptyQueue() {
  return el("div", { class: "empty-state" }, el("h2", { class: "empty-title", text: "ماكو تذاكر بهالتشغيل" }),
    el("p", { text: "اختار تشغيل ثاني من فوق، أو الصق تذكرة جديدة." }),
    el("button", { type: "button", class: "btn", onclick: () => hooks.newTicket?.() }, icon("plus"), "تذكرة جديدة"));
}

const decisionsAr = (n) => countAr(n, { one: "قرار واحد", two: "قرارين", few: "قرارات", many: "قرار" });

/** Every ticket decided: the session's numbers (the human feedback the project was missing). */
function allDone() {
  const recs = allItems().map((it) => S.decisions.get(it.key)).filter(Boolean);
  const s = summarize(recs);
  const med = median(s.seconds);
  const stat = (n, label) => el("div", { class: "stat" }, el("b", {}, num(n)), el("span", { text: label }));
  return el("section", { class: "all-done", "aria-labelledby": "doneTitle" },
    el("h2", { id: "doneTitle", class: "empty-title", tabindex: "-1" }, icon("done"), "خلصت القائمة"),
    el("p", {}, "قررت على ", ticketsAr(s.n), ". هذي الأرقام تنحفظ بسجل القرارات بدون نص الرد."),
    el("div", { class: "stats" },
      stat(s.approved, "اعتمدتها كما هي"), stat(s.edited, "عدّلتها واعتمدتها"), stat(s.took_over, "استلمتها بنفسك"),
      stat(s.forwarded, "حوّلتها للقسم"), stat(s.corrected, "صحّحت نوعها أو قسمها أو أولويتها")),
    el("p", {}, "المسودات اللي بقت بدون تغيير: ", num(s.keptUnchanged), " من ", num(s.drafts),
      ". الوقت الوسيط لكل تذكرة: ", fmtSeconds(med), "."),
    // Decisions faster than reading a ticket and its draft say nothing about the drafts.
    s.quick ? el("p", { class: "callout callout-warn" }, icon("check"), el("span", {},
      el("strong", {}, decisionsAr(s.quick), ` انحسمت بأقل من ${QUICK_S} ثواني.`),
      " هذا أسرع من قراية التذكرة والمسودة، فهذي القرارات ما تنحسب رأي بالمسودات.")) : null,
    s.reasons.length ? [el("h3", { class: "section-title", text: "أسباب التعديل والاستلام" }),
      el("ul", { class: "reason-counts" }, s.reasons.map(([c, n]) => el("li", {}, el("span", { text: S.meta.reason_codes_ar[c] || c }), num(n))))]
      : el("p", { class: "hint", text: "ما اخترت أسباب للتعديل أو الاستلام." }));
}

export function liveUpdated(it) {
  renderQueue();
  if (S.agent.openKey !== it.key) return;
  if (it.status === "running") {
    $("liveSteps")?.replaceWith(liveSteps(it));
  } else {
    const hadFocus = $("agentMain").contains(document.activeElement);
    S.agent.tab = tabOf(it);
    // The agent's time starts when the result is on screen, not while the pipeline worked on it.
    if (S.mode === "agent" && !document.hidden) startClock(it);
    renderQueue();
    renderTicket();
    renderWhy();
    if (hadFocus) $("ticketTitle")?.focus();
  }
}

export function setBudgetBanner() {
  const title = "وصل التشغيل لحد الصرف.";
  setBanner("budget", { kind: "bad", icon: "escalated", title,
    text: "التذاكر الجديدة ما تنرسل لنموذج وتروح لموظف. التشغيلات المحفوظة والقرارات تشتغل عادي." });
  showToast(`${title} التذاكر الجديدة تروح لموظف بدون نموذج.`);
}

export { pauseClock };
