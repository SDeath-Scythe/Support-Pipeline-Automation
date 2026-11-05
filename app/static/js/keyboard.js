// Keyboard shortcuts, bound by KeyboardEvent.code so they work on an Arabic layout too (J is «ت»).
// Single keys never fire while typing and can be switched off in the shortcut sheet (WCAG 2.1.4).

import { S } from "./state.js";
import { dismissTips, openDialog, typingIn } from "./util.js";

/**
 * actions: {next, prev, approve, focusDraft, leave, takeOver, disarm, forward, toggleWhy, closeWhy, whyIsDrawer,
 *   undo, tab(n), save()}
 */
export function initKeys(actions) {
  const sheet = document.getElementById("sheet");
  const toggle = document.getElementById("singleKeys");
  toggle.checked = S.prefs.singleKeys;
  toggle.addEventListener("change", () => { S.prefs.singleKeys = toggle.checked; actions.save(); });
  document.getElementById("sheetClose").addEventListener("click", () => sheet.close());
  const openSheet = () => openDialog(sheet, document.getElementById("sheetClose"));

  document.addEventListener("keydown", (e) => {
    if (e.defaultPrevented || e.isComposing) return;
    if (document.querySelector("dialog[open]")) return;    // a dialog handles its own keys (Escape closes it)
    const agent = S.mode === "agent";
    const mod = e.ctrlKey || e.metaKey;

    if (mod && !e.altKey && (e.code === "Enter" || e.code === "NumpadEnter")) {
      if (!agent) return;
      e.preventDefault();
      actions.approve();
      return;
    }
    if (mod && !e.altKey && !e.shiftKey && e.code === "KeyZ") {
      if (typingIn(e.target) || !agent) return;   // the text field keeps its own undo
      e.preventDefault();
      actions.undo();
      return;
    }
    if (e.key === "Escape") {
      if (agent && e.target?.id === "draft") { e.preventDefault(); actions.leave(); return; }
      // One thing per press, the nearest first: a tip on screen (WCAG 1.4.13), an armed take-over («رجوع»),
      // then «ليش؟» beside the ticket (over 720 px), from inside it or from anywhere in the page that is not
      // a field (a select keeps its own Escape).
      if (dismissTips()) { e.preventDefault(); return; }
      if (agent && !typingIn(e.target) && actions.disarm()) { e.preventDefault(); return; }
      const why = document.getElementById("why");
      if (agent && actions.whyIsDrawer() && document.body.classList.contains("why-open")
        && (why.contains(e.target) || !typingIn(e.target))) { e.preventDefault(); actions.closeWhy(); }
      return;
    }
    if (mod || e.altKey) return;
    if (typingIn(e.target)) return;
    // Every key below is a single character, «?» included: all of them stop when the agent switches
    // single-key shortcuts off (WCAG 2.1.4). The sheet then opens from its button in the header.
    if (!S.prefs.singleKeys) return;

    const isHelp = e.key === "?" || e.key === "؟" || (e.code === "Slash" && e.shiftKey);
    if (isHelp) { e.preventDefault(); openSheet(); return; }

    if (!agent) return;
    const inPage = !e.target || e.target === document.body || e.target.id === "ticketTitle";
    switch (e.code) {
      case "KeyJ": e.preventDefault(); actions.next(); break;
      case "KeyK": e.preventDefault(); actions.prev(); break;
      case "ArrowDown": if (inPage) { e.preventDefault(); actions.next(); } break;
      case "ArrowUp": if (inPage) { e.preventDefault(); actions.prev(); } break;
      case "KeyE": if (actions.focusDraft()) e.preventDefault(); break;
      case "KeyT": e.preventDefault(); actions.takeOver(); break;
      case "KeyF": e.preventDefault(); actions.forward(); break;
      case "KeyW": e.preventDefault(); actions.toggleWhy(); break;
      case "Digit1": case "Digit2": case "Digit3": case "Digit4":
      case "Numpad1": case "Numpad2": case "Numpad3": case "Numpad4":
        e.preventDefault(); actions.tab(Number(e.code.slice(-1)) - 1); break;
      default: break;
    }
  });
  return openSheet;
}
