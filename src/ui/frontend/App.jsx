import { useMemo } from "react";
import { createApiClient } from "./api/client.js";
import AuditForm from "./audit/AuditForm.jsx";
import AuditResults from "./audit/AuditResults.jsx";
import ReviewPanel from "./review/ReviewPanel.jsx";
import { useAuditJob } from "./hooks/useAuditJob.js";

function configuredBaseUrl() { return String(window.localStorage.getItem("UX_UI_AUDITOR_API_BASE_URL") || window.__UX_UI_AUDITOR_CONFIG__?.apiBaseUrl || "").replace(/\/+$/, ""); }
function isCrossOrigin(value) { try { return value && new URL(value).origin !== window.location.origin; } catch { return false; } }
export default function App() {
  const api = useMemo(() => createApiClient({ normalizeBaseUrl: (v) => String(v || "").replace(/\/+$/, ""), configuredBaseUrl, isCrossOrigin }), []);
  const { job, setJob, error, setError, cancel } = useAuditJob(api);
  return <main><header><h1>UX/UI Auditor</h1><p>Evidence-aware audits and structured review.</p></header>{error && <p className="error" role="alert">{error}</p>}<AuditForm api={api} onCreated={setJob} onError={setError} />{job && <section className="card"><h2>Audit progress</h2><p>{job.status || "queued"}: {job.stage || "Preparing audit"}</p>{!['completed','failed','cancelled'].includes(job.status) && <button onClick={() => cancel().catch((e) => setError(e.message))}>Cancel audit</button>}</section>}<AuditResults job={job} />{job?.id && <ReviewPanel api={api} jobId={job.id} onError={setError} />}</main>;
}
