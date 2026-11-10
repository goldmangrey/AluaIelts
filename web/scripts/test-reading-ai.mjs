// Full local Next → FastAPI → Next Worker route → mocked adapter → FastAPI validation.
import {mkdtemp,cp,symlink,mkdir,writeFile,readFile,rm} from 'node:fs/promises';
import {createRequire} from 'node:module';
import {tmpdir} from 'node:os';
import {resolve,dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawn} from 'node:child_process';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..'),require=createRequire(import.meta.url);
const {chromium,webkit,expect}=require('@playwright/test');
if(!process.env.ALUA_READING_AI_FIXTURE)throw Error('Run through pytest disposable backend fixture.');
const fixture=JSON.parse(await readFile(process.env.ALUA_READING_AI_FIXTURE,'utf8'));
const temp=await mkdtemp(join(tmpdir(),'alua-reading-ai-browser-')),output=join(root,'docs/reading-ai-review-v1');
await mkdir(output,{recursive:true});let server,log='';const checks=[];
async function file(name,text){const path=join(temp,name);await mkdir(dirname(path),{recursive:true});await writeFile(path,text);}
try{
 for(const name of ['src','public','package.json','tsconfig.json','next.config.ts','postcss.config.mjs'])await cp(join(root,name),join(temp,name),{recursive:true});
 await symlink(join(root,'node_modules'),join(temp,'node_modules'),'dir');
 await file('src/lib/firebase/client.ts',`import type {Auth} from 'firebase/auth';export function firebaseConfigured(){return true}export async function getFirebaseAuth():Promise<Auth>{throw Error('Local fixture only')}export async function getIdToken(){return ${JSON.stringify(fixture.token)}}`);
 await file('src/features/auth/session.ts',`'use client';import {useSyncExternalStore} from 'react';const initial={status:'loading' as const,user:null,profile:null,generation:0};const ready={status:'ready' as const,user:{uid:${JSON.stringify(fixture.uid)},email:null},profile:null,generation:1};export function useSession(){return useSyncExternalStore(()=>()=>{},()=>ready,()=>initial)}export async function prepareGoogleAuth(){return async()=>{}}export async function retrySession(){}export async function logout(){}export async function authenticate(){}export function rejectSession(){}`);
 let route=await readFile(join(root,'src/app/api/reading/explain/route.ts'),'utf8');
 route=route.replace("import {getCloudflareContext} from '@opennextjs/cloudflare';",'').replace('const env=(await getCloudflareContext({async:true})).env as AIEnv;',"const env:AIEnv={GROQ_API_KEY:'local-fixture-only'};");
 await file('src/app/api/reading/explain/route.ts',route);
 await file('src/lib/ai/adapters/groq.ts',`import type {Adapter} from './common';
export const groqAdapter:Adapter=async(_env,_model,input,signal)=>{
 const data=JSON.parse(input.messages.find(m=>m.role==='user')!.content.split('\\n').slice(1).join('\\n'));
 if(data.question_number===8)await new Promise<void>((resolve,reject)=>{const t=setTimeout(resolve,800);signal.addEventListener('abort',()=>{clearTimeout(t);reject(Error())},{once:true});});
 let evidence:any[]=[];
 if(data.grounding.mode==='heading'){const i=data.blocks.findIndex((b:any)=>data.grounding.targets.includes(b.label));if(i>=0)evidence=[{block_index:i,quote:data.blocks[i].text.slice(0,1200),kind:'support'}];}
 for(let i=0;i<data.blocks.length&&!evidence.length;i++)for(const target of data.grounding.targets){const b=data.blocks[i];if(b.type!=='paragraph')continue;const at=b.text.toLowerCase().indexOf(target.toLowerCase());if(at<0)continue;let left=b.text.lastIndexOf('.',at-1)+1;const right=b.text.indexOf('.',at+target.length);let quote=b.text.slice(left,right<0?undefined:right+1).trim();if(data.grounding.focus&&!data.grounding.focus.some((w:string)=>(quote.toLowerCase().match(/[a-z]{3,}/g)||[]).includes(w))){left=b.text.lastIndexOf('.',Math.max(0,left-2))+1;quote=b.text.slice(left,right<0?undefined:right+1).trim();}if(data.grounding.focus&&!data.grounding.focus.some((w:string)=>(quote.toLowerCase().match(/[a-z]{3,}/g)||[]).includes(w)))continue;if(b.text.indexOf(quote,b.text.indexOf(quote)+1)<0)evidence=[{block_index:i,quote,kind:data.not_given?'relevant_context':'support'}];}
 return {response:JSON.stringify({why_user_answer_wrong:'В сохранённом ответе указано другое слово. Сравните его с условием задания и цитатой.',why_correct_answer_works:data.grounding.mode==='heading'?'Сохранённый ключ связывает heading с основной темой указанного абзаца. Цитата показывает контекст.':'Цитата содержит слово из сохранённого ключа и показывает его контекст.',ielts_tip:'Для Summary Completion проверьте точную форму слова и ограничение количества слов.',evidence_status:evidence.length?'found':'unavailable',evidence})};
};`);
 const env={...process.env,NEXT_PUBLIC_API_BASE_URL:'http://127.0.0.1:3427/api/v1'};
 for(const key of Object.keys(env))if(key.startsWith('NEXT_PUBLIC_FIREBASE'))env[key]='';
 server=spawn(process.execPath,[require.resolve('next/dist/bin/next'),'dev','--webpack','--hostname','127.0.0.1','--port','3327'],{cwd:temp,env,stdio:['ignore','pipe','pipe']});
 server.stdout.on('data',d=>{log+=d;});server.stderr.on('data',d=>{log+=d;});
 for(let n=0;n<120;n++){try{if((await fetch('http://127.0.0.1:3327')).ok)break;}catch{}await new Promise(r=>setTimeout(r,250));if(n===119)throw Error(log.slice(-2500));}
 for(const [name,engine,viewport]of [['desktop',chromium,{width:1366,height:768}],['mobile',webkit,{width:390,height:844}]]){
  const browser=await engine.launch({headless:true});
  try{
   const context=await browser.newContext({viewport}),page=await context.newPage();page.setDefaultTimeout(20000);
   const errors=[];page.on('pageerror',e=>errors.push(e.message));
   await page.route('**/*',r=>{const u=r.request().url();return u.startsWith('blob:')||['localhost','127.0.0.1'].includes(new URL(u).hostname)?r.continue():r.abort();});
   let requests=0;page.on('request',r=>{if(r.url().endsWith('/api/reading/review'))requests++;});
   const aid=fixture.attempt.id;
   await page.goto(`http://127.0.0.1:3327/reading/attempts/${aid}/result`);
   await page.locator(`a[href="/reading/attempts/${aid}/review"]`).first().waitFor();
   await page.evaluate(async fixture=>{
     localStorage.setItem(`alua:reading:bookmarks:v2:${fixture.uid}:${fixture.attempt.id}:${fixture.highlight.passageId}`,'[3]');
     await new Promise((resolve,reject)=>{const req=indexedDB.open('alua-reading-drafts',1);req.onupgradeneeded=()=>{req.result.createObjectStore('drafts',{keyPath:'key'});req.result.createObjectStore('leases',{keyPath:'key'});};req.onerror=()=>reject(req.error);req.onsuccess=()=>{const db=req.result,tx=db.transaction('drafts','readwrite');tx.objectStore('drafts').put({key:JSON.stringify([fixture.uid,fixture.attempt.id,fixture.attempt.content_hash]),uid:fixture.uid,attemptId:fixture.attempt.id,hash:fixture.attempt.content_hash,view:{highlights:[fixture.highlight]}});tx.oncomplete=()=>{db.close();resolve();};};});
   },fixture);
   await page.locator(`a[href="/reading/attempts/${aid}/review"]`).first().click();
   await expect(page.getByRole('button',{name:'All 40',exact:true})).toBeVisible();
   async function go(number){await page.getByRole('button',{name:'All 40',exact:true}).click();await page.getByRole('button',{name:new RegExp('^Question '+number+',')}).click();}
   await go(7);const explain=page.getByRole('button',{name:'Explain question 7 with AI',exact:true});
   await expect(explain).toBeVisible();await page.screenshot({path:join(output,`${name}-closed.png`),fullPage:true});
   await explain.focus();await page.keyboard.press('Enter');
   const card=page.getByRole('region',{name:'AI explanation for question 7',exact:true});
   await expect(card.getByRole('button',{name:'Show in passage'})).toBeVisible();
   await expect(explain).toHaveAttribute('aria-expanded','true');await page.screenshot({path:join(output,`${name}-open.png`),fullPage:true});
   await card.getByRole('button',{name:'Show in passage'}).click();
   const mark=page.locator('[data-reading-ai="true"]').first();await expect(mark).toBeVisible();
   await expect(page.getByRole('button',{name:'Back to Q7'})).toBeVisible();
   const inContainer=await mark.evaluate(el=>{const a=el.getBoundingClientRect(),b=el.closest('.passage-scroll').getBoundingClientRect();return a.top>=b.top&&a.top<b.bottom;});expect(inContainer).toBe(true);
   await page.screenshot({path:join(output,`${name}-evidence.png`),fullPage:true});
   expect(await page.locator('mark[data-reading-ai][class*="userEvidence"]').count()).toBeGreaterThan(0);
   await page.route('**/api/translate',r=>r.fulfill({json:{expression:r.request().postDataJSON().selected,translation:'контекст'}}));
   await page.getByRole('button',{name:'Translate',exact:true}).click();
   await page.getByRole('button',{name:'Back to Q7'}).click();await card.getByRole('button',{name:'Show in passage'}).click();await page.waitForTimeout(350);
   const point=await page.locator(`[data-highlight-block="${fixture.highlight.block}"]`).evaluate((span,word)=>{
     const text=span.textContent,at=text.toLowerCase().indexOf(word.toLowerCase()),walker=document.createTreeWalker(span,NodeFilter.SHOW_TEXT);let node,offset=0,start,end;
     while((node=walker.nextNode())){const size=node.textContent.length;if(!start&&at<offset+size)start={node,offset:at-offset};if(at+word.length<=offset+size){end={node,offset:at+word.length-offset};break;}offset+=size;}
     const range=document.createRange();range.setStart(start.node,start.offset);range.setEnd(end.node,end.offset);const rect=range.getClientRects()[0];return {x:rect.x+rect.width/2,y:rect.y+rect.height/2};
   },fixture.target);
   await page.mouse.click(point.x,point.y);await expect(page.getByRole('status',{name:'Перевод',exact:true})).toContainText('контекст');
   await page.getByRole('button',{name:'Закрыть перевод',exact:true}).click();
   expect(await page.evaluate(f=>localStorage.getItem(`alua:reading:bookmarks:v2:${f.uid}:${f.attempt.id}:${f.highlight.passageId}`),fixture)).toBe('[3]');

   await page.getByRole('button',{name:'Back to Q7'}).click();await expect(card).toBeVisible();
   const before=requests;await explain.click();await expect(card).toHaveCount(0);await explain.click();await expect(card.getByText('Saved explanation')).toBeVisible();expect(requests).toBe(before);
   // A different question/passage clears the active evidence. Late responses cannot attach to Q7.
   await go(8);await page.getByRole('button',{name:'Explain question 8 with AI',exact:true}).click();await go(7);await explain.click();
   await expect(page.getByRole('region',{name:'AI explanation for question 7',exact:true})).toBeVisible();await page.waitForTimeout(1000);
   expect(await page.getByRole('region',{name:'AI explanation for question 8',exact:true}).count()).toBe(0);
   await page.getByRole('button',{name:'Passage 2',exact:true}).click();expect(await page.locator('[data-reading-ai="true"]').count()).toBe(0);
   // Error/retry state: transport is mocked only for this explicit negative case.
   await go(6);let fail='rate';await page.route('**/api/reading/review',r=>fail?r.fulfill({status:fail==='rate'?429:503,json:{error:{code:'reading_ai_unavailable'}}}):r.continue());
   await page.getByRole('button',{name:'Explain question 6 with AI',exact:true}).click();
   const q6=page.getByRole('region',{name:'AI explanation for question 6',exact:true});await expect(q6.getByRole('alert')).toContainText('через минуту');fail='provider';await q6.getByRole('button',{name:'Retry',exact:true}).click();await expect(q6.getByRole('alert')).toContainText('временно недоступен');fail='';await q6.getByRole('button',{name:'Retry',exact:true}).click();await expect(q6.getByRole('button',{name:'Show in passage'})).toBeVisible();
   await page.route('**/api/reading/review',r=>r.request().postDataJSON().question_id.endsWith('-09')?r.fulfill({json:{question_id:r.request().postDataJSON().question_id,fingerprint:'synthetic-unavailable',source_status:'needs_review',cached:false,review:{why_user_answer_wrong:'Не удалось надёжно подтвердить фрагмент текста для этого вопроса.',why_correct_answer_works:'Подтверждённого объяснения по доступному тексту сейчас нет.',ielts_tip:'Сопоставьте формулировку задания с полным контекстом.',evidence_status:'unavailable',evidence:[],reason:'visual_context_unavailable'}}}):r.fallback());
   await go(9);await page.getByRole('button',{name:'Explain question 9 with AI',exact:true}).click();const limited=page.getByRole('region',{name:'AI explanation for question 9',exact:true});await expect(limited).toContainText('Подсветка недоступна');expect(await limited.getByRole('button',{name:'Show in passage'}).count()).toBe(0);expect(await page.locator('[data-reading-ai="true"]').count()).toBe(0);await page.screenshot({path:join(output,`${name}-unavailable.png`),fullPage:true});
   await go(16);await page.getByRole('button',{name:'Explain question 16 with AI',exact:true}).click();const heading=page.getByRole('region',{name:'AI explanation for question 16',exact:true});await expect(heading.getByRole('button',{name:'Show in passage'})).toBeVisible();await heading.getByRole('button',{name:'Show in passage'}).click();await expect(page.locator('[data-reading-ai="true"]').first()).toBeVisible();await page.getByRole('button',{name:'Back to Q16'}).click();
   await go(37);await expect(page.getByRole('button',{name:'Explain question 37 with AI',exact:true})).toBeVisible();
   expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);expect(errors).toEqual([]);
   // No answer mutation is made by any review action.
   const current=await page.request.get(`http://127.0.0.1:3427/api/v1/reading/attempts/${aid}`,{headers:{Authorization:`Bearer ${fixture.token}`}});
   expect((await current.json()).answers).toEqual(fixture.attempt.answers);
   checks.push({name,passed:true,requests,screenshots:[`${name}-closed.png`,`${name}-open.png`,`${name}-evidence.png`]});
   await context.close();
  }finally{await browser.close();}
 }
 await writeFile(join(output,'results.json'),JSON.stringify(checks,null,2));console.log('2 PASS — real local Reading Result → Review → AI → evidence → return; retry, cache and stale responses');
}catch(error){console.error(log.slice(-2500));throw error;}
finally{if(server){server.kill('SIGTERM');if(server.exitCode===null)await new Promise(r=>server.once('exit',r));}await rm(temp,{recursive:true,force:true});}
