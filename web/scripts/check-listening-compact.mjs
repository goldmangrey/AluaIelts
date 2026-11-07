// Local component browser measurements; isolated API/media fixture, never production.
import {execFileSync,spawn} from 'node:child_process';
import {readFileSync,writeFileSync,mkdirSync,openSync} from 'node:fs';
import {createRequire} from 'node:module';
import {dirname,resolve,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..'),req=createRequire(import.meta.url),before=process.argv.includes('--before');
const out=join(root,'docs/listening-compact-v5');mkdirSync(out,{recursive:true});
const {fixture}=process.env.ALUA_COMPACT_BASELINE_FIXTURE?{fixture:process.env.ALUA_COMPACT_BASELINE_FIXTURE}:JSON.parse(execFileSync(process.execPath,[join(root,'web/scripts/check-listening-ui.mjs'),'--prepare-only'],{encoding:'utf8'}));
const port=3398,url=`http://127.0.0.1:${port}`,log=openSync(join(fixture,'compact.log'),'w'),server=spawn(process.execPath,[req.resolve('next/dist/bin/next'),'dev','--webpack','--hostname','127.0.0.1','--port',String(port)],{cwd:fixture,stdio:['ignore',log,log]});
const wait=async fn=>{for(let n=0;n<150;n++){if(await fn())return;await new Promise(r=>setTimeout(r,100));}throw Error('Readiness timeout');};
const cases=[],errors=[],unverified=[];
const audioManifest=JSON.parse(readFileSync(join(root,'backend/app/content/listening_audio_v1/audio_manifest.json'),'utf8')).items;
const audioRoot=process.env.ALUA_LOCAL_LISTENING_AUDIO||join(process.env.HOME,'Desktop/Listening');
try{
 await wait(async()=>{try{return(await fetch(url)).ok;}catch{return false;}});
 for(const engine of before?['chromium']:['chromium','webkit']){
  let browser;try{browser=await req('@playwright/test')[engine].launch();}catch(e){unverified.push({engine,message:String(e)});continue;}
  try{for(const [width,height] of [[1440,900],[1366,768],[1280,720],[390,844],[375,667]]){
   const context=await browser.newContext({viewport:{width,height}}),page=await context.newPage();page.setDefaultTimeout(20000);
   page.on('pageerror',e=>errors.push(e.message));await page.route('**/*',r=>new URL(r.request().url()).hostname==='127.0.0.1'||r.request().url().startsWith('blob:')?r.continue():r.abort());await page.route('**/api/listening/authorize',r=>r.fulfill({json:{}}));await page.route('**/api/listening/audio/**',r=>{const part=Number(r.request().url().split('/').pop()),item=audioManifest.find(a=>a.exam_id==='cambridge-04-test-01'&&a.part_number===part),bytes=readFileSync(join(audioRoot,item.relative_path));return r.fulfill({status:200,contentType:'audio/mpeg',headers:{'Accept-Ranges':'bytes'},body:bytes});});
   await page.goto(url);await page.locator('#question-1').waitFor();await page.waitForFunction(()=>document.querySelector('audio')?.readyState>0);await page.waitForFunction(()=>[...document.querySelectorAll('[data-source-asset]')].every(e=>e.querySelector('img')?.naturalWidth>0));
   const metrics=await page.evaluate(()=>{const h=s=>document.querySelector(s)?.getBoundingClientRect().height||0;const player=document.querySelector('[aria-label="Listening audio player"]'),source=document.querySelector('[aria-label="Listening source material"]'),q=document.querySelector('[aria-label="Listening questions"]');return {header:h('main>div>div:first-child'),player:player.getBoundingClientRect().height,footer:h('main>footer'),workspace:Math.max(source.getBoundingClientRect().height,q.getBoundingClientRect().height),workspaceBottom:q.getBoundingClientRect().bottom,leftBeforeRight:source.getBoundingClientRect().right<=q.getBoundingClientRect().left+1,overflow:document.documentElement.scrollWidth>innerWidth+1};});
   if(!before){
    assert.equal(metrics.footer,0);assert(!metrics.overflow);assert(metrics.header<=44);assert(metrics.player<=112);assert.equal(metrics.workspaceBottom,height);if(width>=760)assert(metrics.leftBeforeRight);
    const nav=page.getByRole('button',{name:'Question navigator',exact:true});await nav.click();const grid=page.getByRole('dialog',{name:'Questions',exact:true});await grid.waitFor();assert.equal(await grid.getByRole('button',{name:/^Go to question/}).count(),40);await page.keyboard.press('Escape');await wait(()=>nav.evaluate(e=>e===document.activeElement));
    await nav.click();await grid.getByRole('button',{name:'Go to question 21',exact:true}).click();await page.locator('#question-21').waitFor({state:'attached'});await nav.click();await page.mouse.click(2,height-2);assert(!(await grid.isVisible()));
    await page.getByRole('button',{name:'Finish',exact:true}).click();await page.getByRole('dialog',{name:'Finish this practice?',exact:true}).waitFor();await page.keyboard.press('Escape');
    assert.equal(await page.getByText(/^(Saving on device…|Saved on device|Syncing…|All changes saved)$/).count(),0);
    await page.getByRole('region',{name:'Listening audio player'}).getByRole('button',{name:/^Part 1/}).click();await page.locator('#question-1').waitFor({state:'attached'});await page.waitForFunction(()=>[...document.querySelectorAll('[data-source-asset]')].every(e=>e.querySelector('img')?.naturalWidth>0));await page.getByRole('button',{name:'Finish',exact:true}).evaluate(e=>e.blur());await page.screenshot({path:join(out,`${engine}-${width}x${height}.png`)});
   }else if(width===1440||width===390)await page.screenshot({path:join(out,`before-${width}x${height}.png`)});
   cases.push({engine,width,height,...metrics,status:'PASS'});await context.close();
  }}finally{await browser.close();}
 }
}catch(e){errors.push(e.stack||String(e));process.exitCode=1;}finally{server.kill('SIGTERM');}
writeFileSync(join(out,before?'before.json':'browser-qa.json'),JSON.stringify({cases,errors,unverified},null,2)+'\n');console.log(JSON.stringify({cases,errors,unverified}));
