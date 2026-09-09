export default function AuditResults({ job }) {
  if (!job || !["completed", "failed", "cancelled"].includes(job.status)) return null;
  return <section className="card"><h2>Audit result</h2><p>{job.error || job.stage || job.status}</p>{job.reportUrl && <a href={job.reportUrl} target="_blank" rel="noreferrer">Open report</a>}{job.artifactUrl && <a href={job.artifactUrl} target="_blank" rel="noreferrer">Open artifacts</a>}</section>;
}
