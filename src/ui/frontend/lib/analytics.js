// GTM-compatible event push; a no-op when no tag manager is installed.
export function track(event, props = {}) {
  if (typeof window !== "undefined" && Array.isArray(window.dataLayer)) window.dataLayer.push({ event, ...props });
}
