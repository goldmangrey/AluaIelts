import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./tests',testMatch:'ai-ux-hotfix.spec.ts',outputDir:'.next/ai-ux-tests',workers:1,timeout:60000,reporter:'list',
 use:{baseURL:'http://127.0.0.1:3315'},projects:[{name:'chromium-desktop',use:{browserName:'chromium',viewport:{width:1366,height:900}}},{name:'webkit-mobile',use:{browserName:'webkit',viewport:{width:390,height:844},isMobile:true}}],
 webServer:{command:`node /Users/yeskendir/Projects/Alua/web/node_modules/next/dist/bin/next dev --webpack --hostname 127.0.0.1 --port 3315`,cwd:process.env.ALUA_REVIEW_TEST_APP,url:'http://127.0.0.1:3315',timeout:120000,reuseExistingServer:false}});
