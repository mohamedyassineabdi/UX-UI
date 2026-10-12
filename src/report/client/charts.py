"""Static, print-safe SVG charts. Values are always direct-labelled; colour never carries meaning alone."""
from __future__ import annotations

import html
import math
from typing import Any

# Status colours, validated with the dataviz palette checker (CVD + normal-vision separation).
SEVERITY_COLOURS = {"critical": "#9F1239", "high": "#EA580C", "medium": "#D4A20B", "low": "#3B82F6"}
BAND_COLOURS = {"red": "#DC2626", "amber": "#D4A20B", "green": "#16A34A", "none": "#CBD5E1"}
TRACK = "#E8EAF2"
INK = "#1F2430"
MUTED = "#5B6275"
SVG = 'xmlns="http://www.w3.org/2000/svg" role="img"'


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _band(score: float | None) -> str:
    return "none" if score is None else "green" if score >= 70 else "amber" if score >= 50 else "red"


def _point(cx: float, cy: float, r: float, degrees: float) -> tuple[float, float]:
    radians = math.radians(degrees)
    return cx + r * math.cos(radians), cy + r * math.sin(radians)


def _arc(cx: float, cy: float, r: float, start: float, end: float) -> str:
    x1, y1 = _point(cx, cy, r, start)
    x2, y2 = _point(cx, cy, r, end)
    large = 1 if end - start > 180 else 0
    return f"M{x1:.2f} {y1:.2f} A{r} {r} 0 {large} 1 {x2:.2f} {y2:.2f}"


def score_gauge(score: float | None, *, label: str, size: int = 180, stroke: int = 14) -> str:
    c = size / 2
    r = c - stroke / 2 - 2
    shown = "—" if score is None else str(round(score))
    aria = f"{label}: not scored" if score is None else f"{label}: {shown} out of 100"
    track = f'<path d="{_arc(c, c, r, 135, 405)}" fill="none" stroke="{TRACK}" stroke-width="{stroke}" stroke-linecap="round"/>'
    value = ""
    if score is not None and score > 0:
        end = 135 + 270 * min(score, 100) / 100
        value = f'<path d="{_arc(c, c, r, 135, end)}" fill="none" stroke="{BAND_COLOURS[_band(score)]}" stroke-width="{stroke}" stroke-linecap="round"/>'
    return (f'<svg {SVG} class="gauge" viewBox="0 0 {size} {size}" width="{size}" height="{size}" aria-label="{_esc(aria)}">{track}{value}'
            f'<text x="{c}" y="{c + 10}" text-anchor="middle" font-size="{size * 0.26:.0f}" font-weight="700" fill="{INK}">{shown}</text>'
            f'<text x="{c}" y="{c + 34}" text-anchor="middle" font-size="13" fill="{MUTED}">/ 100</text></svg>')


def axis_bars(axes: list[dict[str, Any]]) -> str:
    row, width, track_x, track_w = 46, 680, 232, 380
    rows = []
    for index, axis in enumerate(axes):
        y = index * row + 18
        name = _esc(axis.get("name") or "Axis")
        rows.append(f'<text x="0" y="{y + 5}" font-size="14" font-weight="600" fill="{INK}">{name}</text>'
                    f'<rect x="{track_x}" y="{y - 5}" width="{track_w}" height="12" rx="6" fill="{TRACK}"/>')
        score = axis.get("score")
        if axis.get("scored") and score is not None:
            fill = max(12.0, track_w * min(float(score), 100) / 100)
            rows.append(f'<rect x="{track_x}" y="{y - 5}" width="{fill:.1f}" height="12" rx="6" fill="{BAND_COLOURS[axis.get("band") or _band(score)]}"/>'
                        f'<text x="{width}" y="{y + 5}" text-anchor="end" font-size="14" font-weight="700" fill="{INK}">{round(float(score))}</text>')
        else:
            rows.append(f'<text x="{width}" y="{y + 5}" text-anchor="end" font-size="13" fill="{MUTED}">Not scored</text>')
    height = max(row, len(axes) * row)
    label = "Score by audit area, out of 100"
    return f'<svg {SVG} class="axis-bars" viewBox="0 0 {width} {height}" width="100%" aria-label="{label}">{"".join(rows)}</svg>'


def severity_donut(counts: dict[str, int], *, size: int = 180) -> str:
    stroke, c = 24, size / 2
    r = c - stroke / 2 - 2
    values = [(severity, int(counts.get(severity) or 0)) for severity in SEVERITY_COLOURS]
    total = sum(value for _, value in values)
    present = [(severity, value) for severity, value in values if value > 0]
    parts = [f'<circle cx="{c}" cy="{c}" r="{r}" fill="none" stroke="{TRACK}" stroke-width="{stroke}"/>']
    if len(present) == 1:
        parts.append(f'<circle cx="{c}" cy="{c}" r="{r}" fill="none" stroke="{SEVERITY_COLOURS[present[0][0]]}" stroke-width="{stroke}"/>')
    elif present:
        gap, start = 1.6, -90.0
        for severity, value in present:
            sweep = 360 * value / total
            parts.append(f'<path d="{_arc(c, c, r, start + gap, start + sweep - gap)}" fill="none" stroke="{SEVERITY_COLOURS[severity]}" stroke-width="{stroke}"/>')
            start += sweep
    summary = ", ".join(f"{value} {severity}" for severity, value in values)
    return (f'<svg {SVG} class="donut" viewBox="0 0 {size} {size}" width="{size}" height="{size}" aria-label="{_esc(f"{total} findings: {summary}")}">{"".join(parts)}'
            f'<text x="{c}" y="{c + 8}" text-anchor="middle" font-size="34" font-weight="700" fill="{INK}">{total}</text>'
            f'<text x="{c}" y="{c + 30}" text-anchor="middle" font-size="13" fill="{MUTED}">findings</text></svg>')
