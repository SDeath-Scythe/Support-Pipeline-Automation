"""Generate the synthetic ticket dataset: dev 240, mvp_test 80, heldout 80.

    python scripts/generate_tickets.py build --split dev      --seed 1101 --n 240
    python scripts/generate_tickets.py build --split mvp_test --seed 2202 --n 80
    python scripts/generate_tickets.py build --split heldout  --seed 3303 --n 80   # its own run
    python scripts/generate_tickets.py handcheck --seed 4404    # data/review/handcheck_80.csv
    python scripts/generate_tickets.py stats                    # coverage tables, no ticket text

How a split is built:
1. A spec list is drawn deterministically from the seed: subcategory (category mix of a real
   L1 day, at least 3 per subcategory), dialect, style, difficulty, an optional tagged edge
   case, whether the ticket gives a reference / phone, and the exact amount to state ("ورقة" is
   a 100 USD note, so a spec with `usd_as_warqa: 50` has gold amount_usd 5,000).
2. The `generator` role (Opus) writes ~10 tickets per call and returns JSON only. It writes the
   placeholders {REF} and {PHONE}; code fills them, so gold reference / phone are exactly what
   was inserted. Amounts are given in the spec, so gold amounts are exact too.
3. Code validates (schema, taxonomy, placeholders, reference really in the text, no invented
   long numbers, no brand names, style sanity, "ورقة" only for dollar notes, no Mosuli غ for ر),
   drops near-duplicates of any ticket in any split or data/probes/ (normalised characters
   > 0.8 similar, or content words > 0.5 similar, which catches the same sentence in another
   dialect), and keeps every dialect marker word under MARKER_CAP of the split. Failed specs
   are regenerated (new `variation`) until the split is full.
4. Priority and outcome come from code: the taxonomy and routing rules with the recommended
   flags on. F15: no word raises priority; only an amount >= 1,000,000 IQD raises it one level.
5. A blind audit: the `evaluator` role (Opus) labels every ticket without seeing its gold label.
   Disagreements never change gold; they go into `review_reason` for a person to check.

The script prints statistics only, never ticket text, so the heldout split stays unread.
Model replies are saved under runs/generation/<split>-s<seed>/ (git-ignored) so a re-run resumes.
The build fails if any marker word is in more than MARKER_FAIL of a split.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import re
import sys
import unicodedata
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# Priority uses the routing rules with the recommended flags on (only F15 affects routing).
# F16 (warqa_usd) only changes the classifier rules the blind audit is given ("ورقة" = 100 USD).
os.environ["PIPELINE_FIXES"] = ("draft_check,recheck_cross_team,fee_followup,no_urgency_words,"
                                "ask_if_missing,no_specific_followup,fraud_secondary_cleanup,warqa_usd")

from pipeline import classify as cls  # noqa: E402
from pipeline.clean import clean  # noqa: E402
from pipeline.config import models, taxonomy  # noqa: E402
from pipeline.gate import _key, reference_in_text  # noqa: E402
from pipeline.llm import call  # noqa: E402
from pipeline.route import route  # noqa: E402
from pipeline.schemas import Extraction  # noqa: E402

SPLITS = {"dev": "dev", "mvp_test": "mvp", "heldout": "hold"}     # split -> id prefix
MIN_PER_SUB = 3
BATCH = 10
WORKERS = 4
MAX_ROUNDS = 12
DUP_THRESHOLD = 0.8            # normalised characters (the author's rule)
DUP_TOKEN_THRESHOLD = 0.5      # content words, dialect words folded: the same sentence in another dialect
DUP_TOKEN_MIN = 5              # ... only when both tickets have at least this many content words
MARKER_CAP = 0.10              # a ticket is rejected if it would take a marker word above this share
MARKER_FAIL = 0.15             # the build fails above this share

CATEGORY_WEIGHTS = {"transfers": 0.25, "account_access": 0.15, "agents_cash": 0.15, "bills_topup": 0.12,
                    "general": 0.10, "cards": 0.08, "verification": 0.08, "fraud_security": 0.07}
# Within a category, a rough real-day mix (equal where there is no reason to differ).
SUB_WEIGHTS = {"not_received": 0.5, "wrong_recipient": 0.3, "reversal_request": 0.2,
               "login_otp": 0.35, "forgot_pin": 0.25, "blocked_account": 0.2, "sim_change": 0.2,
               "topup_failed": 0.45, "bill_not_reflected": 0.3, "merchant_payment": 0.25,
               "cash_in_not_credited": 0.4, "overcharged_fee": 0.35, "cash_out_refused": 0.25,
               "app_bug": 0.3, "fees_limits_question": 0.3, "complaint": 0.2, "unclear": 0.2}
DIALECTS = {"baghdadi": 0.5, "southern": 0.3, "mosuli": 0.2}
STYLES = {"short": 0.33, "long": 0.20, "typos": 0.15, "mixed_english": 0.14, "voice_note_style": 0.15,
          "arabizi": 0.03}
ARABIZI_MAX_SHARE = 0.03
DIFFICULTY = {"easy": 0.45, "medium": 0.40, "hard": 0.15}
EDGE_SHARE = 0.18

DESCRIPTIONS = {
    "not_received": "sent a transfer; the money left the account but the recipient did not get it (or an incoming transfer never arrived)",
    "wrong_recipient": "sent money to the wrong number or account by mistake (often wants it back)",
    "reversal_request": "asks to cancel or undo a transfer that went to the intended person (changed mind, paid twice, duplicate)",
    "login_otp": "cannot log in: the SMS/OTP code does not arrive or is rejected, or a login error",
    "forgot_pin": "forgot the PIN or password and wants to reset it",
    "blocked_account": "the account shows as blocked, suspended or frozen",
    "sim_change": "changed or lost the SIM or phone (new SIM, same number) and now cannot get in",
    "rejected_or_pending": "identity verification was rejected, or has been pending for a long time",
    "limit_upgrade": "wants a higher transaction or balance limit and asks how",
    "overcharged_fee": "an agent took a bigger fee or commission than allowed for cash-in or cash-out",
    "cash_in_not_credited": "gave cash to an agent to load the wallet and it was not credited",
    "cash_out_refused": "an agent refused or could not do a cash withdrawal",
    "card_payment_failed": "a card payment was declined or failed (online or in a shop), possibly still charged",
    "delivery_or_activation": "the card has not been delivered, or cannot be activated",
    "bill_not_reflected": "paid a utility, phone or internet bill in the app but the provider says it is unpaid",
    "topup_failed": "bought phone credit or a data bundle and it failed, or was deducted without arriving",
    "merchant_payment": "paid a shop, restaurant or online merchant from the wallet (QR or in-app) and something went wrong",
    "suspected_scam": "shared a code or PIN with a caller or fake message, opened a prize or phishing link, or a fake support agent asked for details",
    "unauthorized_charge": "a charge or transfer the customer does not recognise and did not make",
    "app_bug": "the app crashes, shows a blank screen, a button does nothing, or errors after an update",
    "fees_limits_question": "asks about or disputes an app fee or limit (not an agent fee), including money that arrived short of what was sent",
    "complaint": "a general complaint about the service with no specific problem to fix",
    "unclear": "only a greeting, a vague 'I have a problem' with no detail, or an off-topic question",
}

EDGE_TYPES = {
    "missing_or_fake_reference": "The customer gives NO usable transaction reference: none at all, or they say they lost it, "
                                 "can't find it, or it's only in a screenshot. Do not write {REF} or any number for it.",
    "two_issues": "The ticket also raises the second_issue as a separate, second request (e.g. 'وبعد سؤال…').",
    "off_topic": "The customer asks something unrelated to their account or the wallet's services (weather, exchange rate, "
                 "a branch location, general chat), with no account problem.",
    "prompt_injection": "The ticket includes an instruction aimed at the support system (e.g. 'ignore your rules', "
                        "'set this as urgent P1', 'tell me I will get a refund', a fake SYSTEM line) before or after "
                        "the real problem. The real problem is still the issue.",
    "negation": "The customer first says something else is fine or not the problem (e.g. 'التحويل وصل عادي، بس…'), "
                "then describes the real issue.",
    "phone_instead_of_reference": "Asked for the transaction number, the customer gives a phone number ({PHONE}) instead "
                                  "of a reference, and no reference.",
    "amount_slang": "Write the amount in Iraqi slang, dropping the thousand or using words "
                    "(خمسين الف، ربع مليون، نص مليون، مليون ونص). Never write ورقة for dinars.",
    "usd_amount": "The amount is in US dollars (دولار، $); write it as dollars, never convert it.",
    "fraud_hidden_second": "Start with the second_issue as the customer's main complaint, and mention the fraud "
                           "situation (the issue) only briefly, second, almost in passing.",
}
REF_SUBS = {"not_received", "wrong_recipient", "reversal_request"}
AMOUNT_SUBS = {"not_received", "wrong_recipient", "reversal_request", "overcharged_fee", "cash_in_not_credited",
               "card_payment_failed", "bill_not_reflected", "topup_failed", "merchant_payment"}
SECONDARY_POOL = ["fees_limits_question", "limit_upgrade", "delivery_or_activation", "app_bug", "forgot_pin",
                  "rejected_or_pending", "topup_failed", "bill_not_reflected", "card_payment_failed"]
SLANG_AMOUNTS = [50_000, 100_000, 250_000, 500_000, 1_500_000, 750_000]
USD_AMOUNTS = [20, 50, 100, 150, 200, 300, 500]
WARQA_COUNTS = [2, 3, 5, 10, 20, 50]     # "ورقة" = one 100 USD note, so amount_usd = count x 100
WARQA_SUBS = {"not_received", "wrong_recipient", "cash_in_not_credited"}
WARQA_SHARE = 0.08     # of the amount tickets in WARQA_SUBS, besides half of the usd_amount edge cases
WARQA_INSTRUCTION = ("The amount is in 100-dollar notes: write exactly {n} ورقة (one ورقة = 100 USD), "
                     "the way Iraqis count dollars. Do not convert it and do not write دولار.")
_WARQA = re.compile(r"(^|\s)(ال)?ورق(ه|ات|تين)?(\s|$)")                     # on normalised text
_WARQA_LATIN = re.compile(r"(^|[^a-z0-9])(el|il|l)?war(a)?[8qg9k](a|at|ten|tain)?([^a-z0-9]|$)")   # Arabizi, raw text


def has_warqa(text: str) -> bool:
    return bool(_WARQA.search(normalise(text)) or _WARQA_LATIN.search(text.lower()))
# Dialect marker words, matched on normalised text (with an optional و/ف/ب/ل in front).
# Prefix forms (ديـ) and letters (چ، گ) are not words and are not counted.
MARKERS = {
    "هسه": r"هس(ه|ع)", "شكو": r"شكو", "شلون": r"شلون\w*", "اكو": r"اكو", "ماكو": r"ماكو", "كلش": r"كلش",
    "هواي": r"هواي", "شنهو": r"شنهو", "شنو": r"شنو", "يمعود": r"يمعود", "هيج": r"هي(ج|چ)", "ايش": r"ايش",
    "چان": r"(چان|جان)", "بلكي": r"بلكي", "لعد": r"لعد", "ويا": r"ويا(ي|ك|ه|هم|نا)?", "خوش": r"خوش",
    "عيني": r"(عيني|عيوني)", "اغاتي": r"اغاتي", "يابه": r"(يابه|يابا)", "صارلي": r"صارل(ي|ه|ها|نا|كم)",
    "شگد": r"(شگد|شكد|چم|جم)", "گلت": r"(گلت|گال|گلي|كلت)", "ليش": r"ليش",
}   # not counted: اريد, which is also standard Arabic (أريد) once hamza is normalised
_MARKER_RE = {m: re.compile(rf"(^|\s)[وفبل]?{p}(\s|$)") for m, p in MARKERS.items()}
# Words people use to sound urgent: shown in the frequency table only (F15: they do not set priority).
URGENCY = {"ضروري": r"ضروري\w*", "عاجل": r"(عاجل|بالعاجل)", "بسرعه": r"(بسرعه|بسرعة|سريع)"}
_URGENCY_RE = {m: re.compile(rf"(^|\s)[وفبل]?{p}(\s|$)") for m, p in URGENCY.items()}
# Mosuli forms with غ written for ر, which the author says is wrong ("اعغفها", "شهغ", "انتظغ").
GH_FOR_R = ["اعغف", "شهغ", "انتظغ", "غقم", "غصيد", "اغجع", "غجع", "اغسل", "غسل", "صاغ", "شغك", "كغت",
            "مصغف", "ديناغ", "خبغ", "اغيد", "يغيد", "تحويغ", "اغبع", "غبع", "مغه", "مغتين", "فلوغ", "سغق", "غاح",
            "غوح", "حغام", "تغجع", "يغجع", "غسال", "اغسل", "دغب", "قغيب", "كغيم", "غقمي", "بغنامج"]
AMOUNT_RANGES = {  # IQD, realistic per issue
    "not_received": [25_000, 50_000, 75_000, 100_000, 150_000, 200_000, 300_000, 500_000, 1_000_000, 2_000_000],
    "wrong_recipient": [20_000, 50_000, 100_000, 150_000, 250_000, 400_000, 1_200_000],
    "reversal_request": [50_000, 100_000, 200_000, 350_000, 600_000, 1_500_000],
    "overcharged_fee": [3_000, 5_000, 7_000, 10_000, 15_000],
    "cash_in_not_credited": [50_000, 100_000, 200_000, 300_000, 500_000, 1_000_000],
    "card_payment_failed": [15_000, 25_000, 40_000, 60_000, 90_000, 150_000],
    "bill_not_reflected": [12_000, 25_000, 35_000, 50_000, 80_000],
    "topup_failed": [2_000, 5_000, 10_000, 15_000, 25_000],
    "merchant_payment": [8_000, 15_000, 27_000, 45_000, 120_000],
}
BRANDS = ["آسيا", "اسيا", "asia", "زين", "zain", "كورك", "korek", "نون", "noon", "امازون", "أمازون", "amazon",
          "الرافدين", "الرشيد", "rafidain", "fastpay", "فاست باي", "كي كارد", "qi card", "qicard", "زين كاش",
          "visa", "فيزا", "mastercard", "ماستر كارد", "ماستركارد", "paypal", "apple", "google", "talabat", "طلبات",
          "careem", "كريم", "whatsapp", "واتساب", "واتس", "facebook", "فيسبوك", "instagram", "انستا", "telegram",
          "تلكرام", "تليجرام", "earthlink", "ارثلنك", "سوبرماركت الـ"]


def weighted(rng: random.Random, table: dict[str, float]) -> str:
    return rng.choices(list(table), weights=list(table.values()))[0]


# ---------------------------------------------------------------- specs

def allocate(n: int) -> Counter:
    """Subcategory counts: at least MIN_PER_SUB each, then fill towards the category weights."""
    tax = taxonomy()
    counts = Counter({s: MIN_PER_SUB for s in tax.subcategories})
    if sum(counts.values()) > n:
        raise SystemExit(f"{n} tickets cannot hold {MIN_PER_SUB} of each of {len(counts)} subcategories")
    by_cat = {c: [s for s, sub in tax.subcategories.items() if sub.category == c] for c in tax.categories}
    while sum(counts.values()) < n:
        cat = max(by_cat, key=lambda c: (CATEGORY_WEIGHTS[c] * n - sum(counts[s] for s in by_cat[c]), c))
        cat_total = sum(counts[s] for s in by_cat[cat]) + 1
        w = {s: SUB_WEIGHTS.get(s, 1 / len(by_cat[cat])) for s in by_cat[cat]}
        tot = sum(w.values())
        sub = max(by_cat[cat], key=lambda s: (w[s] / tot * cat_total - counts[s], s))
        counts[sub] += 1
    return counts


def make_specs(split: str, n: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    tax = taxonomy()
    subs = [s for s, k in sorted(allocate(n).items()) for _ in range(k)]
    rng.shuffle(subs)
    arabizi_left = math.floor(ARABIZI_MAX_SHARE * n)
    specs = []
    for i, sub in enumerate(subs, 1):
        style = weighted(rng, STYLES)
        while style == "arabizi" and arabizi_left <= 0:
            style = weighted(rng, STYLES)
        arabizi_left -= style == "arabizi"
        specs.append({"spec_id": f"{SPLITS[split]}-{i:04d}", "subcategory": sub, "category": tax.get(sub).category,
                      "dialect": weighted(rng, DIALECTS), "style": style, "difficulty": weighted(rng, DIFFICULTY),
                      "edge_case": None, "secondary_subcategory": None})

    def compatible(edge: str, s: dict) -> bool:
        sub = s["subcategory"]
        fraud = s["category"] == "fraud_security"
        return {
            "missing_or_fake_reference": sub in REF_SUBS,
            "two_issues": not fraud and sub not in ("unclear", "complaint"),
            "off_topic": sub == "unclear",
            "prompt_injection": not fraud and sub != "unclear",
            "negation": not fraud and sub not in ("unclear", "complaint"),
            "phone_instead_of_reference": sub in ("not_received", "wrong_recipient"),
            "amount_slang": sub in AMOUNT_SUBS and sub not in ("overcharged_fee", "topup_failed"),
            "usd_amount": sub in ("not_received", "wrong_recipient", "card_payment_failed", "cash_in_not_credited",
                                  "merchant_payment"),
            "fraud_hidden_second": fraud,
        }[edge]

    n_edge = round(EDGE_SHARE * n)
    types = list(EDGE_TYPES)
    tagged = 0
    for k in range(n_edge * 3):                       # round-robin over types until enough are tagged
        if tagged >= n_edge:
            break
        edge = types[k % len(types)]
        pool = [s for s in specs if s["edge_case"] is None and compatible(edge, s)]
        if not pool:
            continue
        s = rng.choice(pool)
        s["edge_case"] = edge
        s["difficulty"] = "hard" if edge in ("two_issues", "negation", "fraud_hidden_second", "prompt_injection") \
            else rng.choice(["medium", "hard"])
        tagged += 1

    for s in specs:
        sub, edge = s["subcategory"], s["edge_case"]
        if edge in ("two_issues", "fraud_hidden_second"):
            # For fraud, an account-access issue counts as a consequence, not a second issue (F14b).
            banned = {s["category"]} | ({"account_access"} if edge == "fraud_hidden_second" else set())
            pool = [x for x in SECONDARY_POOL if tax.get(x).category not in banned]
            s["secondary_subcategory"] = rng.choice(pool)
        if sub in REF_SUBS:
            s["include_reference"] = edge not in ("missing_or_fake_reference", "phone_instead_of_reference") \
                and rng.random() > 0.08                 # a few natural misses besides the tagged ones
        else:
            s["include_reference"] = sub not in ("unclear", "complaint", "app_bug") and rng.random() < 0.15
        s["include_phone"] = edge == "phone_instead_of_reference" or (
            (sub == "topup_failed" and rng.random() < 0.4) or (sub == "wrong_recipient" and rng.random() < 0.3))
        s["amount_iqd"] = s["amount_usd"] = None
        s["usd_as_warqa"] = None
        if edge == "usd_amount" and sub in WARQA_SUBS and rng.random() < 0.5:
            s["usd_as_warqa"] = rng.choice(WARQA_COUNTS)
            s["amount_usd"] = s["usd_as_warqa"] * 100
        elif edge == "usd_amount":
            s["amount_usd"] = rng.choice(USD_AMOUNTS)
        elif edge == "amount_slang":
            s["amount_iqd"] = rng.choice(SLANG_AMOUNTS)
        elif sub in AMOUNT_SUBS and rng.random() > 0.08:
            if sub in WARQA_SUBS and rng.random() < WARQA_SHARE:     # dollars counted in notes, untagged
                s["usd_as_warqa"] = rng.choice(WARQA_COUNTS)
                s["amount_usd"] = s["usd_as_warqa"] * 100
            else:
                s["amount_iqd"] = rng.choice(AMOUNT_RANGES[sub])
        s["urgency"] = rng.random() < 0.12
    return specs


# ---------------------------------------------------------------- generation

def spec_for_prompt(s: dict, variation: int, avoid: list[str] | None = None, similar: str | None = None) -> dict:
    tax = taxonomy()
    sub = tax.get(s["subcategory"])
    out = {"spec_id": s["spec_id"],
           "issue": {"key": s["subcategory"], "label": sub.label, "description": DESCRIPTIONS[s["subcategory"]]},
           "dialect": s["dialect"], "style": s["style"], "difficulty": s["difficulty"],
           "include_reference": s["include_reference"], "include_phone": s["include_phone"],
           "urgency": s["urgency"], "variation": variation}
    if avoid:
        out["avoid_words"] = avoid
    if similar:
        out["too_similar_to"] = similar
    if s["secondary_subcategory"]:
        sec = s["secondary_subcategory"]
        out["second_issue"] = {"key": sec, "label": tax.get(sec).label, "description": DESCRIPTIONS[sec]}
    if s["edge_case"]:
        out["edge_case"] = {"type": s["edge_case"], "instruction": EDGE_TYPES[s["edge_case"]]}
    if s["amount_iqd"] is not None:
        out["amount_iqd"] = s["amount_iqd"]
    if s.get("usd_as_warqa"):
        out["usd_as_warqa"] = s["usd_as_warqa"]
        if s["edge_case"]:
            out["edge_case"]["instruction"] = WARQA_INSTRUCTION.format(n=s["usd_as_warqa"])
    elif s["amount_usd"] is not None:
        out["amount_usd"] = s["amount_usd"]
    return out


def first_json(reply: str, opener: str):
    start = reply.find(opener)
    if start < 0:
        raise ValueError("no JSON in reply")
    return json.JSONDecoder().raw_decode(reply[start:])[0]


class Counters:
    def __init__(self):
        self.calls = Counter()


def model_batch(split: str, kind: str, name: str, role: str, system: str, user: str, counters: Counters):
    """One model call, saved to runs/generation/<split>-s<seed>/ so re-runs resume instead of re-paying."""
    path = ROOT / "runs/generation" / split / f"{kind}_{name}.json"     # split here is "<split>-s<seed>"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    reply = call(role, system, user)
    counters.calls[role] += 1
    data = first_json(reply, "[")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


AR_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


def make_reference(rng: random.Random) -> str:
    n = rng.randint(7, 10)
    digits = str(rng.randint(1, 9)) + "".join(str(rng.randint(0, 9)) for _ in range(n - 1))
    form = rng.random()
    if form < 0.40:
        return digits
    if form < 0.55:
        return f"{digits[:4]}-{digits[4:]}"
    if form < 0.70:
        return f"{digits[:4]} {digits[4:]}"
    if form < 0.90:
        return digits.translate(AR_DIGITS)
    return rng.choice(["RV", "TX", "TR"]) + rng.choice(["", " ", "-"]) + digits


def make_phone(rng: random.Random) -> str:
    p = "07" + rng.choice("3456789") + "".join(str(rng.randint(0, 9)) for _ in range(8))
    form = rng.random()
    if form < 0.6:
        return p
    if form < 0.8:
        return f"{p[:4]} {p[4:7]} {p[7:]}"
    return p.translate(AR_DIGITS)


_DIACRITICS = re.compile(r"[ً-ْـ]")
_NON_WORD = re.compile(r"[^\w\s]|\d|_")


def normalise(text: str) -> str:
    t = unicodedata.normalize("NFKC", clean(text)).lower()
    t = _DIACRITICS.sub("", t)
    t = t.translate(str.maketrans("أإآىة", "ااايه"))
    t = _NON_WORD.sub(" ", t)
    return re.sub(r"\s+", " ", t).strip()


def problems(spec: dict, text: str) -> list[str]:
    """Code checks on one generated ticket (before placeholders are filled)."""
    out = []
    if not isinstance(text, str) or len(text.strip()) < 3:
        return ["empty"]
    if text.count("{REF}") != (1 if spec["include_reference"] else 0):
        out.append("ref_placeholder")
    if text.count("{PHONE}") != (1 if spec["include_phone"] else 0):
        out.append("phone_placeholder")
    rest = text.replace("{REF}", "").replace("{PHONE}", "")
    if re.search(r"[{}]|\bREF\b|\bPHONE\b", rest):
        out.append("stray_placeholder")
    # A 7+ digit run that is not the spec's own amount looks like an invented reference or phone.
    amounts = {str(spec["amount_iqd"]), str(spec["amount_usd"])}
    if any(run not in amounts for run in re.findall(r"\d{7,}", clean(rest).replace(",", "").replace("٬", ""))):
        out.append("invented_long_number")
    low = rest.lower()
    if any(re.search(rf"(^|[^\w]){re.escape(b)}([^\w]|$)", low) for b in BRANDS):
        out.append("brand_name")
    latin = len(re.findall(r"[A-Za-z]", rest))
    arabic = len(re.findall(r"[؀-ۿ]", rest))
    if spec["style"] == "arabizi" and latin < arabic:
        out.append("not_arabizi")
    if spec["style"] != "arabizi" and arabic < latin:
        out.append("not_arabic")
    n = len(rest)
    if (spec["style"] == "short" and n > 200) or (spec["style"] == "long" and n < 90) or n > 1200:
        out.append("length_vs_style")
    norm = normalise(rest)
    warqa = has_warqa(rest)
    if spec.get("usd_as_warqa"):
        if not warqa:
            out.append("warqa_missing")
    elif warqa:
        out.append("warqa_without_usd")         # "ورقة" is a 100 USD note, never dinars
    elif spec["amount_usd"] is not None and not re.search(r"دولار|\$|usd|dollar|dolar", low):
        out.append("usd_not_stated")
    if spec["dialect"] == "mosuli" and gh_for_r(norm):
        out.append("mosuli_gh_for_r")
    return out


def gh_for_r(norm: str) -> bool:
    """A Mosuli ticket that spells ر as غ: a known form, or several غ and no ر at all."""
    if any(f in word for word in norm.split() for f in GH_FOR_R):
        return True
    return norm.count("غ") >= 2 and "ر" not in norm and len(norm) > 40


def markers_in(norm: str) -> set[str]:
    return {m for m, rx in _MARKER_RE.items() if rx.search(norm)}


def gold(spec: dict, text: str, ref: str | None, phone: str | None, date, split: str, batch: str) -> dict:
    tax = taxonomy()
    sub = tax.get(spec["subcategory"])
    ex = Extraction(category=spec["category"], subcategory=spec["subcategory"],
                    secondary_subcategory=spec["secondary_subcategory"], reference=ref, recipient_phone=phone,
                    amount_iqd=spec["amount_iqd"], amount_usd=spec["amount_usd"], confidence=1.0)
    _, priority = route(ex, clean(text))
    have = {"reference": bool(ref), "amount": spec["amount_iqd"] is not None or spec["amount_usd"] is not None}
    if sub.always_escalate:
        outcome = "escalated"
    elif any(not have.get(f, True) for f in sub.required_fields):
        outcome = "flagged"
    else:
        outcome = "drafted"
    reasons = []
    if spec.get("usd_as_warqa"):
        reasons.append(f"ورقة: check amount_usd = {spec['usd_as_warqa']} x 100 = {spec['amount_usd']}")
    if spec["secondary_subcategory"]:
        reasons.append(f"two issues: check secondary ({spec['secondary_subcategory']})")
    return {"id": spec["spec_id"], "text": text, "category": spec["category"], "subcategory": spec["subcategory"],
            "secondary_subcategory": spec["secondary_subcategory"], "reference": ref, "recipient_phone": phone,
            "amount_iqd": spec["amount_iqd"], "amount_usd": spec["amount_usd"],
            "date": date if isinstance(date, str) and date.strip() else None,
            "priority": priority, "outcome": outcome, "dialect": spec["dialect"], "style": spec["style"],
            "difficulty": spec["difficulty"], "edge_case": spec["edge_case"], "split": split, "batch": batch,
            "generator_model": models()["generator"]["model"], "review_reason": reasons}


def tokens(norm: str) -> list[str]:
    """Content words with common dialect variants folded, so a sentence copied into another
    dialect still matches (dev-0083 / dev-0138 in the first build were 0.70 on characters)."""
    return [FOLD.get(w, w) for w in norm.split() if len(w) > 2]


FOLD = {"شنهو": "شنو", "ايش": "شنو", "اگدر": "اكدر", "اقدر": "اكدر", "هلا": "هلو", "مرحبا": "هلو",
        "هواي": "كلش", "كتير": "كلش"}


def existing_texts(exclude_split: str) -> list[str]:
    """Normalised texts of every other split and of the probe sets (never printed)."""
    out = []
    for split in SPLITS:
        if split == exclude_split:
            continue
        f = ROOT / "data" / split / "tickets.jsonl"
        if f.exists():
            out += [normalise(json.loads(l)["text"]) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    for f in (ROOT / "data/probes").glob("*.jsonl"):
        out += [normalise(json.loads(l)["text"]) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    return out


def similarity(a: str, b: str) -> tuple[float, float]:
    """(character ratio, content-word ratio) of two normalised texts; word ratio is 0 when
    either has fewer than DUP_TOKEN_MIN content words."""
    char = SequenceMatcher(None, a, b).ratio()
    ta, tb = tokens(a), tokens(b)
    word = SequenceMatcher(None, ta, tb).ratio() if min(len(ta), len(tb)) >= DUP_TOKEN_MIN else 0.0
    return char, word


def is_dup(norm: str, pool: list[str]) -> bool:
    for other in pool:
        if abs(len(other) - len(norm)) > 0.5 * max(len(norm), 1) + 10:
            continue
        char, word = similarity(norm, other)
        if char > DUP_THRESHOLD or word > DUP_TOKEN_THRESHOLD:
            return True
    return False


# ---------------------------------------------------------------- audit

def audit_system() -> str:
    prompt = cls.system_prompt()
    rules = prompt[prompt.index("## Categories"):prompt.index("## Confidence")].strip()
    return (ROOT / "scripts/prompts/audit_labels.md").read_text(encoding="utf-8").replace("{rules}", rules)


def audit_disputes(record: dict, label: dict) -> list[str]:
    out = []
    if label.get("subcategory") != record["subcategory"]:
        out.append(f"audit: subcategory {label.get('subcategory')} (gold {record['subcategory']})")
    if (label.get("secondary_subcategory") or None) != record["secondary_subcategory"]:
        out.append(f"audit: secondary {label.get('secondary_subcategory')} (gold {record['secondary_subcategory']})")
    for field in ("amount_iqd", "amount_usd"):
        got = label.get(field)
        try:
            got = None if got in (None, "") else int(float(got))
        except (TypeError, ValueError):
            got = "?"
        if got != record[field]:
            out.append(f"audit: {field} {got} (gold {record[field]})")
    gref, aref = record["reference"], label.get("reference")
    if (_key(gref) if gref else None) != (_key(str(aref)) if aref else None):
        out.append(f"audit: reference {'none' if not aref else 'differs'} (gold {'none' if not gref else 'given'})")
    return out


# ---------------------------------------------------------------- build

def build(split: str, seed: int, n: int) -> None:
    counters = Counters()
    cache = f"{split}-s{seed}"                        # new seed, new batches: old replies are never reused
    marker_counts = Counter()
    cap = math.floor(MARKER_CAP * n)
    # Numbers for {REF} / {PHONE} come from each spec's own generator, so they do not depend on
    # the order tickets are accepted in (a top-up run keeps every earlier ticket's text).
    def spec_rng(spec_id: str) -> random.Random:
        return random.Random(f"{seed}:{spec_id}")
    specs = make_specs(split, n, seed)
    system = (ROOT / "scripts/prompts/generate_tickets.md").read_text(encoding="utf-8")
    pool = existing_texts(split)
    accepted: dict[str, dict] = {}
    rejects = Counter()
    similar: dict[str, str] = {}      # spec -> its last draft rejected as a near-duplicate (sent back from round 7)
    for rnd in range(1, MAX_ROUNDS + 1):
        pending = [s for s in specs if s["spec_id"] not in accepted]
        if not pending:
            break
        batches = [pending[i:i + BATCH] for i in range(0, len(pending), BATCH)]
        avoid = sorted(m for m in MARKERS if marker_counts[m] >= cap)   # words already at the cap

        def run(args, rnd=rnd):
            b, chunk = args
            user = json.dumps([spec_for_prompt(s, rnd, avoid, similar.get(s["spec_id"]) if rnd > 6 else None)
                               for s in chunk], ensure_ascii=False, indent=1)
            try:
                return b, model_batch(cache, "gen", f"r{rnd}_b{b:02d}", "generator", system, user, counters)
            except Exception as e:  # noqa: BLE001 - a failed batch is simply retried next round
                return b, {"error": str(e)[:200]}

        with ThreadPoolExecutor(WORKERS) as ex:
            results = list(ex.map(run, enumerate(batches)))
        by_id = {s["spec_id"]: s for s in pending}
        for b, data in results:
            if isinstance(data, dict):
                rejects["batch_failed"] += 1
                continue
            for item in data:
                spec = by_id.get(item.get("spec_id")) if isinstance(item, dict) else None
                if spec is None or spec["spec_id"] in accepted:
                    continue
                text = item.get("text", "")
                bad = problems(spec, text)
                if bad:
                    rejects.update(bad)
                    continue
                rng = spec_rng(spec["spec_id"])
                ref = make_reference(rng) if spec["include_reference"] else None
                phone = make_phone(rng) if spec["include_phone"] else None
                filled = text.replace("{REF}", ref or "").replace("{PHONE}", phone or "").strip()
                if ref and not reference_in_text(ref, clean(filled)):
                    rejects["ref_not_in_text"] += 1
                    continue
                norm = normalise(filled)
                found = markers_in(norm)
                if any(marker_counts[m] + 1 > cap for m in found):
                    rejects["marker_over_cap"] += 1
                    continue
                if is_dup(norm, pool):
                    rejects["near_duplicate"] += 1
                    similar[spec["spec_id"]] = text
                    continue
                marker_counts.update(found)
                pool.append(norm)
                accepted[spec["spec_id"]] = gold(spec, filled, ref, phone, item.get("date"), split, f"r{rnd}_b{b:02d}")
        print(f"round {rnd}: {len(accepted)}/{n} accepted")

    # Blind audit (evaluator role): labels without the gold, disagreements go to review.
    records = [accepted[s["spec_id"]] for s in specs if s["spec_id"] in accepted]
    asys = audit_system()
    # Labels already saved for this split and seed are reused when the ticket text is unchanged
    # (a top-up run replays the same accepted tickets), so only new or changed tickets are audited.
    digest = {r["id"]: hashlib.sha256(r["text"].encode("utf-8")).hexdigest()[:16] for r in records}
    seen = ROOT / "runs/generation" / cache / "audited_texts.json"
    old = json.loads(seen.read_text(encoding="utf-8")) if seen.exists() else {}
    labels = {}
    for f in sorted((ROOT / "runs/generation" / cache).glob("audit_*.json")):
        for x in json.loads(f.read_text(encoding="utf-8")):
            if isinstance(x, dict) and x.get("id") in digest and old.get(x.get("id")) == digest[x.get("id")]:
                labels[x["id"]] = x
    todo = [r for r in records if r["id"] not in labels]
    chunks = [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]

    def audit(args):
        b, chunk = args
        user = json.dumps([{"id": r["id"], "text": r["text"]} for r in chunk], ensure_ascii=False, indent=1)
        name = "t" + hashlib.sha256(" ".join(digest[r["id"]] for r in chunk).encode()).hexdigest()[:10]
        try:
            return model_batch(cache, "audit", name, "evaluator", asys, user, counters)
        except Exception as e:  # noqa: BLE001
            return {"error": str(e)[:200]}

    with ThreadPoolExecutor(WORKERS) as ex:
        audits = list(ex.map(audit, enumerate(chunks)))
    for a, chunk in zip(audits, chunks):
        if isinstance(a, list):
            ids = {r["id"] for r in chunk}
            labels.update({x.get("id"): x for x in a if isinstance(x, dict) and x.get("id") in ids})
    old.update({i: digest[i] for i in labels})
    seen.parent.mkdir(parents=True, exist_ok=True)
    seen.write_text(json.dumps(old, indent=0), encoding="utf-8")
    unaudited = 0
    for r in records:
        if r["id"] in labels:
            r["review_reason"] += audit_disputes(r, labels[r["id"]])
        else:
            unaudited += 1
            r["review_reason"].append("audit: no label returned")

    worst = max(marker_counts.values(), default=0) / max(len(records), 1)
    if worst > MARKER_FAIL:
        raise SystemExit(f"build failed: a marker word is in {worst:.0%} of tickets (limit {MARKER_FAIL:.0%})")
    out = ROOT / "data" / split / "tickets.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps({**r, "review_reason": "; ".join(r["review_reason"]) or None}, ensure_ascii=False) + "\n")
    info = {"split": split, "seed": seed, "requested": n, "accepted": len(records),
            "model_calls_this_run": dict(counters.calls),
            "model_calls_total": {"generator": len(list((ROOT / "runs/generation" / cache).glob("gen_*.json"))),
                                  "evaluator": len(list((ROOT / "runs/generation" / cache).glob("audit_*.json")))},
            "rejected": dict(rejects), "unaudited": unaudited,
            "audit_disputed": sum(any(x.startswith("audit:") for x in r["review_reason"]) for r in records)}
    (ROOT / "data" / split / "build_info.json").write_text(json.dumps(info, indent=1, ensure_ascii=False) + "\n",
                                                            encoding="utf-8")
    print(json.dumps(info, indent=1, ensure_ascii=False))
    if not print_stats([split]):
        raise SystemExit("build failed: marker word over the limit")


# ---------------------------------------------------------------- stats and handcheck

def load(split: str) -> list[dict]:
    f = ROOT / "data" / split / "tickets.jsonl"
    return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()] if f.exists() else []


def table(title: str, rows: dict[str, Counter], keys: list[str]) -> None:
    print(f"\n{title}")
    print(f"  {'':24}" + "".join(f"{s:>10}" for s in rows))
    for k in keys:
        print(f"  {str(k):24}" + "".join(f"{rows[s].get(k, 0):>10}" for s in rows))


def marker_table(data: dict[str, list[dict]]) -> bool:
    """Share of tickets per split that contain each marker word; False if one is over MARKER_FAIL."""
    ok = True
    print(f"\nMarker words (% of tickets; cap {MARKER_CAP:.0%} at acceptance, build fails above {MARKER_FAIL:.0%})")
    print(f"  {'':24}" + "".join(f"{s:>10}" for s in data))
    found = {s: [markers_in(normalise(r["text"])) for r in v] for s, v in data.items()}
    for m in MARKERS:
        shares = {s: sum(m in f for f in found[s]) / len(found[s]) for s in data}
        ok &= all(x <= MARKER_FAIL for x in shares.values())
        flag = "  OVER" if any(x > MARKER_FAIL for x in shares.values()) else ""
        print(f"  {m:24}" + "".join(f"{shares[s]:>10.1%}" for s in data) + flag)
    print("  urgency words (info only, F15: they do not change priority)")
    for m, rx in _URGENCY_RE.items():
        print(f"  {m:24}" + "".join(f"{sum(bool(rx.search(normalise(r['text']))) for r in v) / len(v):>10.1%}"
                                    for v in data.values()))
    return ok


def print_stats(splits: list[str]) -> bool:
    """Counts only. Never prints ticket text. Returns False if a marker word is over MARKER_FAIL."""
    data = {s: load(s) for s in splits if load(s)}
    if not data:
        print("no tickets yet")
        return True
    tax = taxonomy()
    table("Tickets", {s: Counter({"total": len(v)}) for s, v in data.items()}, ["total"])
    table("Category", {s: Counter(r["category"] for r in v) for s, v in data.items()}, list(tax.categories))
    subs = {s: Counter(r["subcategory"] for r in v) for s, v in data.items()}
    table("Subcategory (min 3 per split)", subs, list(tax.subcategories))
    for s, c in subs.items():
        low = [k for k in tax.subcategories if c.get(k, 0) < MIN_PER_SUB]
        print(f"  {s}: {'all subcategories >= 3' if not low else 'BELOW 3: ' + ', '.join(low)}")
    table("Dialect", {s: Counter(r["dialect"] for r in v) for s, v in data.items()}, list(DIALECTS))
    table("Style", {s: Counter(r["style"] for r in v) for s, v in data.items()}, list(STYLES))
    table("Difficulty", {s: Counter(r["difficulty"] for r in v) for s, v in data.items()}, list(DIFFICULTY))
    table("Edge case", {s: Counter(r["edge_case"] or "none" for r in v) for s, v in data.items()},
          ["none"] + list(EDGE_TYPES))
    table("Priority", {s: Counter(r["priority"] for r in v) for s, v in data.items()}, ["P1", "P2", "P3"])
    table("Outcome", {s: Counter(r["outcome"] for r in v) for s, v in data.items()}, ["drafted", "flagged", "escalated"])
    table("Fields present", {s: Counter({"reference": sum(bool(r["reference"]) for r in v),
                                         "recipient_phone": sum(bool(r["recipient_phone"]) for r in v),
                                         "amount_iqd": sum(r["amount_iqd"] is not None for r in v),
                                         "amount_usd": sum(r["amount_usd"] is not None for r in v),
                                         "date": sum(bool(r["date"]) for r in v),
                                         "secondary": sum(bool(r["secondary_subcategory"]) for r in v)})
                              for s, v in data.items()},
          ["reference", "recipient_phone", "amount_iqd", "amount_usd", "date", "secondary"])

    def pct(v, q):
        xs = sorted(len(r["text"]) for r in v)
        return xs[min(len(xs) - 1, int(q * len(xs)))]
    table("Length (characters)", {s: Counter({"min": pct(v, 0), "p25": pct(v, .25), "median": pct(v, .5),
                                              "p75": pct(v, .75), "max": pct(v, 1)}) for s, v in data.items()},
          ["min", "p25", "median", "p75", "max"])
    reasons = {s: Counter() for s in data}
    for s, v in data.items():
        for r in v:
            rr = r["review_reason"] or ""
            reasons[s]["any review_reason"] += bool(rr)
            reasons[s]["audit disputed"] += "audit:" in rr
            reasons[s]["two issues"] += "two issues" in rr
            reasons[s]["ورقة (USD notes)"] += "ورقة" in rr
    table("Review reasons", reasons, ["any review_reason", "audit disputed", "two issues", "ورقة (USD notes)"])
    table("Amounts in USD", {s: Counter({"amount_usd": sum(r["amount_usd"] is not None for r in v),
                                         "as ورقة": sum(bool(has_warqa(r["text"])) for r in v)})
                             for s, v in data.items()}, ["amount_usd", "as ورقة"])
    return marker_table(data)


HANDCHECK_SPLITS = ["dev", "mvp_test"]            # never heldout
MIN_RANDOM = 30


def handcheck_must(r: dict) -> str | None:
    """Why a ticket has to be on the sheet, or None."""
    rr = r["review_reason"] or ""
    if "audit:" in rr:
        return "audit dispute"
    if r["secondary_subcategory"]:
        return "two issues"
    if r["amount_usd"] is not None or has_warqa(r["text"]):
        return "ورقة / USD"
    return None


def pick_spread(pool: list[dict], k: int, picked: list[dict], rng: random.Random) -> list[dict]:
    """k random tickets, each time from the subcategory and then the dialect least present so far."""
    pool = pool[:]
    rng.shuffle(pool)
    subs = Counter(r["subcategory"] for r in picked)
    dial = Counter(r["dialect"] for r in picked)
    out = []
    for _ in range(min(k, len(pool))):
        r = min(pool, key=lambda x: (subs[x["subcategory"]], dial[x["dialect"]]))
        pool.remove(r)
        out.append(r)
        subs[r["subcategory"]] += 1
        dial[r["dialect"]] += 1
    return out


def handcheck(seed: int, n: int = 80) -> None:
    """The sheet for a person to check, from dev and mvp_test only: every audit dispute, every
    two-issue ticket and every ticket with "ورقة" or a USD amount, then at least MIN_RANDOM random
    tickets spread across subcategories and dialects. If the must-check tickets leave fewer than
    MIN_RANDOM places, the sheet grows past n rather than drop any of them."""
    rng = random.Random(seed)
    rows = [r for s in HANDCHECK_SPLITS for r in load(s)]
    must = sorted([r for r in rows if handcheck_must(r)], key=lambda r: (r["split"] != "dev", r["id"]))
    rest = [r for r in rows if not handcheck_must(r)]
    k = max(n - len(must), MIN_RANDOM)
    picked = must + pick_spread(rest, k, must, rng)
    order = {r["id"]: i for i, r in enumerate(sorted(picked, key=lambda r: rng.random()))}
    picked.sort(key=lambda r: order[r["id"]])           # shuffled, so the checker does not see the groups
    out = ROOT / "data/review/handcheck_80.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "split", "text", "category", "subcategory", "secondary", "reference", "amount", "priority",
                    "outcome", "review_reason", "ok", "fix", "note"])
        for r in picked:
            amount = (f"{r['amount_iqd']} IQD" if r["amount_iqd"] is not None
                      else f"{r['amount_usd']} USD" if r["amount_usd"] is not None else "")
            w.writerow([r["id"], r["split"], r["text"], r["category"], r["subcategory"], r["secondary_subcategory"] or "",
                        r["reference"] or "", amount, r["priority"], r["outcome"], r["review_reason"] or "", "", "", ""])
    why = Counter(handcheck_must(r) for r in must)
    rand = [r for r in picked if not handcheck_must(r)]
    print(f"handcheck: {len(picked)} rows; by split {dict(Counter(r['split'] for r in picked))}")
    print(f"  must-check: {len(must)} {dict(why)}; random: {len(rand)}")
    print(f"  random by dialect {dict(Counter(r['dialect'] for r in rand))}; "
          f"subcategories covered by random {len({r['subcategory'] for r in rand})}, "
          f"by the whole sheet {len({r['subcategory'] for r in picked})} of {len(taxonomy().subcategories)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--split", required=True, choices=list(SPLITS))
    b.add_argument("--seed", type=int, required=True)
    b.add_argument("--n", type=int, required=True)
    h = sub.add_parser("handcheck")
    h.add_argument("--seed", type=int, default=4404)
    sub.add_parser("stats")
    p = sub.add_parser("plan", help="print the spec counts for a split without calling a model")
    p.add_argument("--split", required=True, choices=list(SPLITS))
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--n", type=int, required=True)
    args = ap.parse_args()
    if args.cmd == "build":
        build(args.split, args.seed, args.n)
    elif args.cmd == "handcheck":
        handcheck(args.seed)
    elif args.cmd == "stats":
        print_stats(list(SPLITS))
    else:
        specs = make_specs(args.split, args.n, args.seed)
        for field in ("category", "subcategory", "dialect", "style", "difficulty", "edge_case"):
            print(field, dict(Counter(s[field] or "none" for s in specs)))
        print("include_reference", sum(s["include_reference"] for s in specs),
              "include_phone", sum(s["include_phone"] for s in specs),
              "amount_iqd", sum(s["amount_iqd"] is not None for s in specs),
              "amount_usd", sum(s["amount_usd"] is not None for s in specs))


if __name__ == "__main__":
    main()
