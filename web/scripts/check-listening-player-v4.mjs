// Real local Cambridge audio + real Exam/Review components; synthetic auth/attempt API.
import {readFileSync,writeFileSync,openSync,mkdirSync} from 'node:fs';
import {resolve,dirname,join} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createRequire} from 'node:module';
import {execFileSync,spawn} from 'node:child_process';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {runInNewContext} from 'node:vm';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..'),web=join(root,'web'),req=createRequire(pathToFileURL(join(web,'package.json')));
const read=p=>JSON.parse(readFileSync(p,'utf8'));
const manifest=read(join(web,'src/features/listening/waveform-manifest.json'));
const audioManifest=read(join(root,'backend/app/content/listening_audio_v1/audio_manifest.json')).items;
const audioRoot=process.env.ALUA_LOCAL_LISTENING_AUDIO||join(process.env.HOME,'Desktop/Listening');
let validated=0;
for(const [eid,entry] of Object.entries(manifest.exams)){
 const bytes=readFileSync(join(web,'public',entry.url));assert.equal(createHash('sha256').update(bytes).digest('hex'),entry.sha256);
 const doc=JSON.parse(bytes);
 for(const [part,track] of Object.entries(doc.parts)){
  const item=audioManifest.find(a=>a.exam_id===eid&&a.part_number===Number(part));
  assert.equal(track.source_sha256,createHash('sha256').update(readFileSync(join(audioRoot,item.relative_path))).digest('hex'));
  assert(track.peaks.length===2048&&track.peaks.every(v=>Number.isInteger(v)&&v>=0&&v<=255)&&track.duration>0);validated++;
 }
}
assert.equal(validated,288);
// Persistence identities and graceful in-memory fallback.
const cell={exports:{}},memory=new Map(),scope={module:null,exports:null,require:()=>manifest,localStorage:{getItem:k=>memory.get(k)||null,setItem:(k,v)=>memory.set(k,v)}};
scope.module=cell;scope.exports=cell.exports;
runInNewContext(req('typescript').transpileModule(readFileSync(join(web,'src/features/listening/audio-progress.ts'),'utf8'),{compilerOptions:{target:99,module:1,esModuleInterop:true}}).outputText,scope);
const {AudioProgress}=cell.exports,eid='cambridge-04-test-01';
const first=new AudioProgress('A','attempt',eid);first.set(1,180);first.set(2,75);
assert.equal(new AudioProgress('A','attempt',eid).get(1),180);
for(const [uid,id,exam] of [['B','attempt',eid],['A','other',eid],['A','attempt','cambridge-04-test-02']])assert.equal(new AudioProgress(uid,id,exam).get(1),0);
scope.localStorage={getItem:()=>{throw Error('Storage unavailable');},setItem:()=>{throw Error('Storage unavailable');}};
const fallback=new AudioProgress('A','memory',eid);fallback.set(3,42);assert.equal(fallback.get(3),42);
const {fixture}=JSON.parse(execFileSync(process.execPath,[join(web,'scripts/check-listening-ui.mjs'),'--prepare-only'],{encoding:'utf8'}));
const put=(p,s)=>writeFileSync(join(fixture,p),s);
put('src/app/page.tsx',`import {readFile} from 'node:fs/promises';import Client from './client';export const dynamic='force-dynamic';export default async function Page({searchParams}:{searchParams:Promise<Record<string,string>>}){const q=await searchParams,id=q.exam||'cambridge-04-test-01';if(!/^cambridge-\\d{2}-test-\\d{2}$/.test(id))throw Error('Invalid exam');return <Client exam={JSON.parse(await readFile(${JSON.stringify(join(root,'backend/app/content/listening_v1/exams/'))}+id+'.json','utf8'))} mode={q.mode||'exam'}/>}`);
put('src/app/client.tsx',`'use client';import {useState,useEffect} from 'react';import {ListeningPage} from '@/features/listening/pages';import type {Exam} from '@/features/listening/models';export default function Client({exam,mode}:{exam:Exam;mode:string}){const [ready,R]=useState(false);useEffect(()=>{const saved=sessionStorage.getItem('server:'+exam.exam_id);const rows=exam.parts.flatMap(p=>p.groups.flatMap(g=>g.questions.map(q=>({question_id:q.question_id,question_number:q.question_number,part_number:p.part_number,user_answer:'wrong',correct:false,correct_answer:'fixture-only correction',grading_issue:null,key_verified:true}))));(window as any).__audit=saved?JSON.parse(saved):{attempt:{id:'local-ui',version:1,content_hash:exam.exam_id,status:'in_progress',answers:{},state:{displayed_part:1,current_question:1,audio_part:1,playback_seconds:0,marked:[]},exam},result:{attempt_id:'local-ui',mode:'verified',label:'Local only',correct_count:0,total_questions:40,graded_count:40,answered_count:40,accuracy:0,estimated_band:null,band_table_version:null,parts:[],questions:rows,exam,grading_issues:{}}};R(true)},[exam]);return ready?<ListeningPage kind={mode==='review'?'review':'attempt'} id='local-ui'/>:null}`);
let api=readFileSync(join(fixture,'src/lib/api/client.ts'),'utf8');
api=api.replace("return structuredClone(path.endsWith('/review')", "sessionStorage.setItem('server:'+f.attempt.exam.exam_id,JSON.stringify(f));return structuredClone(path.endsWith('/review')");put('src/lib/api/client.ts',api);
const port=3397,url=`http://127.0.0.1:${port}`,out=join(root,'docs/listening-player-v4');mkdirSync(out,{recursive:true});
const log=openSync(join(fixture,'v4.log'),'w'),server=spawn(process.execPath,[req.resolve('next/dist/bin/next'),'dev','--webpack','--hostname','127.0.0.1','--port',String(port)],{cwd:fixture,stdio:['ignore',log,log]});
const cases=[],errors=[],unverified=[];let stage='boot',diagnostic=async()=>'';
const wait=async check=>{for(let i=0;i<150;i++){if(await check())return;await new Promise(r=>setTimeout(r,100));}throw Error('Timed out: '+stage+' '+await diagnostic());};
try{
 await wait(async()=>{try{return (await fetch(url)).ok;}catch{return false;}});
 for(const engine of (process.argv.includes('--webkit-only')?['webkit']:['chromium','webkit'])){
  let browser;try{browser=await req('@playwright/test')[engine].launch({headless:true});}catch(e){unverified.push({engine,reason:String(e)});continue;}
  try{for(const mobile of [false,true])for(const mode of ['exam','review']){
   const context=await browser.newContext({viewport:mobile?{width:390,height:844}:{width:1440,height:900},isMobile:mobile,hasTouch:mobile}),page=await context.newPage();page.setDefaultTimeout(20000);page.on('pageerror',e=>errors.push(e.message));
   await page.route('**/*',route=>new URL(route.request().url()).hostname==='127.0.0.1'||route.request().url().startsWith('blob:')?route.continue():route.abort());
   await page.route('**/api/listening/authorize',r=>r.fulfill({json:{}}));
   const buffers=new Map();let audioFetches=0;
   await page.route('**/api/listening/audio/**',route=>{
    if(route.request().resourceType()==='fetch')audioFetches++;
    const eid=new URL(page.url()).searchParams.get('exam')||'cambridge-04-test-01',part=Number(route.request().url().split('/').pop());
    const item=audioManifest.find(a=>a.exam_id===eid&&a.part_number===part),path=join(audioRoot,item.relative_path);
    if(!buffers.has(path))buffers.set(path,readFileSync(path));const bytes=buffers.get(path);
    const range=/^bytes=(\d+)-(\d*)$/.exec(route.request().headers().range||'');
    const start=range?Number(range[1]):0,end=range&&range[2]?Math.min(bytes.length-1,Number(range[2])):bytes.length-1;
    return route.fulfill({status:range?206:200,contentType:'audio/mpeg',headers:{'Accept-Ranges':'bytes','Content-Length':String(end-start+1),...(range?{'Content-Range':`bytes ${start}-${end}/${bytes.length}`}:{})},body:bytes.subarray(start,end+1)});
   });
   await page.route('**/api/listening/review',route=>{
    const n=route.request().postDataJSON().question_number;
    return route.fulfill({json:{what_happened:'Local evidence playback QA',why:'Synthetic explanation only',next_time:'Listen again',evidence:{available:true,reason:null,part:Math.ceil(n/10),quote:'Local fixture',segment_ids:['fixture-only'],clip_start:1.5,clip_end:2.2}}});
   });
   const player=page.getByRole('region',{name:'Listening audio player'}),audio=page.locator('audio').first();
   diagnostic=async()=>JSON.stringify(await page.evaluate(()=>{const a=document.querySelector('audio');return {time:a?.currentTime,paused:a?.paused,src:a?.currentSrc,ready:a?.readyState,duration:a?.duration,status:document.querySelector('[role=status]')?.textContent,alerts:[...document.querySelectorAll('[role=alert]')].map(e=>e.textContent)};}));
   const native=()=>audio.evaluate(el=>({time:el.currentTime,paused:el.paused,src:el.currentSrc,duration:el.duration,ready:el.readyState}));
   const ready=async part=>wait(async()=>{const a=await native();return a.ready>=1&&a.src.endsWith('/'+part);});
   const view=async part=>{await player.getByRole('button',{name:new RegExp('^Part '+part)}).click();await page.locator('#question-'+((part-1)*10+1)).waitFor({state:'attached'});};
   const listen=async part=>{await view(part);await player.getByRole('button',{name:`Listen to Part ${part}`,exact:true}).click();stage+=' ready '+part;await ready(part);stage+=' playing '+part;await wait(async()=>!(await native()).paused);};
   const pause=async()=>{const b=player.getByRole('button',{name:'Pause',exact:true});if(!(await native()).paused){await b.waitFor({state:'visible'});await b.click();}await wait(async()=>(await native()).paused);};
   const start=async()=>{await player.getByRole('button',{name:'Play',exact:true}).click();await wait(async()=>!(await native()).paused);};
   const position=async seconds=>{await page.getByLabel('Audio progress').fill(String(Math.floor(seconds*10)/10));await wait(async()=>Math.abs((await native()).time-seconds)<2);};
   const store=()=>page.evaluate(()=>{const key=Object.keys(localStorage).find(k=>k.startsWith('alua:listening:audio:v1:'));return key?JSON.parse(localStorage.getItem(key)):null;});
   stage=`${engine}/${mobile}/${mode}: initial`;await page.goto(url+'/?mode='+mode);await ready(1);await page.locator('[data-waveform-source=audio]').waitFor();assert((await native()).duration>180);
   stage=`${engine}/${mobile}/${mode}: navigation`;await start();await position(180);await view(2);assert((await native()).src.endsWith('/1')&&!(await native()).paused&&(await native()).time>=180);
   await view(1);assert((await native()).time>=180);
   if(mode==='exam'){
    await page.getByLabel('Question 1',{exact:true}).fill('player V4 QA');
    await page.waitForFunction(()=>window.__audit.attempt.answers['cambridge-04-test-01-q01']==='player V4 QA');
    assert((await native()).src.endsWith('/1')&&!(await native()).paused);
   }
   await pause();const saved1=(await native()).time;
   stage=`${engine}/${mobile}/${mode}: switch`;await listen(2);await pause();await position(75);await pause();const saved2=(await native()).time;await listen(1);assert(Math.abs((await native()).time-saved1)<2);await pause();
   stage=`${engine}/${mobile}/${mode}: reload`;await page.reload();await ready(1);assert((await native()).paused&&Math.abs((await native()).time-saved1)<2);if(mode==='exam')assert.equal(await page.getByLabel('Question 1',{exact:true}).inputValue(),'player V4 QA');
   stage=`${engine}/${mobile}/${mode}: seek`;await position(180);await player.getByRole('button',{name:'Forward 5 seconds'}).click();assert(Math.abs((await native()).time-185)<.2);await player.getByRole('button',{name:'Back 5 seconds'}).click();assert(Math.abs((await native()).time-180)<2);
   // Real pointer + keyboard seek, in addition to range input changes.
   const rail=page.getByLabel('Audio progress'),rect=await rail.boundingBox();await rail.click({position:{x:rect.width*.25,y:rect.height/2}});const pointerTime=(await native()).time;
   if(mobile){await rail.tap({position:{x:rect.width*.5,y:rect.height/2}});assert(Math.abs((await native()).time-(await native()).duration*.5)<10);}
   await rail.focus();const beforeKey=(await native()).time;await page.keyboard.press('ArrowRight');assert((await native()).time>beforeKey);assert(pointerTime>0);await position(180);
   if(mode==='review'){const beforeMoment=await store();stage=`${engine}/${mobile}/${mode}: AI`;
    const go=async n=>{await page.getByRole('button',{name:'Question navigator',exact:true}).click();await page.getByRole('button',{name:`Go to question ${n}`,exact:true}).click();};
    await go(2);await page.locator('#question-2').getByRole('button',{name:'Explain with AI'}).click();
    await page.getByRole('button',{name:'Play Moment',exact:true}).click();
    await wait(async()=>{const a=await native();return a.paused&&a.time>178;});assert(Math.abs((await native()).time-180)<2);assert.equal((await store()).positions[1],beforeMoment.positions[1]);
    await go(12);await page.locator('#question-12').getByRole('button',{name:'Explain with AI'}).click();await page.getByRole('button',{name:'Loop Moment',exact:true}).click();await ready(2);
    await audio.evaluate(el=>{el.dataset.loops='0';el.addEventListener('seeked',()=>{if(el.currentTime<1.7)el.dataset.loops=String(Number(el.dataset.loops)+1);});});
    await wait(async()=>Number(await audio.getAttribute('data-loops'))>=2);
    assert.equal((await store()).positions[1],beforeMoment.positions[1]);assert.equal((await store()).positions[2],beforeMoment.positions[2]);assert.equal(await page.locator('audio').evaluateAll(es=>es.filter(e=>!e.paused).length),1);
    await page.getByRole('button',{name:'Loop Moment',exact:true}).click();await ready(1);assert((await native()).paused&&Math.abs((await native()).time-180)<2);
   }
   // The same identity/attempt ID on a different exam must not reuse its positions.
   stage=`${engine}/${mobile}/${mode}: isolation`;await page.waitForLoadState('networkidle');await page.goto(url+'/?mode='+mode+'&exam=cambridge-04-test-02');await ready(1);assert((await native()).time<.5&&(await native()).paused);
   stage=`${engine}/${mobile}/${mode}: initial`;await page.waitForLoadState('networkidle');await page.goto(url+'/?mode='+mode);await ready(1);assert(Math.abs((await native()).time-180)<2&&(await native()).paused);
   stage=`${engine}/${mobile}/${mode}: natural end`;await start();await page.getByLabel('Audio progress').fill(String(Math.floor(((await native()).duration-.2)*10)/10));await ready(2);await wait(async()=>!(await native()).paused);assert((await native()).time>=saved2-2);
   stage=`${engine}/${mobile}/${mode}: screenshot`;await pause();await listen(1);await position(3);await pause();await view(1);await page.locator('[data-waveform-source=audio]').waitFor();
   assert.equal(audioFetches,0,'Waveform must never fetch/decode the audio');
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1&&document.documentElement.scrollHeight<=innerHeight+1));
   const name=`${engine}-${mobile?'mobile':'desktop'}-${mode}`;await player.screenshot({path:join(out,name+'-player.png')});await page.screenshot({path:join(out,name+'.png')});
   if(mode==='exam'){
    await page.getByRole('button',{name:'Finish',exact:true}).click();await page.getByRole('button',{name:'Finish and view results',exact:true}).click();await page.waitForURL(/\/results$/);
    await page.getByRole('link',{name:'Review all questions'}).click();await page.getByRole('heading',{name:'Review your answers'}).waitFor();assert((await page.locator('#question-1').textContent()).includes('player V4 QA'));
   }
   cases.push({engine,mobile,mode,status:'PASS',real_audio:true,screenshot:name+'-player.png'});await page.waitForLoadState('networkidle');await context.close();
  }}finally{await browser.close();}
 }
 assert.equal(errors.length,0,JSON.stringify(errors));
}catch(error){errors.push(stage+': '+String(error)+' '+await diagnostic().catch(e=>'Diagnostic unavailable: '+String(e)));process.exitCode=1;}finally{server.kill('SIGTERM');}
writeFileSync(join(out,'qa.json'),JSON.stringify({waveforms_validated:validated,cases,unverified,errors,fixture,scope:'Real local Cambridge MP3 and production UI; synthetic local identity/attempt/AI responses. No production connections.'},null,2)+'\n');
console.log(JSON.stringify({waveforms:validated,passed:cases.length,unverified,errors,fixture},null,2));
