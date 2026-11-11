import {test, expect} from '@playwright/test';
import {createAI, type Telemetry} from '../src/lib/ai/orchestrator';
import {type Adapter, type AIEnv, type Provider, ProviderError, retryAfter, timed, chatOutput} from '../src/lib/ai/adapters/common';
import {groqAdapter} from '../src/lib/ai/adapters/groq';
import {cloudflareAdapter} from '../src/lib/ai/adapters/cloudflare';
import {geminiAdapter} from '../src/lib/ai/adapters/gemini';
import {openrouterAdapter} from '../src/lib/ai/adapters/openrouter';
import {models, candidates} from '../src/lib/ai/tasks';
import {modelJSON, reviewJSON, groq, fallback} from '../src/lib/ai/providers';
import {validateReview} from '../src/lib/ai/review';
import {validateTranslation, parseTranslationOutput} from '../src/features/reading/translate/context';
const order: Provider[] = ['groq','cloudflare','gemini','openrouter'];
const messages = [{role: 'user' as const, content: 'Synthetic fixture'}];
const env: AIEnv = {GROQ_API_KEY: 'fixture', GEMINI_API_KEY: 'fixture', OPENROUTER_API_KEY: 'fixture', AI_EXTERNAL_TASKS: 'smart_translate,listening_review', AI: {run: async () => ({response: '{}'})}};
const good = {response: '{"ok":true}'};
function harness(failures: Partial<Record<Provider, unknown>> = {}) {
  const calls: Provider[] = [], events: Telemetry[] = []; let clock = 0;
  const adapters = Object.fromEntries(order.map(provider => [provider, async () => {
    calls.push(provider); if (failures[provider]) throw failures[provider]; return good;
  }])) as unknown as Record<Provider, Adapter>;
  const ai = createAI({adapters, log: e => events.push(e), now: () => clock});
  return {ai, calls, events, adapters, advance: (ms: number) => {clock += ms;},
    generate: (policy = env) => ai.generate({env: policy, task: 'smart_translate', messages, validate: modelJSON})};
}
for (let count = 0; count <= 4; count++) test(`sequential fallback: ${count} unavailable providers`, async () => {
  const h = harness(Object.fromEntries(order.slice(0,count).map(p => [p,new ProviderError(503,true)])));
  if (count === 4) await expect(h.generate()).rejects.toMatchObject({status:503,reason:'all_providers_unavailable'});
  else expect(await h.generate()).toEqual({ok:true});
  expect(h.calls).toEqual(order.slice(0, Math.min(4,count+1)));
});
for (const status of [408,429,500,502,503,504,404,410,401,403]) test(`provider HTTP ${status} advances without user auth error`, async () => {
  const h = harness({groq:new ProviderError(status,true)}); expect(await h.generate()).toEqual({ok:true});
  expect(h.calls).toEqual(['groq','cloudflare']);
});
test('network failure advances', async () => {const h=harness({groq:new TypeError('network')}); await h.generate(); expect(h.calls).toEqual(['groq','cloudflare']);});
for (const invalid of [{response:'not JSON'},{response:'{}'},{response:''}]) test(`invalid JSON/schema/output advances: ${invalid.response}`,async()=>{
  const h=harness(); h.adapters.groq=async()=>invalid;
  const value=await h.ai.generate({env,task:'smart_translate',messages,validate:o=>{
    const parsed=modelJSON(o) as {ok?:boolean}; if(parsed.ok!==true)throw Error(); return parsed;
  }});expect(value).toEqual({ok:true});expect(h.calls).toEqual(['cloudflare']);
});
test('translation semantic failure advances and preserves exact selected occurrence',async()=>{
  const input={sentence:'We used to travel; now we are used to staying.',selected:'used',start:29,end:33};
  const h=harness();h.adapters.groq=async()=>({response:'{"expression":"used to travel","translation":"раньше"}'});
  h.adapters.cloudflare=async()=>({response:'{"expression":"are used to","translation":"привыкли"}'});
  const value=await h.ai.generate({env,task:'smart_translate',messages,validate:o=>validateTranslation(parseTranslationOutput(o),input)});
  expect(value).toEqual({expression:'are used to',translation:'привыкли'});
});
test('deadline exhausted: no new attempt and no late success',async()=>{
  const h=harness();h.adapters.groq=async()=>{h.calls.push('groq');h.advance(15_001);throw new ProviderError(504,true);};
  await expect(h.generate()).rejects.toMatchObject({status:504});expect(h.calls).toEqual(['groq']);
  h.adapters.groq=async()=>{h.calls.push('groq');h.advance(15_001);return good;};
  h.advance(3000);await expect(h.generate()).rejects.toMatchObject({status:504});
});
test('actual timeout aborts adapter signal',async()=>{
  let aborted=false;
  await expect(timed(signal=>new Promise(()=>{signal.addEventListener('abort',()=>{aborted=true;});}),5)).rejects.toMatchObject({status:504});
  expect(aborted).toBe(true);
});
test('cooldown skips rate-limited model and expires according to Retry-After',async()=>{
  const h=harness({groq:new ProviderError(429,true,'http_429',60_000)});
  await h.generate();await h.generate();expect(h.calls).toEqual(['groq','cloudflare','cloudflare']);
  h.advance(60_001);await h.generate();expect(h.calls.slice(-2)).toEqual(['groq','cloudflare']);
  expect(h.events.some(e=>e.fallback_reason==='cooldown')).toBe(true);
});
test('Retry-After bounded seconds/date and malformed values',()=>{
  expect(retryAfter('60')).toBe(60_000);expect(retryAfter('99999999999')).toBe(300_000);
  expect(retryAfter('invalid')).toBe(0);expect(retryAfter('-1')).toBe(0);
  const now=Date.parse('2026-11-10T00:00:00Z');expect(retryAfter('Tue, 10 Nov 2026 00:00:05 GMT',now)).toBe(5000);
});
for(const missing of ['GEMINI_API_KEY','OPENROUTER_API_KEY'] as const)test(`Listening works without ${missing}`,async()=>{
  const h=harness();expect(await h.ai.generate({env:{...env,[missing]:undefined},task:'listening_review',messages,validate:modelJSON})).toEqual({ok:true});expect(h.calls).toEqual(['groq']);
});
test('privacy deny by default, per-task approval and independent kill switches',()=>{
  expect(candidates('listening_review',{...env,AI_EXTERNAL_TASKS:undefined}).map(c=>c.provider)).toEqual(order.slice(0,2));
  expect(candidates('listening_review',{...env,AI_EXTERNAL_TASKS:'smart_translate'}).map(c=>c.provider)).toEqual(order.slice(0,2));
  expect(candidates('smart_translate',{...env,AI_GEMINI_ENABLED:'false',AI_OPENROUTER_ENABLED:'false'}).map(c=>c.provider)).toEqual(order.slice(0,2));
  expect(candidates('speaking_assessment',env)).toEqual([]);
  expect(candidates('writing_assessment',env).map(c=>c.provider)).toEqual(order.slice(0,2));
});
test('reserved routes and oversized input never invoke providers',async()=>{
  const h=harness();await expect(h.ai.generate({env,task:'speaking_assessment',messages,validate:modelJSON})).rejects.toMatchObject({reason:'invalid_task_input'});
  await expect(h.ai.generate({env,task:'smart_translate',messages:[{role:'user',content:'x'.repeat(96_001)}],validate:modelJSON})).rejects.toMatchObject({reason:'invalid_task_input'});expect(h.calls).toEqual([]);
});
const review={what_happened:'Названа другая сумма.',why:'Ответ отличается от ключа.',next_time:'Сравните число.',segment_ids:['seg-0001'],quote:'Forty pounds.'};
const context={duration:12,segments:[{id:'seg-0001',start:1,end:2,text:'Forty pounds.'},{id:'seg-0002',start:3,end:4,text:'For students.'}]};
test('Listening schema, exact quote, contiguous IDs and trusted duration',()=>{
  expect(validateReview({response:JSON.stringify(review)},context)).toEqual(review);
  for(const patch of [{segment_ids:['seg-9999']},{segment_ids:['seg-0001','seg-0001']},{segment_ids:['seg-0002','seg-0001']},{quote:'Invented'},{clip_start:1},{why:'English only'},{segment_ids:[],quote:'invented'}])
    expect(()=>validateReview({response:JSON.stringify({...review,...patch})},context)).toThrow();
  expect(()=>validateReview({response:JSON.stringify(review)},{...context,duration:1})).toThrow();
  expect(reviewJSON({response:JSON.stringify({...review,segment_ids:[],quote:''})})).toBeTruthy();
});
test('Listening invalid evidence triggers provider fallback',async()=>{
  const h=harness();h.adapters.groq=async()=>({response:JSON.stringify({...review,quote:'invented'})});
  h.adapters.cloudflare=async()=>({response:JSON.stringify(review)});
  expect(await h.ai.generate({env,task:'listening_review',messages,validate:o=>validateReview(o,context)})).toEqual(review);
});
// Test HTTP adapter contracts without keys, quota consumption or external network.
const input={messages:[{role:'system' as const,content:'Fixture rules'},...messages],temperature:0,maxTokens:160};
function mockFetch(handler: (url:string,body:Record<string,unknown>,init:RequestInit)=>Response|Promise<Response>){
  const original=globalThis.fetch;
  globalThis.fetch=async(url,init={})=>handler(String(url),init.body?JSON.parse(init.body as string):{},init);
  return ()=>{globalThis.fetch=original;};
}
test('Groq and Gemini only send their supported parameters and normalize final text',async()=>{
  const restore=mockFetch((url,body,init)=>{
    expect(init.redirect).toBe('manual');expect(body.chat_template_kwargs).toBeUndefined();
    if(url.includes('groq.com')){expect(body.model).toBe(models.groq);expect(body.reasoning_effort).toBe('low');expect(body.include_reasoning).toBe(false);return Response.json({choices:[{message:{content:'{}',reasoning:'private'}}]});}
    expect(url).toBe('https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent');
    expect(body.reasoning_effort).toBeUndefined();expect(body.include_reasoning).toBeUndefined();expect(body.response_format).toBeUndefined();
    expect(body.generationConfig).toEqual({temperature:0,maxOutputTokens:160,responseMimeType:'application/json'});
    expect(body.systemInstruction).toEqual({parts:[{text:'Fixture rules'}]});
    expect((init.headers as Record<string,string>)['x-goog-api-key']).toBe('fixture');
    return Response.json({candidates:[{finishReason:'STOP',content:{parts:[{text:'private',thought:true},{text:'{}'}]}}]});
  });
  try{for(const [adapter,model]of [[groqAdapter,models.groq],[geminiAdapter,models.gemini]] as const)expect(await adapter(env,model,input,new AbortController().signal)).toEqual({response:'{}'});}finally{restore();}
});
test('native Cloudflare binding receives signal and documented JSON format',async()=>{
  const signal=new AbortController().signal;
  expect(await cloudflareAdapter({AI:{run:async(model,body,options)=>{
    expect(model).toBe(models.cloudflare);expect(options?.signal).toBe(signal);expect(body.response_format).toEqual({type:'json_object'});
    expect(body.reasoning_effort).toBeUndefined();expect(body.max_completion_tokens).toBe(160);
    return {choices:[{message:{content:'{}'}}]};
  }}},models.cloudflare,input,signal)).toEqual({response:'{}'});
});
test('local Wrangler binding does not serialize AbortSignal',async()=>{
  const previous=process.env.ALUA_LOCAL_STACK;process.env.ALUA_LOCAL_STACK='true';
  try {
    expect(await cloudflareAdapter({AI:{run:async(_model,_body,options)=>{
      expect(options).toBeUndefined();return {response:'{}'};
    }}},models.cloudflare,input,new AbortController().signal)).toEqual({response:'{}'});
  } finally {
    if(previous===undefined)delete process.env.ALUA_LOCAL_STACK;else process.env.ALUA_LOCAL_STACK=previous;
  }
});
test('OpenRouter denies paid IDs before network and verifies free catalog eligibility',async()=>{
  let requests=0;const restore=mockFetch((url,body)=>{
    requests++;
    if(url.endsWith('/models'))return Response.json({data:[{id:'fixture/safe:free',pricing:{prompt:'0',completion:'0'},supported_parameters:['response_format'],architecture:{output_modalities:['text']}}]});
    expect(body.model).toBe('fixture/safe:free');expect(body.models).toBeUndefined();expect(body.route).toBeUndefined();
    expect(body.reasoning_effort).toBeUndefined();expect(body.include_reasoning).toBeUndefined();
    expect(body.provider).toEqual({require_parameters:true,data_collection:'deny',max_price:{prompt:0,completion:0}});
    return Response.json({choices:[{message:{content:'{}'}}]});
  });
  try{
    await expect(openrouterAdapter(env,'paid/model',input,new AbortController().signal)).rejects.toMatchObject({reason:'free_model_unavailable'});expect(requests).toBe(0);
    expect(await openrouterAdapter(env,'fixture/safe:free',input,new AbortController().signal)).toEqual({response:'{}'});expect(requests).toBe(2);
    await expect(openrouterAdapter(env,'fixture/missing:free',input,new AbortController().signal)).rejects.toMatchObject({reason:'free_model_unavailable'});expect(requests).toBe(3);
  }finally{restore();}
});
for(const catalog of [{pricing:{prompt:'0.01',completion:'0'}},{supported_parameters:[]},{pricing:{prompt:'0',completion:'0',request:'1'}}])test(`OpenRouter fail closed: ${JSON.stringify(catalog)}`,async()=>{
  let posts=0;const restore=mockFetch((url)=>{if(!url.endsWith('/models'))posts++;return Response.json({data:[{id:'fixture/rejected:free',pricing:{prompt:'0',completion:'0'},supported_parameters:['response_format'],architecture:{output_modalities:['text']},...catalog}]});});
  try{await expect(openrouterAdapter(env,'fixture/rejected:free',input,new AbortController().signal)).rejects.toMatchObject({reason:'free_model_unavailable'});expect(posts).toBe(0);}finally{restore();}
});
test('real adapter missing keys fail over; telemetry is metadata only',async()=>{
  const events:Telemetry[]=[];const ai=createAI({log:e=>events.push(e)});
  expect(await ai.generate({env:{AI:env.AI},task:'listening_review',messages,validate:modelJSON})).toEqual({});
  expect(events[0]?.fallback_reason).toBe('configuration_failure');
  for(const e of events){const {http_status,request_id,...base}=e;expect(Object.keys(base).sort()).toEqual(['fallback_reason','latency_ms','model','outcome','provider','task']);if(http_status!==undefined)expect(Number.isInteger(http_status)&&http_status>=100&&http_status<=599).toBe(true);if(request_id!==undefined)expect(request_id).toMatch(/^[A-Za-z0-9:_-]{1,160}$/);}
  expect(JSON.stringify(events)).not.toContain('Synthetic fixture');
});

test('normalizes documented text blocks without accepting mixed content',()=>{
  expect(chatOutput({choices:[{message:{content:[{type:'text',text:'{'},{type:'output_text',text:'}'}]}}]})).toEqual({response:'{}'});
  expect(()=>chatOutput({response:[{type:'reasoning',text:'private'}]})).toThrow();
});

test('compatibility helpers preserve fallback on network failures',async()=>{
  let calls=0;
  const output=await fallback(()=>groq({GROQ_API_KEY:'fixture'},{},100,async()=>{throw new TypeError('synthetic network failure');}),async()=>{calls++;return good;});
  expect(output).toEqual(good);expect(calls).toBe(1);
});

test('caller budget can shorten a task but cannot extend its deadline',async()=>{
 let now=0;const calls:string[]=[];
 const ai=createAI({now:()=>now,log:()=>{},adapters:{groq:async()=>{calls.push('groq');now+=450;throw new ProviderError(503,true)},cloudflare:async()=>{calls.push('cloudflare');return {response:'{}'}}}});
 await expect(ai.generate({env:{},task:'smart_translate',messages,validate:modelJSON,deadlineMs:500})).rejects.toBeTruthy();expect(calls).toEqual(['groq']);
 now=0;calls.length=0;await expect(ai.generate({env:{},task:'smart_translate',messages,validate:modelJSON,deadlineMs:100})).rejects.toBeTruthy();expect(calls).toEqual([]);
 const capped=createAI({now:()=>now,log:()=>{},adapters:{groq:async()=>{now=15001;throw new ProviderError(503,true)},cloudflare:async()=>{throw Error('late provider')}}});now=0;await expect(capped.generate({env:{},task:'smart_translate',messages,validate:modelJSON,deadlineMs:99999})).rejects.toMatchObject({status:504});
});

// Writing keeps shared routing/privacy gates and fails closed on invented evidence.
import {validateReview as writingReview,evidenceCandidates,wordCount} from '../src/features/writing/contract';
const writingEssay='😀 Adults need practical literacy support. Governments should fund evening classes.';
function writingFixture(){const anchor=evidenceCandidates(writingEssay)[0]!;return {criteria:['task_response','coherence_cohesion','lexical_resource','grammar'].map(name=>({name,band:6,rationale_en:'Relevant but limited development.',explanation_ru:'Нужно развить аргумент.',evidence:[anchor],improvement:'Develop a workplace example.'})),top_improvements:[1,2,3].map(n=>({action:`Develop specific point ${n}.`,quote:anchor.quote})),issues:[{...anchor,category:'style_suggestion',why:'Add specificity.',better:'Adults need accessible literacy support.',explanation_ru:'Уточните доступность.',corrected_translation_ru:'Взрослым нужна доступная помощь в освоении грамотности.'}],uncertainty:'This short synthetic sample is not a live assessment.'};}
test('Writing strict schema, evidence, offsets, missing criteria and untrusted total',()=>{
 expect(wordCount("Don't re-write children’s work.")).toBe(4);expect(writingReview(writingFixture(),writingEssay).criteria).toHaveLength(4);
 const mutations:((r:ReturnType<typeof writingFixture>)=>void)[]=[r=>{r.criteria.pop()},r=>{r.criteria[0]!.band=6.3},r=>{r.criteria[0]!.evidence=[]},r=>{r.issues[0]!.start++},r=>{r.issues[0]!.quote='Fabricated sentence.'},r=>{Object.assign(r,{estimated_band:9})}];
 for(const mutate of mutations){const r=writingFixture();mutate(r);expect(()=>writingReview(r,writingEssay)).toThrow();}
});
test('Writing invalid evidence falls back; metadata belongs to successful adapter',async()=>{
 const events:Telemetry[]=[];let metadata:Telemetry|undefined;
 const engine=createAI({adapters:{groq:async()=>({response:{...writingFixture(),issues:[{...writingFixture().issues[0],start:99}]}}),cloudflare:async()=>({response:writingFixture()})},log:e=>events.push(e)});
 const result=await engine.generate({env:{},task:'writing_assessment',messages,validate:o=>writingReview(o,writingEssay),onSuccess:e=>{metadata=e}});
 expect(result.criteria).toHaveLength(4);expect(metadata?.provider).toBe('cloudflare');expect(events.map(e=>e.outcome)).toEqual(['failure','success']);
});
test('Writing timeout and full fallback failure return explicit unavailable',async()=>{
 const engine=createAI({adapters:{groq:async()=>{throw new ProviderError(504,true,'timeout')},cloudflare:async()=>{throw new ProviderError(503,true)}},log:()=>{}});
 await expect(engine.generate({env:{},task:'writing_assessment',messages,validate:o=>writingReview(o,writingEssay)})).rejects.toMatchObject({status:504});
});
import {validateModelReview as writingModelReview} from '../src/features/writing/contract';
test('Writing source-owned IDs resolve only exact quotes; guessed offsets and invented quotes fail',()=>{
 const source=writingFixture();const raw={...source,criteria:source.criteria.map(c=>({...c,evidence:c.evidence.map(()=>({candidate_id:'s0'}))})),issues:source.issues.map(i=>{const {start,end,quote,...fields}=i;void start;void end;void quote;return {...fields,candidate_id:'s0'}})};
 const wire={...raw,top_improvements:raw.top_improvements.map(i=>({action:i.action,candidate_id:'s0'}))};
 expect(writingModelReview({response:JSON.stringify(wire)},writingEssay)).toEqual(source);
 for(const patch of [{quote:'Never written here.'},{candidate_id:'s999'},{start:0}]){const bad=structuredClone(wire);Object.assign(bad.criteria[0]!.evidence[0]!,patch);expect(()=>writingModelReview(bad,writingEssay)).toThrow();}
});
test('Writing rejects generic complexity advice and unsupported certainty',()=>{
 for(const action of ['Use more advanced vocabulary.','Incorporate even more sophisticated collocations.','Utilize more advanced academic collocations to replace standard phrasing in the introduction.']){const r=writingFixture();r.criteria[2]!.improvement=action;expect(()=>writingReview(r,writingEssay)).toThrow('generic_complexity_advice');}
 const r=writingFixture();r.uncertainty='None.';expect(()=>writingReview(r,writingEssay)).toThrow('unsupported_certainty');
});

import {readFileSync} from 'node:fs';
import ts from 'typescript';
import * as writingFailures from '../src/features/writing/failure';

test('terminal provider 429 and cooldown retain status and trustworthy Retry-After',async()=>{
 let calls=0;const engine=createAI({adapters:{groq:async()=>{throw new ProviderError(503,false,'configuration_failure')},cloudflare:async()=>{calls++;throw new ProviderError(429,true,'http_429',20_000,'safe-request-123')}},log:()=>{}});
 for(let i=0;i<2;i++)await expect(engine.generate({env:{},task:'writing_assessment',messages,validate:modelJSON})).rejects.toMatchObject({status:429,reason:'provider_rate_limited'});
 expect(calls).toBe(1);
 const unknown=createAI({adapters:{groq:async()=>{throw new ProviderError(429,true)},cloudflare:async()=>{throw new ProviderError(503,false,'configuration_failure')}},log:()=>{}});
 await expect(unknown.generate({env:{},task:'writing_assessment',messages,validate:modelJSON})).rejects.toMatchObject({status:429,retryAfterMs:0});
});
test('HTTP adapters preserve provider request ID and Retry-After without body logging',async()=>{
 const response=Response.json({error:'not logged'},{status:429,headers:{'Retry-After':'17','X-Request-ID':'provider-abc'}});
 await expect(groqAdapter({GROQ_API_KEY:'test'},models.groq,{messages,maxTokens:100,temperature:0},new AbortController().signal,async()=>response)).rejects.toMatchObject({status:429,retryAfterMs:17000,requestId:'provider-abc'});
 await expect(groqAdapter({GROQ_API_KEY:'test'},models.groq,{messages,maxTokens:100,temperature:0},new AbortController().signal,async()=>Response.json({}, {status:429,headers:{'Retry-After':'1200'}}))).rejects.toMatchObject({retryAfterMs:1200000});
 await expect(cloudflareAdapter({AI:{run:async()=>{throw {status:429,headers:{'retry-after':'12','cf-ray':'ray-123'}}}}},models.cloudflare,{messages,maxTokens:100,temperature:0},new AbortController().signal)).rejects.toMatchObject({status:429,retryAfterMs:12000,requestId:'ray-123'});
});
function writingRouteHarness(){
 let mode='success',claims=0,generations=0,environment=0,completed=0;
 const attempt={id:'11111111-2222-4333-8444-555555555555',status:'submitted',version:1,essay:writingEssay,task:{id:'writing-t2-000004'},assessment:null as unknown};
 const code=ts.transpileModule(readFileSync('src/app/api/writing/assess/route.ts','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
 const exports:{POST?:(r:Request)=>Promise<Response>}={};
 new Function('require','exports',code)((name:string)=>{
  if(name==='@opennextjs/cloudflare')return {getCloudflareContext:async()=>{environment++;if(mode==='environment')throw Error('synthetic setup error');return {env:{AI:{run:async()=>{throw Error('No real AI permitted')}}}}}};
  if(name.endsWith('/tasks'))return {candidates:()=>[{provider:'cloudflare'}]};
  if(name.endsWith('/proxy'))return {proxyAlua:async()=>mode==='ownership'?Response.json({error:{code:'not_found'}},{status:404}):Response.json(attempt)};
  if(name.endsWith('/bridge'))return {bridge:async(_auth:string,_id:string,action:string)=>{if(action==='claim'){claims++;if(mode==='limit')return Response.json({error:{code:'writing_rate_limited',retryable:true}},{status:429,headers:{'Retry-After':'31'}});if(mode==='legacy-limit')return Response.json({error:{code:'ai_rate_limit'}},{status:429});return Response.json({cached:false,lease:'lease',essay:writingEssay,task:attempt.task,failure_protocol:1});}completed++;return Response.json({...attempt,assessment:mode==='success'?{estimated_band:6}:null});}};
  if(name.endsWith('/orchestrator'))return {ProviderError,ai:{generate:async(options:{onAttempt?:(p:Provider)=>void;onSuccess?:(e:{provider:string;model:string})=>void})=>{generations++;options.onAttempt?.('cloudflare');if(mode==='invalid')throw new ProviderError(502,true,'invalid_output');if(mode==='provider-limit')throw new ProviderError(429,true,'http_429',15000);if(mode==='unavailable')throw new ProviderError(503,true,'all_providers_unavailable');options.onSuccess?.({provider:'cloudflare',model:'mock'});return writingFixture();}}};
  if(name.endsWith('/prompt'))return {writingPrompt:'Fixture only'};
  return {validateModelReview:writingModelReview,evidenceCandidates};
 },exports);
 return {mode:(v:string)=>{mode=v},cached:()=>{attempt.assessment={estimated_band:6}},request:()=>exports.POST!(new Request('http://localhost/api/writing/assess',{method:'POST',headers:{Authorization:'Bearer fixture'},body:JSON.stringify({attempt_id:attempt.id})})),counts:()=>({claims,generations,environment,completed})};
}
test('Writing authenticates ownership, checks cache and preflights environment before claiming quota',async()=>{
 const own=writingRouteHarness();own.mode('ownership');expect((await own.request()).status).toBe(404);expect(own.counts()).toEqual({claims:0,generations:0,environment:0,completed:0});
 const env=writingRouteHarness();env.mode('environment');const failed=await env.request();expect(failed.status).toBe(503);expect((await failed.json()).error.kind).toBe('configuration_error');expect(env.counts().claims).toBe(0);
 const cached=writingRouteHarness();cached.cached();expect((await cached.request()).status).toBe(200);expect(cached.counts()).toEqual({claims:0,generations:0,environment:0,completed:0});
});
test('Writing preserves application/provider limits, invalid-output and unavailable error classes',async()=>{
 for(const [mode,status,kind,source,wait] of [['limit',429,'rate_limited','application','31'],['legacy-limit',429,'rate_limited','application',null],['provider-limit',429,'rate_limited','provider','15'],['invalid',502,'invalid_response','provider',null],['unavailable',503,'provider_unavailable','provider',null]] as const){const h=writingRouteHarness();h.mode(mode);const response=await h.request();expect(response.status).toBe(status);expect(response.headers.get('retry-after')).toBe(wait);expect(response.headers.get('x-request-id')).toBeTruthy();const body=await response.json();expect(body.error).toMatchObject({kind,source});if(mode==='legacy-limit')expect(body.error.retryable).toBe(false);expect(h.counts().generations).toBe(mode.includes('limit')&&!mode.startsWith('provider')?0:1);}
});
test('Writing error parser never invents a retry time or exposes raw codes as UI copy',()=>{
 const missing=writingFailures.responseFailure(429,{error:{code:'ai_rate_limit'}},new Headers(),1000);expect(missing.failure.retryAt).toBeUndefined();
 const known=writingFailures.responseFailure(429,{error:{code:'provider_rate_limited',source:'provider',retryable:true}},new Headers({'Retry-After':'15'}),1000);expect(known.failure).toMatchObject({kind:'rate_limited',source:'provider',retryAt:16000});
});
test('Writing client coalesces two concurrent submissions into a single HTTP request',async()=>{
 const code=ts.transpileModule(readFileSync('src/features/writing/api.ts','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
 const exports:{assess?:(uid:string,id:string)=>Promise<unknown>}={};
 new Function('require','exports',code)((name:string)=>name.includes('/firebase/')?{getIdToken:async()=> 'fixture'}:name.endsWith('/client')?{createApiClient:()=>{},ApiError:class extends Error{}}:writingFailures,exports);
 const original=globalThis.fetch;let calls=0,resolve:(v:Response)=>void=()=>{};
 globalThis.fetch=async()=>{calls++;return new Promise<Response>(done=>{resolve=done})};
 try{const first=exports.assess!('owner','attempt'),second=exports.assess!('owner','attempt');expect(first).toBe(second);await Promise.resolve();resolve(Response.json({id:'attempt'}));await first;expect(calls).toBe(1);}finally{globalThis.fetch=original;}
});
