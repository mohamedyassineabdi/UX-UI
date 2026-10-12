"""AI review through the signed-in `claude` CLI instead of an API key."""
import json
import subprocess

import pytest
from pydantic import BaseModel

from src.audit import ai_review_client
from src.audit.ai_review_client import AIReviewClient, load_ai_review_config


class _Verdict(BaseModel):
    verdict: str


def _cli_reply(result="{}", *, is_error=False, subtype="success"):
    return json.dumps({"type": "result", "subtype": subtype, "is_error": is_error, "result": result})


@pytest.fixture
def clean_env(monkeypatch):
    monkeypatch.setattr(ai_review_client, "_load_project_dotenv", lambda: None)
    for key in ("AI_REVIEW_BACKEND", "AI_REVIEW_MODEL", "AI_REVIEW_BASE_URL", "AI_REVIEW_API_KEY",
                "OLLAMA_HOST", "OLLAMA_MODEL", "OLLAMA_BASE_URL", "OLLAMA_API_KEY",
                "GROQ_API_KEY", "GROQ_MODEL", "GROQ_BASE_URL",
                "OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_BASE_URL"):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def fake_cli(monkeypatch, clean_env):
    calls = []
    reply = {"stdout": _cli_reply('{"verdict": "ok"}'), "returncode": 0, "raise": None}

    def run(command, **kwargs):
        calls.append({"command": list(command), **kwargs})
        if reply["raise"]:
            raise reply["raise"]
        return subprocess.CompletedProcess(command, reply["returncode"], stdout=reply["stdout"], stderr="")

    monkeypatch.setenv("AI_REVIEW_BACKEND", "claude_cli")
    monkeypatch.setenv("AI_REVIEW_REQUEST_SPACING_SECONDS", "0")
    monkeypatch.setattr(ai_review_client, "_claude_binary", lambda: "claude")
    monkeypatch.setattr(ai_review_client.subprocess, "run", run)
    return calls, reply


def _review(client=None):
    return (client or AIReviewClient()).review_validated_json(
        "You are a reviewer.", {"finding": "Low contrast"}, schema=_Verdict, prompt_version="t1")


def test_claude_cli_config_needs_no_key_or_url(fake_cli):
    config = load_ai_review_config()
    assert config.backend == "claude_cli"
    assert config.model == "claude-cli"
    assert config.api_key == ""


def test_claude_cli_review_returns_validated_result(fake_cli):
    _, reply = fake_cli
    reply["stdout"] = _cli_reply('```json\n{"verdict": "keep"}\n```')
    out = _review()
    assert out["status"] == "completed"
    assert out["result"] == {"verdict": "keep"}
    assert out["metadata"]["provider"] == "claude_cli"
    assert out["metadata"]["model"] == "claude-cli"


def test_claude_cli_has_no_tools_and_prompt_goes_through_stdin(fake_cli):
    calls, _ = fake_cli
    _review()
    command, call = calls[0]["command"], calls[0]
    assert command[:2] == ["claude", "-p"]
    assert command[command.index("--tools") + 1] == ""
    assert "--strict-mcp-config" in command and "--no-session-persistence" in command
    assert "You are a reviewer." in call["input"] and "Low contrast" in call["input"]
    assert "Low contrast" not in " ".join(command)
    assert call["timeout"] == 120


@pytest.mark.parametrize("stdout", [
    _cli_reply("Not logged in", is_error=True),
    _cli_reply("", subtype="error_max_turns"),
    "not json at all",
])
def test_claude_cli_failures_mark_the_review_failed(fake_cli, stdout):
    _, reply = fake_cli
    reply["stdout"], reply["returncode"] = stdout, 1
    assert _review()["status"] == "failed"


def test_claude_cli_timeout_raises(fake_cli):
    _, reply = fake_cli
    reply["raise"] = subprocess.TimeoutExpired(cmd="claude", timeout=120)
    with pytest.raises(RuntimeError, match="timed out"):
        AIReviewClient()._call_claude_cli("system", {"a": 1})


def test_missing_cli_raises(fake_cli):
    _, reply = fake_cli
    reply["raise"] = FileNotFoundError("claude")
    with pytest.raises(RuntimeError, match="not available"):
        AIReviewClient()._call_claude_cli("system", {"a": 1})


def test_other_backends_still_load(clean_env, monkeypatch):
    assert load_ai_review_config().backend == "ollama"
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")
    config = load_ai_review_config()
    assert (config.backend, config.model) == ("openai", "gpt-test")
