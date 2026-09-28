import { defineConfig } from "vite";

// The browser only ever calls /api/... on this dev server; Vite forwards those requests to the
// backend, so there is no CORS setup. In Docker the target is http://backend:8000 (set in compose).
// 127.0.0.1 rather than "localhost": Node may resolve localhost to IPv6 ::1, while uvicorn listens on IPv4 only.
const target = process.env.VITE_PROXY_TARGET ?? "http://127.0.0.1:8000";

export default defineConfig({
  server: {
    host: true, // listen on all interfaces so the port is reachable from outside a container
    port: 5173,
    proxy: { "/api": target },
  },
});
