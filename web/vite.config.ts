/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The API (python -m nasa_in_mining serve) serves recorded cases; in development Vite proxies /api to it.
// The contract schema lives in ../contract and is bundled for run-time validation.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://127.0.0.1:8000" }, fs: { allow: [".."] } },
  build: { outDir: "dist", sourcemap: false, chunkSizeWarningLimit: 1600 },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["src/test/setup.ts"],
    exclude: ["e2e/**", "node_modules/**"],
  },
});
