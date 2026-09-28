import { defineConfig } from "vite";

// The browser only ever calls /api/... on this dev server; Vite forwards those requests to the
// backend, so there is no CORS setup. In Docker the target is http://backend:8000 (set in compose).
const target = process.env.VITE_PROXY_TARGET ?? "http://localhost:8000";

export default defineConfig({
  server: {
    host: true, // listen on all interfaces so the port is reachable from outside a container
    port: 5173,
    proxy: { "/api": target },
  },
});
