// Small helpers shared by every view. Every node is built here with textContent: no HTML strings, so a
// ticket or a model reply can never become markup.

const SVG_NS = "http://www.w3.org/2000/svg";

/** el("div", {class: "x", text: "..."}, child, "text", [more]) */
export function el(tag, attrs = {}, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === "class") n.className = v;
    else if (k === "text") n.textContent = v;
    else if (k === "dataset") Object.assign(n.dataset, v);
    else if (k.startsWith("on") && typeof v === "function") n.addEventListener(k.slice(2), v);
    else if (k === "hidden" || k === "disabled" || k === "checked") n[k] = !!v;
    else n.setAttribute(k, v === true ? "" : String(v));
  }
  append(n, kids);
  return n;
}

/** node.append() that skips null, false and nested arrays (append(null) would add the text "null"). */
export function add(n, ...kids) {
  append(n, kids);
  return n;
}

function append(n, kids) {
  for (const k of kids.flat(Infinity)) {
    if (k == null || k === false) continue;
    n.append(k.nodeType ? k : document.createTextNode(String(k)));
  }
}

/** A map read with keys that come from data (flags, teams, types): no inherited keys, so a key like
 *  "constructor" or "__proto__" reads as missing instead of reaching Object.prototype. */
export function dict(obj) {
  return Object.assign(Object.create(null), obj || {});
}

/** A left-to-right island inside Arabic text: ids, references, phones, amounts, P1, times, model ids. */
export function ltr(text, cls = "") {
  return el("bdi", { dir: "ltr", class: cls || null, text: String(text) });
}
export const mono = (text) => ltr(text, "mono");
/** A ticket's id as the page shows it. A live run's id (live-<UTC time>-<6 hex>, the decision log's) is
 *  shortened to «live-» and its 6 hex digits. */
export const ticketId = (key) => mono(String(key).replace(/^live-\d{14}-(?=[0-9a-f]{6}$)/, "live-"));
export const num = (text) => ltr(text, "num");

// Line icons (24 px grid, drawn with currentColor). Built with createElementNS, never from a string.
const ICONS = {
  ready: ["M20 6 9 17l-5-5"],
  check: ["M12 9v4", "M12 17h.01", "M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"],
  escalated: ["M12 3 4 6v6c0 5 3.4 8.5 8 9 4.6-.5 8-4 8-9V6z", "M12 8v4", "M12 16h.01"],
  done: ["M22 11.1V12a10 10 0 1 1-5.9-9.1", "M22 4 12 14l-3-3"],
  running: ["M21 12a9 9 0 1 1-6.2-8.6"],
  lost: ["M2 2l20 20", "M8.5 16.4a5 5 0 0 1 7 0", "M2 8.8a15 15 0 0 1 4.2-2.6", "M10.7 5.1A15 15 0 0 1 22 8.8", "M12 20h.01"],
  back: ["M9 18l6-6-6-6"],          // drawn pointing right: "back" in a right-to-left page
  next: ["M15 18l-6-6 6-6"],
  up: ["M18 15l-6-6-6 6"],
  down: ["M6 9l6 6 6-6"],
  plus: ["M12 5v14", "M5 12h14"],
  keyboard: ["M2 6h20v12H2z", "M6 10h.01", "M10 10h.01", "M14 10h.01", "M18 10h.01", "M7 14h10"],
  panel: ["M3 4h18v16H3z", "M9 4v16"],
  lock: ["M5 11h14v10H5z", "M8 11V7a4 4 0 0 1 8 0v4"],
  send: ["M19 12H5", "M11 6l-6 6 6 6"],   // forward points left in a right-to-left page
  user: ["M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2", "M12 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8z"],
  undo: ["M9 14 4 9l5-5", "M4 9h11a5 5 0 0 1 0 10h-3"],
  edit: ["M12 20h9", "M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"],
  close: ["M18 6 6 18", "M6 6l12 12"],
};
export function icon(name, cls = "") {
  const s = document.createElementNS(SVG_NS, "svg");
  s.setAttribute("viewBox", "0 0 24 24");
  s.setAttribute("aria-hidden", "true");
  s.setAttribute("focusable", "false");
  s.setAttribute("class", `icon icon-${name} ${cls}`.trim());
  for (const d of ICONS[name] || []) {
    const p = document.createElementNS(SVG_NS, "path");
    p.setAttribute("d", d);
    s.append(p);
  }
  return s;
}

const AR_LETTER = /[\u0600-\u06FF]/;
/** <kbd> hints: kbd("J", "ت") → "J / ت"; kbd("Ctrl+Enter"). A single key (no modifier) is hidden while
 *  single-key shortcuts are switched off (body.keys-off); an Arabic letter gets the Arabic face. */
export function kbd(...keys) {
  const single = keys.every((k) => !k.includes("+"));
  const out = el("span", { class: `kbd-hint${single ? " kbd-single" : ""}`, "aria-hidden": "true" });
  keys.forEach((k, i) => {
    if (i) out.append(el("span", { class: "kbd-sep", text: "/" }));
    out.append(el("kbd", { class: AR_LETTER.test(k) ? "kbd-ar" : null, dir: AR_LETTER.test(k) ? null : "ltr", text: k }));
  });
  return out;
}
export const MAC = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent || "");
export const MOD = MAC ? "⌘" : "Ctrl";

// --- numbers and digits ---

const AR_DIGITS = /[٠-٩۰-۹]/g;
/** Arabic-Indic and Persian digits as Western digits, one character for one (offsets stay valid). */
export function westernDigits(s) {
  return String(s ?? "").replace(AR_DIGITS, (d) => {
    const c = d.charCodeAt(0);
    return String(c >= 0x6f0 ? c - 0x6f0 : c - 0x660);
  });
}
export const fmtInt = (n) => Number(n).toLocaleString("en-US");

/** Seconds as nodes, the numbers in left-to-right islands: «14 ث», «2 د 5 ث». */
export function fmtSeconds(s) {
  if (s == null || !isFinite(s)) return "—";
  if (s < 60) return [num(s < 10 ? s.toFixed(1) : String(Math.round(s))), " ث"];
  const m = Math.floor(s / 60), r = Math.round(s % 60);
  return [num(String(m)), " د ", num(String(r)), " ث"];
}

/** A pipeline event's own time in ms (e.own): its e.ms counts from the ticket's start, and the stages run
 *  one after another, so a stage took the time since the event just before it. Sets and returns e. */
export function stampOwn(prev, e) {
  if (e && typeof e.ms === "number" && e.own == null) {
    e.own = Math.max(0, e.ms - (typeof prev?.ms === "number" ? prev.ms : 0));
  }
  return e;
}

export function median(xs) {
  const a = xs.filter((x) => typeof x === "number" && isFinite(x)).sort((p, q) => p - q);
  if (!a.length) return null;
  const m = Math.floor(a.length / 2);
  return a.length % 2 ? a[m] : (a[m - 1] + a[m]) / 2;
}

// Digit groups split by spaces or hyphens («0791 079 0226», «9776 593217», «2497-53512»), and a reference of letters,
// a hyphen and digits («BP-77120458»): in a right-to-left paragraph each digit group after Arabic text is its own
// number, and the space or hyphen between them does not join them, so the groups come out in reverse order (Unicode
// bidi rules W2 and W4), and a reference can split across two lines.
const DIGIT = "[0-9\\u0660-\\u0669\\u06F0-\\u06F9]";
const DIGIT_GROUPS = new RegExp(`${DIGIT}+(?:[ \\u00A0\\u2011-]${DIGIT}+)+|(?<![A-Za-z])[A-Za-z]+-${DIGIT}+(?:-[A-Za-z0-9]+)*`, "g");

/** Plain text with every run of space- or hyphen-separated digit groups (and every «BP-…» reference) in a
 *  left-to-right island that does not break across lines, so a phone or a reference reads in the order it was
 *  written (read-only text: queue rows, replies, the customer). */
export function digitRuns(s) {
  const frag = document.createDocumentFragment();
  const str = String(s ?? "");
  let last = 0;
  for (const m of str.matchAll(DIGIT_GROUPS)) {
    if (m.index > last) frag.append(str.slice(last, m.index));
    frag.append(ltr(m[0], "num nowrap"));
    last = m.index + m[0].length;
  }
  if (last < str.length) frag.append(str.slice(last));
  return frag;
}

// The draft box can't hold an island, so a space between two digits is shown as a no-break space
// (U+00A0): its bidi class (CS) joins the groups into one number. A hyphen between two letters or digits
// («2497-53512», «M-30417») is shown as a non-breaking hyphen (U+2011), so a reference never splits across
// lines. After Arabic text, digits joined by a hyphen of either kind still read backwards (bidi rule W2 makes
// them Arabic numbers, which a hyphen does not join), so a left-to-right mark (U+200E) goes before each such
// run: the digits then read left to right, in order (second round of role-played test sessions). The mark is
// one character more, so offsets in the real text are mapped (shownAt, realAt); realDraft() takes the marks out
// and turns the rest back before the text is compared, checked or saved: the reply keeps its plain hyphen.
const DIGIT_SPACE = /(?<=[0-9\u0660-\u0669\u06F0-\u06F9]) (?=[0-9\u0660-\u0669\u06F0-\u06F9])/g;
const DIGIT_NBSP = /(?<=[0-9\u0660-\u0669\u06F0-\u06F9])\u00A0(?=[0-9\u0660-\u0669\u06F0-\u06F9])/g;
const WORD_HYPHEN = /(?<=[\p{L}\p{N}])-(?=[\p{L}\p{N}])/gu;
const WORD_NBHYPHEN = /(?<=[\p{L}\p{N}])\u2011(?=[\p{L}\p{N}])/gu;
const HYPHEN_RUN = /(?<![\p{L}\p{N}\u200E])[0-9\u0660-\u0669\u06F0-\u06F9]+(?:[-\u2011][\p{L}\p{N}]+)+/gu;
const LRM = "\u200E";
export const shownDraft = (text) => String(text ?? "").replace(/\u200E/g, "").replace(HYPHEN_RUN, (m) => LRM + m)
  .replace(DIGIT_SPACE, "\u00A0").replace(WORD_HYPHEN, "\u2011");
export const realDraft = (shown) => String(shown ?? "").replace(/\u200E/g, "").replace(DIGIT_NBSP, " ").replace(WORD_NBHYPHEN, "-");
/** Where offset `i` of the real text (realDraft(shown)) is in `shown`: the marks before it are counted in. */
export function shownAt(shown, i) {
  let real = 0;
  for (let j = 0; j < shown.length; j++) {
    if (shown[j] === LRM) continue;
    if (real === i) return j;
    real++;
  }
  return shown.length;
}
/** Where offset `j` of `shown` is in the real text. */
export const realAt = (shown, j) => j - (shown.slice(0, j).match(/\u200E/g) || []).length;

// Direction controls (embeddings, overrides, isolates, marks) change the order text is drawn in, not the
// order the model and the rules read. The page shows the order they read, and says how many it hid.
const BIDI_CONTROLS = /[\u202A-\u202E\u2066-\u2069]/g;
const BIDI_MARKS = /[\u200E\u200F]/g;
/** Customer text without direction controls: {text, hidden} (hidden counts the controls, not the marks). */
export function plainText(s) {
  const str = String(s ?? "");
  const hidden = (str.match(BIDI_CONTROLS) || []).length;
  return { text: str.replace(BIDI_CONTROLS, "").replace(BIDI_MARKS, ""), hidden };
}

// A message padded with blank lines («سطر وحد، 60 سطر فاضي، وبعدين نص») pushed the rest of the ticket and the draft
// off the screen while approve was on (second round of role-played test sessions). Three or more line breaks, with
// only spaces between them, are shown as one blank line. A line of only a zero-width, wide or ideographic space, a
// blank-looking filler, or a carriage return (CRLF line ends) is blank too (review before shipping, 7 Nov: those
// paddings were shown whole). Each run still becomes two characters, so the cuts below keep their offsets.
const BLANK_RUN = /\n(?:[\t\r\p{Zs}\u200B-\u200D\u2060\uFEFF\u115F\u1160\u3164\uFFA0\u2800]*\n){2,}/gu;
/** {text, removed, at(i)}: the text with each run of blank lines kept to one, how many blank lines went, and where
 *  offset i of the original text is in the new one (for the hidden numbers' ranges). */
export function collapseBlank(s) {
  const str = String(s ?? "");
  const cuts = [];   // [start, end] in the original that go, in order
  let removed = 0;
  const text = str.replace(BLANK_RUN, (m, off) => {
    cuts.push([off + 2, off + m.length]);
    removed += (m.match(/\n/g) || []).length - 2;
    return "\n\n";
  });
  const at = (i) => {
    let shift = 0;
    for (const [a, b] of cuts) {
      if (i >= b) shift += b - a;
      else if (i > a) shift += i - a;
    }
    return i - shift;
  };
  return { text, removed, at };
}

// An Arabic paragraph that starts with a Latin word («SYSTEM: وأكد…») was laid out left to right: the page lets
// each paragraph take the direction of its first letter (unicode-bidi: plaintext). A paragraph that is mostly
// Arabic letters gets a right-to-left mark (U+200F) at its start, so it reads right to left; English stays left
// to right (second round of role-played test sessions).
const AR_LETTERS = /[\u0600-\u06FF\u0750-\u077F]/g;
const LATIN_LETTERS = /[A-Za-z]/g;
const FIRST_STRONG = /[A-Za-z\u0600-\u06FF\u0750-\u077F]/;
/** The offsets where a paragraph of `text` needs a right-to-left mark: mostly Arabic, with a Latin letter first. */
export function rtlStarts(text) {
  const out = [];
  let at = 0;
  for (const para of String(text ?? "").split("\n")) {
    const ar = (para.match(AR_LETTERS) || []).length, lat = (para.match(LATIN_LETTERS) || []).length;
    const first = para.match(FIRST_STRONG);
    if (ar > lat && first && /[A-Za-z]/.test(first[0])) out.push(at);
    at += para.length + 1;
  }
  return out;
}
/** The same text with the mark put in (read-only text, where no offset is kept: queue rows, replies). */
export const rtlText = (text) => {
  let out = String(text ?? "");
  for (const i of rtlStarts(out).reverse()) out = `${out.slice(0, i)}\u200F${out.slice(i)}`;
  return out;
};

/** A count with its noun in the right form: 1 «تذكرة وحدة», 2 «تذكرتين», 3–10 «3 تذاكر», 11+ «11 تذكرة». */
export function countAr(n, { one, two, few, many }) {
  if (n === 1) return one;
  if (n === 2) return two;
  return [num(String(n)), " ", n >= 3 && n <= 10 ? few : many];
}
const TICKET_FORMS = { one: "تذكرة وحدة", two: "تذكرتين", few: "تذاكر", many: "تذكرة" };
export const ticketsAr = (n) => countAr(n, TICKET_FORMS);
/** The same as plain text (for an <option>, a title). */
export const ticketsText = (n) => (n === 1 ? TICKET_FORMS.one : n === 2 ? TICKET_FORMS.two : `${n} ${n >= 3 && n <= 10 ? TICKET_FORMS.few : TICKET_FORMS.many}`);

// A Latin word or number («TX-2291», «2,000,000», «(Sunday)»), and a run of them with the spaces, commas
// and brackets between them.
const LATIN_WORD = "\\(?[0-9A-Za-z$](?:[0-9A-Za-z$,._:/'’-]*[0-9A-Za-z$])?\\)?";
const LATIN_RUN = new RegExp(`${LATIN_WORD}(?:[,;]?[ \\t]+${LATIN_WORD})*`, "g");
/** Text with every run of Latin words or digits wrapped in one LTR island (for notes from the pipeline).
 *  One island per run, not per word: islands side by side are laid out right to left, so an English
 *  phrase split into words would read backwards. */
export function richText(s) {
  const frag = document.createDocumentFragment();
  const re = new RegExp(LATIN_RUN);
  let last = 0, m;
  const str = String(s ?? "");
  while ((m = re.exec(str))) {
    if (m.index > last) frag.append(str.slice(last, m.index));
    frag.append(ltr(m[0], /^\(?[0-9$]/.test(m[0]) ? "num" : ""));
    last = m.index + m[0].length;
  }
  if (last < str.length) frag.append(str.slice(last));
  return frag;
}

// --- offsets: the server counts code points (Python), the page counts UTF-16 units ---

/** [start, end) in code points → [start, end) in UTF-16 units of the same text; null if out of range. */
export function cpToUtf16(text, start, end) {
  let cp = 0, u = 0, s = null, e = null;
  for (const ch of text) {
    if (cp === start) s = u;
    if (cp === end) e = u;
    cp++;
    u += ch.length;
  }
  if (s === null && cp === start) s = u;
  if (e === null && cp === end) e = u;
  return s === null || e === null || e < s ? null : [s, e];
}

/** A text with each range [start, end] (UTF-16, not overlapping) put as `mask`. */
export function masked(text, ranges, mask) {
  let out = text;
  for (const [s, e] of [...ranges].sort((a, b) => b[0] - a[0])) out = out.slice(0, s) + mask + out.slice(e);
  return out;
}

/** A text as fragments with some ranges wrapped: spans = [{start, end, make(text) → node}] in UTF-16.
 *  plain(text) builds the parts between them (default: the text as it is). */
export function spanned(text, spans, plain = (t) => t) {
  const frag = document.createDocumentFragment();
  // A span with insert (start === end) puts its node at that place and takes no text (a direction mark).
  const sorted = spans.filter((x) => x && (x.end > x.start || (x.insert && x.end === x.start)))
    .sort((a, b) => a.start - b.start || (b.insert ? 1 : 0) - (a.insert ? 1 : 0));
  let at = 0;
  for (const sp of sorted) {
    if (sp.start < at) continue;   // overlapping ranges: the first wins
    if (sp.start > at) frag.append(plain(text.slice(at, sp.start)));
    frag.append(sp.make(text.slice(sp.start, sp.end)));
    at = sp.end;
  }
  if (at < text.length) frag.append(plain(text.slice(at)));
  return frag;
}

// --- tips: a few words on hover, keyboard focus or a tap ---

/** A trigger button with its tip (WCAG 1.4.13): the tip is a real element (role=tooltip) that describes the
 *  button (aria-describedby). It shows on hover, on keyboard focus, or after a tap or click that pins it (a
 *  second one, or leaving, unpins it). The pointer can move onto it. Escape hides it (dismissTips) until the
 *  pointer and the focus leave. Returns the wrapper (tag, default span) holding both. */
export function withTip(trigger, tipKids, { id, tag = "span", cls = "", describe = null } = {}) {
  const tip = el("span", { id, role: "tooltip", class: "tip" }, tipKids);
  trigger.setAttribute("aria-describedby", describe || id);
  const box = el(tag, { class: `has-tip ${cls}`.trim() }, trigger, tip);
  // A touch screen keeps :hover on what was tapped, so a tap's tip follows the taps alone (the pin).
  trigger.addEventListener("pointerdown", (e) => box.classList.toggle("by-touch", e.pointerType !== "mouse"));
  trigger.addEventListener("click", () => { box.classList.toggle("is-pinned"); box.classList.remove("is-dismissed"); });
  box.addEventListener("mouseleave", () => { if (!box.contains(document.activeElement)) box.classList.remove("is-dismissed"); });
  box.addEventListener("focusout", (e) => {
    if (box.contains(e.relatedTarget)) return;
    box.classList.remove("is-pinned");
    if (!box.matches(":hover")) box.classList.remove("is-dismissed");
  });
  return box;
}
/** Escape: hide every tip on screen (hovered, focused or pinned). True if one was shown. */
export function dismissTips() {
  let any = false;
  for (const box of document.querySelectorAll(".has-tip")) {
    const tip = box.querySelector(":scope > .tip");
    if (!tip || getComputedStyle(tip).visibility !== "visible") continue;
    box.classList.add("is-dismissed");
    box.classList.remove("is-pinned");
    any = true;
  }
  return any;
}

// --- preferences: never ticket text, drafts or edits ---

// v2 (5 Nov): «ليش؟» starts closed. v1 saved whyOpen: true for everyone (it was the default and every save
// wrote it), so until the page first saves v2 it reads v1 for the other four and drops its whyOpen: the
// panel opens by itself only after the agent opened it.
const PREF_KEY = "support-viewer-prefs-v2";
const PREF_KEY_V1 = "support-viewer-prefs-v1";
// introSeen: the first-visit card («أول مرة هنا؟») was dismissed with «فهمت».
// whyOpen: the agent opened «ليش؟» (the button or W) and left it open.
// The mode is not kept: every visit starts in «وضع الموظف» (a pasted ticket then opens as a ticket, not a trace).
const PREF_DEFAULTS = { singleKeys: true, whyOpen: false, source: null, introSeen: false };
export function loadPrefs() {
  try {
    const now = localStorage.getItem(PREF_KEY);
    const raw = JSON.parse(now || localStorage.getItem(PREF_KEY_V1) || "{}");
    if (!now) delete raw.whyOpen;
    const out = { ...PREF_DEFAULTS };
    if (typeof raw.singleKeys === "boolean") out.singleKeys = raw.singleKeys;
    if (typeof raw.whyOpen === "boolean") out.whyOpen = raw.whyOpen;
    if (typeof raw.source === "string" && raw.source.length < 300) out.source = raw.source;
    if (typeof raw.introSeen === "boolean") out.introSeen = raw.introSeen;
    return out;
  } catch {
    return { ...PREF_DEFAULTS };
  }
}
export function savePrefs(prefs) {
  try {
    const { singleKeys, whyOpen, source, introSeen } = prefs;
    localStorage.setItem(PREF_KEY, JSON.stringify({ singleKeys, whyOpen, source, introSeen }));
  } catch { /* private window or blocked storage: the page works without it */ }
}

export function reducedMotion() {
  return matchMedia("(prefers-reduced-motion: reduce)").matches;
}
export function isPhone() {
  return matchMedia("(max-width: 720px)").matches;
}
/** A touch screen is the main pointer: no key hints in the page's words (the «?» sheet still lists them). */
export function coarsePointer() {
  return matchMedia("(pointer: coarse)").matches;
}

/** True when a key press is going into a text field (single-key shortcuts stay quiet). */
export function typingIn(target) {
  if (!target || !(target instanceof Element)) return false;
  if (target.isContentEditable) return true;
  const tag = target.tagName;
  if (tag === "TEXTAREA" || tag === "SELECT") return true;
  if (tag === "INPUT") return !["checkbox", "radio", "button", "submit", "reset", "range", "color"].includes(target.type);
  return false;
}

export function debounce(fn, ms) {
  let t = null;
  const d = (...args) => { clearTimeout(t); t = setTimeout(() => { t = null; fn(...args); }, ms); };
  d.cancel = () => { clearTimeout(t); t = null; };
  d.pending = () => t !== null;
  return d;
}

/** Native modal dialog: the rest of the page is inert, Escape closes it, focus returns where it was,
 *  unless something else took the focus meanwhile (a ticket the dialog started opened its heading). */
export function openDialog(dlg, focusEl) {
  const back = document.activeElement;
  dlg.addEventListener("close", () => {
    const now = document.activeElement;
    const free = !now || now === document.body || dlg.contains(now);
    if (free && back && back.isConnected) back.focus();
  }, { once: true });
  dlg.showModal();
  (focusEl || dlg.querySelector("[autofocus]") || dlg.querySelector("button, textarea, input, select"))?.focus();
}
