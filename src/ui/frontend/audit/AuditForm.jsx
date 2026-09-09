import { useState } from "react";
import { createAudit } from "../api/audits.js";

export default function AuditForm({ api, onCreated, onError }) {
  const [kind, setKind] = useState("website"); const [values, setValues] = useState({ mode: "gtm", url: "", figmaUrl: "", siteName: "" }); const [busy, setBusy] = useState(false);
  const update = (event) => setValues({ ...values, [event.target.name]: event.target.value });
  async function submit(event) { event.preventDefault(); setBusy(true); try { onCreated(await createAudit(api, kind, values)); } catch (error) { onError(error.message); } finally { setBusy(false); } }
  return <form className="card audit-form" onSubmit={submit}>
    <label>Audit type<select value={kind} onChange={(e) => setKind(e.target.value)}><option value="website">Website</option><option value="screenshot">Screenshots</option><option value="mobile">Mobile</option><option value="figma">Figma</option></select></label>
    {kind === "website" && <><label>Website URL<input required name="url" type="url" value={values.url} onChange={update} /></label><label>Mode<select name="mode" value={values.mode} onChange={update}><option value="gtm">Website audit</option></select></label></>}
    {kind === "figma" && <label>Figma URL<input required name="figmaUrl" type="url" value={values.figmaUrl} onChange={update} /></label>}
    {kind === "screenshot" && <><label>Audit name<input name="siteName" value={values.siteName} onChange={update} /></label><label>Screenshots<input required type="file" accept="image/png,image/jpeg,image/webp" multiple onChange={(e) => setValues({ ...values, files: [...e.target.files] })} /></label></>}
    {kind === "mobile" && <><label>App package<input required name="appPackage" value={values.appPackage || ""} onChange={update} /></label><label>Activity<input name="appActivity" value={values.appActivity || ""} onChange={update} /></label><label>Appium URL<input name="appiumUrl" value={values.appiumUrl || "http://127.0.0.1:4723"} onChange={update} /></label></>}
    <button disabled={busy} type="submit">{busy ? "Starting…" : "Start audit"}</button>
  </form>;
}
