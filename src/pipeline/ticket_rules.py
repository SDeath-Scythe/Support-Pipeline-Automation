"""Code rules that read the customer's text for a risk the models can miss. Each was a flag in fixes.py
until 7 Nov, when they became the normal code; run.py decides what a match does.

The rules read the ticket folded (clean.fold: ASCII digits, no harakat or invisible characters, Persian
letters as Arabic), so «الرمز السرّي» or a zero-width space inside a word reads as the plain word. Line
breaks are kept, so "SYSTEM:" at the start of a line is still at the start of a line.
"""

from __future__ import annotations

import re

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


def device_lost(raw: str) -> bool:
    text = fold(raw)[0]
    return bool(_LOST_PHONE.search(text) and _OPEN.search(text))


def other_phone(raw: str) -> bool:
    """The customer says they write from someone else's phone or number («احجي من تلفون اختي»)."""
    return bool(_OTHER_PHONE.search(fold(raw)[0]))


# --- complaint_risk: a regulator threat or a repeat contact (no priority change) ---

_PFX = r"(?<!\w)[وفبل]{0,2}(?:ال)?"
_COMPLAINT = re.compile(
    rf"{_PFX}(?:بنك|مصرف)\s+(?:ال)?مركزي"
    rf"|{_PFX}جه(?:ات|[ةه])\s+(?:ال)?رقابي[ةه]?"
    r"|(?<!\w)[ولف]{0,2}[اأ]شتكي\s+(?:عليكم|عليك|ضدكم)"
    r"|(?<!\w)(?:[اأ]قدم|[اأ]رفع|اسجل|اسوي)\s+(?:عليكم\s+|ضدكم\s+)?(?:شكو[ىاه]|دعو[ىاه]|قضي[ةه])\s+(?:عليكم|ضدكم)"
    r"|(?<!\w)(?:[اأ]رفع|اسوي)\s+(?:عليكم|ضدكم)\s+(?:شكو[ىاه]|دعو[ىاه]|قضي[ةه])"
    r"|(?<!\w)(?:ثالث|رابع|خامس|عاشر)[ةه]?\s+مر[ةه](?!\w)"
    r"|(?<!\w)(?:لل|ال)مر[ةه]\s+(?:ال)?(?:ثالث|رابع|خامس|عاشر)[ةه]?(?!\w)"
    r"|(?<!\w)[و]?(?:اتصل|راسل|اراسل|كتب|اكتب|حجي|احجي)\w*(?:\s+\S+){0,2}?\s+"
    r"(?:ثلث|ثلاث|اربع|خمس|ست|سبع|عشر|هواي|هوايه|هواية|عدة|[3-9]|\d\d)\s*مرات"
    r"|(?<!\w)صارلي\s+(?:[^\s.،,!?؟]+\s+){1,2}?(?:اكتبلكم|اراسلكم|اتصل\w*|اراجع\w*|احاكي\w*)")


def complaint_risk(raw: str) -> bool:
    return bool(_COMPLAINT.search(fold(raw)[0]))


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
