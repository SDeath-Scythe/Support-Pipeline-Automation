// Page-wide pieces: the one polite status region (the decision toast) and the banners under the header.

import { el, icon } from "./util.js";

const toast = () => document.getElementById("toast");
const statusEl = () => document.getElementById("status");
const undoBtn = () => document.getElementById("toastUndo");

let timer = null;
let undoAction = null;
let hovering = false;
let returnTo = null;   // where focus was before it entered the toast

/** Show a decision message for about 6 s (it waits while the pointer or focus is on it). One polite
 *  status region for the whole page: streamed stages are never announced. */
export function showToast(content, onUndo = null) {
  clearTimeout(timer);
  statusEl().replaceChildren(...[content].flat(Infinity).map((c) => (c?.nodeType ? c : document.createTextNode(String(c ?? "")))));
  undoAction = onUndo;
  undoBtn().hidden = !onUndo;
  toast().classList.add("is-shown");
  arm();
}
function arm() {
  clearTimeout(timer);
  timer = setTimeout(() => {
    if (hovering || toast().contains(document.activeElement)) return arm();
    hideToast();
  }, 6000);
}
export function hideToast() {
  clearTimeout(timer);
  const t = toast();
  const hadFocus = t.contains(document.activeElement);
  t.classList.remove("is-shown");
  undoAction = null;
  // A hidden toast can't keep the focus: it goes back where it was, never to <body>.
  if (hadFocus) {
    const back = returnTo?.isConnected ? returnTo : document.getElementById("ticketTitle") || document.getElementById("main");
    back?.focus();
  }
  // The status text stays until the next message, so it isn't announced as removed.
}
export function initToast() {
  const t = toast();
  t.addEventListener("mouseenter", () => { hovering = true; });
  t.addEventListener("mouseleave", () => { hovering = false; });
  t.addEventListener("focusin", (e) => { if (e.relatedTarget && !t.contains(e.relatedTarget)) returnTo = e.relatedTarget; });
  undoBtn().addEventListener("click", () => { const fn = undoAction; hideToast(); fn?.(); });
  document.getElementById("toastClose").addEventListener("click", hideToast);
}

// --- banners ---

const banners = new Map();

/** A banner under the header, by id: {kind: "warn" | "bad" | "info", title, text, action: {label, run}}. */
export function setBanner(id, b) {
  banners.set(id, b);
  drawBanners();
}
export function clearBanner(id) {
  if (banners.delete(id)) drawBanners();
}
function drawBanners() {
  const box = document.getElementById("banners");
  box.replaceChildren(...[...banners.entries()].map(([id, b]) => el("div", { class: `banner banner-${b.kind}`, dataset: { id } },
    icon(b.icon || (b.kind === "info" ? "lock" : b.kind === "bad" ? "lost" : "check")),
    el("p", { class: "banner-text" }, b.title ? el("strong", { text: b.title }) : null, b.title ? " " : null, b.text),
    b.action ? el("button", { type: "button", class: "btn btn-quiet btn-small", text: b.action.label, onclick: b.action.run }) : null)));
  box.hidden = banners.size === 0;
}
