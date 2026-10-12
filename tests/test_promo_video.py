"""Structural checks for the French promo video (video/promo-fr).

Pins the timeline, the French copy, the product facts and that every asset is local,
so the render can't drift from docs/superpowers/specs/2026-10-08-promo-video-fr-design.md.
"""
import json
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "video" / "promo-fr"
COMPS = PROJECT / "compositions"
LANDING = ROOT / "src" / "ui" / "frontend" / "landing" / "Landing.jsx"

WINDOWS = [
    ("hook", 0, 4.5), ("logo", 4.5, 2), ("solution", 6.5, 2.5), ("input", 9, 3),
    ("evidence", 12, 5), ("stat", 17, 3), ("report-expert", 20, 6), ("end", 26, 4),
]
FORBIDDEN = re.compile(r"claude|\bvlm\b|\bgpt\b|gemini|machine finding", re.I)


class _Collect(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def tags(path):
    parser = _Collect()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser.tags


def text_of(name):
    return (COMPS / f"{name}.html").read_text(encoding="utf-8")


def copy():
    return json.loads((PROJECT / "copy.json").read_text(encoding="utf-8"))


def assets(name):
    return json.loads((PROJECT / "assets" / name).read_text(encoding="utf-8"))


def project_files():
    return [p for p in PROJECT.rglob("*") if p.is_file() and "node_modules" not in p.parts and "renders" not in p.parts]


def test_timeline_windows():
    found = {a["data-composition-id"]: a for t, a in tags(PROJECT / "index.html") if "data-composition-src" in a}
    root = next(a for t, a in tags(PROJECT / "index.html") if "data-composition-id" in a and "data-composition-src" not in a)
    assert float(root["data-duration"]) == 30
    assert (root["data-width"], root["data-height"]) == ("1920", "1080")
    for name, start, duration in WINDOWS:
        clip = found[name]
        assert clip["data-composition-src"] == f"compositions/{name}.html"
        assert (float(clip["data-start"]), float(clip["data-duration"])) == (start, duration), name
        inner = next(a for t, a in tags(COMPS / f"{name}.html") if "data-composition-id" in a)
        assert inner["data-composition-id"] == name


def test_copy_is_french_and_clean():
    checked = [p for p in project_files() if p.suffix in {".html", ".json", ".js", ".css"}]
    assert checked
    for path in checked:
        assert not FORBIDDEN.search(path.read_text(encoding="utf-8")), path


def _landing_findings():
    source = LANDING.read_text(encoding="utf-8")
    block = source[source.index("const FINDINGS = ["):source.index("].map(item")]
    rows = re.findall(r'axis: "(\w+)".*?measured: (true|false), box: \[([\d, ]+)\].*?fr: "([^"]+)"', block)
    return [{"axis": a, "measured": m == "true", "box": [int(n) for n in b.split(",")], "fr": fr} for a, m, b, fr in rows]


def test_facts():
    axes = assets("axes.json")
    assert len(axes) == 7
    assert sum(axis["criteria"] for axis in axes) == 67
    expected = _landing_findings()
    assert len(expected) == 5
    assert [{k: f[k] for k in ("axis", "measured", "box", "fr")} for f in assets("findings.json")] == expected


# Kept out of git on purpose (the expert's photo, the personal-use test music): a fresh clone won't have them.
LOCAL_ONLY = {"assets/expert.jpg", "assets/audio/music-test.mp3"}


def test_assets_are_local():
    ignored = (PROJECT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert LOCAL_ONLY <= set(ignored)
    refs = re.compile(r'''(?:src|href)=["']([^"'#]+)["']|url\(["']?([^"')]+)["']?\)''')
    for path in project_files():
        if path.suffix not in {".html", ".css"}:
            continue
        for match in refs.finditer(path.read_text(encoding="utf-8")):
            ref = match.group(1) or match.group(2)
            if ref.startswith("data:"):
                continue
            assert not ref.startswith(("http:", "https:", "/")), (path, ref)
            base = PROJECT if path.parent == COMPS else path.parent
            if ref in LOCAL_ONLY and not (base / ref).is_file():
                continue
            assert (base / ref).resolve().is_file(), (path, ref)
            assert PROJECT in (base / ref).resolve().parents, (path, ref)


def visible_text(name):
    """Composition text with tags removed, so split-word markup still reads as the sentence."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text_of(name)))


def test_dotfield_is_deterministic():
    source = (PROJECT / "lib" / "dotfield.js").read_text(encoding="utf-8")
    assert not re.search(r"Math\.random|Date\.now|performance\.now|requestAnimationFrame", source)
    assert "mulberry32" in source
    points = (PROJECT / "lib" / "logo-points.js").read_text(encoding="utf-8")
    assert points.startswith("window.LOGO_POINTS = [")


def test_hook_copy():
    text = visible_text("hook")
    positions = [text.index(line) for line in copy()["hook"]]
    assert positions == sorted(positions)
    assert "createDotField" in text_of("hook") and "createDotField" in text_of("logo")
    assert "assets/ey-studio-plus.png" in text_of("logo")


def test_solution_input_copy():
    c = copy()
    solution, given = visible_text("solution"), visible_text("input")
    assert c["solution"]["word"] in solution and c["solution"]["subtitle"] in solution
    for phrase in c["input"] + c["sources"] + ["Lancer un audit"]:
        assert phrase in given, phrase


def test_input_types_example_url():
    urls = re.findall(r"https?://[^\s\"'<]+|[\w-]+\.(?:fr|com)\b", text_of("input"))
    assert urls and set(urls) == {"https://exemple.fr"}


def test_solution_giant_word():
    source = text_of("solution")
    rule = re.search(r"#solution-word\s*\{([^}]*)\}", source).group(1)
    assert int(re.search(r"font-weight:\s*(\d+)", rule).group(1)) <= 300
    assert int(re.search(r"font-size:\s*(\d+)px", rule).group(1)) >= 220
    assert 'class="horizon"' in source
    assert 'href="lib/horizon.css"' in (PROJECT / "index.html").read_text(encoding="utf-8")


FINDING_TIMES = [13.2, 13.9, 14.6, 15.3, 16.0]


def _findings_markup():
    root = next(a for t, a in tags(COMPS / "evidence.html") if a.get("data-composition-id") == "evidence")
    return float(root["data-scale"]), [a for t, a in tags(COMPS / "evidence.html") if "finding" in a.get("class", "").split()]


def test_evidence_boxes_scaled():
    scale, found = _findings_markup()
    assert len(found) == 5
    for item, attrs in zip(assets("findings.json"), found):
        style = dict(re.findall(r"([\w-]+):\s*([\d.]+)px", attrs["style"]))
        for key, value in zip(("left", "top", "width", "height"), item["box"]):
            assert abs(float(style[key]) - value * scale) <= 1, (item["fr"], key)


def test_evidence_labels_and_times():
    c, text = copy(), visible_text("evidence")
    assert c["evidence"] in text
    for item in assets("findings.json"):
        assert item["fr"] in text
    assert text.count(c["measured"]) == 1 and text.count(c["expertReview"]) == 4
    _, found = _findings_markup()
    assert [float(a["data-sfx"]) for a in found] == FINDING_TIMES


def test_stat_counter():
    c, found = copy(), tags(COMPS / "stat.html")
    counter = next(a for t, a in found if a.get("id") == "stat-count")
    assert counter["data-to"] == str(sum(axis["criteria"] for axis in assets("axes.json"))) == "67"
    chips = re.findall(r'<li class="stat-chip"[^>]*>(.*?)</li>', text_of("stat"))
    assert [re.sub(r"<[^>]+>.*", "", chip).strip() for chip in chips] == [axis["fr"] for axis in assets("axes.json")]
    assert c["stat"][0] in visible_text("stat") and "critères." in visible_text("stat")


def test_expert_card():
    c, text = copy(), visible_text("report-expert")
    for key in ("report", "expert", "expertName", "expertTitle", "cta"):
        assert c[key] in text, key
    photo = next(a for t, a in tags(COMPS / "report-expert.html") if t == "img" and a.get("id") == "re-photo")
    assert photo["src"] == "assets/expert.jpg" and photo["alt"] == c["expertName"]


def test_end_copy():
    c, text, source = copy(), visible_text("end"), text_of("end")
    for line in c["payoff"] + [c["tagline"]]:
        assert line in text, line
    assert 'src="assets/ey-studio-plus.png"' in source
    assert 'class="horizon"' in source and "createDotField" in source


def test_audio_tracks():
    audio = [a for t, a in tags(PROJECT / "index.html") if t == "audio"]
    assert all(a.get("id") for a in audio)
    music = [a for a in audio if a["id"] == "music"]
    assert len(music) == 1
    assert (float(music[0]["data-start"]), float(music[0]["data-duration"])) == (0, 30)
    assert float(music[0]["data-volume"]) <= 0.6
    ticks = sorted(float(a["data-start"]) for a in audio if a["id"].startswith("tick-finding"))
    assert len(ticks) == 5 and all(abs(t - e) <= 0.05 for t, e in zip(ticks, FINDING_TIMES))
    counter = [float(a["data-start"]) for a in audio if a["id"].startswith("tick-count")]
    assert counter and all(17.3 <= t <= 19.0 for t in counter)
    assert [float(a["data-start"]) for a in audio if a["id"] == "tick-cta"] == [25.0]
    credits = (PROJECT / "assets" / "audio" / "CREDITS.md").read_text(encoding="utf-8")
    for name in {Path(a["src"]).name for a in audio}:
        assert name in credits, name
