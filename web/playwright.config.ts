import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "@playwright/test";

const here = fileURLToPath(new URL(".", import.meta.url));

// Browser journey against the real local service (recorded case, offline). Run `npm run build` first.
const python = resolve(here, "..", ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
export default defineConfig({
  testDir: "e2e",
  timeout: 60_000,
  use: { baseURL: "http://127.0.0.1:8799", trace: "off" },
  webServer: {
    // the launcher stops the whole server process tree on Windows, where the venv python is a trampoline
    command: `node "${resolve(here, "e2e", "serve.mjs")}" "${python}" -m nasa_in_mining serve --cases "${resolve(here, "..", "cases")}" --web "${resolve(here, "dist")}" --port 8799`,
    url: "http://127.0.0.1:8799/api/health",
    reuseExistingServer: false,
    timeout: 60_000,
  },
  projects: [
    { name: "desktop", use: { browserName: "chromium", viewport: { width: 1440, height: 900 } } },
    { name: "mobile", use: { browserName: "chromium", viewport: { width: 390, height: 844 } } },
  ],
});
