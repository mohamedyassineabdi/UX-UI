"""Methodology-v2 rule attribution and score-eligibility registry.

The registry deliberately uses stable emitted keys (``Sheet:row`` and partner
``machine_criterion`` IDs), never criterion prose.  A record has one primary
axis; tags are descriptive only and never create another score consequence.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


AXIS_IDS = ("task_execution", "flow_architecture", "trust_accessibility", "ui_consistency", "content_microcopy")
MODES = ("website", "screenshot", "mobile", "figma")


@dataclass(frozen=True)
class RuleMetadata:
    primary_axis: str | None
    subfacet: str
    score_eligible: bool
    tier: str
    evidence_grade: str
    applicable_modes: tuple[str, ...]
    secondary_tags: tuple[str, ...] = ()
    dedupe_family: str = ""


def _record(axis: str | None, subfacet: str, *, grade: str = "C", score: bool = True,
            tier: str = "supporting", modes: tuple[str, ...] = ("website",),
            tags: tuple[str, ...] = (), family: str = "") -> RuleMetadata:
    return RuleMetadata(axis, subfacet, score and grade in {"A", "B", "C"}, tier, grade, modes, tags, family)


RULE_REGISTRY: dict[str, RuleMetadata] = {}


def _add(keys: Iterable[str], axis: str | None, subfacet: str, **kwargs: object) -> None:
    for key in keys:
        RULE_REGISTRY[key] = _record(axis, subfacet, **kwargs)


# Direct workbook runners.  Rows with subjective, proxy-only, or unavailable
# evidence remain reportable but are deliberately absent from numeric scoring.
_add([f"Content:{row}" for row in (4, 5, 6, 9, 10, 12, 15, 20, 21, 22)], "content_microcopy", "plain_language", tags=("content_clarity",))
_add(["Content:16"], "trust_accessibility", "contrast", grade="B", tier="core", tags=("accessibility",), family="contrast")
_add(["Content:24"], "trust_accessibility", "semantics", grade="B", tier="core", tags=("accessibility",), family="text_alternative")
_add(["Content:25"], "trust_accessibility", "semantics", score=False, tags=("accessibility",), family="text_alternative")
_add([f"Content:{row}" for row in (7, 8, 11, 13, 14, 17, 18, 19, 23)], None, "human_or_proxy", grade="D", score=False)

_add([f"Labeling:{row}" for row in (4, 5, 6, 7, 12, 24)], "content_microcopy", "labels", tags=("content_clarity",))
_add([f"Labeling:{row}" for row in (10, 11, 14, 15, 16)], "flow_architecture", "information_scent", tags=("navigation",))
_add([f"Labeling:{row}" for row in (8, 21, 25, 26)], "ui_consistency", "visual_hierarchy", tags=("visual_hierarchy",))
_add(["Labeling:18", "Labeling:19", "Labeling:22"], "trust_accessibility", "forms_accessibility", grade="B", tags=("forms", "accessibility"))

_add([f"Navigation:{row}" for row in (4, 5, 6, 7, 9, 10, 11, 13, 16, 17, 18, 19)], "flow_architecture", "navigation_structure", tags=("navigation",))
_add(["Navigation:8"], "content_microcopy", "labels", tags=("navigation",))
_add([f"Navigation:{row}" for row in (14, 15)], "task_execution", "control_behavior", tags=("search",))
_add([f"Navigation:{row}" for row in (21, 22, 23, 24, 25, 28)], "task_execution", "task_continuity", tags=("workflow",))
_add(["Navigation:26"], "content_microcopy", "instructions", tags=("task_guidance",))
_add(["Navigation:27"], "ui_consistency", "component_consistency", tags=("component_consistency",))

_add([f"Forms:{row}" for row in (4, 5, 6, 7, 12, 14, 18, 19, 20, 25)], "task_execution", "forms", tags=("forms",))
_add(["Forms:9", "Forms:10", "Forms:11", "Forms:13", "Forms:16", "Forms:17"], "trust_accessibility", "forms_accessibility", grade="B", tags=("forms", "accessibility"))
_add(["Forms:22", "Forms:23", "Forms:24"], "trust_accessibility", "semantics", grade="B", tags=("accessibility",))

_add([f"Feedback:{row}" for row in (4, 5, 8, 9, 10, 12, 19, 22, 24, 25, 26)], "task_execution", "feedback", tags=("feedback", "error_recovery"))
_add(["Feedback:6", "Feedback:7"], "ui_consistency", "color_state_consistency", tags=("feedback",))
_add(["Feedback:13", "Feedback:14", "Feedback:15", "Feedback:18", "Feedback:21"], "content_microcopy", "instructions", tags=("content_clarity",))
_add(["Feedback:17"], "trust_accessibility", "status_accessibility", score=False, tags=("accessibility", "forms"))
_add(["Feedback:23"], None, "trust_credibility", grade="D", score=False, tags=("contactability",))

# Partner-generated stable criterion IDs.
_add(["tested-viewport-support", "no-horizontal-scrolling", "layout-consistency", "responsive-desktop-mobile"], "ui_consistency", "responsive_consistency", tags=("responsive",))
_add(["negative-space-scanning"], "ui_consistency", "spacing_alignment", tags=("visual_hierarchy",))
_add(["information-order-expectation"], "flow_architecture", "taxonomy_grouping", score=False, grade="D", tags=("information_architecture",))
_add(["modal-focus-appropriateness", "no-distracting-animation", "no-distracting-animation-runtime"], "trust_accessibility", "focus_management", score=False, grade="D", tags=("accessibility", "motion"))
_add(["visual-style-consistency"], "ui_consistency", "component_consistency", tags=("component_consistency",))
_add(["visual-metaphor-clarity"], None, "human_review", score=False, grade="D")

_add(["cta-clearly-labeled-and-clickable", "verbs-used-for-actions", "interactive-labeling-familiar-not-system-oriented", "controls-provide-hints-help-tooltips-where-applicable"], "content_microcopy", "action_wording", tags=("interaction",))
_add(["users-have-control-over-interactive-workflows", "ui-responds-consistently-to-user-actions", "frequently-used-features-readily-available", "default-primary-actions-not-destructive", "destructive-actions-confirmed-before-execution", "standard-browser-functions-supported", "editable-droplists-where-applicable", "secondary-actions-displayed-as-links"], "task_execution", "control_behavior", tags=("interaction", "user_control"))
_add(["red-reserved-for-destructive-actions", "controls-placed-consistently", "controls-related-to-surrounding-information", "interactive-elements-not-abstracted", "primary-secondary-tertiary-controls-visually-distinct"], "ui_consistency", "component_consistency", tags=("interaction", "visual_hierarchy"))

_add(["information-order-importance", "visual-hierarchy-reflects-priority", "visual-grouping-proximity-alignment", "negative-space-purpose", "similar-information-consistency", "colors-reinforce-hierarchy", "color-scheme-consistency", "most-important-items-have-most-contrast", "contrast-primary-mechanism-for-hierarchy", "contrast-separates-content-from-controls", "contrast-separates-labels-from-content", "foreground-distinguished-from-background", "font-size-weight-differentiate-content-types", "font-consistency-across-screens", "fonts-reinforce-hierarchy", "fonts-separate-labels-from-content", "fonts-separate-content-from-controls"], "ui_consistency", "visual_hierarchy", modes=("website", "screenshot", "figma"), tags=("visual_hierarchy",))
_add(["required-action-direction", "cta-primary-visual-element"], "task_execution", "task_initiation", tags=("visual_hierarchy",))
_add(["ui-uses-no-more-than-3-primary-colors", "chrome-desaturated-colors", "no-oversaturated-colors", "no-more-than-two-font-families", "content-fonts-at-least-12px"], "ui_consistency", "typography_consistency", score=False, grade="D", tags=("visual_hierarchy",))

# Non-sheet stable families used by callers/tests.  They are intentionally
# mode-limited so static audit modes cannot claim runtime/DOM evidence.
_add(["axe", "axe:*"], "trust_accessibility", "semantics", grade="A", tier="core", tags=("accessibility",), family="accessibility")
_add(["accessible_name"], "trust_accessibility", "accessible_names", grade="A", tier="core", tags=("accessibility",), family="accessibility")
_add(["keyboard_focus"], "trust_accessibility", "keyboard", grade="B", tier="core", tags=("accessibility",), family="accessibility")
_add(["performance_runtime", "lcp", "fcp", "tbt", "speed_index"], "task_execution", "runtime_responsiveness", grade="B", tier="core", tags=("performance",), family="performance")
_add(["lighthouse_category"], None, "performance_category", grade="B", score=False, tags=("performance",), family="performance")
_add(["vlm", "ai_visual"], None, "ai_interpretation", grade="E", score=False, tags=("ai_visual",))


def lookup_rule(key: str) -> RuleMetadata | None:
    normalized = str(key or "").strip()
    if normalized in RULE_REGISTRY:
        return RULE_REGISTRY[normalized]
    # A few partner rows intentionally aggregate equivalent deterministic and
    # runtime criterion IDs. They share one registry record and score effect.
    for candidate in normalized.split(","):
        candidate = candidate.strip()
        if candidate in RULE_REGISTRY:
            return RULE_REGISTRY[candidate]
    if normalized.startswith("axe"):
        return RULE_REGISTRY["axe:*"]
    return None
