import { createRequire } from "node:module";
import {defineConfig,devices} from "@playwright/test";
export default defineConfig({testDir:"./tests",outputDir:"test-results-reading-release",workers:1,retries:0,reporter:"list",fullyParallel:true,
 use:{baseURL:"http://127.0.0.1:3300",trace:"retain-on-failure"},
 projects:[{name:"release-contracts",testMatch:"reading-release-contracts.spec.ts"},{name:"release-chromium",testMatch:"reading-release-browser.spec.ts",use:{...devices["Desktop Chrome"],viewport:{width:1440,height:900}}},{name:"release-webkit",testMatch:"reading-release-browser.spec.ts",use:{...devices["Desktop Safari"],viewport:{width:1280,height:800}}},{name:"release-mobile-webkit",testMatch:"reading-release-mobile.spec.ts",use:{...devices["iPhone 13"]}},{name:"release-mobile-chrome",testMatch:"reading-release-mobile.spec.ts",use:{...devices["Pixel 7"]}}],
 webServer:{command:`node "${createRequire(__filename).resolve("next/dist/bin/next")}" start --hostname 127.0.0.1 --port 3300`,url:"http://127.0.0.1:3300",cwd:process.env.ALUA_C_TEST_APP,reuseExistingServer:false,env:{ALUA_C_FIXTURES:process.env.ALUA_C_FIXTURES??""}}
});
