// The details the pipeline pulled out of a ticket (reference, amount, phone, time), each paired with the
// place it was written in the customer's text. Matching reads Arabic-Indic digits as Western digits and
// skips the separators people type («٤٤٧١-٩٠٣٢», «2,000,000»), so the underline sits on what they wrote.

import { digitRuns, el, fmtInt, mono, num, spanned, westernDigits } from "./util.js";

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
  if (ex.date) out.push({ label: "الوقت", value: () => el("span", { dir: "rtl", text: ex.date }), at: findLiteral(text, ex.date) });
  return out;
}

/** The customer's text with each found fact underlined (mark[data-fact]). Digit groups split by spaces
 *  that no fact matched keep their written order too (digitRuns). */
export function textWithFacts(text, facts) {
  return spanned(text, facts.map((f, i) => f.at && {
    start: f.at.start, end: f.at.end,
    // A reference or a phone keeps its own left-to-right order inside the Arabic sentence.
    make: (s) => el("mark", { class: "fact-mark", dir: f.ltr ? "ltr" : null, dataset: { fact: String(i) }, text: s }),
  }), digitRuns);
}

/** The fact list: focusing or hovering an item lights its place in the text (inside `scope`). */
export function factList(facts, scope) {
  const light = (i, on) => {
    scope.querySelectorAll(`[data-fact="${i}"]`).forEach((n) => n.classList.toggle("is-hot", on));
  };
  return el("ul", { class: "facts", "aria-label": "المعلومات اللي طلعت من التذكرة" },
    facts.map((f, i) => {
      const parts = [
        el("span", { class: "fact-label", text: f.label }),
        el("span", { class: "fact-value" }, f.value()),
        f.at ? null : el("span", { class: "fact-where", text: "ما لكيناه بالنص بنفس الشكل" }),
      ];
      if (!f.at) return el("li", { class: "fact" }, parts);
      const btn = el("button", { type: "button", class: "fact-btn" }, parts);
      btn.addEventListener("mouseenter", () => light(i, true));
      btn.addEventListener("mouseleave", () => light(i, false));
      btn.addEventListener("focus", () => light(i, true));
      btn.addEventListener("blur", () => light(i, false));
      btn.addEventListener("click", () => scope.querySelector(`[data-fact="${i}"]`)?.scrollIntoView({ block: "nearest" }));
      return el("li", { class: "fact" }, btn);
    }));
}
