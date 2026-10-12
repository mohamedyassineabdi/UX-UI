"""Map v2 emitted rule keys to v3 criterion ids (spec §10).

Built by walking the v2 RULE_REGISTRY: each (v2 axis, subfacet) has a default
v3 criterion, and self-describing keys or dedupe families that name a more
specific defect override it. Only score-eligible v2 rules are mapped.
"""
from __future__ import annotations

from ..rule_registry import RULE_REGISTRY

SUBFACET_CRITERIA: dict[tuple[str, str], str] = {
    ("task_execution", "task_initiation"): "usability.primary_action_clear",
    ("task_execution", "feedback"): "usability.action_feedback",
    ("task_execution", "forms"): "usability.form_requirements_upfront",
    ("task_execution", "control_behavior"): "usability.user_control_exit_undo",
    ("task_execution", "task_continuity"): "usability.user_control_exit_undo",
    ("task_execution", "runtime_responsiveness"): "performance.lcp",
    ("flow_architecture", "navigation_structure"): "navigation.nav_structure_depth",
    ("flow_architecture", "information_scent"): "navigation.nav_label_scent",
    ("trust_accessibility", "contrast"): "accessibility.text_contrast",
    ("trust_accessibility", "accessible_names"): "accessibility.names_labels",
    ("trust_accessibility", "forms_accessibility"): "accessibility.names_labels",
    ("trust_accessibility", "keyboard"): "accessibility.keyboard_operable",
    ("trust_accessibility", "semantics"): "accessibility.structure_headings_landmarks",
    ("ui_consistency", "visual_hierarchy"): "visual.visual_hierarchy",
    ("ui_consistency", "component_consistency"): "visual.component_consistency",
    ("ui_consistency", "color_state_consistency"): "visual.colour_purpose",
    ("ui_consistency", "spacing_alignment"): "visual.spacing_rhythm",
    # v3 §3 files responsive layout under performance, not visual.
    ("ui_consistency", "responsive_consistency"): "performance.responsive_no_horizontal_scroll",
    ("content_microcopy", "plain_language"): "content.plain_language",
    ("content_microcopy", "action_wording"): "content.descriptive_cta_labels",
    ("content_microcopy", "instructions"): "content.instructional_text",
    ("content_microcopy", "labels"): "content.consistent_terminology",
}

FAMILY_CRITERIA: dict[str, str] = {
    "text_alternative": "accessibility.text_alternatives",
}

KEY_CRITERIA: dict[str, str] = {
    "lcp": "performance.lcp",
    "performance": "performance.lcp",
    "fcp": "performance.first_render",
    "speed_index": "performance.first_render",
    "tbt": "performance.inp",
    "performance_runtime": "performance.inp",
    "destructive-actions-confirmed-before-execution": "usability.destructive_action_safeguard",
    "default-primary-actions-not-destructive": "usability.destructive_action_safeguard",
    "ui-responds-consistently-to-user-actions": "usability.action_feedback",
    "visual-grouping-proximity-alignment": "visual.gestalt_grouping",
    "negative-space-purpose": "visual.spacing_rhythm",
    "font-size-weight-differentiate-content-types": "visual.typographic_scale",
    "font-consistency-across-screens": "visual.typographic_scale",
    "fonts-reinforce-hierarchy": "visual.typographic_scale",
    "fonts-separate-labels-from-content": "visual.typographic_scale",
    "fonts-separate-content-from-controls": "visual.typographic_scale",
    "colors-reinforce-hierarchy": "visual.colour_purpose",
    "color-scheme-consistency": "visual.colour_purpose",
    "red-reserved-for-destructive-actions": "visual.colour_purpose",
    "primary-secondary-tertiary-controls-visually-distinct": "visual.button_hierarchy",
    "interactive-elements-not-abstracted": "visual.affordance_clarity",
}


# v2 emits axe results as "axe:<rule id>"; the registry only knows "axe:*".
# Common axe rules map to the specific criterion so they dedupe with the custom
# and AI detectors of the same defect; unlisted ones fall back to "axe:*".
AXE_CRITERIA: dict[str, str] = {
    **dict.fromkeys(["color-contrast", "color-contrast-enhanced"], "accessibility.text_contrast"),
    **dict.fromkeys(["image-alt", "role-img-alt", "input-image-alt", "svg-img-alt", "area-alt", "object-alt"], "accessibility.text_alternatives"),
    **dict.fromkeys(["label", "button-name", "link-name", "input-button-name", "select-name", "aria-input-field-name",
                     "aria-toggle-field-name", "aria-command-name", "label-title-only"], "accessibility.names_labels"),
    **dict.fromkeys(["heading-order", "page-has-heading-one", "empty-heading", "landmark-one-main", "landmark-unique",
                     "landmark-no-duplicate-main", "region", "bypass", "list", "listitem"], "accessibility.structure_headings_landmarks"),
    "target-size": "accessibility.target_size",
    "meta-viewport": "accessibility.reflow_zoom",
    **dict.fromkeys(["scrollable-region-focusable", "nested-interactive"], "accessibility.keyboard_operable"),
    "tabindex": "accessibility.focus_order",
    **dict.fromkeys(["blink", "marquee"], "accessibility.motion_control"),
    "link-in-text-block": "accessibility.non_text_contrast",
}


def _build() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for key, meta in RULE_REGISTRY.items():
        if not meta.score_eligible or meta.primary_axis is None:
            continue
        mapped = KEY_CRITERIA.get(key) or FAMILY_CRITERIA.get(meta.dedupe_family) or SUBFACET_CRITERIA.get((meta.primary_axis, meta.subfacet))
        if mapped:
            mapping[key] = mapped
    return mapping


RULE_CRITERION_MAP_V3: dict[str, str] = _build()


def criterion_for_rule(rule_key: str) -> str | None:
    """Resolve a v2 emitted key the way v2 lookup_rule does: exact, comma parts, then axe wildcard."""
    normalized = str(rule_key or "").strip()
    if normalized in RULE_CRITERION_MAP_V3:
        return RULE_CRITERION_MAP_V3[normalized]
    for candidate in normalized.split(","):
        if candidate.strip() in RULE_CRITERION_MAP_V3:
            return RULE_CRITERION_MAP_V3[candidate.strip()]
    if normalized.startswith("axe"):
        axe_rule = normalized.split(":", 1)[1].strip() if ":" in normalized else ""
        return AXE_CRITERIA.get(axe_rule) or RULE_CRITERION_MAP_V3.get("axe:*")
    return None
