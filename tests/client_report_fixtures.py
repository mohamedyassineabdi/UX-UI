"""Shared audit fixture modelled on a real GTM website audit (managers.tn)."""
import copy

_AXES = [
    ("task_execution", "Task & Interaction", 83.3, True),
    ("flow_architecture", "IA & Navigation", 44.4, True),
    ("trust_accessibility", "Accessibility", 27.3, True),
    ("visual_hierarchy", "Hierarchy & Consistency", 62.5, True),
    ("content_guidance", "Content & Guidance", None, False),
]

_MACHINE = {
    "site": {"homepage": "https://managers.tn/", "domain": "managers.tn", "display_name": "Octobre Rose: a news headline", "language": "fr-FR"},
    "methodology": [{"step": "Context", "description": "We isolate the homepage and core pages before scoring."}],
    "scannedPages": [{"page_name": "Home", "page_url": "https://managers.tn/"}, {"page_name": "Category", "page_url": "https://managers.tn/cat"}],
    "coverage": {"summary": {"completed": 2}},
    "axes": [{"id": axis_id, "name": name, "shortName": name, "score": score, "scored": scored, "summary": f"{name} summary",
              "strengths": [{"title": f"{name} strength"}], "painPoints": [{"title": f"{name} pain"}],
              "opportunities": [f"Improve {name}"]} for axis_id, name, score, scored in _AXES],
    "executiveSummary": {"overallScore": 60.2, "overallRating": "Measured", "overallReason": None, "criticalFindingCount": 0,
                         "hasCriticalBlocker": False, "positioningHook": "Managers is Tunisia's business news outlet.",
                         "strongestAxis": {"id": "task_execution", "name": "Task & Interaction"},
                         "weakestAxis": {"id": "trust_accessibility", "name": "Accessibility"},
                         "topPriorities": [{"title": "Buttons must have discernible text", "severity": "high", "axisName": "Accessibility", "recommendation": "Label icon buttons."}]},
    "recommendations": [
        {"priority": "Critical", "title": "Label icon buttons", "description": "Add accessible names.", "impact": "Major", "axis": "Accessibility"},
        {"priority": "Medium", "title": "Unify nav language", "description": "Use French labels.", "impact": "Moderate", "axis": "IA & Navigation"},
        {"priority": "Low", "title": "Trim homepage", "description": "Reduce repeated blocks.", "impact": "Minor", "axis": "Hierarchy & Consistency"},
    ],
    "deduplicatedFindings": [
        {"deduplicationId": "d1", "title": "Buttons must have discernible text", "severity": "high", "sourceSheet": "Accessibility", "pageName": "Home",
         "pageUrl": "https://managers.tn/", "evidence": "Axe button-name: 2 nodes.", "explanation": "Icon buttons have no name.",
         "whyItMatters": "Screen readers announce nothing.", "recommendation": "Add aria-label.", "measurementClass": "standards_automated",
         "evidenceBundle": {"source": "axe-core", "criterion": "4.1.2", "target": "button.icon"}},
        {"deduplicationId": "d2", "title": "Links rely on colour", "severity": "medium", "sourceSheet": "Accessibility", "pageName": "Home",
         "pageUrl": "https://managers.tn/", "evidence": "1.38:1", "explanation": "Links only differ by colour.", "whyItMatters": "Low vision.",
         "recommendation": "Underline links.", "visualRegion": {"x": 0.1, "y": 0.3, "width": 0.2, "height": 0.1}},
        {"deduplicationId": "d3", "title": "Duplicate finding", "severity": "low", "pageName": "Home", "evidence": "Dup."},
    ],
    "aiDiscoveredFindings": [
        {"title": "Blank thumbnail column", "severity": "medium", "axisName": "Hierarchy & Consistency", "pageName": "Home", "pageUrl": "https://managers.tn/",
         "evidence": "Empty thumbnails.", "whyItMatters": "Looks broken.", "recommendation": "Add images.", "aiDiscovered": True,
         "screenshotPath": "shared/audits/x/main.png", "visualRegion": {"x": 0.11, "y": 0.35, "width": 0.25, "height": 0.3, "coordinate_system": "normalized_0_1"}},
        {"title": "Mixed-language navigation", "severity": "low", "axisName": "IA & Navigation", "pageName": "Home", "evidence": "BUSINESS, ECO.",
         "recommendation": "Use one language.", "aiDiscovered": True},
    ],
}

REVISION = {"revisionId": "r" * 32, "reviewStatus": "validated", "reviewerId": "auditor-1", "changes": {
    "d1": {"reviewNote": "Confirmed on mobile too", "priorityOverride": "critical", "reviewedRecommendation": "Give every icon button an accessible name."},
    "d3": {"suppressed": True, "suppressionReason": "Duplicate of d2"},
}}


def machine():
    return copy.deepcopy(_MACHINE)
