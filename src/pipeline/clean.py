"""Light, rule-based cleaning before the model sees a ticket, and masking before a run is saved."""

from __future__ import annotations

import re
import unicodedata

# Arabic-Indic (٠-٩) and Persian (۰-۹) digits -> ASCII, so references and
# amounts compare the same way however the customer typed them.
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_TATWEEL = "ـ"
_WS = re.compile(r"\s+")


def clean(text: str) -> str:
    text = drop_format_chars(text.translate(_DIGITS).replace(_TATWEEL, ""))
    return _WS.sub(" ", text).strip()


def drop_format_chars(text: str) -> str:
    """The text without invisible format characters (Unicode Cf: zero-width
    spaces and joiners, direction marks and controls, the BOM, soft hyphens, tag characters). A reader
    doesn't see them, but they split a number («88\u200b41\u200b902») or reverse what the page shows."""
    return "".join(c for c in text if unicodedata.category(c) != "Cf")


# Persian kaf and yeh, as typed on Kurdish and Persian keyboards. «ى» is left alone: «تنسى» needs it.
_LETTERS = str.maketrans("کی", "كي")


def fold(text: str) -> tuple[str, list[int]]:
    """The text as the rules read it, and where each of its characters came from (so a match can be
    pointed at, or masked, in the text as written). Digits become ASCII; tatweel, harakat (shadda) and
    invisible format characters (ZWNJ, RLM, soft hyphen) are dropped, since a reader doesn't see them
    but they would split a word; Persian kaf/yeh become Arabic; presentation forms (the «ﻻ» ligature,
    fullwidth letters) become plain letters. Whitespace is kept."""
    chars, pos = [], []
    for i, c in enumerate(text):
        if c == _TATWEEL or unicodedata.category(c) in ("Mn", "Cf"):
            continue
        if "\ufb50" <= c <= "\ufdff" or "\ufe70" <= c <= "\ufeff" or "\uff01" <= c <= "\uff5e":
            c = unicodedata.normalize("NFKC", c)
        for ch in c.translate(_DIGITS).translate(_LETTERS):
            chars.append(ch)
            pos.append(i)
    pos.append(len(text))
    return "".join(chars), pos


# The prompts wrap the customer's text in <ticket>...</ticket>. A customer who types those tags can
# end the ticket early and write lines that look like ours (e.g. a forged "Known facts: ..." line).
# Variants a model may still read as the tag count too: invisible characters inside it ("</tic\u200bket>"),
# fullwidth brackets ("＜/ticket＞"), "/>" and attributes ("</ticket x>").
_HIDDEN = "[\u00ad\u200b-\u200f\u2060\ufeff]*"
_TICKET_TAG = re.compile(
    rf"[<＜]{_HIDDEN}\s*{_HIDDEN}(/?){_HIDDEN}\s*{_HIDDEN}" + _HIDDEN.join("ticket") + rf"(?:\b[^<>＜＞]*)?{_HIDDEN}[>＞]",
    re.IGNORECASE)


def neutralise_tags(text: str) -> str:
    """Swap any <ticket> or </ticket> the customer typed for look-alike brackets, so only our own
    tags delimit the ticket. Text without such a tag comes back unchanged (prompts stay byte-identical)."""
    return _TICKET_TAG.sub(lambda m: f"‹{m.group(1)}ticket›", text)


# --- numbers worth hiding: phone, card, account and transaction numbers, and codes ---

# A digit run: digit groups joined by "-", "." or up to two spaces or no-break spaces
# ("0770-123-4567", "0770.123.4567", "0770  123 4567"). An amount with thousands commas and a
# date are matched first so they are never part of a run, and a run never takes one in after a
# space ("07701234567 250,000", "07701234567 30.10.2026").
_SPACE = r"[ \u00a0\u2009\u202f]{1,2}"
_SEP = rf"(?:[-.]|{_SPACE})"
_AMOUNT = r"\d{1,3}(?:[,٬]\d{3})+(?:\.\d+)?(?!\d)"
_FULL_DATE = r"(?:\d{4}[-./]\d{1,2}[-./]\d{1,2}|\d{1,2}[-./]\d{1,2}[-./]\d{4})(?!\d|[-.]\d)"
_NUMBERS = re.compile(
    r"(?<!\d)(?:"
    rf"(?P<amount>{_AMOUNT})"
    r"|(?P<date>\d{4}(?P<s1>[-./])\d{1,2}(?P=s1)\d{1,2}|\d{1,2}(?P<s2>[-./])\d{1,2}(?P=s2)\d{4}|\d{4}-\d{4})"
    r"(?!\d|[-.]\d)"
    rf"|(?P<run>\+?\d+(?:(?:[-.]|{_SPACE}(?!{_AMOUNT}|{_FULL_DATE}))\d+)*)(?!\d))")

# A word that names a secret code, with its Arabic prefixes (و ف ب ل ال) and possessive endings.
# A code that names something else (an error, a discount, an agent or shop, a referral, a
# transaction or order, a QR, a place) is not a secret: "كود العملية 88213" is a reference.
_PFX = r"(?:[وف]?(?:بال|لل|ال|ب|ل)?ـ*)"
_NOT_SECRET = (r"(?:ال)?(?:خط[أا]|غلط|خصم|وكيل|متجر|تاجر|محل|دعو[ةه]|[إا]حال[ةه]|عملي[ةه]|حوال[ةه]"
               r"|تحويل|طلب|فرع|دول[ةه]|بلد|منطق[ةه]|بريدي?|QR|كيو|فاتور[ةه]|مشترك|اشتراك|تتبع|شحن[ةه]|منفذ"
               r"|مندوب|تذكر[ةه]|مرجع)(?!\w)")
# A digit may follow the word directly ("OTP482913", "الرمز4829"): only a letter ends the match early.
CREDENTIAL = re.compile(
    rf"(?<!\w)(?P<pfx>{_PFX})(?:"
    rf"(?:رمز|رموز|كود|[اأ]كواد)(?:ي|ك|ج|كم|نا|ه|ها)?(?![^\W\d_])(?!\s+{_NOT_SECRET})"
    r"(?:\s+(?:ال)?(?:تحقق|تفعيل|سري|دخول))?"
    r"|رقم(?:ي|ك|ج|كم)?\s+(?:ال)?سري"
    r"|كلم[ةه]\s+(?:ال)?(?:سر|مرور)"
    r"|OTP|PIN|CVV2?|CVC|[بپ]اسو+رد(?:ي|ك|ج|كم|نا)?|password|passcode"
    r")(?![^\W\d_])", re.IGNORECASE)
# Second round of role-played test sessions (secret_forms, adopted 7 Nov): the card's security code said in words, «الرقم اللي ورا البطاقة 731»,
# «الرمز اللي بظهر البطاقة».
_BACK_OF_CARD = re.compile(
    rf"(?<!\w)(?P<pfx>{_PFX})(?:رقم|رمز|كود|[اأ]رقام)\s+(?:اللي|الي|الموجود|المكتوب)?\s*(?:\S+\s+)?"
    r"(?:ورا|وره|خلف|بظهر|ظهر|على\s+ظهر|بالظهر|بالخلف)(?:\s+(?:ال)?(?:بطاق[ةه]|كارت)\w*)?(?![^\W\d_])")
# What a code after a credential word is, for the advice: a PIN or password, the card's security code, or a one-time code.
_PIN_WORD = re.compile(r"سري|PIN|كلم[ةه]|[بپ]اسو+رد|password|passcode", re.IGNORECASE)
_CVV_WORD = re.compile(r"CVV|CVC|ورا|وره|خلف|ظهر", re.IGNORECASE)

_CLAUSE_BREAK = re.compile(r"[.،,!?؟؛;\n]")
_LETTER = re.compile(r"[^\W\d_]")


def _luhn(digits: str) -> bool:
    total = 0
    for i, c in enumerate(reversed(digits)):
        d = int(c) * (2 if i % 2 else 1)
        total += d - 9 if d > 9 else d
    return total % 10 == 0


def _plausible_date(text: str) -> bool:
    parts = [int(p) for p in re.split(r"[-./]", text)]
    if len(parts) == 2:                                   # a year range, "2025-2026"
        return 1900 <= parts[0] <= parts[1] <= 2099
    if parts[0] >= 1000:
        y, m, d = parts
    else:
        d, m, y = parts
        if m > 12:                                        # month first ("10-30-2026")
            d, m = m, d
    return 1900 <= y <= 2099 and 1 <= m <= 12 and 1 <= d <= 31


# A number after one of these belongs to it, not to an earlier credential word:
# "نسيان الرقم السري وإكمال الحوالة رقم 9365140" is a transfer reference (dev-0099). "My number"
# («لرقمي») is where a code was sent, so it doesn't own the number: "الكود اللي اجه لرقمي 482913".
_OWN_NUMBER = re.compile(r"[وفبل]?(?:ال)?(?:رقم(?:ه|ها|هم)?|مبلغ\w*|حوال\w*|تحويل\w*|عملي\w*)")
# A number followed by a currency or a time unit is an amount or a wait, not a code:
# "الرمز ما وصل وحولت 50000 دينار", "اطلب رمز جديد بعد 120 ثانية".
_UNIT_AFTER = re.compile(r"\s*(?:دينار|د\.ع|[أا]لف|آلاف|الاف|مليون|دولار|IQD|USD|\$|ثاني|ثواني|دقيق|دقايق|ساع)",
                         re.IGNORECASE)


# «..» or «…» is a pause in a chat line, not the end of a clause: «كود التفعيل.. لا لحظه وصل هسه 482915».
_PAUSE = re.compile(r"\.{2,}|…")


def _after_credential(text: str, start: int, ends: list[int]) -> int | None:
    """The end of a credential word at most five words before `start`, in the same clause
    ("PIN: 1234", "رمز التحقق اللي وصلني على الموبايل 482913"), with no other number or
    "رقم/مبلغ/حوالة" in between; None if there is none. «..» or «…» doesn't end the clause."""
    for end in ends:
        between = _PAUSE.sub(" ", text[end:start])
        if end > start or _CLAUSE_BREAK.search(between) or re.search(r"\d", between):
            continue
        words = [w for w in between.split() if _LETTER.search(w)]
        if len(words) <= 5 and not any(_OWN_NUMBER.fullmatch(w) for w in words):
            return end
    return None


def _card(digits: str) -> bool:
    """A Luhn-valid 13-19 digit number with a card network's first digits (3, 4, 5, 6, or 2221-2720).
    An Iraqi phone in international form (964...) or a long reference passes Luhn one time in ten."""
    return (13 <= len(digits) <= 19 and _luhn(digits)
            and (digits[0] in "3456" or "2221" <= digits[:4] <= "2720"))


# A card number written in groups of four with mixed separators («5204-7311 8826 - 4413»), and a
# 13-19 digit number that the customer says is their card («رقم البطاقة 5213904477162280», «البطاقة اللي عندي رقمها
# 4211 7781 0093 5526») even when it fails the Luhn check (a typo, or a made-up number: it is still meant as one).
_GAP = r"[ \u00a0\u2009\u202f]{0,2}[-.]?[ \u00a0\u2009\u202f]{0,2}"
_CARD_GROUPS = re.compile(rf"(?<![\d,٬])\d{{4}}(?:{_GAP}\d{{4}}){{2}}{_GAP}\d{{1,7}}(?![\d,٬])")
_CARD_WORD = re.compile(r"(?<!\w)[وفبل]?(?:ال)?(?:بطاق(?:ت|[ةه])\w*|كارت\w*|card)(?!\w)(?!\s+(?:ال)?(?:وطني|موحد|ذكي|تموين|سكن|هوي)\w*)",
                        re.IGNORECASE)
_NOT_CARD_NUMBER = re.compile(r"[وفبل]?(?:ال)?(?:مبلغ\w*|حوال\w*|تحويل\w*|عملي\w*|هاتف\w*|تلفون\w*|موبايل\w*)")


def _card_said(text: str, start: int) -> bool:
    """A card word («بطاقتي», «رقم البطاقة», «الكارت») at most six words before `start`, in the same clause, with no
    other number and no amount, transfer or phone word in between."""
    for m in _CARD_WORD.finditer(text, max(0, start - 80), start):
        between = _PAUSE.sub(" ", text[m.end():start])
        if _CLAUSE_BREAK.search(between) or re.search(r"\d", between):
            continue
        words = [w for w in between.split() if _LETTER.search(w)]
        if len(words) <= 6 and not any(_NOT_CARD_NUMBER.fullmatch(w) for w in words):
            return True
    return False


def _secret_kind(text: str, cred: tuple[int, int]) -> str:
    """What a code after a credential word is: "pin" (a PIN or password), "cvv" (the card's security code) or
    "otp" (a one-time or login code), from the word and the two words after it."""
    s, e = cred
    near = text[s:e] + " " + " ".join(text[e:e + 40].split()[:2])
    return "cvv" if _CVV_WORD.search(near) else "pin" if _PIN_WORD.search(near) else "otp"


def _spans(raw: str, detail: bool = False) -> list[tuple[int, int, str]]:
    """(start, end, kind) of every number worth hiding in `raw`, in text order. kind is "code" (3-8
    digits after a credential word), "card" (a card number, see _card) or "long" (any other run of 7+
    digits). Dates, comma amounts, "1.000.000", decimals like 3.5 and "5000-10000 دينار" are not runs.
    The rules read the folded text (so «الرقم السرّي» and «الکود» count), and the spans point into `raw`.
    With `detail`, a code's kind says what it is: "pin", "cvv" or "otp" (_secret_kind)."""
    text, pos = fold(raw)
    creds = sorted([m.span() for m in CREDENTIAL.finditer(text)] + [m.span() for m in _BACK_OF_CARD.finditer(text)])
    ends = [e for _, e in creds]
    out = []
    cards = [m.span() for m in _CARD_GROUPS.finditer(text)]
    for s0, e0 in cards:
        digits = re.sub(r"\D", "", text[s0:e0])
        if 13 <= len(digits) <= 19 and (_card(digits) or _card_said(text, s0)):
            out.append((s0, e0, "card"))
    for m in _NUMBERS.finditer(text):
        if m.group("amount") or (m.group("date") and _plausible_date(m.group("date"))):
            continue
        start, end = m.span()
        if any(s0 < end and start < e0 for s0, e0, _ in out):
            continue                                       # part of a card number found above
        if start >= 2 and text[start - 1] == "-" and re.match(r"[A-Za-z]", text[start - 2]):
            continue                                       # an id such as «AG-2290» or «TX-88213»: not a secret
        inside = next((e for s, e in creds if s <= start < e), None)   # "CVV2 123": the 2 is the word's
        if inside is not None:
            start = inside
            while start < end and not text[start].isdigit():
                start += 1
            if start == end:
                continue
        run = text[start:end]
        digits = "".join(c for c in run if c.isdigit())
        seps = re.findall(_SEP, run)
        owner = None
        if _card(digits) or (13 <= len(digits) <= 19 and _card_said(text, start)):
            kind = "card"
        elif seps == ["-"] and _UNIT_AFTER.match(text, end):
            continue                                       # "بين 5000-10000 دينار": a range of amounts
        elif 3 <= len(digits) <= 8 and not _UNIT_AFTER.match(text, end) and (
                owner := _after_credential(text, start, ends)) is not None:
            kind = "code"
        elif re.fullmatch(r"\d{1,3}(?:\.\d{3}){2,}", run):
            continue                                       # "1.500.000": an amount
        elif seps == ["."] and len(run.split(".")[1]) <= 2:
            whole = run.split(".")[0]                      # a decimal: only the whole part counts
            if sum(c.isdigit() for c in whole) < 7:
                continue
            end, kind = start + len(whole), "long"
        elif len(digits) >= 7:
            kind = "long"
        else:
            continue
        if detail and kind == "code":
            kind = _secret_kind(text, next(c for c in creds if c[1] == owner))
        out.append((start, end, kind))
    return sorted((pos[s], pos[e - 1] + 1, k) for s, e, k in out)


def sensitive_numbers(text: str) -> list[tuple[int, int, str]]:
    """(start, end, kind) of each card number ("card") or code after a credential word ("code") in
    `text`. A draft must never repeat these, even when the customer wrote them."""
    return [s for s in _spans(text) if s[2] != "long"]


def secret_kinds(text: str) -> list[str]:
    """What the customer wrote, by kind, in text order and once each: "card" (a card number), "cvv" (its
    security code), "pin" (a PIN or password) or "otp" (a one-time or login code), so the advice can name it."""
    return list(dict.fromkeys(k for _, _, k in _spans(text, detail=True) if k != "long"))


def _hide(s: str) -> str:
    digits = [i for i, c in enumerate(s) if c.isdigit()]
    keep = set(digits[:2] + digits[-2:])
    return "".join("*" if c.isdigit() and i not in keep else c for i, c in enumerate(s))


def mask_for_logs(text: str) -> str:
    """Hide long numbers (phone, card, account, transaction) before saving, keeping the first
    and last two digits so a person can still tell two numbers apart. A code after a credential
    word ("OTP 482913", "PIN 1234") is hidden entirely. Names are not masked."""
    for start, end, kind in reversed(_spans(text)):
        part = text[start:end]
        hidden = re.sub(r"\d", "*", part) if kind == "code" else _hide(part)
        text = text[:start] + hidden + text[end:]
    return text


def mask_run(value):
    """mask_for_logs applied to every string in a saved run (ticket text, prompts, model
    replies, drafts, notes); numbers, keys and structure are kept."""
    if isinstance(value, str):
        return mask_for_logs(value)
    if isinstance(value, list):
        return [mask_run(v) for v in value]
    if isinstance(value, dict):
        return {k: mask_run(v) for k, v in value.items()}
    return value
