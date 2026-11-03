import { defineConfig, devices } from "@playwright/test";
export default defineConfig({
  testDir: "./tests", workers: 1, reporter: "list",
  use: { baseURL: "http://127.0.0.1:3350" },
  projects: [
    { name: "contracts", testMatch: "smart-translate-contracts.spec.ts" },
    { name: "desktop", testMatch: "smart-translate-browser.spec.ts", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", testMatch: "smart-translate-browser.spec.ts", use: { ...devices["iPhone 13"] } },
  ],
  webServer: process.env.ALUA_TRANSLATE_APP ? { command: `node "${process.cwd()}/node_modules/next/dist/bin/next" dev --webpack --hostname 127.0.0.1 --port 3350`, cwd: process.env.ALUA_TRANSLATE_APP, url: "http://127.0.0.1:3350", reuseExistingServer: false, timeout: 120000 } : undefined,
});
