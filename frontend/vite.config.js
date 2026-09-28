import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// in dev, api calls are proxied to the fastapi server on :8000
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "/process-customer-message": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
    },
  },
});
