// The draft composer: an editable draft with the draft-check findings highlighted in place (a mirror
// behind a transparent textarea, so the highlight follows the real line breaks in right-to-left text),
// and the findings listed under it. Edits are re-checked with POST /api/check (debounced, stale calls
// aborted, only the latest answer used). Findings count only for the exact text they were computed on:
// an approval re-checks anything newer.

import { checkDraft, ServerError } from "./api.js";
import { CHECK_SHORT_AR } from "./labels.js";
import { S, draftDone, extractionOf, uid } from "./state.js";
import { cpToUtf16, debounce, el, icon, realDraft, shownDraft, spanned, withTip } from "./util.js";

/** The draft and its findings as saved by the pipeline (spans from 1 Nov, or recomputed by the server). */
export function originalDraft(item) {
  const d = draftDone(item) || {};
  const text = item.result?.draft_ar ?? d.reply ?? "";
  const findings = d.check_spans ?? item.result?.draft_checks ?? [];
  const recomputed = !!(d.check_spans_recomputed || item.result?.draft_checks_recomputed);
  return { text, findings, recomputed, allowed: d.user_prompt ?? "", subcategory: extractionOf(item)?.subcategory || null };
}

export function isBlocking(kind) {
  return (S.meta.blocking_checks || []).includes(kind);
}

/**
 * build(item, onUpdate) → {node, textarea, state(), checkNow(), lock(on), caretRect()}
 * state(): {text, edited, findings, check: "ok" | "pending" | "error", error, current}
 *   findings: the last answer; current: it was computed on exactly this text (an approval needs that).
 */
export function buildComposer(item, onUpdate) {
  const orig = originalDraft(item);
  const key = uid(item);
  let text = S.edits.get(key) ?? orig.text;
  let findings = orig.findings;
  let checkedText = orig.text;   // the text `findings` belong to
  let check = "ok", error = null, seq = 0, ctl = null;

  const labelText = el("span", { class: "composer-label-text" });
  const label = el("label", { class: "composer-label", for: "draft" }, labelText);
  const restore = el("button", { type: "button", class: "link-btn", text: "رجّع المسودة الأصلية", hidden: true });
  const mirror = el("div", { class: "composer-mirror", "aria-hidden": "true" });
  // Each paragraph takes the direction of its own first letter (the stylesheet's unicode-bidi: plaintext,
  // on the mirror too), so a line in English reads left to right with its full stop at its end.
  const ta = el("textarea", {
    id: "draft", class: "composer-input", dir: "rtl", lang: "ar", spellcheck: "false", autocomplete: "off",
    "aria-describedby": "draftChecks", rows: "4",
  });
  // Shown with a no-break space between digit groups, so «0791 079 0226» reads as written (util.js).
  ta.value = shownDraft(text);
  const field = el("div", { class: "composer-field" }, mirror, ta);
  // Ctrl+Enter from inside the draft and Esc out of it are on the approve button and in the «?» sheet.
  const list = el("div", { id: "draftChecks", class: "checks", "aria-live": "off" });

  const node = el("section", { class: "composer", "aria-labelledby": "draftLabel" },
    el("div", { class: "composer-head" }, el("span", { id: "draftLabel" }, label), restore),
    field, list);

  function fit() {
    ta.style.height = "auto";
    ta.style.height = `${ta.scrollHeight + 2}px`;
  }

  const current = () => check === "ok" && checkedText === text;

  function spans() {
    if (checkedText !== text) return [];   // offsets of an older text would land on the wrong words
    const all = findings.map((f, i) => {
      const r = cpToUtf16(text, f.start, f.end);
      const block = isBlocking(f.kind);
      return r && { start: r[0], end: r[1], block, make: (s) => el("mark", { class: `finding ${block ? "is-blocking" : "is-warn"}`, dataset: { finding: String(i) }, text: s }) };
    }).filter(Boolean);
    // Where a warning and a blocking finding overlap (a card number is also an unknown number), the phrase
    // that stops the approval is the one drawn, whole.
    const blocks = all.filter((x) => x.block);
    return all.filter((x) => x.block || !blocks.some((b) => x.start < b.end && b.start < x.end));
  }

  function drawMirror() {
    // The mirror shows exactly what the textarea shows (same characters, same line breaks).
    mirror.replaceChildren(spanned(ta.value, spans()), "​\n");   // the trailing line keeps the heights equal
  }

  function light(i, on) {
    mirror.querySelectorAll(`[data-finding="${i}"]`).forEach((n) => n.classList.toggle("is-hot", on));
  }

  function drawList() {
    const edited = text !== orig.text;
    labelText.textContent = edited ? "معدّلة منك" : "مسودة مقترحة";
    node.classList.toggle("is-edited", edited);
    restore.hidden = !edited;
    const items = [];
    if (check === "pending") items.push(el("p", { class: "checks-state", text: "يفحص التعديل…" }));
    if (check === "error") items.push(el("p", { class: "checks-state is-bad" }, error || "ما كدرنا نفحص التعديل.", " ",
      el("button", { type: "button", class: "link-btn", text: "جرب مرة ثانية", onclick: () => checkNow() })));
    if (findings.length) {   // while a newer check runs, the last answer stays listed (not highlighted)
      items.push(el("ul", { class: "checks-list", "aria-label": "فحص المسودة" }, findings.map((f, i) => {
        const block = isBlocking(f.kind);
        const r = cpToUtf16(text, f.start, f.end);
        const b = el("button", { type: "button", class: `check-item ${block ? "is-blocking" : "is-warn"}` },
          icon(block ? "lock" : "check"),
          el("span", { class: "check-tag", text: block ? "يمنع الاعتماد" : "انتبه" }),
          el("span", { class: "check-why", text: S.meta.check_ar?.[f.kind] || f.kind }),
          el("span", { class: "check-text", dir: "rtl", text: `«${f.text}»` }));
        b.addEventListener("mouseenter", () => light(i, true));
        b.addEventListener("mouseleave", () => light(i, false));
        b.addEventListener("focus", () => light(i, true));
        b.addEventListener("blur", () => light(i, false));
        b.addEventListener("click", () => { if (r && checkedText === text) { ta.focus(); ta.setSelectionRange(r[0], r[1]); } });
        return el("li", {}, b);
      })));
    } else if (current()) {
      // All clear: a few muted words; what was checked is in their tip (hover, focus, or a tap that pins it).
      const ran = (S.meta.checks_active || []).map((k) => CHECK_SHORT_AR[k] || k);
      const ok = el("button", { type: "button", class: "checks-ok" }, icon("ready"), "ما بيها مشكلة");
      items.push(withTip(ok, `فحصنا المسودة وما لكينا: ${ran.join("، ")}`, { id: "checksTip", tag: "p", cls: "checks-clean" }));
    }
    list.replaceChildren(...items);
  }

  function draw() {
    drawMirror();
    drawList();
    onUpdate?.();
  }

  async function run() {
    const mine = ++seq;
    ctl?.abort();
    ctl = new AbortController();
    const sent = text;
    const body = { draft: sent, allowed_text: orig.allowed, subcategory: orig.subcategory };
    try {
      const got = await checkDraft(body, ctl.signal);
      if (mine !== seq || sent !== text) return;   // the text changed meanwhile: a newer check follows
      findings = got;
      checkedText = sent;
      check = "ok";
      error = null;
    } catch (e) {
      if (e?.name === "AbortError" || mine !== seq) return;
      check = "error";
      error = e instanceof ServerError ? e.message : "انقطع الاتصال، فما انفحص التعديل.";
    }
    draw();
  }
  const later = debounce(() => { run(); }, 400);

  function changed(e) {
    // Typed or pasted text is shown like the draft was: a no-break space between digit groups, a
    // non-breaking hyphen in a reference. One character for one, so the caret stays where it was. Not
    // while an input method is composing (it would break the word being composed).
    if (!e?.isComposing && shownDraft(ta.value) !== ta.value) {
      const [from, to, way] = [ta.selectionStart, ta.selectionEnd, ta.selectionDirection];
      ta.value = shownDraft(ta.value);
      ta.setSelectionRange(from, to, way);
    }
    const shown = ta.value;
    text = shown === shownDraft(orig.text) ? orig.text : realDraft(shown);
    // Any edit makes every check in flight stale: a late answer is for an older text.
    seq++;
    ctl?.abort();
    if (text === orig.text) {
      S.edits.delete(key);
      later.cancel();
      findings = orig.findings;
      checkedText = orig.text;
      check = "ok";
      error = null;
    } else {
      S.edits.set(key, text);
      check = "pending";
      later();
    }
    fit();
    draw();
  }

  /** Check the current text now (before an approval); resolves once the findings belong to it. */
  async function checkNow() {
    for (let i = 0; i < 3 && !current(); i++) {
      later.cancel();
      check = "pending";
      drawList();
      await run();
      if (check === "error") return;
    }
  }

  /** The caret's place on screen (from the mirror, which has the same layout), to keep it in view. */
  function caretRect() {
    const at = Math.min(ta.selectionEnd ?? 0, ta.value.length);
    const walker = document.createTreeWalker(mirror, NodeFilter.SHOW_TEXT);
    let n, left = at;
    while ((n = walker.nextNode())) {
      if (left <= n.data.length) {
        const r = document.createRange();
        r.setStart(n, left);
        r.setEnd(n, left);
        const rect = r.getClientRects()[0] || r.getBoundingClientRect();
        return rect && rect.height ? rect : null;
      }
      left -= n.data.length;
    }
    return null;
  }

  ta.addEventListener("input", changed);
  ta.addEventListener("compositionend", changed);
  restore.addEventListener("click", () => { ta.value = shownDraft(orig.text); changed(); ta.focus(); });
  requestAnimationFrame(fit);
  window.addEventListener("resize", fit, { passive: true });

  if (text !== orig.text) { check = "pending"; later(); }
  drawMirror();
  drawList();

  return {
    node, textarea: ta,
    state: () => ({ text, edited: text !== orig.text, findings, check, error, original: orig, current: current() }),
    checkNow,
    caretRect,
    /** While a decision is being saved the text can't change under it. */
    lock: (on) => { ta.readOnly = on; },
    dispose: () => { later.cancel(); ctl?.abort(); window.removeEventListener("resize", fit); },
  };
}
