"""Client report charts are static, print-safe SVG with labels that never rely on colour alone."""
import xml.etree.ElementTree as ET

from src.report.client.charts import BAND_COLOURS, SEVERITY_COLOURS, axis_bars, score_gauge, severity_donut

AXES = [{"name": "Accessibility", "score": 27.3, "scored": True, "band": "red"},
        {"name": "<b>Content</b>", "score": None, "scored": False, "band": "none"}]


def parses(svg):
    ET.fromstring(svg)
    return svg


def test_gauge_shows_rounded_score_in_band_colour():
    svg = parses(score_gauge(60.2, label="Overall UX score"))
    assert ">60<" in svg and BAND_COLOURS["amber"] in svg and 'aria-label="Overall UX score: 60 out of 100"' in svg


def test_gauge_without_score_shows_dash():
    svg = parses(score_gauge(None, label="Overall UX score"))
    assert "—" in svg and "not scored" in svg


def test_axis_bars_label_values_and_unscored_axes():
    svg = parses(axis_bars(AXES))
    assert ">27<" in svg and "Not scored" in svg and "&lt;b&gt;Content&lt;/b&gt;" in svg and BAND_COLOURS["red"] in svg


def test_donut_draws_only_non_zero_segments_with_total():
    svg = parses(severity_donut({"critical": 0, "high": 4, "medium": 8, "low": 5}))
    assert ">17<" in svg
    assert svg.count("<path") == 3 and SEVERITY_COLOURS["critical"] not in svg


def test_donut_with_no_findings_does_not_divide_by_zero():
    svg = parses(severity_donut({"critical": 0, "high": 0, "medium": 0, "low": 0}))
    assert ">0<" in svg and "<path" not in svg


def test_single_severity_donut_is_a_full_ring():
    svg = parses(severity_donut({"critical": 3, "high": 0, "medium": 0, "low": 0}))
    assert ">3<" in svg and SEVERITY_COLOURS["critical"] in svg


def test_charts_have_no_scripts_or_external_references():
    for svg in (score_gauge(80, label="x"), axis_bars(AXES), severity_donut({"high": 1})):
        assert "<script" not in svg and "http" not in svg.replace("http://www.w3.org/2000/svg", "")
