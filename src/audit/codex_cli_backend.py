"""Isolated, opt-in Codex CLI transport for machine-validated audit reviews.

Never invoke an agent in the project working directory: prompts and attached
screenshots are untrusted audit evidence, not instructions to execute.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Sequence


def run_codex_cli_json(
    *,
    prompt: str,
    timeout: int,
    image_paths: Sequence[Path] = (),
    model: str | None = None,
) -> str:
    """Return the Codex final message for validation by vlm_schema.

    Requires the independently installed and authenticated Codex CLI.
    Uses an isolated temporary cwd, an ephemeral run, and a read-only sandbox.
    No shell is used, and nothing from stdout/stderr is logged.
    """
    configured_binary = os.environ.get("GTM_CODEX_CLI", "").strip()
    binary = configured_binary or shutil.which("codex")
    if not binary:
        raise RuntimeError("Codex CLI not found. Install Codex and run 'codex login' first.")

    images: list[Path] = []
    for original in image_paths:
        path = Path(original).resolve(strict=True)
        if not path.is_file() or path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            raise ValueError("Codex vision requires existing PNG, JPEG, or WebP image files.")
        images.append(path)

    with tempfile.TemporaryDirectory(prefix="uxui-codex-") as temporary:
        output_file = Path(temporary) / "last-message.txt"
        command = [
            binary,
            "exec",
            "--sandbox", "read-only",
            "--ephemeral",
            "--skip-git-repo-check",
            "--ignore-user-config",
            "--ignore-rules",
            "--output-last-message", str(output_file),
        ]
        if model and model != "codex-cli":
            command.extend(["--model", model])
        for path in images:
            command.extend(["--image", str(path)])
        command.append("-")

        try:
            result = subprocess.run(
                command,
                input=prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                cwd=temporary,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"Codex CLI timed out after {timeout} seconds.") from exc
        except OSError as exc:
            raise RuntimeError("Codex CLI could not be started; check its installation.") from exc

        if result.returncode != 0:
            # Do not include output: stderr may contain sensitive prompt/image data.
            raise RuntimeError(
                f"Codex CLI exited with code {result.returncode}. "
                "Check 'codex login status' and CLI/model availability."
            )
        if not output_file.is_file():
            raise RuntimeError("Codex CLI succeeded but did not create a final response.")
        answer = output_file.read_text(encoding="utf-8").strip()
        if not answer:
            raise RuntimeError("Codex CLI returned an empty final response.")
        return answer
