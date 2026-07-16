// Thin API layer. Uses same-origin /api (Vite proxies to Django in dev,
// same host in prod). Override with VITE_API_BASE if the API lives elsewhere.
const BASE = import.meta.env.VITE_API_BASE || "";

async function request(path, options) {
  const res = await fetch(`${BASE}/api${path}`, options);
  let body = null;
  try {
    body = await res.json();
  } catch {
    /* non-JSON error */
  }
  if (!res.ok) {
    const detail = body?.detail || `Request failed (${res.status})`;
    throw new Error(detail);
  }
  return body;
}

export function health() {
  return request("/health/");
}

export function autocomplete(text, signal) {
  return request(`/geocode/autocomplete/?text=${encodeURIComponent(text)}`, { signal });
}

export function planTrip(input) {
  return request("/plan/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}
