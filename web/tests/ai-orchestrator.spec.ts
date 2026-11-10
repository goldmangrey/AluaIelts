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
  await expect(h.generate()).rejects.toMatchObject({status:503});expect(h.calls).toEqual(['groq']);
  h.adapters.groq=async()=>{h.calls.push('groq');h.advance(15_001);return good;};
  h.advance(3000);await expect(h.generate()).rejects.toMatchObject({status:503});
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
  for(const task of ['writing_assessment','speaking_assessment'] as const)expect(candidates(task,env)).toEqual([]);
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
  for(const e of events)expect(Object.keys(e).sort()).toEqual(['fallback_reason','latency_ms','model','outcome','provider','task']);
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
