import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// The dev server proxies API calls to the backend so the frontend can use
// same-origin relative paths ("/health", "/api/..."). Override the target with
// VITE_PROXY_TARGET if the backend runs elsewhere.
const proxyTarget = process.env.VITE_PROXY_TARGET ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/health": { target: proxyTarget, changeOrigin: true },
      "/api": { target: proxyTarget, changeOrigin: true },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});
