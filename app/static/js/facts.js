// The details the pipeline pulled out of a ticket (reference, amount, phone, time), each paired with the
// place it was written in the customer's text. Matching reads Arabic-Indic digits as Western digits and
// skips the separators people type («٤٤٧١-٩٠٣٢», «2,000,000»), so the underline sits on what they wrote.

import { SECRET_MASK } from "./labels.js";
import { digitRuns, el, fmtInt, mono, num, spanned, westernDigits, withTip } from "./util.js";

const SEP = "[\\s\\-_/.,٫٬،]*";   // spaces, - _ / . , and the Arabic separators
const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

function firstMatch(text, re) {
  const m = re.exec(westernDigits(text));   // one character for one: offsets are the original text's
  return m ? { start: m.index, end: m.index + m[0].length } : null;
}

/** A reference or a phone, wherever it is split by spaces or dashes. */
export function findLoose(text, value) {
  const chars = [...westernDigits(value)].filter((c) => /[0-9A-Za-z]/.test(c));
  if (chars.length < 3) return null;
  return firstMatch(text, new RegExp(`(?<![0-9A-Za-z])${chars.map(esc).join(SEP)}(?![0-9A-Za-z])`, "i"));
}

// --- a card number or a code the customer wrote (result.secret_spans), hidden until the agent asks ---

/** The ranges of result.secret_spans ([start, end] in UTF-16 units of the message as shown) that fit `text`.
 *  Ranges that do not fit are dropped. */
export function fitSpans(spans, text) {
  return Array.isArray(spans) ? spans.filter((x) => Array.isArray(x) && Number.isInteger(x[0]) && Number.isInteger(x[1])
    && x[0] >= 0 && x[0] < x[1] && x[1] <= text.length) : [];
}

/** «••••» in place of a hidden number, read as «رقم مخفي» by a screen reader. */
export const secretMask = () => el("span", { class: "secret-mask" },
  el("span", { "aria-hidden": "true", text: SECRET_MASK }), el("span", { class: "sr-only", text: "رقم مخفي" }));

/** Every place in `text` where one of the hidden numbers (`digits`: each a string of Western digits) is
 *  written again, however its digits are split or written (the cleaned text, a model's answer, a prompt). */
export function secretRanges(text, digits) {
  const out = [];
  const plain = westernDigits(text);   // one character for one: offsets are the original text's
  for (const d of digits) {
    if (!d) continue;
    for (const m of plain.matchAll(new RegExp(`(?<![0-9])${[...d].join(SEP)}(?![0-9])`, "g"))) out.push([m.index, m.index + m[0].length]);
  }
  return out;
}

/** An amount written as digits (2,000,000), or as «12 الف», «2 مليون» or «5 ورقة» (100-dollar notes). */
export function findAmount(text, n, currency) {
  if (!Number.isInteger(n) || n <= 0) return null;
  const tries = [`(?<![0-9])${[...String(n)].join("[,.\\s٫٬]?")}(?![0-9])`];
  if (currency === "iqd" && n % 1_000_000 === 0) tries.push(`(?<![0-9])${n / 1_000_000}\\s*(?:مليون|ملايين)`);
  if (currency === "iqd" && n % 1000 === 0) tries.push(`(?<![0-9])${n / 1000}\\s*(?:ألف|الف|آلاف|الاف|ألاف)`);
  if (currency === "usd" && n % 100 === 0) tries.push(`(?<![0-9])${n / 100}\\s*(?:ورقة|ورقه|اوراق|أوراق)`);
  for (const t of tries) {
    const hit = firstMatch(text, new RegExp(t));
    if (hit) return hit;
  }
  return null;
}

/** A time as the model copied it («قبل يومين», «من البارحة»). */
export function findLiteral(text, value) {
  const v = westernDigits(String(value || "")).trim();
  if (!v) return null;
  const i = westernDigits(text).indexOf(v);
  return i < 0 ? null : { start: i, end: i + v.length };
}

/** The parts of a time with no Latin letter, joined; null when none is left. */
export function arabicDate(value) {
  if (!value) return null;
  const kept = String(value).split(/[;؛()]/).map((p) => p.trim().replace(/^[ ,،-]+|[ ,،-]+$/g, "")).filter((p) => p && !/[A-Za-z]/.test(p));
  return kept.join(" ") || null;
}

/** The facts of a ticket's extraction, each with a label, a display node and its place in `text`. */
export function factsOf(extraction, text, subcategory) {
  const ex = extraction || {};
  const out = [];
  if (ex.reference) out.push({ label: "رقم العملية", value: () => mono(ex.reference), at: findLoose(text, ex.reference), ltr: true });
  if (ex.amount_iqd != null) {
    out.push({ label: "المبلغ", value: () => [num(fmtInt(ex.amount_iqd)), " دينار"], at: findAmount(text, ex.amount_iqd, "iqd") });
  } else if (ex.amount_usd != null) {
    out.push({ label: "المبلغ", value: () => [num(fmtInt(ex.amount_usd)), " دولار"], at: findAmount(text, ex.amount_usd, "usd") });
  }
  if (ex.fee_iqd != null) {
    out.push({ label: "العمولة المعترض عليها", value: () => [num(fmtInt(ex.fee_iqd)), " دينار"], at: findAmount(text, ex.fee_iqd, "iqd") });
  }
  if (ex.recipient_phone) {
    out.push({ label: subcategory === "topup_failed" ? "الرقم اللي انشحن" : "رقم المستلم",
      value: () => mono(ex.recipient_phone), at: findLoose(text, ex.recipient_phone), ltr: true });
  }
  // The time as the model copied it, without an English gloss it sometimes adds («البارحة (card lost); …»), as in the
  // team note (handoff.py arabic_date).
  const date = arabicDate(ex.date);
  if (date) out.push({ label: "الوقت", value: () => el("span", { dir: "rtl", text: date }), at: findLiteral(text, date), words: true });
  return out;
}

/** The customer's text with each found fact underlined (mark[data-fact]). Digit groups split by spaces
 *  that no fact matched keep their written order too (digitRuns). Each `hidden` range ([start, end], a card
 *  number or a code) is drawn as «••••» instead, with no underline on it. A right-to-left mark (U+200F) goes at
 *  each offset in `rtl` (a mostly Arabic paragraph that starts with a Latin word, util.js rtlStarts). */
export function textWithFacts(text, facts, hidden = [], rtl = []) {
  const over = (at) => hidden.some(([s, e]) => at.start < e && s < at.end);
  return spanned(text, [
    ...rtl.map((i) => ({ start: i, end: i, insert: true, make: () => "\u200F" })),
    ...hidden.map(([s, e]) => ({ start: s, end: e, make: secretMask })),
    ...facts.map((f, i) => f.at && !over(f.at) && {
      start: f.at.start, end: f.at.end,
      // A reference or a phone keeps its own left-to-right order inside the Arabic sentence.
      make: (s) => el("mark", { class: "fact-mark", dir: f.ltr ? "ltr" : null, dataset: { fact: String(i) }, text: s }),
    }),
  ], digitRuns);
}

export const NOT_FOUND_AR = "ما لكيناه بالنص بنفس الشكل";
// What to do about it (the tip's second half, and the marker's description for a screen reader).
export const NOT_FOUND_DO_AR = "يمكن الزبون كاتبه بالحروف أو بشكل ثاني: قارنه بالرسالة.";

/** The facts as one quiet line under the customer's text, written the normal way (Western digits, amounts
 *  with their unit): «رقم العملية 9776 593217 · المبلغ 2,000,000 دينار · الوقت: من البارحة». Hovering or
 *  focusing a value lights its underline in the text (inside `scope`), and hovering the underline lights
 *  the value. A value not found in the text has no underline: a small «؟» marker, named for what it means,
 *  whose tip (hover, focus or a tap) says it and what to do. */
export function factLine(facts, scope) {
  const light = (i, on) => {
    scope.querySelectorAll(`[data-fact="${i}"]`).forEach((n) => n.classList.toggle("is-hot", on));
    line.querySelector(`[data-fact-val="${i}"]`)?.classList.toggle("is-hot", on);
  };
  const line = el("ul", { class: "facts", "aria-label": "المعلومات اللي طلعت من التذكرة" },
    facts.map((f, i) => {
      // A time is words: a colon keeps the label apart from it. A number reads apart by itself.
      const parts = [el("span", { class: "fact-label", text: f.words ? `${f.label}: ` : `${f.label} ` }),
        el("span", { class: "fact-value" }, f.value())];
      if (!f.at) {
        // The marker's «؟» is drawn by the stylesheet. Its name says what it means; its tip says that again
        // for the eye, and what to do (that half describes the button, so it is not read twice).
        const mark = el("button", { type: "button", class: "fact-tip", "aria-label": NOT_FOUND_AR });
        const li = withTip(mark, [`${NOT_FOUND_AR}. `, el("span", { id: `factTip${i}Do`, text: NOT_FOUND_DO_AR })],
          { id: `factTip${i}`, tag: "li", cls: "fact is-unfound", describe: `factTip${i}Do` });
        li.prepend(...parts);
        return li;
      }
      const btn = el("button", { type: "button", class: "fact-btn", dataset: { factVal: String(i) } }, parts);
      for (const [ev, on] of [["mouseenter", true], ["mouseleave", false], ["focus", true], ["blur", false]]) {
        btn.addEventListener(ev, () => light(i, on));
      }
      btn.addEventListener("click", () => scope.querySelector(`[data-fact="${i}"]`)?.scrollIntoView({ block: "nearest" }));
      return el("li", { class: "fact" }, btn);
    }));
  // The other way round: the underline in the text lights its value in the line. A touch screen has no
  // hover: a tap on the underline shows the value just after it (the line can be off screen, under the
  // action bar), until the next tap. The line says the same to a screen reader.
  scope.querySelectorAll("[data-fact]").forEach((m) => {
    m.addEventListener("mouseenter", () => light(m.dataset.fact, true));
    m.addEventListener("mouseleave", () => light(m.dataset.fact, false));
    m.addEventListener("click", () => {
      const shown = m.nextElementSibling?.classList.contains("fact-pop");
      scope.querySelectorAll(".fact-pop").forEach((n) => n.remove());
      if (shown) return;
      const f = facts[m.dataset.fact];
      m.after(el("span", { class: "fact-pop", "aria-hidden": "true", dir: "rtl" }, f.words ? `${f.label}: ` : `${f.label} `, f.value()));
    });
  });
  return line;
}
