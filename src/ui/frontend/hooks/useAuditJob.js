import { useEffect, useState } from "react";
import { cancelAudit, getAudit } from "../api/audits.js";

const TERMINAL = new Set(["completed", "failed", "cancelled"]);
export function useAuditJob(api) {
  const [job, setJob] = useState(null); const [error, setError] = useState("");
  useEffect(() => {
    if (!job?.id || TERMINAL.has(job.status)) return undefined;
    const timer = window.setInterval(() => getAudit(api, job.id).then(setJob).catch((e) => setError(e.message)), 1500);
    return () => window.clearInterval(timer);
  }, [api, job?.id, job?.status]);
  return { job, setJob, error, setError, cancel: async () => { if (job?.id) setJob(await cancelAudit(api, job.id)); } };
}
