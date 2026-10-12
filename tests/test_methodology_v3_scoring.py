import pytest

from src.gtm_audit.methodology_v3.config import load_methodology
from src.gtm_audit.methodology_v3.eligibility import is_score_eligible, normalize_confidence
from src.gtm_audit.methodology_v3.severity import Severity, escalate

GATE = 0.8


@pytest.fixture(scope="module")
def methodology():
    return load_methodology()


@pytest.mark.parametrize("severity, on_key_task, expected, escalated", [
    (Severity.CRITICAL, False, Severity.CRITICAL, False),
    (Severity.HIGH, False, Severity.HIGH, False),
    (Severity.MEDIUM, False, Severity.MEDIUM, False),
    (Severity.LOW, False, Severity.LOW, False),
    (Severity.CRITICAL, True, Severity.CRITICAL, False),
    (Severity.HIGH, True, Severity.CRITICAL, True),
    (Severity.MEDIUM, True, Severity.HIGH, True),
    (Severity.LOW, True, Severity.MEDIUM, True),
])
def test_escalation_table(severity, on_key_task, expected, escalated):
    assert escalate(severity, on_key_task) == (expected, escalated)


def test_severity_rank_orders_critical_first():
    assert [s.rank for s in (Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW)] == [0, 1, 2, 3]
    assert Severity("high") is Severity.HIGH


@pytest.mark.parametrize("value, expected", [
    ("0.85", 0.85),
    (85, 0.85),
    (None, 0.0),
    ("abc", 0.0),
    (1.4, 0.014),  # only values > 1 are read as percentages
    (1, 1.0),
    (0.8, 0.8),
    (-0.2, 0.0),
    (250, 1.0),
    (True, 0.0),
])
def test_normalize_confidence(value, expected):
    assert normalize_confidence(value) == pytest.approx(expected)


def test_measured_rows_are_always_eligible(methodology):
    criterion = methodology.criterion("accessibility.text_contrast")
    assert is_score_eligible({}, criterion, GATE) is True


@pytest.mark.parametrize("row, expected", [
    ({"confidence": 0.8, "elementIds": ["e4"]}, True),
    ({"confidence": 0.79, "elementIds": ["e4"]}, False),
    ({"confidence": 0.9}, False),
    ({"confidence": 0.9, "elementIds": []}, False),
    ({"confidence": 0.9, "screenshotRegion": {"x": 0, "y": 0, "width": 10, "height": 10}}, True),
    ({"confidence": "85", "elementIds": ["e4"]}, True),
    ({"outcome": "pass", "confidence": 0.9}, True),  # passes are reported as ids, with no location to cite
    ({"outcome": "pass", "confidence": 0.5}, False),
])
def test_ai_assessed_eligibility(methodology, row, expected):
    criterion = methodology.criterion("usability.primary_action_clear")
    assert is_score_eligible(row, criterion, GATE) is expected


@pytest.mark.parametrize("row, expected", [
    ({}, False),
    ({"reviewStatus": "pending"}, False),
    ({"reviewStatus": "confirmed"}, True),
])
def test_manual_only_needs_confirmation(methodology, row, expected):
    criterion = methodology.criterion("usability.destructive_action_safeguard")
    assert is_score_eligible(row, criterion, GATE) is expected


# --- Task 4: axis scoring -------------------------------------------------

from src.gtm_audit.methodology_v3.scoring import dedupe_key, maturity_for, score_axis_v3


def _passes(axis, target="website", **extra):
    return [{"criterionId": c.id, "outcome": "pass", "pageId": "home", "confidence": 0.95, "reviewStatus": "confirmed", **extra}
            for c in axis.criteria if target in c.targets]


def _fail(criterion_id, severity="medium", **extra):
    row = {"criterionId": criterion_id, "outcome": "fail", "severity": severity, "pageId": "home", "elementIds": ["e1"],
           "confidence": 0.95, "reviewStatus": "confirmed"}
    row.update(extra)
    return row


def _without(rows, criterion_id):
    return [row for row in rows if row["criterionId"] != criterion_id]


def _small_axis(methodology, criteria_targets):
    template = methodology.criterion("accessibility.text_contrast")
    criteria = tuple(
        template.model_copy(update={"id": f"accessibility.c{i}", "targets": targets, "logical_defect_family": f"fam-{i}"})
        for i, targets in enumerate(criteria_targets)
    )
    return methodology.axis("accessibility").model_copy(update={"criteria": criteria})


def test_all_pass_scores_100_and_level_5(methodology):
    axis = methodology.axis("usability")
    result = score_axis_v3(_passes(axis), axis, "website", methodology.scoring)
    assert result.score == 100 and result.maturity == 5
    assert result.worst_severity is None and result.scored_defects == 0
    assert result.maturity_label.en == "Excellent"


def test_core_fail_and_supporting_pass_scores_twenty(methodology):
    axis = _small_axis(methodology, [("website",), ("website",)])
    core, supporting = axis.criteria
    axis = axis.model_copy(update={"criteria": (core, supporting.model_copy(update={"weight": "supporting"}))})
    rows = [_fail(core.id, "medium"), {"criterionId": supporting.id, "outcome": "pass"}]
    result = score_axis_v3(rows, axis, "website", methodology.scoring)
    assert result.score == 20 and result.maturity == 1


def test_critical_fail_on_ninety_five_axis_caps_maturity_at_two(methodology):
    axis = methodology.axis("usability")
    rows = _without(_passes(axis), "usability.form_input_effort") + [_fail("usability.form_input_effort", "critical")]
    result = score_axis_v3(rows, axis, "website", methodology.scoring)
    assert result.score == 70  # base 95 (19 of 20 weight) minus 25
    assert result.maturity == 2 and result.worst_severity is Severity.CRITICAL


def test_maturity_caps(methodology):
    bands = methodology.scoring.maturity_bands
    assert maturity_for(95, None, bands) == 5
    assert maturity_for(95, Severity.HIGH, bands) == 4
    assert maturity_for(95, Severity.CRITICAL, bands) == 2
    assert maturity_for(95, Severity.MEDIUM, bands) == 5
    assert maturity_for(20, Severity.CRITICAL, bands) == 1
    assert maturity_for(75, None, bands) == 4 and maturity_for(74.9, None, bands) == 3


def test_high_fail_caps_maturity_at_four(methodology):
    axis = methodology.axis("usability")
    rows = _without(_passes(axis), "usability.form_input_effort") + [_fail("usability.form_input_effort", "high")]
    assert score_axis_v3(rows, axis, "website", methodology.scoring).maturity <= 4


def test_unknown_or_foreign_criterion_is_ignored(methodology):
    axis = methodology.axis("usability")
    rows = _passes(axis) + [_fail("usability.does_not_exist", "critical"), _fail("trust.pricing_transparency", "critical"), {"outcome": "fail"}]
    result = score_axis_v3(rows, axis, "website", methodology.scoring)
    assert result.score == 100 and result.scored_defects == 0


def test_distinct_defects_without_location_never_collapse(methodology):
    axis = methodology.axis("usability")
    a = {"criterionId": "usability.form_input_effort", "outcome": "fail", "severity": "medium", "findingId": "f1"}
    b = {"criterionId": "usability.form_input_effort", "outcome": "fail", "severity": "medium", "findingId": "f2"}
    criterion = methodology.criterion("usability.form_input_effort")
    assert dedupe_key(a, criterion) != dedupe_key(b, criterion)
    rows = _without(_passes(axis), "usability.form_input_effort") + [a, b]
    result = score_axis_v3(rows, axis, "website", methodology.scoring)
    assert result.scored_defects == 2 and result.score == 85  # base 95 minus 2 x 5


def test_same_defect_from_three_detectors_is_penalised_once(methodology):
    axis = methodology.axis("accessibility")
    rows = _without(_passes(axis), "accessibility.text_contrast") + [
        _fail("accessibility.text_contrast", "medium", source="axe", findingId="axe-1", elementIds=["e2", "e1"]),
        _fail("accessibility.text_contrast", "medium", source="custom", findingId="chk-9", elementIds=["e1", "e2"]),
        _fail("accessibility.text_contrast", "high", source="ai", findingId="ai-3", elementIds=["e1", "e2"]),
    ]
    result = score_axis_v3(rows, axis, "website", methodology.scoring)
    assert result.scored_defects == 1
    assert result.worst_severity is Severity.HIGH  # highest severity kept for the key
    total = sum(c.numeric_weight for c in axis.criteria)
    assert result.score == pytest.approx(100 * (total - 3) / total - 12)


def test_figma_scores_from_evaluated_criteria_with_coverage(methodology):
    runtime = ("website", "webapp", "mobile")
    axis = _small_axis(methodology, [("website", "figma")] * 4 + [runtime] * 6)
    rows = [{"criterionId": c.id, "outcome": "pass"} for c in axis.criteria]
    result = score_axis_v3(rows, axis, "figma", methodology.scoring)
    assert result is not None and result.score == 100
    assert result.coverage.evaluated == 4 and result.coverage.applicable == 4
    assert set(result.coverage.not_applicable_for_target) == {f"accessibility.c{i}" for i in range(4, 10)}
    assert result.coverage.not_evaluated == ()


def test_unevaluated_criteria_are_listed_and_zero_evaluated_scores_zero(methodology):
    axis = _small_axis(methodology, [("website",)] * 3)
    rows = [{"criterionId": "accessibility.c0", "outcome": "warning"}, {"criterionId": "accessibility.c1", "outcome": "unknown"}]
    result = score_axis_v3(rows, axis, "website", methodology.scoring)
    assert result.score == 0.0 and result.maturity == 1
    assert result.coverage.evaluated == 0 and result.coverage.applicable == 3
    assert set(result.coverage.not_evaluated) == {"accessibility.c0", "accessibility.c1", "accessibility.c2"}


def test_zero_applicable_criteria_returns_none(methodology):
    axis = _small_axis(methodology, [("website",)] * 3)
    assert score_axis_v3([], axis, "figma", methodology.scoring) is None


def test_key_task_escalation_is_applied_and_recorded(methodology):
    axis = methodology.axis("usability")
    rows = _without(_passes(axis), "usability.form_input_effort") + [
        _fail("usability.form_input_effort", "medium", onKeyTask=True, findingId="f7")
    ]
    result = score_axis_v3(rows, axis, "website", methodology.scoring)
    assert result.worst_severity is Severity.HIGH
    assert result.score == 83  # base 95 minus high 12
    assert result.escalations == ("f7",)


def test_low_confidence_ai_fail_is_an_observation_only(methodology):
    axis = methodology.axis("usability")
    weak = _fail("usability.primary_action_clear", "high", confidence=0.5, findingId="ai-weak")
    result = score_axis_v3(_passes(axis) + [weak], axis, "website", methodology.scoring)
    assert result.score == 100 and result.scored_defects == 0
    assert [row["findingId"] for row in result.observations] == ["ai-weak"]


def test_missing_severity_on_fail_defaults_to_medium(methodology):
    axis = methodology.axis("usability")
    rows = _without(_passes(axis), "usability.form_input_effort") + [_fail("usability.form_input_effort", None)]
    assert score_axis_v3(rows, axis, "website", methodology.scoring).score == 90
    assert score_axis_v3(rows, axis, "website", methodology.scoring).score == 90


# --- Task 5: overall score --------------------------------------------------

from src.gtm_audit.methodology_v3.scoring import AxisScore, Coverage, overall_v3


def _axis_score(methodology, axis_id, score, maturity=None):
    bands = methodology.scoring.maturity_bands
    level = maturity if maturity is not None else maturity_for(score, None, bands)
    return AxisScore(axis_id=axis_id, score=score, maturity=level, maturity_label=bands[5 - level].label,
                     coverage=Coverage(1, 1, (), ()), worst_severity=None, scored_defects=0, observations=(), escalations=())


def _all_axes(methodology, scores):
    return [_axis_score(methodology, axis_id, score) for axis_id, score in zip(AXIS_ORDER, scores)]


AXIS_ORDER = ("usability", "navigation", "visual", "content", "accessibility", "performance", "trust")


def test_overall_equal_weight_average(methodology):
    result = overall_v3(_all_axes(methodology, [100, 90, 80, 70, 60, 80, 80]), None, methodology)
    assert result.score == pytest.approx(80)
    assert result.axes_scored == 7
    assert result.weights_used == {axis_id: 1.0 for axis_id in AXIS_ORDER}


def test_ecommerce_weighting_pulls_toward_trust(methodology):
    scores = _all_axes(methodology, [80, 80, 80, 80, 80, 80, 40])
    equal = overall_v3(scores, None, methodology)
    ecommerce = overall_v3(scores, "ecommerce", methodology)
    assert ecommerce.score < equal.score
    assert ecommerce.weights_used["trust"] == 1.5 and ecommerce.weights_used["visual"] == 1.0


@pytest.mark.parametrize("product_type", ["spaceship", None, ""])
def test_unknown_or_missing_product_type_uses_equal_weights(methodology, product_type):
    result = overall_v3(_all_axes(methodology, [100, 50, 50, 50, 50, 50, 50]), product_type, methodology)
    assert result.score == pytest.approx(400 / 7)
    assert set(result.weights_used.values()) == {1.0}


def test_none_axes_are_skipped_and_weights_renormalised(methodology):
    scores = [_axis_score(methodology, "usability", 90), None, _axis_score(methodology, "trust", 60)]
    result = overall_v3(scores, "ecommerce", methodology)
    assert result.axes_scored == 2
    assert result.score == pytest.approx((90 * 1.3 + 60 * 1.5) / 2.8)
    assert set(result.weights_used) == {"usability", "trust"}


def test_overall_maturity_is_capped_by_worst_axis(methodology):
    scores = [_axis_score(methodology, "usability", 100), _axis_score(methodology, "navigation", 100),
              _axis_score(methodology, "visual", 95, maturity=1)]
    result = overall_v3(scores, None, methodology)
    assert result.score > 90 and result.maturity <= 2
    assert result.maturity_label.en == "Weak"


def test_all_none_scores_zero(methodology):
    result = overall_v3([None, None], "saas", methodology)
    assert (result.score, result.maturity, result.axes_scored) == (0.0, 1, 0)


def test_seeded_product_type_weights(methodology):
    weights = methodology.product_type_weights
    assert set(weights) == {"ecommerce", "saas", "content", "leadgen", "finance", "public_service"}
    assert weights["ecommerce"] == {"trust": 1.5, "usability": 1.3, "performance": 1.2}
    assert weights["finance"] == {"trust": 1.6, "accessibility": 1.2}
    assert weights["public_service"] == {"accessibility": 1.6, "content": 1.3}


# --- Task 5: overall score --------------------------------------------------

from src.gtm_audit.methodology_v3.scoring import AxisScore, Coverage, overall_v3


def _axis_score(methodology, axis_id, score, maturity=None):
    bands = methodology.scoring.maturity_bands
    level = maturity if maturity is not None else maturity_for(score, None, bands)
    return AxisScore(axis_id=axis_id, score=score, maturity=level, maturity_label=bands[5 - level].label,
                     coverage=Coverage(1, 1, (), ()), worst_severity=None, scored_defects=0, observations=(), escalations=())


def _all_axes(methodology, scores):
    return [_axis_score(methodology, axis_id, score) for axis_id, score in zip(AXIS_ORDER, scores)]


AXIS_ORDER = ("usability", "navigation", "visual", "content", "accessibility", "performance", "trust")


def test_overall_equal_weight_average(methodology):
    result = overall_v3(_all_axes(methodology, [100, 90, 80, 70, 60, 80, 80]), None, methodology)
    assert result.score == pytest.approx(80)
    assert result.axes_scored == 7
    assert result.weights_used == {axis_id: 1.0 for axis_id in AXIS_ORDER}


def test_ecommerce_weighting_pulls_toward_trust(methodology):
    scores = _all_axes(methodology, [80, 80, 80, 80, 80, 80, 40])
    equal = overall_v3(scores, None, methodology)
    ecommerce = overall_v3(scores, "ecommerce", methodology)
    assert ecommerce.score < equal.score
    assert ecommerce.weights_used["trust"] == 1.5 and ecommerce.weights_used["visual"] == 1.0


@pytest.mark.parametrize("product_type", ["spaceship", None, ""])
def test_unknown_or_missing_product_type_uses_equal_weights(methodology, product_type):
    result = overall_v3(_all_axes(methodology, [100, 50, 50, 50, 50, 50, 50]), product_type, methodology)
    assert result.score == pytest.approx(400 / 7)
    assert set(result.weights_used.values()) == {1.0}


def test_none_axes_are_skipped_and_weights_renormalised(methodology):
    scores = [_axis_score(methodology, "usability", 90), None, _axis_score(methodology, "trust", 60)]
    result = overall_v3(scores, "ecommerce", methodology)
    assert result.axes_scored == 2
    assert result.score == pytest.approx((90 * 1.3 + 60 * 1.5) / 2.8)
    assert set(result.weights_used) == {"usability", "trust"}


def test_overall_maturity_is_capped_by_worst_axis(methodology):
    scores = [_axis_score(methodology, "usability", 100), _axis_score(methodology, "navigation", 100),
              _axis_score(methodology, "visual", 95, maturity=1)]
    result = overall_v3(scores, None, methodology)
    assert result.score > 90 and result.maturity <= 2
    assert result.maturity_label.en == "Weak"


def test_all_none_scores_zero(methodology):
    result = overall_v3([None, None], "saas", methodology)
    assert (result.score, result.maturity, result.axes_scored) == (0.0, 1, 0)


def test_seeded_product_type_weights(methodology):
    weights = methodology.product_type_weights
    assert set(weights) == {"ecommerce", "saas", "content", "leadgen", "finance", "public_service"}
    assert weights["ecommerce"] == {"trust": 1.5, "usability": 1.3, "performance": 1.2}
    assert weights["finance"] == {"trust": 1.6, "accessibility": 1.2}
    assert weights["public_service"] == {"accessibility": 1.6, "content": 1.3}


# --- Final review fixes -----------------------------------------------------

from src.gtm_audit.methodology_v3.scoring import unscored_rows


def test_overall_skips_axes_with_nothing_evaluated(methodology):
    empty = _axis_score(methodology, "trust", 0.0, maturity=1)
    empty = empty.__class__(**{**empty.__dict__, "coverage": Coverage(0, 9, (), ())})
    scores = _all_axes(methodology, [100] * 6) + [empty]
    result = overall_v3(scores, None, methodology)
    assert result.axes_scored == 6 and result.score == 100 and result.maturity == 5
    assert "trust" not in result.weights_used


def test_location_less_rows_from_a_generator_never_collapse(methodology):
    axis = methodology.axis("usability")
    passes = _without(_passes(axis), "usability.form_input_effort")

    def stream():  # a streaming reader that reuses one buffer dict per row
        yield from passes
        buffer = {}
        for _ in range(3):
            buffer.clear()
            buffer.update({"criterionId": "usability.form_input_effort", "outcome": "fail", "severity": "low"})
            yield buffer

    assert score_axis_v3(stream(), axis, "website", methodology.scoring).scored_defects == 3


def test_severity_enum_is_honoured(methodology):
    axis = methodology.axis("usability")
    rows = _without(_passes(axis), "usability.form_input_effort") + [_fail("usability.form_input_effort", Severity.CRITICAL)]
    result = score_axis_v3(rows, axis, "website", methodology.scoring)
    assert result.worst_severity is Severity.CRITICAL and result.score == 70


def test_region_only_findings_on_one_page_stay_distinct(methodology):
    axis = methodology.axis("visual")
    region = lambda y: {"x": 0, "y": y, "width": 100, "height": 40}
    rows = _without(_passes(axis), "visual.visual_hierarchy") + [
        _fail("visual.visual_hierarchy", elementIds=[], screenshotRegion=region(0), findingId="a"),
        _fail("visual.visual_hierarchy", elementIds=[], screenshotRegion=region(500), findingId="b"),
    ]
    assert score_axis_v3(rows, axis, "website", methodology.scoring).scored_defects == 2


def test_page_types_limit_applicability(methodology):
    axis = methodology.axis("usability")
    rows = [row for row in _passes(axis) if "any" in methodology.criterion(row["criterionId"]).page_types]
    result = score_axis_v3(rows, axis, "website", methodology.scoring, page_types={"article"})
    assert "usability.form_input_effort" in result.coverage.not_applicable_for_target
    assert result.coverage.not_evaluated == ()
    assert result.coverage.evaluated == result.coverage.applicable


def test_page_types_omitted_keeps_every_target_criterion(methodology):
    axis = methodology.axis("usability")
    assert score_axis_v3([], axis, "website", methodology.scoring).coverage.applicable == len(axis.criteria)


def test_unknown_criterion_rows_are_reported_as_unscored(methodology):
    rows = [{"criterionId": "usability.typo", "findingId": "x"}, {"criterionId": "trust.pricing_transparency"}, {"outcome": "fail"}]
    assert [row.get("findingId") for row in unscored_rows(rows, methodology)] == ["x"]
