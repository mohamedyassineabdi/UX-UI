import Icon from "../components/Icon.jsx";
import { InlineAlert } from "../components/Primitives.jsx";
import { machineFindings } from "../api/artifacts.js";
import AuditOverview from "./AuditOverview.jsx";

export default function AuditResults({ job, machine }) {
  if (job.status !== "completed") return null;
  const data = machine?.data || machine;
  const findings = machineFindings(data);
  return <><a className="report-open-button" href={`/report/${encodeURIComponent(job.id)}`}><Icon name="report" size={18}/><span>Open report</span><span aria-hidden="true">↗</span></a><AIReviewStatus job={job}/><section className="audit-content audit-overview-panel"><AuditOverview machine={data} findings={findings}/></section></>;
}

export function AIReviewStatus({ job }) {
  if (job.aiReviewStatus === "running") return <InlineAlert tone="info" title="AI review in progress">The AI agent is reviewing the screenshots. Its findings will be added to the report in about a minute.</InlineAlert>;
  if (job.aiReviewStatus === "completed") return <InlineAlert tone="success" title="AI review added to the report">Open the report to see the visual findings alongside the machine checks.</InlineAlert>;
  if (job.aiReviewStatus === "failed") return <InlineAlert tone="warning" title="The AI review didn’t finish" details={job.aiReviewError?.replace(/claude(?: code)?(?: cli)?/gi, "AI agent")}>The machine report is complete and ready to review.</InlineAlert>;
  return null;
}
