// Real Listening UI/IndexedDB and authenticated-image cache; isolated synthetic API.
import {execFileSync,spawn} from 'node:child_process';
import {readFileSync,writeFileSync,openSync,mkdirSync} from 'node:fs';
import {resolve,dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import assert from 'node:assert/strict';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..'),web=join(root,'web'),req=createRequire(import.meta.url);
const {fixture}=JSON.parse(execFileSync(process.execPath,[join(web,'scripts/check-listening-ui.mjs'),'--prepare-only'],{encoding:'utf8'}));
const apiPath=join(fixture,'src/lib/api/client.ts');let api=readFileSync(apiPath,'utf8');api=api.replace("return structuredClone(path.endsWith('/review')","localStorage.setItem('server',JSON.stringify(f));return structuredClone(path.endsWith('/review')");writeFileSync(apiPath,api);
const clientPath=join(fixture,'src/app/client.tsx');let client=readFileSync(clientPath,'utf8');client=client.replace('localStorage.clear();','').replace("R(true)},[exam])","const saved=localStorage.getItem('server');if(saved)(window as any).__audit=JSON.parse(saved);R(true)},[exam])");writeFileSync(clientPath,client);
const url='http://127.0.0.1:3396',log=openSync(join(fixture,'navigation.log'),'w'),server=spawn(process.execPath,[req.resolve('next/dist/bin/next'),'dev','--webpack','--hostname','127.0.0.1','--port','3396'],{cwd:fixture,stdio:['ignore',log,log]});
const wait=async fn=>{for(let i=0;i<150;i++){if(await fn())return;await new Promise(r=>setTimeout(r,100));}throw Error('Readiness timeout');};
const cases=[],errors=[],unverified=[];let stage='boot';
try{
 await wait(async()=>{try{return(await fetch(url)).ok;}catch{return false;}});
 for(const engine of ['chromium','webkit']){
  let browser;try{browser=await req('@playwright/test')[engine].launch();}catch(e){unverified.push({engine,error:String(e)});continue;}
  try{for(const mobile of [false,true])for(const mode of ['exam','review']){
   stage=`${engine}/${mobile}/${mode}`;const context=await browser.newContext({viewport:mobile?{width:390,height:844}:{width:1440,height:900},isMobile:mobile,hasTouch:mobile}),page=await context.newPage(),gets=new Map();page.on('request',r=>{if(new URL(r.url()).pathname.startsWith('/asset/'))gets.set(r.url(),(gets.get(r.url())||0)+1);});page.on('pageerror',e=>errors.push(stage+': '+e.message));
   await page.route('**/*',r=>(new URL(r.request().url()).hostname==='127.0.0.1'||r.request().url().startsWith('blob:'))?r.continue():r.abort());await page.route('**/api/listening/authorize',r=>r.fulfill({json:{}}));await page.route('**/api/listening/audio/**',r=>r.fulfill({status:404}));
   stage+=':initial';await page.goto(url+'/?mode='+mode);const player=page.getByRole('region',{name:'Listening audio player'});
   await page.locator('#question-1').waitFor();
   const view=async p=>{await player.getByRole('button',{name:new RegExp('^Part '+p)}).click();await page.locator('#question-'+((p-1)*10+1)).waitFor({state:'attached'});};
   const ready=()=>wait(()=>page.locator('[data-source-asset] > button img').evaluateAll(images=>images.length>0&&images.every(img=>img.complete&&img.naturalWidth>0)));
   stage+=':images';await ready();await page.waitForLoadState('networkidle');
   const source=page.locator('[aria-label="Listening source material"]'),questions=page.locator('[aria-label="Listening questions"]');
   const panel=async name=>{const button=page.getByRole('button',{name,exact:true});if(await button.isVisible())await button.click();};
   await panel('Source material');await source.evaluate(e=>{e.scrollTop=100;});await page.waitForTimeout(40);const expected=await source.evaluate(e=>e.scrollTop);await panel('Questions');await questions.evaluate(e=>{e.scrollTop=130;});await page.waitForTimeout(40);
   const right=await questions.evaluate(e=>e.scrollTop);
   stage+=':switch';for(const p of [2,3,1,4,1]){await view(p);await ready();assert.equal(await page.getByText('Loading original image…',{exact:true}).count(),0);}
   await panel('Source material');assert.equal(await source.evaluate(e=>e.scrollTop),expected);await panel('Questions');assert.equal(await questions.evaluate(e=>e.scrollTop),right);
   const before=[...gets.values()].reduce((n,v)=>n+v,0);for(const p of [2,3,1]){await view(p);await ready();}assert.equal([...gets.values()].reduce((n,v)=>n+v,0),before);assert([...gets.values()].every(n=>n===1));
   if(mode==='exam'){
    await panel('Questions');await page.getByLabel('Question 1',{exact:true}).fill('navigation fixture');await page.waitForFunction(async()=>new Promise(resolve=>{const r=indexedDB.open('alua-reading-drafts',1);r.onsuccess=()=>{const tx=r.result.transaction('drafts'),q=tx.objectStore('drafts').getAll();q.onsuccess=()=>{resolve(q.result.some(d=>Object.values(d.answers).includes('navigation fixture')));r.result.close();};};}));
    const other=await context.newPage();await other.goto(url);await page.bringToFront();stage+=':two-tabs';await wait(async()=>await page.getByLabel('Question 1',{exact:true}).isDisabled()||await other.getByLabel('Question 1',{exact:true}).isDisabled());
    const disabled=[await page.getByLabel('Question 1',{exact:true}).isDisabled(),await other.getByLabel('Question 1',{exact:true}).isDisabled()];assert.equal(disabled.filter(Boolean).length,1,'Only one tab may edit');assert((await page.locator('body').innerText()+await other.locator('body').innerText()).includes('Open in another tab · Read only'));await other.close();
    stage+=':reload';await page.reload();await page.getByLabel('Question 1',{exact:true}).waitFor();assert.equal(await page.getByLabel('Question 1',{exact:true}).inputValue(),'navigation fixture');assert.equal(await page.getByLabel('Question 1',{exact:true}).isEnabled(),true);
   }
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));cases.push({engine,mobile,mode,status:'PASS',duplicateAssetGetsOnReturn:0,uniqueRequests:gets.size,scroll:'PASS',indexedDB:mode==='exam'?'durable reload + two-tab lease PASS':'readonly'});await context.close();
  }}finally{await browser.close();}
 }
 assert.equal(errors.length,0,JSON.stringify(errors));
}catch(e){errors.push(stage+': '+String(e));process.exitCode=1;}finally{server.kill('SIGTERM');}
const out=join(root,'docs/exam-reliability');mkdirSync(out,{recursive:true});writeFileSync(join(out,'navigation-qa.json'),JSON.stringify({cases,errors,unverified,fixture},null,2)+'\n');console.log(JSON.stringify({cases,errors,unverified,fixture}));
