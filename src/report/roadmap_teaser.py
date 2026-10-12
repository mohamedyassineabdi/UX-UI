"""Lead-generation "strategic roadmap" teaser with expert booking.

The teaser shows audit-specific counts and a blurred placeholder roadmap, then
invites the client to book a call with an EY Studio+ expert. It never carries
real recommendation text: callers pass findings, but only severity, axis, and
identity fields are read.
"""
from __future__ import annotations

import html
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


STYLESHEET_PATH = Path(__file__).resolve().parents[1] / "ui" / "frontend" / "styles" / "roadmap-teaser.css"
DEFAULT_BOOKING_URL = "https://cal.com/sofiene-m-hadheb-nwve91/30min"
DEFAULT_EXPERT_NAME = "Sofiene Mhadheb"
EXPERT_TITLE = {
    "en": "Customer Innovation and Experience Design Expert, EY Studio+",
    "fr": "Expert en innovation client et design d'expérience, EY Studio+",
}
CHIP_LABELS = (("quickWins", "quickWin"), ("structural", "structuralOne"), ("axes", "axesOne"))
BOOKING_HOSTS = {"cal.com", "app.cal.com"}
STRUCTURAL = {"critical", "high"}
QUICK_WIN = {"medium", "low"}
NON_FAILING = {"pass", "passed", "true", "not_applicable", "n/a", "na"}

COPY = {
    "en": {
        "eyebrow": "Expert roadmap",
        "heading": "Turn this audit into a redesign that meets your business goals",
        "body": "Get a prioritised redesign roadmap built from these findings — what to fix first, what to rethink, and how it ties to your business goals — in a 30-minute session with an EY Studio+ product design expert.",
        "cleanHeading": "Keep the momentum: plan your next design iteration",
        "cleanBody": "This audit found no blocking issues. Talk to an EY Studio+ product design expert about where to take the experience next.",
        "cta": "Book a call with an expert",
        "quickWins": "quick wins",
        "quickWin": "quick win",
        "structuralOne": "structural change",
        "axesOne": "area to improve",
        "structural": "structural changes",
        "axes": "areas to improve",
        "lockLabel": "Roadmap shared in your expert session",
        "modalTitle": "Book your expert session",
        "close": "Close",
        "newTab": "opens the booking page",
        "openNewTab": "Open in a new tab",
    },
    "fr": {
        "eyebrow": "Feuille de route experte",
        "heading": "Transformez cet audit en une refonte alignée sur vos objectifs business",
        "body": "Obtenez une feuille de route de refonte priorisée, construite à partir de ces constats — quoi corriger d'abord, quoi repenser et comment l'aligner sur vos objectifs business — lors d'une session de 30 minutes avec un expert product design EY Studio+.",
        "cleanHeading": "Gardez l'élan : planifiez votre prochaine itération design",
        "cleanBody": "Cet audit n'a relevé aucun problème bloquant. Échangez avec un expert product design EY Studio+ sur la suite de votre expérience.",
        "cta": "Réserver un appel avec un expert",
        "quickWins": "gains rapides",
        "quickWin": "gain rapide",
        "structuralOne": "changement structurel",
        "axesOne": "axe à améliorer",
        "structural": "changements structurels",
        "axes": "axes à améliorer",
        "lockLabel": "Feuille de route partagée lors de votre session expert",
        "modalTitle": "Réservez votre session expert",
        "close": "Fermer",
        "newTab": "ouvre la page de réservation",
        "openNewTab": "Ouvrir dans un nouvel onglet",
    },
}


@dataclass(frozen=True)
class ExpertBooking:
    url: str
    name: str
    title: dict[str, str]
    photo_url: str | None

    @property
    def initials(self) -> str:
        parts = [part for part in self.name.split() if part]
        if not parts:
            return ""
        return (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()


def _normalized_booking_url(url: str) -> str | None:
    """Return a canonical https://cal.com URL, or None for anything a browser could read differently."""
    if not url or "\\" in url or any(ch.isspace() for ch in url):
        return None
    parsed = urlparse(url)
    try:
        port = parsed.port
    except ValueError:
        return None
    if parsed.scheme != "https" or parsed.hostname not in BOOKING_HOSTS or parsed.username or parsed.password or port is not None:
        return None
    if parsed.path.strip("/") == "":
        return None
    return urlunparse(("https", parsed.hostname, parsed.path, "", parsed.query, ""))


def expert_booking_config() -> ExpertBooking | None:
    url = _normalized_booking_url(os.environ.get("EXPERT_BOOKING_URL", DEFAULT_BOOKING_URL).strip())
    if url is None:
        return None
    photo = os.environ.get("EXPERT_PHOTO_URL", "").strip()
    return ExpertBooking(
        url=url,
        name=os.environ.get("EXPERT_NAME", "").strip() or DEFAULT_EXPERT_NAME,
        title=dict(EXPERT_TITLE),
        photo_url=photo if photo.startswith("https://") else None,
    )


def teaser_counts(findings: Iterable[Any]) -> dict[str, int]:
    seen: set[str] = set()
    quick = structural = 0
    axes: set[str] = set()
    for index, item in enumerate(findings or []):
        if not isinstance(item, dict):
            continue
        if str(item.get("outcome") or item.get("status") or "fail").lower() in NON_FAILING:
            continue
        identity = str(item.get("deduplicationId") or item.get("findingId") or item.get("id") or f"row-{index}")
        if identity in seen:
            continue
        seen.add(identity)
        severity = str(item.get("severity") or "").lower()
        if severity in STRUCTURAL:
            structural += 1
        elif severity in QUICK_WIN:
            quick += 1
        else:
            continue
        axis = item.get("axisId") or item.get("axis")
        if axis:
            axes.add(str(axis))
    return {"quickWins": quick, "structural": structural, "axes": len(axes)}


def findings_from_report(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the report's full finding list, else axis pain points tagged with their axis."""
    for key in ("allFindings", "findings", "deduplicatedFindings"):
        if isinstance(payload.get(key), list) and payload[key]:
            return list(payload[key])
    return [
        {**point, "axisId": point.get("axisId") or axis.get("id")}
        for axis in payload.get("axes") or [] if isinstance(axis, dict)
        for point in axis.get("painPoints") or [] if isinstance(point, dict)
    ]


def teaser_copy(lang: str) -> dict[str, str]:
    return dict(COPY.get(str(lang or "").lower(), COPY["en"]))


def _lang(lang: str) -> str:
    return str(lang or "").lower() if str(lang or "").lower() in COPY else "en"


def booking_url(base: str, *, site_url: str, report_url: str | None, embed: bool) -> str:
    parsed = urlparse(base)
    query = parse_qsl(parsed.query, keep_blank_values=True)
    notes = f"UX/UI audit: {site_url}" + (f" — Report: {report_url}" if report_url else "")
    query.append(("notes", notes))
    if embed:
        query.append(("embed", "true"))
    return urlunparse(parsed._replace(query=urlencode(query)))


def teaser_payload(findings: Iterable[Any], *, lang: str, site_url: str, report_url: str | None) -> dict[str, Any] | None:
    config = expert_booking_config()
    if config is None:
        return None
    code = _lang(lang)
    return {
        "enabled": True,
        "lang": code,
        "counts": teaser_counts(findings),
        "copy": teaser_copy(code),
        "expert": {"name": config.name, "title": config.title[code], "photoUrl": config.photo_url, "initials": config.initials},
        "bookingUrl": booking_url(config.url, site_url=site_url, report_url=report_url, embed=False),
        "embedUrl": booking_url(config.url, site_url=site_url, report_url=report_url, embed=True),
    }


def render_roadmap_teaser_html(findings: Iterable[Any], *, lang: str, site_url: str, report_url: str | None = None) -> str:
    payload = teaser_payload(findings, lang=lang, site_url=site_url, report_url=report_url)
    if payload is None:
        return ""
    esc = lambda value: html.escape(str(value), quote=True)  # noqa: E731
    copy, counts, expert = payload["copy"], payload["counts"], payload["expert"]
    has_findings = counts["quickWins"] + counts["structural"] > 0
    heading = copy["heading"] if has_findings else copy["cleanHeading"]
    body = copy["body"] if has_findings else copy["cleanBody"]
    chips = "".join(
        f'<li class="rt-chip"><strong>{counts[key]}</strong> {esc(copy[one] if counts[key] == 1 else copy[key])}</li>'
        for key, one in CHIP_LABELS if counts[key]
    ) if has_findings else ""
    rows = "".join(
        f'<div class="rt-row"><span class="rt-dot rt-dot-{i}"></span><span class="rt-bar" style="width:{w}%"></span>'
        f'<span class="rt-pill"></span></div>'
        for i, w in enumerate((72, 58, 81, 46))
    )
    avatar = (f'<img class="rt-avatar" src="{esc(expert["photoUrl"])}" alt="">' if expert["photoUrl"]
              else f'<span class="rt-avatar" aria-hidden="true">{esc(expert["initials"])}</span>')
    return f"""<section id="roadmap-teaser" class="rt" lang="{payload['lang']}" aria-labelledby="rt-heading">
<style>{_stylesheet()}</style>
<div class="rt-card">
  <div class="rt-stage">
    <div class="rt-preview" aria-hidden="true"><div class="rt-rows">{rows}</div></div>
    <div class="rt-lock"><span class="rt-lock-icon" aria-hidden="true">{_LOCK_SVG}</span><span>{esc(copy['lockLabel'])}</span></div>
  </div>
  <div class="rt-content">
    <p class="rt-eyebrow">{esc(copy['eyebrow'])}</p>
    <h2 id="rt-heading">{esc(heading)}</h2>
    <p class="rt-body">{esc(body)}</p>
    {f'<ul class="rt-chips">{chips}</ul>' if chips else ''}
    <div class="rt-footer">
      <div class="rt-expert">{avatar}<div><p class="rt-name">{esc(expert['name'])}</p><p class="rt-title">{esc(expert['title'])}</p></div></div>
      <a class="rt-cta" data-rt-cta href="{esc(payload['bookingUrl'])}" target="_blank" rel="noopener">{esc(copy['cta'])}<span class="rt-sr"> ({esc(copy['newTab'])})</span><span aria-hidden="true" class="rt-arrow">→</span></a>
    </div>
  </div>
</div>
<dialog class="rt-dialog" aria-labelledby="rt-dialog-title">
  <div class="rt-dialog-head"><h2 id="rt-dialog-title">{esc(copy['modalTitle'])}</h2><div class="rt-dialog-actions"><a class="rt-newtab" href="{esc(payload['bookingUrl'])}" target="_blank" rel="noopener">{esc(copy['openNewTab'])}</a><button type="button" class="rt-close" data-rt-close>{esc(copy['close'])}</button></div></div>
  <iframe class="rt-frame" title="{esc(copy['modalTitle'])}" data-src="{esc(payload['embedUrl'])}" loading="lazy"></iframe>
</dialog>
<script>{_JS}</script>
</section>"""


@lru_cache(maxsize=1)
def _stylesheet() -> str:
    return STYLESHEET_PATH.read_text(encoding="utf-8").strip()


_LOCK_SVG = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>'


_JS = """(function(){var s=document.currentScript&&document.currentScript.parentNode;if(!s||!s.querySelector)return;
var a=s.querySelector('[data-rt-cta]'),d=s.querySelector('dialog'),c=s.querySelector('[data-rt-close]'),f=s.querySelector('iframe');
function t(e){if(window.dataLayer&&window.dataLayer.push)window.dataLayer.push({event:e});}
if('IntersectionObserver' in window){var o=new IntersectionObserver(function(es){if(es.some(function(x){return x.isIntersecting;})){t('roadmap_teaser_viewed');o.disconnect();}},{threshold:.4});o.observe(s);}
if(!a||!d||typeof d.showModal!=='function')return;
a.addEventListener('click',function(e){t('booking_cta_clicked');e.preventDefault();if(!f.getAttribute('src'))f.setAttribute('src',f.getAttribute('data-src'));d.showModal();c.focus();});
c.addEventListener('click',function(){d.close();});
d.addEventListener('click',function(e){if(e.target===d)d.close();});
d.addEventListener('close',function(){a.focus();});
window.addEventListener('message',function(e){if(!/^https:\\/\\/(app\\.)?cal\\.com$/.test(e.origin))return;var m=e.data&&(e.data.type||e.data.action||(e.data.data&&e.data.data.type))||'';if(String(m).indexOf('bookingSuccessful')!==-1)t('booking_completed');});
})();"""
