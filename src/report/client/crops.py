"""Crop a finding's screenshot to the affected section and highlight it. No precise region → no image."""
from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any

from src.gtm_audit.generate_gtm_report import ROOT_DIR, _draw_red_highlight, _is_precise_region, _region_to_pixels, _visual_region_from_item

MIN_CROP = (640, 360)
PADDING = 0.6  # extra context around the region, as a fraction of its size


def _resolve(raw: Any, root: Path) -> Path | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    root = root.resolve()
    source = Path(raw)
    candidate = source if source.is_absolute() else root / source
    if candidate.is_symlink():
        return None
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root) or not resolved.is_file():
        return None
    return resolved


def _crop_box(width: int, height: int, x: float, y: float, w: float, h: float) -> tuple[int, int, int, int]:
    crop_w = min(width, max(w * (1 + 2 * PADDING), MIN_CROP[0]))
    wanted_h = max(h * (1 + 2 * PADDING), MIN_CROP[1], crop_w * 9 / 16)
    crop_h = min(height, wanted_h, crop_w)  # never taller than wide: a section, not a scroll
    left = max(0.0, min(x + w / 2 - crop_w / 2, width - crop_w))
    # A region taller than the crop is shown from its start, where the issue begins.
    target = y - MIN_CROP[1] * 0.15 if wanted_h > crop_w else y + h / 2 - crop_h / 2
    top = max(0.0, min(target, height - crop_h))
    return int(left), int(top), int(left + crop_w), int(top + crop_h)


def crop_evidence(finding: dict[str, Any], *, root: Path = ROOT_DIR, max_width: int = 1100) -> str | None:
    try:
        from PIL import Image, ImageDraw

        path = _resolve(finding.get("screenshotPath"), Path(root))
        if path is None:
            return None
        with Image.open(path) as source:
            image = source.convert("RGB")
        region = _visual_region_from_item(finding)
        if not _is_precise_region(finding, region, image.width, image.height):
            return None
        x, y, w, h = _region_to_pixels(region, image.width, image.height)
        left, top, right, bottom = _crop_box(image.width, image.height, x, y, w, h)
        image = image.crop((left, top, right, bottom))
        scale = min(1.0, max_width / image.width)
        if scale < 1.0:
            image = image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.LANCZOS)
        halo = 14
        bounds = ((x - left) * scale - halo, (y - top) * scale - halo, (x - left + w) * scale + halo, (y - top + h) * scale + halo)
        _draw_red_highlight(ImageDraw.Draw(image, "RGBA"), bounds, image.width, image.height, broad=True)
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=82, optimize=True)
        return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
    except Exception:
        return None


def crop_all(findings: list[dict[str, Any]], *, root: Path = ROOT_DIR) -> dict[str, str]:
    crops = {}
    for finding in findings:
        uri = crop_evidence(finding, root=root) if isinstance(finding, dict) else None
        if uri:
            crops[str(finding.get("key"))] = uri
    return crops
