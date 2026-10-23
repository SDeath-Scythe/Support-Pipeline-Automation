"""Generate the synthetic ticket dataset: dev 240, mvp_test 80, heldout 80.

    python scripts/generate_tickets.py build --split dev      --seed 1001 --n 240
    python scripts/generate_tickets.py build --split mvp_test --seed 2002 --n 80
    python scripts/generate_tickets.py build --split heldout  --seed 3003 --n 80   # its own run
    python scripts/generate_tickets.py handcheck --seed 4004    # data/review/handcheck_80.csv
    python scripts/generate_tickets.py stats                    # coverage tables, no ticket text

How a split is built:
1. A spec list is drawn deterministically from the seed: subcategory (category mix of a real
   L1 day, at least 3 per subcategory), dialect, style, difficulty, an optional tagged edge
   case, whether the ticket gives a reference / phone, and the exact amount to state.
2. The `generator` role (Opus) writes ~10 tickets per call and returns JSON only. It writes the
   placeholders {REF} and {PHONE}; code fills them, so gold reference / phone are exactly what
   was inserted. Amounts are given in the spec, so gold amounts are exact too.
3. Code validates (schema, taxonomy, placeholders, reference really in the text, no invented
   long numbers, no brand names, style sanity) and drops near-duplicates (normalised similarity
   > 0.85 against every other ticket in any split and the probe sets). Failed specs are
   regenerated (new `variation`) until the split is full.
4. Priority and outcome come from code: the taxonomy and routing rules with the recommended
   flags on (F7: "هسه" alone does not raise priority).
5. A blind audit: the `evaluator` role (Opus) labels every ticket without seeing its gold label.
   Disagreements never change gold; they go into `review_reason` for a person to check.

The script prints statistics only, never ticket text, so the heldout split stays unread.
Model replies are saved under runs/generation/<split>/ (git-ignored) so a re-run resumes.
"""

from __future__ import annotations

import argparse
import csv
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

# Priority uses the routing rules with the recommended flags on (only F7 affects routing).
os.environ["PIPELINE_FIXES"] = ("draft_check,recheck_cross_team,fee_followup,no_now_urgency,"
                                "ask_if_missing,no_specific_followup,fraud_secondary_cleanup")

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
MAX_ROUNDS = 5
DUP_THRESHOLD = 0.85

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
                    "(خمسين ورقة، ربع مليون، نص مليون، مليون ونص).",
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
        if edge == "usd_amount":
            s["amount_usd"] = rng.choice(USD_AMOUNTS)
        elif edge == "amount_slang":
            s["amount_iqd"] = rng.choice(SLANG_AMOUNTS)
        elif sub in AMOUNT_SUBS and rng.random() > 0.08:
            s["amount_iqd"] = rng.choice(AMOUNT_RANGES[sub])
        s["urgency"] = rng.random() < 0.12
    return specs


# ---------------------------------------------------------------- generation

def spec_for_prompt(s: dict, variation: int) -> dict:
    tax = taxonomy()
    sub = tax.get(s["subcategory"])
    out = {"spec_id": s["spec_id"],
           "issue": {"key": s["subcategory"], "label": sub.label, "description": DESCRIPTIONS[s["subcategory"]]},
           "dialect": s["dialect"], "style": s["style"], "difficulty": s["difficulty"],
           "include_reference": s["include_reference"], "include_phone": s["include_phone"],
           "urgency": s["urgency"], "variation": variation}
    if s["secondary_subcategory"]:
        sec = s["secondary_subcategory"]
        out["second_issue"] = {"key": sec, "label": tax.get(sec).label, "description": DESCRIPTIONS[sec]}
    if s["edge_case"]:
        out["edge_case"] = {"type": s["edge_case"], "instruction": EDGE_TYPES[s["edge_case"]]}
    if s["amount_iqd"] is not None:
        out["amount_iqd"] = s["amount_iqd"]
    if s["amount_usd"] is not None:
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
    """One model call, saved to runs/generation/<split>/ so re-runs resume instead of re-paying."""
    path = ROOT / "runs/generation" / split / f"{kind}_{name}.json"
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
    if spec["amount_usd"] is not None and not re.search(r"دولار|\$|usd|dollar|dolar", low):
        out.append("usd_not_stated")
    return out


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
    if re.search("هسه", text):
        reasons.append("contains هسه: check priority (F7 on, so it does not raise priority alone)")
    if spec["secondary_subcategory"]:
        reasons.append(f"two issues: check secondary ({spec['secondary_subcategory']})")
    return {"id": spec["spec_id"], "text": text, "category": spec["category"], "subcategory": spec["subcategory"],
            "secondary_subcategory": spec["secondary_subcategory"], "reference": ref, "recipient_phone": phone,
            "amount_iqd": spec["amount_iqd"], "amount_usd": spec["amount_usd"],
            "date": date if isinstance(date, str) and date.strip() else None,
            "priority": priority, "outcome": outcome, "dialect": spec["dialect"], "style": spec["style"],
            "difficulty": spec["difficulty"], "edge_case": spec["edge_case"], "split": split, "batch": batch,
            "generator_model": models()["generator"]["model"], "review_reason": reasons}


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


def is_dup(norm: str, pool: list[str]) -> bool:
    for other in pool:
        if abs(len(other) - len(norm)) > 0.3 * max(len(norm), 1) + 10:
            continue
        if SequenceMatcher(None, norm, other).ratio() > DUP_THRESHOLD:
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
    rng = random.Random(seed * 7 + 1)                # numbers for {REF} / {PHONE}
    specs = make_specs(split, n, seed)
    system = (ROOT / "scripts/prompts/generate_tickets.md").read_text(encoding="utf-8")
    pool = existing_texts(split)
    accepted: dict[str, dict] = {}
    rejects = Counter()
    for rnd in range(1, MAX_ROUNDS + 1):
        pending = [s for s in specs if s["spec_id"] not in accepted]
        if not pending:
            break
        batches = [pending[i:i + BATCH] for i in range(0, len(pending), BATCH)]

        def run(args, rnd=rnd):
            b, chunk = args
            user = json.dumps([spec_for_prompt(s, rnd) for s in chunk], ensure_ascii=False, indent=1)
            try:
                return b, model_batch(split, "gen", f"r{rnd}_b{b:02d}", "generator", system, user, counters)
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
                ref = make_reference(rng) if spec["include_reference"] else None
                phone = make_phone(rng) if spec["include_phone"] else None
                filled = text.replace("{REF}", ref or "").replace("{PHONE}", phone or "").strip()
                if ref and not reference_in_text(ref, clean(filled)):
                    rejects["ref_not_in_text"] += 1
                    continue
                norm = normalise(filled)
                if is_dup(norm, pool):
                    rejects["near_duplicate"] += 1
                    continue
                pool.append(norm)
                accepted[spec["spec_id"]] = gold(spec, filled, ref, phone, item.get("date"), split, f"r{rnd}_b{b:02d}")
        print(f"round {rnd}: {len(accepted)}/{n} accepted")

    # Blind audit (evaluator role): labels without the gold, disagreements go to review.
    records = [accepted[s["spec_id"]] for s in specs if s["spec_id"] in accepted]
    asys = audit_system()
    chunks = [records[i:i + BATCH] for i in range(0, len(records), BATCH)]

    def audit(args):
        b, chunk = args
        user = json.dumps([{"id": r["id"], "text": r["text"]} for r in chunk], ensure_ascii=False, indent=1)
        try:
            return model_batch(split, "audit", f"b{b:02d}", "evaluator", asys, user, counters)
        except Exception as e:  # noqa: BLE001
            return {"error": str(e)[:200]}

    with ThreadPoolExecutor(WORKERS) as ex:
        audits = list(ex.map(audit, enumerate(chunks)))
    labels = {}
    for a in audits:
        if isinstance(a, list):
            labels.update({x.get("id"): x for x in a if isinstance(x, dict)})
    unaudited = 0
    for r in records:
        if r["id"] in labels:
            r["review_reason"] += audit_disputes(r, labels[r["id"]])
        else:
            unaudited += 1
            r["review_reason"].append("audit: no label returned")

    out = ROOT / "data" / split / "tickets.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps({**r, "review_reason": "; ".join(r["review_reason"]) or None}, ensure_ascii=False) + "\n")
    info = {"split": split, "seed": seed, "requested": n, "accepted": len(records),
            "model_calls_this_run": dict(counters.calls),
            "model_calls_total": {"generator": len(list((ROOT / "runs/generation" / split).glob("gen_*.json"))),
                                  "evaluator": len(list((ROOT / "runs/generation" / split).glob("audit_*.json")))},
            "rejected": dict(rejects), "unaudited": unaudited,
            "audit_disputed": sum(any(x.startswith("audit:") for x in r["review_reason"]) for r in records)}
    (ROOT / "data" / split / "build_info.json").write_text(json.dumps(info, indent=1, ensure_ascii=False) + "\n",
                                                            encoding="utf-8")
    print(json.dumps(info, indent=1, ensure_ascii=False))
    print_stats([split])


# ---------------------------------------------------------------- stats and handcheck

def load(split: str) -> list[dict]:
    f = ROOT / "data" / split / "tickets.jsonl"
    return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()] if f.exists() else []


def table(title: str, rows: dict[str, Counter], keys: list[str]) -> None:
    print(f"\n{title}")
    print(f"  {'':24}" + "".join(f"{s:>10}" for s in rows))
    for k in keys:
        print(f"  {str(k):24}" + "".join(f"{rows[s].get(k, 0):>10}" for s in rows))


def print_stats(splits: list[str]) -> None:
    """Counts only. Never prints ticket text."""
    data = {s: load(s) for s in splits if load(s)}
    if not data:
        print("no tickets yet")
        return
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
            reasons[s]["contains هسه"] += "هسه" in rr
    table("Review reasons", reasons, ["any review_reason", "audit disputed", "two issues", "contains هسه"])


def handcheck(seed: int, n: int = 80) -> None:
    rng = random.Random(seed)
    rows = [r for s in SPLITS for r in load(s)]
    def rank(r):
        rr = r["review_reason"] or ""
        return 0 if "audit:" in rr else 1 if "two issues" in rr else 2
    review = sorted([r for r in rows if r["review_reason"]], key=lambda r: (rank(r), r["id"]))
    picked = review[:n]
    left = n - len(picked)
    if left > 0:
        rest = {s: [r for r in rows if r["split"] == s and not r["review_reason"]] for s in SPLITS}
        share = {"dev": 0.5, "mvp_test": 0.25, "heldout": 0.25}
        quota = {s: int(left * share[s]) for s in SPLITS}
        quota["dev"] += left - sum(quota.values())
        for s in SPLITS:
            picked += rng.sample(rest[s], min(quota[s], len(rest[s])))
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
    by_split = Counter(r["split"] for r in picked)
    print(f"handcheck: {len(picked)} rows ({len(review)} with a review_reason"
          f"{', ' + str(len(review) - n) + ' did not fit' if len(review) > n else ''}); by split: {dict(by_split)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--split", required=True, choices=list(SPLITS))
    b.add_argument("--seed", type=int, required=True)
    b.add_argument("--n", type=int, required=True)
    h = sub.add_parser("handcheck")
    h.add_argument("--seed", type=int, default=4004)
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
