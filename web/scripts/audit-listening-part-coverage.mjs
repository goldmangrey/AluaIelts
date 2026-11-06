// Read-only regression audit. Writes only docs artifacts; does not import/mutate content.
// node web/scripts/audit-listening-part-coverage.mjs [--browser]
import {readFileSync,writeFileSync,mkdirSync,readdirSync,cpSync,mkdtempSync,symlinkSync} from 'node:fs';
import {resolve,dirname,join} from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {createRequire} from 'node:module';
import {runInNewContext} from 'node:vm';
import {createHash} from 'node:crypto';
import {tmpdir} from 'node:os';
import {spawn} from 'node:child_process';
import assert from 'node:assert/strict';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..'),web=join(root,'web'),out=join(root,'docs/listening-visual-audit/stage1');
const req=createRequire(pathToFileURL(join(web,'package.json'))),ts=req('typescript'),React=req('react'),{renderToStaticMarkup}=req('react-dom/server');
const feature=join(web,'src/features/listening'),read=p=>JSON.parse(readFileSync(p,'utf8')),registry=read(join(feature,'visual-materials.json'));
const cache=new Map();
function load(path){
 if(cache.has(path))return cache.get(path).exports;
 const cell={exports:{}};cache.set(path,cell);
 const requireLocal=id=>{
  if(id.endsWith('.css'))return new Proxy({},{get:(_,name)=>String(name)});
  if(id==='./api')return {api:()=>()=>Promise.reject(Error('No backend in audit'))};
  if(id.startsWith('.')){let p=resolve(dirname(path),id);if(p.endsWith('.json'))return read(p);if(!/\.tsx?$/.test(p))p+=id==='./questions'?'.tsx':'.ts';return load(p);}
  return req(id);
 };
 runInNewContext(ts.transpileModule(readFileSync(path,'utf8'),{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText,{module:cell,exports:cell.exports,require:requireLocal,Set,Map,console});return cell.exports;
}
const {sourceMaterial}=load(join(feature,'source-material.ts')),{WorkspaceQuestions}=load(join(feature,'workspace-questions.tsx'));
// Minimal regression: Q1–4 and Q5–10 must share the same two mounted images,
// regardless of the active question. Uses the real two-group Cambridge Part.
if(process.argv.includes('--assert-complete')){
 const exam=read(join(root,'backend/app/content/listening_v1/exams/cambridge-04-test-01.json'));
 const expected=exam.parts[0].visual_materials.map(m=>m.asset_id);
 assert.deepEqual(exam.parts[0].groups.map(g=>g.question_range),[[1,4],[5,10]]);assert.equal(expected.length,2);
 for(const current of [1,4,5,10]){
  const html=renderToStaticMarkup(React.createElement(WorkspaceQuestions,{exam,part:1,current,navigation:0,uid:'test',id:'test',answers:{},onAnswer:()=>{},onFocus:()=>{},disabled:false}));
  assert.deepEqual([...html.matchAll(/data-source-asset="([^"]+)"/g)].map(m=>m[1]),expected,`Q${current}: both Part images must remain mounted`);
 }
}
const findings=read(join(root,'docs/listening-visual-audit/reviewed-findings.json')).findings;
const pairs=findings.filter(f=>f.kind==='duplicate_content').map(f=>f.assets).concat(registry.provenance.additional_reviewed_relations.map(r=>[r.a,r.b]));
const partResults=[],csv=[],emptyGroups=[],filteredReproductions=[];let states=0,groups=0,missingStates=0;
const sha=p=>createHash('sha256').update(readFileSync(p)).digest('hex');
const fingerprints={};for(const f of ['source-material.ts','workspace-questions.tsx','questions.tsx','pages.tsx','review.tsx','visual-materials.json'])fingerprints['web/src/features/listening/'+f]=sha(join(feature,f));
for(const file of readdirSync(join(root,'backend/app/content/listening_v1/exams')).filter(f=>f.endsWith('.json')).sort()){
 const exam=read(join(root,'backend/app/content/listening_v1/exams',file));
 for(const part of exam.parts){
  groups+=part.groups.length;
  const materials=part.visual_materials||registry.parts[`${exam.exam_id}-p${part.part_number}`].materials;
  const byGroup=part.groups.map(g=>({range:g.question_range,ids:[...sourceMaterial(exam,part,g).assets]}));
  const union=new Set(byGroup.flatMap(g=>g.ids));
  const expected=materials.filter(m=>union.has(m.asset_id)).sort((a,b)=>a.display_order-b.display_order).map(m=>m.asset_id);
  assert.equal(union.size,expected.length);assert.equal(new Set(expected).size,expected.length);
  assert.equal(expected.length,materials.length,'Every canonical page must serve a visible group');
  const duplicatePairs=pairs.filter(pair=>pair.every(a=>expected.includes(a)));assert.equal(duplicatePairs.length,0);
  assert(materials.every((m,i)=>!i||materials[i-1].question_range[0]<=m.question_range[0]));
  const assets=new Set(exam.assets.map(a=>a.asset_id));assert(expected.every(a=>assets.has(a)));
  const policy=registry.parts[`${exam.exam_id}-p${part.part_number}`];
  assert((policy.excluded_asset_ids||[]).every(a=>!expected.includes(a)));
  assert.deepEqual(materials.map(m=>m.asset_id),policy.materials.map(m=>m.asset_id));
  const initial=part.groups[0].questions[0].question_number,contexts=[];
  for(const group of part.groups){
   const current=group.questions[0].question_number;
   const markup=renderToStaticMarkup(React.createElement(WorkspaceQuestions,{exam,part:part.part_number,current,navigation:0,uid:'audit-only',id:'audit-only',answers:{},onAnswer:()=>{},onFocus:()=>{},disabled:false}));
   const actual=[...markup.matchAll(/data-source-asset="([^"]+)"/g)].map(m=>m[1]);
   const visible=[...markup.matchAll(/id="question-(\d+)"/g)].map(m=>Number(m[1]));
   assert.deepEqual(visible,part.groups.flatMap(g=>g.questions.map(q=>q.question_number)));
   assert(actual.every(id=>expected.includes(id)),'UI introduced unreviewed/foreign material');
   assert.deepEqual(actual,expected.filter(id=>actual.includes(id)),'UI order/duplicates differ from canonical Part order');
   const missing=expected.filter(a=>!actual.includes(a));states++;if(missing.length)missingStates++;
   const context={current_question:current,active_group:group.question_range,actual_asset_ids:actual,missing_asset_ids:missing,missing_question_ranges:materials.filter(m=>missing.includes(m.asset_id)).map(m=>({asset_id:m.asset_id,question_range:m.question_range})),evidence:'component verified (actual WorkspaceQuestions SSR)',status:missing.length?'CONFIRMED_MISSING_RENDER':'COVERED'};
   contexts.push(context);
   if(missing.length)csv.push({test_id:exam.exam_id,book:exam.book,test:exam.printed_test_number,part:part.part_number,current_question:current,visible_question_range:part.question_range,active_group:group.question_range,expected_asset_ids:expected,actual_asset_ids:actual,missing_asset_ids:missing,missing_question_ranges:context.missing_question_ranges,severity:'HIGH',cause:'all_part_questions_but_active_group_material',evidence:context.evidence,reproduce:`Open Exam/Review All ${exam.exam_id} Part ${part.part_number}; current Q${current}; scroll questions without focusing another group.`});
   if(!actual.length)emptyGroups.push({test_id:exam.exam_id,part:part.part_number,range:group.question_range,presentation:group.presentation_mode,question_type:group.question_type,has_source_lines:group.content_blocks.some(b=>b.kind==='source_line'),has_answer_bank:!!group.answer_bank,status:group.presentation_mode==='structured'?'textual_group_no_image_expected':'REQUIRES_REVIEW'});
  }
  if(exam.exam_id==='cambridge-04-test-01'&&part.part_number===1){
   for(const numbers of [[1,5],[5]]){
    const selected=new Set(numbers),html=renderToStaticMarkup(React.createElement(WorkspaceQuestions,{exam,part:1,current:numbers[0],navigation:0,uid:'audit-only',id:'audit-only',answers:{},onAnswer:()=>{},onFocus:()=>{},disabled:true,visibleQuestions:selected,renderAnswer:()=>React.createElement('p',null,'Synthetic saved answer')}));
    const actual=[...html.matchAll(/data-source-asset="([^"]+)"/g)].map(m=>m[1]);
    const wanted=materials.filter(m=>numbers.some(n=>m.question_range[0]<=n&&n<=m.question_range[1])).map(m=>m.asset_id);
    filteredReproductions.push({test_id:exam.exam_id,part:1,visible_questions:numbers,expected_asset_ids:wanted,actual_asset_ids:actual,missing_asset_ids:wanted.filter(a=>!actual.includes(a)),evidence:'component verified with actual visibleQuestions and renderAnswer props'});
    if(process.argv.includes('--assert-complete'))assert.deepEqual(actual,wanted,'Filtered Review must cover all visible groups');
   }
  }
  const first=contexts.find(c=>c.current_question===initial);
  partResults.push({test_id:exam.exam_id,book:exam.book,test:exam.printed_test_number,part:part.part_number,visible_question_range:part.question_range,question_ranges:part.groups.map(g=>g.question_range),expected_asset_ids:expected,actual_asset_ids:first.actual_asset_ids,missing_asset_ids:first.missing_asset_ids,status:contexts.some(c=>c.missing_asset_ids.length)?'CONFIRMED_MISSING_RENDER':'COVERED_IN_COMPONENT',evidence:'component verified',contexts});
 }
}
let browser={status:'NOT RUN',cases:[]};
if(process.argv.includes('--browser')){
 const stage2=process.argv.includes('--stage2');
 const browserOut=stage2?join(root,'docs/listening-visual-audit/stage2'):out;mkdirSync(browserOut,{recursive:true});
 const sandbox=mkdtempSync(join(tmpdir(),'alua-part-coverage-'));const put=(p,s)=>{const path=join(sandbox,p);mkdirSync(dirname(path),{recursive:true});writeFileSync(path,s);};
 for(const path of ['src/features/listening','src/styles','package.json','tsconfig.json','next.config.ts','postcss.config.mjs'])cpSync(join(web,path),join(sandbox,path),{recursive:true});
 symlinkSync(join(web,'node_modules'),join(sandbox,'node_modules'),'dir');
 put('src/lib/api/client.ts',`export class ApiError extends Error{};export function createApiClient(){return async function(path:string,_signal?:AbortSignal,_options?:unknown,type?:string){if(type!=='blob')throw Error('No backend in coverage audit');const id=path.split('/').pop();const response=await fetch('/asset/'+id);if(!response.ok)throw Error('Missing');return response.blob()}}`);
 put('src/lib/firebase/client.ts',`export async function getIdToken(){return 'local-audit-only'}`);
 put('src/app/layout.tsx',`import '@/styles/globals.css';export default function Layout({children}:{children:React.ReactNode}){return <html><body>{children}</body></html>}`);
 put('src/app/page.tsx',`import {readFile} from 'node:fs/promises';import Client from './client';export const dynamic='force-dynamic';export default async function Page({searchParams}:{searchParams:Promise<Record<string,string>>}){const q=await searchParams;const id=q.exam||'cambridge-04-test-01';if(!/^cambridge-\\d{2}-test-\\d{2}$/.test(id))throw Error('Invalid id');const exam=JSON.parse(await readFile(${JSON.stringify(join(root,'backend/app/content/listening_v1/exams/'))}+id+'.json','utf8'));return <Client exam={exam} initial={Number(q.q)||1} mode={q.mode||'exam'}/>}`);
 put('src/app/client.tsx',`'use client';import {useState} from 'react';import {WorkspaceQuestions} from '@/features/listening/workspace-questions';import {ListeningReview} from '@/features/listening/review';import type {Exam,Result} from '@/features/listening/models';import s from '@/features/listening/listening.module.css';import w from '@/features/listening/workspace.module.css';export default function Client({exam,initial,mode}:{exam:Exam;initial:number;mode:string}){const [q,Q]=useState(initial),[nav,N]=useState(0);if(mode==='review'){const rows=exam.parts.flatMap(p=>p.groups.flatMap(g=>g.questions.map(x=>({question_id:x.question_id,question_number:x.question_number,part_number:p.part_number,user_answer:'',correct:null,correct_answer:null,grading_issue:null,key_verified:false}))));if(initial!==1)rows.sort((a,b)=>a.question_number===initial?-1:b.question_number===initial?1:a.question_number-b.question_number);const result={attempt_id:'audit-only',mode:'ungraded',label:'Audit only',correct_count:null,total_questions:40,graded_count:0,answered_count:0,accuracy:null,estimated_band:null,band_table_version:null,parts:[],questions:rows,exam,grading_issues:{}} as Result;return <ListeningReview result={result} uid='audit-only'/>}return <main className={s.workspace+' '+w.workspace}><header style={{padding:12}}>Local component reproduction (Exam WorkspaceQuestions, same props as pages.tsx)<button onClick={()=>{Q(v=>Math.min(40,v+1));N(v=>v+1)}}>Audit next question</button></header><WorkspaceQuestions exam={exam} part={Math.ceil(q/10)} current={q} navigation={nav} uid='audit-only' id='audit-only' answers={{}} onAnswer={()=>{}} onFocus={Q} disabled={false}/></main>}`);
 if(stage2){
  // Actual Exam/Review page components; identity/attempt API exist only in this
  // disposable origin. No real user data, audio, AI or backend connections.
  put('src/features/auth/session.ts',`const session={status:'ready',user:{uid:'audit-only'},generation:1};export function useSession(){return session}export async function retrySession(){}`);
  put('src/lib/api/client.ts',`export class ApiError extends Error{};export function createApiClient(){return async function(path:string,_signal?:AbortSignal,options?:any,type?:string){if(type==='blob'){const id=path.split('/').pop();if(!id?.startsWith('asset-'))throw Error('Audio outside image QA');const response=await fetch('/asset/'+id);if(!response.ok)throw Error('Missing image');return response.blob()}const fixture=(window as any).__audit;if(!fixture)throw Error('No fixture');if(path.endsWith('/sync')){fixture.attempt={...fixture.attempt,...options.body,version:fixture.attempt.version+1};return structuredClone(fixture.attempt)}return structuredClone(path.endsWith('/review')?fixture.result:fixture.attempt)}}`);
  put('src/app/api/listening/authorize/route.ts',`export async function POST(){return Response.json({})}`);
  put('src/app/client.tsx',`'use client';import {useState,useEffect} from 'react';import {ListeningPage} from '@/features/listening/pages';import type {Exam} from '@/features/listening/models';export default function Client({exam,initial,mode}:{exam:Exam;initial:number;mode:string}){const [ready,R]=useState(false);useEffect(()=>{localStorage.clear();const rows=exam.parts.flatMap(p=>p.groups.flatMap(g=>g.questions.map(q=>({question_id:q.question_id,question_number:q.question_number,part_number:p.part_number,user_answer:'',correct:null,correct_answer:null,grading_issue:null,key_verified:false}))));rows.sort((a,b)=>a.question_number===initial?-1:b.question_number===initial?1:a.question_number-b.question_number);(window as any).__audit={attempt:{id:'audit-only',version:1,content_hash:exam.exam_id,status:'in_progress',answers:{},state:{displayed_part:Math.ceil(initial/10),current_question:initial,audio_part:Math.ceil(initial/10),playback_seconds:0,marked:[]},exam},result:{attempt_id:'audit-only',mode:'ungraded',label:'Audit only',correct_count:null,total_questions:40,graded_count:0,answered_count:0,accuracy:null,estimated_band:null,band_table_version:null,parts:[],questions:rows,exam,grading_issues:{}}};R(true)},[exam,initial]);return ready?<ListeningPage kind={mode==='review'?'review':'attempt'} id='audit-only'/>:null}`);
 }
 put('src/app/asset/[id]/route.ts',`import {readFile} from 'node:fs/promises';export async function GET(_r:Request,{params}:{params:Promise<{id:string}>}){const {id}=await params;const root=${JSON.stringify(join(root,'backend/app/content/listening_v1'))};const a=JSON.parse(await readFile(root+'/qa/assets.json','utf8')).assets.find((a:any)=>a.asset_id===id&&a.visibility==='public');if(!a)return new Response(null,{status:404});return new Response(await readFile(root+'/'+a.relative_path),{headers:{'Content-Type':a.relative_path.endsWith('.png')?'image/png':'image/jpeg'}})}`);
 const log=await import('node:fs').then(fs=>fs.openSync(join(sandbox,'server.log'),'w'));
 const server=spawn(process.execPath,[req.resolve('next/dist/bin/next'),'dev','--webpack','--hostname','127.0.0.1','--port','3391'],{cwd:sandbox,env:{...process.env,NEXT_PUBLIC_API_BASE_URL:'http://127.0.0.1:3391'},stdio:['ignore',log,log]});
 let chromium;
 try{
  for(let i=0;i<100;i++){try{if((await fetch('http://127.0.0.1:3391/?exam=cambridge-04-test-01')).ok)break;}catch{}await new Promise(r=>setTimeout(r,250));}
  chromium=await req('@playwright/test').chromium.launch({headless:true});const page=await chromium.newPage({viewport:{width:1440,height:900}});page.setDefaultTimeout(15000);
  const browserCases=[],errors=[];
  const repairs=stage2?read(join(root,'backend/scripts/listening_dataset/image_repairs.json')).repairs:[];page.on('pageerror',e=>errors.push(e.message));
  const cases=[['cambridge-04-test-01',1],['cambridge-05-test-01',1],['cambridge-09-test-02',2],['cambridge-14-test-02',2],['cambridge-18-test-02',4],['cambridge-19-test-03',1],['cambridge-14-test-01',1],['cambridge-04-test-02',2]];
  if(stage2)cases.push(['cambridge-05-test-04',2],['cambridge-11-test-03',3],['cambridge-18-test-03',1],['cambridge-19-test-01',2],['cambridge-21-test-02',3]);
  if(process.argv.includes('--final'))cases.push(['cambridge-07-test-04',1],['cambridge-06-test-03',3]);
  const snap=async()=>({visible:await page.locator('[id^="question-"]').evaluateAll(els=>els.map(e=>Number(e.id.split('-').pop()))),actual:await page.locator('[data-source-asset]').evaluateAll(els=>els.map(e=>e.getAttribute('data-source-asset')))});
  for(const [eid,pn] of cases)for(const mode of ['exam','review']){
   const record=partResults.find(p=>p.test_id===eid&&p.part===pn),q=record.visible_question_range[0];
   await page.goto(`http://127.0.0.1:3391/?exam=${eid}&q=${q}&mode=${mode}`);await page.locator(`[id="question-${q}"]`).waitFor();await page.waitForFunction(()=>[...document.querySelectorAll('[data-source-asset]')].every(e=>e.querySelector('img')?.naturalWidth>0));
   const first=await snap();assert.deepEqual(first.actual,record.actual_asset_ids);assert.equal(first.visible.length,10);
   const missing=record.expected_asset_ids.filter(a=>!first.actual.includes(a)),source=page.getByRole('region',{name:'Listening source material'}),right=page.getByRole('region',{name:'Listening questions'});
   const sourceBox=await source.count()?await source.boundingBox():null,rightBox=await right.boundingBox();
   if(sourceBox)assert(sourceBox.x+sourceBox.width<=rightBox.x+1);
   const rightBefore=await right.evaluate(e=>e.scrollTop);
   if(sourceBox)await source.evaluate(e=>{e.scrollTop=180});
   assert.equal(await right.evaluate(e=>e.scrollTop),rightBefore,'Left scroll must not move questions');
   const sourceBefore=await source.count()?await source.evaluate(e=>e.scrollTop):null;
   await right.evaluate(e=>{e.scrollTop=e.scrollHeight});const passive=await snap();assert.deepEqual(passive.actual,first.actual);
   const sourceAfter=await source.count()?await source.evaluate(e=>e.scrollTop):null;
   assert.equal(sourceAfter,sourceBefore,'Question scroll must not move materials');
   const shot=`regression-${eid}-p${pn}-${mode}.png`;await page.screenshot({path:join(browserOut,shot)});
   let transition=null;
   if(record.contexts.length>1){const target=record.contexts[1].current_question;await page.locator(`#question-${target}`).focus();await page.waitForFunction(ids=>JSON.stringify([...document.querySelectorAll('[data-source-asset]')].map(e=>e.getAttribute('data-source-asset')))===JSON.stringify(ids),record.contexts[1].actual_asset_ids);transition={target_question:target,...await snap()};assert.deepEqual(transition.actual,first.actual,'Focus must retain every material');if(sourceBox)assert.equal(await source.evaluate(e=>e.scrollTop),sourceBefore,'Focus must preserve manual source scroll');}
   let enlarged=null;
   if(stage2){const repair=repairs.find(r=>r.exam_id===eid&&r.part===pn);if(repair){const image=page.locator(`[data-source-asset="${repair.new_asset_id}"]`);await image.getByRole('button',{name:'Enlarge source image'}).click();const dialog=image.locator('dialog');await dialog.waitFor({state:'visible'});assert(await dialog.locator('img').evaluate(e=>e.naturalWidth>500));enlarged=`repaired-${eid}-p${pn}-${mode}.png`;await page.screenshot({path:join(browserOut,enlarged)});await dialog.getByRole('button',{name:'Close image',exact:true}).click();assert.deepEqual((await snap()).actual,first.actual);}}
   browserCases.push({test_id:eid,part:pn,mode,initial_current:q,expected:record.expected_asset_ids,...first,missing,status:missing.length?'CONFIRMED_MISSING_RENDER':'CONTROL_COVERED',passive_scroll_assets_unchanged:true,source_scroll_unchanged:sourceBefore===sourceAfter,transition,screenshot:shot,enlarged_screenshot:enlarged});
  }
  browser={status:'COMPLETED',exam_page:stage2?'actual ListeningPage with real Workspace/Draft/Navigator; synthetic identity/attempt API':'WorkspaceQuestions wrapper',environment:'Installed Playwright headless Chromium; actual unmodified WorkspaceQuestions + Asset + resolver + CSS; actual ListeningReview with synthetic ungraded rows, no backend/auth/AI/audio.',sandbox,cases:browserCases,page_errors:errors};
 }catch(error){browser={status:'BLOCKED',error:String(error),sandbox,cases:[]};}
 finally{await chromium?.close();server.kill('SIGTERM');}
 writeFileSync(join(browserOut,stage2?'browser-evidence.json':'regression-browser-evidence.json'),JSON.stringify(browser,null,2)+'\n');
}
const verified=new Set(browser.cases.map(c=>`${c.test_id}-p${c.part}`));
for(const p of partResults)if(verified.has(`${p.test_id}-p${p.part}`))p.evidence='browser verified + component verified';
for(const f of csv)if(browser.cases.some(c=>c.test_id===f.test_id&&c.part===f.part&&c.initial_current===f.current_question&&c.missing.length))f.evidence='browser verified (Exam + Review)';
const summary={tests:partResults.length/4,parts:partResults.length,groups,parts_with_multiple_unique_images:partResults.filter(p=>p.expected_asset_ids.length>1).length,confirmed_missing_render_parts:partResults.filter(p=>p.status==='CONFIRMED_MISSING_RENDER').length,confirmed_missing_render_states:missingStates,initial_missing_render_parts:partResults.filter(p=>p.missing_asset_ids.length).length,states_checked:states,suspected_cases:0,browser_verified_parts:verified.size,browser_verified_mode_cases:browser.cases.length,union_duplicate_pairs:0,union_order_inversions:0,wrong_part:0,empty_image_groups:emptyGroups.length,browser_status:browser.status};
mkdirSync(out,{recursive:true});writeFileSync(join(out,'part-coverage.json'),JSON.stringify({summary,definitions:{actual:'Initial current = first question; contexts list every group-first current. Expected = canonical ordered union of suitable group assets for all visible Part questions.',scope:'Current dataset, Exam and Review All. Filtered Review must union materials for visible questions only. No assertion of full physical crop quality.'},source_sha256:fingerprints,parts:partResults,empty_image_groups:emptyGroups,filtered_reproductions:filteredReproductions},null,2)+'\n');
const columns=['test_id','book','test','part','current_question','visible_question_range','active_group','expected_asset_ids','actual_asset_ids','missing_asset_ids','missing_question_ranges','severity','cause','evidence','reproduce'];const quote=v=>'"'+String(typeof v==='object'?JSON.stringify(v):v).replaceAll('"','""')+'"';writeFileSync(join(out,'regression-findings.csv'),columns.join(',')+'\n'+csv.map(r=>columns.map(c=>quote(r[c])).join(',')).join('\n')+'\n');
console.log(JSON.stringify(summary,null,2));
if(browser.status==='BLOCKED')console.error(browser.error);
// Audit mode records known failures successfully; use this explicit gate after
// an authorized fix. HTTP/image availability alone can never satisfy the gate.
if(process.argv.includes('--assert-complete')&&(missingStates||browser.status==='BLOCKED'||browser.page_errors?.length))process.exitCode=1;
