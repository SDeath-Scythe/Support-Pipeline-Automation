// Running a pasted ticket through the pipeline, live. The server runs one at a time and stops calling
// models once the page goes away; this side aborts the stream when the agent cancels or leaves.

import { NetworkError, ServerError, openStream, readEvents } from "./api.js";
import { LIVE_TURN_ON_AR } from "./labels.js";
import { S } from "./state.js";
import { el, fmtInt, num, openDialog, richText, stampOwn } from "./util.js";

const hooks = { started: null, updated: null, budget: null };
export function setLiveHooks(h) { Object.assign(hooks, h); }

const controllers = new Set();
const BUSY_AR = "اكو تذكرة دتنعالج هسه، انتظر لما تخلص.";
/** Said whenever a pasted ticket goes to a model (not with the system off, or replaying the cache). */
const ABROAD_AR = "النص ينرسل لمزوّد نموذج خارجي برا العراق، فالصق بس التذاكر المسموح بإرسالها.";
const LIVE_ID = /^live-\d{14}-[0-9a-f]{6}$/;
/** LLM_CACHE_ONLY=1 (the author's demo): what a pasted ticket gets. Said in a banner and in the dialog. */
export const CACHE_AR = "التذكرة تاخذ أجوبة النموذج المحفوظة من قبل، بدون أي استدعاء، فالمراحل تخلص بلحظة. تذكرة ما إلها أجوبة محفوظة تروح لموظف.";
addEventListener("pagehide", () => {
  for (const c of controllers) c.abort();
  // Pasted customer text is never kept by the page: not in the history entry either.
  const ta = document.getElementById("newText");
  if (ta) ta.value = "";
});

/** Whether a new ticket can run, and if not, why (Arabic). With PIPELINE_MODE=off a run calls no
 *  model (every ticket goes to a person), so it stays allowed: it shows the kill switch working. */
export function liveState() {
  if (S.liveBlocked) return { ok: false, reason: S.liveBlocked };
  if (S.meta.live.available || S.meta.mode === "off") return { ok: true, reason: null };
  return { ok: false, reason: S.meta.live.reason_ar || "التشغيل المباشر مو متاح." };
}

/**
 * Stream one ticket. Throws ServerError / NetworkError if the server refused it before streaming.
 * Resolves to "done" (a result arrived), "lost" (the stream broke) or "cancelled" (aborted here).
 */
export async function streamTicket(text, { onEvent, signal }) {
  const resp = await openStream(text, signal);
  let got = false;
  try {
    await readEvents(resp, (e) => {
      if (e.live_id) return;   // the server's id for the run: a set's ticket keeps its own
      if (e.stage === "result") got = true;
      if (e.status === "error" && e.data?.kind === "BudgetExceeded") {
        S.liveBlocked = e.data.error || "وصل التشغيل لحد الصرف.";
        hooks.budget?.(S.liveBlocked);
      }
      onEvent(e);
    });
    return got ? "done" : "lost";
  } catch (e) {
    if (e?.name === "AbortError") return got ? "done" : "cancelled";
    if (e instanceof NetworkError) return got ? "done" : "lost";
    throw e;
  }
}

export function cancelLive(item) {
  item.ctl?.abort();
}

// --- the new-ticket dialog ---

export function initNewTicket() {
  const dlg = document.getElementById("newDialog");
  const ta = document.getElementById("newText");
  const count = document.getElementById("newCount");
  const err = document.getElementById("newError");
  const run = document.getElementById("newRun");
  const note = document.getElementById("newNote");

  const update = () => {
    const max = S.meta.limits.max_ticket_chars;
    const n = ta.value.trim().length;
    count.replaceChildren(num(fmtInt(n)), " من ", num(fmtInt(max)), " حرف");
    count.classList.toggle("is-over", n > max);
  };
  ta.addEventListener("input", () => { err.textContent = ""; update(); });
  // Ctrl/Cmd+Enter runs it, as it approves a draft in the inbox (keyboard.js leaves a dialog's keys to it).
  const form = document.getElementById("newForm");
  ta.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && !e.altKey && e.key === "Enter" && !e.isComposing) { e.preventDefault(); form.requestSubmit(); }
  });

  // Closed without running (رجوع, Escape): the pasted text goes. A refused run keeps it while the
  // dialog stays open, so the agent can fix it.
  dlg.addEventListener("close", () => { ta.value = ""; err.textContent = ""; });
  document.getElementById("newCancel").addEventListener("click", () => dlg.close());
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (run.getAttribute("aria-disabled") === "true") return;   // already sending this one
    const text = ta.value.trim();
    const max = S.meta.limits.max_ticket_chars;
    const st = liveState();
    if (!st.ok) { err.textContent = st.reason; return; }
    if (!text) { err.textContent = "اكتب نص التذكرة أول."; ta.focus(); return; }
    if (text.length > max) { err.textContent = `التذكرة أطول من الحد المسموح (${fmtInt(max)} حرف).`; ta.focus(); return; }
    if (S.liveBusy) { err.textContent = BUSY_AR; return; }
    run.setAttribute("aria-disabled", "true");
    // A refusal (413, 429, 403, 400) keeps the dialog open with the server's Arabic message. Once the
    // server took it, the button is free again (the run goes on in the queue).
    try {
      await probeAndRun(text, () => { ta.value = ""; update(); dlg.close(); run.removeAttribute("aria-disabled"); });
    } catch (ex) {
      err.textContent = ex instanceof ServerError ? ex.message : ex instanceof NetworkError ? "انقطع الاتصال بالخادم: تأكد إنه شغّال." : "ما انشغلت التذكرة.";
    } finally {
      run.removeAttribute("aria-disabled");
    }
  });

  const field = [document.querySelector('label[for="newText"]'), ta, count];
  return function openNew() {
    const st = liveState();
    err.textContent = "";
    note.replaceChildren();
    if (!st.ok) {
      // The agent's sentence, then what turns it on (for whoever runs the server; not after a spent budget).
      const turnOn = S.liveBlocked ? null : LIVE_TURN_ON_AR[S.meta.live.cause];
      note.append(el("strong", { text: st.reason }), ...(turnOn ? [el("br"), richText(turnOn)] : []));
    } else if (S.liveBusy) note.append(el("strong", { text: BUSY_AR }));
    else if (S.meta.mode === "off") note.append(el("strong", { text: "النظام موقف: " }), "التذكرة ما تنرسل لأي نموذج، وتروح لموظف مباشرة.");
    else if (S.meta.mode === "classify_only") note.append(el("strong", { text: "المسودات موقفة: " }), "النظام يصنّفها ويوجّهها بس، والرد عليك.", el("br"), ABROAD_AR);
    else if (S.meta.cache_only) note.append(el("strong", { text: "إعادة من الكاش: " }), CACHE_AR);
    else note.append("التذكرة تمر بالمراحل كلها وتطلع بالقائمة. ", el("strong", { text: "التذاكر الجديدة ما تنحفظ: " }), "إذا حدّثت الصفحة تروح.", el("br"), ABROAD_AR);
    note.classList.toggle("hint-warn", !st.ok);
    run.toggleAttribute("disabled", !st.ok);
    // Nothing can run: no box that looks ready for typing but takes none.
    for (const n of field) n.hidden = !st.ok;
    ta.readOnly = !st.ok;
    update();
    // Nothing can run: focus «رجوع», not a box that looks ready for typing but takes none.
    openDialog(dlg, st.ok ? ta : document.getElementById("newCancel"));
  };
}

/** Start the stream first, so a refusal is shown in the dialog; then add the row under the id the server
 *  gave the run (its first event: live-<UTC time>-<6 hex>, the decision log's ticket id) and read the rest. */
async function probeAndRun(text, accepted) {
  const ctl = new AbortController();
  const resp = await openStream(text, ctl.signal);   // throws on a refusal
  controllers.add(ctl);
  let item = null;
  const start = (key) => {
    if (!LIVE_ID.test(key || "")) throw new NetworkError("no run id");
    accepted();
    S.liveSeq++;
    item = { key, run: "live", live: true, order: -S.liveSeq, ticket: { id: key, text }, events: [], result: null, status: "running", ctl };
    S.live.unshift(item);
    S.liveBusy = true;
    hooks.started?.(item);
  };
  let got = false;
  try {
    await readEvents(resp, (e) => {
      if (!item) return start(e.live_id);
      item.events.push(stampOwn(item.events.at(-1), e));
      if (e.stage === "result") { item.result = e.data; got = true; }
      if (e.status === "error" && e.data?.kind === "BudgetExceeded") {
        S.liveBlocked = e.data.error || "وصل التشغيل لحد الصرف.";
        hooks.budget?.(S.liveBlocked);
      }
      hooks.updated?.(item);
    });
    if (!item) throw new NetworkError("no run id");
    item.status = got ? "done" : "lost";
  } catch (e) {
    if (!item) { ctl.abort(); throw e; }   // nothing on screen yet: the dialog says it
    item.status = got ? "done" : e?.name === "AbortError" ? "cancelled" : "lost";
  } finally {
    controllers.delete(ctl);
    if (item) {
      S.liveBusy = false;
      hooks.updated?.(item);
    }
  }
}

/** Run an existing live ticket again (after a lost connection or a cancel). */
export async function rerun(item) {
  if (S.liveBusy) throw new ServerError(429, BUSY_AR);
  await probeAndRun(item.ticket.text, () => {});
}
