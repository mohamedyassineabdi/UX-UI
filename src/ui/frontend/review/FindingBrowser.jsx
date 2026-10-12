import { useEffect, useMemo, useRef, useState } from "react";
import { findingId } from "../api/artifacts.js";
import { Button, Disclosure, Field } from "../components/Primitives.jsx";
import EvidencePanel, { evidenceText } from "./EvidencePanel.jsx";
import GuidedFindingEditor from "./GuidedFindingEditor.jsx";
import ReadableRecord from "../components/ReadableRecord.jsx";

const DETAIL_FIELDS = [["findingId", "Finding ID"], ["severity", "Severity"], ["confidence", "Confidence"], ["axisName", "Audit area"], ["sourceSheet", "Criteria group"], ["ruleId", "Rule"], ["pageName", "Page"], ["pageUrl", "Page URL"], ["evidenceIds", "Evidence IDs"], ["sources", "Sources"], ["confirmationCount", "Confirmed by"]];
export default function FindingBrowser({ api, job, findings, model, reviewing, initialSeverity, onReview }) {
  const [query, setQuery] = useState("");
  const [severity, setSeverity] = useState(initialSeverity || "");
  const [axis, setAxis] = useState("");
  const [decision, setDecision] = useState("");
  const [selected, setSelected] = useState("");
  const [drilled, setDrilled] = useState(false);
  const [limit, setLimit] = useState(25);
  const heading = useRef(null), selectedButton = useRef(null), detail = useRef(null);
  const rows = useMemo(() => findings.map((item, index) => ({ ...item, key: findingId(item) || `readonly-${index}` })), [findings]);
  const state = item => model.changes[findingId(item)]?.reviewDecision || "No decision";
  const visible = rows.filter(item => (!severity || item.severity === severity) && (!axis || (item.axisName || item.axisId) === axis) && (!decision || state(item) === decision) && evidenceText([item.title, item.message, item.pageUrl, findingId(item), item.evidence]).toLowerCase().includes(query.toLowerCase()));
  const active = visible.find(item => item.key === selected) || visible[0];
  useEffect(() => { if (detail.current) detail.current.scrollTop = 0; }, [active?.key]);
  const levels = [...new Set(rows.map(item => item.severity).filter(Boolean))];
  const axes = [...new Set(rows.map(item => item.axisName || item.axisId).filter(Boolean))];
  const decisions = [...new Set(rows.map(state))];
  function filter(setter, value) { setter(value); setLimit(25); if (matchMedia("(max-width: 767px)").matches) setDrilled(false); }
  function choose(item) {
    setSelected(item.key); setDrilled(true);
    if (matchMedia("(max-width: 767px)").matches) requestAnimationFrame(() => heading.current?.focus());
  }
  function back() { setDrilled(false); requestAnimationFrame(() => selectedButton.current?.focus()); }
  const assessment = active && <dl className="machine-assessment">{[["Interpretation", active.insight || active.explanation], ["Impact", active.impact || active.whyItMatters], ["Machine recommendation", active.recommendation]].filter(([, value]) => value).map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{evidenceText(value)}</dd></div>)}</dl>;
  return <div className={`finding-browser ${drilled ? "is-drilled" : ""}`}>
    <aside className="finding-navigation" aria-label="Finding selection">
      <div className="finding-filters"><div className="section-row"><h2>{reviewing ? "Review findings" : "Findings"}</h2><span className="metadata">{findings.length}</span></div>
        {rows.length > 1 && <><Field type="search" label="Find a finding" placeholder="Title, evidence, page or ID" value={query} onChange={e => filter(setQuery, e.target.value)}/>
        <div className="filter-grid">{levels.length > 1 && <Field as="select" label="Severity" value={severity} onChange={e => filter(setSeverity, e.target.value)}><option value="">All severities</option>{levels.map(level => <option key={level}>{level}</option>)}</Field>}{axes.length > 1 && <Field as="select" label="UX dimension" value={axis} onChange={e => filter(setAxis, e.target.value)}><option value="">All dimensions</option>{axes.map(name => <option key={name}>{name}</option>)}</Field>}{(decisions.length > 1 || decision) && <Field as="select" label="Review state" value={decision} onChange={e => filter(setDecision, e.target.value)}><option value="">All decisions</option>{decisions.map(name => <option key={name} value={name}>{name.replaceAll("_", " ")}</option>)}</Field>}</div></>}
        <p className="metadata" role="status">{visible.length} of {rows.length} findings</p>
        {(query || severity || axis || decision) && <Button variant="quiet" onClick={() => { setQuery(""); setSeverity(""); setAxis(""); setDecision(""); setLimit(25); }}>Clear filters</Button>}
      </div>
      <div className="finding-list">{visible.slice(0, limit).map(item => <button ref={active?.key === item.key ? selectedButton : undefined} key={item.key} type="button" className={`finding-item ${active?.key === item.key ? "is-selected" : ""}`} aria-pressed={active?.key === item.key} onClick={() => choose(item)}>
        <span className="finding-row-meta"><span className={`severity-label severity-${item.severity}`}>{item.severity || "Severity not provided"}</span><span>{state(item).replaceAll("_", " ")}</span></span>
        <strong>{item.title || item.message || item.key}</strong>
        {(item.axisName || item.axisId || item.pageName) && <span className="finding-context">{item.axisName || item.axisId || item.pageName}</span>}
      </button>)}</div>
      {visible.length > limit && <Button onClick={() => setLimit(value => value + 25)}>Show next 25 findings</Button>}
      {!visible.length && <div className="empty-state">No findings match these filters.</div>}
    </aside>
    {active ? <article ref={detail} className="finding-detail" aria-label="Selected finding">
      <Button className="finding-back" onClick={back}>← Back to findings</Button>
      <header className="finding-detail-heading"><p className="eyebrow">{reviewing ? "Evidence-led review" : "Machine finding"}</p><h2 ref={heading} tabIndex={-1}>{active.title || active.message || "Untitled finding"}</h2><div className="finding-meta"><span className={`severity-label severity-${active.severity}`}>{active.severity || "Severity not provided"}</span>{(active.axisName || active.axisId) && <span>{active.axisName || active.axisId}</span>}<span>{active.aiDiscovered ? "AI-discovered" : "Machine assessment"}</span></div></header>
      <EvidencePanel api={api} job={job} finding={active}/>
      {reviewing ? <Disclosure title="Machine interpretation & recommendation">{assessment}</Disclosure> : assessment}
      {reviewing ? <GuidedFindingEditor finding={job.type === "figma" ? { ...active, reviewUnsupported: true } : active} value={model.changes[findingId(active)] || {}} disabled={!!model.busy || model.conflict || !model.review} onChange={model.edit}/> : <div className="finding-review-link"><p>Reviewer decision: <strong>{state(active).replaceAll("_", " ")}</strong></p><Button onClick={onReview}>Review this finding</Button></div>}
      <Disclosure title="Finding details"><ReadableRecord record={{ ...active, findingId: findingId(active), confidence: typeof active.confidence === "number" ? `${Math.round(active.confidence * 100)}%` : active.confidence }} fields={DETAIL_FIELDS}/></Disclosure>
    </article> : <div className="empty-state"><h3>{rows.length ? "No matching finding" : "No structured findings available"}</h3><p>{rows.length ? "Change your filters to continue." : "Open the source report to inspect the available evidence."}</p></div>}
  </div>;
}
