import json
from pathlib import Path

from figma_audit.criteria_catalog import load_criteria_catalog
from src.gtm_audit import common
from src.gtm_audit.generate_gtm_report import AXIS_LABELS
from src.gtm_audit.scoring import AXIS_IDS, RULE_AXIS_MAP, SHEET_AXIS_MAP


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "shared" / "config" / "audit_axes.json"
IDS = (
    "task_execution",
    "flow_architecture",
    "trust_accessibility",
    "ui_consistency",
    "content_microcopy",
)
NAMES = (
    "Task Effectiveness & Interaction",
    "Information Architecture & Navigation",
    "Accessibility",
    "Visual Hierarchy & Interface Consistency",
    "Content Clarity & Guidance",
)


def test_v2_config_keeps_stable_ids_and_updates_display_metadata():
    payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    assert payload["version"] == 2
    assert tuple(axis["id"] for axis in payload["axes"]) == IDS
    assert tuple(axis["name"] for axis in payload["axes"]) == NAMES
    assert payload["axes"][2]["short_name"] == "Accessibility"
    assert "trust" not in payload["axes"][2]["description"].lower()
    assert "buyer journey" not in payload["axes"][1]["description"].lower()
    assert "conversion" not in payload["axes"][0]["description"].lower()
    assert "field Core Web Vitals" not in " ".join(payload["axes"][0]["look_for"])


def test_v2_fallback_and_figma_overlay_match_current_axis_meanings():
    fallback = common.default_audit_criteria_payload()
    assert fallback["version"] == 2
    assert tuple(axis["id"] for axis in fallback["axes"]) == IDS
    assert tuple(axis["name"] for axis in fallback["axes"]) == NAMES
    assert "trust" not in fallback["axes"][2]["description"].lower()
    catalog = load_criteria_catalog()
    assert tuple(criterion.id for criterion in catalog.criteria[:5]) == IDS
    assert tuple(criterion.name for criterion in catalog.criteria[:5]) == NAMES


def test_active_report_labels_and_scoring_registry_are_unchanged():
    assert tuple(AXIS_IDS) == IDS
    assert tuple(AXIS_LABELS[axis_id] for axis_id in IDS) == NAMES
    assert SHEET_AXIS_MAP == {
        "Content": {"content_microcopy": 1.0, "trust_accessibility": 0.5},
        "Labeling": {"content_microcopy": 1.0, "task_execution": 0.5},
        "Navigation": {"flow_architecture": 1.0},
        "Feedback": {"task_execution": 1.0},
        "Forms": {"task_execution": 1.0, "trust_accessibility": 0.5},
        "Interaction": {"task_execution": 1.0},
        "Presentation": {"ui_consistency": 1.0},
        "Visual hierarchy": {"ui_consistency": 1.0, "content_microcopy": 0.5},
    }
    assert RULE_AXIS_MAP
    assert all(len(mapping) == 1 for mapping in RULE_AXIS_MAP.values())
