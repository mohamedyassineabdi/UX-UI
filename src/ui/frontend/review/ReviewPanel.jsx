import { useMemo, useState } from "react";
import ReadableRecord from "../components/ReadableRecord.jsx";
import { findingId, machineFindings } from "../api/artifacts.js";
import { Button, Disclosure, ErrorAlert, Field, InlineAlert, StatusBadge } from "../components/Primitives.jsx";
import ProtectedResource from "../components/ProtectedResource.jsx";
import AuditOverview from "../audit/AuditOverview.jsx";
import FindingBrowser from "./FindingBrowser.jsx";
import RevisionHistory from "./RevisionHistory.jsx";
import useReview, { actionTitles } from "./useReview.js";

export default function ReviewPanel({ api, job, machine, machineLoading, onDirty, onJob }) {
  const model = useReview(api, job, onDirty, onJob);
  const [tab, setTab] = useState("overview");
  const [severity, setSeverity] = useState("");
  const [browserVersion, setBrowserVersion] = useState(0);
  const { review, changes, busy, dirty, conflict, fresh, current, revisionId, publication } = model;
  const findings = useMemo(() => {
    const list = [...machineFindings(machine)];
    for (const id of Object.keys(changes)) if (!list.some(item => findingId(item) === id)) list.push({ findingId: id, title: id });
    return list;
  }, [machine, changes]);
  const status = review?.reviewStatus || (model.failure?.action === "load" ? "Review unavailable" : "Loading review");
  const next = dirty || status === "changes_requested" || !revisionId ? "save" : status === "in_review" ? "validate" : ["validated", "approved"].includes(status) ? "publish" : "save";
  const labels = { save: "Save revision", validate: "Validate revision", publish: publication?.revisionId === revisionId && !dirty ? "Published" : "Publish reviewed report" };
  const pending = { save: "Saving…", validate: "Validating…", publish: "Publishing…" };
  function browse(level = "") { setSeverity(level); setBrowserVersion(value => value + 1); setTab("findings"); }
  function tabKey(e) {
    const tabs = ["overview", "findings", "review"];
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key)) return;
    e.preventDefault();
    const index = e.key === "Home" ? 0 : e.key === "End" ? 2 : (tabs.indexOf(tab) + (e.key === "ArrowRight" ? 1 : 2)) % 3;
    setTab(tabs[index]); document.getElementById(`tab-${tabs[index]}`)?.focus();
  }
  return <section className="audit-content">
    <div className="audit-local-toolbar"><div role="tablist" aria-label="Audit sections" onKeyDown={tabKey}>{["overview", "findings", "review"].map(name => <button role="tab" type="button" id={`tab-${name}`} aria-controls={name === "overview" ? "panel-overview" : "panel-browser"} aria-selected={tab === name} tabIndex={tab === name ? 0 : -1} key={name} onClick={() => setTab(name)}>{name[0].toUpperCase() + name.slice(1)}{name === "findings" && <span>{findings.length}</span>}{name === "review" && dirty && <span aria-label="Unsaved changes">•</span>}</button>)}</div><StatusBadge status={status}/></div>
    <div id="panel-overview" role="tabpanel" aria-labelledby="tab-overview" hidden={tab !== "overview"}>{machineLoading ? <p role="status" className="loading-message">Loading audit evidence…</p> : <AuditOverview machine={machine} findings={findings} review={review} changes={changes} onBrowse={browse}/>}</div>
    <div id="panel-browser" role="tabpanel" aria-labelledby={tab === "review" ? "tab-review" : "tab-findings"} hidden={tab === "overview"}>
      {!review && !model.failure && <p role="status">Loading review…</p>}
      {model.failure?.action === "load" && <ErrorAlert error={model.failure.error} title={actionTitles.load} action={<Button onClick={model.retry}>Retry review</Button>}/>}
      {machineLoading ? <p role="status">Loading findings…</p> : <FindingBrowser key={browserVersion} api={api} job={job} findings={findings} model={model} reviewing={tab === "review"} initialSeverity={severity} onReview={() => setTab("review")}/>}
      {tab === "review" && <div className="review-support">
        {conflict && <InlineAlert title="This review was changed in another session. Refresh before saving again." tone="warning"><p>Your draft is preserved. Load the latest revision to compare it before choosing which edits to keep.</p>{!fresh ? <Button disabled={!!busy} onClick={model.refreshConflict}>Refresh latest revision</Button> : <><Disclosure title="Latest saved changes"><ReadableRecord record={current?.changes || {}}/></Disclosure><p>Using your draft replaces the saved review fields with your draft.</p><div className="actions"><Button onClick={() => model.resolveConflict(false)}>Use latest revision</Button><Button onClick={() => model.resolveConflict(true)}>Use my draft as next revision</Button></div></>}</InlineAlert>}
        <Disclosure title={`Revision history · ${review?.revisions?.length || 0}`}><RevisionHistory revisions={review?.revisions || []} currentId={revisionId}/>{current && <ProtectedResource api={api} path={`/api/audits/${encodeURIComponent(job.id)}/review-report/${encodeURIComponent(revisionId)}`} report>Preview saved revision</ProtectedResource>}</Disclosure>
        {dirty && <Disclosure title="Revision reason (optional)"><Field label="Revision reason (optional)" maxLength={1000} hint="Up to 1,000 characters." value={model.reason} onChange={e => model.setReason(e.target.value)}/></Disclosure>}
      </div>}
    </div>
    {tab === "review" && <div className="review-actionbar glass-surface" aria-label="Review actions"><div className="review-feedback">        {model.failure && model.failure.action !== "load" && <ErrorAlert error={model.failure.error} title={model.failure.afterSuccess ? "Action completed; revision refresh is unavailable" : actionTitles[model.failure.action]} action={<Button variant="quiet" onClick={model.dismiss}>Dismiss error</Button>}/>}
        {model.validation && <InlineAlert title="Review needs attention">{model.validation}</InlineAlert>}
</div><div className="review-save-state"><StatusBadge status={status}/><strong>{dirty ? "Unsaved changes" : revisionId ? "All changes saved" : "No saved revision"}</strong><p role="status">{model.notice || (dirty ? "Save before validating or publishing." : status === "validated" ? "Approval is optional. Publishing preserves this revision." : status === "in_review" ? "Validate when your review is ready." : "Machine evidence and scores stay intact.")}</p></div><div className="actions">{status === "validated" && !dirty && <Button disabled={!!busy || conflict} onClick={() => model.action("approve")}>{busy === "approve" ? "Approving…" : "Approve revision"}</Button>}<Button variant="primary" disabled={!review || !!busy || conflict || (next === "save" && !dirty && status !== "changes_requested") || (next === "publish" && publication?.revisionId === revisionId)} onClick={() => model.action(next)}>{busy === next ? pending[next] : labels[next]}</Button>{publication?.publicationUrl && /^https?:\/\//i.test(publication.publicationUrl) && <a href={publication.publicationUrl} target="_blank" rel="noreferrer">Open published report ↗</a>}</div></div>}
  </section>;
}
