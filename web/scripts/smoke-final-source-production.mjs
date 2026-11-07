// Mutating smoke: ONLY a dedicated QA profile with exact display-name/learner guards.
// Requires a private short-lived Firebase session at /tmp/alua-submit-hotfix-qa-private.json.
// Never use a real learner session; creates only ordinary QA API attempts.
import {readFileSync,writeFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import {dirname,resolve} from 'node:path';
import assert from 'node:assert/strict';
import {randomUUID} from 'node:crypto';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..'),require=createRequire(root+'/web/package.json');
const {chromium}=require('@playwright/test');
const auth=JSON.parse(readFileSync('/tmp/alua-submit-hotfix-qa-private.json','utf8'));
const base=process.env.ALUA_SMOKE_BASE||'https://alua.study';assert(['https://alua.study','https://source-image-budget-alua-ielts.yeskendiriskakov.workers.dev'].includes(base),'Unapproved smoke origin');const headers={Authorization:'Bearer '+auth.idToken};
const user={uid:auth.uid,email:auth.email,emailVerified:true,isAnonymous:false,providerData:[],stsTokenManager:{refreshToken:auth.refreshToken,accessToken:auth.idToken,expirationTime:Date.now()+Number(auth.expiresIn)*1000},apiKey:auth.apiKey,appName:'alua-web'};
const browser=await chromium.launch({headless:true});const results=[],errors=[],assetResponses=[],assetFailures=[];let lastPage;
const profile=await fetch(base+'/api/alua/me',{headers}).then(r=>r.json());assert(profile.uid===auth.learner_id&&profile.display_name==='ALUA QA Release');
async function api(path,body){const r=await fetch(base+'/api/alua'+path,{headers:{...headers,'Content-Type':'application/json'},...(body?{method:'POST',body:JSON.stringify(body)}:{})});assert(r.ok,`${path.replace(/[0-9a-f-]{36}/g,'QA-ID')} HTTP ${r.status}`);return r.json();}
try{
 for(const [kind,count,mobile] of (process.argv.includes('--sources-only')?[]:[['listening',15,false],['listening',40,true],['reading',15,true],['reading',40,false]])){
  const eid=kind==='listening'?'cambridge-14-test-01':'cambridge-18-test-01';
  const created=await api('/'+kind+'/attempts',{event_id:randomUUID(),exam_id:eid,reuse_active:false,...(kind==='reading'?{mode:'full_exam'}:{})});
  const context=await browser.newContext({viewport:mobile?{width:390,height:844}:{width:1440,height:1000},isMobile:mobile,hasTouch:mobile});
  await context.addInitScript(({key,user})=>localStorage.setItem(key,JSON.stringify(user)),{key:`firebase:authUser:${auth.apiKey}:alua-web`,user});
  let rejected=false;const seen=[],submitPayloads=[],assetRequests=[];
  await context.route('**/api/alua/**',async route=>{
   const req=route.request(),url=new URL(req.url());
   if(!['GET','HEAD'].includes(req.method())){
    assert(url.pathname.includes('/'+kind+'/attempts/'+created.id),'Refusing mutation outside dedicated QA attempt');
    if(url.pathname.endsWith('/submit')){
     const body=req.postDataJSON();submitPayloads.push(structuredClone(body));seen.push(body.event_id);
     if(!rejected){rejected=true;body.answers_checksum='0'.repeat(64);return route.continue({postData:JSON.stringify(body)});}
    }
   }
   if(url.pathname.includes('/assets/'))assetRequests.push(url.pathname);
   return route.continue();
  });
  const page=await context.newPage();lastPage=page;page.on('response',r=>{if(r.url().includes('/assets/'))assetResponses.push({asset:r.url().split('/').pop(),status:r.status()})});page.on('requestfailed',r=>{if(r.url().includes('/assets/'))assetFailures.push({asset:r.url().split('/').pop(),error:r.failure()?.errorText})});page.setDefaultTimeout(35000);page.on('pageerror',e=>errors.push({kind,type:e.name,message:e.message.slice(0,180)}));
  await page.goto(`${base}/${kind}/attempts/${created.id}`);
  const showQuestions=async()=>{const b=page.getByRole('button',{name:'Questions',exact:true});if(await b.isVisible())await b.click();};
  const go=async n=>{await page.getByRole('button',{name:`Part ${Math.ceil(n/10)}`,exact:false}).first().click();await showQuestions();await page.locator(`#question-${n}`).waitFor({state:'attached'});await page.waitForFunction(()=>document.querySelectorAll('[data-source-asset]').length>0&&[...document.querySelectorAll('[data-source-asset]')].every(e=>e.querySelector('img')?.naturalWidth>0),null,{timeout:80_000});};
  if(kind==='listening'){
   await page.getByRole('button',{name:'Finish',exact:true}).waitFor();assert.equal(await page.locator('main>footer').count(),0);assert(await page.locator('main[data-exam-mode=compact]').isVisible());await showQuestions();
   for(let n=1;n<=count;n++){
    if([11,21,31].includes(n))await go(n);
    const q=page.locator(`#question-${n}`),input=q.locator('input[type=text],input:not([type])');
    if(await input.count())await input.fill('qa');else await q.locator('input[type=radio]:not(:disabled)').first().check();
   }
  }else{
   await page.getByRole('button',{name:'Finish',exact:true}).waitFor();await showQuestions();
   for(let n=1;n<=count;n++){
    if(n===14||n===27)await page.getByRole('button',{name:`Passage ${n===14?2:3}`,exact:true}).click();
    const input=page.getByLabel(`Answer ${n}`,{exact:true});
    if(await input.evaluate(e=>e.tagName==='INPUT'))await input.fill('qa');else await input.locator('button:not(:disabled)').first().click();
   }
  }
  const finish=async()=>{
   await page.getByRole('button',{name:kind==='listening'?'Finish':'Finish',exact:true}).click();
   const response=page.waitForResponse(r=>r.url().endsWith('/submit')&&r.request().method()==='POST');
   await page.getByRole('button',{name:kind==='listening'?'Finish and view results':'Finish test',exact:true}).click();return response;
  };
  const denial=await finish();assert.equal(denial.status(),422);const denialBody=await denial.json();assert.equal(denialBody.error?.code,'validation_error');
  if(kind==='listening'){await go(1);}else await page.getByRole('button',{name:'Passage 1',exact:true}).click();
  const first=page.getByLabel(kind==='listening'?'Question 1':'Answer 1',{exact:true});await first.waitFor();assert(await first.isEnabled());const saved=page.waitForResponse(r=>r.url().endsWith('/sync')&&r.status()===200);await first.fill('recovered');await saved;
  await page.reload();await showQuestions();await first.waitFor();assert.equal(await first.inputValue(),'recovered');assert(await first.isEnabled());
  let player=null,returnAssetGETs=null;
  if(kind==='listening'){
   const audio=page.locator('audio').first();await page.waitForFunction(()=>document.querySelector('audio')?.readyState>0);
   await page.getByRole('button',{name:'Play',exact:true}).click();await page.waitForFunction(()=>document.querySelector('audio')?.currentTime>.1);
   await page.getByLabel('Audio progress').fill('15');await go(11);const p=await audio.evaluate(a=>({paused:a.paused,current:a.currentTime}));assert(!p.paused&&p.current>=14);
   await go(21);await go(1);const baseline=assetRequests.length,prepared=new Set(assetRequests);await go(11);await go(21);await go(1);returnAssetGETs=assetRequests.slice(baseline).filter(path=>prepared.has(path)).length;assert.equal(returnAssetGETs,0);
   await page.getByRole('button',{name:'Pause',exact:true}).click();player='PASS';
  }
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  await page.screenshot({path:root+`/docs/listening-final-source-release/production-${kind}-${mobile?'mobile':'desktop'}.png`});
  const accepted=await finish();assert.equal(accepted.status(),200);const final=await accepted.json();assert.equal(final.final_snapshot_accepted,true);assert.equal(Object.values(final.answers).filter(Boolean).length,count);assert.notEqual(seen[0],seen.at(-1));assert.deepEqual(final.answers,submitPayloads.at(-1).answers);assert.equal(final.answers_checksum,submitPayloads.at(-1).answers_checksum);const replay=await api('/'+kind+'/attempts/'+created.id+'/submit',submitPayloads.at(-1));assert.deepEqual(replay,final);const changed=await fetch(base+'/api/alua/'+kind+'/attempts/'+created.id+'/submit',{method:'POST',headers:{...headers,'Content-Type':'application/json'},body:JSON.stringify({...submitPayloads.at(-1),local_revision:submitPayloads.at(-1).local_revision+1})});assert.equal(changed.status,409);
  const result=await api('/'+kind+'/attempts/'+created.id+'/result');const rows=result.questions??result.positions;assert.equal(rows.filter(r=>r.user_answer).length,count);
  if(kind==='listening'){await page.getByRole('link',{name:'Review all questions'}).click();await page.getByRole('heading',{name:'Review your answers'}).waitFor();}
  else{await page.getByRole('heading',{name:'Your result.'}).waitFor();await page.getByRole('link',{name:/^Review (?:\d+ mistakes?|all answers)$/}).click();await showQuestions();await page.getByLabel('Answer 1',{exact:true}).waitFor();assert(await page.getByLabel('Answer 1',{exact:true}).isDisabled());}
  results.push({kind,count,viewport:mobile?'mobile':'desktop',exam:'PASS',real_backend_422_recovery:'PASS',reload:'PASS',submit:'PASS',backend_result_count:rows.filter(r=>r.user_answer).length,review:'PASS',player,duplicate_asset_GETs_on_return:returnAssetGETs});console.log(JSON.stringify(results.at(-1)));await context.close();
 }

 const registry=JSON.parse(readFileSync(root+'/web/src/features/listening/visual-materials.json','utf8'));
 for(const [eid,part,mobile]of (process.argv.includes('--answers-only')?[]:[['cambridge-04-test-01',4,false],['cambridge-06-test-02',1,true],['cambridge-07-test-04',1,false],['cambridge-14-test-03',1,true]])){
  const created=await api('/listening/attempts',{event_id:randomUUID(),exam_id:eid,reuse_active:false});
  const context=await browser.newContext({viewport:mobile?{width:390,height:844}:{width:1440,height:900},isMobile:mobile,hasTouch:mobile});
  await context.addInitScript(({key,user})=>localStorage.setItem(key,JSON.stringify(user)),{key:`firebase:authUser:${auth.apiKey}:alua-web`,user});
  await context.route('**/api/alua/**',route=>{if(!['GET','HEAD'].includes(route.request().method()))assert(new URL(route.request().url()).pathname.includes('/listening/attempts/'+created.id),'Refusing non-QA mutation');return route.continue();});
  const page=await context.newPage();lastPage=page;page.on('response',r=>{if(r.url().includes('/assets/'))assetResponses.push({asset:r.url().split('/').pop(),status:r.status()})});page.on('requestfailed',r=>{if(r.url().includes('/assets/'))assetFailures.push({asset:r.url().split('/').pop(),error:r.failure()?.errorText})});page.setDefaultTimeout(35000);page.on('pageerror',e=>errors.push({kind:'source',type:e.name,message:e.message.slice(0,180)}));
  await page.goto(base+'/listening/attempts/'+created.id);await page.locator('#question-1').waitFor({state:'attached'});
  const expected=registry.parts[eid+'-p'+part].materials.map(m=>m.asset_id);
  const verify=async()=>{
   await page.getByRole('region',{name:'Listening audio player'}).getByRole('button',{name:new RegExp('^Part '+part)}).click();
   const tab=page.getByRole('button',{name:'Source material',exact:true});if(await tab.isVisible())await tab.click();
   const source=page.getByRole('region',{name:'Listening source material',includeHidden:true});
   await page.waitForFunction(()=>[...document.querySelectorAll('[data-source-asset]')].length>0&&[...document.querySelectorAll('[data-source-asset]')].every(e=>e.querySelector('img')?.naturalWidth>0),null,{timeout:80_000});
   const ids=()=>source.locator('[data-source-asset]').evaluateAll(es=>es.map(e=>e.getAttribute('data-source-asset')));assert.deepEqual(await ids(),expected);
   await source.evaluate(e=>e.scrollTop=120);const scroll=await source.evaluate(e=>e.scrollTop);
   const qt=page.getByRole('button',{name:'Questions',exact:true});if(await qt.isVisible())await qt.click();
   await page.locator('#question-'+(part*10)).focus();assert.deepEqual(await ids(),expected);if(await tab.isVisible())await tab.click();assert.equal(await source.evaluate(e=>e.scrollTop),scroll);
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  };
  await verify();await page.getByRole('button',{name:'Finish',exact:true}).click();const submitted=page.waitForResponse(r=>r.url().endsWith('/submit')&&r.status()===200);await page.getByRole('button',{name:'Finish and view results',exact:true}).click();assert.equal((await(await submitted).json()).final_snapshot_accepted,true);
  await page.getByRole('link',{name:'Review all questions'}).click();await page.getByRole('heading',{name:'Review your answers'}).waitFor();await verify();
  const tab=page.getByRole('button',{name:'Source material',exact:true});if(await tab.isVisible())await tab.click();await page.screenshot({path:root+'/docs/listening-final-source-release/production-source-'+eid+'-p'+part+'.png'});
  results.push({kind:'source',exam_id:eid,part,viewport:mobile?'mobile':'desktop',exam:'PASS',review:'PASS',ordered_assets:expected,focus_invariance:'PASS',source_fidelity:eid==='cambridge-14-test-03'?'UNRESOLVED original layout; retained full fallback':'VERIFIED'});await context.close();
 }
 assert.equal(errors.length,0);
}catch(e){errors.push({type:'check_failure',message:e.message.slice(0,300),images:lastPage&&!lastPage.isClosed()?await lastPage.locator('[data-source-asset]').evaluateAll(es=>es.map(e=>({asset:e.getAttribute('data-source-asset'),width:e.querySelector('img')?.naturalWidth||0,error:!!e.querySelector('[role=alert]')}))).catch(()=>[]):[]});console.log('PRODUCTION_BROWSER_CHECK_FAILED',e.message);process.exitCode=1;}finally{await browser.close();writeFileSync(root+'/docs/listening-final-source-release/'+((base.includes('workers.dev')?'preview-':'')+(process.argv.includes('--sources-only')?'production-source-browser.json':process.argv.includes('--answers-only')?'production-answer-browser.json':'production-browser.json')),JSON.stringify({origin:base,results,page_errors:errors,assetResponses,assetFailures},null,2)+'\n');}
