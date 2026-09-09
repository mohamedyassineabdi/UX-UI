export async function createAudit(api, kind, values) {
  if (kind === "screenshot") {
    const form = new FormData();
    form.set("auditType", "screenshot");
    form.set("surfaceType", values.surfaceType || "website");
    form.set("siteName", values.siteName || "Screenshot audit");
    for (const file of values.files || []) form.append("screenshots", file);
    return api.json(await api.request("/api/audits", { method: "POST", body: form }), "Unable to start the screenshot audit.");
  }
  const body = kind === "mobile" ? { auditType: "mobile", appLabel: values.appLabel, appPackage: values.appPackage, appActivity: values.appActivity, appiumUrl: values.appiumUrl, deviceName: values.deviceName, platformVersion: values.platformVersion, udid: values.udid } : kind === "figma" ? { auditType: "figma", figmaUrl: values.figmaUrl } : { auditType: "website", url: values.url, mode: values.mode || "gtm" };
  return api.json(await api.request("/api/audits", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }), "Unable to start the audit.");
}
export const getAudit = (api, id) => api.request(`/api/audits/${encodeURIComponent(id)}`).then((response) => api.json(response, "Unable to refresh audit status."));
export const cancelAudit = (api, id) => api.request(`/api/audits/${encodeURIComponent(id)}/cancel`, { method: "POST" }).then((response) => api.json(response, "Unable to cancel audit."));
