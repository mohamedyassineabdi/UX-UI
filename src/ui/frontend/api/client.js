export class ApiError extends Error {
  constructor(message, { status = 0, requestId = "" } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.requestId = requestId;
  }
}

export function createApiClient({ normalizeBaseUrl, configuredBaseUrl, isCrossOrigin }) {
  function baseUrl(value) {
    return normalizeBaseUrl(value === undefined ? configuredBaseUrl() : value);
  }

  function url(path, configured) {
    const base = baseUrl(configured);
    return !base ? path : path.startsWith("/") ? `${base}${path}` : `${base}/${path}`;
  }

  function headers(extra, configured) {
    const result = new Headers(extra || {});
    const token = sessionStorage.getItem("internalPortalToken") || sessionStorage.getItem("internalPortalAdminToken");
    if (token) result.set("Authorization", `Bearer ${token}`);
    const base = baseUrl(configured);
    if (isCrossOrigin(base) && base.includes("ngrok")) result.set("ngrok-skip-browser-warning", "true");
    return result;
  }

  async function request(path, options, configured) {
    const target = url(path, configured);
    try {
      const response = await fetch(target, { ...(options || {}), headers: headers(options?.headers, configured) });
      if (response.status === 401 || response.status === 403) window.dispatchEvent(new CustomEvent("uxui:authorization-failed", { detail: { status: response.status } }));
      return response;
    } catch (_error) {
      throw new ApiError(`Unable to reach backend API at ${baseUrl(configured) || window.location.origin}. Confirm the Python server is running and update the Backend API URL in this form.`);
    }
  }

  async function json(response, fallbackMessage) {
    const text = await response.text();
    const clean = text.trim();
    const requestId = response.headers.get("x-request-id") || "";
    if (clean && ((response.headers.get("content-type") || "").includes("application/json") || /^[{[]/.test(clean))) {
      try {
        const payload = JSON.parse(clean);
        if (!response.ok) throw new ApiError(payload.error || fallbackMessage || "Backend request failed.", { status: response.status, requestId });
        return payload;
      } catch (error) {
        if (error instanceof ApiError) throw error;
        throw new ApiError(`Backend returned malformed JSON from ${response.url || "the API"}.`, { status: response.status, requestId });
      }
    }
    if (!clean && response.ok) return {};
    throw new ApiError(fallbackMessage || "Backend returned a non-JSON response.", { status: response.status, requestId });
  }

  return { url, headers, request, json };
}
