export async function api(method, args = {}) {
  const res = await fetch(`/api/method/${method}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Frappe-CSRF-Token": window.csrf_token || "",
    },
    body: JSON.stringify(args),
    credentials: "include",
  })
  const json = await res.json()
  if (json.exc || json.exception) {
    throw new Error(readableError(json))
  }
  return json.message
}

function readableError(json) {
  const raw = json._server_messages
  if (raw) {
    try {
      const list = JSON.parse(raw)
      const first = typeof list[0] === "string" ? JSON.parse(list[0]) : list[0]
      return first.message || first || "Request failed"
    } catch {
      return String(raw)
    }
  }
  return json.exception || json.exc || "Request failed"
}
