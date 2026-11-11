import { createRequire } from "node:module";
import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests", testMatch: "results-v2.spec.ts", outputDir: "test-results-results-v2", workers: 2, reporter: "list",
  use: { baseURL: "http://127.0.0.1:3312", trace: "retain-on-failure" },
  projects: [
    { name: "desktop-1440", use: { browserName: "chromium", viewport: { width: 1440, height: 900 } } },
    { name: "desktop-1366", use: { browserName: "chromium", viewport: { width: 1366, height: 768 } } },
    { name: "mobile-390", use: { browserName: "chromium", viewport: { width: 390, height: 844 }, isMobile: true, deviceScaleFactor: 2 } },
  ],
  webServer: { command: `node "${createRequire(__filename).resolve("next/dist/bin/next")}" ${process.env.ALUA_REVIEW_PRODUCTION === "1" ? "start" : "dev --webpack"} --hostname 127.0.0.1 --port 3312`, url: "http://127.0.0.1:3312", cwd: process.env.ALUA_REVIEW_TEST_APP, reuseExistingServer: false, timeout: 120000 },
});
