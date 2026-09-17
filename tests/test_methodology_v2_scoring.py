from src.gtm_audit.scoring import axis_mapping, deduplicate_findings, score_axis


def row(key, outcome="fail", **extra):
    return {
        "logicalRuleKey": key,
        "outcome": outcome,
        "applicability": "applicable",
        "measurement": "measured",
        "confidence": 0.8,
        "auditMode": "website",
        **extra,
    }


def test_v2_one_rule_has_one_primary_score_axis_not_sheet_fallback():
    assert axis_mapping(row("Labeling:4")) == {"content_microcopy": 1.0}
    assert axis_mapping(row("Forms:10")) == {"trust_accessibility": 1.0}
    assert axis_mapping(row("Forms:19")) == {"task_execution": 1.0}
    assert axis_mapping(row("visual-hierarchy-reflects-priority")) == {"ui_consistency": 1.0}
    assert axis_mapping(row("Content:16")) == {"trust_accessibility": 1.0}
    assert axis_mapping({"machine_criterion": "no-distracting-animation,no-distracting-animation-runtime"}) == {}


def test_structural_navigation_task_and_wording_rules_are_separated():
    assert axis_mapping(row("Navigation:9")) == {"flow_architecture": 1.0}
    assert axis_mapping(row("Navigation:8")) == {"content_microcopy": 1.0}
    assert axis_mapping(row("Navigation:23")) == {"task_execution": 1.0}
    assert axis_mapping(row("visual-grouping-proximity-alignment")) == {"ui_consistency": 1.0}


def test_accessibility_and_ai_eligibility_policy():
    assert axis_mapping(row("axe:button-name", measurementClass="standards_automated")) == {"trust_accessibility": 1.0}
    assert axis_mapping(row("accessible_name", measurementClass="standards_automated")) == {"trust_accessibility": 1.0}
    assert axis_mapping(row("keyboard_focus", measurementClass="browser_runtime")) == {"trust_accessibility": 1.0}
    assert axis_mapping(row("ai_visual", measurementClass="ai_visual")) == {}
    assert axis_mapping(row("lighthouse_category", measurementClass="standards_automated")) == {}


def test_performance_metric_family_has_one_score_consequence():
    result = score_axis([row("lcp", outcome="fail", target="page-1"), row("fcp", outcome="pass", target="page-1")])
    assert result.score == 0.0
    assert result.measured_count == 1


def test_modes_do_not_score_runtime_or_dom_rules_when_unavailable():
    assert axis_mapping(row("performance_runtime", auditMode="screenshot")) == {}
    assert axis_mapping(row("keyboard_focus", auditMode="figma")) == {}
    assert axis_mapping(row("axe:button-name", auditMode="mobile")) == {}
    assert axis_mapping(row("visual-hierarchy-reflects-priority", auditMode="screenshot")) == {"ui_consistency": 1.0}


def test_unmapped_v2_rule_is_reportable_but_not_scored_and_v1_is_isolated():
    assert axis_mapping(row("unknown-stable-rule")) == {}
    legacy = row("unknown-stable-rule", axisMethodologyVersion=1, ruleId="rule_legacy", sheet="Forms")
    assert axis_mapping(legacy) == {"task_execution": 1.0, "trust_accessibility": 0.5}


def test_controlled_legacy_vs_v2_attribution_comparison():
    # V1 sheet interpretation could penalize each representative defect twice;
    # v2 attributes the same logical defect once by its stable rule key.
    cases = [
        ("Content", "Content:4", "content_microcopy"),
        ("Forms", "Forms:10", "trust_accessibility"),
        ("Forms", "Forms:19", "task_execution"),
        ("Navigation", "Navigation:9", "flow_architecture"),
        ("Visual hierarchy", "visual-hierarchy-reflects-priority", "ui_consistency"),
        ("Content", "Content:16", "trust_accessibility"),
        ("Interaction", "destructive-actions-confirmed-before-execution", "task_execution"),
    ]
    for sheet, key, expected_axis in cases:
        old = axis_mapping(row(key, axisMethodologyVersion=1, ruleId="rule_legacy", sheet=sheet))
        new = axis_mapping(row(key))
        assert new == {expected_axis: 1.0}
        assert len(new) == 1
        if sheet in {"Content", "Forms", "Visual hierarchy"}:
            assert len(old) == 2


def test_logical_defect_dedupe_preserves_supplemental_evidence_without_triple_penalty():
    base = {"logicalDefectId": "button-name:#save", "target": "#save", "provenance": {"pageRefs": [{"pageId": "p1"}]}}
    merged = deduplicate_findings([
        {**base, "ruleId": "axe:button-name", "source": "axe", "measurementClass": "standards_automated"},
        {**base, "ruleId": "accessible_name", "source": "dom", "measurementClass": "deterministic_custom"},
        {**base, "ruleId": "ai_visual", "source": "vlm", "measurementClass": "ai_visual"},
    ])
    assert len(merged) == 1
    assert merged[0]["confirmationCount"] == 3
    assert merged[0]["sources"] == ["axe", "dom", "vlm"]
