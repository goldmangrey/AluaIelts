// Local-only UI/player regression, real components + synthetic identity/API/audio.
// No backend, auth provider, recordings, user data or production connections.
import {readFileSync,writeFileSync,mkdirSync,cpSync,mkdtempSync,symlinkSync,openSync} from 'node:fs';
import {resolve,dirname,join} from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {createRequire} from 'node:module';
import {tmpdir} from 'node:os';
import {spawn,execFileSync} from 'node:child_process';
import assert from 'node:assert/strict';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..'),web=join(root,'web');
const req=createRequire(pathToFileURL(join(web,'package.json')));
const manifest=JSON.parse(readFileSync(join(web,'src/features/listening/waveform-manifest.json'),'utf8'));
assert.equal(Object.keys(manifest.exams).length,72);
const fixture=mkdtempSync(join(tmpdir(),'alua-listening-ui-')),put=(p,s)=>{const path=join(fixture,p);mkdirSync(dirname(path),{recursive:true});writeFileSync(path,s);};
for(const p of ['src/features/listening','src/features/exam-reliability','src/features/reading/exam/draft-storage.ts','src/styles','package.json','tsconfig.json','next.config.ts','postcss.config.mjs']){mkdirSync(dirname(join(fixture,p)),{recursive:true});cpSync(join(web,p),join(fixture,p),{recursive:true});}
cpSync(join(web,'public/listening-waveforms'),join(fixture,'public/listening-waveforms'),{recursive:true});
symlinkSync(join(web,'node_modules'),join(fixture,'node_modules'),'dir');
put('next.config.ts',readFileSync(join(fixture,'next.config.ts'),'utf8').replace('const config: NextConfig = {','const config: NextConfig = { devIndicators:false,'));
put('src/features/auth/session.ts',`const session={status:'ready',user:{uid:'local-ui'},generation:1};export function useSession(){return session}export async function retrySession(){}`);
put('src/lib/firebase/client.ts',`export async function getIdToken(){return 'local-ui-only'}`);
put('src/lib/api/client.ts',`export class ApiError extends Error{};export function createApiClient(){return async function(path:string,_signal?:AbortSignal,options?:any,type?:string){if(type==='blob'){const response=await fetch('/asset/'+path.split('/').pop(),{signal:_signal});return response.blob()}const f=(window as any).__audit;if(path.endsWith('/sync')){f.attempt={...f.attempt,...options.body,version:f.attempt.version+1};}if(path.endsWith('/submit')){f.attempt={...f.attempt,...options.body,status:'submitted',version:f.attempt.version+1,final_snapshot_accepted:true};f.result.questions.forEach((q:any)=>q.user_answer=f.attempt.answers[q.question_id]||'');f.result.answered_count=Object.keys(f.attempt.answers).length;}return structuredClone(path.endsWith('/review')||path.endsWith('/result')?f.result:f.attempt)}}`);
put('src/app/layout.tsx',`import '@/styles/globals.css';export default function Layout({children}:{children:React.ReactNode}){return <html><body>{children}</body></html>}`);
put('src/app/page.tsx',`import {readFile} from 'node:fs/promises';import Client from './client';export const dynamic='force-dynamic';export default async function Page({searchParams}:{searchParams:Promise<Record<string,string>>}){const q=await searchParams;return <Client exam={JSON.parse(await readFile(${JSON.stringify(join(root,'backend/app/content/listening_v1/exams/cambridge-04-test-01.json'))},'utf8'))} mode={q.mode||'exam'}/>}`);
put('src/app/client.tsx',`'use client';import {useState,useEffect} from 'react';import {ListeningPage} from '@/features/listening/pages';import type {Exam} from '@/features/listening/models';export default function Client({exam,mode}:{exam:Exam;mode:string}){const [ready,R]=useState(false);useEffect(()=>{localStorage.clear();const rows=exam.parts.flatMap(p=>p.groups.flatMap(g=>g.questions.map(q=>({question_id:q.question_id,question_number:q.question_number,part_number:p.part_number,user_answer:'',correct:null,correct_answer:null,grading_issue:null,key_verified:false}))));(window as any).__audit={attempt:{id:'local-ui',version:1,content_hash:exam.exam_id,status:'in_progress',answers:{},state:{displayed_part:1,current_question:1,audio_part:1,playback_seconds:0,marked:[1]},exam},result:{attempt_id:'local-ui',mode:'ungraded',label:'Local only',correct_count:null,total_questions:40,graded_count:0,answered_count:0,accuracy:null,estimated_band:null,band_table_version:null,parts:[],questions:rows,exam,grading_issues:{}}};R(true)},[exam]);return ready?<ListeningPage kind={mode==='review'?'review':'attempt'} id='local-ui'/>:null}`);
put('src/app/listening/attempts/[id]/[mode]/page.tsx',`'use client';import {useParams} from 'next/navigation';import {ListeningPage} from '@/features/listening/pages';export default function Page(){const p=useParams();return <ListeningPage kind={p.mode==='review'?'review':'result'} id='local-ui'/>}`);
put('src/app/asset/[id]/route.ts',`import {readFile} from 'node:fs/promises';export async function GET(_r:Request,{params}:{params:Promise<{id:string}>}){const {id}=await params,root=${JSON.stringify(join(root,'backend/app/content/listening_v1'))};const a=JSON.parse(await readFile(root+'/qa/assets.json','utf8')).assets.find((a:any)=>a.asset_id===id&&a.visibility==='public');if(!a)return new Response(null,{status:404});return new Response(await readFile(root+'/'+a.relative_path),{headers:{'Content-Type':a.relative_path.endsWith('.png')?'image/png':'image/jpeg'}})}`);
if(process.argv.includes('--prepare-only')){console.log(JSON.stringify({fixture}));process.exit(0);}
// Native PCM WAV: varying amplitude and real pauses, not a decorative bar pattern.
const samples=8000*12,wav=Buffer.alloc(44+samples*2);wav.write('RIFF');wav.writeUInt32LE(wav.length-8,4);wav.write('WAVEfmt ',8);wav.writeUInt32LE(16,16);wav.writeUInt16LE(1,20);wav.writeUInt16LE(1,22);wav.writeUInt32LE(8000,24);wav.writeUInt32LE(16000,28);wav.writeUInt16LE(2,32);wav.writeUInt16LE(16,34);wav.write('data',36);wav.writeUInt32LE(samples*2,40);
for(let i=0;i<samples;i++){const t=i/8000;const envelope=t<2?0:t<4?.2:t<8?.8:.1;wav.writeInt16LE(Math.round(Math.sin(t*2*Math.PI*220)*envelope*30000),44+i*2);}
const tracks={exam:{bytes:wav,type:'audio/wav'},review:{bytes:wav,type:'audio/wav'}};
if(process.argv.includes('--compressed')){
 writeFileSync(join(fixture,'test.wav'),wav);
 for(const [mode,extension,type] of [['exam','mp3','audio/mpeg'],['review','m4a','audio/mp4']]){
  const path=join(fixture,'test.'+extension);execFileSync('ffmpeg',['-v','error','-i',join(fixture,'test.wav'),path]);tracks[mode]={bytes:readFileSync(path),type};
 }
}
const port=3395,url=`http://127.0.0.1:${port}`,log=openSync(join(fixture,'server.log'),'w');
const server=spawn(process.execPath,[req.resolve('next/dist/bin/next'),'dev','--webpack','--hostname','127.0.0.1','--port',String(port)],{cwd:fixture,stdio:['ignore',log,log]});
const cases=[],errors=[];
const wait=async check=>{for(let i=0;i<100;i++){if(await check())return;await new Promise(r=>setTimeout(r,150));}throw Error('Timed out');};
try{
 await wait(async()=>{try{return (await fetch(url)).ok;}catch{return false;}});
 for(const mobile of [false,true]){
  const browser=await req('@playwright/test').chromium.launch({headless:true});
  try{for(const mode of ['exam','review']){
   const page=await browser.newPage({viewport:mobile?{width:390,height:844}:{width:1440,height:900}});page.setDefaultTimeout(15000);
   page.on('pageerror',e=>errors.push(e.message));
   await page.route('**/*',route=>new URL(route.request().url()).hostname==='127.0.0.1'||route.request().url().startsWith('blob:')?route.continue():route.abort());
   await page.route('**/api/listening/authorize',route=>route.fulfill({json:{}}));
   const track=tracks[mode].bytes;
   await page.route('**/api/listening/audio/**',route=>{
    const range=/^bytes=(\d+)-(\d*)$/.exec(route.request().headers().range||'');
    const start=range?Number(range[1]):0,end=range&&range[2]?Math.min(track.length-1,Number(range[2])):track.length-1;
    return route.fulfill({status:range?206:200,contentType:tracks[mode].type,headers:{'Accept-Ranges':'bytes','Content-Length':String(end-start+1),...(range?{'Content-Range':`bytes ${start}-${end}/${track.length}`}:{})},body:track.subarray(start,end+1)});
   });
   await page.goto(`${url}/?mode=${mode}`);await page.locator('#question-1').waitFor({state:'attached'});
   await page.locator('[data-waveform-source="audio"]').waitFor();
   const waveform=page.locator('[data-waveform]');const box=await waveform.boundingBox();
   const heights=await waveform.locator('g').first().locator('rect').evaluateAll(es=>es.map(e=>Number(e.getAttribute('height'))));
   assert(heights.length>=(mobile?32:128));assert(Math.max(...heights)>20&&Math.min(...heights)<5);
   await page.getByRole('button',{name:'Play',exact:true}).click();
   await wait(()=>page.locator('audio').first().evaluate(el=>el.currentTime>.2&&!el.paused));
   await page.getByLabel('Audio progress').fill('6');await page.getByRole('button',{name:'Pause',exact:true}).click();
   assert(await page.locator('audio').first().evaluate(el=>el.paused&&el.currentTime>=6));
   await page.getByRole('button',{name:'Back 5 seconds',exact:true}).click();assert(await page.locator('audio').first().evaluate(el=>el.currentTime<2));
   await page.getByRole('button',{name:'Forward 5 seconds',exact:true}).click();assert(await page.locator('audio').first().evaluate(el=>el.currentTime>=6));
   assert.equal(await page.getByRole('button',{name:/^(Unmark|Mark) question/}).count(),0);
   assert.equal(await page.locator('[data-marked]').count(),0);
   assert.equal(await page.getByRole('region',{name:'Listening source material',includeHidden:true}).locator('header span').count(),0);
   assert.equal(await page.locator('footer').getByText(/^\d+ \/ 40$/).count(),0);
   const source=page.getByRole('region',{name:'Listening source material',includeHidden:true}),questions=page.getByRole('region',{name:'Listening questions',exact:true});
   const panel=async name=>{const button=page.getByRole('button',{name,exact:true});if(await button.isVisible())await button.click();};
   await panel('Source material');await page.waitForFunction(()=>[...document.querySelectorAll('[data-source-asset] img')].every(i=>i.naturalWidth>0));
   const ids=()=>source.locator('[data-source-asset]').evaluateAll(es=>es.map(e=>e.getAttribute('data-source-asset')));
   const original=await ids();assert.equal(original.length,2);await source.evaluate(e=>{e.scrollTop=200;});const offset=await source.evaluate(e=>e.scrollTop);
   await panel('Questions');await page.locator('#question-5').focus();assert.deepEqual(await ids(),original);
   if(!mobile){assert.equal(await source.evaluate(e=>e.scrollTop),offset);await questions.evaluate(e=>{e.scrollTop=e.scrollHeight;});assert.equal(await source.evaluate(e=>e.scrollTop),offset);}
   await page.getByRole('button',{name:'Question navigator',exact:true}).click();await page.getByRole('button',{name:'Go to question 1',exact:true}).click();
   if(mode==='exam'){
    await page.getByLabel('Question 1',{exact:true}).fill('local cleanup QA');
    await page.waitForFunction(()=>window.__audit.attempt.answers['cambridge-04-test-01-q01']==='local cleanup QA');
   }
   await page.getByRole('button',{name:/^Part 2/}).click();await page.locator('#question-11').waitFor({state:'attached'});
   await page.getByRole('button',{name:/^Part 1/}).click();await page.locator('#question-1').waitFor({state:'attached'});assert.deepEqual(await ids(),original);
   if(mode==='exam')assert.equal(await page.getByLabel('Question 1',{exact:true}).inputValue(),'local cleanup QA');
   await page.locator('[data-waveform-source="audio"]').waitFor();const after=await waveform.boundingBox();assert.equal(after.height,box.height);
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1&&document.documentElement.scrollHeight<=innerHeight+1));
   await panel('Source material');await page.screenshot({path:join(fixture,`${mode}-${mobile?'mobile':'desktop'}.png`)});
   if(mode==='exam'){
    await page.getByRole('button',{name:'Finish',exact:true}).click();await page.getByRole('button',{name:'Keep practising',exact:true}).click();
    await page.getByRole('button',{name:'Finish',exact:true}).click();await page.getByRole('button',{name:'Finish and view results',exact:true}).click();await page.waitForURL(/\/results$/);
    await page.getByRole('link',{name:'Review all questions'}).click();await page.getByRole('heading',{name:'Review your answers'}).waitFor();await panel('Questions');assert(await page.locator('#question-1').textContent().then(t=>t.includes('local cleanup QA')));
   }
   cases.push({mode,mobile,audio:tracks[mode].type,bars:heights.length,status:'PASS'});await page.close();
  }}finally{await browser.close();}
 }
 assert.equal(errors.length,0,JSON.stringify(errors));
} catch(error){errors.push(String(error));process.exitCode=1;}finally{server.kill('SIGTERM');}
writeFileSync(join(fixture,'result.json'),JSON.stringify({cases,errors},null,2));
console.log(JSON.stringify({waveform_manifest:'PASS',cases,errors,artifacts:fixture},null,2));
