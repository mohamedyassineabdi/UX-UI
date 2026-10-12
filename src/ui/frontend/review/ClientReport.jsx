import { useEffect, useRef, useState } from "react";
import { getClientReportHtml } from "../api/clientReport.js";
import { ErrorAlert } from "../components/Primitives.jsx";

// Scripts never run in the report frame; same-origin only lets the page size the frame to its content,
// and popups let report links open in a new tab instead of replacing the report.
export default function ClientReport({ api, jobId, revisionId }) {
  const frame = useRef(null);
  const [html, setHtml] = useState("");
  const [error, setError] = useState(null);
  useEffect(() => {
    let live = true;
    setHtml(""); setError(null);
    getClientReportHtml(api, jobId, revisionId).then(value => live && setHtml(value)).catch(value => live && setError(value));
    return () => { live = false; };
  }, [api, jobId, revisionId]);
  useEffect(() => {
    const fit = () => { const doc = frame.current?.contentDocument; if (doc?.documentElement) frame.current.style.height = `${doc.documentElement.scrollHeight}px`; };
    window.addEventListener("resize", fit);
    frame.current?.addEventListener("load", fit);
    return () => { window.removeEventListener("resize", fit); frame.current?.removeEventListener("load", fit); };
  }, [html]);
  if (error) return <ErrorAlert error={error} title="Couldn’t load the client report"/>;
  if (!html) return <p role="status" className="loading-message">Preparing the client report…</p>;
  return <iframe ref={frame} className="client-report-frame" title="Client report" sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox" srcDoc={html}/>;
}
