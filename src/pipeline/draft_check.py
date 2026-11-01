"""F2 (draft_check): rule checks on a draft before an agent sees it.

The drafter prompt already forbids these; the rules catch the cases where it slips.
A draft with a problem is still shown, but flagged with the reason. findings() also says where in
the draft each problem is, so the viewer can highlight it.

The rules read the draft folded (clean.fold: ASCII digits, no tatweel, harakat or invisible
characters), so «الرّمز» or a ZWNJ inside a word reads as the plain word; spans point into the draft
as written.
"""

from __future__ import annotations

import re

from . import fixes
from .clean import CREDENTIAL, clean, fold, sensitive_numbers

KINDS = ("stray_latin", "promise", "asks_secret", "unknown_number", "hold_reason", "sensitive_number")

# Arabic letters only: not punctuation ("،" "؟" "؛"), digits or tatweel ("بالـcard"), which can
# sit next to an English word the customer used (the API pilot flagged "declined،").
_AR = "ء-ؿف-يٮ-ۓ"

# A Latin letter glued to an Arabic one, e.g. "hلا".
_GLUED = re.compile(rf"[A-Za-z][{_AR}]|[{_AR}][A-Za-z]")
_LATIN_WORD = re.compile(r"[A-Za-z]+")
# Latin words a draft may use even if the customer did not.
_LATIN_OK = {"otp", "pin", "qr", "sms", "iqd", "usd", "app"}

# Promises of an outcome or a time. "خلال" + a time unit is only allowed if it is a known fact.
# "راح نرجع نخبرك" (we'll get back to you) is not a promise, so a return verb only counts
# with money near it, and not as "about the money" («راح نرجعلك بخصوص المبلغ»).
_MONEY = r"(فلوس|المبلغ|مبلغ|الرصيد|المصاري|رسوم|الرسوم|العمولة|عمولة|الفرق)"
_ABOUT = r"(?!(?:بخصوص|عن|حول|بشأن|بموضوع|على)\s)"
_PROMISES = [
    rf"{_MONEY}\S*\s+(\S+\s+){{0,2}}?راح\s+(ت|ي)(?:رجع|نعاد|نضاف)",
    rf"راح\s+(ن|ت|ي)رجع\S*\s+({_ABOUT}\S+\s+){{0,2}}?{_MONEY}",
    rf"(ن|ت)رجعل\S*\s+({_ABOUT}\S+\s+)?{_MONEY}",
    rf"نعيد\S*\s+(\S+\s+)?{_MONEY}",
    r"راح\s+(?:يتم\s+)?(?:استرجاع|استرداد|[اإ]رجاع)\s+(?:ال)?(?:مبلغ|فلوس|رسوم|عمول)",
    r"راح\s+(?:ت|ن)سترد|راح\s+(?:يتم\s+)?(?:تعويض|تتعوض)",
    r"(?:ينضاف|نضيف)\w*\s+(?:ال)?(?:رصيد|مبلغ|فلوس)",
    r"نعوض",
    # «حتى نضمن أمان حسابك» is a reason, «طريقة مضمونة هي» a fact, «أكيد راح نساعدك» a courtesy.
    r"(?<!حتى )(?<!لكي )نضمن(?!\s+(?:ال)?(?:[أا]مان|سلام[ةه]|حماي[ةه]))",
    r"(?<!\w)مضمون(?!ة\s+هي)",
    r"(?<!\w)[اأ]كيد\s+راح(?!\s+(?:ن|ي)?(?:ساعد|تابع|خدم|شوف|تواصل|رد|راجع))",
    r"راح (ت|ي)وصل(ك|ج|ه|ها)? خلال",
]
# «ما نكدر نضمن» / «ما راح نرجعلك فلوسك»: a promise word just after a negation is not a promise.
_NEG_BEFORE = {"ما", "مو", "لا", "ماكو", "محد", "مانكدر", "مانگدر", "مانقدر", "ماگدر", "ماكدر", "ماقدر"}
# The whole unit word is kept, so a policy «خلال يومين» doesn't allow a draft's «خلال يوم».
_UNIT = r"(?:دقيق|دقايق|ساع|يوم|[أا]يام|[أا]سبوع|[أا]سابيع|شهر|[أا]شهر)\w*"
_TIME = re.compile(rf"(?:خلال|بظرف|ظرف|بغضون|غضون|بحدود|[أا]قصاها|ما\s+ياخذ\s+[أا]كثر\s+من)\s+(?:\S+\s+)?{_UNIT}"
                   rf"|خلال\s+ال{_UNIT}\s+(?:ال)?(?:جاي|قادم|مقبل)\w*")
_ALEF = str.maketrans("أإآ", "ااا")

# --- asking for a secret: a request, then within a few words a secret, with no negation ---

# A secret is a credential word (clean.CREDENTIAL: رمز, كود, الرقم السري, كلمة السر, باسورد, OTP, PIN, ...)
# or one of these: a full card number, the digits on the back of the card, "the digits that reached you".
_SECRET_EXTRA = re.compile(
    r"(?<!\w)(?P<pfx>[وف]?(?:ال)?)(?:"
    r"رقم\s+(?:ال)?بطاق(?:[ةه]|ت(?:ك|ج|كم))(?!\w)"
    r"|[أا]رقام\s+(?:اللي\s+|الي\s+)?(?:ورا|خلف|ب?ظهر|على\s+ظهر)\s+(?:ال)?بطاق\w*"
    r"|[أا]رقام\s+(?:اللي|الي)\s+وصل\w*)")
# «آخر ٤ أرقام من البطاقة» is the safe way to find a card: «رقم البطاقة» after «آخر» is not the card.
_LAST = {"آخر", "اخر", "أخر"}
# A request is one of these kinds, matched on a word with one leading و/ف dropped:
# 1. send / give / share / tell, as an order or "you" form: دزلنا, تدزلي, ارسل, إرسال, ابعث, انطينا, عطينا,
#    أعطني, شاركنا, زودنا, تكتبلنا, حطلي, خبرنا, أكدلنا, راسلنا, قلي. Not "we/he" forms (ندزلك رمز جديد),
#    the past (دزيت، انطيت، شاركت، زودت) or "we did it for you" (دزينالك، انطيناك).
_SEND = re.compile(r"(?:ت?دز(?!يت)|(?:ا|أ|إ|ت)رسل(?!ت)|(?:ا|أ|إ|ت)بعث(?!ت)|اكتب|تكتب(?:لي|لنا|النا)"
                   r"|(?:ا|ت)?نطي(?!ت)|(?:ا|أ|إ|ت)?عطي(?!ت)|(?:ا|أ|إ)عط(?:ني|نا)|ت?شارك(?!ت)|ت?زود(?!ت)"
                   r"|(?:ب|ل)?(?:ا|إ)رسال|(?:ب|ل)?تزويد|(?:ب|ل)?مشارك[ةه]|(?:ا|أ)?خبر(?:ني|نا)(?!ك|ج|كم)"
                   r"|ت?(?:ا|أ)كد(?:لي|لنا)|راسل(?:ني|نا)|حطل(?:ي|نا|نه)(?!\w))")
_WE_DID = re.compile(r"نا(?:ل)?(?:ك|ج|كم)$|^دزينا$")
_TELL = {"قلي", "قلنا", "قولي", "قولنا", "گلي", "گلنا", "گولي", "گولنا", "گللي", "قللي", "قوليلي", "گوليلي",
         "خبرني", "خبرنا", "خبرنه"}
# 2. "you write" or "we know/see" only after a request word: «لازم تكتب الكود», «نحتاج نعرف الرمز»,
#    but not «فهمت إنك تكتب الرمز».
_SOFT = re.compile(r"تكتب")
_KNOW = {"نعرف", "نشوف", "ناخذ", "نستلم", "نحصل"}
_ASKING = {"لازم", "ممكن", "رجاء", "رجاءً", "ياريت", "نرجو", "نرجوك", "نحتاج", "نريد", "محتاجين", "تكدر",
           "تگدر", "تقدر", "يرجى"}
# 3. "we/I need" with the secret right after it: «نحتاج الرمز», «اريد منك الرمز» (not «نحتاج تغير الرمز»).
_NEED = ("نحتاج", "نريد", "محتاج", "احتاج", "أحتاج", "اريد", "أريد")
_FILLER = {"منك", "منج", "منكم", "بس", "هم", "همين", "رجاء", "رجاءً", "ايضا", "ايضاً", "أيضا", "أيضاً", "هسه",
           "هسة", "الحين"}
# 4. "what" with the secret right after it: «شنو الرمز اللي وصلك؟», Mosuli «ايش», southern «شني»
#    (not «شنو المشكلة بالرمز»).
_WHAT = {"شنو", "شنهو", "شنهي", "اشنو", "شنوه", "شكد", "شگد", "ايش", "إيش", "شني"}
# «شنو الكود اللي يطلعلك بالشاشة؟» asks for an error on screen; «نحتاج الرمز يوصلك أول» is about it arriving.
_ON_SCREEN = re.compile(r"\s+(?:اللي|الي)\s+(?:ي|ت)?(?:طلع|ظهر)")
_ARRIVES = re.compile(r"\s+(?:ي|ت)(?:وصل|جي)")
# «اكتب الرمز بالتطبيق»: typing the code into the app is an instruction, not a request to us.
_IN_APP = re.compile(r"(?<!\w)(?:بال|ب|في\s+(?:ال)?|داخل\s+(?:ال)?)(?:تطبيق|برنامج|خان[ةه]|شاش[ةه]|app)(?!\w)",
                     re.IGNORECASE)
# The secret first, then the request: «الكود اللي اجاك دزه النا», «إذا وصلك الرمز، دزه إلنا», «دزلي ياه».
_SEND_IT = re.compile(r"(?:ت?دز|(?:ا|أ|إ)رسل|(?:ا|أ|إ)بعث|(?:ا|ت)?نطي(?:ن|ني|نا)?|ت?شارك)(?:ه|ها|يا?ه|ياها|اه)"
                      r"(?:لنا|النا|لي)?")
_SEND_TO = re.compile(r"(?:ت?دز|(?:ا|أ|إ)رسل|(?:ا|أ|إ)بعث|(?:ا|ت)?نطي|حط)(?:لنا|لي|نا|ني)")
_IT = {"ياه", "اياه", "إياه", "ياها", "إلنا", "النا", "لنا"}
# Or with no verb: «ممكن الرمز اللي وصلك؟», «الرمز اللي وصلك شنو؟».
_TAIL = r"(?:\s+(?:اللي|الي)\s+\S+)?"
_POLITE_ASK = re.compile(r"\s*(?:ممكن|رجاء[ًا]?|ياريت|يا\s+ريت|لو\s+سمحت)\s+(?:منك\s+)?$")
_POLITE_TAIL = re.compile(_TAIL + r"\s*(?:لو\s+سمحت|مالتك|مالك)?\s*$")
_WHAT_TAIL = re.compile(_TAIL + r"\s+(?:هو\s+)?(?:شنو|شنهو|ايش|إيش|شني)\s*$")

# A negation is a whole word, not a prefix: «لازم» and «ماكو مشكلة» are not negations. «لا»/«ما» glued
# to a verb counts («لاتشارك», «ماتحتاج»); «ماكو/مافي/ماله» count only before داعي/حاجة («ماكو داعي تدزلنا»).
_NEGATIONS = {"لا", "ما", "مو", "بدون", "ممنوع", "أبد", "ابد", "أبدا", "ابدا", "أبداً", "ابداً", "ماراح", "مراح",
              "محد", "احذر", "حذاري", "تجنب", "اوعى", "اوعا", "إياك", "اياك", "بالك", "عدم", "يمنع"}
_GLUED_NEG = re.compile(r"(?:لا|ما)[تين]\w{2,}")
_NO_NEED = {"داعي", "حاجة", "حاجه", "ضرورة", "ضروره", "لزوم"}
# «لا تقلق، دزلنا الرمز» / «لا تنسى تدزلنا الرمز»: the negation belongs to the other verb.
_OTHER_VERB = {"تقلق", "تخاف", "تحاتي", "تنسى", "تنسا", "تتردد", "تشيل"}
# «بعد ما يوصلك دزلنا الرمز»: "ما" after these words means "when", not "not".
_MA_CONJ = {"بعد", "قبل", "كل", "مثل", "لحد", "لين", "الى", "إلى", "أول", "اول"}
# «ما عليك أمر», «ما قصرت», «اذا ما يخالف», «اذا ما عندك مانع» are Iraqi for "please", not negations.
_COURTESY = {"عليك", "عليج", "عليكم", "قصرت", "قصرتي", "قصرتوا", "يخالف"}
# «غير مسموح تدز الرمز» is a negation; «إذا الرمز غير صحيح دزلنا الجديد» is not.
_NOT_ALLOWED = {"مسموح", "مطلوب", "ضروري", "لازم"}
# Someone else's request, quoted in a warning: «أي شخص يطلب منك تدزله الرمز هو محتال», «لو أحد گالك انطيني
# الرمز». A past form always is; a present one («القسم يطلب منك ترسل الرمز») only with "if" or "anyone".
_REPORTED_PAST = {"طلب", "طلبوا", "گالك", "گلك", "قالك", "قلك", "كلك", "سألك"}
_REPORTED_NOW = {"يطلب", "يطلبون", "يطلبوا", "يطلبلك", "يگلك", "يقولك", "يقلك", "يكلك", "يگولك", "يسألك"}
_IF_OR_ANYONE = {"اذا", "إذا", "لو", "لما", "ان", "إن", "أي", "اي", "أحد", "احد", "واحد", "شخص", "حدا"}
_ASK_VERB = re.compile(r"(?:ن|ي)طلب\w*")

_CLAUSE = re.compile(r"[^.،,!?؟؛;\n]+")

# --- tipping-off (Iraq AML/CFT Law 39/2015): never tell a customer about an investigation, a
# suspicion, a report to an authority, compliance or monitoring. «بلاغك» / «البلاغ مالتك» (the
# customer's own complaint) and «إبلاغك» (we'll let you know) are not counted; «تجميد/مجمد» is left
# out because drafts restate a customer's "my account is frozen".
_HOLD = re.compile(
    r"(?<!\w)[وف]?(?:بال|لل|عال|ال|ب|ل|ك)?(?:"
    r"تحقيق\w*|[اإ]شتباه\w*|مشتبه\w*|مشبوه\w*|شبه[ةه](?!\w)|شبهات|مشكوك\w*|مريب\w*|شكوك\w*|امتثال"
    r"|(?:رفع|قدم|سجل)\w*\s+(?:\S+\s+)?(?:بلاغ|تقرير)\w*"
    r"|بلاغ(?:ات)?\s+(?:رسمي|ضد|بحق|عن(?:ك|ج|كم)(?!\w)|عن\s+حساب(?:ك|ج|كم)|على\s+حساب)"
    r"|(?:[أإا]?بلغنا|[إا]بلاغ)\s+(?:ال)?(?:جه(?:[ةه]|ات)|شرط[ةه]|سلط\w*|بنك\s+(?:ال)?مركزي)"
    r"|[إا]بلاغ\s+عن\s+(?:حساب|عملي|تحويل|حوال)\w*"
    r"|(?:تحت|قيد)\s+(?:ال)?مراقب[ةه]|(?:غس(?:ي)?ل|تبييض)\s+(?:ال)?[أاإ]موال|تمويل\s+(?:ال)?[إا]رهاب"
    r"|(?:مراجع[ةه]|تدقيق)\s+(?:ال)?[أا]مني[ةه]?|جه(?:[ةه]|ات)\s+(?:ال)?(?:رقابي|[أا]مني)[ةه]"
    r")|(?<![A-Za-z])AML(?![A-Za-z])", re.IGNORECASE)
# Safety advice: a suspicious link or call («لا تفتح روابط مشبوهة»), or the customer's own doubt
# («إذا عندك اشتباه بأي رسالة», «إذا شفت أي نشاط مشبوه بلغنا»), is not about the customer.
_SUSPICION = re.compile(r"[اإ]شتباه|مشبوه|مريب|شكوك|مشكوك|شبه")
_PHISH = {"رابط", "روابط", "رسالة", "رساله", "رسائل", "رسايل", "مسج", "مسجات", "اتصال", "اتصالات", "مكالمة",
          "مكالمه", "مكالمات", "رقم", "ارقام", "أرقام", "موقع", "مواقع", "صفحة", "صفحات", "تطبيق", "تطبيقات",
          "ملف", "ملفات", "اشخاص", "أشخاص", "جهات"}
_YOU_HAVE = {"عندك", "عندج", "عندكم"}
_IF = {"إذا", "اذا", "لو", "بحال", "حال"}
_NOTICE = {"شفت", "لاحظت", "حسيت", "تشوف", "تلاحظ", "صار", "وصلك", "وصلتك", "اتصل"}
# «لتحقيق رضاك» = to achieve, not an investigation.
_ACHIEVE = re.compile(r"\s*(?:ال)?(?:رضا|طلب|هدف|[أا]فضل|رغب)")

_NUMBER = re.compile(r"\d[\d,٬.]*\d|\d")
_THOUSAND_AFTER = re.compile(r"\s*(?:[أا]لف|آلاف|الاف)(?!\w)")
_MILLION_AFTER = re.compile(r"\s*مليون(?!\w)")


def _numbers(text: str) -> set[str]:
    return {re.sub(r"[,٬.]", "", n) for n in _NUMBER.findall(clean(text))}


def _normalise(text: str) -> tuple[str, list[int]]:
    """The draft as the rules read it, keeping where each character came from (see clean.fold)."""
    return fold(text)


def _raw(pos: list[int], start: int, end: int) -> tuple[int, int]:
    """A span in the normalised text, as a span in the draft as written."""
    return pos[start], pos[end - 1] + 1


def _whole_words(text: str, start: int, end: int) -> tuple[int, int]:
    """Widen a span to whole words ("فلوس" inside "الفلوس", "خلال يوم" of "خلال يومين"), for highlighting."""
    while start > 0 and not text[start - 1].isspace():
        start -= 1
    while end < len(text) and not (text[end].isspace() or text[end] in ".،,!?؟؛;:"):
        end += 1
    return start, end


def _squash(s: str) -> str:
    return " ".join(s.translate(_ALEF).split())


def _bare(token: str) -> str:
    token = token.strip("\"'«»()[]:،,")
    return token[1:] if token[:1] in "وف" and len(token) > 2 else token


# --- one function per rule: each returns the (start, end) of the first problem in the draft, or None ---

def _stray_latin(draft: str, allowed_text: str) -> tuple[int, int] | None:
    allowed = {w.lower() for w in _LATIN_WORD.findall(allowed_text)} | _LATIN_OK
    hits = [m.span() for m in _LATIN_WORD.finditer(draft) if m.group().lower() not in allowed][:1]
    glued = _GLUED.search(draft)
    if glued:
        hits.append(_whole_words(draft, *glued.span()))   # the whole word, "hلا"
    return min(hits, key=lambda h: (h[0], -h[1])) if hits else None


def _promise(draft: str, norm: str, pos: list[int], facts_text: str) -> tuple[int, int] | None:
    # A time is allowed only from the policy facts, never because the customer (or a line forged
    # inside the ticket) wrote it.
    time_ok = {_squash(m.group()) for m in _TIME.finditer(fold(clean(facts_text))[0])}
    hits = [_raw(pos, *m.span()) for m in (re.search(p, norm) for p in _PROMISES)
            if m and not _NEG_BEFORE & set(norm[:m.start()].split()[-3:])]
    hits += [_raw(pos, *m.span()) for m in _TIME.finditer(norm) if _squash(m.group()) not in time_ok][:1]
    return _whole_words(draft, *min(hits)) if hits else None


def _is_negation(words: list[str], k: int) -> bool:
    w, nxt, prev = words[k], words[k + 1] if k + 1 < len(words) else "", words[k - 1] if k else ""
    if w in {"لا", "ما"} and nxt in _OTHER_VERB:
        return False
    if w == "ما" and (prev in _MA_CONJ or nxt in _COURTESY or (nxt == "عندك" and words[k + 2:k + 3] == ["مانع"])):
        return False
    if w == "غير":
        return nxt in _NOT_ALLOWED
    if w in {"ماكو", "مافي", "ماله", "مالها", "مالهم"}:
        return nxt in _NO_NEED
    if w in _NEGATIONS:
        return True
    return (bool(_GLUED_NEG.fullmatch(w)) and not w.startswith(("لان", "مانع"))   # «لانه» = because
            and w[2:] not in _OTHER_VERB)


def _after_preposition(pfx: str) -> bool:
    """«شنو المشكلة بالرمز»: a secret after ب/ل is talked about, not asked for."""
    p = pfx.lstrip("وف").rstrip("ـ")
    return p.startswith("ب") or p in ("ل", "لل")


def _request_at(words: list[str], i: int, j: int, pfx: str, after: str) -> bool:
    """Is word i a request for the secret that starts at word j? `after` is the clause after the secret."""
    w, between = words[i], words[i + 1:j]
    if w.endswith("نا") and words[i + 1:i + 2] in (["لك"], ["الك"], ["إلك"], ["إليك"]):
        return False                                        # «ارسلنا لك رمز جديد»: we sent you
    if w in {"اكتب", "تكتب"} and _IN_APP.search(after):
        return False
    if (_SEND.match(w) and not _WE_DID.search(w)) or w in _TELL:
        return True
    before = words[max(0, i - 2):i]
    if _SOFT.match(w) or w in _KNOW:
        return (any(x in _ASKING for x in before) or before == ["يا", "ريت"]
                or (w in _KNOW and i > 0 and words[i - 1].startswith(_NEED) and not between))
    if w.startswith(_NEED):
        return len(between) <= 1 and all(x in _FILLER for x in between) and not _ARRIVES.match(after)
    if w in _WHAT:
        return all(x in {"هو", "هي"} for x in between) and not _after_preposition(pfx) and not _ON_SCREEN.match(after)
    return False


def _someone_else_asks(words: list[str], i: int) -> bool:
    """The request at word i is quoted, not made: «إذا أحد طلب منك تدز الرمز», «ما نطلب منك ... تدزلنا الرمز».
    The quoting verb must be within four words of the request («طلب» is also the noun "a request")."""
    before, near = words[:i], set(words[max(0, i - 4):i])
    if near & _REPORTED_PAST or (near & _REPORTED_NOW and _IF_OR_ANYONE & set(before)):
        return True
    return any(_ASK_VERB.fullmatch(x) and any(_is_negation(words, q) for q in range(max(0, k - 3), k))
               for k, x in enumerate(before))


def _secrets(text: str) -> list[tuple[int, int, str]]:
    found = [(m.start(), m.end(), m.group("pfx") or "") for m in CREDENTIAL.finditer(text)]
    for m in _SECRET_EXTRA.finditer(text):
        if not _LAST & {_bare(w) for w in text[:m.start()].split()[-4:]}:
            found.append((m.start(), m.end(), m.group("pfx") or ""))
    return sorted(found)


def _asks_secret(norm: str, pos: list[int]) -> tuple[int, int] | None:
    for clause in _CLAUSE.finditer(norm):
        text, base = clause.group(), clause.start()
        question = norm[clause.end():clause.end() + 1] in ("؟", "?")
        tokens = list(re.finditer(r"\S+", text))
        words = [_bare(t.group()) for t in tokens]
        for start, end, pfx in _secrets(text):
            head, tail = text[:start], text[end:]
            if ((question and _POLITE_ASK.fullmatch(head) and _POLITE_TAIL.fullmatch(tail))
                    or (_WHAT_TAIL.match(tail) and not _after_preposition(pfx) and not _ON_SCREEN.match(tail))):
                return _raw(pos, base + len(head) - len(head.lstrip()), base + end)
            j = next(k for k, t in enumerate(tokens) if t.start() <= start < t.end())
            for i in range(j - 1, max(-1, j - 5), -1):          # the request: at most three words before
                if _request_at(words, i, j, pfx, tail):
                    window = list(range(max(0, i - 4), i)) + list(range(i + 1, j))
                    if not (any(_is_negation(words, k) for k in window) or _someone_else_asks(words, i)):
                        return _raw(pos, base + tokens[i].start(), base + end)
                    break
    return None


def _asks_for_it(norm: str, pos: list[int]) -> tuple[int, int] | None:
    """The secret named first, then "send it" within six words, across a comma: «الكود اللي اجاك دزه النا»."""
    for sm in CREDENTIAL.finditer(norm):
        rest = norm[sm.end():]
        cut = re.search(r"[.!?؟;\n]", rest)
        tokens = list(re.finditer(r"\S+", rest[:cut.start() if cut else len(rest)]))[:6]
        words = [_bare(t.group()) for t in tokens]
        for k, w in enumerate(words):
            nxt = words[k + 1] if k + 1 < len(words) else ""
            if _SEND_IT.fullmatch(w) or (_SEND_TO.fullmatch(w) and nxt in _IT):
                if not any(_is_negation(words, x) for x in range(max(0, k - 3), k)):
                    return _raw(pos, sm.start(), sm.end() + tokens[k].end())
                break
    return None


def _unknown_number(norm: str, pos: list[int], allowed_text: str) -> tuple[int, int] | None:
    allowed = _numbers(allowed_text)
    thousands = {str(int(n) * 1000) for n in allowed if n.isdigit() and len(n) <= 4}
    if re.search(r"(^|\s)(ال|أل)ف(\s|$)", allowed_text):   # "الف وحدة" = 1,000 written as a word
        thousands.add("1000")
    for m in _NUMBER.finditer(norm):
        n = re.sub(r"[,٬]", "", m.group())
        if n.replace(".", "") in allowed | thousands:
            continue
        # «50 ألف» or «1.5 مليون» in the draft for a ticket that wrote 50000 or 1,500,000.
        scale = 1000 if _THOUSAND_AFTER.match(norm, m.end()) else 1_000_000 if _MILLION_AFTER.match(norm, m.end()) else 0
        if scale and re.fullmatch(r"\d+(?:\.\d+)?", n) and str(round(float(n) * scale)) in allowed:
            continue
        return _raw(pos, *m.span())
    return None


def _hold_reason(norm: str, pos: list[int]) -> tuple[int, int] | None:
    for m in _HOLD.finditer(norm):
        clause = re.split(r"[.،,!?؟؛;\n]", norm[:m.start()])[-1]
        before = [_bare(w) for w in clause.split()]
        prev = re.sub(r"^(?:بال|لل|ال|ب|ل)", "", before[-1]) if before else ""
        if _SUSPICION.search(m.group()) and (prev in _PHISH or _YOU_HAVE & set(before[-2:])
                                             or (before[:1] and before[0] in _IF and _NOTICE & set(before))):
            continue
        if "تحقيق" in m.group() and _ACHIEVE.match(norm, m.end()):
            continue
        return _raw(pos, *m.span())
    return None


def _sensitive_number(norm: str, pos: list[int]) -> tuple[int, int] | None:
    spans = sensitive_numbers(norm)
    return _raw(pos, spans[0][0], spans[0][1]) if spans else None


def findings(draft: str, allowed_text: str, facts_text: str = "") -> list[dict]:
    """Each problem kind found in `draft`, in KINDS order, with the span of its first occurrence:
    {"kind", "start", "end", "text"} where text == draft[start:end] (for highlighting), except that a
    sensitive_number's digits are given as "*": the span is saved with the run, and masking can't
    tell a bare code from any other number.

    `allowed_text` is everything the drafter was given (the ticket, extracted fields and known facts):
    words and numbers from it may appear in the draft. `facts_text` is the policy facts alone: a time
    («خلال يومين») is allowed only from there. hold_reason and sensitive_number run only when their
    fix flag is on (PIPELINE_FIXES).
    """
    norm, pos = _normalise(draft)
    spans = {
        "stray_latin": _stray_latin(draft, allowed_text),
        "promise": _promise(draft, norm, pos, facts_text),
        "asks_secret": _asks_secret(norm, pos) or _asks_for_it(norm, pos),
        "unknown_number": _unknown_number(norm, pos, allowed_text),
        "hold_reason": _hold_reason(norm, pos) if fixes.enabled("hold_reason") else None,
        "sensitive_number": _sensitive_number(norm, pos) if fixes.enabled("sensitive_number") else None,
    }
    out = [{"kind": k, "start": s[0], "end": s[1], "text": draft[s[0]:s[1]]} for k, s in spans.items() if s]
    for f in out:
        if f["kind"] == "sensitive_number":
            f["text"] = re.sub(r"\d", "*", f["text"])
    return sorted(out, key=lambda f: KINDS.index(f["kind"]))


def problems(draft: str, allowed_text: str, facts_text: str = "") -> list[str]:
    """The problem kinds found in `draft`, in KINDS order (see findings)."""
    return [f["kind"] for f in findings(draft, allowed_text, facts_text)]
