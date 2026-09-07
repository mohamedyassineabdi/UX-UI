from src.gtm_audit.scoring import RULE_AXIS_MAP, axis_mapping, deduplicate_findings, overall_score, score_axis
from src.gtm_audit.generate_gtm_audit import sheet_score


def row(outcome="pass", **extra):
    return {"outcome": outcome, "applicability": "applicable", "measurement": "measured", "confidence": 0.8, **extra}


def test_no_evidence_is_not_scored():
    result = score_axis([])
    assert result.scored is False and result.score is None


def test_na_unknown_and_collection_failures_do_not_contribute_credit():
    result = score_axis([row("pass"), row("fail"), row("pass", applicability="not_applicable"), row("unknown", measurement="not_measured"), row("unknown", measurement="collection_failed")])
    assert result.score == 50 and result.applicable_count == 4 and result.measured_count == 2
    assert result.not_measured_count == 1 and result.collection_failed_count == 1


def test_warning_is_a_caution_not_half_credit():
    result = score_axis([row("pass"), row("warning"), row("fail")])
    assert result.score == 50 and result.warning_count == 1 and result.measured_count == 2


def test_dedup_preserves_sources_but_distinct_targets_remain_distinct():
    base = {"ruleId": "rule_x", "provenance": {"pageRefs": [{"pageId": "p1"}]}, "target": "#email", "evidenceIds": ["e1"]}
    merged = deduplicate_findings([{**base, "source": "deterministic"}, {**base, "source": "wcag", "evidenceIds": ["e2"]}, {**base, "target": "#password", "source": "deterministic"}])
    assert len(merged) == 2
    assert any(item["confirmationCount"] == 2 and item["evidenceIds"] == ["e1", "e2"] for item in merged)


def test_critical_blocker_remains_visible_and_order_is_deterministic():
    axis = score_axis([row("pass")])
    critical = row("fail", severity="critical", provenance={"status": "verified"})
    assert overall_score([axis], [critical])["hasCriticalBlocker"] is True
    assert score_axis([row("fail"), row("pass")]).score == score_axis([row("pass"), row("fail")]).score


def test_explicit_mapping_beats_keywords_and_custom_rules_are_unmapped():
    RULE_AXIS_MAP["rule_explicit"] = {"flow_architecture": 1.0}
    try:
        assert axis_mapping({"ruleId": "rule_explicit", "sheet": "Forms", "criterion": "accessibility navigation task"}) == {"flow_architecture": 1.0}
        assert axis_mapping({"ruleId": "custom_rule", "sheet": "Forms"}) == {}
    finally:
        RULE_AXIS_MAP.pop("rule_explicit", None)


def test_empty_legacy_sheet_context_is_not_a_neutral_score_and_performance_is_not_tripled():
    assert sheet_score({}) is None
    source = open("src/gtm_audit/generate_gtm_audit.py", encoding="utf-8").read()
    assert '"coreWebVitals": performance_score' not in source
    assert '"pageSpeed": performance_score' not in source
