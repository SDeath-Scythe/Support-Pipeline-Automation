// The page's state: what is loaded, what the agent decided, and what they are editing. Edits, ticks and
// corrections live in memory only (never in localStorage); decisions go to the server's log.
//
// Two runs can hold the same ticket id (t2-0009 is in the final run and in an experiment), so everything
// the agent did to a ticket is kept by uid(item) = run + id, never by the id alone.

import { getJSON, postJSON } from "./api.js";
import { PRIORITY_RANK } from "./labels.js";

export const S = {
  meta: null,
  prefs: null,
  runs: [],
  sets: [],
  mode: "agent",
  agent: { source: null, run: null, items: [], loading: false, error: null, tab: null, openKey: null },
  live: [],             // tickets pasted in this page (run "live"), newest first
  liveSeq: 0,           // the order of live rows (their ids come from the server)
  liveBusy: false,      // the server runs one live ticket at a time
  liveBlocked: null,    // Arabic reason once the spending cap was reached
  decisions: new Map(), // ticket key → the decision that stands (not undone), for the run on screen and live
  session: [],          // decisions made in this page, newest last: the undo stack ({id, key, run})
  edits: new Map(),     // uid → the draft text as the agent left it (kept after a decision, so undo brings it back)
  acks: new Map(),      // uid → what the agent ticked "تأكدت" for
  reasons: new Map(),   // uid → Set of reason codes
  corrections: new Map(), // uid → {subcategory, team, priority} the agent chose
  time: new Map(),      // uid → {ms, since, visits}: how long the ticket was on screen, over every visit
  finalText: new Map(), // uid → the reply as decided in this page (shown on the done ticket)
  timing: null,         // the uid whose clock is running
};

/** The key for everything the agent did to one ticket of one run. */
export const uid = (item) => `${item.run}\u0000${item.key}`;

// --- one ticket's data ---

/** The last finished event of a stage (not "running"). */
export function ev(item, stage) {
  const list = item.events || [];
  for (let i = list.length - 1; i >= 0; i--) if (list[i].stage === stage && list[i].status !== "running") return list[i];
  return null;
}
export function draftDone(item) {
  const e = ev(item, "draft");
  return e && e.status === "done" ? e.data : null;
}
export function errorEvent(item) {
  return (item.events || []).find((e) => e.status === "error") || null;
}
export function outcomeOf(item) {
  if (item.result) return item.result.outcome;
  if (item.status === "lost" || item.status === "cancelled") return "escalated";
  return null;
}
export function tabOf(item) {
  if (S.decisions.has(item.key)) return "done";
  if (item.status === "running") return "running";
  return outcomeOf(item) || "escalated";
}
export function flagsOf(item) {
  const f = item.result?.flags || [];
  if (item.status === "lost") return ["connection_lost"];
  if (item.status === "cancelled") return ["cancelled"];
  return f;
}
/** What the pipeline read from the ticket. A result without it (the drafter failed after the type was
 *  known) falls back to the classify or re-check step that produced it. */
export function extractionOf(item) {
  if (item.result?.extraction) return item.result.extraction;
  const usedSecond = (item.result?.flags || []).includes("recheck_used_second");
  const step = (usedSecond && ev(item, "recheck")) || ev(item, "classify");
  return step?.status === "done" ? step.data?.extraction || null : null;
}
export const subOf = (item) => extractionOf(item)?.subcategory || null;

/** The team and priority an issue type gets (route.py): the type's team and default priority, raised
 *  one level for a large amount. */
export function routeFor(sub, extraction) {
  const s = S.meta.subcategories[sub];
  if (!s || !sub) return { team: null, priority: null };
  let p = s.default_priority;
  const rules = S.meta.priority_rules || {};
  const big = (extraction?.amount_iqd != null && extraction.amount_iqd >= rules.large_amount_iqd)
    || (extraction?.amount_usd != null && extraction.amount_usd >= rules.large_amount_usd);
  if (big && p !== "P1") p = `P${Number(p.slice(1)) - 1}`;
  return { team: s.team, priority: p };
}

/** Type, team and priority as the agent now sees them (their corrections over the pipeline's). */
export function effective(item) {
  const c = S.corrections.get(uid(item)) || {};
  return {
    subcategory: c.subcategory || subOf(item),
    team: c.team || item.result?.team || null,
    priority: c.priority || item.result?.priority || null,
  };
}
/** Only the fields that differ from what the pipeline decided (POST /api/decision "corrected"). */
export function correctedFor(item) {
  const c = S.corrections.get(uid(item)) || {};
  const out = {};
  if (c.subcategory && c.subcategory !== subOf(item)) out.subcategory = c.subcategory;
  if (c.team && c.team !== item.result?.team) out.team = c.team;
  if (c.priority && c.priority !== item.result?.priority) out.priority = c.priority;
  return out;
}

// --- the queue ---

export function allItems() {
  return [...S.live, ...S.agent.items];
}
export function findItem(key) {
  return allItems().find((it) => it.key === key) || null;
}
// No priority (the system never read the ticket: switched off, too long, an error) sorts first: it
// could be anything, so a person should look at it before the known P1s.
const rank = (it) => PRIORITY_RANK[effective(it).priority] ?? 0;
/** Priority first (none, then P1, P2, P3), then queue order; tickets pasted here come first. */
export function sortItems(list) {
  return [...list].sort((a, b) => rank(a) - rank(b) || a.order - b.order);
}
export const priorityRank = rank;

/** Whether the agent's own answer (a correction) makes this ticket one that is never drafted (fraud):
 *  then it is handled like an escalation, whatever the pipeline decided. */
export function escalatesNow(item) {
  if (outcomeOf(item) === "escalated") return true;
  const sub = effective(item).subcategory;
  return !!(sub && S.meta.subcategories[sub]?.always_escalate);
}

// The working tabs, in the order a tie in priority is broken: escalations first (forwarding one is quick
// and the receiving team waits for it), then the drafts that need a check, then the ready ones.
const WORK_TABS = ["escalated", "flagged", "drafted"];
/** The most urgent open ticket: priority first, then (on a tie) the tab given, then the tab order above,
 *  then the queue order. */
export function mostUrgent(preferTab = null) {
  const key = (it) => [rank(it), tabOf(it) === preferTab ? 0 : 1, WORK_TABS.indexOf(tabOf(it)), it.order];
  const cmp = (a, b) => { const x = key(a), y = key(b); for (let i = 0; i < x.length; i++) if (x[i] !== y[i]) return x[i] - y[i]; return 0; };
  return openItems().filter((it) => WORK_TABS.includes(tabOf(it))).sort(cmp)[0] || null;
}
export function itemsInTab(tab) {
  const list = allItems();
  if (tab === "done") {   // newest decision first
    return list.filter((it) => S.decisions.has(it.key))
      .sort((a, b) => (S.decisions.get(b.key).ts || "").localeCompare(S.decisions.get(a.key).ts || ""));
  }
  return sortItems(list.filter((it) => tabOf(it) === tab));
}
export function runningItems() {
  return S.live.filter((it) => it.status === "running" && !S.decisions.has(it.key));
}
export function openItems() {
  return allItems().filter((it) => !S.decisions.has(it.key) && it.status !== "running");
}

// --- decisions ---

/** The decision that stands for each ticket: the latest one that was not undone. */
export function standing(records) {
  const undone = new Set(records.filter((d) => d.action === "undone").map((d) => d.undoes));
  const out = new Map();
  for (const d of records) {
    if (d.action === "undone" || undone.has(d.id)) continue;
    out.set(d.ticket_id, d);
  }
  return out;
}

export async function restoreDecisions(runName) {
  const { decisions } = await getJSON(`/api/decisions?run=${encodeURIComponent(runName)}`);
  return standing(decisions || []);
}

const FLAG_OK = /^[A-Za-z0-9_.:-]{1,64}$/;

// --- time on a ticket: added up over every visit, paused while another ticket, the other mode or another
// browser tab is in front, and never counting the pipeline's own processing time ---

function clockOf(u) {
  if (!S.time.has(u)) S.time.set(u, { ms: 0, since: null, visits: 0 });
  return S.time.get(u);
}
/** Stop the running clock (another ticket opened, the page hidden, the mode switched). */
export function pauseClock() {
  if (!S.timing) return;
  const c = clockOf(S.timing);
  if (c.since != null) c.ms += performance.now() - c.since;
  c.since = null;
  S.timing = null;
}
/** Start the clock of the ticket on screen. visit: a new visit (not a return from a hidden tab). */
export function startClock(item, { visit = true } = {}) {
  pauseClock();
  if (!item || item.status === "running" || S.decisions.has(item.key)) return;
  const u = uid(item);
  const c = clockOf(u);
  c.since = performance.now();
  if (visit || !c.visits) c.visits++;
  S.timing = u;
}
/** {seconds, visits} spent on a ticket so far. */
export function timeOn(item) {
  const c = S.time.get(uid(item));
  if (!c) return { seconds: 0, visits: 1 };
  const ms = c.ms + (c.since != null ? performance.now() - c.since : 0);
  return { seconds: Math.min(36000, Math.max(0, Math.round(ms / 100) / 10)), visits: Math.max(1, c.visits) };
}

/** Record a decision. Returns the stored record (with its id). */
export async function decide(item, action, extra = {}) {
  const { seconds, visits } = timeOn(item);
  const body = {
    run: item.run,
    ticket_id: item.key,
    action,
    pipeline_outcome: outcomeOf(item) || "escalated",
    flags: flagsOf(item).filter((f) => FLAG_OK.test(f)).slice(0, 32),
    reason_codes: [...(S.reasons.get(uid(item)) || [])],
    seconds,
    visits,
    warnings_acknowledged: extra.acknowledged || [],
    draft_text: extra.draft_text ?? null,
    final_text: extra.final_text ?? null,
    corrected: correctedFor(item),
  };
  const { id } = await postJSON("/api/decision", body);
  pauseClock();
  const record = {
    ...body, id, ts: new Date().toISOString(), draft_text: undefined, final_text: undefined,
    edit_chars: extra.edit_chars ?? null,
  };
  S.decisions.set(item.key, record);
  S.session.push({ id, key: item.key, run: item.run });
  if (extra.final_text != null) S.finalText.set(uid(item), extra.final_text);
  return record;
}

/** Take back a decision: the ticket returns to its tab, with the agent's edit, reasons and corrections
 *  as they were. `entry` ({id, key, run}) names the exact decision: when the ticket on screen belongs to
 *  another run, or its standing decision is another one, nothing is undone (returns null). */
export async function undo(key, entry = null) {
  const d = S.decisions.get(key);
  const item = findItem(key);
  if (!d || !item) return null;
  if (entry && (entry.run !== item.run || entry.id !== d.id)) return null;
  await postJSON("/api/decision", {
    run: item.run, ticket_id: key, action: "undone", pipeline_outcome: d.pipeline_outcome,
    flags: d.flags || [], reason_codes: [], seconds: 0, corrected: {}, undoes: d.id,
  });
  S.decisions.delete(key);
  S.finalText.delete(uid(item));
  S.session = S.session.filter((s) => s.id !== d.id);
  return item;
}

/** Re-read the decisions of the run on screen (another tab decided a ticket: the server said 409). */
export async function refreshDecisions() {
  const name = S.agent.source;
  if (!name) return;
  const decided = await restoreDecisions(name);
  if (S.agent.source !== name) return;
  for (const it of S.agent.items) {
    if (decided.has(it.key)) S.decisions.set(it.key, decided.get(it.key));
    else S.decisions.delete(it.key);
  }
}

export const QUICK_S = 3;

/** What the agent did over a set of decisions: the human-feedback numbers. */
export function summarize(records) {
  const list = [...records];
  const count = (a) => list.filter((d) => d.action === a).length;
  const reasons = new Map();
  for (const d of list) for (const c of d.reason_codes || []) reasons.set(c, (reasons.get(c) || 0) + 1);
  const withDraft = list.filter((d) => d.pipeline_outcome !== "escalated");
  return {
    n: list.length,
    approved: count("approved"),
    edited: count("edited"),
    took_over: count("took_over"),
    forwarded: count("forwarded"),
    drafts: withDraft.length,
    keptUnchanged: withDraft.filter((d) => d.action === "approved").length,
    reasons: [...reasons.entries()].sort((a, b) => b[1] - a[1]),
    seconds: list.map((d) => d.seconds),
    // Faster than a person can read a ticket and its draft: counted apart, never read as an opinion.
    quick: list.filter((d) => typeof d.seconds === "number" && d.seconds < QUICK_S).length,
    corrected: list.filter((d) => d.corrected && Object.keys(d.corrected).length).length,
  };
}
