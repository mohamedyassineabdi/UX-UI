"""v2 validation scenarios A–J (docs/METHODOLOGY_V2_VALIDATION.md §5), re-expressed on v3 axes."""
import importlib.util
from pathlib import Path

import pytest

from src.gtm_audit.methodology_v3 import AXIS_IDS, Severity, load_methodology, overall_v3, score_axis_v3
from src.gtm_audit.methodology_v3.rule_map import criterion_for_rule

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def methodology():
    return load_methodology()


def _clean(methodology, target="website"):
    """Every applicable criterion passes with eligible evidence."""
    return [{"criterionId": c.id, "outcome": "pass", "pageId": "home", "confidence": 0.95, "reviewStatus": "confirmed"}
            for axis in methodology.axes for c in axis.criteria if target in c.targets]


def _with(rows, *failures):
    failed = {row["criterionId"] for row in failures}
    return [row for row in rows if row["criterionId"] not in failed] + list(failures)


def _fail(criterion_id, severity="medium", **extra):
    return {"criterionId": criterion_id, "outcome": "fail", "severity": severity, "pageId": "home",
            "elementIds": ["e1"], "confidence": 0.95, "reviewStatus": "confirmed", **extra}


def _score(methodology, rows, target="website"):
    return {axis.id: score_axis_v3(rows, axis, target, methodology.scoring) for axis in methodology.axes}


def _hurt_axes(scores):
    return {axis_id for axis_id, result in scores.items() if result is not None and result.score < 100}


def test_a_clean_measured_audit_scores_100_everywhere(methodology):
    scores = _score(methodology, _clean(methodology))
    assert all(result.score == 100 and result.maturity == 5 for result in scores.values())
    overall = overall_v3(scores.values(), None, methodology)
    assert overall.score == 100 and overall.maturity == 5 and overall.axes_scored == len(AXIS_IDS)


def test_b_ambiguous_action_wording_hurts_content_only(methodology):
    rows = _with(_clean(methodology), _fail(criterion_for_rule("verbs-used-for-actions")))
    assert _hurt_axes(_score(methodology, rows)) == {"content"}


def test_c_axe_custom_and_ai_on_one_defect_is_one_consequence(methodology):
    rows = _with(_clean(methodology),
                 _fail(criterion_for_rule("Content:16"), findingId="custom-1"),
                 _fail(criterion_for_rule("axe:color-contrast"), findingId="axe-1"),
                 _fail("accessibility.text_contrast", "high", findingId="ai-1"))
    scores = _score(methodology, rows)
    assert _hurt_axes(scores) == {"accessibility"}
    assert scores["accessibility"].scored_defects == 1
    assert scores["accessibility"].worst_severity is Severity.HIGH


def test_d_control_activation_failure_hurts_usability_only(methodology):
    rows = _with(_clean(methodology), _fail(criterion_for_rule("Feedback:4"), "high"))
    assert _hurt_axes(_score(methodology, rows)) == {"usability"}


def test_e_structural_navigation_hurts_navigation_only(methodology):
    rows = _with(_clean(methodology), _fail(criterion_for_rule("Navigation:9")))
    assert _hurt_axes(_score(methodology, rows)) == {"navigation"}


def test_f_visual_hierarchy_hurts_visual_only(methodology):
    rows = _with(_clean(methodology), _fail(criterion_for_rule("visual-hierarchy-reflects-priority")))
    assert _hurt_axes(_score(methodology, rows)) == {"visual"}


def test_g_mixed_form_defects_are_attributed_one_per_axis(methodology):
    rows = _with(_clean(methodology),
                 _fail("accessibility.names_labels", elementIds=["e14"]),
                 _fail("usability.error_recovery", elementIds=["e14"]),
                 _fail("content.helpful_error_wording", elementIds=["e19"]))
    scores = _score(methodology, rows)
    assert _hurt_axes(scores) == {"accessibility", "usability", "content"}
    assert all(scores[axis_id].scored_defects == 1 for axis_id in ("accessibility", "usability", "content"))


def test_h_page_speed_metrics_on_one_page_are_one_performance_consequence(methodology):
    metrics = [_fail(criterion_for_rule(key), "high", elementIds=[], findingId=key) for key in ("lcp", "fcp", "tbt", "speed_index")]
    rows = [row for row in _clean(methodology) if row["criterionId"] not in {m["criterionId"] for m in metrics}] + metrics
    scores = _score(methodology, rows)
    assert _hurt_axes(scores) == {"performance"}
    assert scores["performance"].scored_defects == 1


def test_i_ai_only_finding_below_gate_is_an_observation(methodology):
    weak = _fail("visual.visual_hierarchy", "high", confidence=0.6, findingId="ai-weak")
    scores = _score(methodology, _with(_clean(methodology), weak))
    assert _hurt_axes(scores) == set()
    assert [row["findingId"] for row in scores["visual"].observations] == ["ai-weak"]


def test_j_no_evidence_still_produces_a_score_with_zero_coverage(methodology):
    scores = _score(methodology, [])
    for result in scores.values():
        assert result.score == 0.0 and result.maturity == 1
        assert result.coverage.evaluated == 0 and result.coverage.applicable > 0


def test_figma_target_omits_nothing_and_reports_runtime_criteria(methodology):
    scores = _score(methodology, _clean(methodology, "figma"), target="figma")
    assert all(result is not None for result in scores.values())
    assert "performance.lcp" in scores["performance"].coverage.not_applicable_for_target


def _renderer():
    spec = importlib.util.spec_from_file_location("render_methodology_doc", ROOT / "scripts" / "render_methodology_doc.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generated_methodology_doc_is_fresh(methodology):
    expected = _renderer().render(methodology)
    assert (ROOT / "docs" / "METHODOLOGY_V3.md").read_text(encoding="utf-8") == expected
