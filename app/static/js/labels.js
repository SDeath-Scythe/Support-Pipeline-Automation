// The page's Arabic words in one place. Labels that the server owns (issue types, teams, flags, reason
// codes, draft checks) come from /api/meta; these are the page's own. Every map that is read with a key
// from the data is a dict() (no inherited keys).

import { dict } from "./util.js";

export const PRIORITY_AR = dict({ P1: "عاجلة", P2: "مهمة", P3: "عادية" });
export const PRIORITY_RANK = dict({ P1: 1, P2: 2, P3: 3 });

// Queue tabs, in their order (keys 1 to 4).
export const TABS = [
  { id: "flagged", label: "تحتاج تأكيد" },
  { id: "escalated", label: "متصعّدة" },
  { id: "drafted", label: "جاهزة" },
  { id: "done", label: "خلصت" },
];

// A row's status: a word, never colour alone. Inside a tab the word is the row's accessible name only
// (the tab already says it); a live row and a broken run show it, with an icon.
export const STATUS = dict({
  drafted: { icon: "ready", word: "جاهزة" },
  flagged: { icon: "check", word: "تحتاج تأكيد" },   // the tab's own words
  escalated: { icon: "escalated", word: "متصعّدة" },
  running: { icon: "running", word: "تنعالج" },
  lost: { icon: "lost", word: "انقطعت" },
});

// What the agent did, as a row word and in the toast.
export const ACTION_WORD = dict({
  approved: "انعتمدت", edited: "انعدّلت وانعتمدت", took_over: "استلمتها", forwarded: "تحوّلت",
});
// The small icon a decided row shows in «خلصت» (its name is ACTION_WORD).
export const ACTION_ICON = dict({ approved: "ready", edited: "edit", took_over: "user", forwarded: "send" });

// The live row while a ticket goes through: what is happening now.
export const STAGE_DOING = dict({
  received: "يستلم…", clean: "ينظف…", classify: "يصنّف…", gate: "يصنّف…", recheck: "يراجع…",
  route: "يوجّه…", draft: "يكتب المسودة…", result: "يخلص…",
});
export const STAGE_ORDER = ["received", "clean", "classify", "gate", "recheck", "route", "draft", "result"];

// The reasons (server REASON_CODES) that are about a reply: offered only on a ticket that had a draft.
export const DRAFT_REASONS = new Set(["tone", "dialect", "asks_unneeded", "promise", "false_claim", "wrong_number",
  "missing_question", "shop_or_agent_name", "typo", "wrong_gender", "wrong_language"]);

// What the drafter is asked to request (draft.FIELD_AR).
export const FIELD_AR = dict({
  reference: "رقم العملية", amount: "المبلغ", date: "تاريخ ووقت العملية", recipient_number: "رقم المستلم",
  agent_location: "اسم الوكيل ومكانه", merchant: "اسم المتجر", bill_type: "نوع الفاتورة",
  phone_number: "الرقم اللي انشحن", screenshot: "صورة من الشاشة",
});

// What a draft check looks for, in a few words (the "nothing found" line names only the checks that ran).
export const CHECK_SHORT_AR = dict({
  stray_latin: "حروف إنكليزية", promise: "وعد بنتيجة أو وقت", asks_secret: "طلب رمز أو كلمة سر",
  unknown_number: "رقم مو بالتذكرة", hold_reason: "ذكر تحقيق أو اشتباه أو بلاغ", sensitive_number: "تكرار رقم بطاقة أو رمز",
  // The warnings from the 7 Nov role-played test sessions (always on since then), and from their second round.
  claims_done: "تگول شي انسوى", repeated_text: "ترحيب أو جملة مكررة", ask_missing: "ما تسأل عن كل اللي ناقص",
  dialect_words: "كلمة مو عراقية", amount_not_in_ticket: "مبلغ مو مثل ما كتبه الزبون",
  persona_slip: "تحجي بصيغة شخص واحد", asks_given: "تسأل عن شي الزبون كاتبه",
});

// What the agent checks before approving: what to look at ("ask"), and what the tick says once they
// did ("done"). A tick on a draft warning says the agent read it and keeps it on purpose; it never
// claims the opposite of what the check found.
const TYPE = { ask: "تأكد من نوع المشكلة", done: "تأكدت من نوع المشكلة" };
export const CONFIRM_AR = dict({
  recheck_used_second: TYPE,
  recheck_disagreed: TYPE,
  invalid_category: TYPE,
  "missing:reference": { ask: "تأكد إن الرد يطلب رقم العملية", done: "تأكدت إن الرد يطلب رقم العملية" },
  "missing:amount": { ask: "تأكد إن الرد يطلب المبلغ", done: "تأكدت إن الرد يطلب المبلغ" },
  ref_not_in_text: { ask: "تأكد من رقم العملية", done: "تأكدت من رقم العملية" },
  "draft:stray_latin": { ask: "راجع الحروف الإنكليزية بالمسودة", done: "راجعت الحروف الإنكليزية، وهي مقصودة" },
  "draft:promise": { ask: "راجع الوعد اللي بالمسودة", done: "راجعت الوعد، وهو مقصود" },
  "draft:unknown_number": { ask: "راجع الأرقام اللي بالمسودة", done: "راجعت الأرقام، وهي صحيحة" },
  "draft:claims_done": { ask: "راجع اللي تگول المسودة إنه انسوى", done: "راجعت، وهو صار فعلاً" },
  "draft:repeated_text": { ask: "راجع التكرار بالمسودة", done: "راجعت التكرار، وهو مقصود" },
  // ask_missing names its fields (askMissingAR): this is the wording when it names none.
  "draft:ask_missing": { ask: "المسودة ما تسأل عن كل اللي ناقص", done: "راجعت، وما يحتاج نسأل" },
  "draft:amount_not_in_ticket": { ask: "قارن المبلغ اللي بالمسودة بالرسالة", done: "قارنت المبلغ بالرسالة" },
  "draft:asks_given": { ask: "المسودة تسأل عن شي الزبون كاتبه بالرسالة", done: "راجعت السؤال، وهو مقصود" },
  draft_for_other_type: { ask: "المسودة انكتبت لنوع ثاني، راجع إنها تناسب النوع اللي اخترته",
    done: "راجعت إن المسودة تناسب النوع اللي اخترته" },
  // Only the team changed: the same point (logged as draft_for_other_type), said about the team.
  draft_for_other_team: { ask: "المسودة انكتبت لقسم ثاني، راجع إنها تناسب القسم اللي اخترته",
    done: "راجعت إن المسودة تناسب القسم اللي اخترته" },
  // The customer asked a second thing (extraction.secondary_subcategory): nobody is routed to it.
  second_request: { ask: "بالتذكرة طلب ثاني محد مستلمه، راجع شنو يكول الرد عنه", done: "راجعت شنو يكول الرد عن الطلب الثاني" },
  // A blocked account or a SIM change (run.py ACCOUNT_RISK): the draft stays; identity comes first. No
  // "before" here: the box is titled «قبل لا تعتمد:» when it lists more than one point.
  account_risk: { ask: "تأكد من هوية الزبون حسب الإجراءات", done: "تأكدت من هوية الزبون" },
  // The code rules on the customer's text (run.py, each behind its flag). The reply is how the customer
  // hears it, so the tick is about the reply.
  secret_in_ticket: { ask: "تأكد إن الرد ينبّه الزبون يغيّر الرمز ويوقف البطاقة", done: "تأكدت إن الرد ينبّه الزبون يغيّر الرمز ويوقف البطاقة" },
  bidi_controls: { ask: "قارن المبلغ والأرقام بالرسالة", done: "قارنت المبلغ والأرقام بالرسالة" },
  amount_disagreed: { ask: "تأكد من المبلغ بالرسالة", done: "تأكدت من المبلغ" },
  other_phone: { ask: "الزبون يكتب من رقم مو رقمه، تأكد من هويته", done: "تأكدت من هوية الزبون" },
  complaint_risk: { ask: "الزبون يهدد بشكوى أو راسلنا أكثر من مرة، راجع الرد بانتباه", done: "راجعت الرد بانتباه" },
  // A fraud escalation forwarded to another team than fraud (the server wants this tick: fraud_team_changed).
  fraud_team_changed: { ask: "هاي تذكرة احتيال، وراح تحوّلها لقسم ثاني", done: "متأكد أحوّل تذكرة احتيال لقسم ثاني" },
});
// What the customer wrote (result.secret_kinds, from the secret_forms rule) and what to tell them: a card number or its
// code means the card; a PIN means the PIN; a one-time code only matters if shared. Without kinds: one sentence for all.
const SECRET_WHAT = dict({ card: "رقم بطاقته", cvv: "الرمز اللي ورا البطاقة", pin: "رمزه السري", otp: "رمز تحقق" });
const SECRET_DO = dict({ card: "يوقف البطاقة", cvv: "يوقف البطاقة", pin: "يغيّر رمزه السري", otp: "ما يشارك الرمز ويا أي أحد" });
export function secretAdviceAR(kinds) {
  const ks = (kinds || []).filter((k) => SECRET_WHAT[k]);
  if (!ks.length) return { why: WHY_AR.secret_in_ticket, ...CONFIRM_AR.secret_in_ticket };
  const what = ks.map((k) => SECRET_WHAT[k]).join(" و");
  const todo = [...new Set(ks.map((k) => SECRET_DO[k]))].join(" و");
  return { why: `الزبون كتب ${what}. نبّهه ${todo}، ولا تكرر الرقم بالرد.`,
    ask: `تأكد إن الرد ينبّه الزبون ${todo}`, done: `تأكدت إن الرد ينبّه الزبون ${todo}` };
}
// Why complaint_risk fired (result.complaint_reasons, from the complaint_reasons rule).
const COMPLAINT_WHY = dict({ threat: "الزبون يهدد بشكوى علينا أو للجهات الرقابية", repeat: "الزبون راسلنا قبل وما وصله رد" });
export function complaintAR(reasons) {
  const said = (reasons || []).map((r) => COMPLAINT_WHY[r]).filter(Boolean);
  if (!said.length) return { why: WHY_AR.complaint_risk, ...CONFIRM_AR.complaint_risk };
  return { why: `${said.join("، و")}.`, ask: `${said.join("، و")}، راجع الرد بانتباه`, done: "راجعت الرد بانتباه" };
}
// The fields an ask_missing warning names (draft_check.ask_missing_fields), as its point: FIELD_AR labels,
// and reference_lost (the customer lost the receipt, and the draft asks them for its reference) apart.
export function askMissingAR(fields) {
  const named = (fields || []).filter((f) => f !== "reference_lost").map((f) => FIELD_AR[f] || f);
  const lost = (fields || []).includes("reference_lost");
  if (!named.length && !lost) return CONFIRM_AR["draft:ask_missing"];
  const ask = [named.length ? `المسودة ما تسأل عن: ${named.join("، ")}` : null,
    lost ? "الزبون ضيّع الوصل، والمسودة تطلب منه رقم العملية" : null].filter(Boolean).join(". ");
  const done = !lost ? CONFIRM_AR["draft:ask_missing"].done : named.length ? "راجعت الأسئلة اللي بالمسودة" : "راجعت طلب رقم العملية، وهو مقصود";
  return { ask, done };
}
// A style note (meta.style_kinds: dialect_words, persona_slip) is one muted line under the draft, never a point to tick:
// friction follows risk, and a tick for a style point teaches agents to tick without reading. It names the words.
export function styleNoteAR(findings) {
  const said = (findings || []).map((f) => {
    const words = Array.isArray(f.words) && f.words.length ? f.words : f.text ? [f.text] : [];
    const quoted = words.map((w) => `«${w}»`).join("، ");
    if (f.kind === "dialect_words") return `${words.length > 1 ? "كلمات" : "كلمة"} مو عراقية${quoted ? `: ${quoted}` : ""}`;
    if (f.kind === "persona_slip") return `الرد يحجي بصيغة المفرد${quoted ? `: ${quoted}` : ""}`;
    return null;
  }).filter(Boolean);
  return said.length ? `ملاحظة صياغة: ${said.join(" · ")}` : "";
}
// A quiet flag (meta.quiet_flags) is a muted note under the summary, never a point to tick.
export const QUIET_AR = dict({ instructions_in_ticket: "بالتذكرة كلام موجّه للنظام، وما انعمل بيه" });
// The reveal of a card number or a code the customer wrote (result.secret_spans), hidden by default.
export const SECRET_MASK = "••••";
export const SECRET_SHOW_AR = "اظهر الرقم";
export const SECRET_HIDE_AR = "اخفي الرقم";
export const CONFIRM_OTHER = { ask: "اقرا الملاحظة اللي فوق", done: "قريت الملاحظة" };
// A missing field the agent marked as not needed for this ticket (logged as missing:<field>:not_needed).
export const NOT_NEEDED_AR = "ما يحتاج بهالتذكرة";
export const notNeededAR = (field) => ({ ask: `${field}: ${NOT_NEEDED_AR}`, done: `راجعت: ${field} ${NOT_NEEDED_AR}` });
// The one tick when the identity check is among several points: it names the attestation first.
export const TICK_IDENTITY_AND_REST = "تأكدت من هوية الزبون وراجعت باقي النقاط";
export const TICK_ALL = "راجعت كل النقاط فوق";
// An escalated ticket where a model said blocked account or SIM change: whoever replies checks identity.
export const IDENTITY_IF_REPLY_AR = "إذا رديت على الزبون، تأكد من هويته حسب الإجراءات أول، ولا تكتب بالرد إنه صار أي تغيير على الحساب.";

// One sentence per flag for the line at the top of a ticket: why it is not ready, with no "title:"
// chained in front of another colon. A flag missing here falls back to the server's wording.
export const WHY_AR = dict({
  recheck_used_second: "النموذجين اختلفوا بنوع المشكلة، تأكد من النوع.",
  recheck_disagreed: "النموذجين اختلفوا بنوع المشكلة، فيستلمها موظف.",
  invalid_category: "التصنيف ما يطابق قائمة الأقسام. تأكد من النوع.",
  "missing:reference": "رقم العملية ناقص. تأكد إن الرد يطلبه.",
  "missing:amount": "المبلغ ناقص. تأكد إن الرد يطلبه.",
  ref_not_in_text: "رقم العملية اللي طلع مو موجود بنص التذكرة. تأكد منه.",
  pipeline_off: "النظام موقف، فالتذكرة يستلمها موظف بدون نموذج.",
  too_long: "التذكرة أطول من الحد المسموح، فيستلمها موظف بدون نموذج.",
  drafts_off: "المسودات موقفة، فالرد عليك.",
  cancelled: "انلغت المعالجة قبل ما تكمل.",
  internal_error: "صار خطأ داخلي، فيستلمها موظف.",
  model_error: "صار خطأ بالنموذج، فيستلمها موظف.",
  account_risk: "حساب مقفول أو تبديل شريحة. تأكد من هوية الزبون حسب الإجراءات قبل لا تعتمد، ولا تكتب بالرد إنه صار أي تغيير على الحساب.",
  connection_lost: "انقطع الاتصال قبل ما تخلص المعالجة.",
  device_lost: "الموبايل ضايع أو مسروق والمحفظة مفتوحة عليه، فيستلمها قسم الاحتيال.",
  budget_reached: "وصل التشغيل لحد الصرف المسموح، فيستلمها موظف.",
  second_request: "بالتذكرة طلب ثاني محد مستلمه، راجع شنو يكول الرد عنه.",
  secret_in_ticket: "الزبون كتب رقم بطاقة أو رمز سري. نبّهه يغيّر الرمز ويوقف البطاقة، ولا تكرر الرقم بالرد.",
  amount_disagreed: "النموذجين قروا مبلغ مختلف، تأكد من المبلغ بالرسالة.",
  complaint_risk: "الزبون يهدد بشكوى للجهات الرقابية أو راسلنا أكثر من مرة.",
});
// The same flags on an escalation, where nobody approves a reply: what the receiving team does about it.
export const WHY_ESC_AR = dict({
  "missing:reference": "رقم العملية ناقص، القسم يطلبه من الزبون.",
  "missing:amount": "المبلغ ناقص، القسم يطلبه من الزبون.",
  secret_in_ticket: "الزبون كتب رقم بطاقة أو رمز سري. القسم ينبّهه، ولا أحد يكرر الرقم.",
});
// Why a stage did not run, as the end of «ما انرسلت لنموذج لأن …» (no colon inside).
export const BECAUSE_AR = dict({
  pipeline_off: "النظام موقف", too_long: "التذكرة أطول من الحد المسموح", drafts_off: "المسودات موقفة",
  cancelled: "المعالجة انلغت", fraud: "احتمال احتيال",
  recheck_disagreed: "النموذجين اختلفوا", model_error: "صار خطأ بالنموذج", internal_error: "صار خطأ داخلي",
  budget_reached: "وصل التشغيل لحد الصرف المسموح", device_lost: "الموبايل ضايع والمحفظة مفتوحة",
});
// A blocking check, as the reason approve is off: what is wrong, then what to do (one instruction).
export const BLOCK_AR = dict({
  asks_secret: "المسودة تطلب رمز أو كلمة سر من الزبون. شيل هالطلب حتى تكدر تعتمدها.",
  hold_reason: "المسودة تذكر تحقيق أو اشتباه أو بلاغ، وممنوع نخبر الزبون بهيج شي. شيل هالكلام حتى تكدر تعتمدها، وإذا تقصد شكوى الزبون اكتب «سجلنا طلبك».",
  sensitive_number: "المسودة تكرر رقم بطاقة أو رمز. احذفه حتى تكدر تعتمدها.",
});

// Process mode: the stages as the trace shows them.
export const STAGES = [
  ["received", "الاستلام", "rule", "التذكرة مثل ما كتبها الزبون"],
  ["clean", "التنظيف", "rule", "توحيد الأرقام والمسافات"],
  ["classify", "التصنيف والاستخراج", "classifier", "يحدد نوع المشكلة ويطلع رقم العملية والمبلغ"],
  ["gate", "بوابة الثقة", "rule", "يقرر: يكمل، ينراجع، أو يتصعّد"],
  ["recheck", "المراجعة الثانية", "rechecker", "نموذج ثاني يصنّف بدون ما يشوف الجواب الأول"],
  ["route", "التوجيه والأولوية", "rule", "القسم المسؤول ودرجة الاستعجال"],
  ["draft", "المسودة", "drafter", "رد مقترح، الموظف يعتمده أو يعدله"],
];
export const OUTCOME_AR = dict({ drafted: "جاهزة للاعتماد", flagged: "جاهزة، بس بيها نقطة تحتاج تأكيد", escalated: "متصعّدة: يستلمها موظف" });
export const OUTCOME_SHORT = dict({ drafted: "جاهزة", flagged: "تحتاج تأكيد", escalated: "متصعّدة" });
export const DECISION_AR = dict({ pass: "يكمل للتوجيه والمسودة", recheck: "يروح للمراجعة الثانية", escalate: "يتصعّد لموظف" });
export const CHANGE_AR = dict({ arabic_digits: "رقم عربي تحوّل", tatweel: "تطويل انشال", extra_spaces: "مسافة زايدة",
  format_chars: "رمز مخفي انشال" });
export const DIFF_AR = dict({ easy: "سهلة", medium: "متوسطة", hard: "صعبة" });
// The gold tags of a synthetic ticket ("كيف يشتغل" only).
export const TAG_AR = dict({
  baghdadi: "بغدادية", southern: "جنوبية", mosuli: "موصلية",
  short: "قصيرة", long: "طويلة", typos: "بيها أغلاط إملائية", mixed_english: "بيها كلمات إنكليزية",
  voice_note_style: "مثل رسالة صوتية", voice_note: "مثل رسالة صوتية", arabizi: "عربيزي",
  off_topic: "برا الموضوع", negation: "بيها نفي", missing_or_fake_reference: "رقم عملية ناقص أو مزيّف",
  two_issues: "مشكلتين", prompt_injection: "تحاول توجّه النموذج", fraud_hidden_second: "احتيال مخفي كمشكلة ثانية",
  phone_instead_of_reference: "رقم هاتف بدل رقم العملية", usd_amount: "مبلغ بالدولار", amount_slang: "مبلغ بالعامية",
});
// Why live runs are off, for "كيف يشتغل" (the agent sees one plain sentence).
export const LIVE_CAUSE_AR = dict({
  pipeline_off: "PIPELINE_MODE=off", bad_backend: "LLM_BACKEND", no_key: "ماكو مفتاح API", no_cli: "أداة claude مو موجودة",
});
// The new-ticket dialog, under the agent's sentence: what turns live runs on, for whoever runs the server.
export const LIVE_TURN_ON_AR = dict({
  no_key: "يشتغل لما يكون عند الخادم مفتاح API.",
  no_cli: "يشتغل لما تكون أداة claude موجودة على الخادم.",
  bad_backend: "يشتغل لما يكون LLM_BACKEND صحيح على الخادم.",
});
