import { createRequire } from "node:module";
import { defineConfig } from "@playwright/test";
const port=process.env.ALUA_GUEST_TEST?3313:3312;
export default defineConfig({
  testDir: "./tests", testMatch: process.env.ALUA_GUEST_TEST ? "guest-experience.spec.ts" : "results-v2.spec.ts", outputDir: process.env.ALUA_GUEST_TEST ? ".next/guest-test-results" : "test-results-results-v2", workers: 2, reporter: "list",
  use: { baseURL: `http://127.0.0.1:${port}`, trace: "retain-on-failure" },
  projects: process.env.ALUA_GUEST_TEST ? [{name:"guest-desktop",use:{browserName:"chromium",viewport:{width:1440,height:1000}}},{name:"guest-mobile",use:{browserName:"webkit",viewport:{width:320,height:844}}}] : [
    { name: "desktop-1440", use: { browserName: "chromium", viewport: { width: 1440, height: 900 } } },
    { name: "desktop-1366", use: { browserName: "chromium", viewport: { width: 1366, height: 768 } } },
    { name: "mobile-390", use: { browserName: "chromium", viewport: { width: 390, height: 844 }, isMobile: true, deviceScaleFactor: 2 } },
  ],
  webServer: { command: `node "${createRequire(__filename).resolve("next/dist/bin/next")}" ${process.env.ALUA_REVIEW_PRODUCTION === "1" ? "start" : "dev --webpack"} --hostname 127.0.0.1 --port ${port}`, url: `http://127.0.0.1:${port}`, cwd: process.env.ALUA_REVIEW_TEST_APP, reuseExistingServer: false, timeout: 120000 },
});
