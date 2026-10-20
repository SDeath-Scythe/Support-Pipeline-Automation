"""F2 (draft_check): rule checks on a draft before an agent sees it.

The drafter prompt already forbids these; the rules catch the cases where it slips.
A draft with a problem is still shown, but flagged with the reason.
"""

from __future__ import annotations

import re

from .clean import clean

_AR = "؀-ۿ"

# A Latin letter glued to an Arabic one, e.g. "hلا".
_GLUED = re.compile(rf"[A-Za-z][{_AR}]|[{_AR}][A-Za-z]")
_LATIN_WORD = re.compile(r"[A-Za-z]+")
# Latin words a draft may use even if the customer did not.
_LATIN_OK = {"otp", "pin", "qr", "sms", "iqd", "usd", "app"}

# Promises of an outcome or a time. "خلال" + a time unit is only allowed if it is a known fact.
# "راح نرجع نخبرك" (we'll get back to you) is not a promise, so a return verb only counts
# with money near it.
_MONEY = r"(فلوس|المبلغ|مبلغ|الرصيد|المصاري)"
_PROMISES = [
    rf"{_MONEY}\S*\s+(\S+\s+){{0,2}}?راح\s+(ت|ي)رجع",
    rf"راح\s+(ن|ت|ي)رجع\S*\s+(\S+\s+){{0,2}}?{_MONEY}",
    rf"(ن|ت)رجعل\S*\s+(\S+\s+)?{_MONEY}",
    r"نعوض", r"نضمن", r"مضمون", r"اكيد راح", r"أكيد راح",
    r"راح (ت|ي)وصل(ك|ج|ه|ها)? خلال",
]
_TIME = re.compile(r"خلال\s+(\S+\s+)?(دقيق|دقايق|ساع|يوم|أيام|ايام|اسبوع|أسبوع|شهر)")

# Asking for a secret: a request verb, then within a few words a secret.
_SECRET = re.compile(
    r"(دز|ارسل|أرسل|ترسل|ابعث|اكتب|انطي|شارك|زود)\S*\s+(?:\S+\s+){0,3}?"
    r"(الرمز|الكود|رمز التحقق|كلمة السر|الباسورد|OTP|PIN)", re.IGNORECASE)
_NEGATIONS = ("لا", "ما", "ابد", "أبد", "بدون")

_NUMBER = re.compile(r"\d[\d,٬.]*\d|\d")


def _numbers(text: str) -> set[str]:
    return {re.sub(r"[,٬.]", "", n) for n in _NUMBER.findall(clean(text))}


def problems(draft: str, allowed_text: str) -> list[str]:
    """Return the problem kinds found in `draft`.

    `allowed_text` is everything the drafter was given (the ticket, extracted fields and
    known facts): words and numbers from it are allowed to appear in the draft.
    """
    found = []
    if _GLUED.search(draft):
        found.append("stray_latin")
    allowed_words = {w.lower() for w in _LATIN_WORD.findall(allowed_text)} | _LATIN_OK
    if any(w.lower() not in allowed_words for w in _LATIN_WORD.findall(draft)) and "stray_latin" not in found:
        found.append("stray_latin")

    time_ok = {m.group() for m in _TIME.finditer(clean(allowed_text))}   # "٢٤" and "24" compare equal
    if any(re.search(p, draft) for p in _PROMISES) or any(m.group() not in time_ok for m in _TIME.finditer(clean(draft))):
        found.append("promise")

    for m in _SECRET.finditer(draft):
        # "لا تشارك الرمز" is a warning, not a request: look at the two words before the verb.
        if not any(t.startswith(_NEGATIONS) for t in draft[:m.start()].split()[-2:]):
            found.append("asks_secret")
            break

    allowed_numbers = _numbers(allowed_text)
    thousands = {str(int(n) * 1000) for n in allowed_numbers if n.isdigit() and len(n) <= 4}
    if re.search(r"(^|\s)(ال|أل)ف(\s|$)", allowed_text):   # "الف وحدة" = 1,000 written as a word
        thousands.add("1000")
    if _numbers(draft) - allowed_numbers - thousands:
        found.append("unknown_number")
    return found
