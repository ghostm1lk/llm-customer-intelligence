import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// During development (npm run dev), API calls are forwarded to the FastAPI server on port 8000,
// so the frontend can use the same relative URLs as in production.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "/process-customer-message": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
    },
  },
});
