from pipeline.clean import clean, mask_for_logs
from pipeline.config import models, taxonomy
from pipeline.gate import check
from pipeline.route import route
from pipeline.schemas import Extraction


def ex(**kw):
    base = dict(category="transfers", subcategory="not_received", reference="88213", amount_iqd=50000, confidence=0.94)
    base.update(kw)
    return Extraction(**base)


TICKET = clean("حولت ٥٠ الف دينار الصبح وما وصلت لصديقي، رقم العملية ٨٨٢١٣")


# --- taxonomy and config ---

def test_taxonomy_shape():
    tax = taxonomy()
    assert len(tax.categories) == 8
    assert len(tax.subcategories) == 23
    for sub in tax.subcategories.values():
        assert sub.team in tax.teams
        assert sub.default_priority in {"P1", "P2", "P3"}


def test_every_role_has_a_model():
    for role in ["classifier", "drafter", "rechecker", "generator", "evaluator"]:
        assert models()[role]["model"]


# --- cleaning ---

def test_clean_converts_arabic_digits_and_whitespace():
    assert clean("رقم   ٨٨٢١٣\n") == "رقم 88213"


def test_mask_hides_long_numbers():
    assert mask_for_logs("رقمي 07712345678") == "رقمي 07*******78"


# --- confidence gate ---

def test_worked_example_passes():
    g = check(ex(), TICKET)
    assert not g.escalate and not g.needs_recheck


def test_invented_reference_is_capped_and_rechecked():
    g = check(ex(reference="99999"), TICKET)
    assert "ref_not_in_text" in g.flags
    assert g.confidence <= 0.60 and g.needs_recheck


def test_missing_required_field_caps_score():
    g = check(ex(amount_iqd=None), TICKET)
    assert "missing:amount" in g.flags and g.confidence <= 0.60


def test_low_confidence_escalates():
    assert check(ex(confidence=0.4), TICKET).escalate


def test_high_risk_is_always_rechecked():
    g = check(ex(subcategory="reversal_request", confidence=0.97), TICKET)
    assert g.needs_recheck and not g.escalate


def test_fraud_always_escalates():
    g = check(ex(category="fraud_security", subcategory="suspected_scam", confidence=0.99), TICKET)
    assert g.escalate and "fraud" in g.flags


def test_mismatched_category_escalates():
    assert check(ex(category="cards"), TICKET).escalate


# --- routing ---

def test_route_worked_example():
    assert route(ex(), TICKET) == ("transfers", "P2")


def test_large_amount_raises_priority():
    assert route(ex(amount_iqd=2_000_000), TICKET) == ("transfers", "P1")


def test_urgent_words_raise_priority():
    assert route(ex(subcategory="topup_failed", category="bills_topup"), "ضروري الرصيد ما وصل") == ("bills", "P2")
