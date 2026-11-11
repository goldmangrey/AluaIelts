import { createRequire } from "node:module";
import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests", testMatch: "review-focus.spec.ts", outputDir: ".next/review-focus-tests", workers: 2, reporter: "list", timeout: 45000,
  use: { baseURL: "http://127.0.0.1:3312", trace: "retain-on-failure" },
  projects: (["chromium", "webkit"] as const).flatMap(browserName => [[1440,900],[1366,768],[1280,720],[390,844],[375,667]].map(([width,height])=>({ name: `${browserName}-${width}`, use: { browserName, viewport: { width: width!, height: height! }, ...(width!<700?{isMobile:true,deviceScaleFactor:2}: {}) } }))),
  webServer: { command: `node "${createRequire(__filename).resolve("next/dist/bin/next")}" ${process.env.ALUA_REVIEW_PRODUCTION === "1" ? "start" : "dev --webpack"} --hostname 127.0.0.1 --port 3312`, url: "http://127.0.0.1:3312", cwd: process.env.ALUA_REVIEW_TEST_APP, reuseExistingServer: false, timeout: 120000 },
});
