// Disposable local frontend, original renderers, supplied readonly projections. No DB.
import {mkdtemp,cp,symlink,mkdir,writeFile,readFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {dirname,join,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import {spawn} from 'node:child_process';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../../..'),web=join(root,'web');
const require=createRequire(join(web,'package.json'));
const {chromium}=require('@playwright/test');
const work='/tmp/alua-reading-fidelity-work',out=join(root,'docs/reading-content-fidelity-v1');
const input=JSON.parse(await readFile(join(work,'browser-data.json'),'utf8'));
const sandbox=await mkdtemp(join(tmpdir(),'alua-reading-fidelity-browser-'));
const env={...process.env,NEXT_PUBLIC_API_BASE_URL:'http://127.0.0.1:3315/api/v1'};
for(const key of Object.keys(env))if(key.startsWith('NEXT_PUBLIC_FIREBASE'))env[key]='';
async function file(name,text){const p=join(sandbox,name);await mkdir(dirname(p),{recursive:true});await writeFile(p,text);}
let server,browser;
try{
 for(const name of ['src','public','package.json','tsconfig.json','next.config.ts','postcss.config.mjs'])await cp(join(web,name),join(sandbox,name),{recursive:true});
 await symlink(join(web,'node_modules'),join(sandbox,'node_modules'),'dir');
 await file('src/lib/firebase/client.ts',`import type {Auth} from 'firebase/auth';export function firebaseConfigured(){return true};export async function getFirebaseAuth():Promise<Auth>{throw Error('Audit fixture only')};export async function getIdToken(){return 'audit-fixture-only'};`);
 await file('src/app/reading-fidelity/[id]/[mode]/page.tsx',`import {readFile} from 'node:fs/promises';import {Harness} from '../../harness';export default async function Page({params}:{params:Promise<{id:string;mode:string}>}){const {id,mode}=await params;const data=JSON.parse(await readFile('${work}/browser-data.json','utf8'));return <Harness data={data.exams[id]} review={mode==='review'}/>}`);
 await file('src/app/reading-fidelity/harness.tsx',`'use client';import {useSyncExternalStore} from 'react';import {ReadingExam} from '@/features/reading/exam/reading-exam';import {parseExam} from '@/features/reading/exam/parse';import type {ReadingResult} from '@/features/reading/exam/results';import type {Attempt} from '@/features/reading/exam/models';export function Harness({data,review}:{data:{exam:unknown;result:ReadingResult};review:boolean}){const ready=useSyncExternalStore(()=>()=>{},()=>true,()=>false);const exam=parseExam(data.exam);const attempt:Attempt={id:'11111111-2222-4333-8444-555555555555',exam_id:exam.id,mode:'full_exam',status:review?'submitted':'in_progress',version:1,content_hash:data.result.content_hash,server_now:new Date().toISOString(),deadline_at:new Date(Date.now()+3600000).toISOString(),answers:{},state:{current_passage:1,checked_question_ids:[]},not_fully_proofread:true,exam};return <div data-audit-ready={ready}><ReadingExam uid='audit-only' attempt={attempt} result={review?data.result:undefined}/></div>}`);
 server=spawn(process.execPath,[require.resolve('next/dist/bin/next'),'dev','--webpack','--hostname','127.0.0.1','--port','3315'],{cwd:sandbox,env,stdio:['ignore','pipe','pipe']});
 let log='';server.stdout.on('data',d=>{log+=d.toString()});server.stderr.on('data',d=>{log+=d.toString()});
 for(let n=0;n<90;n++){try{await fetch('http://127.0.0.1:3315');break}catch{}await new Promise(r=>setTimeout(r,500));if(n===89)throw Error(log.slice(-1500));}
 browser=await chromium.launch({headless:true});
 const results={};for(const id of Object.keys(input.exams)){try{const previous=JSON.parse(await readFile(join(out,'checkpoints',`browser-${id}.json`),'utf8'));if(previous.modes.exam?.visible_question_records===40&&previous.modes.review?.visible_question_records===40&&!previous.errors.length)results[id]=previous;}catch{}}const queue=Object.keys(input.exams).filter(id=>!results[id]).sort();await mkdir(join(out,'checkpoints'),{recursive:true});await mkdir(join(out,'evidence'),{recursive:true});await mkdir(join(work,'dom'),{recursive:true});
 async function worker(){while(queue.length){const id=queue.shift();const context=await browser.newContext({viewport:{width:1440,height:900}}),page=await context.newPage();const result={exam_id:id,modes:{},errors:[],mutations:[]};
  await page.route('**/api/alua/**',async route=>{const req=route.request(),path=new URL(req.url()).pathname;if(req.method()!=='GET'){result.mutations.push(path);await route.fulfill({status:405});return;}if(path.includes('/assets/')){const aid=decodeURIComponent(path.split('/assets/')[1]);const asset=input.assets[aid];await route.fulfill(asset?{path:asset,contentType:'image/png'}:{status:404});return;}await route.fulfill({json:{items:[]}});});
  page.on('pageerror',e=>result.errors.push(e.message));
  for(const mode of ['exam','review']){const passages=[];try{
   await page.goto(`http://127.0.0.1:3315/reading-fidelity/${id}/${mode}`,{waitUntil:'domcontentloaded'});await page.locator('[data-audit-ready=true] .exam-workspace').waitFor({timeout:20000});
   for(const passage of input.exams[id].exam.passages){await page.getByRole('button',{name:`Passage ${passage.number}`,exact:true}).click();const group=page.getByRole('region',{name:`Questions for passage ${passage.number}`,exact:true});await group.waitFor({state:'visible'});await page.waitForFunction(n=>[...document.querySelectorAll(`section[aria-label="Questions for passage ${n}"] .reading-asset`)].every(el=>el.querySelector('img')?.naturalWidth>0||el.querySelector('[role=alert]')),passage.number,{timeout:10000});
    const data=await page.evaluate(({n})=>{const section=document.querySelector(`section[aria-label="Questions for passage ${n}"]`);return {number:n,title:document.querySelector('.passage-article h1')?.textContent,paragraphs:[...document.querySelectorAll('[data-highlight-block]')].map(el=>({index:Number(el.getAttribute('data-highlight-block')),text:el.textContent})),questions:[...section.querySelectorAll('[data-question]')].map(el=>({number:Number(el.getAttribute('data-question')),visible:el.getClientRects().length>0,inline:el.classList.contains('inline-question'),text:el.textContent,controls:[...el.querySelectorAll('input,select,button[aria-pressed]')].map(c=>({type:c.getAttribute('type')||c.tagName,label:c.getAttribute('aria-label')||c.textContent,disabled:c.disabled}))})),groups:[...section.querySelectorAll('.question-group')].map(el=>({type:el.getAttribute('data-question-type'),representation:el.getAttribute('data-representation'),heading:el.querySelector('.group-heading')?.textContent,text:el.textContent,images:[...el.querySelectorAll('img')].map(im=>({loaded:im.naturalWidth>0,alt:im.alt}))})),passage_text:document.querySelector('.passage-article')?.textContent};},{n:passage.number});
    await writeFile(join(work,'dom',`${id}-p${passage.number}-${mode}.json`),JSON.stringify(data));
    const norm=t=>t.replace(/\s+/g,' ').trim();data.paragraphs=data.paragraphs.map(p=>({index:p.index,exact_json_text:norm(p.text)===norm(passage.content[p.index]?.text??''),characters:p.text.length}));delete data.passage_text;
    data.questions=data.questions.map(q=>({...q,text_excerpt:q.text.slice(0,180),text:undefined}));data.groups=data.groups.map(g=>({...g,text_excerpt:g.text.slice(0,180),text:undefined}));passages.push(data);
    if(mode==='exam'&&((id==='cambridge-07-test-01'&&[1,3].includes(passage.number))||(id==='cambridge-06-test-01'&&passage.number===2))){const start=id==='cambridge-06-test-01'?23:passage.number===1?6:37;const target=group.locator(`.question-group`).filter({has:page.locator(`[data-question="${start}"]`)});await target.screenshot({path:join(out,'evidence',`${id}-g${start}-browser.png`),timeout:20000}).catch(e=>result.errors.push('screenshot: '+e.message));}
   }
   result.modes[mode]={passages,question_records:passages.flatMap(p=>p.questions).length,visible_question_records:passages.flatMap(p=>p.questions).filter(q=>q.visible).length};
  }catch(e){result.errors.push(`${mode}: ${e.message}`);}}
  results[id]=result;await writeFile(join(out,'checkpoints',`browser-${id}.json`),JSON.stringify(result,null,2));await context.close();console.log(`${Object.keys(results).length}/72 ${id} exam=${result.modes.exam?.visible_question_records} review=${result.modes.review?.visible_question_records} errors=${result.errors.length}`);
 }}
 await Promise.all([worker(),worker()]);await writeFile(join(out,'browser-observations.json'),JSON.stringify(Object.fromEntries(Object.entries(results).sort()),null,2));
}finally{await browser?.close();server?.kill('SIGTERM');await rm(sandbox,{recursive:true,force:true});}
