// Final device/navigation QA on the existing disposable part-coverage fixture.
// Run audit-listening-part-coverage.mjs --browser --stage2 --final first.
import {readFileSync,writeFileSync,mkdirSync,openSync} from 'node:fs';
import {resolve,dirname,join} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createRequire} from 'node:module';
import {spawn} from 'node:child_process';
import assert from 'node:assert/strict';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..');
const web=join(root,'web'),req=createRequire(pathToFileURL(join(web,'package.json')));
const read=p=>JSON.parse(readFileSync(p,'utf8'));
const fixture=read(join(root,'docs/listening-visual-audit/stage2/browser-evidence.json')).sandbox;
const registry=read(join(web,'src/features/listening/visual-materials.json')).parts;
const out=join(root,'docs/listening-final-release');mkdirSync(out,{recursive:true});
const log=openSync(join(fixture,'release-devices.log'),'w');
const server=spawn(process.execPath,[req.resolve('next/dist/bin/next'),'dev','--webpack','--hostname','127.0.0.1','--port','3393'],{cwd:fixture,stdio:['ignore',log,log]});
const cases=[],errors=[];
const ids=page=>page.locator('[data-source-asset]').evaluateAll(es=>es.map(e=>e.getAttribute('data-source-asset')));
const loaded=page=>page.waitForFunction(()=>[...document.querySelectorAll('[data-source-asset]')].every(e=>e.querySelector('img')?.naturalWidth>0));
const policy=(id,p)=>registry[`${id}-p${p}`].materials.map(m=>m.asset_id);
const visible=async(page,panel)=>{const button=page.getByRole('button',{name:panel==='source'?'Source material':'Questions',exact:true});if(await button.isVisible())await button.click();};
try{
 for(let i=0;i<120;i++){try{if((await fetch('http://127.0.0.1:3393/?exam=cambridge-04-test-01')).ok)break;}catch{}await new Promise(r=>setTimeout(r,250));}
 for(const [engine,mobile] of [['chromium',true],['webkit',false],['webkit',true]]){
  let browser;
  try{browser=await req('@playwright/test')[engine].launch({headless:true});}catch(error){cases.push({engine,mobile,status:'NOT VERIFIED',reason:String(error)});continue;}
  try{
   for(const [eid,pn] of [['cambridge-04-test-01',1],['cambridge-07-test-04',1],['cambridge-06-test-03',3]])for(const mode of ['exam','review']){
    const context=await browser.newContext({viewport:mobile?{width:390,height:844}:{width:1440,height:900},isMobile:mobile,hasTouch:mobile});
    const page=await context.newPage();page.setDefaultTimeout(20000);page.on('pageerror',e=>errors.push(e.message));
    const q=(pn-1)*10+1;await page.goto(`http://127.0.0.1:3393/?exam=${eid}&q=${q}&mode=${mode}`);await page.locator(`#question-${q}`).waitFor({state:'attached'});await loaded(page);
    assert.deepEqual(await ids(page),policy(eid,pn));await visible(page,'source');
    const source=page.getByRole('region',{name:'Listening source material'});assert(await source.isVisible());
    if(!mobile){const left=await source.boundingBox(),right=await page.getByRole('region',{name:'Listening questions'}).boundingBox();assert(left.x+left.width<=right.x+1);}
    await source.evaluate(e=>{e.scrollTop=e.scrollHeight;});await visible(page,'questions');
    const initial=await ids(page);await page.locator(`#question-${q+4}`).focus();assert.deepEqual(await ids(page),initial);
    let saved=null;
    if(mode==='exam'&&eid==='cambridge-04-test-01'){
     await page.getByLabel('Question 1',{exact:true}).fill('release local QA');const key=eid+'-q01';
     await page.waitForFunction(key=>window.__audit.attempt.answers[key]==='release local QA',key);
     await page.getByRole('button',{name:/^Part 2/}).click();await page.locator('#question-11').waitFor({state:'attached'});await loaded(page);assert.deepEqual(await ids(page),policy(eid,2));
     await page.getByRole('button',{name:/^Part 1/}).click();await page.locator('#question-1').waitFor({state:'attached'});await loaded(page);await visible(page,'questions');assert.equal(await page.getByLabel('Question 1',{exact:true}).inputValue(),'release local QA');assert.deepEqual(await ids(page),initial);saved='PASS (synthetic sync + Part return)';
    }
    if(eid==='cambridge-07-test-04')assert(await page.getByText('Write NO MORE THAN THREE WORDS AND/OR A NUMBER for each answer.',{exact:false}).count()>0);
    const screenshot=`${engine}-${mobile?'mobile':'desktop'}-${eid}-${mode}.png`;await visible(page,'source');await page.screenshot({path:join(out,screenshot)});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    cases.push({engine,mobile,test_id:eid,part:pn,mode,status:'PASS',all_material_ids:await ids(page),save_and_part_return:saved,c014_instruction:eid==='cambridge-07-test-04'?'Full verbatim word-limit instruction already present in question header; scan wear remains':null,screenshot});await context.close();
   }
  }finally{await browser.close();}
 }
 assert.equal(errors.length,0,JSON.stringify(errors));
}catch(error){errors.push(String(error));process.exitCode=1;}finally{server.kill('SIGTERM');}
writeFileSync(join(out,'device-browser-qa.json'),JSON.stringify({cases,page_errors:errors,scope:'Real page/Workspace/Review with existing localhost synthetic API fixture; no production mutations'},null,2)+'\n');
console.log(JSON.stringify({passed:cases.filter(c=>c.status==='PASS').length,not_verified:cases.filter(c=>c.status==='NOT VERIFIED').length,errors},null,2));
