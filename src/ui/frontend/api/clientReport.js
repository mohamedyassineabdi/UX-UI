// The EY Studio+ client report: the same document is shown in-app, deployed and printed to PDF.
export function clientReportPath(jobId, revisionId, { pdf = false, embed = false } = {}) {
  const params = new URLSearchParams();
  if (revisionId) params.set("revision", revisionId);
  if (embed) params.set("embed", "1");
  const query = params.toString();
  return `/api/audits/${encodeURIComponent(jobId)}/client-report${pdf ? ".pdf" : ""}${query ? `?${query}` : ""}`;
}

async function failure(response, fallback) {
  const payload = await response.json().catch(() => ({}));
  return new Error(payload.error || fallback);
}

export async function getClientReportHtml(api, jobId, revisionId) {
  const response = await api.request(clientReportPath(jobId, revisionId, { embed: true }));
  if (!response.ok) throw await failure(response, "The client report could not be loaded.");
  return response.text();
}

export async function downloadClientReportPdf(api, jobId, revisionId) {
  const response = await api.request(clientReportPath(jobId, revisionId, { pdf: true }));
  if (!response.ok) throw await failure(response, "The PDF could not be created.");
  const name = /filename="([^"]+)"/.exec(response.headers.get("Content-Disposition") || "")?.[1] || "ux-audit-report.pdf";
  const url = URL.createObjectURL(await response.blob());
  const link = Object.assign(document.createElement("a"), { href: url, download: name });
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
