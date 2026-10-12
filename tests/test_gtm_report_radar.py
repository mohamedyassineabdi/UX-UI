from src.gtm_audit.generate_gtm_report import render_radar_chart


def test_radar_chart_renders_unscored_axes_without_crashing():
    axes = [
        {"id": "task_execution", "name": "Task", "score": 80},
        {"id": "trust_accessibility", "name": "Accessibility", "score": None, "scored": False},
        {"id": "ui_consistency", "name": "Visual", "score": "65"},
    ]
    svg = render_radar_chart(axes)
    assert "<svg" in svg
    assert svg.count("not scored") == 1
