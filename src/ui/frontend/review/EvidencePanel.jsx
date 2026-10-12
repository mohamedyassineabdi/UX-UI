import { useEffect, useState } from "react";
import { evidencePath } from "../api/artifacts.js";
import { Disclosure } from "../components/Primitives.jsx";
import ProtectedResource from "../components/ProtectedResource.jsx";
import { ReadableValue } from "../components/ReadableRecord.jsx";
export const evidenceText = value => typeof value === "string" ? value : Array.isArray(value) && value.every(item => typeof item === "string") ? value.join("\n") : value == null ? "" : JSON.stringify(value, null, 2);
export default function EvidencePanel({ api, job, finding }) {
  const path = evidencePath(finding.screenshotPath || finding.screenshot_path || finding.visual_evidence?.[0]?.image_path, job);
  const [image, setImage] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let live = true, objectUrl;
    setImage(null); setError("");
    if (path) api.request(path).then(async response => {
      if (!response.ok) throw new Error("The captured image is unavailable for this session.");
      const blob = await response.blob();
      if (!/^image\/(png|jpeg|webp|gif)$/.test(blob.type)) throw new Error("This artifact cannot be previewed as an image.");
      objectUrl = URL.createObjectURL(blob);
      if (live) setImage(objectUrl);
      else URL.revokeObjectURL(objectUrl);
    }).catch(e => { if (live) setError(e.message); });
    return () => { live = false; if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [api, path]);
  const bundle = finding.evidenceBundle;
  const pageUrl = finding.pageUrl || finding.page_url;
  const origin = bundle?.source || finding.measurementMethod || finding.sourceSheet || (finding.aiDiscovered ? "AI-discovered observation" : "Source report");
  return <section className="evidence-panel" aria-label="Finding evidence"><div className="section-row"><h3>Observation & evidence</h3><span className="metadata">{evidenceText(origin)}</span></div>
    {pageUrl && /^https?:\/\//i.test(pageUrl) && <a className="evidence-url" href={pageUrl} target="_blank" rel="noreferrer">{pageUrl} ↗</a>}
    {path && <figure className="evidence-image">{image ? <img src={image} alt={`Captured interface for ${finding.title || finding.message || "this finding"}. Inspect the evidence text for the reported issue.`}/> : <p role="status">{error || "Loading captured evidence…"}</p>}<figcaption>Captured artifact <ProtectedResource api={api} path={path}>Open captured image</ProtectedResource></figcaption></figure>}
    {!path && (finding.screenshotPath || finding.visual_evidence?.length > 0) && <p className="section-caption">The referenced image is not available through this audit’s protected artifacts.</p>}
    <p className="evidence-observation">{evidenceText(finding.evidence || finding.visibleSignals) || "No observation text was supplied. Inspect the source report for supporting context."}</p>
    {(bundle || finding.evidenceIds || finding.sources || finding.wcagCriterion || finding.visualRegion) && <Disclosure title="Evidence provenance & check details"><dl className="provenance">{[["Evidence IDs", finding.evidenceIds], ["Sources", finding.sources], ["WCAG criterion", finding.wcagCriterion || bundle?.criterion], ["Target / selector", bundle?.target], ["Visual region", finding.visualRegion], ["Measurement class", finding.measurementClass], ["Check details", bundle?.raw], ["Limitations", finding.limitations]].filter(([, value]) => value != null).map(([label, value]) => <div key={label}><dt>{label}</dt><dd><ReadableValue value={value}/></dd></div>)}</dl></Disclosure>}
  </section>;
}
