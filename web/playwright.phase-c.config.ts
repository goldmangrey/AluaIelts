import { createRequire } from "node:module";
import { defineConfig, devices } from "@playwright/test";
export default defineConfig({
  testDir: "./tests", fullyParallel: true, workers: 3, retries: 0, reporter: "list", forbidOnly: !!process.env.CI,
  use: { baseURL: "http://127.0.0.1:3300", trace: "retain-on-failure" },
  projects: [
    { name: "contracts", testMatch: "reading-contracts.spec.ts" },
    { name: "chromium", testMatch: "reading-browser.spec.ts", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 1000 } } },
    { name: "webkit", testMatch: "reading-browser.spec.ts", use: { ...devices["Desktop Safari"], viewport: { width: 1280, height: 900 } } },
    { name: "firefox", testMatch: "reading-browser.spec.ts", use: { ...devices["Desktop Firefox"], viewport: { width: 1920, height: 1080 } } },
    { name: "mobile", testMatch: "reading-mobile.spec.ts", use: { ...devices["iPhone 13"] } },
  ],
  webServer: { command: `node "${createRequire(__filename).resolve("next/dist/bin/next")}" start --hostname 127.0.0.1 --port 3300`, url: "http://127.0.0.1:3300", cwd: process.env.ALUA_C_TEST_APP, reuseExistingServer: false, env: { ALUA_C_FIXTURES: process.env.ALUA_C_FIXTURES ?? "" } },
});
