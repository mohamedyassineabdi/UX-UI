from __future__ import annotations

import tomllib
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


def test_requirements_export_matches_canonical_direct_dependencies():
    project = tomllib.loads((ROOT_DIR / "pyproject.toml").read_text(encoding="utf-8"))
    canonical = set(project["project"]["dependencies"])
    exported = {
        line.strip()
        for line in (ROOT_DIR / "requirements.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

    assert exported == canonical
