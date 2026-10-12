import { useEffect, useState } from "react";
import Icon from "../components/Icon.jsx";
import Icon3D from "../components/Icon3D.jsx";
import DotField from "./DotField.jsx";
import HowItWorks from "./HowItWorks.jsx";
import Reveal from "./Reveal.jsx";
import useInView from "./useInView.js";
import capture from "./assets/w3c-bad-citylights.jpg";
import logo from "../assets/ey-studio-plus.png";

// The seven methodology v3 axes. Names, core questions and criterion counts mirror
// shared/config/audit_methodology_v3.json (tests/test_landing_copy.py keeps them in sync).
const AXES = [
  { id: "usability", short: { en: "Usability", fr: "Utilisabilité" }, name: { en: "Usability & Task Flow", fr: "Utilisabilité et parcours de tâche" }, question: { en: "Can users complete their key tasks efficiently, with clear feedback and easy recovery from errors?", fr: "Les utilisateurs peuvent-ils accomplir leurs tâches clés efficacement, avec un retour clair et une récupération facile en cas d'erreur ?" }, criteria: 10, standards: ["NN/g", "Baymard", "WCAG 2.2"] },
  { id: "navigation", short: { en: "Navigation", fr: "Navigation" }, name: { en: "Information Architecture & Navigation", fr: "Architecture de l'information et navigation" }, question: { en: "Can users find what they need and always know where they are and how to get back?", fr: "Les utilisateurs trouvent-ils ce qu'ils cherchent et savent-ils toujours où ils sont et comment revenir en arrière ?" }, criteria: 9, standards: ["NN/g", "Baymard", "WCAG 2.2"] },
  { id: "visual", short: { en: "Visual design", fr: "Design visuel" }, name: { en: "Visual Design & Hierarchy", fr: "Design visuel et hiérarchie" }, question: { en: "Does the visual design make priorities obvious and stay consistent across the interface?", fr: "Le design visuel rend-il les priorités évidentes et reste-t-il cohérent dans toute l'interface ?" }, criteria: 10, standards: ["Gestalt", "ISO 9241", "NN/g"] },
  { id: "content", short: { en: "Content", fr: "Contenu" }, name: { en: "Content & Microcopy", fr: "Contenu et microcopie" }, question: { en: "Is the text plain, scannable, and specific enough for users to act with confidence?", fr: "Le texte est-il simple, lisible en diagonale et assez précis pour que l'utilisateur agisse en confiance ?" }, criteria: 8, standards: ["NN/g", "Baymard", "ISO 9241"] },
  { id: "accessibility", short: { en: "Accessibility", fr: "Accessibilité" }, name: { en: "Accessibility & Inclusion", fr: "Accessibilité et inclusion" }, question: { en: "Can people with disabilities perceive, operate, and understand the interface (WCAG 2.2 AA)?", fr: "Les personnes en situation de handicap peuvent-elles percevoir, utiliser et comprendre l'interface (WCAG 2.2 AA) ?" }, criteria: 12, standards: ["WCAG 2.2", "axe-core"] },
  { id: "performance", short: { en: "Performance", fr: "Performance" }, name: { en: "Performance & Responsiveness", fr: "Performance et adaptabilité" }, question: { en: "Does the interface load and respond fast, and adapt properly to every screen size?", fr: "L'interface se charge-t-elle et répond-elle rapidement, et s'adapte-t-elle correctement à chaque taille d'écran ?" }, criteria: 9, standards: ["Core Web Vitals", "WCAG 2.2", "NN/g"] },
  { id: "trust", short: { en: "Trust", fr: "Confiance" }, name: { en: "Trust & Credibility", fr: "Confiance et crédibilité" }, question: { en: "Does the product earn trust through transparency, honest design, and credible signals?", fr: "Le produit gagne-t-il la confiance par la transparence, un design honnête et des signaux crédibles ?" }, criteria: 9, standards: ["Stanford Web Credibility", "Baymard", "NN/g"] },
];
const CRITERIA_TOTAL = AXES.reduce((sum, axis) => sum + axis.criteria, 0);

// Real capture of W3C's Before-and-After Demonstration (inaccessible home page). One finding per axis that the
// capture can show: the contrast result is measured by axe-core 4.11 (assets/w3c-bad-axe.json); the others are expert
// observations of what is visible. Performance and trust need the live site, so the demo raises nothing on them.
// Boxes are element bounds in the 780×560 capture.
const W = 780, H = 560, SCAN_MS = 3000;
const FINDINGS = [
  { axis: "usability", severity: "high", measured: false, box: [626, 33, 145, 19], text: { en: "Quick menu is a bare dropdown with no label or Go button", fr: "Le menu rapide est une liste déroulante sans libellé ni bouton Valider" } },
  { axis: "visual", severity: "low", measured: false, box: [175, 144, 434, 69], text: { en: "Three competing type styles in one column", fr: "Trois styles typographiques concurrents dans une même colonne" } },
  { axis: "navigation", severity: "medium", measured: false, box: [0, 146, 155, 140], below: true, text: { en: "Menu doesn’t show which page you’re on", fr: "Le menu n’indique pas la page en cours" } },
  { axis: "accessibility", severity: "high", measured: true, box: [635, 149, 104, 16], text: { en: "Contrast 3.88:1, needs 4.5:1", fr: "Contraste de 3,88:1, 4,5:1 requis" } },
  { axis: "content", severity: "medium", measured: false, box: [180, 487, 48, 16], below: true, text: { en: "“MORE” links don’t say where they lead", fr: "Les liens « MORE » n’indiquent pas leur destination" } },
].map(item => ({ ...item, delay: 250 + Math.round(item.box[1] / H * SCAN_MS) }));
const SHORT = Object.fromEntries(AXES.map(axis => [axis.id, axis.short]));

const LANGS = { en: "English", fr: "Français" };
const COPY = {
  en: {
    title: "UX/UI Audit Tool with Evidence for Every Finding | EY Studio+",
    description: `Audit websites, apps and Figma files on 7 UX axes and ${CRITERIA_TOTAL} criteria: usability, navigation, visual design, content, WCAG 2.2 accessibility, performance and trust.`,
    locale: "en_US", skip: "Skip to content", home: "EY Studio Plus home", language: "Language",
    eyebrow: "UX/UI audit tool",
    h1: ["UX/UI audits you can trace back to ", "evidence", "."],
    lead: "Point it at a website, app or Figma file. It captures the screens, checks them against 7 UX axes and pins every issue to the element behind it, ready for expert review.",
    cta: "Start an audit",
    sources: "Website, screenshots, Android app or Figma",
    sourceLabels: { website: "Website", screenshot: "Screenshots", mobile: "Android app", figma: "Figma" },
    alt: "Home page of Citylights, W3C’s intentionally inaccessible demonstration site.",
    running: "Auditing 7 UX axes…", done: "UX/UI audit complete", axesList: "Axes checked",
    severity: { high: "High", medium: "Medium", low: "Low" },
    expert: "Expert review", measured: "Measured · axe-core",
    tally: <><b>5</b> issues across 7 axes</>, replay: "Replay",
    caption: "Real capture of W3C’s Before-and-After Demonstration (inaccessible version). Contrast is measured by axe-core 4.11; the other findings are expert review of this capture.",
    openApp: "Open the app", seeIt: "See it work",
    howTitle: "How every audit is built",
    steps: [
      ["Capture every screen.", "Point it at a URL, screenshots, an Android app or a Figma file. It records each screen and the elements on it."],
      [`Check 7 axes, ${CRITERIA_TOTAL} criteria.`, "Automated tools measure what can be measured; the AI agent reviews the rest and keeps a finding only with 80% confidence and cited evidence. Each axis is scored out of 100."],
      ["A specialist signs off.", "Every finding is reviewed before the report is published, in the app, as a shareable link and as a PDF."],
    ],
    closing: "See the evidence behind your product’s UX.",
    coverage: "Coverage", flow: ["Draft", "Saved", "Deployed"],
    axesTitle: "What every UX/UI audit checks",
    axesLead: `7 axes and ${CRITERIA_TOTAL} criteria grounded in WCAG 2.2, Nielsen Norman Group heuristics, Baymard research and Core Web Vitals. Each axis is scored out of 100 and rated from 1 (Critical) to 5 (Excellent).`,
    criteria: count => `${count} criteria`,
    footer: ["Built around evidence. Refined by human judgment.", "Automated checks support a WCAG review; they don’t replace it."],
  },
  fr: {
    title: "Outil d’audit UX/UI fondé sur des preuves | EY Studio+",
    description: `Auditez sites, applications et maquettes Figma sur 7 axes UX et ${CRITERIA_TOTAL} critères : utilisabilité, navigation, design, contenu, accessibilité WCAG 2.2, performance, confiance.`,
    locale: "fr_FR", skip: "Aller au contenu", home: "Accueil EY Studio Plus", language: "Langue",
    eyebrow: "Outil d’audit UX/UI",
    h1: ["Des audits UX/UI fondés sur des ", "preuves", "."],
    lead: "Indiquez un site, une application ou un fichier Figma. L’outil capture les écrans, les évalue sur 7 axes UX et rattache chaque problème à l’élément concerné, prêt pour la revue d’un expert.",
    cta: "Lancer un audit",
    sources: "Site web, captures d’écran, app Android ou Figma",
    sourceLabels: { website: "Site web", screenshot: "Captures d’écran", mobile: "App Android", figma: "Figma" },
    alt: "Page d’accueil de Citylights, site de démonstration volontairement inaccessible du W3C.",
    running: "Analyse des 7 axes UX…", done: "Audit UX/UI terminé", axesList: "Axes vérifiés",
    severity: { high: "Élevée", medium: "Moyenne", low: "Faible" },
    expert: "Revue d’expert", measured: "Mesuré · axe-core",
    tally: <><b>5</b> problèmes sur 7 axes</>, replay: "Rejouer",
    caption: "Capture réelle de la démonstration Avant/Après du W3C (version inaccessible). Le contraste est mesuré par axe-core 4.11 ; les autres constats relèvent d’une revue d’expert de cette capture.",
    openApp: "Ouvrir l’application", seeIt: "Voir l’audit en action",
    howTitle: "Comment chaque audit est construit",
    steps: [
      ["Capturer chaque écran.", "Indiquez une URL, des captures, une app Android ou un fichier Figma. L’outil enregistre chaque écran et ses éléments."],
      [`Vérifier 7 axes, ${CRITERIA_TOTAL} critères.`, "Les outils automatisés mesurent ce qui est mesurable ; l’agent IA examine le reste et ne retient un constat qu’avec 80 % de confiance et une preuve citée. Chaque axe est noté sur 100."],
      ["Validé par un spécialiste.", "Chaque constat est relu avant publication : dans l’application, en lien partageable et en PDF."],
    ],
    closing: "Voyez les preuves derrière l’UX de votre produit.",
    coverage: "Couverture", flow: ["Brouillon", "Enregistré", "Publié"],
    axesTitle: "Ce que vérifie chaque audit UX/UI",
    axesLead: `7 axes et ${CRITERIA_TOTAL} critères fondés sur les WCAG 2.2, les heuristiques de Nielsen Norman Group, les recherches Baymard et les Core Web Vitals. Chaque axe est noté sur 100 et classé de 1 (Critique) à 5 (Excellent).`,
    criteria: count => `${count} critères`,
    footer: ["Fondé sur des preuves. Affiné par le jugement humain.", "Les contrôles automatisés appuient une revue WCAG ; ils ne la remplacent pas."],
  },
};
const SOURCES = ["website", "screenshot", "mobile", "figma"];

const langHref = lang => (lang === "en" ? "/" : `/?lang=${lang}`);

function initialLang() {
  try { const fromUrl = new URLSearchParams(window.location.search).get("lang"); if (Object.hasOwn(LANGS, fromUrl ?? "")) return fromUrl; } catch { /* default below */ }
  try { const saved = window.localStorage.getItem("lang"); if (Object.hasOwn(LANGS, saved ?? "")) return saved; } catch { /* default below */ }
  try { return navigator.language.toLowerCase().startsWith("fr") ? "fr" : "en"; } catch { return "en"; }
}

function headTag(tag, attrs) {
  const selector = tag + Object.entries(attrs).filter(([key]) => key !== "content" && key !== "href").map(([key, value]) => `[${key}="${value}"]`).join("");
  let node = document.head.querySelector(selector);
  if (!node) { node = document.createElement(tag); document.head.appendChild(node); }
  Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
}

// Language, title, description, social tags, canonical and hreflang alternates follow the chosen language.
function useDocumentHead(lang, t) {
  useEffect(() => {
    const origin = window.location.origin;
    document.documentElement.lang = lang;
    document.title = t.title;
    headTag("meta", { name: "description", content: t.description });
    headTag("meta", { property: "og:title", content: t.title });
    headTag("meta", { property: "og:description", content: t.description });
    headTag("meta", { property: "og:locale", content: t.locale });
    headTag("meta", { property: "og:url", content: origin + langHref(lang) });
    headTag("link", { rel: "canonical", href: origin + langHref(lang) });
    Object.keys(LANGS).forEach(code => headTag("link", { rel: "alternate", hreflang: code, href: origin + langHref(code) }));
    headTag("link", { rel: "alternate", hreflang: "x-default", href: origin + "/" });
  }, [lang, t]);
}

function reducedMotion() {
  try { return window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch { return false; }
}

function AuditDemo({ lang, t }) {
  const [run, setRun] = useState(0);
  const [done, setDone] = useState(reducedMotion);
  // The scan waits until the capture itself is 40% visible: the whole figure can be taller than a phone screen.
  const [frameRef, seen] = useInView({ threshold: .4, once: true });
  useEffect(() => {
    if (reducedMotion()) { setDone(true); return undefined; }
    setDone(false);
    if (!seen) return undefined;
    const timer = setTimeout(() => setDone(true), SCAN_MS + 600);
    return () => clearTimeout(timer);
  }, [run, seen]);
  const pct = (value, total) => `${(value / total) * 100}%`;
  return <figure className={`lp-demo ${done ? "is-done" : seen ? "is-running" : "is-idle is-running"}`} key={run}>
    <div className="lp-browser" ref={frameRef}>
      <div className="lp-browser-bar" aria-hidden="true"><i/><i/><i/><span>citylights · W3C demo site</span></div>
      <div className="lp-shot">
        <img src={capture} width={W} height={H} alt={t.alt}/>
        <span className="lp-scan" aria-hidden="true"/>
        {FINDINGS.map(({ axis, box: [x, y, w, h], delay, below }) => <span key={axis} className={`lp-box ${below ? "is-below" : ""}`} aria-hidden="true" style={{ left: pct(x, W), top: pct(y, H), width: pct(w, W), height: pct(h, H), animationDelay: `${delay}ms` }}><b>{SHORT[axis][lang]}</b></span>)}
      </div>
    </div>
    <div className="lp-log">
      <p className="lp-log-status" role="status">{done ? <><Icon name="check" size={14}/> {t.done}</> : <><span className="lp-spinner" aria-hidden="true"/> {t.running}</>}</p>
      <ul className="lp-dims" aria-label={t.axesList}>{AXES.map(axis => { const hit = FINDINGS.find(item => item.axis === axis.id); return <li key={axis.id} className={hit ? "" : "is-clear"} style={{ animationDelay: `${hit ? hit.delay : SCAN_MS}ms` }}>{axis.short[lang]}</li>; })}</ul>
      <ol>{FINDINGS.map(({ axis, text, severity, measured, delay }) => <li key={axis} style={{ animationDelay: `${delay}ms` }}><span className={`lp-impact is-${severity}`}>{t.severity[severity]}</span><span className="lp-row-dim">{SHORT[axis][lang]}</span><strong>{text[lang]}</strong><span className="lp-wcag">{measured ? t.measured : t.expert}</span></li>)}</ol>
      <div className="lp-log-foot"><span>{t.tally}</span><button type="button" onClick={() => setRun(value => value + 1)} disabled={!done}>{t.replay}</button></div>
    </div>
    <figcaption>{t.caption}</figcaption>
  </figure>;
}

function structuredData(lang, t) {
  return JSON.stringify({
    "@context": "https://schema.org", "@type": "SoftwareApplication", name: "EY Studio+ UX/UI Auditor",
    applicationCategory: "BusinessApplication", operatingSystem: "Web", inLanguage: lang, description: t.description,
    featureList: AXES.map(axis => axis.name[lang]),
  });
}

export default function Landing() {
  const [lang, setLang] = useState(initialLang);
  const t = COPY[lang];
  useDocumentHead(lang, t);
  // The header turns solid as soon as the page scrolls, before the headline can slide under it.
  const [topRef, atTop] = useInView();
  const chooseLang = (event, code) => {
    event.preventDefault();
    setLang(code);
    try { window.localStorage.setItem("lang", code); } catch { /* the choice still applies to this visit */ }
    try { window.history.replaceState(null, "", langHref(code)); } catch { /* URL stays as is */ }
  };
  return <div className="lp">
    <script type="application/ld+json">{structuredData(lang, t)}</script>
    <span className="lp-top" ref={topRef} aria-hidden="true"/>
    <a className="skip-link" href="#main-content">{t.skip}</a>
    <header className={`lp-header ${atTop ? "" : "is-solid"}`}>
      <div className="lp-wrap lp-header-inner">
        <a className="brand lp-brand" href={langHref(lang)} aria-label={t.home}><img className="brand-logo" src={logo} alt="" width="1000" height="390"/></a>
        <div className="lp-header-actions">
          <nav className="lp-lang" aria-label={t.language}>{Object.entries(LANGS).map(([code, label]) => <a key={code} href={langHref(code)} hrefLang={code} lang={code} aria-label={label} aria-current={code === lang ? "true" : undefined} onClick={event => chooseLang(event, code)}>{code.toUpperCase()}</a>)}</nav>
          <a className="lp-open" href="/app">{t.openApp}</a>
        </div>
      </div>
    </header>
    <main id="main-content" tabIndex={-1} className="lp-main">
      <section className="lp-hero" aria-labelledby="lp-title">
        <DotField variant="hero"/>
        <div className="lp-intro">
          <p className="lp-eyebrow"><span aria-hidden="true"/>{t.eyebrow}</p>
          <h1 id="lp-title">{t.h1[0]}<span className="lp-word">{t.h1[1]}<i/><i/><i/><i/></span>{t.h1[2]}</h1>
          <p className="lp-lead">{t.lead}</p>
          <div className="lp-actions">
            <a className="lp-cta" href="/app">{t.cta}<Icon name="arrow" size={18}/></a>
            <a className="lp-ghost" href="#demo">{t.seeIt}</a>
          </div>
          <div className="lp-sources"><span>{t.sources}</span><ul>{SOURCES.map(id => <li key={id} title={t.sourceLabels[id]}><Icon3D name={id} size={30}/><span className="sr-only">{t.sourceLabels[id]}</span></li>)}</ul></div>
        </div>
      </section>
      <section id="demo" className="lp-wrap lp-demo-section" aria-labelledby="lp-demo-title">
        <h2 id="lp-demo-title" className="sr-only">{t.seeIt}</h2>
        <AuditDemo lang={lang} t={t}/>
      </section>
      <HowItWorks lang={lang} t={t} axes={AXES}/>
      <section className="lp-wrap lp-axes" aria-labelledby="lp-axes-title">
        <Reveal as="h2" id="lp-axes-title">{t.axesTitle}</Reveal>
        <Reveal as="p" className="lp-axes-lead">{t.axesLead}</Reveal>
        <Reveal as="ol">{AXES.map((axis, index) => <li key={axis.id} style={{ "--i": index }}><h3>{axis.name[lang]}</h3><p>{axis.question[lang]}</p><p className="lp-axis-meta">{t.criteria(axis.criteria)} · {axis.standards.join(" · ")}</p></li>)}</Reveal>
      </section>
      <section className="lp-closing" aria-labelledby="lp-closing-title">
        <DotField variant="quiet"/>
        <Reveal as="h2" id="lp-closing-title">{t.closing}</Reveal>
        <a className="lp-cta" href="/app">{t.cta}<Icon name="arrow" size={18}/></a>
      </section>
    </main>
    <footer className="lp-footer">
      <div className="lp-wrap lp-footer-lines"><span>{t.footer[0]}</span><span>{t.footer[1]}</span></div>
      <span className="lp-wordmark" aria-hidden="true"/>
    </footer>
  </div>;
}
