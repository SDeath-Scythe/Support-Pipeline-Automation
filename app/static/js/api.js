// Every call to the viewer's /api/: the per-page token, the server's Arabic errors, and the live event stream.

// The server puts a per-process token in the page; every /api/ call must send it back.
const TOKEN = document.querySelector('meta[name="viewer-token"]')?.content || "";

/** The server answered with a refusal: its Arabic message (and the field it names, if any). */
export class ServerError extends Error {
  constructor(status, message, field = null) {
    super(message || `HTTP ${status}`);
    this.status = status;
    this.field = field;
  }
}
/** The server could not be reached, or the connection dropped. */
export class NetworkError extends Error {}

const listeners = new Set();
/** Called with every NetworkError and every 403 (a restarted server has a new token). */
export function onTrouble(fn) { listeners.add(fn); }
function trouble(err) { for (const fn of listeners) fn(err); }

export async function api(url, opts = {}) {
  let r;
  try {
    r = await fetch(url, { ...opts, headers: { ...(opts.headers || {}), "X-Viewer-Token": TOKEN } });
  } catch (e) {
    if (e?.name === "AbortError") throw e;
    const err = new NetworkError("network");
    trouble(err);
    throw err;
  }
  if (!r.ok) {
    let body = null;
    try { body = await r.json(); } catch { /* not JSON */ }
    const err = new ServerError(r.status, body?.error, body?.field ?? null);
    if (r.status === 403) trouble(err);
    throw err;
  }
  return r;
}

export const getJSON = (url, opts) => api(url, opts).then((r) => r.json());

export function postJSON(url, body, opts = {}) {
  return api(url, { ...opts, method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
    .then((r) => r.json());
}

/** Start a live run. Resolves once the server accepted it (the caller shows a refusal: 413, 429, 403, 400). */
export async function openStream(text, signal) {
  return api("/api/stream", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }), signal,
  });
}

/** Read "data: {...}" blocks until "event: end". Comment lines (": ping") are ignored. A stream that
 *  closes before its end throws a NetworkError. */
export async function readEvents(response, onEvent) {
  const reader = response.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  for (;;) {
    let chunk;
    try {
      chunk = await reader.read();
    } catch (e) {
      if (e?.name === "AbortError") throw e;
      throw new NetworkError("stream");
    }
    if (chunk.done) throw new NetworkError("closed before its end");
    buf += dec.decode(chunk.value, { stream: true }).replace(/\r\n?/g, "\n");
    let i;
    while ((i = buf.indexOf("\n\n")) >= 0) {
      const lines = buf.slice(0, i).split("\n");
      buf = buf.slice(i + 2);
      if (lines.includes("event: end")) {
        reader.cancel().catch(() => {});
        return;
      }
      const data = lines.filter((l) => l.startsWith("data:")).map((l) => l.slice(5).replace(/^ /, "")).join("\n");
      if (data) onEvent(JSON.parse(data));
    }
  }
}

/** POST /api/check: the draft rules on a draft the agent is editing. Nothing is logged by the server. */
export function checkDraft({ draft, allowed_text, subcategory }, signal) {
  const body = { draft, allowed_text };
  if (subcategory) body.subcategory = subcategory;
  return postJSON("/api/check", body, { signal }).then((j) => j.findings || []);
}
