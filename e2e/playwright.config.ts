// EN-12 + Day 6 (docs/test-plan.md). Two stacks:
//  - E2E_STACK=local (default): Playwright starts backend/tests/e2e_server.py + the Vite dev server and runs the
//    test cases of docs/test-cases.md (specs/tc-*.spec.ts). No Docker needed — runs on a laptop and on every PR.
//  - E2E_STACK=compose: the docker compose stack (Keycloak, PostgreSQL, MinIO, TEI, fake LLM) or staging
//    (E2E_BASE_URL) with the journey specs f*.spec.ts and a11y.spec.ts.
import { defineConfig, devices } from "@playwright/test";
import path from "node:path";

const stack = process.env.E2E_STACK ?? "local";
const local = stack === "local";
// Own ports for the local stack, never reused: a dev server of another project on :5173 once answered the tests
// (HD-3). Override with E2E_WEB_PORT / E2E_API_PORT if these are taken.
const webPort = Number(process.env.E2E_WEB_PORT ?? 5180);
const apiPort = Number(process.env.E2E_API_PORT ?? 8000);
const webBase = `http://localhost:${webPort}`;
const baseURL = process.env.E2E_BASE_URL ?? (local ? webBase : "http://localhost:5173");
const root = path.resolve(__dirname, "..");
const python =
  process.env.E2E_PYTHON ??
  path.join(root, "backend", ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");

export default defineConfig({
  testDir: "specs",
  testMatch: local ? /tc-.*\.spec\.ts/ : /(f\d-.*|a11y)\.spec\.ts/,
  timeout: 360_000, // TC-201-04 allows the 49.5 MB file up to 300 s (NFR-03)
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1, // one shared library per run: test cases run in the order of docs/test-cases.md
  retries: 0, // Day 6: a PASS must hold without retries; flakiness is found by running the suite twice
  reporter: [
    ["list"],
    ["html", { open: "never", outputFolder: "playwright-report" }],
    ["junit", { outputFile: path.join(root, "reports", `junit-${process.env.E2E_RUN ?? "run"}.xml`) }],
    ["json", { outputFile: path.join(root, "reports", `results-${process.env.E2E_RUN ?? "run"}.json`) }],
  ],
  use: { baseURL, trace: "on", screenshot: "on", video: "off", locale: "vi-VN", actionTimeout: 15_000 },
  projects: local
    ? [{ name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } } }]
    : [
        // T-EN12.4 / LG-14: the company browsers (PQ-004: Chrome and Edge)
        { name: "chrome", use: { ...devices["Desktop Chrome"], channel: "chrome", viewport: { width: 1440, height: 900 } } },
        { name: "edge", use: { ...devices["Desktop Edge"], channel: "msedge", viewport: { width: 1440, height: 900 } } },
      ],
  webServer: local
    ? [
        {
          command: `"${python}" -m tests.e2e_server`,
          cwd: path.join(root, "backend"),
          url: `http://localhost:${apiPort}/healthz`,
          env: { E2E_API_PORT: String(apiPort), E2E_WEB_BASE: webBase },
          reuseExistingServer: false, // fresh in-memory data every run → repeatable
          timeout: 60_000,
        },
        {
          command: `npm run dev -- --port ${webPort} --strictPort`,
          cwd: path.join(root, "web"),
          url: webBase,
          env: { API_PROXY_TARGET: `http://localhost:${apiPort}` },
          reuseExistingServer: false,
          timeout: 120_000,
        },
      ]
    : undefined,
});
