import {defineConfig,devices} from "@playwright/test";
export default defineConfig({testDir:"./tests",testMatch:"workers.spec.ts",outputDir:"test-results-workers",workers:1,retries:0,reporter:"list",
 use:{...devices["Desktop Chrome"],baseURL:"http://127.0.0.1:8787",trace:"retain-on-failure"},
 webServer:[
  {command:`node "${process.env.ALUA_WORKERS_ADAPTER_CLI}" preview --port 8787 --ip 127.0.0.1`,cwd:process.cwd(),url:"http://127.0.0.1:8787",reuseExistingServer:!process.env.CI,env:{WRANGLER_SEND_METRICS:"false"}},
  {command:`node "${process.env.ALUA_WORKERS_ADAPTER_CLI}" preview --port 8791 --ip 127.0.0.1`,cwd:process.env.ALUA_WORKERS_TEST_APP,url:"http://127.0.0.1:8791",reuseExistingServer:false,env:{NEXT_PUBLIC_API_BASE_URL:"http://127.0.0.1:8899/api/v1",WRANGLER_SEND_METRICS:"false"}},
 ]});
