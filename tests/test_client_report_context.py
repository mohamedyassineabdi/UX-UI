"""The client report context turns audit data plus review edits into presentation-ready facts."""
import copy
import json

from client_report_fixtures import REVISION, machine
from src.report.client.context import build_client_report_context


def build(data=None, revision=REVISION, **kwargs):
    return build_client_report_context(audit_id="audit-1", machine=machine() if data is None else data, revision=revision, **kwargs)


def test_kpis_count_visible_findings_and_pages():
    context = build()
    assert context["kpis"] == {"pagesAudited": 2, "findings": 4, "critical": 1, "blockers": True}
    assert context["overall"]["score"] == 60.2 and context["overall"]["rating"] == "Measured"


def test_site_name_uses_the_domain_not_the_page_title():
    assert build()["site"] == {"name": "managers.tn", "url": "https://managers.tn/"}


def test_severity_counts_apply_reviewer_priority_override():
    assert build()["severityCounts"] == {"critical": 1, "high": 0, "medium": 2, "low": 1}


def test_axis_bands_follow_score_thresholds():
    bands = {axis["name"]: axis["band"] for axis in build()["axes"]}
    assert bands == {"Task & Interaction": "green", "IA & Navigation": "red", "Accessibility": "red",
                     "Hierarchy & Consistency": "amber", "Content & Guidance": "none"}


def test_suppressed_findings_move_to_excluded_with_reason():
    context = build()
    assert "Duplicate finding" not in [f["title"] for f in context["findings"]]
    assert context["excluded"] == [{"title": "Duplicate finding", "reason": "Duplicate of d2"}]


def test_reviewer_edits_override_machine_text():
    first = build()["findings"][0]
    assert first["key"] == "d1" and first["severity"] == "critical"
    assert first["recommendation"] == "Give every icon button an accessible name."
    assert first["reviewerNote"] == "Confirmed on mobile too" and first["reviewerPriority"] == "critical"


def test_findings_sorted_by_severity_and_ai_findings_keyed():
    findings = build()["findings"]
    assert [f["severity"] for f in findings] == ["critical", "medium", "medium", "low"]
    ai = [f for f in findings if f["aiDiscovered"]]
    assert [f["key"] for f in ai] == ["ai-0", "ai-1"]
    assert ai[0]["problem"] == "Empty thumbnails." and ai[0]["whyItMatters"] == "Looks broken."


def test_ai_finding_already_in_deduplicated_list_is_not_repeated():
    data = machine()
    data["aiDiscoveredFindings"].append({"title": "Links rely on colour", "pageUrl": "https://managers.tn/", "aiDiscovered": True})
    assert [f["title"] for f in build(data)["findings"]].count("Links rely on colour") == 1


def test_roadmap_sequences_findings_by_severity():
    roadmap = build()["roadmap"]
    assert [item["title"] for item in roadmap["now"]] == ["Buttons must have discernible text"]
    assert [item["title"] for item in roadmap["next"]] == ["Links rely on colour", "Blank thumbnail column"]
    assert [item["title"] for item in roadmap["later"]] == ["Mixed-language navigation"]
    assert roadmap["now"][0]["description"] == "Give every icon button an accessible name."


def test_roadmap_lanes_are_capped():
    data = machine()
    data["aiDiscoveredFindings"] = [{"title": f"Issue {i}", "severity": "low"} for i in range(12)]
    assert len(build(data)["roadmap"]["later"]) == 5


def test_insights_take_titles_and_cap_at_four():
    insights = build()["insights"]
    assert insights["strengths"][0] == "Task & Interaction strength"
    assert all(len(items) <= 4 for items in insights.values())
    assert insights["recommendations"][0] == "Label icon buttons"


def test_top_priorities_and_strongest_weakest_axes():
    context = build()
    assert context["topPriorities"][0]["title"] == "Buttons must have discernible text"
    assert context["strongestAxis"] == "Task & Interaction" and context["weakestAxis"] == "Accessibility"


def test_review_label_and_audit_date():
    context = build(audit_date="2026-10-06")
    assert context["auditDate"] == "2026-10-06" and context["review"]["status"] == "validated"
    assert build(revision=None)["review"]["label"] == "Automated audit — not reviewed"


def test_context_is_json_serialisable_and_input_untouched():
    data = machine()
    before = copy.deepcopy(data)
    json.dumps(build(data))
    assert data == before


def test_empty_machine_still_builds():
    context = build({}, revision=None)
    assert context["overall"]["score"] is None and context["findings"] == [] and context["axes"] == []
    assert context["kpis"] == {"pagesAudited": 0, "findings": 0, "critical": 0, "blockers": False}


def test_passing_checks_are_not_findings():
    data = machine()
    data["deduplicatedFindings"].append({"deduplicationId": "ok", "title": "Has a skip link", "outcome": "pass", "severity": "high"})
    assert "Has a skip link" not in [f["title"] for f in build(data)["findings"]]


def test_same_defect_reported_twice_is_shown_once():
    data = {"findings": [{"findingId": "f5", "deduplicationId": "d1", "title": "Same", "severity": "medium"},
                         {"findingId": "f6", "deduplicationId": "d1", "title": "Same", "severity": "medium"}]}
    assert len(build(data, revision=None)["findings"]) == 1


# --- Final review fixes -------------------------------------------------------

def test_reviewer_can_suppress_and_edit_ai_findings_by_key():
    revision = {"reviewStatus": "validated", "changes": {"ai-0": {"suppressed": True, "suppressionReason": "Lazy loading, not a defect"},
                                                         "ai-1": {"priorityOverride": "high", "reviewNote": "Confirmed"}}}
    context = build(revision=revision)
    titles = [f["title"] for f in context["findings"]]
    assert "Blank thumbnail column" not in titles
    assert {"title": "Blank thumbnail column", "reason": "Lazy loading, not a defect"} in context["excluded"]
    mixed = next(f for f in context["findings"] if f["key"] == "ai-1")
    assert mixed["severity"] == "high" and mixed["reviewerNote"] == "Confirmed"


def test_suppressed_finding_is_not_re_added_from_the_ai_list():
    data = machine()
    data["aiDiscoveredFindings"].append({"title": "Duplicate finding", "pageUrl": "https://managers.tn/", "aiDiscovered": True})
    assert "Duplicate finding" not in [f["title"] for f in build(data)["findings"]]


def test_suppressed_titles_never_reach_insights():
    data = machine()
    data["axes"][2]["painPoints"].append({"title": "Duplicate finding"})
    data["recommendations"].append({"priority": "Low", "title": "Duplicate finding"})
    insights = build(data)["insights"]
    assert "Duplicate finding" not in insights["improvements"] + insights["recommendations"]


def test_top_priorities_reflect_reviewer_edits():
    first = build()["topPriorities"][0]
    assert first["title"] == "Buttons must have discernible text"
    assert first["severity"] == "critical" and first["recommendation"] == "Give every icon button an accessible name."


def test_non_finite_and_malformed_values_do_not_crash():
    data = machine()
    data["executiveSummary"]["overallScore"] = "nan"
    data["axes"][0]["score"] = float("inf")
    context = build(data)
    assert context["overall"]["score"] is None and context["axes"][0]["band"] == "none"
    broken = build({"executiveSummary": "oops", "priorities": ["x", None], "findings": ["y"]}, revision=None)
    assert broken["findings"] == [] and broken["overall"]["score"] is None


def test_findings_name_how_they_were_verified_in_plain_language():
    context = build()
    methods = {f["title"]: f["provenance"]["method"] for f in context["findings"]}
    assert methods == {"Buttons must have discernible text": "Automated accessibility test (WCAG)",
                       "Links rely on colour": "Automated checklist test on the page code",
                       "Blank thumbnail column": "AI agent review of screenshots",
                       "Mixed-language navigation": "AI agent review of screenshots"}
    first = context["findings"][0]["provenance"]
    assert first["standard"] == "WCAG 4.1.2" and first["page"] == "/"


def test_appendix_counts_findings_per_verification_method_and_lists_page_paths():
    appendix = build()["appendix"]
    assert appendix["methods"] == [{"label": "Automated accessibility test (WCAG)", "count": 1},
                                   {"label": "Automated checklist test on the page code", "count": 1},
                                   {"label": "AI agent review of screenshots", "count": 2}]
    assert [p["path"] for p in appendix["coverage"]] == ["/", "/cat"]
    assert not any("GTM" in step for step in appendix["methodology"])


def test_site_wide_findings_say_site_wide_not_the_generator_placeholder():
    data = machine()
    data["deduplicatedFindings"][1].pop("pageUrl")
    data["deduplicatedFindings"][1]["pageName"] = "the audited journey"
    pages = {f["title"]: f["provenance"]["page"] for f in build(data)["findings"]}
    assert pages["Links rely on colour"] == "Site-wide" and pages["Mixed-language navigation"] == "Home"
