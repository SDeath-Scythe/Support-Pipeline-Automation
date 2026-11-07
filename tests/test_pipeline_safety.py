"""Safety and reliability of the pipeline core (security review, 1 Nov): input limits, the kill
switch, cancellation, error handling, retries, the spending cap, the real-data guard and the
cache-only replay. Every model call is stubbed; nothing here reaches a model."""

import importlib.util
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace as NS

import pytest
import yaml

from pipeline import config, gate, llm
from pipeline.schemas import Extraction

ROOT = Path(__file__).resolve().parents[1]

APP_BUG = '{"category": "general", "subcategory": "app_bug", "confidence": 0.92}'
APP_BUG_UNSURE = '{"category": "general", "subcategory": "app_bug", "confidence": 0.70}'
FRAUD = '{"category": "fraud_security", "subcategory": "suspected_scam", "confidence": 0.95}'
SIM = '{"category": "account_access", "subcategory": "sim_change", "confidence": 0.95}'
TICKET = "التطبيق يفتح شاشة بيضاء"

_ENV = ("PIPELINE_MODE", "REAL_DATA", "LLM_CACHE_ONLY", "LLM_CACHE_DIR", "LLM_CACHE_SALT", "LLM_PROFILE",
        "PIPELINE_FIXES", "LLM_BUDGET_USD", "LLM_BACKEND", "ANTHROPIC_BASE_URL")


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for var in _ENV:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def fake(monkeypatch):
    """Stub every model call the pipeline makes and record which ones were made, in order."""
    from pipeline import draft as drf
    from pipeline import run

    seen: list[str] = []
    replies = {"classifier": APP_BUG, "rechecker": APP_BUG, "drafter": "هلا بيك، راح نشيك",
               "summary": "التطبيق يفتح شاشة بيضاء", "fee": '{"fee_iqd": null}'}

    def fake_call(role, system, user, attempt=0):
        kind = "summary" if "ONE short line" in system else ("fee" if system == run.cls.fee_prompt() else role)
        seen.append(kind)
        reply = replies[kind]
        if isinstance(reply, Exception):
            raise reply
        return reply

    def fake_draft_call(role, system, user):
        seen.append("drafter")
        return replies["drafter"]

    monkeypatch.setattr(run, "call", fake_call)
    monkeypatch.setattr(drf, "call", fake_draft_call)
    return NS(run=run, seen=seen, replies=replies)


def _stages(events):
    return [(e["stage"], e["status"]) for e in events]


def _closes_every_stage(events, run):
    """Every stage ends exactly once (done, skipped or error) and the result comes last."""
    ends = [e["stage"] for e in events if e["status"] != "running"]
    assert ends == run.STAGES, ends


# --- contract A: limits ---

def test_limits_come_from_thresholds_with_defaults(monkeypatch):
    assert config.limits() == {"max_ticket_chars": 4000, "max_batch_tickets": 1000, "max_request_bytes": 65536}
    monkeypatch.setattr(config, "thresholds", lambda: {"confidence": {}})          # block missing
    assert config.limits()["max_ticket_chars"] == 4000
    monkeypatch.setattr(config, "thresholds", lambda: {"limits": {"max_ticket_chars": 50}})
    assert config.limits() == {"max_ticket_chars": 50, "max_batch_tickets": 1000, "max_request_bytes": 65536}


def test_too_long_ticket_is_escalated_before_any_model_call(fake):
    events = []
    result = fake.run.process("ا" * 4001, events.append)
    assert fake.seen == []
    assert result["outcome"] == "escalated" and result["flags"] == ["too_long"]
    assert result["notes_ar"] == ["التذكرة أطول من الحد المسموح: يستلمها موظف بدون نموذج"]
    assert "الحد المسموح" in result["handoff_ar"] and "خطأ بالنموذج" not in result["handoff_ar"]
    _closes_every_stage(events, fake.run)
    assert ("classify", "skipped") in _stages(events) and "draft_ar" not in result


def test_ticket_at_the_limit_still_runs(fake, monkeypatch):
    monkeypatch.setattr(fake.run, "limits", lambda: {"max_ticket_chars": len(TICKET)})
    assert fake.run.process(TICKET)["outcome"] == "drafted" and fake.seen == ["classifier", "drafter"]
    fake.seen.clear()
    assert fake.run.process(TICKET + " ا")["flags"] == ["too_long"] and fake.seen == []


# --- contract B: run mode / kill switch ---

def test_pipeline_mode_env_wins_and_rejects_unknown(monkeypatch):
    assert config.pipeline_mode() == "full"
    monkeypatch.setattr(config, "_default_mode", lambda: "classify_only")         # models.yaml `mode:`
    assert config.pipeline_mode() == "classify_only"
    monkeypatch.setenv("PIPELINE_MODE", " OFF ")
    assert config.pipeline_mode() == "off"
    monkeypatch.setenv("PIPELINE_MODE", "sideways")
    with pytest.raises(ValueError):
        config.pipeline_mode()


def _models_yaml(monkeypatch, text):
    """models.yaml as the file would say it: parsed by YAML, not a value handed to the code."""
    real = config.load_yaml
    monkeypatch.setattr(config, "load_yaml", lambda name: yaml.safe_load(text) if name == "models.yaml" else real(name))


def test_bare_off_in_models_yaml_switches_the_pipeline_off(fake, monkeypatch):
    """YAML reads a bare `mode: off` as False; that must mean off, not the full (paid) pipeline."""
    _models_yaml(monkeypatch, "mode: off\n")
    assert config.pipeline_mode() == "off"
    result = fake.run.process(TICKET)
    assert fake.seen == [] and result["flags"] == ["pipeline_off"]
    for text, mode in (("mode: no\n", "off"), ("mode: false\n", "off"), ("mode: \"off\"\n", "off"),
                       ("mode: classify_only\n", "classify_only"), ("backend: cli\n", "full"), ("mode:\n", "full")):
        _models_yaml(monkeypatch, text)
        assert config.pipeline_mode() == mode, text
    _models_yaml(monkeypatch, "mode: on\n")              # True is not a mode
    with pytest.raises(ValueError):
        config.pipeline_mode()


def test_editing_models_yaml_takes_effect_without_a_restart(monkeypatch):
    _models_yaml(monkeypatch, "mode: full\n")
    assert config.pipeline_mode() == "full"
    _models_yaml(monkeypatch, "mode: \"off\"\n")
    assert config.pipeline_mode() == "off"
    monkeypatch.setattr(llm, "_call_cli", lambda *a: pytest.fail("must not call a model"))
    monkeypatch.setenv("LLM_BACKEND", "cli")
    with pytest.raises(llm.BackendError):
        llm.call("classifier", "S", "U")


def test_pipeline_off_makes_no_model_call(fake, monkeypatch):
    monkeypatch.setenv("PIPELINE_MODE", "off")
    events = []
    result = fake.run.process(TICKET, events.append)
    assert fake.seen == [] and result["outcome"] == "escalated" and result["flags"] == ["pipeline_off"]
    assert result["notes_ar"] == ["النظام موقف: يستلمها موظف يدوياً"]
    _closes_every_stage(events, fake.run)


def test_llm_call_refuses_when_off(monkeypatch):
    """The kill switch holds even for a caller that does not check it."""
    sent = []
    monkeypatch.setenv("PIPELINE_MODE", "off")
    monkeypatch.setenv("LLM_BACKEND", "cli")
    monkeypatch.setattr(llm, "_call_cli", lambda *a: sent.append(a) or "x")
    with pytest.raises(llm.BackendError):
        llm.call("classifier", "S", "U")
    assert sent == []


def test_classify_only_routes_but_never_drafts(fake, monkeypatch):
    monkeypatch.setenv("PIPELINE_MODE", "classify_only")
    events = []
    result = fake.run.process(TICKET, events.append)
    assert fake.seen == ["classifier"]                                  # no draft, no summary call
    assert result["outcome"] == "escalated" and result["flags"] == ["drafts_off"]
    assert result["team"] == "tech" and result["priority"] == "P3" and "draft_ar" not in result
    assert "المسودات موقفة" in result["handoff_ar"] and "الموضوع" in result["handoff_ar"]
    assert ("draft", "skipped") in _stages(events)
    _closes_every_stage(events, fake.run)


def test_invalid_mode_escalates_instead_of_raising(fake, monkeypatch):
    monkeypatch.setenv("PIPELINE_MODE", "sideways")
    result = fake.run.process(TICKET)
    assert result["flags"] == ["internal_error"] and fake.seen == []


# --- contract E: should_stop ---

def test_should_stop_before_the_first_call(fake):
    events = []
    result = fake.run.process(TICKET, events.append, should_stop=lambda: True)
    assert fake.seen == [] and result["outcome"] == "escalated" and result["flags"] == ["cancelled"]
    assert result["notes_ar"] == ["انلغت المعالجة قبل ما تكمل"]
    _closes_every_stage(events, fake.run)


def test_should_stop_between_classify_and_recheck(fake):
    fake.replies["classifier"] = APP_BUG_UNSURE                          # 0.70: would be re-checked
    events = []
    result = fake.run.process(TICKET, events.append, should_stop=lambda: len(fake.seen) >= 1)
    assert fake.seen == ["classifier"]
    assert result["flags"] == ["cancelled"] and result["extraction"]["subcategory"] == "app_bug"
    assert ("recheck", "skipped") in _stages(events)
    _closes_every_stage(events, fake.run)


def test_should_stop_before_the_draft(fake):
    result = fake.run.process(TICKET, should_stop=lambda: len(fake.seen) >= 1)
    assert fake.seen == ["classifier"] and result["flags"] == ["cancelled"]
    assert result["team"] == "tech" and "draft_ar" not in result


def test_should_stop_skips_the_team_summary(fake):
    fake.replies["classifier"] = FRAUD
    result = fake.run.process("واحد اتصل وطلب الرمز وانطيته", should_stop=lambda: len(fake.seen) >= 1)
    assert fake.seen == ["classifier"] and result["flags"] == ["fraud", "cancelled"]
    assert "الخلاصة" not in result["handoff_ar"]


def test_should_stop_is_checked_before_a_retry(monkeypatch):
    """A page closed while a call times out gets no second, paid attempt."""
    from pipeline import run

    attempts, stop = [], {"now": False}

    def send(cfg, system, user):
        attempts.append(user)
        stop["now"] = True                                 # the browser goes away during the call
        raise _sdk_error("APITimeoutError")

    monkeypatch.setenv("LLM_BACKEND", "api")
    monkeypatch.setattr(llm, "_call_api", send)
    monkeypatch.setattr(llm, "_pause", lambda s: None)
    events = []
    result = run.process(TICKET, events.append, should_stop=lambda: stop["now"])
    assert len(attempts) == 1 and result["flags"] == ["cancelled"]
    _closes_every_stage(events, run)


def test_before_retry_is_per_thread_and_restored():
    calls = []
    with llm.before_retry(lambda: calls.append("outer")):
        with llm.before_retry(lambda: calls.append("inner")):
            llm._retry_check.fn()
        llm._retry_check.fn()
    assert calls == ["inner", "outer"] and llm._retry_check.fn is None


def test_should_stop_never_called_means_normal_run(fake):
    result = fake.run.process(TICKET, should_stop=lambda: False)
    assert result["outcome"] == "drafted" and fake.seen == ["classifier", "drafter"]


# --- contract G: errors never leak, process() never raises ---

SECRET = "leak 07701234567 /home/someone/secret.txt"


def test_crash_inside_route_ends_as_internal_error_without_the_message(fake, monkeypatch):
    def broken_route(ex, text):
        raise RuntimeError(SECRET)

    monkeypatch.setattr(fake.run, "route", broken_route)
    events = []
    result = fake.run.process(TICKET, events.append)
    assert result["outcome"] == "escalated" and result["flags"] == ["internal_error"]
    assert result["notes_ar"] == ["صار خطأ داخلي، تحتاج مراجعة يدوية"]
    assert fake.seen == ["classifier"]                                  # no summary call, no draft
    err = [e for e in events if e["status"] == "error"]
    assert [(e["stage"], e["data"]) for e in err] == [
        ("route", {"error": "صار خطأ داخلي، تحتاج مراجعة يدوية", "kind": "RuntimeError"})]
    dumped = json.dumps([events, result], ensure_ascii=False)
    assert "leak" not in dumped and "07701234567" not in dumped and "secret" not in dumped
    _closes_every_stage(events, fake.run)


def test_model_error_event_has_kind_not_message(fake):
    fake.replies["classifier"] = RuntimeError(SECRET)
    events = []
    result = fake.run.process(TICKET, events.append)
    assert result["flags"] == ["model_error"]
    err = next(e for e in events if e["status"] == "error")
    assert err["stage"] == "classify"
    assert err["data"] == {"error": "صار خطأ بالنموذج، تحتاج مراجعة يدوية", "kind": "RuntimeError"}
    assert "leak" not in json.dumps([events, result], ensure_ascii=False)


def test_budget_refusal_is_named_so_run_batch_can_spot_it(fake):
    fake.replies["classifier"] = llm.BudgetExceeded("API budget of $5.00 reached")
    events = []
    fake.run.process(TICKET, events.append)
    err = next(e for e in events if e["status"] == "error")
    assert err["data"]["kind"] == "BudgetExceeded" and "$" not in err["data"]["error"]
    assert "BudgetExceeded" in json.dumps(events)        # run_batch's budget_hit check


def test_failed_draft_call_reports_kind_only(fake, monkeypatch):
    from pipeline import draft as drf

    def broken(role, system, user):
        raise llm.CacheMiss(SECRET)

    monkeypatch.setattr(drf, "call", broken)
    events = []
    result = fake.run.process(TICKET, events.append)
    assert result["outcome"] == "escalated" and "model_error" in result["flags"]
    err = next(e for e in events if e["status"] == "error")
    assert err["stage"] == "draft" and err["data"]["kind"] == "CacheMiss" and "leak" not in json.dumps(events)


def test_a_listener_that_raises_does_not_stop_the_ticket(fake):
    def emit(event):
        raise OSError("browser went away")

    assert fake.run.process(TICKET, emit)["outcome"] == "drafted"


def test_a_lone_surrogate_is_replaced_so_the_run_can_be_saved(fake):
    """JSON allows "\\ud83d" (an emoji cut in half); it can't be encoded, so events and run files failed."""
    events = []
    result = fake.run.process("\ud83d " + TICKET, events.append)
    assert result["outcome"] == "drafted"
    json.dumps([events, result], ensure_ascii=False).encode("utf-8")      # raised before
    assert events[0]["data"]["text"] == "? " + TICKET


def test_non_text_input_is_escalated_not_raised(fake):
    result = fake.run.process(None)                                      # type: ignore[arg-type]
    assert result["outcome"] == "escalated" and result["flags"] == ["internal_error"] and fake.seen == []


def test_usage_labels_are_not_added_up():
    from pipeline.run import _add_usage

    out = _add_usage({"input_tokens": 1, "inference_geo": "us", "cost_usd": 0.1},
                     {"input_tokens": 2, "inference_geo": "eu", "cost_usd": 0.2})
    assert out["input_tokens"] == 3 and out["inference_geo"] == "eu" and out["cost_usd"] == pytest.approx(0.3)
    out = _add_usage({"output_tokens": 4, "inference_geo": None}, {"output_tokens": 0, "inference_geo": None})
    assert out["output_tokens"] == 4 and out["inference_geo"] is None


# --- contract F: flag notes ---

def test_new_flags_have_their_arabic_notes():
    from pipeline.run import FLAG_AR

    assert {k: FLAG_AR[k] for k in ("too_long", "pipeline_off", "drafts_off", "cancelled", "internal_error",
                                     "draft:hold_reason", "draft:sensitive_number", "account_risk")} == {
        "too_long": "التذكرة أطول من الحد المسموح: يستلمها موظف بدون نموذج",
        "pipeline_off": "النظام موقف: يستلمها موظف يدوياً",
        "drafts_off": "المسودات موقفة: يرد الموظف بنفسه",
        "cancelled": "انلغت المعالجة قبل ما تكمل",
        "internal_error": "صار خطأ داخلي، تحتاج مراجعة يدوية",
        "draft:hold_reason": "المسودة تذكر تحقيق أو اشتباه أو بلاغ: لا تعتمدها، ممنوع نخبر الزبون",
        "draft:sensitive_number": "المسودة تكرر رقم بطاقة أو رمز: احذفه قبل الاعتماد",
        "account_risk": "حساب مقفول أو تبديل شريحة: تأكد من هوية الزبون حسب الإجراءات قبل الاعتماد، "
                        "ولا تكتب بالرد إنه صار أي تغيير على الحساب",
    }


# --- contract H: the 5 Nov adoption (hold_reason, sensitive_number, account_risk) ---

def _ex(sub, cat="account_access", conf=0.95):
    return Extraction(category=cat, subcategory=sub, confidence=conf)


def _reply(sub, conf, cat="account_access"):
    return json.dumps({"category": cat, "subcategory": sub, "confidence": conf})


@pytest.mark.parametrize("name", ["hold_reason", "sensitive_number", "escalate_account_risk"])
def test_an_adopted_flag_name_is_refused_with_what_became_of_it(name, monkeypatch):
    from pipeline import fixes

    assert name not in fixes.FIXES and fixes.active() == frozenset()
    monkeypatch.setenv("PIPELINE_FIXES", f"{name}, ")
    with pytest.raises(ValueError) as e:
        fixes.active()
    msg = str(e.value)
    assert name in msg and "normal code" in msg and "5 Nov 2026" in msg and "Remove it from PIPELINE_FIXES" in msg
    with pytest.raises(KeyError):
        fixes.enabled(name)


def test_the_new_flag_name_is_not_a_fix_either(monkeypatch):
    from pipeline import fixes

    monkeypatch.setenv("PIPELINE_FIXES", "account_risk")
    with pytest.raises(ValueError, match="Unknown fix"):
        fixes.active()


def test_the_gate_never_escalates_a_blocked_account_or_a_sim_change():
    sim = gate.check(_ex("sim_change"), "بدلت الشريحة وما يوصلني الرمز")
    assert not sim.escalate and sim.needs_recheck and sim.flags == []        # high risk: re-checked, as before
    blocked = gate.check(_ex("blocked_account"), "حسابي انقفل")
    assert not blocked.escalate and not blocked.needs_recheck and blocked.flags == []


@pytest.mark.parametrize("sub", ["blocked_account", "sim_change"])
def test_account_risk_flags_the_draft_and_never_escalates(fake, sub):
    fake.replies["classifier"] = fake.replies["rechecker"] = _reply(sub, 0.95)
    events = []
    result = fake.run.process("بدلت الشريحة وهسه ما يوصلني الرمز" if sub == "sim_change" else "حسابي انقفل", events.append)
    assert result["outcome"] == "flagged" and result["flags"] == ["account_risk"]
    assert result["draft_ar"] and "handoff_ar" not in result
    assert result["notes_ar"] == [fake.run.FLAG_AR["account_risk"]]
    assert "summary" not in fake.seen and fake.seen[-1] == "drafter"
    assert [e["stage"] for e in events if e["status"] == "skipped"] == ([] if sub == "sim_change" else ["recheck"])


def test_account_risk_reads_the_type_after_the_recheck_not_the_first_label(fake):
    """t2-0009: the first model said sim_change (unsure), the re-check said login_otp and the draft was
    written for login_otp. No account_risk (the old flag escalated it before the re-check could correct it)."""
    fake.replies["classifier"] = _reply("sim_change", 0.70)
    fake.replies["rechecker"] = _reply("login_otp", 0.95)
    result = fake.run.process("رمز التحقق ما يوصلني من البارحة، الخط نفسه والموبايل نفسه")
    assert result["outcome"] == "flagged" and result["flags"] == ["recheck_used_second"]
    assert result["recheck_alternative"] == "sim_change" and result["extraction"]["subcategory"] == "login_otp"
    assert result["draft_ar"] and "account_risk" not in result["flags"]


@pytest.mark.parametrize("sub", ["blocked_account", "sim_change"])
def test_account_risk_applies_when_the_recheck_changed_the_type_to_it(fake, sub):
    fake.replies["classifier"] = _reply("login_otp", 0.70)
    fake.replies["rechecker"] = _reply(sub, 0.95)
    result = fake.run.process("ما اكدر افوت للحساب")
    assert result["outcome"] == "flagged" and result["flags"] == ["recheck_used_second", "account_risk"]
    assert result["recheck_alternative"] == "login_otp" and result["extraction"]["subcategory"] == sub
    assert result["draft_ar"]


def test_account_risk_is_not_added_to_an_escalation(fake):
    """The re-check said sim_change but too unsure to use: the models disagree, so a person takes it, with
    the reason the team note gives for that (no account_risk flag, which is never a reason to escalate).
    Whoever takes it writes the reply, so the note ends with the identity reminder (5 Nov review)."""
    from pipeline.handoff import IDENTITY_AR

    fake.replies["classifier"] = _reply("login_otp", 0.70)
    fake.replies["rechecker"] = _reply("sim_change", 0.50)
    result = fake.run.process("ما اكدر افوت للحساب")
    assert result["outcome"] == "escalated" and result["flags"] == ["recheck_disagreed"]
    assert "draft_ar" not in result and "من البداية" not in result["handoff_ar"]
    assert result["handoff_ar"].split("\n")[-1] == IDENTITY_AR
    assert "سبب التصعيد: النموذجين اختلفوا" in result["handoff_ar"]


@pytest.mark.parametrize("case", ["unsure", "draft_error", "drafts_off"])
def test_an_escalated_blocked_account_or_sim_change_note_reminds_of_identity(fake, monkeypatch, case):
    """5 Nov review: account_risk only flags a draft, so a blocked account or a SIM change that escalates
    for another reason (too unsure, a draft model error, drafts switched off) reached the team with no
    identity reminder. The note now ends with it; nothing else in the note changes."""
    from pipeline.handoff import IDENTITY_AR

    if case == "unsure":
        fake.replies["classifier"] = _reply("blocked_account", 0.40)
    else:
        fake.replies["classifier"] = fake.replies["rechecker"] = _reply("sim_change", 0.95)
    if case == "draft_error":
        monkeypatch.setattr(fake.run.drf, "call", lambda *a: (_ for _ in ()).throw(RuntimeError("model down")))
    if case == "drafts_off":
        monkeypatch.setenv("PIPELINE_MODE", "classify_only")
    result = fake.run.process("حسابي انقفل وما اكدر افوت" if case == "unsure" else "بدلت الشريحة وهسه ما يوصلني الرمز")
    assert result["outcome"] == "escalated" and "account_risk" not in result["flags"] and "draft_ar" not in result
    lines = result["handoff_ar"].split("\n")
    assert lines[-1] == IDENTITY_AR and lines.count(IDENTITY_AR) == 1 and lines[0].startswith("الموضوع:")


@pytest.mark.parametrize("sub", ["login_otp", "app_bug"])
def test_no_identity_reminder_for_other_types_or_fraud(fake, sub):
    from pipeline.handoff import IDENTITY_AR

    fake.replies["classifier"] = _reply(sub, 0.40, cat="account_access" if sub == "login_otp" else "general")
    result = fake.run.process("ما اكدر افوت للحساب")
    assert result["outcome"] == "escalated" and IDENTITY_AR not in result["handoff_ar"]
    fake.replies["classifier"] = _reply("sim_change", 0.70)
    fake.replies["rechecker"] = FRAUD          # the first model said SIM change, the re-check said fraud
    result = fake.run.process("واحد اتصل كال من الشركة وانطيته الرمز وهسه بدلولي الشريحة")
    assert result["flags"] == ["fraud"] and IDENTITY_AR not in result["handoff_ar"]


@pytest.mark.parametrize("first", ["sim_change", "blocked_account"])
def test_fraud_is_still_escalated_with_no_draft(fake, first):
    fake.replies["classifier"] = _reply(first, 0.70)
    fake.replies["rechecker"] = FRAUD
    result = fake.run.process("واحد اتصل كال من الشركة وانطيته الرمز وهسه حسابي انقفل")
    assert result["outcome"] == "escalated" and result["flags"] == ["fraud"]
    assert "draft_ar" not in result and "drafter" not in fake.seen and "احتمال احتيال" in result["handoff_ar"]
    fake.seen.clear()
    fake.replies["classifier"] = FRAUD
    result = fake.run.process("واحد اتصل كال من الشركة وانطيته الرمز")
    assert result["outcome"] == "escalated" and result["flags"] == ["fraud"] and "drafter" not in fake.seen


@pytest.mark.parametrize("kind, draft", [
    ("hold_reason", "هلا بيك، حسابك تحت التحقيق حالياً"),
    ("hold_reason", "هلا بيك، رفعنا بلاغ للقسم المختص"),         # stays flagged (the author's decision, 5 Nov)
    ("hold_reason", "هلا بيك، سجلنا بلاغ بمشكلتك"),
    ("sensitive_number", "هلا بيك، لا تشارك رمز التحقق 482913 ويا أحد"),
])
def test_hold_reason_and_sensitive_number_always_flag_the_draft(fake, kind, draft):
    fake.replies["drafter"] = draft
    events = []
    result = fake.run.process(TICKET + "، ووصلني رمز 482913", events.append)   # the number is the customer's
    assert result["outcome"] == "flagged" and result["flags"] == [f"draft:{kind}"]
    assert [f["kind"] for f in result["draft_checks"]] == [kind]
    done = next(e for e in events if e["stage"] == "draft" and e["status"] == "done")
    assert done["data"]["checks"] == [kind] and done["data"]["check_spans"] == result["draft_checks"]
    assert not any(ch.isdigit() for f in result["draft_checks"] for ch in f["text"])


# --- contract J: draft checks get the policy facts, not the ticket ---

def test_draft_spans_reach_the_event_and_the_result(fake):
    fake.replies["drafter"] = "hلا بيك"
    events = []
    result = fake.run.process(TICKET, events.append)
    done = next(e for e in events if e["stage"] == "draft" and e["status"] == "done")
    assert result["flags"] == ["draft:stray_latin"]
    assert result["draft_checks"] == done["data"]["check_spans"]
    assert [f["kind"] for f in result["draft_checks"]] == ["stray_latin"]
    assert all({"kind", "start", "end", "text"} <= f.keys() for f in result["draft_checks"])


def test_a_time_the_customer_wrote_is_still_a_promise(fake):
    """The customer's «خلال يومين» is not a policy fact, so a draft repeating it is flagged."""
    fake.replies["drafter"] = "هلا بيك، التطبيق راح يتصلح خلال يومين."
    result = fake.run.process("التطبيق عالق، وكالولي يتصلح خلال يومين")
    assert "draft:promise" in result["flags"]


# --- contract D and llm retries ---

def _sdk_error(name, status=None):
    import anthropic

    try:
        import httpx2 as httpx
    except ImportError:  # older SDKs
        import httpx
    req = httpx.Request("POST", "https://example.invalid/v1/messages")
    cls = getattr(anthropic, name)
    return cls(request=req) if status is None else cls("refused", response=httpx.Response(status, request=req), body=None)


@pytest.fixture
def flaky(monkeypatch):
    """llm.call on the api backend, with the request replaced by a stub that raises the queued errors.
    Waits before a retry are recorded, not slept."""
    attempts, errors, pauses = [], [], []

    def send(cfg, system, user):
        attempts.append(user)
        if errors:
            raise errors.pop(0)
        return "ok"

    monkeypatch.setenv("LLM_BACKEND", "api")
    monkeypatch.setattr(llm, "_call_api", send)
    monkeypatch.setattr(llm, "_pause", pauses.append)
    return NS(attempts=attempts, errors=errors, pauses=pauses)


def _status_error(name, status, headers=None):
    err = _sdk_error(name, status)
    err.response.headers.update(headers or {})
    return err


@pytest.mark.parametrize("name,status,headers,low,high", [
    ("RateLimitError", 429, {"retry-after": "3"}, 3, 3),
    ("RateLimitError", 429, {"retry-after": "120"}, 10, 10),           # capped
    ("RateLimitError", 429, {}, 1, 2),
    ("InternalServerError", 529, {}, 1, 2),                             # overloaded
])
def test_rate_limit_or_overload_waits_before_the_retry(flaky, name, status, headers, low, high):
    """The SDK's own retries (which waited) are off, so call() must wait: an immediate retry of a 429
    fails the same way and escalates the ticket as a model error."""
    flaky.errors.append(_status_error(name, status, headers))
    assert llm.call("classifier", "S", "U") == "ok" and len(flaky.attempts) == 2
    [wait] = flaky.pauses
    assert low <= wait <= high


def test_a_timeout_is_retried_at_once(flaky):
    flaky.errors.append(_sdk_error("APITimeoutError"))
    assert llm.call("classifier", "S", "U") == "ok" and flaky.pauses == [0.0]


def test_before_retry_stops_the_second_attempt(flaky):
    class Stop(BaseException):
        pass

    def stop():
        raise Stop

    flaky.errors.append(_sdk_error("APITimeoutError"))
    with llm.before_retry(stop), pytest.raises(Stop):
        llm.call("classifier", "S", "U")
    assert len(flaky.attempts) == 1


@pytest.mark.parametrize("name,status", [("APITimeoutError", None), ("APIConnectionError", None),
                                         ("RateLimitError", 429), ("InternalServerError", 500)])
def test_transient_error_is_retried_once(flaky, name, status):
    if name == "APIConnectionError":
        import anthropic

        err = _sdk_error("APITimeoutError")
        err = anthropic.APIConnectionError(request=err.request)
    else:
        err = _sdk_error(name, status)
    flaky.errors.append(err)
    assert llm.call("classifier", "S", "U") == "ok" and len(flaky.attempts) == 2

    flaky.attempts.clear()
    flaky.errors.extend([err, err])
    with pytest.raises(RuntimeError) as info:
        llm.call("classifier", "S", "U")
    assert len(flaky.attempts) == 2 and info.value.__cause__ is err


@pytest.mark.parametrize("name,status", [("BadRequestError", 400), ("AuthenticationError", 401),
                                         ("PermissionDeniedError", 403), ("NotFoundError", 404)])
def test_rejected_request_is_not_retried(flaky, name, status):
    err = _sdk_error(name, status)
    flaky.errors.append(err)
    with pytest.raises(type(err)):
        llm.call("classifier", "S", "U")
    assert len(flaky.attempts) == 1


@pytest.mark.parametrize("err", [llm.CacheMiss("miss"), llm.BudgetExceeded("cap"), llm.BackendError("no")])
def test_our_own_refusals_are_not_retried(flaky, err):
    flaky.errors.append(err)
    with pytest.raises(type(err)):
        llm.call("classifier", "S", "U")
    assert len(flaky.attempts) == 1


def test_cli_failure_is_still_retried_once(monkeypatch):
    attempts = []

    def send(cfg, system, user):
        attempts.append(1)
        if len(attempts) == 1:
            raise RuntimeError("claude -p exited 1")
        return "ok"

    monkeypatch.setenv("LLM_BACKEND", "cli")
    monkeypatch.setattr(llm, "_call_cli", send)
    assert llm.call("classifier", "S", "U") == "ok" and len(attempts) == 2


def test_api_client_has_no_sdk_retries_and_a_timeout(monkeypatch):
    import anthropic

    made = {}

    class FakeClient:
        def __init__(self, **kw):
            made.update(kw)

    monkeypatch.setattr(anthropic, "Anthropic", FakeClient)
    monkeypatch.setattr(llm, "_client", None)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-a-key")
    llm._get_client()
    assert made["max_retries"] == 0 and made["timeout"] == 60.0
    assert config.load_yaml("models.yaml")["timeout_s"] == 60


def _create_recorder(calls, geo=None):
    def create(**kw):
        calls.append(kw)
        usage = NS(input_tokens=10, output_tokens=5, cache_read_input_tokens=0, cache_creation_input_tokens=0)
        if geo:
            usage.inference_geo = geo
        return NS(content=[NS(type="text", text="OK")], stop_reason="end_turn", usage=usage)
    return create


def test_unpriced_model_fails_closed_under_a_budget(monkeypatch):
    calls = []
    monkeypatch.setattr(llm, "_get_client", lambda: NS(messages=NS(create=_create_recorder(calls))))
    monkeypatch.setattr(llm, "_spent", {"usd": 0.0})
    cfg = {"model": "claude-unpriced-9", "max_tokens": 100}
    monkeypatch.setenv("LLM_BUDGET_USD", "1")
    with pytest.raises(llm.BackendError, match="No price"):
        llm._call_api(cfg, "S", "U")
    assert calls == []                                                  # refused before any request
    monkeypatch.setenv("LLM_BUDGET_USD", "0")                           # no cap: nothing to count against
    assert llm._call_api(cfg, "S", "U") == "OK" and len(calls) == 1
    assert llm.price_usd("unknown", NS(input_tokens=1, output_tokens=1)) is None


@pytest.mark.parametrize("cap", ["nan", "-1", "inf", "five"])
def test_a_budget_that_is_not_a_number_of_dollars_refuses(monkeypatch, cap):
    """NaN compares as never reached: it used to switch the cap off."""
    calls = []
    monkeypatch.setattr(llm, "_get_client", lambda: NS(messages=NS(create=_create_recorder(calls))))
    monkeypatch.setenv("LLM_BUDGET_USD", cap)
    with pytest.raises(llm.BackendError, match="LLM_BUDGET_USD"):
        llm._call_api({"model": "claude-haiku-5-5", "max_tokens": 100}, "S", "U")
    assert calls == []


def test_budget_accepts_zero_and_dollars(monkeypatch):
    monkeypatch.setenv("LLM_BUDGET_USD", "0")
    assert llm.budget_usd() == 0
    monkeypatch.setenv("LLM_BUDGET_USD", "2.5")
    assert llm.budget_usd() == 2.5
    monkeypatch.delenv("LLM_BUDGET_USD")
    assert llm.budget_usd() == 5.0                                      # models.yaml


def test_partial_price_fails_closed_before_the_request(monkeypatch):
    """A price with only input/output used to pass the check, then fail after the paid reply (uncounted,
    and retried: paid twice)."""
    real = llm.load_yaml

    def with_partial_price(name):
        data = real(name)
        if name == "models.yaml":
            data = {**data, "prices": {**data["prices"], "claude-x": {"input": 2.0, "output": 10.0}}}
        return data

    calls = []
    monkeypatch.setattr(llm, "load_yaml", with_partial_price)
    monkeypatch.setattr(llm, "_get_client", lambda: NS(messages=NS(create=_create_recorder(calls))))
    monkeypatch.setattr(llm, "_spent", {"usd": 0.0})
    monkeypatch.setenv("LLM_BUDGET_USD", "5")
    with pytest.raises(llm.BackendError, match="cache_write"):
        llm._call_api({"model": "claude-x", "max_tokens": 100}, "S", "U")
    assert calls == []
    monkeypatch.setenv("LLM_BUDGET_USD", "0")                           # no cap: sent, and pricing can't crash
    assert llm._call_api({"model": "claude-x", "max_tokens": 100}, "S", "U") == "OK" and len(calls) == 1
    assert llm.price_usd("claude-x", NS(input_tokens=1, output_tokens=1)) is None


def test_api_records_inference_geo_and_a_role_timeout(monkeypatch):
    calls = []
    monkeypatch.setattr(llm, "_get_client", lambda: NS(messages=NS(create=_create_recorder(calls, geo="us"))))
    monkeypatch.setattr(llm, "_spent", {"usd": 0.0})
    llm._call_api({"model": "claude-haiku-5-5", "max_tokens": 100, "timeout_s": 600}, "S", "U")
    assert llm.last_usage()["inference_geo"] == "us" and calls[0]["timeout"] == 600.0
    llm._call_api({"model": "claude-haiku-5-5", "max_tokens": 100}, "S", "U")
    assert "timeout" not in calls[1]                                    # the client's 60 s applies


# --- contract D: cache-only replay ---

def test_cache_only_replays_hits_and_raises_on_a_miss(monkeypatch, tmp_path):
    sent = []
    monkeypatch.setenv("LLM_BACKEND", "api")
    monkeypatch.setenv("LLM_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(llm, "_call_api", lambda cfg, s, u: sent.append(u) or f"reply to {u}")
    assert llm.call("classifier", "S", "stored") == "reply to stored" and sent == ["stored"]

    monkeypatch.setenv("LLM_CACHE_ONLY", "1")
    assert llm.call("classifier", "S", "stored") == "reply to stored"
    assert llm.last_usage()["cached"] is True
    with pytest.raises(llm.CacheMiss):
        llm.call("classifier", "S", "never seen")
    assert sent == ["stored"]                                           # nothing sent, no retry
    assert not list(tmp_path.glob("*.lock"))                            # lock released after the miss


def test_cache_only_needs_a_cache_dir(monkeypatch):
    monkeypatch.setenv("LLM_BACKEND", "cli")
    monkeypatch.setenv("LLM_CACHE_ONLY", "1")
    monkeypatch.setattr(llm, "_call_cli", lambda *a: pytest.fail("must not call a model"))
    with pytest.raises(llm.BackendError, match="LLM_CACHE_DIR"):
        llm.call("classifier", "S", "U")


# --- contract C: real-data guard ---

@pytest.mark.parametrize("var,value,needle", [("LLM_BACKEND", "cli", "cli"),
                                              ("LLM_PROFILE", "groq", "LLM_PROFILE"),
                                              ("LLM_CACHE_DIR", "runs/cache", "LLM_CACHE_DIR"),
                                              ("LLM_CACHE_ONLY", "1", "LLM_CACHE_ONLY")])
def test_real_data_refuses_development_paths(monkeypatch, var, value, needle):
    monkeypatch.setenv("LLM_BACKEND", "api")
    monkeypatch.setenv(var, value)
    llm.assert_real_data_safe()                                         # synthetic data: allowed
    monkeypatch.setenv("REAL_DATA", "1")
    assert llm.real_data()
    with pytest.raises(llm.BackendError, match=needle) as info:
        llm.assert_real_data_safe()
    assert "REAL_DATA=1" in str(info.value)


@pytest.mark.parametrize("value", ["1", "y", "2", "enabled", "TRUE", " on "])
def test_real_data_fails_closed_on_any_value_that_is_not_off(monkeypatch, value):
    monkeypatch.setenv("REAL_DATA", value)
    monkeypatch.setenv("LLM_BACKEND", "cli")
    assert llm.real_data()
    with pytest.raises(llm.BackendError):
        llm.assert_real_data_safe()


@pytest.mark.parametrize("value", ["", "0", "false", "No", "off"])
def test_real_data_off_values(monkeypatch, value):
    monkeypatch.setenv("REAL_DATA", value)
    assert not llm.real_data()


def test_real_data_refuses_another_api_endpoint(monkeypatch):
    """The SDK reads ANTHROPIC_BASE_URL (also from .env): tickets and the key would go to that host."""
    monkeypatch.setenv("LLM_BACKEND", "api")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://127.0.0.1:9")
    llm.assert_real_data_safe()                                         # synthetic data: allowed
    monkeypatch.setenv("REAL_DATA", "1")
    with pytest.raises(llm.BackendError, match="ANTHROPIC_BASE_URL"):
        llm.assert_real_data_safe()
    for ok in ("https://api.anthropic.com", "https://api.anthropic.com/"):
        monkeypatch.setenv("ANTHROPIC_BASE_URL", ok)
        llm.assert_real_data_safe()


def test_real_data_on_the_api_is_allowed_and_checked_by_call(monkeypatch):
    monkeypatch.setenv("REAL_DATA", "1")
    monkeypatch.setenv("LLM_BACKEND", "api")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-a-key")
    llm.assert_real_data_safe()
    monkeypatch.setenv("LLM_BACKEND", "cli")
    monkeypatch.setattr(llm, "_call_cli", lambda *a: pytest.fail("must not call a model"))
    with pytest.raises(llm.BackendError) as info:
        llm.call("classifier", "S", "U")
    assert "sk-test" not in str(info.value)


# --- scripts/run_batch.py ---

def _run_batch(monkeypatch, tmp_path, n_tickets, *args):
    spec = importlib.util.spec_from_file_location("run_batch_under_test", ROOT / "scripts/run_batch.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    src = tmp_path / "set.jsonl"
    src.write_text("\n".join(json.dumps({"id": f"t{i}", "text": TICKET}) for i in range(n_tickets)), encoding="utf-8")
    out = tmp_path / "run.json"
    monkeypatch.setattr(sys, "argv", ["run_batch.py", str(src), "--out", str(out), "--workers", "2", *args])
    return mod, out


def test_run_batch_records_mode_and_makes_no_call_when_off(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("PIPELINE_MODE", "off")
    monkeypatch.setenv("LLM_BACKEND", "api")
    mod, out = _run_batch(monkeypatch, tmp_path, 3)
    monkeypatch.setattr(llm, "_call_api", lambda *a: pytest.fail("must not call a model"))
    mod.main()
    run = json.loads(out.read_text(encoding="utf-8"))
    assert run["meta"]["mode"] == "off" and run["meta"]["real_data"] is False
    assert [t["result"]["flags"] for t in run["tickets"]] == [["pipeline_off"]] * 3
    assert run["meta"]["usage"]["model_calls"] == 0


def test_run_batch_refuses_too_many_tickets(monkeypatch, tmp_path):
    mod, out = _run_batch(monkeypatch, tmp_path, 3)
    monkeypatch.setattr(mod, "limits", lambda: {"max_batch_tickets": 2})
    with pytest.raises(SystemExit, match="max_batch_tickets"):
        mod.main()
    assert not out.exists()


def test_run_batch_refuses_no_mask_and_cli_with_real_data(monkeypatch, tmp_path):
    monkeypatch.setenv("REAL_DATA", "1")
    monkeypatch.setenv("LLM_BACKEND", "api")
    mod, out = _run_batch(monkeypatch, tmp_path, 1, "--no-mask")
    with pytest.raises(SystemExit, match="--no-mask"):
        mod.main()
    monkeypatch.setenv("LLM_BACKEND", "cli")
    mod, out = _run_batch(monkeypatch, tmp_path, 1)
    with pytest.raises(SystemExit, match="Refused"):
        mod.main()
    assert not out.exists()


def test_run_batch_saves_a_ticket_with_a_lone_surrogate(monkeypatch, tmp_path):
    """The final save used to raise UnicodeEncodeError: every other ticket's spend was lost."""
    monkeypatch.setenv("PIPELINE_MODE", "off")
    monkeypatch.setenv("LLM_BACKEND", "api")
    mod, out = _run_batch(monkeypatch, tmp_path, 2)
    src = Path(sys.argv[1])
    src.write_text('{"id": "t0", "text": "\\ud83d ' + TICKET + '"}\n{"id": "t1", "text": "' + TICKET + '"}\n',
                   encoding="utf-8")
    mod.main()
    run = json.loads(out.read_text(encoding="utf-8"))
    assert [t["ticket"]["text"] for t in run["tickets"]] == ["? " + TICKET, TICKET]


def test_run_batch_save_is_whole_or_nothing(monkeypatch, tmp_path):
    mod, out = _run_batch(monkeypatch, tmp_path, 1)
    out.write_text("an earlier run", encoding="utf-8")
    with pytest.raises(UnicodeEncodeError):
        mod.save(out, "\ud83d")
    assert out.read_text(encoding="utf-8") == "an earlier run" and list(tmp_path.glob("*.tmp")) == []


def test_run_batch_with_real_data_records_it(monkeypatch, tmp_path):
    monkeypatch.setenv("REAL_DATA", "1")
    monkeypatch.setenv("LLM_BACKEND", "api")
    monkeypatch.setenv("PIPELINE_MODE", "off")
    mod, out = _run_batch(monkeypatch, tmp_path, 1)
    mod.main()
    meta = json.loads(out.read_text(encoding="utf-8"))["meta"]
    assert meta["real_data"] is True and meta["masked"] is True and meta["mode"] == "off"
    if os.name == "posix":
        assert out.stat().st_mode & 0o777 == 0o600                     # customer text: owner only


def test_run_batch_refuses_a_bad_budget(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_BUDGET_USD", "nan")
    mod, out = _run_batch(monkeypatch, tmp_path, 1)
    with pytest.raises(SystemExit, match="LLM_BUDGET_USD"):
        mod.main()
    assert not out.exists()
