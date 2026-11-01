// "كيف يشتغل": how the pipeline reached each answer, and how well it does. The run and ticket-set
// picker, the overview against the gold labels, each ticket stage by stage with exactly what each model
// was sent and returned, a replay, "run all" over a ticket set, and what agents decided on the run.

import { NetworkError, ServerError, getJSON } from "./api.js";
import { streamTicket, liveState } from "./live.js";
import { CHANGE_AR, DECISION_AR, DIFF_AR, FIELD_AR, LIVE_CAUSE_AR, OUTCOME_AR, OUTCOME_SHORT, STAGES, TAG_AR } from "./labels.js";
import { QUICK_S, S, restoreDecisions, summarize } from "./state.js";
import { showToast } from "./ui.js";
import {
  add, digitRuns, dict, el, fmtInt, ltr, median, mono, num, openDialog, plainText, reducedMotion, richText, ticketsAr,
  westernDigits,
} from "./util.js";

const hooks = { toAgent: null, savePrefs: null, loadOnPick: null };
export function setProcessHooks(h) { Object.assign(hooks, h); }

const P = {
  source: null,          // "run:<name>" or "set:<name>"
  run: null,             // the run JSON (runs)
  tickets: [],           // the tickets shown in the list
  results: new Map(),    // set tickets run live here: id → {events, result}
  status: new Map(),     // id → outcome or "running"
  current: null,         // the ticket key on screen
  timers: [],            // replay timers: cleared on every change of view
  ctl: null,             // the live run going on here
  runAll: false,
  loadedFor: null,
  follow: null,          // the live ticket whose events this view follows
  replaying: false,      // a replay is drawing its stages one by one
  interrupted: false,    // the mode switched mid-replay: draw the ticket again on return
};
const $ = (id) => document.getElementById(id);

export function stopProcess() {
  if (P.replaying) P.interrupted = true;
  P.replaying = false;
  clearTimers();
}
function clearTimers() {
  for (const t of P.timers) clearTimeout(t);
  P.timers = [];
}

const subLabel = (k) => (S.meta.subcategories[k] ? `${S.meta.subcategories[k].category_label} › ${S.meta.subcategories[k].label}` : k ?? "—");
const fmtAmount = (ex) => (ex.amount_iqd != null ? `${fmtInt(ex.amount_iqd)} دينار` : ex.amount_usd != null ? `${fmtInt(ex.amount_usd)} دولار` : null);
const norm = (s) => (s ? westernDigits(String(s)).replace(/[^0-9A-Za-z]/g, "").toLowerCase() : null);
const backendAr = (b) => (b === "cli" ? "خطة Claude (تطوير)" : b === "api" ? "API" : b || "—");
/** Isolated, with the direction of its own first letter (a <bdi> with no dir is dir=auto). */
const bidiAuto = (text) => el("bdi", { text: String(text) });
/** Seconds in this view: «5.3 ث», like the inbox. */
const secs = (x) => [num((Number(x) || 0).toFixed(1)), " ث"];
const BUSY_AR = "اكو تذكرة دتنعالج هسه، انتظر لما تخلص.";

// --- the side list ---

export async function renderProcess() {
  const nav = $("processNav");
  if (!nav.dataset.built) buildNav(nav);
  if (P.loadedFor !== P.source) await loadSource(P.source);
  drawList();
  if (!P.current) showDefault();
  else if (P.interrupted && P.run) {   // left mid-replay: draw that ticket whole
    P.interrupted = false;
    const i = P.tickets.findIndex((t) => t.id === P.current);
    if (i >= 0) replay(i, { instant: true });
  }
}

function buildNav(nav) {
  nav.dataset.built = "1";
  const src = el("select", { id: "pSource", class: "select" });
  const g1 = el("optgroup", { label: "مجموعات تذاكر (تشغيل مباشر)" });
  S.sets.forEach((n) => g1.append(el("option", { value: `set:${n}`, text: n })));
  const g2 = el("optgroup", { label: "التشغيل النهائي (محفوظ بالمشروع)" });
  const g3 = el("optgroup", { label: "تشغيلات دفعة" });
  const g4 = el("optgroup", { label: "تجارب الإصلاحات" });
  for (const r of S.runs) {
    const name = r.name.split("/").pop();
    const fixes = r.fixes?.length ? (r.fixes.length > 3 ? ` (${r.fixes.length} إصلاحات)` : ` (${r.fixes.join("، ")})`) : "";
    const g = r.name.startsWith("saved/") ? g2 : r.experiment ? g4 : g3;
    g.append(el("option", { value: `run:${r.name}`, text: r.experiment ? `${r.set} · ${name}${r.name.startsWith("saved/") ? "" : fixes}` : `${r.set} · ${(r.started || "").replace("T", " ").slice(0, 16)} · ${r.backend}` }));
  }
  for (const g of [g2, g3, g4, g1]) if (g.children.length) src.append(g);
  if (!P.source) P.source = S.agent.source ? `run:${S.agent.source}` : src.options[0]?.value;
  src.value = P.source;
  // A keyboard user can browse the options: the source loads on Enter or when the select is left.
  const pick = async (v) => {
    if (P.ctl) { src.value = P.source; showToast("اكو تشغيل هنا: وقّفه أو انتظره يخلص أول."); return; }
    P.source = v;
    P.current = null;
    clearTimers();
    await loadSource(P.source);
    drawList();
    showDefault();
  };
  if (hooks.loadOnPick) hooks.loadOnPick(src, pick);
  else src.addEventListener("change", () => pick(src.value));
  const sort = el("select", { id: "pSort", class: "select" },
    el("option", { value: "received", text: "بترتيب الوصول" }),
    el("option", { value: "priority", text: "حسب الأولوية (P1 والمتصعّدة أول)" }),
    el("option", { value: "team", text: "حسب القسم" }));
  sort.addEventListener("change", drawList);
  const overview = el("button", { type: "button", id: "pOverview", class: "btn btn-small", text: "ملخص التشغيل",
    onclick: () => { P.current = null; clearTimers(); showDefault(); drawList(); } });
  const runAll = el("button", { type: "button", id: "pRunAll", class: "btn btn-small", text: "شغّل كل القائمة", onclick: confirmRunAll });
  const stop = el("button", { type: "button", id: "pStop", class: "btn btn-small", text: "وقّف التشغيل", hidden: true,
    onclick: () => { P.runAll = false; P.ctl?.abort(); } });
  nav.replaceChildren(
    el("div", { class: "pnav-controls" },
      el("label", { class: "field" }, el("span", { text: "المصدر" }), src),
      el("label", { class: "field" }, el("span", { text: "الترتيب" }), sort),
      el("div", { class: "row-btns" }, overview, runAll, stop)),
    el("p", { id: "pMeta", class: "hint" }),
    el("p", { class: "hint pnav-live" }, "التشغيل المباشر هنا: ", backendAr(S.meta.backend), " · ",
      ltr(S.meta.models.classifier || "", "mono nowrap"), " / ", ltr(S.meta.models.drafter || "", "mono nowrap"),
      S.meta.mode !== "full" ? ` · الوضع ${S.meta.mode === "off" ? "موقف" : "تصنيف بس"}` : "",
      // The technical cause stays here; the agent sees one plain sentence.
      // A setting name reads left to right; an Arabic cause («أداة claude مو موجودة») keeps its own order.
      !S.meta.live.available && S.meta.live.cause ? [" · مو مفعّل: ", bidiAuto(LIVE_CAUSE_AR[S.meta.live.cause] || S.meta.live.cause)] : ""),
    el("ul", { id: "pList", class: "plist", "aria-label": "التذاكر" }));
}

async function loadSource(v) {
  P.loadedFor = v;
  P.results = new Map();
  P.status = new Map();
  const [kind, name] = [v.slice(0, 3), v.slice(4)];
  $("pList")?.replaceChildren(el("li", { class: "hint", text: "يحمّل…" }));
  try {
    if (kind === "set") {
      P.run = null;
      P.tickets = await getJSON(`/api/tickets?set=${encodeURIComponent(name)}`);
    } else {
      P.run = await getJSON(`/api/run?name=${encodeURIComponent(name)}`);
      P.tickets = P.run.tickets.map((r) => r.ticket);
      P.run.tickets.forEach((r) => P.status.set(r.ticket.id, r.result.outcome));
    }
  } catch (e) {
    P.run = null;
    P.tickets = [];
    $("processMain").replaceChildren(el("div", { class: "empty-state" }, el("h2", { class: "empty-title", text: "ما كدرنا نحمّل المصدر" }),
      el("p", { text: e instanceof ServerError ? e.message : "انقطع الاتصال بالخادم." })));
  }
  const isSet = kind === "set";
  $("pRunAll").hidden = !isSet;
  $("pOverview").hidden = isSet;
  const m = P.run?.meta;
  $("pMeta").replaceChildren(...(m ? [`${m.set} · `, ltr((m.started || "").replace("T", " ").slice(0, 16)), " · ", backendAr(m.backend),
    el("br"), ltr(m.models?.classifier || "", "mono nowrap"), " / ", ltr(m.models?.drafter || "", "mono nowrap")]
    : [ticketsAr(P.tickets.length), " بدون نتائج: شغّلها حتى تشوف المراحل."]));
}

function rowResult(i) {
  return P.run?.tickets[i]?.result || P.results.get(P.tickets[i]?.id)?.result || {};
}

function order() {
  const by = $("pSort")?.value || "received";
  const idx = P.tickets.map((_, i) => i);
  if (by === "received") return idx;
  const rank = { escalated: 0, flagged: 1, drafted: 2 };
  const pri = (i) => ({ P1: 1, P2: 2, P3: 3 })[rowResult(i).priority] ?? 9;
  const cmp = by === "team"
    ? (a, b) => (rowResult(a).team || "~").localeCompare(rowResult(b).team || "~") || pri(a) - pri(b) || a - b
    : (a, b) => pri(a) - pri(b) || (rank[rowResult(a).outcome] ?? 9) - (rank[rowResult(b).outcome] ?? 9) || a - b;
  return idx.sort(cmp);
}

function drawList() {
  const list = $("pList");
  if (!list) return;
  const by = $("pSort")?.value;
  const rows = order().map((i) => {
    const t = P.tickets[i];
    const key = t.id || `custom-${i}`;
    const res = rowResult(i);
    const st = P.status.get(key) || "";
    const verdict = P.run ? (scoreRow(P.run.tickets[i]).sub ? el("span", { class: "mark-ok", text: " ✓", "aria-label": "النوع صحيح" })
      : el("span", { class: "mark-no", text: " ✗", "aria-label": "النوع غلط" })) : null;
    const meta = [ltr(t.id || ""), res.priority ? [" · ", ltr(res.priority)] : null,
      res.team && by === "team" ? ` · ${S.meta.teams[res.team]?.label_ar}` : null,
      t.difficulty ? ` · ${DIFF_AR[t.difficulty] || t.difficulty}` : null, t.edge_case ? [" · ", TAG_AR[t.edge_case] || ltr(t.edge_case)] : null,
      t.trap ? [" · ", ltr(t.trap)] : null];
    const b = el("button", { type: "button", class: "prow", "aria-current": P.current === key ? "true" : null },
      el("span", { class: `pdot ${st}`, "aria-hidden": "true" }),
      el("span", { class: "prow-body" }, el("span", { class: "prow-text", dir: "rtl" }, digitRuns(plainText(t.text).text)),
        el("span", { class: "prow-meta" }, meta, st ? ` · ${OUTCOME_SHORT[st] || (st === "running" ? "تنعالج" : "")}` : "", verdict)));
    b.addEventListener("click", () => openTicket(i));
    return el("li", {}, b);
  });
  list.replaceChildren(...rows);
}

export function showDefault() {
  clearTimers();
  if (P.run) return renderOverview();
  $("processMain").replaceChildren(el("div", { class: "empty-state" },
    el("h2", { class: "empty-title", text: "مجموعة تذاكر بدون نتائج" }),
    el("p", { text: "اختار تذكرة حتى تشوفها وتشغّلها مرحلة بمرحلة، أو شغّل القائمة كلها." }),
    el("p", { class: "hint" }, "التشغيل يستدعي النموذج، يعني يكلف من الرصيد. ", liveState().ok ? "" : liveState().reason)));
}

/** Open a ticket by its index in P.tickets: a saved run replays, a set ticket shows its text and a run button. */
function openTicket(i) {
  if (P.ctl && !P.runAll) return;
  clearTimers();
  const t = P.tickets[i];
  P.current = t.id;
  drawList();
  if (P.run) return replay(i);
  const done = P.results.get(t.id);
  buildView(t, `مجموعة ${P.source.slice(4)}`);
  if (done) { done.events.forEach(render); renderResultBox(done.result, t); return; }
  const st = liveState();
  $("pResult").replaceChildren(el("div", { class: "result" },
    el("p", { class: "hint", text: "هذي التذكرة ما انشغلت بعد. التشغيل يستدعي النموذج (يكلف من الرصيد)." }),
    el("button", { type: "button", class: "btn btn-primary", "aria-disabled": st.ok ? null : "true",
      onclick: () => st.ok && runOne(t) }, "شغّل هذي التذكرة"),
    st.ok ? null : el("p", { class: "hint", text: st.reason })));
  if (t.subcategory) $("pResult").append(goldTable(t, {}));
}

export function openRunTicket(id) {
  const i = P.tickets.findIndex((t) => t.id === id);
  if (i >= 0) openTicket(i);
}
/** Open a ticket of the run on screen by id (the stage map's examples). */
function openById(id) {
  P.interrupted = false;
  openRunTicket(id);
  $("traceTitle")?.focus();
}

/** Show a live ticket (from the agent's queue) stage by stage. */
export function showLive(item) {
  clearTimers();
  P.current = item.key;
  drawList();
  buildView({ id: item.key, text: item.ticket.text }, "تذكرة مباشرة");
  item.events.forEach(render);
  P.follow = item.key;
}
export function liveEvent(item, e) {
  if (P.follow === item.key && P.current === item.key && document.body.dataset.mode === "process") render(e);
}

// --- one ticket, stage by stage ---

function buildView(ticket, origin) {
  const list = el("ol", { class: "stages" });
  for (const [id, name, kind, desc] of STAGES) {
    const model = kind !== "rule" ? S.meta.models[kind] : null;
    list.append(el("li", { class: "stage", id: `st-${id}` },
      el("div", { class: "stage-head" },
        el("h3", { text: name }),
        el("span", { class: model ? "kind model" : "kind" }, model ? ltr(model) : "قاعدة ثابتة"),
        el("span", { class: "state" })),
      el("p", { class: "stage-desc", text: desc }),
      el("div", { class: "stage-body" })));
  }
  $("processMain").replaceChildren(el("article", { class: "trace", "aria-labelledby": "traceTitle" },
    el("h2", { id: "traceTitle", class: "trace-title", tabindex: "-1" }, ticket.id ? ["التذكرة ", mono(ticket.id)] : "تذكرة جديدة",
      el("span", { class: "trace-origin", text: ` · ${origin}` })),
    el("div", { class: "slip", dir: "rtl" }, digitRuns(plainText(ticket.text).text)),
    list,
    el("div", { id: "pResult" })));
}

function setStage(id, st, ms) {
  const n = $(`st-${id}`);
  if (!n) return null;
  n.className = `stage ${st}`;
  const label = dict({ running: "يشتغل…", done: secs(ms / 1000), skipped: "تخطّى", error: "خطأ" })[st] || "";
  n.querySelector(".state").replaceChildren(...[label].flat());
  return n.querySelector(".stage-body");
}

function usageText(u) {
  if (!u || u.input_tokens == null) return null;
  return el("p", { class: "note" }, "التوكنز: ", ltr(fmtInt(u.input_tokens)), " داخل / ", ltr(fmtInt(u.output_tokens)), " طالع",
    u.cost_usd ? [" · الكلفة المحسوبة ", ltr(`$${u.cost_usd.toFixed(4)}`)] : "", u.cached ? " · من الكاش" : "");
}

function promptDetails(d) {
  return el("details", { class: "io" }, el("summary", { text: "شوف اللي انرسل للنموذج وجوابه" }),
    usageText(d.usage),
    el("p", { class: "note", text: "الرسالة:" }), el("pre", { dir: "ltr", text: d.user_prompt || "" }),
    el("p", { class: "note", text: "الجواب كما هو:" }), el("pre", { dir: "ltr", text: d.reply || "" }));
}

function fieldsList(ex) {
  const rows = [
    ["سؤال ثاني", ex.secondary_subcategory ? subLabel(ex.secondary_subcategory) : null],
    ["رقم العملية", ex.reference ? mono(ex.reference) : null], ["رقم المستلم", ex.recipient_phone ? mono(ex.recipient_phone) : null],
    ["المبلغ", fmtAmount(ex) ? richText(fmtAmount(ex)) : null], ["الوقت", ex.date],
    ["الاحتمال الثاني", ex.runner_up ? subLabel(ex.runner_up) : null],
  ];
  if (ex.fee_iqd != null) rows.splice(4, 0, ["العمولة المعترض عليها", richText(`${fmtInt(ex.fee_iqd)} دينار`)]);
  return el("dl", { class: "kv" }, rows.map(([k, v]) => [el("dt", { text: k }), el("dd", {}, v ?? "—")]));
}

function scale(d) {
  const t = S.meta.thresholds;
  const pct = (x) => `${Math.max(0, Math.min(1, x)) * 100}%`;
  const zone = (cls, w, text) => { const z = el("div", { class: `zone ${cls}`, text }); z.style.width = pct(w); return z; };
  const track = el("div", { class: "track" }, zone("esc", t.recheck_from, "يتصعّد"), zone("rec", t.pass_above - t.recheck_from, "ينراجع"), zone("pass", 1 - t.pass_above, "يكمل"));
  const markers = el("div", { class: "markers" });
  const changed = Math.abs(d.model_confidence - d.confidence) > 0.005;
  if (changed) {
    const m = el("div", { class: "mark model" }, el("span", { class: "pin" }), `النموذج ${d.model_confidence.toFixed(2)}`);
    m.style.left = pct(d.model_confidence);
    markers.append(m);
  }
  const fin = el("div", { class: "mark final" }, el("span", { class: "pin" }), `${changed ? "بعد القواعد" : "الثقة"} ${d.confidence.toFixed(2)}`);
  fin.style.left = pct(changed && !reducedMotion() ? d.model_confidence : d.confidence);
  markers.append(fin);
  if (changed && !reducedMotion()) P.timers.push(setTimeout(() => { fin.style.left = pct(d.confidence); }, 250));
  // Each label sits at its own value, like the markers (the zones change at 0.60 and 0.75).
  const ticks = el("div", { class: "ticks" }, [0, t.recheck_from, t.pass_above, 1].map((x) => {
    const s = el("span", { class: x === 0 ? "tick-start" : x === 1 ? "tick-end" : null, text: String(x) });
    s.style.left = pct(x);
    return s;
  }));
  return el("div", { class: "scale", dir: "ltr", role: "img", "aria-label": `الثقة ${d.confidence.toFixed(2)}: التصعيد تحت ${t.recheck_from}، المراجعة لحد ${t.pass_above}` },
    track, markers, ticks);
}

function render(e) {
  const d = e.data || {};
  if (e.stage === "result") return renderResultBox(d, P.tickets.find((t) => t.id === P.current));
  const body = setStage(e.stage, e.status, e.ms);
  if (!body) return;
  body.replaceChildren();
  if (e.status === "skipped") return add(body, el("p", { class: "note", text: d.why ? `ما احتاجت: ${d.why}` : "ما احتاجت" }));
  if (e.status === "error") return add(body, el("p", { class: "chip bad" }, d.error, d.kind ? [" · ", ltr(d.kind)] : ""));
  if (e.status === "running") return;
  if (e.stage === "received") add(body, el("p", { class: "note" }, num(d.chars), " حرف"));
  if (e.stage === "clean") {
    add(body, el("div", { class: "cleaned", dir: "rtl", text: d.text }));
    const ch = Object.entries(d.changes || {}).filter(([, n]) => n > 0);
    add(body, el("div", { class: "chips" }, ch.length ? ch.map(([k, n]) => el("span", { class: "chip" }, num(n), ` ${CHANGE_AR[k] || k}`)) : el("span", { class: "note", text: "ما احتاجت تنظيف" })));
  }
  if (e.stage === "classify" || e.stage === "recheck") {
    const ex = d.extraction || {};
    if (e.stage === "recheck") add(body, el("p", { class: `chip ${d.agree ? "ok" : "bad"}`, text: d.agree ? "متفق مع التصنيف الأول" : `مختلف: قال ${subLabel(d.second)}` }));
    add(body, el("p", { class: "big", text: subLabel(ex.subcategory) }), fieldsList(ex),
      el("p", { class: "note" }, "ثقة النموذج بنفسه: ", ltr((ex.confidence ?? 0).toFixed(2))),
      ex.rationale ? el("div", { class: "rationale" }, el("p", { class: "note", text: "تفسير النموذج (إنكليزي):" }), el("p", { dir: "ltr", lang: "en", class: "rationale-text", text: ex.rationale })) : null,
      d.cleared_secondary ? el("p", { class: "note", text: `انشال السؤال الثاني (${subLabel(d.cleared_secondary)}): نتيجة للاحتيال مو طلب ثاني.` }) : null,
      promptDetails(d));
  }
  if (e.stage === "gate") {
    add(body, scale(d), el("p", { class: `decision ${d.decision}`, text: DECISION_AR[d.decision] }));
    const chips = (d.flags || []).map((f) => el("span", { class: f === "fraud" ? "chip bad" : "chip warn", text: S.meta.flag_ar[f] || f }));
    if (d.high_risk && d.decision === "recheck" && d.confidence >= S.meta.thresholds.pass_above) chips.push(el("span", { class: "chip warn", text: "نوع حساس: ينراجع دائماً" }));
    if (chips.length) add(body, el("div", { class: "chips" }, chips));
    if (d.reasons?.length) add(body, el("p", { class: "note", dir: "ltr", lang: "en", text: d.reasons.join("; ") }));
  }
  if (e.stage === "route") {
    add(body, el("dl", { class: "kv" }, el("dt", { text: "القسم" }), el("dd", { text: d.team_ar }), el("dt", { text: "الأولوية" }), el("dd", {}, ltr(d.priority))));
    if (d.fee_call) add(body, el("p", { class: "note" }, "استدعاء صغير للعمولة: ", d.fee_call.fee_iqd != null ? richText(`${fmtInt(d.fee_call.fee_iqd)} دينار`) : "ما لكى عمولة"), usageText(d.usage));
  }
  if (e.stage === "draft") {
    if (d.ask_for?.length) add(body, el("div", { class: "chips" }, el("span", { class: "note", text: "يطلب من الزبون: " }), d.ask_for.map((f) => el("span", { class: "chip warn", text: FIELD_AR[f] || f }))));
    add(body, el("div", { class: "bubble", dir: "rtl" }, digitRuns(d.reply)));
    const checks = d.check_spans || [];
    if (checks.length) add(body, el("div", { class: "chips" }, checks.map((f) => el("span", { class: "chip warn" }, S.meta.check_ar[f.kind] || f.kind, ": «", f.text, "»"))));
    else add(body, el("p", { class: "note", text: "فحص المسودة ما لكى شي." }));
    if (d.check_spans_recomputed) add(body, el("p", { class: "note", text: "هذا التشغيل أقدم من فحص المسودات، فانفحصت هسه بنفس القواعد." }));
    add(body, promptDetails(d));
  }
}

function renderResultBox(d, gold) {
  const box = el("div", { class: `result ${d.outcome}` },
    el("p", { class: "outcome", text: OUTCOME_AR[d.outcome] || d.outcome }),
    d.notes_ar?.length ? el("div", { class: "chips" }, d.notes_ar.map((n) => el("span", { class: "chip", text: n }))) : null,
    d.team ? el("p", { class: "note" }, `${S.meta.teams[d.team]?.label_ar || d.team} · `, ltr(d.priority || "—")) : null,
    d.handoff_ar ? el("div", { class: "handoff-box" }, el("p", { class: "note", text: "ملاحظة للقسم المستلم" }), el("p", { class: "handoff-body", dir: "rtl" }, richText(d.handoff_ar))) : null,
    d.usage ? usageText(d.usage) : null);
  const inAgent = P.run && S.agent.source && P.source === `run:${S.agent.source}` && gold?.id;
  if (inAgent) add(box, el("button", { type: "button", class: "btn btn-small", text: "افتحها بوضع الموظف", onclick: () => hooks.toAgent?.(gold.id) }));
  if (P.follow && P.current === P.follow) add(box, el("button", { type: "button", class: "btn btn-small", text: "افتحها بوضع الموظف", onclick: () => hooks.toAgent?.(P.follow) }));
  if (gold?.subcategory) add(box, goldTable(gold, d));
  $("pResult")?.replaceChildren(box);
}

function goldTable(g, d) {
  const ex = d.extraction || {};
  const rows = [
    ["subcategory", "النوع", g.subcategory, ex.subcategory, subLabel],
    ["reference", "رقم العملية", g.reference, ex.reference, (x) => x ?? "—", true],
    ["amount_iqd", "المبلغ (دينار)", g.amount_iqd, ex.amount_iqd, (x) => (x != null ? fmtInt(x) : "—")],
    ["amount_usd", "المبلغ (دولار)", g.amount_usd, ex.amount_usd, (x) => x ?? "—"],
    ["priority", "الأولوية", g.priority, d.priority, (x) => x ?? "—"],
    ["outcome", "النتيجة", g.outcome, d.outcome, (x) => OUTCOME_SHORT[x] ?? "—"],
  ].filter((r) => r[0] in g).map((r) => r.slice(1));
  const tb = el("tbody");
  const ran = d.outcome != null;
  for (const [k, want, got, f, isRef] of rows) {
    const ok = isRef ? norm(want) === norm(got) : (want ?? null) === (got ?? null);
    tb.append(el("tr", {}, el("th", { scope: "row", text: k }), el("td", {}, f(want)),
      el("td", {}, !ran ? "—" : ok ? el("span", { class: "mark-ok", text: "✓" }) : el("span", {}, el("span", { class: "mark-no", text: "✗ " }), "طلع: ", f(got)))));
  }
  const tags = [g.difficulty && (DIFF_AR[g.difficulty] || g.difficulty), ...[g.edge_case, g.dialect, g.style].map((x) => x && (TAG_AR[x] || x))].filter(Boolean);
  return el("div", { class: "gold" },
    el("p", { class: "note" }, "الجواب المتوقع", tags.length ? [" · ", tags.join(" · ")] : ""),
    el("div", { class: "table-wrap" }, el("table", { class: "grid" }, el("thead", {}, el("tr", {}, ["الحقل", "المتوقع", "النظام"].map((h) => el("th", { scope: "col", text: h })))), tb)));
}

function replay(i, { instant = false } = {}) {
  const row = P.run.tickets[i];
  buildView(row.ticket, "إعادة عرض من تشغيل محفوظ");
  $("processMain").querySelector(".trace").prepend(el("p", { class: "note" }, `تشغيل محفوظ · ${backendAr(P.run.meta.backend)} · `, secs(row.seconds)));
  const evs = row.events.filter((e) => e.status !== "running");
  if (!evs.some((e) => e.stage === "result")) evs.push({ stage: "result", status: "done", data: row.result, ms: 0 });
  if (instant || reducedMotion()) {
    evs.forEach(render);
  } else {
    P.replaying = true;
    evs.forEach((e, k) => P.timers.push(setTimeout(() => {
      render(e);
      if (k === evs.length - 1) P.replaying = false;
    }, k * 160)));
  }
  $("traceTitle")?.focus({ preventScroll: true });
}

// --- running set tickets ---

async function runOne(t) {
  if (P.ctl) return false;
  if (S.liveBusy) { showRefusal(BUSY_AR); return false; }
  const src = P.source;   // if the view moves to another source meanwhile, this run stops drawing
  clearTimers();
  P.current = t.id;
  P.status.set(t.id, "running");
  P.follow = null;
  drawList();
  buildView(t, `مجموعة ${P.source.slice(4)}`);
  const events = [];
  let result = null;
  P.ctl = new AbortController();
  S.liveBusy = true;
  $("pStop").hidden = false;
  try {
    const status = await streamTicket(t.text, {
      signal: P.ctl.signal,
      onEvent: (e) => {
        events.push(e);
        if (e.stage === "result") result = e.data;
        if (P.current === t.id && P.source === src) render(e);
      },
    });
    if (status !== "done" && P.source === src) showRefusal(status === "cancelled" ? "انلغى التشغيل." : "انقطع الاتصال قبل ما تخلص التذكرة.");
  } catch (e) {
    if (P.source === src) showRefusal(e instanceof ServerError ? e.message : e instanceof NetworkError ? "انقطع الاتصال بالخادم." : "ما انشغلت التذكرة.");
  } finally {
    P.ctl = null;
    S.liveBusy = false;
    $("pStop").hidden = true;
  }
  if (P.source !== src) return false;
  if (result) P.results.set(t.id, { events, result });
  P.status.set(t.id, result?.outcome || "");
  drawList();
  return !!result;
}

function showRefusal(msg) {
  $("pResult")?.replaceChildren(el("div", { class: "result escalated" }, el("p", { class: "outcome", text: msg })));
}

function confirmRunAll() {
  if (P.ctl || !P.tickets.length) return;
  const st = liveState();
  const dlg = $("confirmDialog");
  const n = P.tickets.length;
  const off = S.meta.mode === "off";
  $("confirmText").replaceChildren(...[st.ok
    ? ["راح نشغّل ", ticketsAr(n), "، وحدة ورا الثانية. ", off ? "النظام موقف، فما راح ينستدعى أي نموذج وكل تذكرة تروح لموظف."
      : ["كل تذكرة تستدعي النموذج (", backendAr(S.meta.backend), ")، يعني تكلف من الرصيد. حد الصرف يوقف التشغيل إذا وصله."]]
    : [st.reason]].flat(Infinity).map((x) => (x?.nodeType ? x : document.createTextNode(String(x)))));
  const ok = $("confirmOk");
  ok.hidden = !st.ok;
  ok.onclick = () => { dlg.close(); runAll(); };
  $("confirmCancel").onclick = () => dlg.close();
  openDialog(dlg, $("confirmCancel"));
}

async function runAll() {
  P.runAll = true;
  for (const t of [...P.tickets]) {
    if (!P.runAll) break;
    const ok = await runOne(t);
    if (!ok) break;
  }
  P.runAll = false;
}

// --- the overview ---

/** The process at a glance, before any number: each step, whether a rule or a model does it, how many
 *  tickets of this run went through it, and an example ticket to open. */
function stageStrip(rows) {
  const done = (stage) => rows.filter((r) => ev(r, stage)?.status === "done");
  const gate = done("gate").map((r) => ev(r, "gate").data?.decision);
  const nGate = (d) => gate.filter((x) => x === d).length;
  const t = S.meta.thresholds;
  const first = (stage, pred = () => true) => rows.find((r) => ev(r, stage)?.status === "done" && pred(r))?.ticket.id;
  const steps = [
    ["الاستلام", "قاعدة", ticketsAr(rows.length), first("received") || rows[0]?.ticket.id],
    ["التنظيف", "قاعدة", ["توحيد الأرقام والمسافات"], first("clean")],
    ["التصنيف والاستخراج", "نموذج", [num(done("classify").length), " انصنّفت"], first("classify")],
    ["بوابة الثقة", ["قاعدة · ", ltr(`${t.recheck_from} / ${t.pass_above}`)],
      [num(nGate("pass")), " كمّلت · ", num(nGate("recheck")), " انراجعت · ", num(nGate("escalate")), " تصعّدت"],
      first("gate", (r) => ev(r, "gate").data?.decision === "recheck") || first("gate")],
    ["المراجعة الثانية", "نموذج ثاني", [num(done("recheck").length), " انراجعت"], first("recheck")],
    ["التوجيه والأولوية", "قاعدة", ["القسم والأولوية من النوع"], first("route")],
    ["المسودة", "نموذج", [num(done("draft").length), " مسودة، وفحصها بالقواعد"], first("draft")],
    ["الموظف يقرر", "إنسان", ["يعتمد أو يعدّل أو يستلم أو يحوّل. ما ينرسل شي تلقائياً"], null],
  ];
  return el("ol", { class: "stage-strip", "aria-label": "مراحل النظام بهالتشغيل" }, steps.map(([name, kind, count, id], k) => {
    const body = [el("span", { class: "ss-name" }, el("span", { class: "ss-n", "aria-hidden": "true", text: String(k + 1) }), name),
      el("span", { class: `ss-kind ${kind === "إنسان" ? "human" : String(kind).startsWith("نموذج") ? "model" : "rule"}` }, kind),
      el("span", { class: "ss-count" }, count)];
    return el("li", { class: "ss" }, id
      ? el("button", { type: "button", class: "ss-btn", title: `مثال: ${id}`, onclick: () => openById(id) }, body, el("span", { class: "ss-eg" }, "مثال ", mono(id)))
      : el("div", { class: "ss-btn is-static" }, body));
  }));
}

function ev(row, stage) {
  return row.events.find((e) => e.stage === stage && e.status !== "running");
}

function scoreRow(row) {
  const g = row.ticket, r = row.result;
  const cl = ev(row, "classify"), gate = ev(row, "gate"), rc = ev(row, "recheck"), dr = ev(row, "draft");
  const ex = cl?.status === "done" ? cl.data.extraction : null;
  // The type the pipeline acted on: the re-check's answer when it was used, else the first model's.
  const used = r.extraction?.subcategory ?? ex?.subcategory;
  return {
    sub: !!used && used === g.subcategory,
    firstSub: !!ex && ex.subcategory === g.subcategory,
    got: used, conf: ex?.confidence, gateConf: gate?.data.confidence,
    outcome: r.outcome === g.outcome, priority: r.priority === g.priority,
    recheck: rc?.status === "done", agree: rc?.data?.agree,
    calls: (cl ? 1 : 0) + (rc?.status === "done" ? 1 : 0) + (dr?.status === "done" ? 1 : 0),
  };
}

function accCell(a, b) {
  const p = b ? a / b : 0;
  const i = el("i");
  i.style.width = `${Math.round(p * 60)}px`;
  return el("span", { class: "acc" }, i, ltr(`${a}/${b}`));
}

async function renderOverview() {
  P.current = null;
  const rows = P.run.tickets, n = rows.length, sc = rows.map(scoreRow);
  const count = (f) => sc.filter(f).length;
  const pct = (a, b) => (b ? Math.round((100 * a) / b) : 0);
  const outc = { drafted: 0, flagged: 0, escalated: 0 };
  rows.forEach((r) => { outc[r.result.outcome] = (outc[r.result.outcome] || 0) + 1; });
  const calls = sc.reduce((a, s) => a + s.calls, 0);
  const avg = rows.reduce((a, r) => a + (r.seconds || 0), 0) / (n || 1);
  const usages = rows.flatMap((r) => r.events.filter((e) => e.status === "done" && e.data.usage?.input_tokens != null).map((e) => e.data.usage));
  const tokens = usages.reduce((a, u) => a + u.input_tokens + u.output_tokens, 0);
  const cost = usages.reduce((a, u) => a + (u.cost_usd || 0), 0);
  const stat = (b, t) => el("div", { class: "stat" }, el("b", {}, typeof b === "string" ? ltr(b) : b), el("span", { text: t }));

  const stats = el("div", { class: "stats" },
    stat(`${count((s) => s.sub)}/${n}`, "نوع المشكلة صحيح"), stat(`${count((s) => s.outcome)}/${n}`, "النتيجة صحيحة"),
    stat(`${count((s) => s.priority)}/${n}`, "الأولوية صحيحة"), stat(`${pct(outc.flagged + outc.escalated, n)}%`, "تحتاج أكثر من اعتماد بضغطة (الهدف ≤ 30%)"),
    stat(`${pct(outc.escalated, n)}%`, "نسبة التصعيد"), stat(`${count((s) => s.recheck)}`, "راحت للمراجعة الثانية"),
    stat((calls / (n || 1)).toFixed(1), "استدعاء نموذج لكل تذكرة"), stat(secs(avg), "معدل وقت التذكرة"),
    stat(usages.length ? fmtInt(Math.round(tokens / n)) : "—", "توكنز لكل تذكرة"),
    stat(cost ? `$${(cost / n).toFixed(4)}` : "—", "الكلفة المحسوبة لكل تذكرة"));

  // The bar shows the share; the words and counts are in the legend under it, so a narrow segment
  // never cuts them off.
  const shown = ["drafted", "flagged", "escalated"].filter((k) => outc[k]);
  const bar = el("div", { class: "bar", role: "img", "aria-label": Object.entries(outc).map(([k, v]) => `${OUTCOME_SHORT[k]} ${v}`).join("، ") },
    shown.map((k) => {
      const d = el("div", { class: k, "aria-hidden": "true" });
      d.style.width = `${(100 * outc[k]) / n}%`;
      return d;
    }));
  const legend = el("ul", { class: "bar-legend", "aria-hidden": "true" },
    shown.map((k) => el("li", {}, el("span", { class: `swatch ${k}` }), `${OUTCOME_SHORT[k]} `, num(outc[k]))));

  const diffs = ["easy", "medium", "hard"].filter((d) => rows.some((r) => r.ticket.difficulty === d));
  const diffTable = el("table", { class: "grid" }, el("caption", { class: "sr-only", text: "حسب الصعوبة" }), el("thead", {}, el("tr", {}, ["المستوى", "التذاكر", "النوع صحيح", "النتيجة صحيحة"].map((h) => el("th", { scope: "col", text: h })))),
    el("tbody", {}, diffs.map((d) => {
      const idx = rows.map((_, i) => i).filter((i) => rows[i].ticket.difficulty === d);
      return el("tr", {}, el("td", { text: DIFF_AR[d] }), el("td", {}, num(idx.length)),
        el("td", {}, accCell(idx.filter((i) => sc[i].sub).length, idx.length)), el("td", {}, accCell(idx.filter((i) => sc[i].outcome).length, idx.length)));
    })));

  const bins = [[0.9, 1.01, "0.90 فما فوق"], [0.75, 0.9, "0.75 – 0.90"], [0.6, 0.75, "0.60 – 0.75"], [0, 0.6, "أقل من 0.60"]];
  const calib = el("table", { class: "grid" }, el("thead", {}, el("tr", {}, ["ثقة النموذج بنفسه", "التذاكر", "كم وحدة صحيحة"].map((h) => el("th", { scope: "col", text: h })))),
    el("tbody", {}, bins.map(([lo, hi, label]) => {
      const idx = sc.filter((s) => s.conf != null && s.conf >= lo && s.conf < hi);
      return el("tr", {}, el("td", {}, ltr(label)), el("td", {}, num(idx.length)), el("td", {}, idx.length ? accCell(idx.filter((s) => s.firstSub).length, idx.length) : "—"));
    })));

  const body = el("tbody");
  rows.forEach((r, i) => {
    const s = sc[i], g = r.ticket;
    // One control per row: the id opens the trace (the row itself is not a tab stop).
    const open = el("button", { type: "button", class: "link-btn row-open", "aria-label": `افتح ${g.id} مرحلة بمرحلة`, onclick: () => openTicket(i) }, mono(g.id));
    const tr = el("tr", { class: "click" },
      el("td", { class: "nowrap" }, open),
      el("td", { text: DIFF_AR[g.difficulty] || "" }),
      el("td", { text: subLabel(g.subcategory) }),
      el("td", {}, s.sub ? el("span", { class: "mark-ok", text: "✓" }) : el("span", {}, el("span", { class: "mark-no", text: "✗ " }), subLabel(s.got))),
      el("td", {}, ltr(s.conf == null ? "—" : Math.abs(s.conf - s.gateConf) > 0.005 ? `${s.conf.toFixed(2)} → ${s.gateConf.toFixed(2)}` : s.conf.toFixed(2))),
      el("td", {}, s.recheck ? (s.agree ? "اتفق" : el("span", { class: "mark-no", text: "اختلف" })) : "—"),
      el("td", { class: "nowrap" }, el("span", { class: `pill ${r.result.outcome}`, text: OUTCOME_SHORT[r.result.outcome] }), s.outcome ? "" : el("span", { class: "mark-no", text: " ✗" })),
      el("td", {}, ltr(r.result.priority || "—"), s.priority ? "" : el("span", { class: "mark-no" }, " ✗ (", ltr(g.priority || "—"), ")")),
      el("td", { class: "nowrap" }, secs(r.seconds)));
    tr.addEventListener("click", (e) => { if (!e.target.closest("button")) openTicket(i); });
    add(body, tr);
  });
  // A table that can scroll sideways is reachable by keyboard (WCAG 2.1.1).
  const wrap = (label, table) => el("div", { class: "table-wrap", tabindex: "0", role: "region", "aria-label": label }, table);
  const all = wrap("كل التذاكر", el("table", { class: "grid" },
    el("thead", {}, el("tr", {}, ["#", "المستوى", "المتوقع", "النظام", "الثقة", "المراجعة", "النتيجة", "الأولوية", "الوقت"].map((h) => el("th", { scope: "col", text: h })))), body));

  const m = P.run.meta;
  const decisions = el("section", { class: "decisions-sum", "aria-labelledby": "decTitle" },
    el("h3", { id: "decTitle", class: "section-title", text: "شنو قرر الموظف على هالتشغيل" }), el("p", { class: "note", text: "يحمّل…" }));
  $("processMain").replaceChildren(el("section", { class: "overview", "aria-labelledby": "ovTitle" },
    el("h2", { id: "ovTitle", class: "trace-title", tabindex: "-1" }, "ملخص تشغيل ", ticketsAr(n)),
    el("p", { class: "lede" }, `${m.set} · `, ltr((m.started || "").replace("T", " ")), ` · ${backendAr(m.backend)} · `,
      ltr(`${m.models?.classifier} / ${m.models?.drafter}`), " · استغرق ", secs(m.wall_seconds || 0), " بالمجموع",
      m.usage?.budget_hit ? el("strong", { class: "mark-no", text: " · وصل حد الصرف: الأرقام مو صالحة" }) : ""),
    stageStrip(rows),
    stats,
    el("h3", { class: "section-title", text: "شنو صار بالتذاكر" }), bar, legend,
    el("h3", { class: "section-title", text: "حسب الصعوبة" }), wrap("حسب الصعوبة", diffTable),
    el("h3", { class: "section-title", text: "هل ثقة النموذج بمحلها؟" }),
    el("p", { class: "note", text: "كل صف يجمع التذاكر حسب الثقة اللي عطاها النموذج لنفسه، ويقارنها بكم وحدة طلعت صحيحة فعلاً. هذا أساس المعايرة." }), wrap("ثقة النموذج والصحة", calib),
    decisions,
    el("h3", { class: "section-title", text: "كل التذاكر" }),
    el("p", { class: "note", text: "اضغط على رقم أي تذكرة حتى تشوفها مرحلة بمرحلة." }), all));
  try {
    const recs = [...(await restoreDecisions(P.source.slice(4))).values()];
    decisions.replaceChildren(decisions.firstChild, decisionsSummary(recs));
  } catch {
    decisions.replaceChildren(decisions.firstChild, el("p", { class: "note", text: "ما كدرنا نقرا سجل القرارات." }));
  }
}

function decisionsSummary(recs) {
  if (!recs.length) return el("p", { class: "note", text: "ماكو قرارات على هالتشغيل بعد. افتحه بوضع الموظف وقرر على التذاكر، والأرقام تطلع هنا." });
  const s = summarize(recs);
  const med = median(s.seconds);
  const pct = (a, b) => (b ? `${Math.round((100 * a) / b)}%` : "—");
  const stat = (b, t) => el("div", { class: "stat" }, el("b", {}, typeof b === "string" ? ltr(b) : b), el("span", { text: t }));
  return el("div", {},
    el("div", { class: "stats" },
      stat(String(s.n), "تذكرة انحسمت"), stat(pct(s.approved, s.drafts), "مسودات انعتمدت كما هي"),
      stat(pct(s.edited, s.drafts), "مسودات انعدّلت"), stat(String(s.took_over), "استلمها الموظف"),
      stat(String(s.forwarded), "تحوّلت للقسم"), stat(med == null ? "—" : secs(med), "الوقت الوسيط لكل تذكرة"),
      stat(String(s.corrected), "تصحيح للنوع أو القسم أو الأولوية"),
      // Faster than reading the ticket and the draft: not an opinion on the draft.
      stat(String(s.quick), `قرار أسرع من ${QUICK_S} ثواني (ما ينحسب رأي)`)),
    s.reasons.length ? el("ul", { class: "reason-counts" }, s.reasons.map(([c, k]) => el("li", {}, el("span", { text: S.meta.reason_codes_ar[c] || c }), num(k))))
      : el("p", { class: "note", text: "ماكو أسباب مختارة." }),
    el("p", { class: "note", text: "من سجل القرارات (بدون نص الرد): آخر قرار لكل تذكرة ما انلغى." }));
}

/** From the agent mode: show this run's ticket here. A run-all going on over a ticket set stops first:
 *  the view is leaving that set, and its next tickets would cost calls nobody is watching. */
export async function focusRunTicket(runName, id) {
  clearTimers();
  if (P.ctl) {
    P.runAll = false;
    P.ctl.abort();
    showToast("وقّفنا تشغيل القائمة حتى نفتح التذكرة.");
  }
  if (P.source !== `run:${runName}`) {
    P.source = `run:${runName}`;
    const sel = $("pSource");
    if (sel) sel.value = P.source;
  }
  await renderProcess();
  openRunTicket(id);
}

