import {createRequire} from 'node:module';
import {defineConfig} from '@playwright/test';
export default defineConfig({
  testDir:'./tests',testMatch:'lua-mascot.spec.ts',workers:1,reporter:'list',timeout:45000,
  outputDir:'.next/lua-tests',use:{baseURL:'http://127.0.0.1:3312',viewport:{width:1440,height:1000}},
  webServer:{command:`node "${createRequire(__filename).resolve('next/dist/bin/next')}" dev --webpack --hostname 127.0.0.1 --port 3312`,url:'http://127.0.0.1:3312',cwd:process.env.ALUA_REVIEW_TEST_APP,reuseExistingServer:false,timeout:120000},
});
