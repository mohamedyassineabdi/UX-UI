from __future__ import annotations

import io

import pytest
from PIL import Image

from src.ui import server


def image_bytes(format_name="PNG", size=(4, 4)):
    output = io.BytesIO()
    Image.new("RGB", size, "red").save(output, format=format_name)
    return output.getvalue()


def form_with(*items):
    return server.MultipartForm(files={"screenshots": list(items)})


def test_valid_upload_uses_server_filename(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "SCREENSHOT_AUDIT_DIR", tmp_path)
    item = server.UploadedFile(filename="../../confusing.exe.png", data=image_bytes(), content_type="image/png")
    paths = server._save_screenshot_uploads(form_with(item), "a" * 12, ["ignored"])
    assert len(paths) == 1
    assert "confusing" not in paths[0].name
    assert paths[0].suffix == ".png"


@pytest.mark.parametrize(
    "item",
    [
        server.UploadedFile(filename="x.png", data=b"not an image", content_type="image/png"),
        server.UploadedFile(filename="x.jpg", data=image_bytes(), content_type="image/jpeg"),
    ],
)
def test_malformed_or_mime_confused_upload_is_rejected_and_cleaned(monkeypatch, tmp_path, item):
    monkeypatch.setattr(server, "SCREENSHOT_AUDIT_DIR", tmp_path)
    job_id = "b" * 12
    with pytest.raises(ValueError):
        server._save_screenshot_uploads(form_with(item), job_id, [])
    assert not (tmp_path / job_id / "uploads").exists()


def test_count_size_dimensions_and_animation_limits(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "SCREENSHOT_AUDIT_DIR", tmp_path)
    valid = server.UploadedFile("x.png", image_bytes(), "image/png")
    monkeypatch.setattr(server, "MAX_UPLOAD_COUNT", 1)
    with pytest.raises(ValueError):
        server._save_screenshot_uploads(form_with(valid, valid), "c" * 12, [])
    monkeypatch.setattr(server, "MAX_UPLOAD_BYTES", 2)
    with pytest.raises(ValueError):
        server._save_screenshot_uploads(form_with(valid), "d" * 12, [])
    monkeypatch.setattr(server, "MAX_UPLOAD_BYTES", 1_000_000)
    monkeypatch.setattr(server, "MAX_IMAGE_DIMENSION", 2)
    with pytest.raises(ValueError):
        server._save_screenshot_uploads(form_with(valid), "e" * 12, [])

    output = io.BytesIO()
    first = Image.new("RGB", (2, 2), "red")
    second = Image.new("RGB", (2, 2), "blue")
    first.save(output, format="WEBP", save_all=True, append_images=[second], duration=10, loop=0)
    animated = server.UploadedFile("x.webp", output.getvalue(), "image/webp")
    monkeypatch.setattr(server, "MAX_IMAGE_DIMENSION", 100)
    with pytest.raises(ValueError):
        server._save_screenshot_uploads(form_with(animated), "f" * 12, [])

