"""Run one ticket through every stage, emitting an event as each stage starts and finishes.

    process(text, emit=print, should_stop=None)

Each event is a dict: {"stage", "status", "data", "ms"}. status is "running", "done",
"skipped" or "error". The viewer streams these to the browser; logging will store them.

process() never raises: whatever goes wrong, the ticket ends escalated to a person and a "result"
event is always emitted. An error event says what failed in fixed Arabic text plus the exception's
type, never its message (which can quote a model reply, the ticket or a file path); the traceback
goes to stderr only.
"""

from __future__ import annotations

import logging
import re
import time
import traceback
import unicodedata
from pathlib import Path
from collections.abc import Callable
from typing import Any

from . import classify as cls
from . import draft as drf
from . import draft_check, fixes, handoff, ticket_rules
from .clean import _DIGITS, _TATWEEL, clean, sensitive_numbers
from .config import limits, pipeline_mode, taxonomy
from .gate import check
from .llm import (BackendError, BudgetExceeded, CacheMiss, backend, before_retry, call, last_usage, model_for,
                  real_data)
from .route import route
from .schemas import Extraction, Outcome

Emit = Callable[[dict[str, Any]], None]

log = logging.getLogger(__name__)

FEE_SUBCATEGORIES = ("overcharged_fee", "fees_limits_question")

# A blocked account or a new SIM is a common step in taking over someone else's account. The draft is
# kept, flagged account_risk: the agent confirms the customer's identity by the institution's own
# procedure before approving (the author's decision, 5 Nov; it replaced the escalate_account_risk flag,
# which escalated them with no draft). It reads the type the draft was written for, after the re-check.
ACCOUNT_RISK = ("blocked_account", "sim_change")

STAGES = ["received", "clean", "classify", "gate", "recheck", "route", "draft", "result"]

# Flags from the code rules on the customer's text (ticket_rules.py, each behind its fixes.py flag), added
# to every outcome. A quiet one is shown but doesn't move a drafted ticket to «تحتاج تأكيد».
QUIET_FLAGS = ("instructions_in_ticket",)
# device_lost: a lost or stolen phone with the wallet open on it goes where fraud goes.
SECURITY_TEAM, SECURITY_PRIORITY = "fraud", "P1"

FLAG_AR = {
    "fraud": "احتمال احتيال: يتابعها قسم الاحتيال مباشرة",
    "invalid_category": "التصنيف ما يطابق قائمة الأقسام",
    "ref_not_in_text": "رقم العملية المستخرج مو موجود بنص التذكرة",
    "missing:reference": "رقم العملية ناقص",
    "missing:amount": "المبلغ ناقص",
    "recheck_disagreed": "النموذج الثاني صنّفها بشكل مختلف",
    "recheck_used_second": "النموذجين اختلفوا: اعتمدنا جواب المراجعة الثانية، تأكد من نوع المشكلة",
    "model_error": "صار خطأ بالنموذج، تحتاج مراجعة يدوية",
    "budget_reached": "وصل التشغيل لحد الصرف المسموح: تحتاج مراجعة يدوية",
    "draft:stray_latin": "المسودة بيها حروف إنكليزية بغير مكانها",
    "draft:promise": "المسودة توعد بنتيجة أو وقت: تأكد قبل الاعتماد",
    "draft:asks_secret": "المسودة تطلب رمز أو كلمة سر: لا تعتمدها",
    "draft:unknown_number": "المسودة بيها رقم مو موجود بالتذكرة أو المعلومات",
    "draft:hold_reason": "المسودة تذكر تحقيق أو اشتباه أو بلاغ: لا تعتمدها، ممنوع نخبر الزبون",
    "draft:sensitive_number": "المسودة تكرر رقم بطاقة أو رمز: احذفه قبل الاعتماد",
    # The warnings behind flags (fixes.py), shown only while their flag is on.
    "draft:claims_done": "المسودة تگول شي انسوى وإحنا ما سويناه: تأكد قبل الاعتماد",
    "draft:repeated_text": "المسودة بيها ترحيب أو جملة مكررة",
    "draft:ask_missing": "المسودة ما تسأل عن كل اللي ناقص",
    "draft:dialect_words": "المسودة بيها كلمة مو عراقية",
    "draft:amount_not_in_ticket": "المسودة تذكر مبلغ بالأرقام والزبون ما كاتبه هيچ: قارنه بالرسالة",
    "account_risk": "حساب مقفول أو تبديل شريحة: تأكد من هوية الزبون حسب الإجراءات قبل الاعتماد، "
                    "ولا تكتب بالرد إنه صار أي تغيير على الحساب",
    # The code rules on the customer's text, shown while their flag (fixes.py) is on.
    "secret_in_ticket": "الزبون كتب رقم بطاقة أو رمز سري: نبّهه يغيّر الرمز ويوقف البطاقة، ولا تكرر الرقم بالرد",
    "bidi_controls": "بالرسالة رموز مخفية تغيّر ترتيب الكتابة: قارن المبلغ والأرقام بالرسالة",
    "amount_disagreed": "النموذجين قروا مبلغ مختلف: تأكد من المبلغ بالرسالة",
    "device_lost": "موبايل ضايع أو مسروق والمحفظة مفتوحة عليه: يتابعها قسم الاحتيال مباشرة",
    "other_phone": "الزبون يكتب من رقم مو رقمه: تأكد من هويته قبل أي تغيير على الحساب",
    "complaint_risk": "الزبون يهدد بشكوى للجهات الرقابية أو راسلنا أكثر من مرة: انتبه للرد",
    "instructions_in_ticket": "بالتذكرة كلام موجّه للنظام، وما انعمل بيه",
    # Escalations the system decides on its own; their team note is built with no model call.
    "too_long": "التذكرة أطول من الحد المسموح: يستلمها موظف بدون نموذج",
    "pipeline_off": "النظام موقف: يستلمها موظف يدوياً",
    "drafts_off": "المسودات موقفة: يرد الموظف بنفسه",
    "cancelled": "انلغت المعالجة قبل ما تكمل",
    "internal_error": "صار خطأ داخلي، تحتاج مراجعة يدوية",
}

# What an error event says: fixed text by exception type. The message itself never leaves stderr.
_ERROR_AR = {
    "BudgetExceeded": "وصل التشغيل لحد الصرف المسموح، فما انرسل الطلب للنموذج",
    "CacheMiss": "ماكو رد محفوظ لهالطلب، والتشغيل على الردود المحفوظة بس",
    "BackendError": "إعدادات الاتصال بالنموذج ما تسمح بهالطلب",
}
_REFUSALS = (BudgetExceeded, CacheMiss, BackendError)   # expected refusals: one log line, no traceback

# If even the normal closing path fails, the team still gets a note.
_LAST_RESORT_NOTE = "سبب التصعيد: صار خطأ داخلي بالنظام. اقرا التذكرة كاملة."


def _error(e: BaseException, *, internal: bool = False) -> dict[str, str]:
    kind = type(e).__name__
    return {"error": FLAG_AR["internal_error"] if internal else _ERROR_AR.get(kind, FLAG_AR["model_error"]),
            "kind": kind}


def _log_error(where: str, e: BaseException) -> None:
    """Report a failure on stderr. Under REAL_DATA=1 only the type and the stack are logged: an
    exception's message can quote a model reply, and with it the customer's numbers."""
    if isinstance(e, _REFUSALS):
        log.warning("%s: %s", where, type(e).__name__ if real_data() else f"{type(e).__name__}: {e}")
    elif real_data():
        log.error("%s failed: %s\n%s", where, type(e).__name__, "".join(traceback.format_tb(e.__traceback__)))
    else:
        log.error("%s failed", where, exc_info=e)


class _Cancelled(BaseException):
    """should_stop() asked to stop. A BaseException, like asyncio.CancelledError, so the stages'
    `except Exception` (a failed model call is escalated as a model error) cannot swallow it."""


def _clean_changes(raw: str) -> dict[str, int]:
    changes = {
        "arabic_digits": sum(1 for ch in raw if ch.translate(_DIGITS) != ch),
        "tatweel": raw.count(_TATWEEL),
        "extra_spaces": len(re.findall(r"\s{2,}|\n", raw)) + (raw != raw.strip()),
    }
    if fixes.enabled("strip_format_chars"):
        changes["format_chars"] = sum(1 for ch in raw if unicodedata.category(ch) == "Cf")
    return changes


def _text_flags(raw: str, text: str) -> list[str]:
    """The flags the code rules raise on the customer's text (ticket_rules.py), for the fixes switched on."""
    on = fixes.active()
    flags = []
    if "secret_in_ticket" in on and (sensitive_numbers(text) or ticket_rules.secret_spans(raw)):
        flags.append("secret_in_ticket")
    if "strip_format_chars" in on and ticket_rules.BIDI_CONTROLS.search(raw):
        flags.append("bidi_controls")
    if "device_lost" in on and ticket_rules.other_phone(raw):
        flags.append("other_phone")
    if "complaint_risk" in on and ticket_rules.complaint_risk(raw):
        flags.append("complaint_risk")
    if "instructions_in_ticket" in on and ticket_rules.instructions_in_ticket(raw):
        flags.append("instructions_in_ticket")
    return flags


def _fraud_view(ex: Extraction) -> Extraction | None:
    """fraud_secondary: an answer whose second type is fraud (always escalated), turned around so the fraud
    type is the topic and the answer's own type its second request. None for any other answer."""
    tax = taxonomy()
    main, sec = tax.subcategories.get(ex.subcategory), tax.subcategories.get(ex.secondary_subcategory or "")
    if main is None or main.always_escalate or sec is None or not sec.always_escalate:
        return None
    return ex.model_copy(update={"category": sec.category, "subcategory": ex.secondary_subcategory,
                                 "secondary_subcategory": ex.subcategory})


def _amounts_differ(a: Extraction, b: Extraction) -> bool:
    """Both models read an amount in the same currency, and not the same one."""
    return any(x is not None and y is not None and x != y
               for x, y in ((a.amount_iqd, b.amount_iqd), (a.amount_usd, b.amount_usd)))


def _failed(e: BaseException) -> str:
    """The flag for a model step that failed: a budget refusal says so; anything else is a model error."""
    return "budget_reached" if isinstance(e, BudgetExceeded) else "model_error"


# Rule 1 of the classifier prompt (fraud: put the other issue in secondary) contradicts rule 5 (a
# consequence is not a second issue), so "gave my code, now locked out" sometimes got login_otp as
# secondary. Rewording the prompt shifted other classifications, so this is enforced in code: a
# consequence of the fraud is cleared, a separate request is kept.
_FRAUD_CONSEQUENCES = ("account_access", "fraud_security")


def _clean_secondary(ex: Extraction) -> Extraction:
    tax = taxonomy()
    sec = tax.subcategories.get(ex.secondary_subcategory or "")
    if ex.category == "fraud_security" and sec is not None and sec.category in _FRAUD_CONSEQUENCES:
        return ex.model_copy(update={"secondary_subcategory": None})
    return ex


def _add_usage(a: dict, b: dict) -> dict:
    """Usage of two calls for one step. Tokens add up; cost counts only calls actually made
    (a cache hit replays a stored cost but spends nothing), so the step is "cached" only if both were.
    A label such as inference_geo is not added up: the later call's is kept."""
    out = {}
    for k in (a.keys() | b.keys()) - {"cached", "cost_usd"}:
        vals = [v for v in (a.get(k), b.get(k)) if v is not None]
        counts = all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in vals)
        out[k] = sum(vals) if vals and counts else (vals[-1] if vals else None)
    cost = sum(u.get("cost_usd") or 0 for u in (a, b) if not u.get("cached"))
    return {**out, "cost_usd": round(cost, 6), "cached": bool(a.get("cached") and b.get("cached")), "retried": True}


_PROMPTS = Path(__file__).parent / "prompts"


def _summary_prompt() -> str:
    """The summary instructions; the summary_qualifiers flag (fixes.py) swaps in the version under test."""
    name = "summary_system.summary_qualifiers.md" if fixes.enabled("summary_qualifiers") else "summary_system.md"
    return (_PROMPTS / name).read_text(encoding="utf-8")


def _team_summary(text: str) -> tuple[str | None, dict]:
    """One Arabic line for the team handling an escalated ticket. A line with a number that is
    not in the ticket is dropped (the note then has no summary), and so is a failed call."""
    try:
        line = call("classifier", _summary_prompt(), cls.user_prompt(text)).strip()
    except Exception:  # noqa: BLE001 - the note works without a summary
        return None, last_usage()
    line = " ".join(line.split())
    if not line or len(line) > 300 or "unknown_number" in draft_check.problems(line, text):
        return None, last_usage()
    return line, last_usage()


def _model_step(role: str, system: str, user: str,
                before_call: Callable[[], None] = lambda: None) -> tuple[Extraction, dict[str, Any]]:
    """One classification by `role`. `before_call` runs before each model call (it raises to stop)."""
    t0 = time.time()
    before_call()
    reply = call(role, system, user)
    usage = last_usage()
    try:
        ex = cls.parse(reply)
    except ValueError:
        # A reply that isn't valid JSON (on the API, Haiku sometimes adds a stray ")" before the
        # closing "}") gets one fresh try before the ticket is escalated as a model error.
        before_call()
        reply = call(role, system, user, attempt=1)
        usage = _add_usage(usage, last_usage())
        ex = cls.parse(reply)
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
        "usage": usage,
        **({"cleared_secondary": cleared} if cleared else {}),
    }


def process(raw_text: str, emit: Emit = lambda e: None,
            should_stop: Callable[[], bool] | None = None) -> dict[str, Any]:
    """Run one ticket through every stage and return its result. Never raises.

    `should_stop` is checked before every model call, retries included; once it returns True the
    ticket ends escalated with flag 'cancelled' and no further call is made (the viewer passes "the
    browser went away", so an abandoned ticket stops spending).
    """
    started = time.time()
    if isinstance(raw_text, str):
        # A lone surrogate (JSON allows "\ud83d", e.g. an emoji cut in half) can't be encoded, so the
        # events and the saved run could not be written. It becomes "?"; valid text is unchanged.
        raw_text = raw_text.encode("utf-8", "replace").decode("utf-8")
    closed: set[str] = set()            # stages that reached done, skipped or error
    sent: list[dict[str, Any]] = []     # the result, once emitted

    def send(stage: str, status: str, data: dict[str, Any] | None = None) -> None:
        if status != "running":
            closed.add(stage)
        try:
            emit({"stage": stage, "status": status, "data": data or {}, "ms": int((time.time() - started) * 1000)})
        except Exception as e:  # noqa: BLE001 - a broken listener must not stop the ticket
            _log_error("emit", e)

    def stop_requested() -> bool:
        return should_stop is not None and bool(should_stop())

    def check_stop() -> None:
        if stop_requested():
            raise _Cancelled

    # What the handoff note (F17) needs, filled in as the stages run. text_flags come from the code rules on
    # the customer's text and late_flags from the models' answers; finish() adds both to every outcome.
    ctx: dict[str, Any] = {"text": "", "ex": None, "confidence": None, "second": None, "cleared": None,
                           "text_flags": [], "late_flags": [], "secret_spans": []}

    def finish(outcome: Outcome, flags: list[str], *, team_summary: bool = True, **extra: Any) -> dict[str, Any]:
        """Emit the result. An escalation gets a note for the team; `team_summary=False` builds it
        without the one-line summary call (escalations the system decided, not the ticket)."""
        added = [f for f in ctx["text_flags"] + ctx["late_flags"] if f not in flags]
        flags = list(flags) + added
        if outcome == Outcome.DRAFTED and any(f not in QUIET_FLAGS for f in added):
            outcome = Outcome.FLAGGED
        result = {"outcome": outcome.value, "flags": flags, "notes_ar": [], **extra}
        if ctx["secret_spans"]:
            result["secret_spans"] = ctx["secret_spans"]
        if outcome == Outcome.ESCALATED:   # no draft: a short note for the team that receives it
            summary = None
            if team_summary and ctx["ex"] is not None:
                if stop_requested():
                    flags.append("cancelled")
                else:
                    summary, result["usage"] = _team_summary(ctx["text"])
            # A blocked account or a SIM change that a person takes over anyway (unsure, models disagreeing,
            # an error, drafts off): whoever replies is reminded of identity too. Not fraud: no reply there.
            identity = "fraud" not in flags and any(e is not None and e.subcategory in ACCOUNT_RISK
                                                    for e in (ctx["ex"], ctx["second"]))
            result["handoff_ar"] = handoff.note(ctx["ex"], flags, confidence=ctx["confidence"],
                                                second=ctx["second"], cleared_secondary=ctx["cleared"],
                                                summary=summary, identity=identity)
        result["notes_ar"] = [FLAG_AR.get(f, f) for f in flags]
        send("result", "done", result)
        sent.append(result)
        return result

    def end_early(flag: str, error: BaseException | None = None, **extra: Any) -> dict[str, Any]:
        """Close every stage still open (the first with the error, if any) and escalate with `flag`.
        Nothing more is sent to a model."""
        for stage in STAGES[:-1]:
            if stage in closed:
                continue
            if error is not None:
                send(stage, "error", _error(error, internal=True))
                error = None
            else:
                send(stage, "skipped", {"why": FLAG_AR[flag]})
        if ctx["ex"] is not None:
            extra.setdefault("extraction", ctx["ex"].model_dump())
        extra.update({k: ctx[k] for k in ("team", "priority") if ctx.get(k)})
        return finish(Outcome.ESCALATED, [flag], team_summary=False, **extra)

    def run() -> dict[str, Any]:
        tax = taxonomy()
        send("received", "done", {"text": raw_text, "chars": len(raw_text)})

        # 1. Clean (rules)
        text = clean(raw_text)
        ctx["text"] = text
        send("clean", "done", {"text": text, "changes": _clean_changes(raw_text)})
        on = fixes.active()
        ctx["text_flags"] = _text_flags(raw_text, text)
        if "secret_in_ticket" in on:
            ctx["secret_spans"] = ticket_rules.secret_spans(raw_text)

        # A very long ticket is not sent to a model: it costs more and is the usual shape of an
        # attempt to bury instructions. A person reads it.
        if len(text) > limits()["max_ticket_chars"]:
            return end_early("too_long")
        mode = pipeline_mode()
        if mode == "off":
            return end_early("pipeline_off")

        # 2. Classify + extract (classifier model)
        send("classify", "running", {"model": model_for("classifier"), "backend": backend()})
        try:
            ex, info = _model_step("classifier", cls.system_prompt(), cls.user_prompt(text), check_stop)
        except Exception as e:  # noqa: BLE001
            _log_error("classify", e)
            send("classify", "error", _error(e))
            for s in ("gate", "recheck", "route", "draft"):
                send(s, "skipped")
            return finish(Outcome.ESCALATED, [_failed(e)])
        ctx.update(ex=ex, cleared=info.get("cleared_secondary"))
        sub = tax.subcategories.get(ex.subcategory)
        info["labels"] = {
            "category": tax.categories.get(ex.category, ex.category),
            "subcategory": sub.label if sub else ex.subcategory,
        }
        send("classify", "done", info)
        # fraud_secondary: a fraud second type is handled as fraud (the gate escalates it); its own type
        # stays in the team note as the second request.
        view = _fraud_view(ex) if "fraud_secondary" in on else None
        if view is not None:
            ex, sub = view, tax.subcategories.get(view.subcategory)
            ctx["ex"] = ex

        # 3. Confidence gate (rules)
        gate = check(ex, text)
        decision = "escalate" if gate.escalate else ("recheck" if gate.needs_recheck else "pass")
        send("gate", "done", {**gate.model_dump(), "model_confidence": ex.confidence, "decision": decision,
                              "high_risk": bool(sub and sub.high_risk)})
        flags = list(gate.flags)
        ctx["confidence"] = gate.confidence

        # device_lost: whoever has the phone has the wallet. The fraud team takes it now, with no draft.
        if "device_lost" in on and ticket_rules.device_lost(raw_text):
            send("recheck", "skipped", {"why": FLAG_AR["device_lost"]})
            ctx.update(team=SECURITY_TEAM, priority=SECURITY_PRIORITY)
            send("route", "done", {"team": SECURITY_TEAM, "team_ar": tax.teams[SECURITY_TEAM]["label_ar"],
                                   "priority": SECURITY_PRIORITY})
            send("draft", "skipped", {"why": FLAG_AR["device_lost"]})
            return finish(Outcome.ESCALATED, flags + ["device_lost"], team=SECURITY_TEAM, priority=SECURITY_PRIORITY,
                          extraction=ex.model_dump())

        if gate.escalate:
            for s in ("recheck",):
                send(s, "skipped", {"why": "البوابة صعّدتها"})
            team, priority = route(ex, text) if sub else ("general", "P2")
            ctx.update(team=team, priority=priority)
            send("route", "done", {"team": team, "team_ar": tax.teams[team]["label_ar"], "priority": priority})
            send("draft", "skipped", {"why": "متصعّدة: يستلمها موظف"})
            return finish(Outcome.ESCALATED, flags, team=team, priority=priority, extraction=ex.model_dump())

        # 4. Re-check (second model, classifies blind)
        alternative = None
        if gate.needs_recheck:
            send("recheck", "running", {"model": model_for("rechecker"), "backend": backend()})
            try:
                ex2, info2 = _model_step("rechecker", cls.system_prompt(), cls.user_prompt(text), check_stop)
            except Exception as e:  # noqa: BLE001
                _log_error("recheck", e)
                send("recheck", "error", _error(e))
                send("route", "skipped")
                send("draft", "skipped")
                return finish(Outcome.ESCALATED, flags + [_failed(e)], extraction=ex.model_dump())
            agree = ex2.subcategory == ex.subcategory
            info2.update(agree=agree, first=ex.subcategory, second=ex2.subcategory)
            send("recheck", "done", info2)
            if "strip_format_chars" in on and _amounts_differ(ex, ex2):
                ctx["late_flags"].append("amount_disagreed")
            view2 = _fraud_view(ex2) if "fraud_secondary" in on else None
            if view2 is not None:      # the re-check's second type is fraud: handled as fraud, as above
                flags.append("fraud")
                ctx["second"] = view2
                team, priority = route(view2, text)
                ctx.update(team=team, priority=priority)
                send("route", "done", {"team": team, "team_ar": tax.teams[team]["label_ar"], "priority": priority})
                send("draft", "skipped", {"why": FLAG_AR["fraud"]})
                return finish(Outcome.ESCALATED, flags, team=team, priority=priority, extraction=ex.model_dump())
            # The re-check model was right in most disagreements, so a disagreement is drafted from its
            # answer, flagged, with the gate rules re-run for it. Never for fraud.
            sub2 = tax.subcategories.get(ex2.subcategory)
            use_second = not agree and sub2 is not None and not sub2.always_escalate
            gate2 = check(ex2, text) if use_second else None
            if use_second and not gate2.escalate:
                alternative, ex, sub = ex.subcategory, ex2, sub2
                flags = list(gate2.flags) + ["recheck_used_second"]
                ctx.update(ex=ex, confidence=gate2.confidence, cleared=info2.get("cleared_secondary"))
            elif not agree or ex2.category == "fraud_security":
                flags.append("fraud" if ex2.category == "fraud_security" else "recheck_disagreed")
                ctx["second"] = ex2
                team, priority = route(ex2 if ex2.category == "fraud_security" else ex, text)
                ctx.update(team=team, priority=priority)
                send("route", "done", {"team": team, "team_ar": tax.teams[team]["label_ar"], "priority": priority})
                send("draft", "skipped", {"why": "المراجعة ما اتفقت: الموظف يقرر"})
                return finish(Outcome.ESCALATED, flags, team=team, priority=priority, extraction=ex.model_dump())
        else:
            send("recheck", "skipped", {"why": f"الثقة {gate.confidence:.2f} عالية والنوع مو حساس"})

        # Fee tickets get a small extra call for the disputed fee, so the classifier prompt (and its
        # accuracy) stays as it is: adding a fee field to it shifted other classifications (round 3).
        fee_call: dict[str, Any] = {}
        if ex.subcategory in FEE_SUBCATEGORIES and ex.fee_iqd is None:
            check_stop()
            try:
                fee_reply = call("classifier", cls.fee_prompt(), cls.user_prompt(text))
                ex = ex.model_copy(update={"fee_iqd": cls.parse_fee(fee_reply)})
                ctx["ex"] = ex
                fee_call = {"fee_call": {"reply": fee_reply, "fee_iqd": ex.fee_iqd}, "usage": last_usage()}
            except Exception as e:  # noqa: BLE001 - the fee is a nice-to-have; carry on without it
                _log_error("fee call", e)

        # 5. Route + priority (rules)
        team, priority = route(ex, text)
        ctx.update(team=team, priority=priority)
        send("route", "done", {"team": team, "team_ar": tax.teams[team]["label_ar"], "priority": priority, **fee_call})

        if mode == "classify_only":   # sorted and routed; the agent writes the reply
            send("draft", "skipped", {"why": FLAG_AR["drafts_off"]})
            return finish(Outcome.ESCALATED, flags + ["drafts_off"], team_summary=False,
                          team=team, priority=priority, extraction=ex.model_dump())

        # 6. Draft (drafter model), then rule checks on it
        send("draft", "running", {"model": model_for("drafter"), "backend": backend(),
                                  "ask_for": drf.ask_for(ex)})
        t0 = time.time()
        user = drf.user_prompt(text, ex, team)
        check_stop()
        try:
            reply = drf.draft(text, ex, team)
        except Exception as e:  # noqa: BLE001
            _log_error("draft", e)
            send("draft", "error", _error(e))
            return finish(Outcome.ESCALATED, flags + [_failed(e)], team=team, priority=priority)
        # A time («خلال يومين») is allowed only from the policy facts, never because the customer wrote it.
        facts_text = drf.facts_text(ex.subcategory)
        checks = draft_check.problems(reply, user, facts_text=facts_text)
        spans = draft_check.findings(reply, user, facts_text=facts_text)
        if ex.subcategory in ACCOUNT_RISK:   # the type the draft was written for: the re-check's, if it was used
            flags.append("account_risk")
        flags += [f"draft:{p}" for p in checks]
        send("draft", "done", {"model": model_for("drafter"), "backend": backend(),
                               "seconds": round(time.time() - t0, 1), "user_prompt": user, "reply": reply,
                               "ask_for": drf.ask_for(ex), "checks": checks, "check_spans": spans,
                               "usage": last_usage()})

        outcome = Outcome.FLAGGED if flags else Outcome.DRAFTED
        extra = {"recheck_alternative": alternative} if alternative else {}
        if fee_call:
            extra["fee_followup"] = True
        return finish(outcome, flags, team=team, priority=priority, draft_ar=reply, draft_checks=spans,
                      extraction=ex.model_dump(), **extra)

    try:
        with before_retry(check_stop):
            return run()
    except _Cancelled:
        flag, error = "cancelled", None
    except Exception as e:  # noqa: BLE001 - process() never raises
        _log_error("ticket", e)
        flag, error = "internal_error", e
    if sent:                 # the ticket had already ended; keep that result
        return sent[-1]
    try:
        return end_early(flag, error)
    except Exception as e:  # noqa: BLE001 - last resort: fixed text, no lookups
        _log_error("closing the ticket", e)
        result = {"outcome": Outcome.ESCALATED.value, "flags": [flag], "notes_ar": [FLAG_AR[flag]],
                  "handoff_ar": _LAST_RESORT_NOTE}
        send("result", "done", result)
        return result
