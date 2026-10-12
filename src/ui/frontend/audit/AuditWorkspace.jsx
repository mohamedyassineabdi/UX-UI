import { useEffect, useState } from "react";
import { Button, Disclosure, ErrorAlert, formatDate, InlineAlert, StatusBadge } from "../components/Primitives.jsx";
import { TERMINAL } from "../hooks/useAuditJob.js";
import { getMachineAudit } from "../api/artifacts.js";
import AuditResults from "./AuditResults.jsx";

export default function AuditWorkspace({ api, job, error, cancel, cancelling, onNew }) {
  const [machine, setMachine] = useState(null);
  const [machineError, setMachineError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    if (job.status !== "completed") return;
    let live = true;
    setLoading(true); setMachineError(null);
    getMachineAudit(api, job).then(data => { if (live) setMachine(data); }).catch(item => { if (live) setMachineError(item); }).finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, [api, job, retry]);

  const terminal = TERMINAL.has(job.status);
  const source = job.inputType === "screenshot" ? "Screenshots" : job.type === "mobile" ? "Mobile App" : job.type === "figma" ? "Figma" : "Website";
  const target = job.siteName || job.appLabel || job.appPackage || job.url || "Audit overview";
  const outcome = { failed: ["The audit couldn’t finish.", "Check the error details, then start another audit when the issue is resolved."], cancelled: ["This audit was cancelled.", "You can start a new audit whenever you’re ready."], interrupted: ["This audit was interrupted.", "The worker stopped before finishing. This run won’t restart automatically; start a new audit to try again."] }[job.status];

  return <>
    <div className="workspace-heading"><div><p className="eyebrow">{source} audit</p><h1 title={target}>{target}</h1><p>{job.mode === "detailed" ? "Detailed workbook audit" : "Machine audit overview"}{job.createdAt ? ` · Created ${formatDate(job.createdAt)}` : ""}</p></div><StatusBadge status={job.status}/></div>
    <ErrorAlert error={error} title="Status updates paused"/>
    {!terminal && <section className="surface progress-panel"><div className="section-row"><div><p className="eyebrow">In progress</p><h2>{job.status === "queued" ? "Your audit is in the queue." : "Gathering a clearer picture."}</h2></div></div><p role="status" aria-live="polite" aria-atomic="true">{job.cancelRequested ? "Cancellation requested. Waiting for the audit to stop safely." : job.stage || "Preparing audit"}</p><div className="indeterminate" role="progressbar" aria-label="Audit in progress"><span/></div><div className="progress-next"><p className="progress-next-title">What happens next</p><ol><li>Collect evidence from your source</li><li>Run checks and measurements</li><li>Score the five UX dimensions</li><li>Open the report for your review</li></ol></div><div className="progress-footer"><span>Progress updates automatically.</span><Button variant="danger" disabled={cancelling || job.cancelRequested} onClick={cancel}>{cancelling || job.cancelRequested ? "Cancelling…" : "Cancel audit"}</Button></div></section>}
    {outcome && <section className="surface outcome-panel"><StatusBadge status={job.status}/><h2>{outcome[0]}</h2><p>{outcome[1]}</p>{job.error && <InlineAlert title="Audit details" tone={job.status === "failed" ? "error" : "warning"} details={job.error}>The server reported an issue during this run.</InlineAlert>}<Button variant="primary" onClick={onNew}>Start another audit</Button></section>}
    <div role="status" className="sr-only">{terminal ? `Audit ${job.status}.` : ""}</div>
    <AuditResults job={job} machine={machine}/>
    {terminal && loading && <p className="loading-message" role="status">Loading audit evidence…</p>}
    <ErrorAlert error={machineError} title="Evidence is unavailable" action={<Button onClick={() => setRetry(value => value + 1)}>Retry evidence</Button>}/>
    <Disclosure title="Audit details & logs"><dl className="audit-details"><div><dt>Audit ID</dt><dd><code>{job.id}</code></dd></div><div><dt>Last update</dt><dd>{formatDate(job.updatedAt) || "Not provided"}</dd></div><div><dt>Status</dt><dd>{job.status}</dd></div></dl>{job.logs?.length > 0 ? <pre tabIndex={0} className="audit-logs">{job.logs.map(line => typeof line === "string" ? line : JSON.stringify(line)).join("\n")}</pre> : <p className="field-hint">No logs are available for this run.</p>}</Disclosure>
  </>;
}
