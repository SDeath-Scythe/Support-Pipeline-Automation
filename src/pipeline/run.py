"""Run one ticket through every stage, emitting an event as each stage starts and finishes.

    process(text, emit=print)

Each event is a dict: {"stage", "status", "data", "ms"}. status is "running", "done",
"skipped" or "error". The viewer streams these to the browser; logging will store them.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from typing import Any

from . import classify as cls
from . import draft as drf
from . import draft_check
from . import handoff
from .clean import _DIGITS, _TATWEEL, clean
from .config import load_yaml, taxonomy
from .fixes import enabled
from .gate import check
from .llm import backend, call, last_usage, model_for
from .route import route
from .schemas import Extraction, Outcome

Emit = Callable[[dict[str, Any]], None]

FEE_SUBCATEGORIES = ("overcharged_fee", "fees_limits_question")

STAGES = ["received", "clean", "classify", "gate", "recheck", "route", "draft", "result"]

FLAG_AR = {
    "fraud": "احتمال احتيال: يتابعها قسم الاحتيال مباشرة",
    "invalid_category": "التصنيف ما يطابق قائمة الأقسام",
    "ref_not_in_text": "رقم العملية المستخرج مو موجود بنص التذكرة",
    "missing:reference": "رقم العملية ناقص",
    "missing:amount": "المبلغ ناقص",
    "recheck_disagreed": "النموذج الثاني صنّفها بشكل مختلف",
    "recheck_same_team": "النموذجين اختلفوا بالنوع بس نفس القسم: تأكد من نوع المشكلة قبل الاعتماد",
    "recheck_used_second": "النموذجين اختلفوا: اعتمدنا جواب المراجعة الثانية، تأكد من نوع المشكلة",
    "model_error": "صار خطأ بالنموذج، تحتاج مراجعة يدوية",
    "draft:stray_latin": "المسودة بيها حروف إنكليزية بغير مكانها",
    "draft:promise": "المسودة توعد بنتيجة أو وقت: تأكد قبل الاعتماد",
    "draft:asks_secret": "المسودة تطلب رمز أو كلمة سر: لا تعتمدها",
    "draft:unknown_number": "المسودة بيها رقم مو موجود بالتذكرة أو المعلومات",
}


def _clean_changes(raw: str) -> dict[str, int]:
    return {
        "arabic_digits": sum(1 for ch in raw if ch.translate(_DIGITS) != ch),
        "tatweel": raw.count(_TATWEEL),
        "extra_spaces": len(re.findall(r"\s{2,}|\n", raw)) + (raw != raw.strip()),
    }


# F14b (fraud_secondary_cleanup): rule 1 of the classifier prompt (fraud: put the other issue in
# secondary) contradicts rule 5 (a consequence is not a second issue), so "gave my code, now locked
# out" sometimes got login_otp as secondary. Rewording the prompt (F14) shifted other classifications,
# so this is enforced in code: a consequence of the fraud is cleared, a separate request is kept.
_FRAUD_CONSEQUENCES = ("account_access", "fraud_security")


def _clean_secondary(ex: Extraction) -> Extraction:
    tax = taxonomy()
    sec = tax.subcategories.get(ex.secondary_subcategory or "")
    if ex.category == "fraud_security" and sec is not None and sec.category in _FRAUD_CONSEQUENCES:
        return ex.model_copy(update={"secondary_subcategory": None})
    return ex


def _model_step(role: str, system: str, user: str) -> tuple[Extraction, dict[str, Any]]:
    t0 = time.time()
    reply = call(role, system, user)
    ex = cls.parse(reply)
    cleared = None
    if enabled("fraud_secondary_cleanup"):
        before = ex.secondary_subcategory
        ex = _clean_secondary(ex)
        cleared = before if before and ex.secondary_subcategory is None else None
    return ex, {
        "role": role,
        "model": model_for(role),
        "backend": backend(),
        "seconds": round(time.time() - t0, 1),
        "user_prompt": user,
        "reply": reply,
        "extraction": ex.model_dump(),
        "usage": last_usage(),
        **({"cleared_secondary": cleared} if cleared else {}),
    }


def process(raw_text: str, emit: Emit = lambda e: None) -> dict[str, Any]:
    started = time.time()

    def send(stage: str, status: str, data: dict[str, Any] | None = None) -> None:
        emit({"stage": stage, "status": status, "data": data or {}, "ms": int((time.time() - started) * 1000)})

    # What the handoff note (F17) needs, filled in as the stages run.
    ctx: dict[str, Any] = {"ex": None, "confidence": None, "second": None, "cleared": None}

    def finish(outcome: Outcome, flags: list[str], **extra: Any) -> dict[str, Any]:
        result = {"outcome": outcome.value, "flags": flags,
                  "notes_ar": [FLAG_AR.get(f, f) for f in flags], **extra}
        if outcome == Outcome.ESCALATED and enabled("handoff_note"):
            result["handoff_ar"] = handoff.note(ctx["ex"], flags, confidence=ctx["confidence"],
                                                second=ctx["second"], cleared_secondary=ctx["cleared"])
        send("result", "done", result)
        return result

    tax = taxonomy()
    send("received", "done", {"text": raw_text, "chars": len(raw_text)})

    # 1. Clean (rules)
    text = clean(raw_text)
    send("clean", "done", {"text": text, "changes": _clean_changes(raw_text)})

    # 2. Classify + extract (classifier model)
    send("classify", "running", {"model": model_for("classifier"), "backend": backend()})
    try:
        ex, info = _model_step("classifier", cls.system_prompt(), cls.user_prompt(text))
    except Exception as e:  # noqa: BLE001
        send("classify", "error", {"error": f"{type(e).__name__}: {e}"})
        for s in ("gate", "recheck", "route", "draft"):
            send(s, "skipped")
        return finish(Outcome.ESCALATED, ["model_error"])
    ctx.update(ex=ex, cleared=info.get("cleared_secondary"))
    sub = tax.subcategories.get(ex.subcategory)
    info["labels"] = {
        "category": tax.categories.get(ex.category, ex.category),
        "subcategory": sub.label if sub else ex.subcategory,
    }
    send("classify", "done", info)

    # 3. Confidence gate (rules)
    gate = check(ex, text)
    decision = "escalate" if gate.escalate else ("recheck" if gate.needs_recheck else "pass")
    send("gate", "done", {**gate.model_dump(), "model_confidence": ex.confidence, "decision": decision,
                          "high_risk": bool(sub and sub.high_risk)})
    flags = list(gate.flags)
    ctx["confidence"] = gate.confidence

    if gate.escalate:
        for s in ("recheck",):
            send(s, "skipped", {"why": "البوابة صعّدتها"})
        team, priority = route(ex, text) if sub else ("general", "P2")
        send("route", "done", {"team": team, "team_ar": tax.teams[team]["label_ar"], "priority": priority})
        send("draft", "skipped", {"why": "متصعّدة: يستلمها موظف"})
        return finish(Outcome.ESCALATED, flags, team=team, priority=priority, extraction=ex.model_dump())

    # 4. Re-check (second model, classifies blind)
    alternative = None
    if gate.needs_recheck:
        send("recheck", "running", {"model": model_for("rechecker"), "backend": backend()})
        try:
            ex2, info2 = _model_step("rechecker", cls.system_prompt(), cls.user_prompt(text))
            agree = ex2.subcategory == ex.subcategory
            info2.update(agree=agree, first=ex.subcategory, second=ex2.subcategory)
            send("recheck", "done", info2)
            # F3 (recheck_same_team): a disagreement inside one team still gets a draft, flagged.
            sub2 = tax.subcategories.get(ex2.subcategory)
            same_team = (not agree and sub is not None and sub2 is not None and sub2.team == sub.team
                         and not sub2.always_escalate)
            # F3b / F3c: the re-check model was right in most disagreements, so draft from its answer
            # (same team only for F3b, any team for F3c). Never for fraud.
            use_second = (not agree and sub2 is not None and not sub2.always_escalate
                          and (enabled("recheck_cross_team") or (same_team and enabled("recheck_use_second"))))
            gate2 = check(ex2, text) if use_second else None
            if use_second and not gate2.escalate:
                alternative, ex, sub = ex.subcategory, ex2, sub2
                flags = list(gate2.flags) + ["recheck_used_second"]
                ctx.update(ex=ex, confidence=gate2.confidence, cleared=info2.get("cleared_secondary"))
            elif same_team and enabled("recheck_same_team"):
                flags.append("recheck_same_team")
                alternative = ex2.subcategory
            elif not agree or ex2.category == "fraud_security":
                flags.append("fraud" if ex2.category == "fraud_security" else "recheck_disagreed")
                ctx["second"] = ex2
                team, priority = route(ex2 if ex2.category == "fraud_security" else ex, text)
                send("route", "done", {"team": team, "team_ar": tax.teams[team]["label_ar"], "priority": priority})
                send("draft", "skipped", {"why": "المراجعة ما اتفقت: الموظف يقرر"})
                return finish(Outcome.ESCALATED, flags, team=team, priority=priority, extraction=ex.model_dump())
        except Exception as e:  # noqa: BLE001
            send("recheck", "error", {"error": f"{type(e).__name__}: {e}"})
            send("route", "skipped")
            send("draft", "skipped")
            return finish(Outcome.ESCALATED, flags + ["model_error"], extraction=ex.model_dump())
    else:
        send("recheck", "skipped", {"why": f"الثقة {gate.confidence:.2f} عالية والنوع مو حساس"})

    # F6b (fee_followup): fee tickets get a small extra call for the disputed fee, so the
    # classifier prompt (and its accuracy) stays as it is. Round 3 showed F6's prompt change
    # shifted some classifications.
    fee_call: dict[str, Any] = {}
    if enabled("fee_followup") and ex.subcategory in FEE_SUBCATEGORIES and ex.fee_iqd is None:
        try:
            fee_reply = call("classifier", cls.fee_prompt(), cls.user_prompt(text))
            ex = ex.model_copy(update={"fee_iqd": cls.parse_fee(fee_reply)})
            fee_call = {"fee_call": {"reply": fee_reply, "fee_iqd": ex.fee_iqd}, "usage": last_usage()}
        except Exception:  # noqa: BLE001 - the fee is a nice-to-have; carry on without it
            pass

    # 5. Route + priority (rules)
    team, priority = route(ex, text)
    send("route", "done", {"team": team, "team_ar": tax.teams[team]["label_ar"], "priority": priority, **fee_call})

    # 6. Draft. F8 (unclear_template): an unclear ticket gets the fixed reply, no model call.
    if enabled("unclear_template") and ex.subcategory == "unclear":
        reply = load_yaml("templates.yaml")["unclear_ar"].strip()
        checks = draft_check.problems(reply, text) if enabled("draft_check") else []
        flags += [f"draft:{p}" for p in checks]
        send("draft", "done", {"model": "قالب ثابت", "template": True, "seconds": 0, "reply": reply,
                               "user_prompt": "(قالب من config/templates.yaml، بدون نموذج)", "ask_for": [],
                               "checks": checks})
        outcome = Outcome.FLAGGED if flags else Outcome.DRAFTED
        return finish(outcome, flags, team=team, priority=priority, draft_ar=reply, extraction=ex.model_dump())

    send("draft", "running", {"model": model_for("drafter"), "backend": backend(),
                              "ask_for": drf.ask_for(ex)})
    t0 = time.time()
    user = drf.user_prompt(text, ex, team)
    try:
        reply = drf.draft(text, ex, team)
    except Exception as e:  # noqa: BLE001
        send("draft", "error", {"error": f"{type(e).__name__}: {e}"})
        return finish(Outcome.ESCALATED, flags + ["model_error"], team=team, priority=priority)
    checks = draft_check.problems(reply, user) if enabled("draft_check") else []
    flags += [f"draft:{p}" for p in checks]
    send("draft", "done", {"model": model_for("drafter"), "backend": backend(),
                           "seconds": round(time.time() - t0, 1), "user_prompt": user, "reply": reply,
                           "ask_for": drf.ask_for(ex), "checks": checks, "usage": last_usage()})

    outcome = Outcome.FLAGGED if flags else Outcome.DRAFTED
    extra = {"recheck_alternative": alternative} if alternative else {}
    if fee_call:
        extra["fee_followup"] = True
    return finish(outcome, flags, team=team, priority=priority, draft_ar=reply, extraction=ex.model_dump(), **extra)
