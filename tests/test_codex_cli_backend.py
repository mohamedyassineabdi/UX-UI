"""Contract tests for the optional read-only Codex subprocess adapter."""
from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.audit.codex_cli_backend import run_codex_cli_json
from src.audit.ai_review_client import load_ai_review_config
from src.gtm_audit import vision_client


def test_backend_is_opt_in(monkeypatch):
    monkeypatch.delenv("AI_REVIEW_BACKEND", raising=False)
    monkeypatch.delenv("GTM_VISION_BACKEND", raising=False)
    assert vision_client.vision_backend() == "ollama"
    monkeypatch.setenv("AI_REVIEW_BACKEND", "codex_cli")
    monkeypatch.setenv("GTM_VISION_BACKEND", "codex_cli")
    assert load_ai_review_config().backend == "codex_cli"
    assert vision_client.vision_backend() == "codex_cli"


def test_cli_missing(monkeypatch):
    monkeypatch.delenv("GTM_CODEX_CLI", raising=False)
    with patch("src.audit.codex_cli_backend.shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="not found"):
            run_codex_cli_json(prompt="{}", timeout=10)


def test_cli_read_only_ephemeral_and_no_shell(monkeypatch, tmp_path):
    monkeypatch.setenv("GTM_CODEX_CLI", "codex")
    screenshot = tmp_path / "example.png"
    screenshot.write_bytes(b"PNG test fixture")
    def fake_run(command, **kwargs):
        assert command[:2] == ["codex", "exec"]
        assert command[command.index("--sandbox") + 1] == "read-only"
        assert "--ephemeral" in command
        assert "--ignore-user-config" in command
        assert "--ignore-rules" in command
        assert "--skip-git-repo-check" in command
        assert command[command.index("--image") + 1] == str(screenshot.resolve())
        assert command[-1] == "-"
        assert kwargs["input"] == "{}"
        assert kwargs["cwd"] != str(tmp_path)
        assert kwargs.get("shell", False) is False
        Path(command[command.index("--output-last-message") + 1]).write_text('{"pass": true}', encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")
    with patch("src.audit.codex_cli_backend.subprocess.run", side_effect=fake_run):
        assert run_codex_cli_json(prompt="{}", timeout=10, image_paths=[screenshot]) == '{"pass": true}'


def test_cli_timeout(monkeypatch):
    monkeypatch.setenv("GTM_CODEX_CLI", "codex")
    with patch("src.audit.codex_cli_backend.subprocess.run", side_effect=subprocess.TimeoutExpired("codex", 1)):
        with pytest.raises(RuntimeError, match="timed out"):
            run_codex_cli_json(prompt="{}", timeout=1)


def test_cli_auth_failure_is_not_exposed(monkeypatch):
    monkeypatch.setenv("GTM_CODEX_CLI", "codex")
    with patch("src.audit.codex_cli_backend.subprocess.run", return_value=SimpleNamespace(returncode=1, stdout="secret", stderr="secret")):
        with pytest.raises(RuntimeError) as exc:
            run_codex_cli_json(prompt="{}", timeout=1)
        assert "secret" not in str(exc.value)


def test_cli_does_not_accept_non_image(monkeypatch, tmp_path):
    monkeypatch.setenv("GTM_CODEX_CLI", "codex")
    bad_file = tmp_path / "sensitive.txt"
    bad_file.write_text("secret")
    with pytest.raises(ValueError, match="image files"):
        run_codex_cli_json(prompt="{}", timeout=1, image_paths=[bad_file])


def test_vision_routes_to_codex_without_ollama(monkeypatch, tmp_path):
    monkeypatch.setenv("GTM_VISION_BACKEND", "codex_cli")
    path = tmp_path / "example.png"
    path.write_bytes(b"fixture")
    with patch("src.gtm_audit.vision_client.run_codex_cli_json", return_value='{"success":true}') as stub:
        with patch("src.gtm_audit.vision_client.requests.post", side_effect=AssertionError("unexpected Ollama HTTP request")):
            result = vision_client._chat_json_with_images(prompt="Review", image_paths=[path], timeout=12)
    assert result["content"] == '{"success":true}'
    assert result["model"] == "codex-cli"
    assert stub.call_args.kwargs["image_paths"] == [path]
