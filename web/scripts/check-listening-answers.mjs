// Visible answer controls: actual dataset + page/draft/review, local synthetic API only.
import {readFileSync,writeFileSync,openSync,readdirSync} from 'node:fs';
import {resolve,dirname,join} from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {createRequire} from 'node:module';
import {execFileSync,spawn} from 'node:child_process';
import assert from 'node:assert/strict';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..'),web=join(root,'web');
const req=createRequire(pathToFileURL(join(web,'package.json')));
const {fixture}=JSON.parse(execFileSync(process.execPath,[join(web,'scripts/check-listening-ui.mjs'),'--prepare-only'],{encoding:'utf8'}));
const put=(p,s)=>writeFileSync(join(fixture,p),s);
put('src/app/page.tsx',`import {readFile} from 'node:fs/promises';import Client from './client';export const dynamic='force-dynamic';export default async function Page({searchParams}:{searchParams:Promise<Record<string,string>>}){const q=await searchParams;const id=q.exam||'cambridge-04-test-01';if(!/^cambridge-\\d{2}-test-\\d{2}$/.test(id))throw Error('Invalid exam');return <Client exam={JSON.parse(await readFile(${JSON.stringify(join(root,'backend/app/content/listening_v1/exams/'))}+id+'.json','utf8'))} initial={Number(q.q)||1}/>}`);
put('src/app/client.tsx',`'use client';import {useState,useEffect} from 'react';import {ListeningPage} from '@/features/listening/pages';import type {Exam} from '@/features/listening/models';export default function Client({exam,initial}:{exam:Exam;initial:number}){const [ready,R]=useState(false);useEffect(()=>{const saved=sessionStorage.getItem('server');const rows=exam.parts.flatMap(p=>p.groups.flatMap(g=>g.questions.map(q=>({question_id:q.question_id,question_number:q.question_number,part_number:p.part_number,user_answer:'',correct:false,correct_answer:'fixture-only correction',grading_issue:null,key_verified:true}))));(window as any).__audit=saved?JSON.parse(saved):{attempt:{id:'local-ui',version:1,content_hash:exam.exam_id,status:'in_progress',answers:{},state:{displayed_part:Math.ceil(initial/10),current_question:initial,audio_part:Math.ceil(initial/10),playback_seconds:0,marked:[]},exam},result:{attempt_id:'local-ui',mode:'verified',label:'Local only',correct_count:0,total_questions:40,graded_count:40,answered_count:0,accuracy:0,estimated_band:null,band_table_version:null,parts:[],questions:rows,exam,grading_issues:{}}};R(true)},[exam,initial]);return ready?<ListeningPage kind='attempt' id='local-ui'/>:null}`);
let api=readFileSync(join(fixture,'src/lib/api/client.ts'),'utf8');
api=api.replace("return structuredClone(path.endsWith('/review')", "sessionStorage.setItem('server',JSON.stringify(f));return structuredClone(path.endsWith('/review')");put('src/lib/api/client.ts',api);
const examples=[
 ['matching','cambridge-04-test-01',23],['diagram_labelling','cambridge-04-test-01',28],
 ['completion_with_word_bank','cambridge-04-test-02',6],['map_labelling','cambridge-06-test-03',14],
 ['plan_labelling','cambridge-11-test-02',17],['flow_chart_completion','cambridge-12-test-06',26],
 ['multiple_choice_single','cambridge-04-test-01',21],['multiple_choice_slots','cambridge-04-test-02',25],
 ['multi_select','cambridge-04-test-03',38],['text','cambridge-04-test-01',1],
];
// One real example for every unchanged text question type as well.
const textTypes=new Set(['note_completion']);
for(const file of readdirSync(join(root,'backend/app/content/listening_v1/exams')).filter(f=>f.endsWith('.json')).sort()){
 const exam=JSON.parse(readFileSync(join(root,'backend/app/content/listening_v1/exams',file),'utf8'));
 for(const part of exam.parts)for(const group of part.groups){
  const question=group.questions.find(q=>q.input_type==='text');
  if(question&&!textTypes.has(group.question_type)){textTypes.add(group.question_type);examples.push(['text_'+group.question_type,exam.exam_id,question.question_number]);}
 }
}
if(process.argv.includes('--text-only'))examples.splice(0,10);
if(process.argv.includes('--layout-only'))examples.splice(0,examples.length,...examples.filter(([type])=>['multiple_choice_single','multiple_choice_slots','multi_select','matching'].includes(type)));
const port=3396,url=`http://127.0.0.1:${port}`,log=openSync(join(fixture,'answers.log'),'w');
const server=spawn(process.execPath,[req.resolve('next/dist/bin/next'),'dev','--webpack','--hostname','127.0.0.1','--port',String(port)],{cwd:fixture,stdio:['ignore',log,log]});
const cases=[],errors=[];
const wait=async check=>{for(let i=0;i<100;i++){if(await check())return;await new Promise(r=>setTimeout(r,100));}throw Error('Timed out');};
try{
 await wait(async()=>{try{return (await fetch(url)).ok;}catch{return false;}});
 const browser=await req('@playwright/test').chromium.launch({headless:true});
 try{for(const mobile of (process.argv.includes('--mobile-only')?[true]:[false,true]))for(const [type,eid,n] of examples){
  const context=await browser.newContext({viewport:mobile?{width:390,height:844}:{width:1440,height:900}}),page=await context.newPage();page.setDefaultTimeout(15000);page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',route=>new URL(route.request().url()).hostname==='127.0.0.1'||route.request().url().startsWith('blob:')?route.continue():route.abort());
  await page.route('**/api/listening/authorize',r=>r.fulfill({json:{}}));await page.route('**/api/listening/audio/**',r=>r.fulfill({status:404}));
  await page.goto(`${url}/?exam=${eid}&q=${n}`);await page.locator(`#question-${n}`).waitFor({state:'attached'});
  const questions=page.getByRole('region',{name:'Listening questions',exact:true});
  assert.equal(await questions.locator('select,[role=combobox],[role=listbox]').count(),0);
  const exam=JSON.parse(readFileSync(join(root,'backend/app/content/listening_v1/exams',eid+'.json'),'utf8'));
  const group=exam.parts.flatMap(p=>p.groups).find(g=>g.questions.some(q=>q.question_number===n));
  const question=group.questions.find(q=>q.question_number===n),key=question.question_id;
  const source=page.getByRole('region',{name:'Listening source material',includeHidden:true});
  const ids=()=>source.locator('[data-source-asset]').evaluateAll(es=>es.map(e=>e.getAttribute('data-source-asset')));
  const assets=await ids();let expected;
  const field=()=>page.locator(`#question-${n}`);
  const sync=async value=>{await page.waitForFunction(({key,value})=>window.__audit.attempt.answers[key]===value,{key,value});};
  if(type.startsWith('text')){
   await field().getByRole('textbox').fill('first answer');await sync('first answer');await field().getByRole('textbox').clear();await sync('');await field().getByRole('textbox').fill('restored text');expected='restored text';
  }else{
   const options=question.options.length?question.options:group.answer_bank.options;
   const inputs=field().locator('input');assert.equal(await inputs.count(),options.length);
   if(group.question_type.startsWith('multiple_choice')){
    const boxes=await field().locator('label:has(input)').evaluateAll(es=>es.map(e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return {x:r.x,y:r.y,bottom:r.bottom,padding:s.padding,font:s.fontSize,minHeight:s.minHeight};}));
    assert(boxes.every((b,i)=>b.x===boxes[0].x&&(!i||b.y>=boxes[i-1].bottom)), 'Existing multiple choice must retain its vertical list');
    assert(boxes.every(b=>b.padding===(mobile?'13px 10px':'13px 16px')&&b.font===(mobile?'13px':'14px')&&b.minHeight==='48px'), 'Existing multiple choice dimensions must remain unchanged');
   }
   if(group.answer_bank){const bank=questions.locator(`[data-question-group="${group.group_id}"]`).getByRole('region',{name:'Answer bank'});assert(await bank.isVisible());for(const op of group.answer_bank.options)if(op.text)assert((await bank.textContent()).includes(op.text));}
   await inputs.nth(0).check();await sync(options[0].label);
   if(type==='multi_select'){
    await inputs.nth(1).check();expected=options.slice(0,2).map(o=>o.label).join(' ');await sync(expected);assert(await inputs.nth(2).isDisabled());await inputs.nth(0).uncheck();assert(await inputs.nth(2).isEnabled());await inputs.nth(2).check();expected=options.slice(1,3).map(o=>o.label).join(' ');await sync(expected);
   }else{
    await inputs.nth(0).focus();await page.keyboard.press('ArrowRight');expected=options[1].label;await sync(expected);assert(await inputs.nth(1).isChecked());
    if(type==='multiple_choice_slots'){
     const other=page.locator(`#question-${n+1}`);assert(await other.locator(`input[value="${expected}"]`).isDisabled());await other.locator('input').nth(0).check();await page.waitForFunction(key=>!!window.__audit.attempt.answers[key],group.questions[1].question_id);
    }
   }
   await field().getByRole('button',{name:'Clear selection',exact:true}).click();await sync('');assert.equal(await field().locator('input:checked').count(),0);
   if(type==='multiple_choice_slots')assert(await page.locator(`#question-${n+1} input[value="${expected}"]`).isEnabled());
   if(type==='multi_select'){await inputs.nth(0).check();await inputs.nth(1).check();expected=options.slice(0,2).map(o=>o.label).join(' ');}else{await inputs.nth(1).check();expected=options[1].label;}
  }
  await sync(expected);assert.deepEqual(await ids(),assets);assert.equal(await page.getByText('fixture-only correction',{exact:true}).count(),0);
  // An option may be reused by another question unless the schema says distinct.
  if(type==='matching'&&!group.selection?.distinct&&group.questions.length>1){const other=group.questions.find(q=>q.question_number!==n);await page.locator(`#question-${other.question_number} input[value="${expected}"]`).check();}
  const part=Math.ceil(n/10),next=part===4?1:part+1;
  await page.getByRole('button',{name:new RegExp('^Part '+next)}).click();await page.getByRole('button',{name:new RegExp('^Part '+part)}).click();assert.deepEqual(await ids(),assets);
  await page.reload();await page.locator(`#question-${n}`).waitFor({state:'attached'});await sync(expected);
  if(type.startsWith('text'))assert.equal(await field().getByRole('textbox').inputValue(),expected);else assert.deepEqual(await field().locator('input:checked').evaluateAll(es=>es.map(e=>e.value)),expected.split(' '));
  // Check the real rendered controls and bank on desktop/mobile, including focus.
  await field().scrollIntoViewIfNeeded();await page.screenshot({path:join(fixture,`${type}-${mobile?'mobile':'desktop'}.png`)});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1&&document.documentElement.scrollHeight<=innerHeight+1));
  await page.getByRole('button',{name:'Finish practice',exact:true}).click();await page.getByRole('button',{name:'Finish and view results',exact:true}).click();await page.waitForURL(/\/results$/);
  await page.getByRole('link',{name:'Review all questions'}).click();await page.getByRole('heading',{name:'Review your answers'}).waitFor();
  await page.getByRole('button',{name:'Question navigator',exact:true}).click();await page.getByRole('button',{name:`Go to question ${n}`,exact:true}).click();
  assert((await field().textContent()).includes(expected));assert((await field().textContent()).includes('fixture-only correction'));assert.equal(await field().getAttribute('data-review-status'),'incorrect');assert.equal(await questions.locator('input,select,[role=combobox]').count(),0);
  cases.push({type,eid,question:n,mobile,status:'PASS'});await context.close();
 }}finally{await browser.close();}
 assert.equal(errors.length,0,JSON.stringify(errors));
}catch(error){errors.push(String(error));process.exitCode=1;}finally{server.kill('SIGTERM');}
writeFileSync(join(fixture,'answer-results.json'),JSON.stringify({cases,errors},null,2));console.log(JSON.stringify({passed:cases.length,cases,errors,artifacts:fixture},null,2));
