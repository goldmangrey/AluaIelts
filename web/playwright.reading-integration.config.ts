import { createRequire } from "node:module";
import {defineConfig,devices} from "@playwright/test";
export default defineConfig({testDir:"./tests",testMatch:"reading-local-integration.spec.ts",outputDir:"test-results-reading-integration",workers:1,retries:0,reporter:"list",
 use:{baseURL:"http://127.0.0.1:3300",trace:"retain-on-failure"},
 projects:[{name:"local-chromium",use:{...devices["Desktop Chrome"],viewport:{width:1440,height:900}}},{name:"local-webkit",use:{...devices["Desktop Safari"],viewport:{width:1280,height:800}}}],
 webServer:{command:`node "${createRequire(__filename).resolve("next/dist/bin/next")}" start --hostname 127.0.0.1 --port 3300`,url:"http://127.0.0.1:3300",cwd:process.env.ALUA_C_TEST_APP,reuseExistingServer:false,env:{ALUA_C_FIXTURES:process.env.ALUA_C_FIXTURES??""}}
});
