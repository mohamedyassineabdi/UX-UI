"""Finding screenshots are cropped to the affected section; never the whole page."""
import base64
import io

from PIL import Image

from src.report.client.crops import crop_all, crop_evidence

REGION = {"x": 0.1, "y": 0.35, "width": 0.25, "height": 0.1, "coordinate_system": "normalized_0_1", "description": "Blank thumbnail column"}


def page(tmp_path, name="main.png", size=(1440, 3000)):
    path = tmp_path / "shots" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, "white").save(path)
    return path


def decode(uri):
    assert uri.startswith("data:image/jpeg;base64,")
    return Image.open(io.BytesIO(base64.b64decode(uri.split(",", 1)[1])))


def test_region_crop_is_a_section_not_the_full_page(tmp_path):
    path = page(tmp_path)
    image = decode(crop_evidence({"screenshotPath": str(path), "visualRegion": REGION}, root=tmp_path))
    assert image.width <= 1100 and image.height < 1500
    assert image.width / image.height < 3  # a readable section, not a sliver


def test_relative_paths_resolve_against_root(tmp_path):
    page(tmp_path)
    assert crop_evidence({"screenshotPath": "shots/main.png", "visualRegion": REGION}, root=tmp_path)


def test_region_from_evidence_bundle_rect_is_used(tmp_path):
    path = page(tmp_path)
    finding = {"screenshotPath": str(path), "title": "Link text", "evidenceBundle": {"target": {"rect": REGION}}}
    assert crop_evidence(finding, root=tmp_path)


def test_no_region_means_no_image(tmp_path):
    assert crop_evidence({"screenshotPath": str(page(tmp_path))}, root=tmp_path) is None


def test_full_page_region_means_no_image(tmp_path):
    region = {"x": 0, "y": 0, "width": 1, "height": 1, "description": "full page"}
    assert crop_evidence({"screenshotPath": str(page(tmp_path)), "visualRegion": region}, root=tmp_path) is None


def test_missing_file_means_no_image(tmp_path):
    assert crop_evidence({"screenshotPath": str(tmp_path / "nope.png"), "visualRegion": REGION}, root=tmp_path) is None


def test_path_outside_root_is_refused(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    outside = page(tmp_path)
    assert crop_evidence({"screenshotPath": str(outside), "visualRegion": REGION}, root=root) is None
    assert crop_evidence({"screenshotPath": "../shots/main.png", "visualRegion": REGION}, root=root) is None


def test_non_image_file_means_no_image(tmp_path):
    path = tmp_path / "fake.png"
    path.write_text("not an image", encoding="utf-8")
    assert crop_evidence({"screenshotPath": str(path), "visualRegion": REGION}, root=tmp_path) is None


def test_crop_all_keys_only_findings_with_crops(tmp_path):
    path = page(tmp_path)
    crops = crop_all([{"key": "a", "screenshotPath": str(path), "visualRegion": REGION}, {"key": "b", "screenshotPath": str(path)}], root=tmp_path)
    assert list(crops) == ["a"]


def test_tall_region_is_capped_to_a_presentable_shape(tmp_path):
    path = page(tmp_path, size=(1440, 15000))
    tall = {"x": 0.11, "y": 0.35, "width": 0.25, "height": 0.3, "coordinate_system": "normalized_0_1", "description": "Blank thumbnail column"}
    image = decode(crop_evidence({"screenshotPath": str(path), "visualRegion": tall}, root=tmp_path))
    assert image.height <= image.width
