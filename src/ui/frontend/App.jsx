import { useEffect, useMemo, useState } from "react";
import { createApiClient } from "./api/client.js";
import AppShell from "./components/AppShell.jsx";
import AuditForm from "./audit/AuditForm.jsx";
import AuditWorkspace from "./audit/AuditWorkspace.jsx";
import InteractiveReport from "./review/InteractiveReport.jsx";
import Landing from "./landing/Landing.jsx";
import { TERMINAL, useAuditJob } from "./hooks/useAuditJob.js";
import { getAudit } from "./api/audits.js";
function configuredBaseUrl() { try { return String(window.localStorage.getItem("UX_UI_AUDITOR_API_BASE_URL") || window.__UX_UI_AUDITOR_CONFIG__?.apiBaseUrl || "").replace(/\/+$/, ""); } catch { return String(window.__UX_UI_AUDITOR_CONFIG__?.apiBaseUrl || "").replace(/\/+$/, ""); } }
function isCrossOrigin(value) { try { return value && new URL(value).origin !== window.location.origin; } catch { return false; } }
export default function App() {
  const api = useMemo(() => createApiClient({ normalizeBaseUrl: v => String(v || "").replace(/\/+$/, ""), configuredBaseUrl, isCrossOrigin }), []);
  const isLanding = window.location.pathname === "/";
  const reportMatch = window.location.pathname.match(/^\/report\/([^/]+)\/?$/);
  const audit = useAuditJob(api);
  const [view, setView] = useState("setup");
  const [dirty, setDirty] = useState(false);
  useEffect(() => {
    if (isLanding) return;
    if (audit.job?.id) {
      try { sessionStorage.setItem("uxui-current-audit", audit.job.id); } catch { /* Session storage is optional. */ }
      return;
    }
    let live = true;
    let saved = "";
    try { saved = sessionStorage.getItem("uxui-current-audit") || ""; } catch { /* Session storage is optional. */ }
    if (saved) getAudit(api, saved).then(job => { if (live) { audit.setJob(job); setView("workspace"); } }).catch(() => { try { sessionStorage.removeItem("uxui-current-audit"); } catch { /* Session storage is optional. */ } });
    return () => { live = false; };
  }, [api, audit.job?.id, audit.setJob, isLanding]);
  function navigate(next) { setView(next); requestAnimationFrame(() => document.querySelector("#main-content")?.focus()); }
  useEffect(() => {
    if (!dirty) return;
    const warn = e => { e.preventDefault(); e.returnValue = ""; };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);
  function beforeCreate() {
    // Confirm before creating a new server job, never after the request succeeds.
    return !dirty || window.confirm("Start a new audit and discard the current audit’s unsaved review changes?");
  }
  function created(job) {
    setDirty(false); audit.setJob(job); navigate("workspace");
  }
  if (isLanding) return <Landing/>;
  if (reportMatch) return <InteractiveReport api={api} auditId={decodeURIComponent(reportMatch[1])}/>;
  return <AppShell job={audit.job} view={view} onView={navigate}><div hidden={view !== "setup"}><AuditForm api={api} onCreated={created} beforeCreate={beforeCreate} activeJob={!!audit.job && !TERMINAL.has(audit.job.status)}/></div>{audit.job && <div hidden={view !== "workspace"}><AuditWorkspace key={audit.job.id} api={api} {...audit} onNew={() => navigate("setup")}/></div>}</AppShell>;
}
