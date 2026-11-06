// Read-only production UI smoke. Private auth token file is never logged.
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {dirname,resolve,join} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createRequire} from 'node:module';
import assert from 'node:assert/strict';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..');
const req=createRequire(pathToFileURL(join(root,'web/package.json')));
const auth=JSON.parse(readFileSync('/tmp/alua-final-auth-private.json','utf8'));
const owner=JSON.parse(readFileSync('/tmp/alua-final-smoke-owner.json','utf8'));
const before=process.argv.includes('--before');
const out=join(root,'docs/listening-final-release');mkdirSync(out,{recursive:true});
const user={uid:auth.uid,email:auth.email,emailVerified:true,isAnonymous:false,providerData:[],stsTokenManager:{refreshToken:auth.refreshToken,accessToken:auth.idToken,expirationTime:Date.now()+Number(auth.expiresIn)*1000},apiKey:auth.apiKey,appName:'alua-web'};
const browser=await req('@playwright/test').chromium.launch({headless:true});
const cases=[],errors=[];let blockedWrites=0;
try{
 const context=await browser.newContext({viewport:{width:1440,height:900}});
 await context.addInitScript(({key,user})=>localStorage.setItem(key,JSON.stringify(user)),{key:`firebase:authUser:${auth.apiKey}:alua-web`,user});
 // Never save navigation/answer changes into an existing real attempt.
 await context.route('**/api/alua/listening/attempts/**',route=>{if(!['GET','HEAD'].includes(route.request().method())){blockedWrites++;return route.abort('blockedbyclient');}return route.continue();});
 const targets=[['review',owner.id],...(!before&&owner.in_progress_id?[['exam',owner.in_progress_id]]:[])];
 for(const [mode,id] of targets){
  const page=await context.newPage();page.setDefaultTimeout(35000);page.on('pageerror',e=>errors.push(e.message.slice(0,180)));
  await page.goto(`https://alua.study/listening/attempts/${id}${mode==='review'?'/review':''}`,{waitUntil:'domcontentloaded'});
  await page.locator('[id^="question-"]').first().waitFor({state:'attached'});
  await page.waitForFunction(()=>[...document.querySelectorAll('[data-source-asset]')].every(e=>e.querySelector('img')?.naturalWidth>0));
  if(!before&&mode==='review'){await page.getByRole('button',{name:/^Part 2/}).click();await page.locator('#question-11').waitFor({state:'attached'});await page.waitForFunction(()=>[...document.querySelectorAll('[data-source-asset]')].every(e=>e.querySelector('img')?.naturalWidth>0));}
  const actual=()=>page.locator('[data-source-asset]').evaluateAll(es=>es.map(e=>e.getAttribute('data-source-asset')));
  const initial=await actual();const source=page.getByRole('region',{name:'Listening source material'}),questions=page.getByRole('region',{name:'Listening questions'});
  const left=await source.boundingBox(),right=await questions.boundingBox();assert(left&&right&&left.x+left.width<=right.x+1);
  const count=await page.locator('[id^="question-"]').count();assert(count>0);
  await source.evaluate(e=>{e.scrollTop=120});const scroll=await source.evaluate(e=>e.scrollTop);
  const groups=page.locator('[data-question-group]');let focusStable=null;
  let focusTransition=null;
  if(await groups.count()>1){
   const current=await page.locator('[id^="question-"][data-current="true"]').first().getAttribute('id');
   for(let i=0;i<await groups.count();i++){
    const group=groups.nth(i);if(await group.locator('[data-current="true"]').count())continue;
    const target=group.locator('[id^="question-"]').first(),targetId=await target.getAttribute('id');await target.focus();
    await page.waitForFunction(id=>document.getElementById(id)?.getAttribute('data-current')==='true',targetId);
    focusStable=JSON.stringify(await actual())===JSON.stringify(initial);focusTransition={from:current,to:targetId};if(!before){assert(focusStable);assert.equal(await source.evaluate(e=>e.scrollTop),scroll);}break;
   }
  }
  const screenshot=`production-${before?'before':'after'}-${mode}.png`;
  await page.screenshot({path:join(out,screenshot),mask:[questions]});
  cases.push({mode,status:'PASS',question_nodes:count,source_asset_ids:initial,left_right:'PASS',focus_stable:focusStable,focus_transition:focusTransition,screenshot});await page.close();
 }
 assert.equal(errors.length,0,JSON.stringify(errors));
}catch(error){errors.push(String(error));process.exitCode=1;}finally{await browser.close();}
writeFileSync(join(out,`production-${before?'before':'after'}-browser.json`),JSON.stringify({cases,page_errors:errors,blocked_mutations:blockedWrites,scope:'Real alua.study, existing identity and attempts; writes blocked to preserve user state'},null,2)+'\n');
console.log(JSON.stringify({phase:before?'before':'after',cases:cases.map(c=>({mode:c.mode,status:c.status})),errors,blocked_mutations:blockedWrites}));
