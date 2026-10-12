import { useEffect, useState } from "react";
import { createAudit } from "../api/audits.js";
import { Button, Disclosure, ErrorAlert, Field, InlineAlert } from "../components/Primitives.jsx";
import Icon from "../components/Icon.jsx";
import AuditTypeSelector from "./AuditTypeSelector.jsx";
import ScreenshotUpload from "./ScreenshotUpload.jsx";
import MobileFields from "./MobileFields.jsx";
export default function AuditForm({ api, onCreated, beforeCreate, activeJob }) {
  const [kind, setKind] = useState("website");
  const [values, setValues] = useState({ mode: "gtm", depth: "quick", url: "", figmaUrl: "", siteName: "", files: [], surfaceType: "website", appiumUrl: "http://127.0.0.1:4723" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [capabilities, setCapabilities] = useState(null);
  const [capError, setCapError] = useState(null);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let live = true; setCapError(null);
    api.request("/api/capabilities").then(r => api.json(r, "Unable to check available audit modes.")).then(data => { if (live) setCapabilities(data); }).catch(e => { if (live) setCapError(e); });
    return () => { live = false; };
  }, [api, retry]);
  const signedOut = capError?.status === 401 || capError?.status === 403;
  const recheck = <Button variant="quiet" onClick={() => setRetry(x => x + 1)}>{signedOut ? "I’ve signed in, check again" : "Try again"}</Button>;
  const update = e => setValues(old => ({ ...old, [e.target.name]: e.target.value }));
  async function submit(e) {
    e.preventDefault(); setError(null);
    if (kind === "screenshot" && !values.files.length) { setError(new Error("Choose at least one screenshot before starting.")); return; }
    if (!beforeCreate()) return;
    setBusy(true);
    try { onCreated(await createAudit(api, kind, { ...values, mode: capabilities?.detailedAuditAvailable === true ? values.mode : "gtm" })); }
    catch (err) { setError(err); } finally { setBusy(false); }
  }
  const descriptions = { website: "Start with a website URL. We’ll examine representative pages and gather evidence for your review.", screenshot: "Upload the screens you want to assess. Findings are based on visible content, not live behavior.", mobile: "Explore an Android app on a connected device, with evidence captured along the way.", figma: "Analyze design structure and rendered surfaces in a Figma file. Runtime behavior is outside this audit’s scope." };
  return <><div className="page-heading"><p className="eyebrow">UX/UI Auditor</p><h1>New audit</h1><p>Choose a source. Collect evidence. Review the findings.</p></div><form className={`audit-form ${busy ? "is-starting" : ""}`} onSubmit={submit} aria-busy={busy}><fieldset disabled={busy} className="form-body"><AuditTypeSelector value={kind} onChange={value => { setKind(value); setError(null); }}/><section className="setup-panel surface" aria-labelledby="configure-title"><div className="setup-main"><div className="section-heading"><h2 id="configure-title"><span className="step-number">2</span> {kind === "website" ? "Where should we look?" : kind === "screenshot" ? "Add your screenshots" : kind === "mobile" ? "Connect to your app" : "Add your design file"}</h2><p>{descriptions[kind]}</p></div><div className="configuration" key={kind}>{kind === "website" && <><Field label="Website URL" className="url-input" hint="Use a public website beginning with https:// or http://." required name="url" type="url" autoComplete="url" placeholder="https://example.com" value={values.url} onChange={update}/><DepthChoice value={values.depth} onChange={depth => setValues(old => ({ ...old, depth }))}/>{capabilities?.detailedAuditAvailable === true && <Disclosure title="Advanced · audit mode"><Field label="Audit mode" as="select" name="mode" value={values.mode} onChange={update}><option value="gtm">Website audit</option><option value="detailed">Detailed · workbook audit</option></Field></Disclosure>}{capError && !signedOut && <InlineAlert tone="warning" title="Advanced audit modes are unavailable" details={capError.message} action={recheck}>You can still run a standard website audit.</InlineAlert>}</>}{kind === "screenshot" && <><ScreenshotUpload files={values.files} onChange={files => setValues(old => ({ ...old, files }))}/><div className="field-grid"><Field label="Audit name (optional)" name="siteName" value={values.siteName} onChange={update} placeholder="For example, checkout flow"/><Field label="Screen type" name="surfaceType" as="select" value={values.surfaceType} onChange={update}><option value="website">Website</option><option value="mobile_app">Mobile app</option></Field></div></>}{kind === "figma" && <Field label="Figma file URL" className="url-input" hint="The audit server needs a Figma token with access to this file." required name="figmaUrl" type="url" placeholder="https://www.figma.com/design/…" value={values.figmaUrl} onChange={update}/>} {kind === "mobile" && <MobileFields api={api} values={values} setValues={setValues} update={update}/>}{signedOut && <InlineAlert title="Sign in to start an audit" action={recheck}>Your session has expired or you aren’t signed in. Sign in through your portal, then come back to this page.</InlineAlert>}<ErrorAlert error={error} title="Couldn’t start this audit"/>{activeJob && <InlineAlert tone="info" title="An audit is already in progress">Return to Current audit to follow its progress or cancel it before starting another.</InlineAlert>}</div><div className="form-footer"><span>{busy ? "Creating your audit…" : signedOut ? "Sign in to continue." : "Review your report before publication."}</span><Button variant="primary" type="submit" disabled={busy || activeJob || signedOut}>{busy ? "Starting…" : "Start audit"}<Icon name="arrow" size={18}/></Button></div></div></section></fieldset></form></>;
}
const DEPTHS = [
  { id: "quick", name: "Quick", description: "Homepage and one menu page · about 1 minute" },
  { id: "deep", name: "Deep", description: "Up to 10 pages · a few minutes" },
];
function DepthChoice({ value, onChange }) {
  return <fieldset className="depth-options"><legend>Audit depth</legend>{DEPTHS.map(depth => <label key={depth.id} className={`depth-option ${value === depth.id ? "is-selected" : ""}`}><input type="radio" name="depth" value={depth.id} checked={value === depth.id} onChange={() => onChange(depth.id)}/><span><strong>{depth.name}</strong><span>{depth.description}</span></span></label>)}</fieldset>;
}
