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
 expect(()=>validateReadingReview(output(fixture.raw),{...context,blocks:[{...context.blocks[0]!,text:context.blocks[0]!.text+' '+fixture.raw.evidence[0]!.quote}]})).toThrow();
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
test('valid evidence unavailable does not cause needless second provider call',async()=>{
 const calls:string[]=[];const raw={...fixture.raw,evidence_status:'unavailable',evidence:[]};
 const ai=createAI({log:()=>{},adapters:{groq:async()=>{calls.push('groq');return output(raw);},cloudflare:async()=>{throw Error('unnecessary');}}});
 expect(await ai.generate({env:{},task:'reading_review',messages,validate:o=>validateReadingReview(o,context)})).toEqual(raw);expect(calls).toEqual(['groq']);
});

// Execute the real handlers with isolated transport bindings, no remote credentials.
import {readFileSync} from 'node:fs';
import ts from 'typescript';
import {ProviderError} from '../src/lib/ai/providers';
import {unavailableReview} from '../src/features/reading/ai/contract';
function handler(failures=0,approved=false,raw:unknown=fixture.raw){
 const code=ts.transpileModule(readFileSync('src/app/api/reading/explain/route.ts','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
 const exports:{POST?:(r:Request)=>Promise<Response>}={};let authorized=true,contextCalls=0;const calls:string[]=[];
 const adapter=(name:string,index:number)=>async()=>{calls.push(name);if(index<failures)throw new ProviderError(503,true);return output(raw);};
 const ai=createAI({log:()=>{},adapters:{groq:adapter('groq',0),cloudflare:adapter('cloudflare',1),gemini:adapter('gemini',2),openrouter:adapter('openrouter',3)}});
 new Function('require','exports',code)((name:string)=>name.includes('opennextjs')?{getCloudflareContext:async()=>({env:approved?{AI_EXTERNAL_TASKS:'reading_review'}:{}})}:name.includes('/proxy')?{proxyAlua:async()=>{contextCalls++;return Response.json(fixture.context,{status:authorized?200:403});}}:name.includes('/orchestrator')?{ai,ProviderError}:name.includes('/contract')?{validateReadingReview,unavailableReview}:name.includes('/prompt')?{readingPrompt}:{},exports);
 const request=(patch={},token='Bearer synthetic.jwt.signature',origin='https://alua.test')=>exports.POST!(new Request('https://alua.test/api/reading/explain',{method:'POST',headers:{Authorization:token,Origin:origin},body:JSON.stringify({attempt_id:'11111111-2222-4333-8444-555555555555',question_id:'q1',...patch})}));
 return {request,calls,contextCalls:()=>contextCalls,deny:()=>{authorized=false;}};
}
test('Reading explain rejects unauthorized/client source injection before any AI call',async()=>{
 const h=handler();expect((await h.request({},'')).status).toBe(401);expect((await h.request({},undefined,'https://evil.test')).status).toBe(403);
 expect((await h.request({correct_answer:'invented'})).status).toBe(400);expect((await h.request({question_id:123})).status).toBe(400);expect(h.contextCalls()).toBe(0);
 h.deny();expect((await h.request()).status).toBe(403);expect(h.calls).toEqual([]);
});
for(const [failures,approved,expected]of [[0,false,['groq']],[1,false,['groq','cloudflare']],[2,true,['groq','cloudflare','gemini']],[3,true,['groq','cloudflare','gemini','openrouter']]] as const)test(`Reading handler fallback ${failures}, approved=${approved}`,async()=>{
 const h=handler(failures,approved),response=await h.request();expect(response.status).toBe(200);expect((await response.json()).fingerprint).toBe(fixture.context.fingerprint);expect(h.calls).toEqual(expected);
});
test('Reading handler all permitted providers fail gracefully',async()=>{const h=handler(4);const response=await h.request();expect(response.status).toBe(503);expect(await response.json()).toEqual({error:{code:'reading_ai_unavailable'}});expect(h.calls).toEqual(['groq','cloudflare']);});
test('text answer in unrelated context is not grounded just because it matches the key',()=>{
 expect(()=>validateReadingReview(output(fixture.raw),{...context,grounding:{mode:'text',targets:['sounds'],focus:['ears']}})).toThrow();
});

test('all model citation failures become controlled evidence unavailable',async()=>{
 const h=handler(0,false,{...fixture.raw,evidence:[{block_index:0,quote:'fabricated quote',kind:'support'}]});
 const response=await h.request();expect(response.status).toBe(200);expect((await response.json()).review.evidence_status).toBe('unavailable');expect(h.calls).toEqual(['groq','cloudflare']);
});
