// Actual controllers, deterministic transport/store failures; no production services.
import {readFileSync} from 'node:fs';
import {resolve,dirname,join} from 'node:path';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import {runInNewContext} from 'node:vm';
import {webcrypto} from 'node:crypto';
import assert from 'node:assert/strict';
const web=resolve(dirname(fileURLToPath(import.meta.url)),'..'),req=createRequire(import.meta.url),ts=req('typescript');
class ApiError extends Error{constructor(status,code){super(code);this.status=status;this.code=code;}}
export function loadController(relative,api,storage=new Map(),globals={}){
 const cache=new Map();
 const scope={console,crypto:webcrypto,structuredClone,setTimeout,clearTimeout,setInterval,clearInterval,queueMicrotask,TextEncoder,performance,AbortController,URL,Blob,localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)},navigator:{onLine:true},window:undefined,...globals};
 function load(path){if(cache.has(path))return cache.get(path).exports;const m={exports:{}};cache.set(path,m);
 const local=id=>{if(id==='@/lib/api/client')return {ApiError};if(id==='./api')return {api:()=>api,attempt:()=>api('get'),eventId:()=>webcrypto.randomUUID()};if(id.startsWith('.')||id.startsWith('@/')){let p=id.startsWith('@/')?join(web,'src',id.slice(2)):resolve(dirname(path),id);if(p.endsWith('.json'))return JSON.parse(readFileSync(p));if(!p.endsWith('.ts'))p+='.ts';return load(p);}return req(id);};
 runInNewContext(ts.transpileModule(readFileSync(path,'utf8'),{compilerOptions:{target:99,module:1,esModuleInterop:true}}).outputText,{...scope,exports:m.exports,module:m,require:local});return m.exports;}
 return load(join(web,relative));
}
export function fakeStore(){let record,leased=false,fail=false;return {read:async()=>structuredClone(record),write:async v=>{if(fail)throw Error('device storage failure');record=structuredClone(v);},acquire:async()=>{leased=true;return true;},release:async()=>{leased=false;},record:()=>record,fail:v=>{fail=v;},leased:()=>leased};}
export function fixture(kind){const ids=Array.from({length:40},(_,i)=>`exam-q${String(i+1).padStart(2,'0')}`);return {ids,initial:{id:'attempt',exam_id:'exam',content_hash:'hash',version:0,status:'in_progress',answers:{},server_now:'2026-01-01T00:00:00Z',deadline_at:null,state:kind==='listening'?{displayed_part:1,current_question:1,audio_part:1,playback_seconds:0,marked:[]}:{current_passage:1,checked_question_ids:[]},exam:kind==='listening'?{exam_id:'exam',parts:[{groups:[{questions:ids.map(question_id=>({question_id}))}]}]}:{id:'exam',passages:[{question_groups:[{type:'sentence_completion',questions:ids.map(id=>({id}))}]}]}}};}

// Before changes, basic delayed-sync baseline passed all four 15/40 cases.
// Archived observations are in EXAM_RELIABILITY_AND_NAVIGATION.md.

if(process.argv.includes('--backend')){
 const base=process.env.RELIABILITY_TEST_URL;
 const request=async(path,body)=>{const r=await fetch(base+path,{method:body?'POST':'GET',headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});const d=await r.json();if(!r.ok)throw new ApiError(r.status,d.error?.code||d.code||(d.detail?.length?'request_validation_error':'request_failed'));return d;};
 const results=[];
 for(const kind of ['listening','reading'])for(const count of [15,40]){
  let initial=await request(`/${kind}/attempts`,{event_id:webcrypto.randomUUID(),exam_id:kind==='listening'?'cambridge-14-test-01':'cambridge-18-test-01',reuse_active:false,...(kind==='reading'?{mode:'full_exam'}:{})});
  const path=`/${kind}/attempts/${initial.id}`;initial=await request(path);
  const ids=kind==='listening'?initial.exam.parts.flatMap(p=>p.groups.flatMap(g=>g.questions.map(q=>q.question_id))):initial.exam.passages.flatMap(p=>p.question_groups.flatMap(g=>g.questions.map(q=>q.id)));
  let release,started,first=true;const barrier=new Promise(r=>release=r),start=new Promise(r=>started=r);const store=fakeStore();
  const sync=async e=>{if(first){first=false;started();await barrier;}return request(path+'/sync',e);};
  const transport=async(url,signal,options)=>url.endsWith('/sync')?sync(options.body):request(path+'/submit',options.body);
  let c;if(kind==='listening'){const {ListeningDraft}=loadController('src/features/listening/draft.ts',transport);c=new ListeningDraft(initial,'test-owner',{store,send:transport,get:()=>request(path)});}else{const {ReliableAnswers}=loadController('src/features/reading/exam/reliable-answers.ts',transport);c=new ReliableAnswers(initial,{uid:'test-owner',store,get:()=>request(path),save:sync,submit:e=>request(path+'/submit',e)});}await c.initialize();
  try{
   const change=(id,v)=>kind==='listening'?c.changeAnswer(id,v):c.change({[id]:v});ids.slice(0,5).forEach(id=>change(id,'fixture'));const flight=c.flush();await start;ids.slice(5,count).forEach(id=>change(id,'fixture'));change(ids[0],'café \u2028 \u{1f3a7}');
   if(kind==='listening')c.changeState({displayed_part:2,current_question:11});
   const finishing=kind==='listening'?c.submit():c.finish();change(ids[1],'must-not-change-frozen');setTimeout(release,count===40?5000:1000);const done=await Promise.allSettled([flight,finishing]);
   if(process.argv.includes('--backend-hotfix')){assert.equal((await request(path)).status,'in_progress');assert.equal(kind==='listening'?c.get().submitting:c.snapshot().phase==='finalizing',false);assert.equal(store.record().submit,undefined);assert(store.record().rejectedSubmit);change(ids[0],'café \u2028 \u{1f3a7}');await (kind==='listening'?c.submit():c.finish());}else for(const result of done)if(result.status==='rejected')throw result.reason;
   const server=await request(path),result=await request(path+'/result');assert.equal(server.status,'submitted');assert.equal(Object.values(server.answers).filter(Boolean).length,count);assert.equal(server.answers[ids[0]],'café \u2028 \u{1f3a7}');assert.equal(server.answers[ids[1]],'fixture');const rows=result.questions||result.positions;assert.equal(rows.filter(q=>q.user_answer).length,count);assert.equal(Object.keys(server.answers).length,40);assert.equal(store.record().submit?.answers_checksum||server.answers_checksum,server.answers_checksum);
   results.push({kind,rapid:count,serverRetained:count,resultRetained:count,frozen:true});
  }finally{release();c.dispose();}
 }
 console.log(JSON.stringify({actualControllersAndPostgres:results}));
}

if(process.argv.includes('--unit')){
 const {createHash}=await import('node:crypto');const sum=a=>createHash('sha256').update(JSON.stringify(Object.entries(a).sort()).replace(/[\u007f-\uffff]/g,c=>'\\u'+c.charCodeAt(0).toString(16).padStart(4,'0'))).digest('hex');
 const results=[];
 for(const kind of ['listening','reading'])for(const scenario of ['reload','timeout-replay','timeout-reload','offline','storage-failure','conflict','newer-input','return-to-test','deadline','multi-select-conflict','final-conflict','validation','validation-reload','pending-validation-reload']){
  if(['deadline','multi-select-conflict','final-conflict'].includes(scenario)&&kind!=='reading')continue;
  const {ids,initial}=fixture(kind),store=fakeStore();let server=structuredClone(initial),offline=false,timeout=false,reject=false,unknownReject=false,hold,started;const events=[],replays=new Map();
  const transport=async(path,signal,options)=>{
   if(path==='get')return structuredClone(server);if(offline)throw new ApiError(0,'network_error');const e=structuredClone(options.body);events.push(e);if(replays.has(e.event_id))return structuredClone(replays.get(e.event_id));
   if(hold){started();await hold;hold=undefined;}
   if(path.endsWith('/submit')&&unknownReject)throw new ApiError(0,'timeout');
   if(path.endsWith('/submit')&&reject)throw new ApiError(422,'request_validation_error');
   if(server.status==='expired')return structuredClone(server);
   if(scenario==='final-conflict'&&path.endsWith('/submit')){server.version++;throw new ApiError(409,'reading_version_conflict');}
   if(e.expected_version!==server.version)throw new ApiError(409,kind+'_version_conflict');
   server={...server,version:server.version+1,answers:kind==='listening'?e.answers:{...server.answers,...e.answers},mutation_applied:true};
   if(path.endsWith('/submit'))server={...server,status:'submitted',answers:e.answers,answers_checksum:sum(e.answers),final_snapshot_accepted:true};
   replays.set(e.event_id,structuredClone(server));if(timeout&&path.endsWith('/submit'))throw new ApiError(0,'timeout');return structuredClone(server);
  };
  const make=()=>{if(kind==='listening'){const {ListeningDraft}=loadController('src/features/listening/draft.ts',transport);return new ListeningDraft(structuredClone(server),'A',{store,send:transport,get:()=>transport('get')});}const {ReliableAnswers}=loadController('src/features/reading/exam/reliable-answers.ts',transport);return new ReliableAnswers(structuredClone(server),{uid:'A',store,get:()=>transport('get'),save:e=>transport('/sync',null,{body:e}),submit:e=>transport('/submit',null,{body:e})});};
  if(scenario==='multi-select-conflict'){const g=initial.exam.passages[0].question_groups[0];initial.exam.passages[0].question_groups=[{...g,type:'multiple_choice_multiple',questions:g.questions.slice(0,2)},{...g,questions:g.questions.slice(2)}];server=structuredClone(initial);}
  let c=make();const change=(id,v)=>kind==='listening'?c.changeAnswer(id,v):c.change({[id]:v}),finish=()=>kind==='listening'?c.submit():c.finish();const flush=()=>c.flush().catch(()=>{}),snapshot=()=>kind==='listening'?c.get():c.snapshot();
  try{
   await c.initialize();change(ids[0],'initial');
   if(['validation','validation-reload','pending-validation-reload'].includes(scenario)){reject=true;unknownReject=scenario==='pending-validation-reload';await finish().catch(()=>{});const oldEvent=events.at(-1);unknownReject=false;if(scenario!=='validation'){c.dispose();c=make();await c.initialize();await flush();}assert.equal(server.status,'in_progress');assert.equal(snapshot().submitting||false,false);assert.equal(kind==='reading'?snapshot().phase:'in_progress','in_progress');assert.equal(store.record().submit,undefined);assert.equal(store.record().rejectedSubmit.event_id,oldEvent.event_id);change(ids[0],'corrected');assert.equal(snapshot().answers[ids[0]],'corrected');reject=false;await finish();assert.equal(server.status,'submitted');assert.equal(server.answers[ids[0]],'corrected');assert.notEqual(events.at(-1).event_id,oldEvent.event_id);}
   if(scenario==='reload'){await new Promise(r=>setImmediate(r));c.dispose();c=make();await c.initialize();await flush();assert.equal(server.answers[ids[0]],'initial');}
   if(scenario==='timeout-replay'||scenario==='timeout-reload'){timeout=true;await finish().catch(()=>{});assert(snapshot().submitting||snapshot().phase==='submission_unknown');const event=events.at(-1);timeout=false;if(scenario==='timeout-reload'){c.dispose();c=make();await c.initialize();}await flush();if(kind==='listening'||scenario!=='timeout-reload')assert.deepEqual(events.at(-1),event);assert.equal(server.status,'submitted');assert.equal(server.answers[ids[0]],'initial');}
   if(scenario==='offline'){offline=true;await finish().catch(()=>{});assert.equal(server.status,'in_progress');offline=false;await flush();assert.equal(server.status,'submitted');}
   if(scenario==='storage-failure'){store.fail(true);change(ids[1],'retained');await new Promise(r=>setImmediate(r));await finish().catch(()=>{});assert.equal(server.status,'in_progress');assert.equal(snapshot().answers[ids[1]],'retained');store.fail(false);await c.retryStorage();await finish();assert.equal(server.answers[ids[1]],'retained');}
   if(scenario==='conflict'){server={...server,version:1,answers:{[ids[0]]:'remote',[ids[1]]:'independent'}};await flush();assert(snapshot().conflict||snapshot().conflicts.length);assert.equal(server.answers[ids[0]],'remote');assert.equal(snapshot().answers[ids[0]],'initial');assert.equal(snapshot().answers[ids[1]],'independent');if(kind==='listening')c.resolve(true);else c.resolve({[ids[0]]:'local'});await flush();await finish();assert.equal(server.answers[ids[1]],'independent');}
   if(scenario==='newer-input'){let release;hold=new Promise(r=>release=r);const start=new Promise(r=>started=r);const f=flush();await start;change(ids[0],'latest');change(ids[1],'second');release();await f;await finish();assert.equal(server.answers[ids[0]],'latest');assert.equal(server.answers[ids[1]],'second');}
   if(scenario==='return-to-test'){offline=true;await finish().catch(()=>{});assert(c.canReturnToTest());offline=false;await c.returnToTest();change(ids[1],'second');await finish();assert.equal(server.answers[ids[0]],'initial');assert.equal(server.answers[ids[1]],'second');}
   if(scenario==='final-conflict'){await finish();await new Promise(r=>setTimeout(r,100));assert.equal(events.filter(e=>e.answers_checksum).length,3);assert.equal(server.status,'in_progress');assert.equal(snapshot().phase,'finalizing');}
   if(scenario==='multi-select-conflict'){c.change({[ids[0]]:'A',[ids[1]]:'B'});server={...server,version:1,answers:{[ids[0]]:'A',[ids[1]]:'C'}};await flush();assert.equal(snapshot().conflicts.length,2);assert.equal(snapshot().answers[ids[1]],'B');}
   if(scenario==='deadline'){server={...server,status:'expired',version:1};await flush();assert.equal(snapshot().terminal,true);assert.equal(snapshot().rejected,true);assert.equal(snapshot().answers[ids[0]],'initial');assert(!events.some(e=>e.answers_checksum));}
   results.push({kind,scenario,status:'PASS'});
  }finally{c.dispose();}
 }
 console.log(JSON.stringify({controllerFailureMatrix:results}));
}

if(process.argv.includes('--unit')){
 let calls=0;const {ListeningAssetCache}=loadController('src/features/listening/asset-cache.ts',async()=>{calls++;return new Blob(['private fixture']);});const cache=new ListeningAssetCache('A','attempt','hash'),end=cache.retain(),release=cache.acquire('active');
 await Promise.all([cache.load('active'),cache.load('active')]);assert.equal(calls,1);const url=cache.peek('active');release();await cache.load('active');assert.equal(calls,1);assert.equal(cache.peek('active'),url);
 const pin=cache.acquire('active');for(let n=0;n<60;n++)await cache.load('asset'+n);assert(cache.peek('active'));assert.equal(cache.peek('asset0'),undefined);pin();end();await new Promise(r=>setImmediate(r));assert.equal(cache.peek('active'),undefined);
 console.log(JSON.stringify({privateCache:'concurrent dedup + reuse + pinned LRU + dispose PASS'}));
}
if(process.argv.includes('--unit')){
 const {ids,initial}=fixture('listening'),storage=new Map(),legacy={base:initial,answers:{[ids[0]]:'legacy fixture'},state:initial.state,serial:1,savedSerial:0};const key=`alua:listening:A:${initial.id}:${initial.content_hash}`;storage.set(key,JSON.stringify(legacy));const store=fakeStore();
 const {ListeningDraft}=loadController('src/features/listening/draft.ts',async()=>{throw new ApiError(0,'offline');},storage);const c=new ListeningDraft(initial,'A',{store});try{await c.initialize();assert.equal(c.get().answers[ids[0]],'legacy fixture');assert.equal(store.record().answers[ids[0]],'legacy fixture');assert(storage.has(key));}finally{c.dispose();}
 console.log(JSON.stringify({legacyListening:'copied to IndexedDB adapter, source retained PASS'}));
}
if(process.argv.includes('--unit')){
 const {createApiClient,ApiError:ClientError}=loadController('src/lib/api/client.ts',null,new Map(),{process:{env:{NEXT_PUBLIC_API_BASE_URL:'http://127.0.0.1:1/api/v1'}},fetch:async()=>new Response(JSON.stringify({detail:[{loc:['body','answers'],type:'extra_forbidden',input:'must-not-retain'}]}),{status:422}),Response});
 try{await createApiClient(async()=> 'fixture-only')('/listening/attempts/fixture/submit',undefined,{method:'POST',body:{}});assert.fail('422 must reject');}catch(e){assert(e instanceof ClientError);assert.equal(e.code,'request_validation_error');assert.deepEqual(JSON.parse(JSON.stringify(e.detail)),[{loc:['body','answers'],type:'extra_forbidden'}]);assert(!JSON.stringify(e).includes('must-not-retain'));}
 console.log(JSON.stringify({validationDiagnostics:'loc/type preserved, input discarded PASS'}));
}
