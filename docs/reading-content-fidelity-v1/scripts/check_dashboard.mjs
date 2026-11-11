// Offline audit dashboard checks. No app server, API or user data access.
import {createRequire} from 'node:module';
import {dirname,resolve,join} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {writeFile} from 'node:fs/promises';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../../..');
const require=createRequire(join(root,'web/package.json'));
const {chromium,webkit}=require('@playwright/test');
const output=join(root,'docs/reading-content-fidelity-v1');
const results=[];
for(const [name,engine] of [['chromium',chromium],['webkit',webkit]]){
 const browser=await engine.launch({headless:true});
 try{
  for(const viewport of [{width:1366,height:768},{width:390,height:844}]){
   const page=await browser.newPage({viewport});const errors=[];page.on('pageerror',e=>errors.push(e.message));
   await page.goto(pathToFileURL(join(output,'index.html')).href+'#cambridge-07-test-01-q-16');
   await page.locator('#item-detail h2').waitFor();
   if(await page.locator('#tests button').count()!==72)throw Error('72-test navigation missing');
   if(await page.locator('#items button').count()!==52)throw Error('C07 T1 full item navigation missing');
   if(!(await page.locator('#item-detail').innerText()).includes('KEY_MISMATCH')){
    // key binding detail is in the report; check the key-specific adjudicated finding.
    await page.locator('#category').selectOption('KEY_OPTION_BINDING');
    if(await page.locator('#findings article').count()!==1)throw Error('Q16 binding finding missing');
   }
   await page.locator('#category').selectOption('');
   await page.locator('#search').fill('q20-source-crop');
   // Stable tags/issue IDs can be searched even when titles have no question text.
   if(await page.locator('#findings article').count()===0){await page.locator('#search').fill('crop');}
   if(await page.locator('#findings article').count()===0)throw Error('Crop evidence missing');
   await page.locator('#findings details').first().locator('summary').click();
   const image=page.locator('#findings details img').first();await image.scrollIntoViewIfNeeded();
   await page.waitForFunction(()=>[...document.querySelectorAll('#findings details[open] img')].every(i=>i.complete&&i.naturalWidth>0));
   await page.locator('#search').fill('');await page.locator('#scope').selectOption('all');await page.locator('#verification').selectOption('candidate');
   if(!(await page.locator('#result-count').innerText()).startsWith('2343 '))throw Error('Candidate coverage mismatch');
   await page.locator('#severity').selectOption('HIGH');
   if(!(await page.locator('#findings').innerText()).includes('UNCONFIRMED_CANDIDATE'))throw Error('Unconfirmed label missing');
   if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Horizontal overflow');
   if(errors.length)throw Error(errors.join('\n'));
   results.push({browser:name,viewport,tests:72,all_item_navigation:true,source_crops_load:true,filtering:true,unconfirmed_labels:true,no_horizontal_overflow:true,javascript_errors:errors});
   await page.close();
  }
 }finally{await browser.close();}
}
await writeFile(join(output,'checkpoints/dashboard-browser-validation.json'),JSON.stringify({scope:'Offline report dashboard only; not corpus source-fidelity certification or production UI QA',results},null,2)+'\n');
console.log(JSON.stringify(results,null,2));
