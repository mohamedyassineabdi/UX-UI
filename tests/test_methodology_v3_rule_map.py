import pytest

from src.gtm_audit.methodology_v3.config import load_methodology
from src.gtm_audit.methodology_v3.rule_map import RULE_CRITERION_MAP_V3, criterion_for_rule
from src.gtm_audit.rule_registry import RULE_REGISTRY

# Spec §10, plus ui_consistency's responsive rules, which v3 §3 files under performance.
V2_TO_V3_AXES = {
    "task_execution": {"usability", "performance"},
    "flow_architecture": {"navigation"},
    "trust_accessibility": {"accessibility", "trust"},
    "ui_consistency": {"visual", "performance"},
    "content_microcopy": {"content"},
}
ELIGIBLE = sorted(key for key, meta in RULE_REGISTRY.items() if meta.score_eligible)


@pytest.fixture(scope="module")
def methodology():
    return load_methodology()


@pytest.mark.parametrize("key", ELIGIBLE)
def test_every_eligible_v2_rule_maps_to_an_existing_criterion(methodology, key):
    criterion_id = criterion_for_rule(key)
    assert criterion_id is not None and methodology.criterion(criterion_id) is not None


@pytest.mark.parametrize("key", ELIGIBLE)
def test_mapped_axis_is_consistent_with_v2_axis(key):
    v3_axis = criterion_for_rule(key).split(".", 1)[0]
    assert v3_axis in V2_TO_V3_AXES[RULE_REGISTRY[key].primary_axis]


def test_only_responsive_ui_rules_move_to_performance():
    moved = {key for key in ELIGIBLE if RULE_REGISTRY[key].primary_axis == "ui_consistency" and criterion_for_rule(key).startswith("performance.")}
    assert moved and all(RULE_REGISTRY[key].subfacet == "responsive_consistency" for key in moved)


@pytest.mark.parametrize("key, expected", [
    ("Content:16", "accessibility.text_contrast"),
    ("lcp", "performance.lcp"),
    ("no-horizontal-scrolling", "performance.responsive_no_horizontal_scroll"),
    ("destructive-actions-confirmed-before-execution", "usability.destructive_action_safeguard"),
    ("keyboard_focus", "accessibility.keyboard_operable"),
])
def test_spot_checks(key, expected):
    assert criterion_for_rule(key) == expected


def test_navigation_rule_maps_to_navigation():
    assert criterion_for_rule("Navigation:9").startswith("navigation.")


@pytest.mark.parametrize("key", ["Nope:1", "", "vlm"])
def test_unknown_or_unscored_key_is_none(key):
    assert criterion_for_rule(key) is None


def test_aggregated_keys_resolve_through_their_parts():
    assert criterion_for_rule("Unknown:1, Content:16") == "accessibility.text_contrast"


@pytest.mark.parametrize("key, expected", [
    ("axe:color-contrast", "accessibility.text_contrast"),
    ("axe:image-alt", "accessibility.text_alternatives"),
    ("axe:button-name", "accessibility.names_labels"),
    ("axe:label", "accessibility.names_labels"),
    ("axe:heading-order", "accessibility.structure_headings_landmarks"),
    ("axe:target-size", "accessibility.target_size"),
])
def test_axe_rules_map_to_their_specific_criterion(key, expected):
    assert criterion_for_rule(key) == expected


def test_unlisted_axe_rules_fall_back_to_the_axe_wildcard():
    assert criterion_for_rule("axe:aria-allowed-attr") == RULE_CRITERION_MAP_V3["axe:*"]


def test_map_only_names_real_criteria(methodology):
    assert all(methodology.criterion(value) is not None for value in RULE_CRITERION_MAP_V3.values())
