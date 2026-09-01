from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
GENERATED_DIR = ROOT_DIR / "shared" / "generated"
DEFAULT_SOURCE = GENERATED_DIR / "gtm_audit.json"
DEFAULT_OUTPUT = GENERATED_DIR / "chatgpt_final_gtm_audit.json"


def finding(
    *,
    finding_id: str,
    axis_id: str,
    axis_name: str,
    axis_score: int,
    title: str,
    page_name: str,
    page_url: str,
    severity: str,
    confidence: str,
    evidence: str,
    explanation: str,
    why_it_matters: str,
    recommendation: str,
    acceptance_criteria: str,
    effort: str,
    screenshot_path: str,
) -> dict[str, Any]:
    confidence_score = {"High": 0.9, "Medium": 0.68, "Low": 0.45}[confidence]
    return {
        "_findingId": finding_id,
        "axisId": axis_id,
        "axisName": axis_name,
        "axisScore": axis_score,
        "title": title,
        "pageName": page_name,
        "pageUrl": page_url,
        "sourceSheet": "ChatGPT evidence validation",
        "severity": severity.lower(),
        "confidence": confidence_score,
        "evidence": evidence,
        "visibleSignals": [evidence],
        "explanation": explanation,
        "whyItMatters": why_it_matters,
        "recommendation": recommendation,
        "screenshotPath": screenshot_path,
        "visualRegion": None,
    }


def build_payload(source: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(source)
    payload["version"] = "chatgpt-final-1.0"
    payload["generator"] = "scripts.build_chatgpt_gtm_final"
    payload.setdefault("site", {})["language"] = "fr"
    payload["site"]["display_name"] = "UE Tunisie"

    screenshots = {
        "home": "shared/output/screenshots/ue-tunisie.org/Home/page/main.png",
        "carte": "shared/output/screenshots/ue-tunisie.org/CARTE/page/main.png",
        "carte_mobile": (
            "shared/generated/gtm-report/evidence/"
            "issue-01-website-layout-breaks-on-phone-screens.png"
        ),
    }

    findings = [
        finding(
            finding_id="UE-01",
            axis_id="flow_architecture",
            axis_name="Flow & Architecture",
            axis_score=62,
            title="Narrow map layout preserves a miniature desktop composition",
            page_name="Carte des actions · Mobile",
            page_url="https://ue-tunisie.org/zone_projects",
            severity="High",
            confidence="High",
            evidence=(
                "The 390 × 844 capture retains the desktop-style header, filter rail, map, "
                "three-column results and multi-column footer at a severely reduced scale."
            ),
            explanation=(
                "At phone width, the project-discovery interface is visually compressed instead "
                "of reorganized into a readable staged or single-column journey. The evidence "
                "describes the visible result; it does not assume the underlying CSS cause."
            ),
            why_it_matters=(
                "Project names, filters, pagination and navigation become difficult to perceive "
                "without magnification, weakening access to the site's primary discovery feature."
            ),
            recommendation=(
                "Introduce a mobile header, a labeled filter drawer, a map/list switch and "
                "single-column project cards."
            ),
            acceptance_criteria=(
                "At 390px and 430px, body text is readable without zoom, filters open in a labeled "
                "panel, cards use one column and no primary content is miniaturized."
            ),
            effort="Large",
            screenshot_path=screenshots["carte_mobile"],
        ),
        finding(
            finding_id="UE-02",
            axis_id="task_execution",
            axis_name="Performance & Task Execution",
            axis_score=64,
            title="Heavy transfers keep both pages loading long after initial paint",
            page_name="Home and Carte",
            page_url="https://ue-tunisie.org/",
            severity="High",
            confidence="High",
            evidence=(
                "Home transferred 13.9 MB across 54 resources with an 11.2 s load event; Carte "
                "transferred 12.4 MB across 73 resources with a 10.6 s load event. FCP remained "
                "near 1.1 s in this Playwright lab crawl."
            ),
            explanation=(
                "Useful content appears earlier than the final load event, but each page continues "
                "loading a large resource set. The values are single-crawl lab observations, not "
                "real-user field data."
            ),
            why_it_matters=(
                "Visitors on slow or metered connections incur avoidable waiting and bandwidth "
                "cost, while the organization has little performance headroom for future content."
            ),
            recommendation=(
                "Resize and modernize imagery, lazy-load below-the-fold media, subset and preload "
                "only essential fonts, and defer non-critical scripts."
            ),
            acceptance_criteria=(
                "Adopt and meet a repeatable page-weight and load-event budget while keeping LCP "
                "at or below 2.5 seconds and CLS below 0.1 under agreed lab conditions."
            ),
            effort="Medium",
            screenshot_path=screenshots["home"],
        ),
        finding(
            finding_id="UE-03",
            axis_id="trust_accessibility",
            axis_name="Trust & Accessibility",
            axis_score=56,
            title="Keyboard reach and focus visibility require dedicated validation",
            page_name="Home and Carte",
            page_url="https://ue-tunisie.org/",
            severity="Medium",
            confidence="Medium",
            evidence=(
                "The Chromium probe recorded 8 unique focus targets from 49 detected controls on "
                "Home and 22 from 71 on Carte, with several weak-focus samples. The probe did not "
                "activate every control and does not establish complete WCAG status."
            ),
            explanation=(
                "The automated evidence identifies a meaningful keyboard-access risk, but its "
                "coverage figures are not sufficient to prove that all remaining controls are "
                "unreachable or that the complete focus order fails."
            ),
            why_it_matters=(
                "If confirmed, visitors who rely on a keyboard or switch input may lose their "
                "position or struggle to reach navigation and project filters."
            ),
            recommendation=(
                "Run a complete Tab and Shift+Tab audit, correct unreachable controls and add a "
                "consistent high-contrast :focus-visible treatment."
            ),
            acceptance_criteria=(
                "Every applicable control is reachable and operable in logical order, focus never "
                "disappears, and the full filter journey works without a pointer."
            ),
            effort="Medium",
            screenshot_path=screenshots["carte"],
        ),
        finding(
            finding_id="UE-04",
            axis_id="trust_accessibility",
            axis_name="Trust & Accessibility",
            axis_score=56,
            title="Most inspected image instances have no extracted alt value",
            page_name="Home and Carte",
            page_url="https://ue-tunisie.org/",
            severity="Medium",
            confidence="High",
            evidence=(
                "The extraction found null alt values on 29 of 32 homepage images and 21 of 24 "
                "Carte images: 50 of 56 inspected image instances in total."
            ),
            explanation=(
                "The affected images include project photography, thematic icons and other visual "
                "content. The audit does not assume that every image is informative, but a missing "
                "attribute is not an intentional empty alternative."
            ),
            why_it_matters=(
                "Assistive technology may omit meaningful project information or announce "
                "unhelpful filenames, reducing access to the site's public-information content."
            ),
            recommendation=(
                "Classify images as informative, functional or decorative; provide concise "
                "contextual alternatives or explicit empty alt attributes as appropriate."
            ),
            acceptance_criteria=(
                "Every rendered img has an intentional alt attribute, automated missing-alt checks "
                "return zero, and a manual screen-reader review confirms useful announcements."
            ),
            effort="Medium",
            screenshot_path=screenshots["home"],
        ),
        finding(
            finding_id="UE-05",
            axis_id="flow_architecture",
            axis_name="Flow & Architecture",
            axis_score=62,
            title="Desktop filters are vertically disconnected from the map workspace",
            page_name="Carte des actions · Desktop",
            page_url="https://ue-tunisie.org/zone_projects",
            severity="Medium",
            confidence="High",
            evidence=(
                "The desktop capture shows a large blank area before Recherche in the left rail, "
                "while the results summary and map are already visible."
            ),
            explanation=(
                "The first filter controls sit substantially below the beginning of the map "
                "workspace, making a core discovery mechanism easy to overlook."
            ),
            why_it_matters=(
                "Visitors may begin browsing the map without discovering the governorate, theme, "
                "organization, status and label filters."
            ),
            recommendation=(
                "Align the filter heading and first control with the map status area and keep the "
                "reset/filter actions in a compact, discoverable region."
            ),
            acceptance_criteria=(
                "Recherche and the first filters appear when the map enters the viewport, actions "
                "remain discoverable and no unexplained gap precedes the form."
            ),
            effort="Medium",
            screenshot_path=screenshots["carte"],
        ),
        finding(
            finding_id="UE-06",
            axis_id="task_execution",
            axis_name="Performance & Task Execution",
            axis_score=64,
            title="Homepage video showcase appears empty in the captured state",
            page_name="Home · Desktop",
            page_url="https://ue-tunisie.org/",
            severity="Medium",
            confidence="High",
            evidence=(
                "The large Vidéos des projets panel shows controls, dots and a label but no poster, "
                "title, thumbnail, loading message or error explanation in the captured state."
            ),
            explanation=(
                "The evidence does not establish whether the cause is lazy loading, an embed "
                "failure or unavailable content; it establishes only that the visible state looks empty."
            ),
            why_it_matters=(
                "A prominent area intended to demonstrate project activity can appear unfinished "
                "and communicates no evidence when third-party media does not load."
            ),
            recommendation=(
                "Render a local poster and descriptive title before the embed loads, with explicit "
                "loading, unavailable and no-content states."
            ),
            acceptance_criteria=(
                "The module always presents a meaningful poster/title or clear status message and "
                "remains informative when embedded media fails."
            ),
            effort="Medium",
            screenshot_path=screenshots["home"],
        ),
        finding(
            finding_id="UE-07",
            axis_id="content_microcopy",
            axis_name="Content & Microcopy",
            axis_score=80,
            title="The map page lacks a distinct document identity and clean heading structure",
            page_name="Carte des actions",
            page_url="https://ue-tunisie.org/zone_projects",
            severity="Medium",
            confidence="High",
            evidence=(
                "Both audited URLs use the same document title. Carte contains three extracted H1 "
                "elements—Carte des actions and Recherche twice—and a skipped H1-to-H3 level."
            ),
            explanation=(
                "The map page has a distinct purpose but is not distinguished in the browser title, "
                "and its duplicated top-level headings make semantic navigation less predictable."
            ),
            why_it_matters=(
                "Bookmarks, browser history and assistive heading navigation provide weaker "
                "orientation around this high-value project-discovery destination."
            ),
            recommendation=(
                "Give Carte a unique descriptive title, retain one meaningful H1 and structure "
                "search, map results and projects as subordinate sections."
            ),
            acceptance_criteria=(
                "Each URL has a unique title, exactly one meaningful H1 and a hierarchy with no "
                "duplicate section headings or skipped levels."
            ),
            effort="Small",
            screenshot_path=screenshots["carte"],
        ),
        finding(
            finding_id="UE-08",
            axis_id="content_microcopy",
            axis_name="Content & Microcopy",
            axis_score=80,
            title="Programme codes and truncated titles slow project-card comprehension",
            page_name="Carte des actions",
            page_url="https://ue-tunisie.org/zone_projects",
            severity="Low",
            confidence="Medium",
            evidence=(
                "Cards display codes such as IPDLI, DEPOLMED, INSADDER and PAP SONEDE, while several "
                "long project headings are shortened with ellipses."
            ),
            explanation=(
                "The codes are legitimate programme identifiers and descriptive titles are present, "
                "but first-time visitors may need more space or context to scan them quickly."
            ),
            why_it_matters=(
                "Important distinguishing words can be hidden at the point where visitors compare "
                "projects, adding interpretation work."
            ),
            recommendation=(
                "Keep codes as secondary metadata, expand them when useful and provide sufficient "
                "space for the plain-language project title."
            ),
            acceptance_criteria=(
                "Each card communicates its subject without prior code knowledge and the full title "
                "is available to sighted and assistive-technology users."
            ),
            effort="Small",
            screenshot_path=screenshots["carte"],
        ),
    ]

    by_axis: dict[str, list[dict[str, Any]]] = {}
    for item in findings:
        by_axis.setdefault(item["axisId"], []).append(item)

    axis_config = {
        "task_execution": {
            "score": 64,
            "severity": "medium",
            "confidence": 0.9,
            "summary": (
                "Initial paint is reasonably fast, but 12.4–13.9 MB transfers, long load events "
                "and an empty captured media state create meaningful friction."
            ),
            "businessImpact": (
                "Heavy delivery increases waiting and data cost, especially on slower or metered connections."
            ),
            "strengths": [
                {
                    "title": "Initial content appears before the page finishes loading",
                    "evidence": "FCP was approximately 1.1 seconds on both audited pages.",
                    "pageName": "Home and Carte",
                    "pageUrl": "https://ue-tunisie.org/",
                    "screenshotPath": screenshots["home"],
                }
            ],
        },
        "flow_architecture": {
            "score": 62,
            "severity": "medium",
            "confidence": 0.88,
            "summary": (
                "Desktop project discovery is understandable, but the narrow layout and displaced "
                "filter rail weaken access to the map journey."
            ),
            "businessImpact": (
                "Discovery friction makes funded projects harder to find and compare across devices."
            ),
            "strengths": [
                {
                    "title": "Desktop project discovery combines filters, map, results and pagination",
                    "evidence": "The Carte capture exposes five filter dimensions and 79 geolocated projects.",
                    "pageName": "Carte",
                    "pageUrl": "https://ue-tunisie.org/zone_projects",
                    "screenshotPath": screenshots["carte"],
                }
            ],
        },
        "trust_accessibility": {
            "score": 56,
            "severity": "medium",
            "confidence": 0.72,
            "summary": (
                "Institutional identity and support routes are strong, while missing image alternatives "
                "and keyboard/focus risks require remediation and manual validation."
            ),
            "businessImpact": (
                "Accessibility barriers reduce the reach of public project information and weaken inclusive trust."
            ),
            "strengths": [
                {
                    "title": "Institutional identity and contact routes are visible",
                    "evidence": "EU–Tunisia branding, legal/help links, telephone and email details are present.",
                    "pageName": "Home and Carte",
                    "pageUrl": "https://ue-tunisie.org/",
                    "screenshotPath": screenshots["home"],
                }
            ],
        },
        "ui_consistency": {
            "score": 78,
            "severity": "low",
            "confidence": 0.88,
            "summary": (
                "The desktop pages share a coherent institutional palette, typography, header, footer "
                "and card system; responsive behavior prevents a higher score."
            ),
            "businessImpact": (
                "A recognizable visual system reinforces credibility and makes the public platform easier to learn."
            ),
            "strengths": [
                {
                    "title": "A coherent desktop visual system supports recognition",
                    "evidence": "Both pages consistently use the blue palette, typography, header/footer and card language.",
                    "pageName": "Home and Carte",
                    "pageUrl": "https://ue-tunisie.org/",
                    "screenshotPath": screenshots["home"],
                }
            ],
        },
        "content_microcopy": {
            "score": 80,
            "severity": "low",
            "confidence": 0.86,
            "summary": (
                "French headings, controls and institutional messaging are generally clear and specific, "
                "with smaller issues in page identity and project-card scanning."
            ),
            "businessImpact": (
                "Clear public-language labels help visitors understand the platform and act with confidence."
            ),
            "strengths": [
                {
                    "title": "The homepage establishes purpose immediately",
                    "evidence": (
                        "The hero identifies the EU–Tunisia partnership and describes the official project platform."
                    ),
                    "pageName": "Home",
                    "pageUrl": "https://ue-tunisie.org/",
                    "screenshotPath": screenshots["home"],
                },
                {
                    "title": "French task labels are concise and familiar",
                    "evidence": "Rechercher, Télécharger, Partager, Réinitialiser and Filtrer are explicit.",
                    "pageName": "Home and Carte",
                    "pageUrl": "https://ue-tunisie.org/",
                    "screenshotPath": screenshots["carte"],
                },
            ],
        },
    }

    for axis in payload.get("axes") or []:
        axis_id = axis.get("id")
        if axis_id not in axis_config:
            continue
        config = axis_config[axis_id]
        axis.update(config)
        axis["shortName"] = {
            "task_execution": "Performance & Task Execution",
            "flow_architecture": "Flow & Architecture",
            "trust_accessibility": "Trust & Accessibility",
            "ui_consistency": "Visual & UI Consistency",
            "content_microcopy": "Content & Microcopy",
        }[axis_id]
        axis["name"] = axis["shortName"]
        axis["painPoints"] = by_axis.get(axis_id, [])
        axis["opportunities"] = [item["recommendation"] for item in axis["painPoints"][:3]]
        axis["evidence"] = [item["evidence"] for item in axis["painPoints"]]
        axis["signals"] = {
            "reviewedBy": "ChatGPT",
            "evidenceValidated": True,
            "acceptedFindings": len(axis["painPoints"]),
        }

    strongest_axis = next(axis for axis in payload["axes"] if axis["id"] == "content_microcopy")
    weakest_axis = next(axis for axis in payload["axes"] if axis["id"] == "trust_accessibility")
    priority_ids = {"UE-01", "UE-02", "UE-04", "UE-03", "UE-06"}
    priorities = [item for item in findings if item["_findingId"] in priority_ids]

    payload["executiveSummary"] = {
        "overallScore": 68,
        "confidence": "Medium",
        "verdict": "Mixed",
        "strongestAxis": {
            "id": strongest_axis["id"],
            "name": strongest_axis["name"],
            "score": strongest_axis["score"],
        },
        "weakestAxis": {
            "id": weakest_axis["id"],
            "name": weakest_axis["name"],
            "score": weakest_axis["score"],
        },
        "summary": (
            "UE Tunisie presents a clear, credible and visually coherent institutional experience "
            "on desktop. Its narrow map layout, heavy resource delivery and verified accessibility "
            "risks materially weaken access to the core project-discovery journey."
        ),
        "positioningHook": (
            "The content proposition is strong; the priority is making it lighter, responsive and inclusive."
        ),
        "topPriorities": priorities,
    }


    payload["recommendations"] = [
        {
            "priority": "Near term",
            "title": "Reconstruct the narrow Carte journey",
            "description": (
                "Introduce a mobile header, labeled filter drawer, map/list switch and single-column results. "
                "Align the desktop filter rail with the map workspace."
            ),
            "impact": "Makes the primary project-discovery journey readable and usable across common device widths.",
            "axis": "Flow & Architecture · UE-01, UE-05",
        },
        {
            "priority": "Near term",
            "title": "Reduce media, image and font delivery",
            "description": (
                "Modernize imagery, lazy-load below-the-fold assets, add resilient video placeholders, "
                "subset fonts and defer non-critical scripts."
            ),
            "impact": "Reduces bandwidth cost and long-tail loading while preserving the existing visual identity.",
            "axis": "Performance & Task Execution · UE-02, UE-06",
        },
        {
            "priority": "Quick win",
            "title": "Make image alternatives intentional",
            "description": (
                "Classify every image and provide contextual alt text or explicit empty alternatives, "
                "then validate the experience with a screen reader."
            ),
            "impact": "Restores access to project and thematic imagery for assistive-technology users.",
            "axis": "Trust & Accessibility · UE-04",
        },
        {
            "priority": "Quick win",
            "title": "Correct titles, headings and project-card scanning",
            "description": (
                "Give Carte a unique document title, retain one H1 and keep programme codes secondary "
                "to readable project names."
            ),
            "impact": "Improves orientation, bookmarks, semantic navigation and first-time comprehension.",
            "axis": "Content & Microcopy · UE-07, UE-08",
        },
        {
            "priority": "Strategic",
            "title": "Establish keyboard, responsive and performance regression gates",
            "description": (
                "Complete manual keyboard/screen-reader validation and add repeatable device, accessibility "
                "and performance checks to release criteria."
            ),
            "impact": "Turns the current audit into a durable quality baseline instead of a one-time remediation.",
            "axis": "Cross-axis · UE-01, UE-02, UE-03, UE-04",
        },
    ]

    payload["methodology"] = [
        {
            "step": "Evidence collection",
            "description": (
                "Two live pages were captured at desktop size, with a narrow Carte view and structured "
                "DOM, content, performance and interaction signals."
            ),
        },
        {
            "step": "Evidence validation",
            "description": (
                "ChatGPT cross-checked machine claims against measurements, extracted content and screenshots, "
                "rejecting contradictions and unsupported conclusions."
            ),
        },
        {
            "step": "Client synthesis",
            "description": (
                "Validated findings were deduplicated, rescored and translated into prioritized actions."
            ),
        },
    ]

    for item in findings:
        item.pop("_findingId", None)

    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the reviewed ChatGPT GTM audit payload.")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_path = Path(args.source).resolve()
    output_path = Path(args.output).resolve()
    with source_path.open("r", encoding="utf-8") as file:
        source = json.load(file)

    if (source.get("site") or {}).get("domain") != "ue-tunisie.org":
        raise ValueError("The source payload is not the expected ue-tunisie.org audit.")

    payload = build_payload(source)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")
    print(f"Reviewed GTM audit payload written to: {output_path}")


if __name__ == "__main__":
    main()
