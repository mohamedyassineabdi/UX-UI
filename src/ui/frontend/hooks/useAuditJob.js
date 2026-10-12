import { useCallback, useEffect, useRef, useState } from "react";
import { cancelAudit, getAudit } from "../api/audits.js";
export const TERMINAL = new Set(["completed", "failed", "cancelled", "interrupted"]);
// A completed job keeps polling while its background AI review runs.
const settled = job => TERMINAL.has(job?.status) && job?.aiReviewStatus !== "running";
export function useAuditJob(api) {
  const [job, setJob] = useState(null);
  const [error, setError] = useState(null);
  const [cancelling, setCancelling] = useState(false);
  const [pollVersion, setPollVersion] = useState(0);
  const generation = useRef(0);
  const acceptJob = useCallback(value => { generation.current += 1; setPollVersion(version => version + 1); setError(null); setJob(value); }, []);
  useEffect(() => {
    if (!job?.id || settled(job)) return;
    let stopped = false; let timer;
    const currentGeneration = generation.current;
    async function poll() {
      try {
        const next = await getAudit(api, job.id);
        if (!stopped && currentGeneration === generation.current) { setJob(next); setError(null); }
        if (settled(next)) return;
      } catch (e) { if (!stopped) setError(e); }
      if (!stopped) timer = window.setTimeout(poll, 1500);
    }
    timer = window.setTimeout(poll, 1500);
    return () => { stopped = true; clearTimeout(timer); };
  }, [api, job?.id, job?.status, job?.aiReviewStatus, pollVersion]);
  async function cancel() {
    if (!job?.id || cancelling) return;
    setCancelling(true); setError(null);
    try { const next = await cancelAudit(api, job.id); acceptJob(next); }
    catch (e) { setError(e); } finally { setCancelling(false); }
  }
  return { job, setJob: acceptJob, error, cancel, cancelling };
}
