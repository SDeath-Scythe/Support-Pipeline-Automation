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

// A row's status: an icon and a word, never colour alone.
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

// The live row while a ticket goes through: what is happening now.
export const STAGE_DOING = dict({
  received: "يستلم…", clean: "ينظف…", classify: "يصنّف…", gate: "يصنّف…", recheck: "يراجع…",
  route: "يوجّه…", draft: "يكتب المسودة…", result: "يخلص…",
});
export const STAGE_ORDER = ["received", "clean", "classify", "gate", "recheck", "route", "draft", "result"];

// What the drafter is asked to request (draft.FIELD_AR).
export const FIELD_AR = dict({
  reference: "رقم العملية", amount: "المبلغ", date: "تاريخ ووقت العملية", recipient_number: "رقم المستلم",
  agent_location: "اسم الوكيل ومكانه", merchant: "اسم المتجر", bill_type: "نوع الفاتورة",
  phone_number: "الرقم اللي انشحن", screenshot: "صورة من الشاشة",
});

// What a draft check looks for, in a few words (the "nothing found" line names only the checks that ran).
export const CHECK_SHORT_AR = dict({
  stray_latin: "حروف إنكليزية", promise: "وعد بنتيجة أو وقت", asks_secret: "طلب رمز أو كلمة سر",
  unknown_number: "رقم مو بالتذكرة", hold_reason: "ذكر تحقيق أو بلاغ", sensitive_number: "تكرار رقم بطاقة أو رمز",
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
  draft_for_other_type: { ask: "المسودة انكتبت لنوع ثاني، راجع إنها تناسب النوع اللي اخترته",
    done: "راجعت إن المسودة تناسب النوع اللي اخترته" },
});
export const CONFIRM_OTHER = { ask: "اقرا الملاحظة اللي فوق", done: "قريت الملاحظة" };

// One sentence per flag for the line at the top of a ticket: why it is not ready, with no "title:"
// chained in front of another colon. A flag missing here falls back to the server's wording.
export const WHY_AR = dict({
  recheck_used_second: "النموذجين اختلفوا بنوع المشكلة واعتمدنا جواب المراجعة الثانية. تأكد من النوع.",
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
  account_risk: "حساب محظور أو تبديل شريحة، فيستلمها موظف بدون مسودة.",
  connection_lost: "انقطع الاتصال قبل ما تخلص المعالجة.",
});
// Why a stage did not run, as the end of «ما انرسلت لنموذج لأن …» (no colon inside).
export const BECAUSE_AR = dict({
  pipeline_off: "النظام موقف", too_long: "التذكرة أطول من الحد المسموح", drafts_off: "المسودات موقفة",
  cancelled: "المعالجة انلغت", fraud: "احتمال احتيال", account_risk: "حساب محظور أو تبديل شريحة",
  recheck_disagreed: "النموذجين اختلفوا", model_error: "صار خطأ بالنموذج", internal_error: "صار خطأ داخلي",
});
// A blocking check, as the reason approve is off: what is wrong, then what to do (one instruction).
export const BLOCK_AR = dict({
  asks_secret: "المسودة تطلب رمز أو كلمة سر من الزبون. شيل هالطلب حتى تكدر تعتمدها.",
  hold_reason: "المسودة تذكر تحقيق أو اشتباه أو بلاغ، وممنوع نخبر الزبون. شيلها حتى تكدر تعتمدها.",
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
export const CHANGE_AR = dict({ arabic_digits: "رقم عربي تحوّل", tatweel: "تطويل انشال", extra_spaces: "مسافة زايدة" });
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
