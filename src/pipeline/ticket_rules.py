"""Code rules that read the customer's text for a risk the models can miss. Each was a flag in fixes.py
until 7 Nov, when they became the normal code; run.py decides what a match does.

The rules read the ticket folded (clean.fold: ASCII digits, no harakat or invisible characters, Persian
letters as Arabic), so «الرمز السرّي» or a zero-width space inside a word reads as the plain word. Line
breaks are kept, so "SYSTEM:" at the start of a line is still at the start of a line.
"""

from __future__ import annotations

import re

from . import clean
from .clean import _TICKET_TAG, fold, sensitive_numbers

# --- secret_in_ticket: a card number or a code the customer wrote ---

# The page shows the customer's message without direction controls and marks (app/static/js/util.js
# plainText), so secret_spans point into that string, counted in UTF-16 code units as JavaScript does.
_PAGE_DROPS = re.compile("[‪-‮⁦-⁩‎‏]")
BIDI_CONTROLS = re.compile("[‪-‮⁦-⁩]")


def shown_text(raw: str) -> str:
    """The customer's message as the page shows it under «رسالة الزبون»."""
    return _PAGE_DROPS.sub("", raw)


def _utf16(text: str, i: int) -> int:
    return i + sum(1 for c in text[:i] if ord(c) > 0xFFFF)


def secret_spans(raw: str) -> list[list[int]]:
    """[start, end] of each card number or code (clean.sensitive_numbers) in shown_text(raw), in UTF-16
    code units, so the page can hide it in «رسالة الزبون»."""
    shown = shown_text(raw)
    return [[_utf16(shown, s), _utf16(shown, e)] for s, e, _ in sensitive_numbers(shown)]


def secret_kinds(raw: str) -> list[str]:
    """What the customer wrote (clean.secret_kinds: "card", "cvv", "pin", "otp"), so the advice can name it."""
    return clean.secret_kinds(shown_text(raw))


def secret_digits(raw: str) -> list[str]:
    """The digits of each card number or code in the ticket, so a note that writes one again can hide it."""
    shown = shown_text(raw)
    return list(dict.fromkeys(re.sub(r"\D", "", fold(shown[s:e])[0]) for s, e, _ in sensitive_numbers(shown)))


# --- device_lost: a lost or stolen phone with the wallet open on it; other_phone ---

_PHONE = r"(?:[وب]?(?:ال)?(?:موبايل|مبايل|تلفون|تليفون|جوال|هاتف|ايفون|آيفون)(?:ي|ه|ها)?)"
_LOST = (r"(?:ضاع|ضاعت|ضايع|ضيعت\w*|انسر[قگك]\w*|سر[قگك](?:و|وا|وه|ولي|ته)|انبا[كگ]\w*|با[كگ](?:وه|ولي)"
         r"|انفقد\w*|فقدت\w*|نشلو\w*|طاح\s+مني|lost|stolen)")
_LOST_PHONE = re.compile(rf"(?<!\w){_PHONE}(?:\s+\S+){{0,4}}?\s+{_LOST}(?!\w)|(?<!\w){_LOST}(?:\s+\S+){{0,4}}?\s+{_PHONE}(?!\w)",
                         re.IGNORECASE)
_APP = r"(?:[وب]?(?:ال)?(?:محفظ[ةه]|حساب|تطبيق|برنامج|ابلكيشن)\w*)"
_OPEN_WORD = r"(?:مفتوح[ةه]?|فاتح[ةه]?|مسجل\s+دخول|logged\s+in)"
_OPEN = re.compile(
    rf"(?<!\w){_APP}(?:\s+\S+){{0,3}}?\s+{_OPEN_WORD}(?!\w)|(?<!\w){_OPEN_WORD}(?:\s+\S+){{0,3}}?\s+{_APP}(?!\w)"
    r"|(?:ما\s+(?:عليه|بيه|عليها|بيها)|بلا|بدون)\s+(?:اي\s+)?(?:قفل|رمز|باسورد|بصم[ةه])", re.IGNORECASE)
_RELATIVE = r"(?:ال)?(?:اخت|اخو|ام|اب|ابو|ابن|بنت|زوج|مرت|صديق|صاحب|جار|عم|خال|رفيق|واحد|غير|ثاني)\w*"
_OTHER_PHONE = re.compile(
    r"(?<!\w)[وف]?(?:احجي|احچي|اكتب|اراسل|اتواصل|اتصل|احاكي|اكلم|ادز)\w*(?:\s+\S+){0,3}?\s+من\s+"
    rf"(?:{_PHONE}|رقم|خط)\s+{_RELATIVE}")


# Second round of role-played test sessions (device_lost_negation, adopted 7 Nov): «المحفظة مو مفتوحة عليه», «الحساب ما مفتوح عليه» say it is not open.
_NOT_OPEN = re.compile(r"(?<!\w)(?:مو|ما|مش|مب|غير|بدون|ليس|ليست)\s+$")


def _wallet_open(text: str) -> bool:
    for m in _OPEN.finditer(text):
        word = re.search(_OPEN_WORD, m.group())
        if word and _NOT_OPEN.search(text[:m.start() + word.start()]):
            continue
        return True
    return False


def device_lost(raw: str) -> bool:
    text = fold(raw)[0]
    return bool(_LOST_PHONE.search(text) and _wallet_open(text))


def other_phone(raw: str) -> bool:
    """The customer says they write from someone else's phone or number («احجي من تلفون اختي»)."""
    return bool(_OTHER_PHONE.search(fold(raw)[0]))


# --- complaint_risk: a regulator threat or a repeat contact (no priority change) ---

# Second round of role-played test sessions (complaint_reasons, adopted 7 Nov): the regulator words count only near a threat or complaint verb
# («حسب تعليمات البنك المركزي» is a mention, not a threat), and a repeat contact said other ways counts: «صارت ساعة من
# كتبتلكم», «راسلتكم قبل وكالولي ننتظر», «ثلث ايام وماحد يرد».
_REGULATOR = r"(?:(?:ال|لل|بال|ل|ب)?(?:بنك|مصرف)\s+(?:ال)?مركزي|(?:ال|لل|بال|ل|ب)?جه(?:ات|[ةه])\s+(?:ال)?رقابي[ةه]?)"
_THREAT_VERB = (r"(?:[اأ]شتكي|[اأ]شكي|نشتكي|شكو[ىاه]|[اأ]قدم|[اأ]رفع|[اأ]بلغ|[اأ]روح|[اأ]راجع|[اأ]كتب|[اأ]راسل"
                r"|[اأ]وصل|[اأ]حجي|[اأ]تصل|بلاغ|دعو[ىاه])\w*")
_THREAT_NEAR = re.compile(rf"(?<!\w)[وف]?{_THREAT_VERB}(?:\s+\S+){{0,4}}?\s+{_REGULATOR}(?!\w)"
                          rf"|(?<!\w){_REGULATOR}(?:\s+\S+){{0,2}}?\s+[وف]?(?:{_THREAT_VERB})(?!\w)")
_WROTE = r"(?:كتبت|راسلت|اتصلت|حجيت|حاجيت|كلمت|دزيت)(?:لكم|كم|بيكم|وياكم|عليكم)?"
_REPEAT = re.compile(
    rf"(?<!\w)(?:صار(?:ت|لي)?|[إا]لي|لي)\s+(?:\S+\s+)?(?:ساع[ةه]|ساعتين|ساعات|يوم|يومين|[اأ]يام|[اأ]سبوع|[اأ]سبوعين|شهر)"
    rf"\s+(?:\S+\s+)?(?:من\s+)?(?:ما\s+)?{_WROTE}(?!\w)"
    rf"|(?<!\w)[و]?{_WROTE}\s+(?:\S+\s+)?(?:قبل|من\s+قبل|سابقا|سابقاً|البارح[ةه]|امس|[أا]مس)(?!\w)"
    r"|(?<!\w)(?:ساع[ةه]|ساعتين|ساعات|يوم|يومين|[اأ]يام|[اأ]سبوع)\s+(?:\S+\s+)?و?(?:ماحد|محد|ما\s+احد|ما\s+أحد)\s+(?:يرد|رد|جاوب|يجاوب)")
_REPEAT_OLD = re.compile(
    r"(?<!\w)(?:ثالث|رابع|خامس|عاشر)[ةه]?\s+مر[ةه](?!\w)"
    r"|(?<!\w)(?:لل|ال)مر[ةه]\s+(?:ال)?(?:ثالث|رابع|خامس|عاشر)[ةه]?(?!\w)"
    r"|(?<!\w)[و]?(?:اتصل|راسل|اراسل|كتب|اكتب|حجي|احجي)\w*(?:\s+\S+){0,2}?\s+"
    r"(?:ثلث|ثلاث|اربع|خمس|ست|سبع|عشر|هواي|هوايه|هواية|عدة|[3-9]|\d\d)\s*مرات"
    r"|(?<!\w)صارلي\s+(?:[^\s.،,!?؟]+\s+){1,2}?(?:اكتبلكم|اراسلكم|اتصل\w*|اراجع\w*|احاكي\w*)")
_THREAT_OLD = re.compile(
    r"(?<!\w)[ولف]{0,2}[اأ]شتكي\s+(?:عليكم|عليك|ضدكم)"
    r"|(?<!\w)(?:[اأ]قدم|[اأ]رفع|اسجل|اسوي)\s+(?:عليكم\s+|ضدكم\s+)?(?:شكو[ىاه]|دعو[ىاه]|قضي[ةه])\s+(?:عليكم|ضدكم)"
    r"|(?<!\w)(?:[اأ]رفع|اسوي)\s+(?:عليكم|ضدكم)\s+(?:شكو[ىاه]|دعو[ىاه]|قضي[ةه])")


def complaint_reasons(raw: str) -> list[str]:
    """Why complaint_risk fires: "threat" (a complaint against us, or to the regulator with a verb that threatens
    it), "repeat" (the customer wrote or called before)."""
    text = fold(raw)[0]
    out = []
    if _THREAT_OLD.search(text) or _THREAT_NEAR.search(text):
        out.append("threat")
    if _REPEAT_OLD.search(text) or _REPEAT.search(text):
        out.append("repeat")
    return out


def complaint_risk(raw: str) -> bool:
    return bool(complaint_reasons(raw))


# --- instructions_in_ticket: text aimed at the system, not at a person (a quiet flag) ---

_INSTRUCTIONS = re.compile(
    r"^[ \t\[#<(*]*(?:system|assistant|developer)[ \t\]>)*]*:"
    r"|\bignore\s+(?:all\s+|any\s+)?(?:the\s+|your\s+)?(?:previous|prior|above|earlier)\s+(?:instructions|prompts?|rules|messages)"
    r"|\bdisregard\s+(?:all\s+|the\s+|your\s+)?(?:previous\s+|prior\s+|above\s+)?(?:instructions|prompts?|rules)"
    r"|\bsystem\s+prompt\b"
    r"|(?:تجاهل|انسى|انسوا|اهمل)\w*\s+(?:كل\s+|جميع\s+)?(?:ال)?(?:تعليمات|اوامر|أوامر|قواعد|توجيهات)"
    r"|(?:اكتب|كول|گول|قول|ردوا?)(?:وا)?\s+(?:لل|ل)زبون"
    r"|(?<!\w)[و]?اكتب(?:وا)?\s+(?:\S+\s+)?بالرد"
    r"|ملاحظ[ةه]\s+للنظام|(?<!\w)(?:الى|إلى|الي)?\s*(?:لل|ال)نظام\s*:"
    r"|مصنف[ةه]\s+مسبق",
    re.IGNORECASE | re.MULTILINE)


def instructions_in_ticket(raw: str) -> bool:
    return bool(_TICKET_TAG.search(raw) or _INSTRUCTIONS.search(fold(raw)[0]))
