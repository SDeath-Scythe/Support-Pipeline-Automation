"""F17 (handoff_note): a short Arabic note for the team that receives an escalated ticket.

Escalated tickets (all fraud included) get no draft, so the receiving team used to see only a
flag label such as "احتمال احتيال". This note tells them, in a few lines, what the ticket is
about, what was extracted, what is missing and why it was escalated.

It is built from fields the pipeline already has: no model call, nothing it can invent, and
it cannot change classification. Values are copied as extracted; the team still reads the ticket.
"""

from __future__ import annotations

from .config import taxonomy, thresholds
from .draft import FIELD_AR, _have, ask_for
from .requirements import missing_required
from .schemas import Extraction

# Fields the pipeline can check in a ticket (others, like a shop name, it can't see).
_CHECKABLE = {"reference", "amount", "date", "recipient_number", "phone_number"}

# Escalations the system decides rather than the ticket (run.py): why the team got it. (account_risk
# is not one: since 5 Nov it flags a draft and never escalates; see IDENTITY_AR below.)
_SYSTEM_REASONS = {
    "too_long": "التذكرة أطول من الحد المسموح، فما انرسلت للنموذج",
    "pipeline_off": "النظام موقف، فما انرسلت للنموذج",
    "drafts_off": "المسودات موقفة: الرد على الزبون عليك",
    "cancelled": "انلغت المعالجة قبل ما تكمل",
    "internal_error": "صار خطأ داخلي بالنظام",
    "budget_reached": "وصل التشغيل لحد الصرف المسموح، فما كملت المعالجة",
}

# A line each for what the code rules found in the customer's text (run.py, ticket_rules.py), after
# the reasons. When they find nothing, the note has no such line.
NOTE_AR = {
    "secret_in_ticket": "رمز سري: الزبون كتب رقم بطاقة أو رمز سري بالرسالة. نبّهه يغيّر الرمز ويوقف البطاقة، "
                        "ولا تكرر الرقم بالرد",
    "other_phone": "رقم ثاني: الزبون يكتب من رقم مو رقمه، فتأكد من هويته قبل أي تغيير على الحساب",
    "complaint_risk": "شكوى: الزبون يهدد بشكوى للجهات الرقابية أو راسلنا أكثر من مرة",
    "bidi_controls": "رموز مخفية: بالرسالة رموز تغيّر ترتيب الكتابة، فقارن المبلغ والأرقام بالرسالة",
    "amount_disagreed": "المبلغ: النموذجين قروا مبلغ مختلف، فتأكد منه بالرسالة",
    "instructions_in_ticket": "كلام للنظام: بالتذكرة كلام موجّه للنظام، وما انعمل بيه",
}


def _label(key: str | None) -> str | None:
    tax = taxonomy()
    sub = tax.subcategories.get(key or "")
    return f"{tax.categories_ar[sub.category]} › {sub.label_ar}" if sub else None


def _facts(ex: Extraction) -> list[str]:
    out = []
    if ex.amount_iqd is not None:
        out.append(f"المبلغ {ex.amount_iqd:,} دينار")
    elif ex.amount_usd is not None:
        out.append(f"المبلغ {ex.amount_usd:,} دولار")
    if getattr(ex, "fee_iqd", None) is not None:
        out.append(f"الرسوم المعترض عليها {ex.fee_iqd:,} دينار")
    if ex.reference:
        out.append(f"رقم العملية {ex.reference}")
    if ex.recipient_phone:
        out.append(f"رقم المستلم {ex.recipient_phone}")
    if ex.date:
        out.append(f"الوقت: {ex.date}")
    return out


def _missing(ex: Extraction) -> list[str]:
    sub = taxonomy().subcategories.get(ex.subcategory)
    if sub is None or sub.always_escalate:
        return []
    wanted = missing_required(ex, sub.required_fields) + [f for f in ask_for(ex) if f in _CHECKABLE]
    seen, out = set(), []
    for f in wanted:
        if f not in seen and not _have(ex, f):
            seen.add(f)
            out.append(FIELD_AR.get(f, f))
    return out


def _reasons(flags: list[str], confidence: float | None, first: Extraction | None,
             second: Extraction | None) -> list[str]:
    out = []
    if "fraud" in flags:
        out.append("احتمال احتيال")
    if "recheck_disagreed" in flags and first is not None and second is not None:
        out.append(f"النموذجين اختلفوا: الأول قال «{_label(first.subcategory) or first.subcategory}» "
                   f"والثاني «{_label(second.subcategory) or second.subcategory}»")
    if "invalid_category" in flags:
        out.append("التصنيف ما يطابق قائمة الأقسام")
    if "device_lost" in flags:
        out.append("الموبايل ضايع أو مسروق والمحفظة مفتوحة عليه، فيحتاج تجميد الحساب بسرعة")
    if "model_error" in flags:
        out.append("صار خطأ بالنموذج، فاقرا التذكرة كاملة")
    out += [why for flag, why in _SYSTEM_REASONS.items() if flag in flags]
    if not out and confidence is not None and confidence < thresholds()["confidence"]["recheck_from"]:
        out.append(f"الثقة واطية ({confidence:.2f}): نوع المشكلة مو واضح")
    return out


# A blocked account or a SIM change that escalated anyway: the person who takes it writes the reply, so the
# note reminds them of what the account_risk flag asks of a drafted one (run.py, 5 Nov review).
IDENTITY_AR = "هوية الزبون: إذا رديت عليه، تأكد من هويته حسب الإجراءات أول، ولا تكتب بالرد إنه صار أي تغيير على الحساب"


def note(ex: Extraction | None, flags: list[str], *, confidence: float | None = None,
         second: Extraction | None = None, cleared_secondary: str | None = None,
         summary: str | None = None, identity: bool = False) -> str:
    """The handoff note, one short line per part. `ex` is the answer the ticket was routed on
    (None if classification failed); `second` is the re-check's answer when the models disagreed.
    `identity`: either answer is a blocked account or a SIM change (run.py decides), so the note
    ends with the identity reminder."""
    if ex is None:
        system = [why for flag, why in _SYSTEM_REASONS.items() if flag in flags]
        if system and "model_error" not in flags:
            return "سبب التصعيد: " + "؛ ".join(system) + ". اقرا التذكرة كاملة."
        return "سبب التصعيد: صار خطأ بالنموذج وما انقرت التذكرة. اقراها كاملة."
    main = second if second is not None and "fraud" in flags and second.category == "fraud_security" else ex
    # When the type itself is in doubt, say so instead of presenting one answer as the topic.
    unsure = "invalid_category" in flags or ("recheck_disagreed" in flags and second is not None)
    lines = ["الموضوع: نوع المشكلة غير محسوم (شوف سبب التصعيد)" if unsure
             else f"الموضوع: {_label(main.subcategory) or main.subcategory}"]
    if summary:   # F21: what happened, in one line (a model wrote it from the ticket alone)
        lines.append(f"الخلاصة: {summary}")

    secondary = main.secondary_subcategory or cleared_secondary
    if secondary and secondary != main.subcategory and _label(secondary) and not unsure:
        tax = taxonomy()
        # A fraud ticket's account lock or unknown charge is part of the same incident (F14b), not a request.
        is_effect = main.category == "fraud_security" and tax.get(secondary).category in ("account_access", "fraud_security")
        lines.append(f"{'أثر على الحساب' if is_effect else 'طلب ثاني'}: {tax.get(secondary).label_ar}")

    facts = _facts(main)
    if facts:
        lines.append("المعلومات: " + " · ".join(facts))
    missing = [] if unsure else _missing(main)   # what's missing depends on the type
    if missing:
        lines.append("ناقص: " + "، ".join(missing))
    reasons = _reasons(flags, confidence, ex, second)
    if reasons:
        lines.append("سبب التصعيد: " + "؛ ".join(reasons))
    lines += [line for flag, line in NOTE_AR.items() if flag in flags]
    if identity:
        lines.append(IDENTITY_AR)
    return "\n".join(lines)
