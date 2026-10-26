/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The SPA and the API share one origin in every environment (cookies are SameSite=Lax, no CORS).
// In dev, Vite proxies /api and /auth to the FastAPI backend.
const target = process.env.API_PROXY_TARGET ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target, changeOrigin: false },
      "/auth": { target, changeOrigin: false },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["src/test/setup.ts"],
    css: false,
    coverage: {
      provider: "v8",
      include: ["src/**/*.{ts,tsx}"],
      exclude: ["src/**/*.test.{ts,tsx}", "src/test/**", "src/main.tsx", "src/vite-env.d.ts"],
      reporter: ["text-summary", "lcov"],
      // Day 5 L0 gate: ≥ 70 % overall
      thresholds: { lines: 70, statements: 70, branches: 70, functions: 70 },
    },
  },
});
