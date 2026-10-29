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
    if "model_error" in flags:
        out.append("صار خطأ بالنموذج: اقرأ التذكرة كاملة")
    if not out and confidence is not None and confidence < thresholds()["confidence"]["recheck_from"]:
        out.append(f"الثقة واطية ({confidence:.2f}): نوع المشكلة مو واضح")
    return out


def note(ex: Extraction | None, flags: list[str], *, confidence: float | None = None,
         second: Extraction | None = None, cleared_secondary: str | None = None,
         summary: str | None = None) -> str:
    """The handoff note, one short line per part. `ex` is the answer the ticket was routed on
    (None if classification failed); `second` is the re-check's answer when the models disagreed."""
    if ex is None:
        return "سبب التصعيد: صار خطأ بالنموذج وما انقرت التذكرة. اقرأها كاملة."
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
        is_effect = main.category == "fraud_security" and tax.get(secondary).category == "account_access"
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
    return "\n".join(lines)
