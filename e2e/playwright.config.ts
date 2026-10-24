// EN-12 (T-EN12.1, T-EN12.4). Runs against the dev compose stack (Keycloak test realm + LLM_PROVIDER=fake) in CI,
// and against staging (real LLM) with E2E_BASE_URL + E2E_*_PASSWORD set.
import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.E2E_BASE_URL ?? "http://localhost:5173";

export default defineConfig({
  testDir: "specs",
  timeout: 90_000,
  expect: { timeout: 15_000 },
  fullyParallel: false, // the library is shared by the whole team: tests run in order on one library
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"], ["html", { open: "never" }], ["junit", { outputFile: "test-results/junit.xml" }]],
  use: { baseURL, trace: "retain-on-failure", screenshot: "only-on-failure", locale: "vi-VN" },
  // T-EN12.4 / LG-14: the two latest versions of the company browsers (PQ-004: Chrome and Edge)
  projects: [
    { name: "chrome", use: { ...devices["Desktop Chrome"], channel: "chrome", viewport: { width: 1440, height: 900 } } },
    { name: "edge", use: { ...devices["Desktop Edge"], channel: "msedge", viewport: { width: 1440, height: 900 } } },
    { name: "chromium-1024", use: { ...devices["Desktop Chrome"], viewport: { width: 1100, height: 800 } } },
  ],
});
