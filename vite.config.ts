import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    // The FastAPI backend runs separately (see backend/); proxy so the
    // frontend can call relative /api/* paths without hitting CORS.
    // BACKEND_URL is set by compose.yaml to reach the sibling container by
    // service name; plain local dev falls back to localhost.
    proxy: { "/api": process.env.BACKEND_URL ?? "http://localhost:8000" },
  },
});
