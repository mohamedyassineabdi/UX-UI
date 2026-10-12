import { useEffect, useMemo, useState } from "react";
import { getAudit } from "../api/audits.js";
import { getMachineAudit, machineFindings } from "../api/artifacts.js";
import { Button, ErrorAlert, InlineAlert, StatusBadge } from "../components/Primitives.jsx";
import FindingBrowser from "./FindingBrowser.jsx";
import ClientReport from "./ClientReport.jsx";
import { downloadClientReportPdf } from "../api/clientReport.js";
import RoadmapTeaser from "./RoadmapTeaser.jsx";
import { AIReviewStatus } from "../audit/AuditResults.jsx";
import useReview, { actionTitles } from "./useReview.js";

export default function InteractiveReport({ api, auditId }) {
  const [job, setJob] = useState(null);
  const [machine, setMachine] = useState(null);
  const [error, setError] = useState(null);
  const [editing, setEditing] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [copied, setCopied] = useState(false);
  const [pdf, setPdf] = useState({ busy: false, error: "" });
  useEffect(() => { getAudit(api, auditId).then(setJob).catch(setError); }, [api, auditId]);
  useEffect(() => { if (job?.status === "completed") getMachineAudit(api, job).then(setMachine).catch(setError); }, [api, job]);
  const model = useReview(api, job || { id: auditId }, setDirty, setJob);
  const findings = useMemo(() => machineFindings(machine?.data || machine), [machine]);
  const status = model.review?.reviewStatus || "unreviewed";
  const deployReady = !!model.revisionId;
  const deployedCurrent = model.publication?.revisionId === model.revisionId && !dirty;
  const deployLabel = model.busy === "publish" ? "Deploying…" : model.publication && !deployedCurrent ? "Deploy updated report" : "Deploy report";
  const deploy = () => { if (!dirty && deployReady) model.action("publish"); };
  const downloadPdf = async () => { setPdf({ busy: true, error: "" }); try { await downloadClientReportPdf(api, job.id || auditId, model.revisionId); setPdf({ busy: false, error: "" }); } catch (e) { setPdf({ busy: false, error: e.message }); } };
  const copy = async () => { if (!model.publication?.publicationUrl) return; await navigator.clipboard?.writeText(model.publication.publicationUrl); setCopied(true); };
  if (error) return <main className="report-page"><ErrorAlert error={error} title="Couldn’t open interactive report"/></main>;
  if (!job || !machine) return <main className="report-page"><p role="status" className="loading-message">Loading interactive report…</p></main>;
  return <main className="report-page">
    <header className="report-toolbar glass-surface"><a className="report-back" href="/app">← Audit overview</a><div className="report-title"><span>Local report</span><strong>{job.siteName || job.appLabel || job.url || "Audit report"}</strong></div><div className="report-toolbar-actions"><Button className={editing ? "" : "is-active"} aria-pressed={!editing} onClick={() => setEditing(false)}>Client report</Button><Button className={editing ? "is-active" : ""} aria-pressed={editing} onClick={() => setEditing(true)}>Review / Edit</Button><Button disabled={pdf.busy} onClick={downloadPdf}>{pdf.busy ? "Preparing PDF…" : "Download PDF"}</Button><StatusBadge status={dirty ? "changes_requested" : status}/><Button variant="primary" disabled={dirty || !deployReady || !!model.busy} onClick={deploy}>{deployReady ? deployLabel : "Save edits first"}</Button></div></header>
    <section className="report-intro">{editing ? <div><p className="eyebrow">Expert review</p><h1>Review findings</h1><p>Automated evidence and scores are read-only. Confirm, adjust or exclude findings before the report goes to the client.</p></div> : <div><p className="eyebrow">Client report</p><h1>Audit report</h1><p>This is exactly what your client receives, online or as a PDF.</p></div>}{model.publication?.publicationUrl && <InlineAlert tone={deployedCurrent ? "success" : "warning"} title={deployedCurrent ? "Report deployed" : "Changes since last deployment"}><p>{deployedCurrent ? model.publication.publicationUrl : "Save the current local changes, then deploy an updated public snapshot."}</p>{deployedCurrent && <div className="actions"><a className="button button-secondary" href={model.publication.publicationUrl} target="_blank" rel="noreferrer">Open deployed report</a><Button onClick={copy}>{copied ? "Copied" : "Copy link"}</Button></div>}</InlineAlert>}</section>
    <AIReviewStatus job={job}/>
    {model.conflict && <InlineAlert tone="warning" title="This review was changed in another session">Your edits are still here. Reload the report to load the latest revision before saving or deploying.</InlineAlert>}
    {model.failure && <ErrorAlert error={model.failure.error} title={actionTitles[model.failure.action]}/>} {model.validation && <InlineAlert title="Review needs attention">{model.validation}</InlineAlert>}
    {pdf.error && <InlineAlert tone="warning" title="Couldn’t create the PDF">{pdf.error}</InlineAlert>}
    {editing ? <section className="report-content"><FindingBrowser api={api} job={job} findings={findings} model={model} reviewing={editing} onReview={() => setEditing(true)}/></section> : <section className="client-report-view"><ClientReport api={api} jobId={job.id || auditId} revisionId={model.revisionId}/></section>}
    <RoadmapTeaser api={api} auditId={job.id || auditId}/>
    {editing && <footer className="report-actionbar glass-surface"><div><strong>{dirty ? "Unsaved changes" : model.revisionId ? "Saved locally" : "No local edits saved"}</strong><p role="status">{model.notice || (dirty ? "Save before deployment." : deployReady ? "The current saved revision is ready to deploy." : "Save your review before deployment.")}</p></div><div className="actions"><Button disabled={!dirty || !!model.busy || model.conflict} onClick={() => model.action("save")}>{model.busy === "save" ? "Saving…" : "Save edits"}</Button><Button variant="primary" disabled={dirty || !deployReady || !!model.busy} onClick={deploy}>{deployLabel}</Button></div></footer>}
  </main>;
}
