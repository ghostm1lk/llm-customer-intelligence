// VITE_API_URL is set at build time on render. empty in dev, where vite proxies to :8000
const API_URL = import.meta.env.VITE_API_URL || "";

export async function checkHealth() {
  const response = await fetch(API_URL + "/health");
  if (!response.ok) {
    throw new Error("Health check failed");
  }
  return response.json();
}

export async function analyzeMessage(message) {
  const response = await fetch(API_URL + "/process-customer-message", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: message }),
  });

  let data = {};
  try {
    data = await response.json();
  } catch {
    data = {};
  }
  return { ok: response.ok, status: response.status, data: data };
}
