import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METHODOLOGY = json.loads((ROOT / "shared/config/audit_methodology_v3.json").read_text(encoding="utf-8"))
LANDING = (ROOT / "src/ui/frontend/landing/Landing.jsx").read_text(encoding="utf-8")
INDEX = (ROOT / "src/ui/frontend/index.html").read_text(encoding="utf-8")


def test_landing_axes_mirror_methodology_v3():
    for axis in METHODOLOGY["axes"]:
        for lang in ("en", "fr"):
            assert f'"{axis["name"][lang]}"' in LANDING, (axis["id"], lang)
            assert f'"{axis["core_question"][lang]}"' in LANDING, (axis["id"], lang)
        line = next(row for row in LANDING.splitlines() if f'{{ id: "{axis["id"]}"' in row)
        assert f'criteria: {len(axis["criteria"])},' in line, axis["id"]


def test_static_description_matches_methodology_size():
    total = sum(len(axis["criteria"]) for axis in METHODOLOGY["axes"])
    assert f'{len(METHODOLOGY["axes"])} UX axes and {total} criteria' in INDEX
