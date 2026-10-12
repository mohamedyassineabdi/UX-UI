"""Vision review through the signed-in `claude` CLI instead of an API key."""
import json
import subprocess
import threading

import pytest

from src.gtm_audit import vision_client
from src.ui import server


def _cli_reply(result="{}", *, is_error=False, subtype="success"):
    return json.dumps({"type": "result", "subtype": subtype, "is_error": is_error, "result": result})


@pytest.fixture
def fake_cli(monkeypatch, tmp_path):
    calls = []
    reply = {"stdout": _cli_reply('{"ok": true}'), "returncode": 0, "raise": None}

    def run(command, **kwargs):
        calls.append({"command": list(command), **kwargs})
        if reply["raise"]:
            raise reply["raise"]
        return subprocess.CompletedProcess(command, reply["returncode"], stdout=reply["stdout"], stderr="")

    monkeypatch.setenv("GTM_VISION_BACKEND", "claude_cli")
    monkeypatch.setattr(vision_client, "_claude_binary", lambda: "claude")
    monkeypatch.setattr(vision_client.subprocess, "run", run)
    image = tmp_path / "shots" / "home.png"
    image.parent.mkdir()
    image.write_bytes(b"png")
    return calls, reply, image


def test_backend_defaults_to_ollama(monkeypatch):
    monkeypatch.delenv("GTM_VISION_BACKEND", raising=False)
    assert vision_client.vision_backend() == "ollama"


def test_claude_cli_returns_the_reply_text(fake_cli):
    calls, reply, image = fake_cli
    reply["stdout"] = _cli_reply('```json\n{"axes": []}\n```')
    out = vision_client._chat_json_with_images(prompt="Review", image_paths=[image], timeout=30)
    assert out == {"model": "claude-cli", "content": '{"axes": []}'}


def test_claude_cli_is_read_only_and_prompt_goes_through_stdin(fake_cli):
    calls, _, image = fake_cli
    vision_client._chat_json_with_images(prompt="Review these", image_paths=[image], timeout=30)
    command, call = calls[0]["command"], calls[0]
    assert command[:2] == ["claude", "-p"]
    assert command[command.index("--tools") + 1] == "Read"
    assert "--strict-mcp-config" in command and "--no-session-persistence" in command
    assert command[command.index("--add-dir") + 1] == str(image.parent)
    assert "Review these" in call["input"] and str(image) in call["input"]
    assert "Review these" not in " ".join(command)
    assert call["timeout"] == 30


@pytest.mark.parametrize("stdout, returncode", [
    (_cli_reply("Not logged in", is_error=True), 1),
    (_cli_reply("", subtype="error_max_turns"), 0),
    ("not json at all", 0),
])
def test_claude_cli_failures_raise(fake_cli, stdout, returncode):
    _, reply, image = fake_cli
    reply["stdout"], reply["returncode"] = stdout, returncode
    with pytest.raises(RuntimeError):
        vision_client._chat_json_with_images(prompt="Review", image_paths=[image], timeout=30)


def test_claude_cli_timeout_raises(fake_cli):
    _, reply, image = fake_cli
    reply["raise"] = subprocess.TimeoutExpired(cmd="claude", timeout=30)
    with pytest.raises(RuntimeError, match="timed out"):
        vision_client._chat_json_with_images(prompt="Review", image_paths=[image], timeout=30)


def test_review_metadata_names_the_claude_provider(fake_cli):
    result = vision_client.run_gtm_vision_review(site_context={}, screenshots=[])
    assert result["metadata"]["provider"] == "claude_cli"


# --- server: fast report first, AI review afterwards ----------------------------

@pytest.fixture
def website_job(monkeypatch, tmp_path):
    from src.jobs.store import JobStore

    store = JobStore(tmp_path / "jobs.sqlite3")
    monkeypatch.setattr(server, "JOB_STORE", store)
    monkeypatch.setattr(server, "AUDITS_DIR", tmp_path / "audits")
    job = server._new_job("https://example.com/", "gtm")
    store.create(job, owner_id="user-a", owner_role="reviewer")
    monkeypatch.setattr(server, "_package_local_report", lambda *_args: "/audits/x/")
    return job["id"]


def test_claude_backend_skips_vision_in_the_timed_pipeline(website_job, monkeypatch):
    monkeypatch.setenv("GTM_VISION_BACKEND", "claude_cli")
    seen = []
    monkeypatch.setattr(server, "_run_command", lambda job_id, command, **kwargs: seen.append(command) or 0)
    monkeypatch.setattr(server, "_start_ai_review", lambda job_id: None)
    server._run_audit_job(website_job)
    assert "--skip-vision" in seen[0]
    assert server.JOB_STORE.get(website_job)["status"] == "completed"


def test_completed_job_starts_ai_review_only_with_claude_backend(website_job, monkeypatch):
    started = []
    monkeypatch.setattr(server, "_run_command", lambda *args, **kwargs: 0)
    monkeypatch.setattr(server, "_start_ai_review", started.append)
    monkeypatch.delenv("GTM_VISION_BACKEND", raising=False)
    server._run_audit_job(website_job)
    assert started == []
    monkeypatch.setenv("GTM_VISION_BACKEND", "claude_cli")
    second = server._new_job("https://example.com/", "gtm")
    server.JOB_STORE.create(second, owner_id="user-a", owner_role="reviewer")
    server._run_audit_job(second["id"])
    assert started == [second["id"]]


def test_ai_review_regenerates_the_report_and_marks_success(website_job, monkeypatch):
    commands = []
    monkeypatch.setattr(server.subprocess, "run", lambda command, **kwargs: commands.append(command) or subprocess.CompletedProcess(command, 0, stdout="ok", stderr=""))
    server._set_job(website_job, status="running"); server._set_job(website_job, status="completed")
    server._run_ai_review(website_job)
    job = server.JOB_STORE.get(website_job)
    assert job["status"] == "completed" and job["aiReviewStatus"] == "completed"
    modules = [command[command.index("-m") + 1] for command in commands]
    assert modules == ["src.gtm_audit.generate_gtm_audit", "src.gtm_audit.generate_gtm_report"]
    assert "--skip-vision" not in commands[0]


def test_ai_review_failure_keeps_the_report(website_job, monkeypatch):
    monkeypatch.setattr(server.subprocess, "run", lambda command, **kwargs: subprocess.CompletedProcess(command, 1, stdout="boom", stderr=""))
    server._set_job(website_job, status="running"); server._set_job(website_job, status="completed", resultUrl="/audits/x/")
    server._run_ai_review(website_job)
    job = server.JOB_STORE.get(website_job)
    assert job["status"] == "completed" and job["resultUrl"] == "/audits/x/"
    assert job["aiReviewStatus"] == "failed" and job["aiReviewError"]


def test_start_ai_review_runs_in_the_background(website_job, monkeypatch):
    done = threading.Event()
    monkeypatch.setattr(server, "_run_ai_review", lambda job_id: done.set())
    server._start_ai_review(website_job)
    assert done.wait(2)
    assert server.JOB_STORE.get(website_job)["aiReviewStatus"] == "running"
