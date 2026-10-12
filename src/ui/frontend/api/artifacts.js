// These are existing, owner-protected artifact routes used by the pipelines.
export function machinePaths(job) {
  const id = encodeURIComponent(job.id);
  if (job.inputType === "screenshot") return [`/artifacts/shared/generated/screenshot-audits/${id}/screenshot_gtm_audit.json`];
  if (job.type === "mobile") return [`/artifacts/shared/generated/mobile-audits/${id}/mobile_gtm_audit.json`];
  if (job.type === "figma") return [`/artifacts/shared/generated/figma-audits/${id}/data/final_result.json`];
  return [`/artifacts/shared/audits/${id}/audit/gtm_audit.json`, `/artifacts/shared/audits/${id}/extraction/audit_results.json`];
}
export async function getMachineAudit(api, job) {
  if (job.artifactsDeleted) return null;
  for (const path of machinePaths(job)) {
    const response = await api.request(path);
    if (response.status === 404) continue;
    return { data: await api.json(response, "Unable to load audit evidence."), path };
  }
  return null;
}
export const findingId = finding => String(finding.findingId || finding.id || finding.deduplicationId || "");
export function machineFindings(machine) {
  const list = machine?.allFindings || machine?.findings || machine?.deduplicatedFindings || machine?.audit?.issues || (machine?.axes || []).flatMap(axis => (axis.painPoints || []).map(item => ({ ...item, axisId: axis.id, axisName: axis.name })));
  const findings = Array.isArray(list) ? list.filter(item => item && typeof item === "object") : [];
  // AI-agent findings are kept apart by the pipeline; the client report keys them "ai-<index>", so review them under the same key.
  const known = new Set(findings.map(item => `${item.title}|${item.pageUrl || ""}`));
  const ai = (Array.isArray(machine?.aiDiscoveredFindings) ? machine.aiDiscoveredFindings : []).map((item, index) => item && typeof item === "object" && !known.has(`${item.title}|${item.pageUrl || ""}`) ? { ...item, findingId: findingId(item) || `ai-${index}`, aiDiscovered: true } : null);
  return [...findings, ...ai.filter(Boolean)];
}

// Accept only artifacts belonging to this run. Never send bearer credentials to a report-provided URL.
export function evidencePath(value, job) {
  if (typeof value !== "string" || /[?#\u0000]/.test(value)) return null;
  const normalized = value.replaceAll("\\", "/");
  if (normalized.split("/").some(part => part === ".." || part === ".") || /%|^https?:/i.test(normalized)) return null;
  const roots = [`shared/audits/${job.id}/`, ...["screenshot", "mobile", "figma"].map(kind => `shared/generated/${kind}-audits/${job.id}/`)];
  for (const root of roots) {
    const index = normalized.indexOf(root);
    if (index >= 0 && (index === 0 || normalized[index - 1] === "/")) return `/artifacts/${normalized.slice(index).split("/").map(encodeURIComponent).join("/")}`;
  }
  return null;
}
