// Talks to the FastAPI backend.
// In production VITE_API_URL is the API's address (set on Render when building the static site).
// In development it is empty, and Vite forwards the requests to http://127.0.0.1:8000.
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
