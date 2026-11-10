import { defineConfig } from "@playwright/test";

// Runs against the API serving the built frontend with the scripted FakeLLM (no API keys needed):
//   npm run build && python -m tests.demo_server   (from the repo root)
export default defineConfig({
  testDir: "tests/e2e",
  timeout: 60_000,
  retries: 0,
  reporter: [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]],
  use: { baseURL: process.env.E2E_BASE_URL ?? "http://127.0.0.1:8000", trace: "retain-on-failure" },
  webServer: process.env.E2E_BASE_URL ? undefined : {
    command: "cd ../.. && python -m tests.demo_server", url: "http://127.0.0.1:8000/api/health", reuseExistingServer: true, timeout: 60_000,
  },
});
