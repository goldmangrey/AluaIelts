import { defineConfig, devices } from "@playwright/test";
import base from "./playwright.config";
export default defineConfig({
  ...base,
  webServer: { ...base.webServer, command: "pnpm start --hostname 127.0.0.1 --port 3100", url: "http://127.0.0.1:3100", cwd: process.env.ALUA_PHASE_B_TEST_APP ?? process.cwd() },
  projects: [
    { name: "contracts", testMatch: ["contracts.spec.ts", "auth-contracts.spec.ts"] },
    { name: "chromium", testMatch: "phase-b-pages.spec.ts", use: { ...devices["Desktop Chrome"] } },
    { name: "webkit", testMatch: "phase-b-pages.spec.ts", use: { ...devices["Desktop Safari"] } },
    { name: "mobile", testMatch: "phase-b-pages.spec.ts", use: { ...devices["iPhone 13"] } },
  ],
});
