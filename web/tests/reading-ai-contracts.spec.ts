import {test,expect} from '@playwright/test';
import fixture from './fixtures/reading-ai-cases.json';
import {validateReadingReview,type ReadingContext} from '../src/features/reading/ai/contract';
import {readingPrompt,typeInstructions} from '../src/features/reading/ai/prompt';
import {createAI} from '../src/lib/ai/orchestrator';
import {candidates} from '../src/lib/ai/tasks';
const context=fixture.context as ReadingContext;
const output=(raw:unknown)=>({response:JSON.stringify(raw)});
const messages=[{role:'user' as const,content:'Synthetic'}];
test('Reading task is enabled with Groq primary and privacy deny by default',()=>{
 expect(candidates('reading_review',{}).map(c=>c.provider)).toEqual(['groq','cloudflare']);
 expect(candidates('reading_review',{AI_EXTERNAL_TASKS:'reading_review'}).map(c=>c.provider)).toEqual(['groq','cloudflare','gemini','openrouter']);
 expect(candidates('listening_review',{}).map(c=>c.provider)).toEqual(['groq','cloudflare']);
 expect(Object.keys(typeInstructions)).toHaveLength(15);
 for(const type of Object.keys(typeInstructions))expect(readingPrompt(type)).toContain(typeInstructions[type]);
});
for(const patch of [{evidence:[{block_index:99,quote:'Bats use sounds',kind:'support'}]},{evidence:[{block_index:0,quote:'Bats use vision',kind:'support'}]},{evidence:[{block_index:0,quote:'find obstacles',kind:'support'}]},{extra:'invented'},{why_correct_answer_works:'Это подтверждено в абзаце Z.'},{why_user_answer_wrong:'Вы невнимательно читали текст.'},{why_user_answer_wrong:'<script>Русский</script>'}])test(`rejects invalid Reading model output ${JSON.stringify(patch)}`,()=>{expect(()=>validateReadingReview(output({...fixture.raw,...patch}),context)).toThrow();});
test('duplicate exact quote, overlapping ranges and NOT GIVEN false proof rejected',()=>{
 expect(()=>validateReadingReview(output(fixture.raw),{...context,blocks:[{...context.blocks[0]!,text:context.blocks[0]!.text+' '+fixture.context.candidates[0]!.quote}]})).toBeTruthy();
 expect(()=>validateReadingReview(output({...fixture.raw,evidence:[...fixture.raw.evidence,...fixture.raw.evidence]}),context)).toThrow();
 const ng={...context,not_given:true,correct_answer:'NOT GIVEN',grounding:{mode:'concepts',targets:['Bats use sounds']}};
 expect(()=>validateReadingReview(output(fixture.raw),ng)).toThrow();
 expect(validateReadingReview(output({...fixture.raw,evidence:[{...fixture.raw.evidence[0],kind:'relevant_context'}]}),ng)).toBeTruthy();
});
test('bad citation falls back before successful provider acceptance',async()=>{
 const calls:string[]=[];const ai=createAI({log:()=>{},adapters:{groq:async()=>{calls.push('groq');return output({...fixture.raw,evidence:[{...fixture.raw.evidence[0],quote:'fabricated quote'}]});},cloudflare:async()=>{calls.push('cloudflare');return output(fixture.raw);}}});
 expect(await ai.generate({env:{},task:'reading_review',messages,validate:o=>validateReadingReview(o,context)})).toEqual(fixture.raw);
 expect(calls).toEqual(['groq','cloudflare']);
});
test('model abstention advances to next provider',async()=>{
 const calls:string[]=[];const raw={...fixture.raw,evidence_status:'unavailable',evidence:[]};
 const ai=createAI({log:()=>{},adapters:{groq:async()=>{calls.push('groq');return output(raw);},cloudflare:async()=>{calls.push('cloudflare');return output(fixture.raw);}}});
 expect(await ai.generate({env:{},task:'reading_review',messages,validate:o=>validateReadingReview(o,context)})).toEqual(fixture.raw);expect(calls).toEqual(['groq','cloudflare']);
});

// Execute the real handlers with isolated transport bindings, no remote credentials.
import {readFileSync} from 'node:fs';
import ts from 'typescript';
import {ProviderError} from '../src/lib/ai/providers';
import {unavailableReview,readingDiagnostic,readingValidationDetail,allowedReadingCandidates,allowedEvidenceKinds} from '../src/features/reading/ai/contract';
function handler(failures=0,approved=false,raw:unknown=fixture.raw,sourceReason:string|null=null,sourceContext:ReadingContext=context){
 const code=ts.transpileModule(readFileSync('src/app/api/reading/explain/route.ts','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
 const exports:{POST?:(r:Request)=>Promise<Response>}={};let authorized=true,contextCalls=0;const calls:string[]=[],modelMessages:string[]=[];
 const adapter=(name:string,index:number)=>async(_env:unknown,_model:string,input:{messages:{role:string;content:string}[]})=>{modelMessages.push(input.messages.find(m=>m.role==='user')!.content);calls.push(name);if(index<failures)throw new ProviderError(503,true);return output(raw);};
 const ai=createAI({log:()=>{},adapters:{groq:adapter('groq',0),cloudflare:adapter('cloudflare',1),gemini:adapter('gemini',2),openrouter:adapter('openrouter',3)}});
 new Function('require','exports',code)((name:string)=>name.includes('opennextjs')?{getCloudflareContext:async()=>({env:approved?{AI_EXTERNAL_TASKS:'reading_review'}:{}})}:name.includes('/proxy')?{proxyAlua:async()=>{contextCalls++;return Response.json({...sourceContext,unavailable_reason:sourceReason},{status:authorized?200:403});}}:name.includes('/orchestrator')?{ai,ProviderError}:name.includes('/contract')?{validateReadingReview,unavailableReview,readingDiagnostic,readingValidationDetail,allowedReadingCandidates}:name.includes('/prompt')?{readingPrompt}:{},exports);
 const request=(patch={},token='Bearer synthetic.jwt.signature',origin='https://alua.test')=>exports.POST!(new Request('https://alua.test/api/reading/explain',{method:'POST',headers:{Authorization:token,Origin:origin},body:JSON.stringify({attempt_id:'11111111-2222-4333-8444-555555555555',question_id:'q1',...patch})}));
 return {request,calls,modelMessages,contextCalls:()=>contextCalls,deny:()=>{authorized=false;}};
}
test('Reading explain rejects unauthorized/client source injection before any AI call',async()=>{
 const h=handler();expect((await h.request({},'')).status).toBe(401);expect((await h.request({},undefined,'https://evil.test')).status).toBe(403);
 expect((await h.request({correct_answer:'invented'})).status).toBe(400);expect((await h.request({question_id:123})).status).toBe(400);expect(h.contextCalls()).toBe(0);
 h.deny();expect((await h.request()).status).toBe(403);expect(h.calls).toEqual([]);
});
for(const [failures,approved,expected]of [[0,false,['groq']],[1,false,['groq','cloudflare']],[2,true,['groq','cloudflare','gemini']],[3,true,['groq','cloudflare','gemini','openrouter']]] as const)test(`Reading handler fallback ${failures}, approved=${approved}`,async()=>{
 const h=handler(failures,approved),response=await h.request();expect(response.status).toBe(200);expect((await response.json()).fingerprint).toBe(fixture.context.fingerprint);expect(h.calls).toEqual(expected);
});
test('Reading handler all permitted providers fail gracefully',async()=>{const h=handler(4);const response=await h.request();expect(response.status).toBe(200);expect((await response.json()).retryable).toBe(true);expect(h.calls).toEqual(['groq','cloudflare']);});
test('source identity is distinct from semantic correctness; lexical focus is not proof',()=>{
 expect(()=>validateReadingReview(output(fixture.raw),{...context,grounding:{mode:'text',targets:['sounds'],focus:['ears']}})).toBeTruthy();
});

test('all model citation failures become controlled evidence unavailable',async()=>{
 const h=handler(0,false,{...fixture.raw,evidence:[{block_index:0,quote:'fabricated quote',kind:'support'}]});
 const response=await h.request();expect(response.status).toBe(200);expect((await response.json()).review.evidence_status).toBe('unavailable');expect(h.calls).toEqual(['groq','cloudflare']);
});
test('Reading diagnostic exposes only a bounded validation category',async()=>{
 const entries:unknown[]=[];const original=console.info;console.info=(...args)=>{entries.push(args);};
 try {
  const h=handler(0,false,{...fixture.raw,evidence:[{candidate_id:'fabricated-private-marker',kind:'support'}]});
  expect((await h.request()).status).toBe(200);
  expect(JSON.stringify(entries)).toContain('"outcome":"invalid_candidate"');
  expect(JSON.stringify(entries)).not.toContain('fabricated-private-marker');
  expect(JSON.stringify(entries)).not.toContain('fingerprint');
 } finally {console.info=original;}
});

for(const row of JSON.parse(readFileSync('tests/fixtures/reading-ai-parity.json','utf8')))test(`shared Unicode parity: ${row.name}`,()=>{
 const text=row.prefix+(row.unit??'').repeat(row.count??0)+(row.suffix??'');
 const run=()=>validateReadingReview(output({...fixture.raw,why_user_answer_wrong:text}),context);
 if(row.accept)expect(run).not.toThrow();else expect(run).toThrow();
});
test('all model abstentions are controlled and retryable; deterministic context makes no calls',async()=>{
 const h=handler(0,false,{...fixture.raw,evidence_status:'unavailable',evidence:[]});
 const result=await (await h.request()).json();expect(result.retryable).toBe(true);expect(result.review.evidence_status).toBe('unavailable');expect(h.calls).toEqual(['groq','cloudflare']);
 const source=handler(0,false,fixture.raw,'source_integrity');expect((await (await source.request()).json()).retryable).not.toBe(true);expect(source.calls).toEqual([]);
});
test('approved abstentions exhaust four providers and remain retryable without cooldown',async()=>{
 const h=handler(0,true,{...fixture.raw,evidence_status:'unavailable',evidence:[]});
 for(let i=0;i<2;i++)expect((await (await h.request()).json()).retryable).toBe(true);
 expect(h.calls).toEqual(['groq','cloudflare','gemini','openrouter','groq','cloudflare','gemini','openrouter']);
});

for(const [answer,kinds] of [['FALSE',['contradiction']],['NO',['contradiction']],['TRUE',['support']],['YES',['support']],['NOT GIVEN',['relevant_context']]] as const)test(`trusted evidence kinds: ${answer}`,()=>{
 const ctx={...context,correct_answer:answer,not_given:answer==='NOT GIVEN'};
 expect(allowedEvidenceKinds(ctx)).toEqual(kinds);
 for(const kind of ['support','contradiction','relevant_context','invented']) {
  const run=()=>validateReadingReview(output({...fixture.raw,evidence:[{...fixture.raw.evidence[0],kind}]}),ctx);
  if((kinds as readonly string[]).includes(kind))expect(run).not.toThrow();else expect(run).toThrow('kind');
 }
});
test('wrong kind falls back without silently changing the model evidence',async()=>{
 const calls:string[]=[];const ctx={...context,correct_answer:'FALSE',not_given:false};
 const valid={...fixture.raw,evidence:[{...fixture.raw.evidence[0],kind:'contradiction'}]};
 const ai=createAI({log:()=>{},adapters:{groq:async()=>{calls.push('groq');return output(fixture.raw);},cloudflare:async()=>{calls.push('cloudflare');return output(valid);}}});
 expect(await ai.generate({env:{},task:'reading_review',messages,validate:o=>validateReadingReview(o,ctx)})).toEqual(valid);
 expect(calls).toEqual(['groq','cloudflare']);expect(fixture.raw.evidence[0]!.kind).toBe('support');
});

test('paragraph models receive only source-owned candidates from the saved target',async()=>{
 const ctx={...context,grounding:{mode:'paragraph',targets:['B']},blocks:[...context.blocks,{...context.blocks[0]!,label:'C'}],candidates:[...context.candidates,{...context.candidates[0]!,id:'other-source-owned',block_index:1}]};
 const h=handler(0,false,fixture.raw,null,ctx);
 expect((await h.request()).status).toBe(200);
 const data=JSON.parse(h.modelMessages[0]!.split('\n').slice(1).join('\n'));
 expect(data.candidates.map((c:{id:string})=>c.id)).toEqual(context.candidates.map(c=>c.id));
 expect(ctx.candidates).toHaveLength(2);
});

test('candidate diagnostics distinguish source identity, allowed set, overlap and prose references without content',()=>{
 const c=context.candidates[0]!;
 const cases:[unknown,ReadingContext,string][]=[
  [{...fixture.raw,evidence:[{candidate_id:'private-marker',kind:'support'}]},context,'unknown_candidate_id'],
  [fixture.raw,{...context,grounding:{mode:'paragraph',targets:['Z']}},'candidate_outside_allowed_set'],
  [{...fixture.raw,evidence:[...fixture.raw.evidence,...fixture.raw.evidence]},context,'duplicate_or_overlap'],
  [fixture.raw,{...context,candidates:[{...c,end:c.end+1}]},'source_quote_mismatch'],
  [{...fixture.raw,why_correct_answer_works:'Сравните с абзаце Z.'},context,'prose_reference'],
 ];
 for(const [raw,ctx,detail]of cases){
  try{validateReadingReview(output(raw),ctx);throw Error('unexpected acceptance');}catch(error){expect(readingValidationDetail(error)).toBe(detail);expect(readingDiagnostic(error)).toBe('invalid_candidate');expect(readingValidationDetail(error)).not.toContain('private-marker');}
 }
 expect(readingValidationDetail(Error('secret-marker'))).toBe('other');
});

test('matching explanations cannot cite an uncited paragraph even when the candidate ID is valid',()=>{
 for(const type of ['matching_information','matching_headings']) {
  const ctx={...context,question_type:type,grounding:{mode:type==='matching_information'?'paragraph':'heading',targets:['B']}};
  const bad={...fixture.raw,why_user_answer_wrong:'В абзаце A описан другой факт.'};
  expect(()=>validateReadingReview(output(bad),ctx)).toThrow('prose_reference');
  const safe={...bad,why_user_answer_wrong:'Выбранный абзац описывает другой факт. Сравните нужную связь с цитатой.'};
  expect(()=>validateReadingReview(output(safe),ctx)).not.toThrow();
  expect(readingPrompt(type)).toContain('Не называй букву ошибочно выбранного пользователем');
 }
});
