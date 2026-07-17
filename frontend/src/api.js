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
    // Routing errors (502/503) carry {detail}. DRF validation errors (400) come
    // back per field: {field: [msg, ...]} (+ optional non_field_errors).
    if (body && typeof body === "object" && !body.detail) {
      const { non_field_errors, ...fields } = body;
      const fieldErrors = {};
      for (const [k, v] of Object.entries(fields)) {
        fieldErrors[k] = Array.isArray(v) ? v[0] : String(v);
      }
      const err = new Error(non_field_errors?.[0] || "Please fix the highlighted fields.");
      if (Object.keys(fieldErrors).length) err.fieldErrors = fieldErrors;
      throw err;
    }
    throw new Error(body?.detail || `Request failed (${res.status})`);
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
