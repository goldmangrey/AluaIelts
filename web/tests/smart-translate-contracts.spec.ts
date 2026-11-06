import {readingInference,listeningInference,groq,cloudflare,fallback,ProviderError,modelJSON,reviewJSON,type AIEnv} from "../src/lib/ai/providers";
import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import ts from "typescript";
import { selectionContext, validInput, validateTranslation, canTranslateAttempt, parseTranslationOutput } from "../src/features/reading/translate/context";

const examples = [
  ["She is looking forward to studying abroad.", "forward", "looking forward to", "с нетерпением ждать"],
  ["I used to walk to school.", "used", "used to", "раньше ходил"],
  ["I am used to walking to school.", "used", "am used to", "привык ходить"],
  ["We take into account every detail.", "account", "take into account", "учитывать"],
  ["As a result of rain, we stayed home.", "result", "As a result of", "в результате"],
  ["The evidence is compelling.", "evidence", "evidence", "доказательства"],
];
for (const [sentence, selected, expression, translation] of examples as [string,string,string,string][]) {
  test(`validates exact contextual expression: ${expression}`, () => {
    const start = sentence.indexOf(selected);
    const input = selectionContext(sentence, start, start + selected.length)!;
    expect(validInput(input)).toBe(true);
    expect(validateTranslation({ expression, translation }, input)).toEqual({ expression, translation });
    expect(validateTranslation({ expression: "invented " + expression, translation }, input)).toBeNull();
  });
}
test("bounds context, rejects partial words, wrong occurrence and malformed output", () => {
  const text = "word ".repeat(500) + "evidence " + "word ".repeat(500);
  const start = text.indexOf("evidence");
  expect(selectionContext(text, start, start + 8)!.sentence.length).toBeLessThanOrEqual(600);
  expect(selectionContext("evidence", 1, 5)).toBeNull();
  const sentence = "We used to travel; now we are used to staying.";
  const selectedStart = sentence.lastIndexOf("used");
  const input = selectionContext(sentence, selectedStart, selectedStart + 4)!;
  expect(validateTranslation({ expression: "used to travel", translation: "раньше ездили" }, input)).toBeNull();
  expect(validateTranslation({ expression: "used to", translation: "x".repeat(300) }, input)).toBeNull();
});

function routeHarness() {
  let calls = 0, mode = "passage_practice", authenticated = true;
  let response = { expression: "looking forward to", translation: "с нетерпением ждать" };
  const input = selectionContext(examples[0]![0]!, 15, 22)!;
  const code = ts.transpileModule(readFileSync("src/app/api/translate/route.ts", "utf8"), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
  const exports: { POST?: (r: Request) => Promise<Response> } = {};
  const proxy = async (_r: Request, segments: string[]) => {
    if (!authenticated) return Response.json({}, { status: 401 });
    return Response.json(segments[0] === "me" ? { uid: "verified-learner" } : segments[1] === "books" ? { items: [{ exams: [{ exam_id: "cambridge-04-test-01", practice_policy_version: "private-practice-v1", enabled_for_private_practice: true, content_status: "needs_review" }] }] } : { mode, exam_id: "cambridge-04-test-01", exam: { passages: [{ id: "p1", content: [{ text: examples[0]![0] }] }] } });
  };
  const run = async (_model: string, args: Record<string, unknown>) => {
    calls++; expect(args.chat_template_kwargs).toEqual({ enable_thinking: false });
    expect(args.max_completion_tokens).toBe(160);
    return { choices: [{ message: { content: JSON.stringify(response) } }] };
  };
  new Function("require", "exports", code)((name: string) => name.includes("providers") ? {readingInference} : name.includes("cloudflare") ? { getCloudflareContext: () => ({ env: { AI: { run } } }) } : name.includes("proxy") ? { proxyAlua: proxy } : { validInput, validateTranslation, canTranslateAttempt, parseTranslationOutput }, exports);
  const request = (patch = {}, token = "Bearer valid.firebase.signature") => exports.POST!(new Request("https://alua.test/api/translate", {
    method: "POST", headers: { Authorization: token }, body: JSON.stringify({ ...input, attemptId: "11111111-2222-4333-8444-555555555555", passageId: "p1", block: 0, ...patch }),
  }));
  return { request, calls: () => calls, mode: (v: string) => mode = v, auth: (v: boolean) => authenticated = v, output: (v: typeof response) => response = v };
}
test("server requires verified Firebase identity, practice ownership/context and validates AI", async () => {
  const h = routeHarness();
  expect((await h.request({}, "Bearer alua_dev_fake")).status).toBe(401);
  h.auth(false); expect((await h.request()).status).toBe(401); expect(h.calls()).toBe(0);
  h.auth(true); h.mode("official_exam"); expect((await h.request({ mode: "full_exam", translationAllowed: true })).status).toBe(403); expect(h.calls()).toBe(0);
  h.mode("full_exam"); expect((await h.request()).status).toBe(200);
  h.mode("passage_practice"); expect((await h.request({ sentence: "fabricated", selected: "fabricated", start: 0, end: 10 })).status).toBe(400);
  h.output({ expression: "look forward to", translation: "ждать" }); expect((await h.request()).status).toBe(502);
  h.output({ expression: "looking forward to", translation: "с нетерпением ждать" });
  const result = await h.request(); expect(result.status).toBe(200); expect(result.headers.get("cache-control")).toContain("no-store");
  expect(await result.json()).toEqual({ expression: "looking forward to", translation: "с нетерпением ждать" });
});
test("server limits requests and body size before AI", async () => {
  const h = routeHarness();
  expect((await h.request({ sentence: "x".repeat(5000) })).status).toBe(413);
  for (let i = 0; i < 12; i++) expect((await h.request()).status).toBe(200);
  expect((await h.request()).status).toBe(429); expect(h.calls()).toBe(12);
});

test("translation allows existing Start test mode only under the known private server policy", () => {
  const attempt = { mode: "full_exam", exam_id: "cambridge-04-test-01" };
  const entry = { exam_id: attempt.exam_id, practice_policy_version: "private-practice-v1", enabled_for_private_practice: true, content_status: "needs_review" };
  const catalog = (e: unknown) => ({ items: [{ exams: [e] }] });
  expect(canTranslateAttempt(attempt, catalog(entry))).toBe(true);
  expect(canTranslateAttempt({ ...attempt, mode: "passage_practice" }, catalog(entry))).toBe(true);
  for (const mode of ["official_exam", "restricted", "future", null]) expect(canTranslateAttempt({ ...attempt, mode }, catalog(entry))).toBe(false);
  for (const patch of [{ practice_policy_version: "official-v1" }, { practice_policy_version: undefined }, { enabled_for_private_practice: false }, { content_status: "blocked" }, { exam_id: "other" }]) expect(canTranslateAttempt(attempt, catalog({ ...entry, ...patch }))).toBe(false);
  expect(canTranslateAttempt(attempt, null)).toBe(false);
});

test("binding output formats retain strict verbatim quote and offset validation", () => {
  const sentence = "She is looking forward to studying abroad.";
  const input = { sentence, selected: "forward", start: 15, end: 22 };
  const result = { expression: "looking forward to", translation: "с нетерпением ждать" };
  const json = JSON.stringify(result);
  for (const output of [{ choices: [{ message: { content: json } }] }, { response: "```json\n" + json + "\n```" }, { response: result }, { choices: [{ message: { content: [{ type: "text", text: json }] } }] }]) expect(validateTranslation(parseTranslationOutput(output), input)).toEqual(result);
  expect(parseTranslationOutput({ response: "Explanation " + json })).toBeNull();
  expect(validateTranslation(parseTranslationOutput({ response: JSON.stringify({ ...result, expression: "look forward to" }) }), input)).toBeNull();
  expect(validInput({ ...input, end: 999 })).toBe(false);
  const multiline = "She is looking\nforward to studying abroad.";
  const start = multiline.indexOf("forward");
  expect(selectionContext(multiline, start, start + 7)?.sentence).toBe(multiline);
});


test("Listening Groq primary, transient Qwen fallback, Reading routing and non-fallback errors",async()=>{
 const original=globalThis.fetch;const input={messages:[{role:'user',content:'Trusted test context'}],response_format:{type:'json_object'},max_completion_tokens:160};
 let status=200,cloudStatus=200;const calls:string[]=[];
 const env:AIEnv={GROQ_API_KEY:'test-only-secret',AI:{run:async(model,body)=>{calls.push(model);if(cloudStatus!==200)throw {status:cloudStatus};expect(body.messages).toEqual(input.messages);return {response:'{"expression":"context","translation":"контекст"}'};}}};
 globalThis.fetch=async(url,options)=>{calls.push(String(url));const payload=JSON.parse(options!.body as string);expect(payload.model).toBe('openai/gpt-oss-120b');expect(payload.include_reasoning).toBe(false);expect(payload.chat_template_kwargs).toBeUndefined();return status===200?Response.json({choices:[{message:{content:'{"expression":"context","translation":"контекст"}',reasoning:'never exposed'}}]}):Response.json({error:{message:'private provider details'}},{status});};
 try{
  expect(modelJSON(await listeningInference(env,input))).toEqual({expression:'context',translation:'контекст'});expect(calls).toHaveLength(1);
  calls.length=0;status=429;await listeningInference(env,input);expect(calls[1]).toBe('@cf/qwen/qwen3-30b-a3b-fp8');
  for(const code of [500,502,503,504]){calls.length=0;status=code;await listeningInference(env,input);expect(calls).toHaveLength(2);}
  for(const code of [400,401,403,404,422]){calls.length=0;status=code;await expect(listeningInference(env,input)).rejects.toBeInstanceOf(ProviderError);expect(calls).toHaveLength(1);}
  calls.length=0;await expect(listeningInference({...env,GROQ_API_KEY:undefined},input)).rejects.toBeInstanceOf(ProviderError);expect(calls).toHaveLength(0);
  status=200;calls.length=0;await readingInference(env,input);expect(calls).toEqual(['@cf/google/gemma-4-26b-a4b-it']);
  cloudStatus=503;calls.length=0;const result=await readingInference(env,input);expect(modelJSON(result)).toEqual({expression:'context',translation:'контекст'});expect(calls).toHaveLength(2);
  cloudStatus=403;calls.length=0;await expect(readingInference(env,input)).rejects.toBeInstanceOf(ProviderError);expect(calls).toHaveLength(1);
  await expect(readingInference({GROQ_API_KEY:'test-only'},input)).rejects.toBeInstanceOf(ProviderError);
  expect(JSON.stringify(result)).not.toContain('never exposed');
 }finally{globalThis.fetch=original;}
});

test("Groq uses Workers-compatible manual redirects and rejects redirect responses",async()=>{
 let fallbackCalls=0;
 const fetcher:typeof fetch=async(_url,options)=>{
  expect(options?.redirect).toBe('manual');
  return new Response(null,{status:302,headers:{Location:'https://example.invalid/redirect'}});
 };
 await expect(fallback(()=>groq({GROQ_API_KEY:'test-only'},{},100,fetcher),async()=>{fallbackCalls++;return {response:'{}'};})).rejects.toMatchObject({status:302,retryable:false});
 expect(fallbackCalls).toBe(0);
});

test("Provider deadlines are bounded and malformed data never causes failover",async()=>{
 const env:AIEnv={GROQ_API_KEY:'test-only',AI:{run:async()=>({response:'{}'})}};
 let fallbackCalls=0;
 const stalled:typeof fetch=async(_url,options)=>new Promise((_,reject)=>{options!.signal!.addEventListener('abort',()=>reject(new DOMException('Aborted','AbortError')));});
 await fallback(()=>groq(env,{},5,stalled),async()=>{fallbackCalls++;return {response:'{}'};});expect(fallbackCalls).toBe(1);
 await expect(cloudflare({AI:{run:()=>new Promise(()=>{})}},'test',{},5)).rejects.toMatchObject({status:504,retryable:true});
 await expect(fallback(()=>groq(env,{},10,async()=>Response.json({choices:[]})),async()=>{fallbackCalls++;return {response:'{}'};})).rejects.toMatchObject({retryable:false});
 expect(fallbackCalls).toBe(1);
 expect(()=>modelJSON({response:'<think>private reasoning</think>{}'})).toThrow();
});


test("Listening Worker accepts only owned completed server context and ignores client-supplied answers",async()=>{
 const code=ts.transpileModule(readFileSync('src/app/api/listening/explain/route.ts','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
 const exports:{POST?:(r:Request)=>Promise<Response>}={};let owned=true,calls=0,status=200;
 const ai={what_happened:'В аудио названа другая сумма.',why:'Ответ не совпадает с ключом.',next_time:'Слушайте число внимательно.',segment_ids:['seg-0001'],quote:'Forty pounds.'};
 const original=globalThis.fetch;
 globalThis.fetch=async()=>{calls++;return status===200?Response.json({choices:[{message:{content:JSON.stringify(ai),reasoning:'secret internal'}}]}):Response.json({}, {status});};
 const context={learner_id:'real-owner',fingerprint:'server-hash',part:1,book:4,test:1,unavailable_reason:null,user_answer:'wrong',correct_answer:'forty',segments:[{id:'seg-0001',start:1,end:2,text:'Forty pounds.'}]};
 new Function('require','exports',code)((name:string)=>name.includes('cloudflare')?{getCloudflareContext:()=>({env:{GROQ_API_KEY:'test-only',AI:{run:async()=>{calls++;return {response:JSON.stringify(ai)};}}}})}:name.includes('proxy')?{proxyAlua:async(_r:Request,segments:string[])=>{expect(segments.slice(-3)).toEqual(['ai-review','2','context']);return Response.json(context,{status:owned?200:403});}}:{listeningInference,reviewJSON},exports);
 const request=(patch={},auth='Bearer trusted.jwt.token')=>exports.POST!(new Request('https://alua.test/api/listening/explain',{method:'POST',headers:{Authorization:auth},body:JSON.stringify({attempt_id:'11111111-2222-4333-8444-555555555555',question_number:2,...patch})}));
 try{
  expect((await request({},'')).status).toBe(401);
  expect((await request({correct_answer:'fabricated'})).status).toBe(400);
  owned=false;expect((await request()).status).toBe(403);expect(calls).toBe(0);
  owned=true;expect(await (await request()).json()).toEqual({review:ai,fingerprint:'server-hash'});expect(calls).toBe(1);
  status=429;expect((await request()).status).toBe(200);expect(calls).toBe(3);
  status=401;expect((await request()).status).toBe(503);expect(calls).toBe(4);
 }finally{globalThis.fetch=original;}
});


test("Cloudflare documented internal quota/timeouts fail over but access/data errors do not",async()=>{
 for(const code of [3036,3040,3007,3008])await expect(cloudflare({AI:{run:async()=>{throw Error(`AI_ERROR: ${code}: provider error`);}}},'test',{})).rejects.toMatchObject({retryable:true});
 for(const code of [5018,5016,3023,3041,5035,5007,5004,3003,3042])await expect(cloudflare({AI:{run:async()=>{throw Error(`AI_ERROR: ${code}: provider error`);}}},'test',{})).rejects.toMatchObject({retryable:false});
});


test("Listening public review entry bounds input and forwards only IDs to protected backend",async()=>{
 const code=ts.transpileModule(readFileSync('src/app/api/listening/review/route.ts','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
 const exports:{POST?:(r:Request)=>Promise<Response>}={};let calls=0;
 new Function('require','exports',code)(()=>({proxyAlua:async(request:Request,segments:string[],_configured:unknown,timeout:number)=>{calls++;expect(request.method).toBe('POST');expect(segments.slice(-2)).toEqual(['ai-review','2']);expect(timeout).toBe(55000);return Response.json({ok:true});}}),exports);
 const request=(patch={},token='Bearer fixture.jwt.signature',origin='https://alua.test')=>exports.POST!(new Request('https://alua.test/api/listening/review',{method:'POST',headers:{Authorization:token,Origin:origin},body:JSON.stringify({attempt_id:'11111111-2222-4333-8444-555555555555',question_number:2,...patch})}));
 expect((await request({},'')).status).toBe(401);expect((await request({},undefined,'https://untrusted.test')).status).toBe(403);expect((await request({transcript:'injected'})).status).toBe(400);expect(calls).toBe(0);
 expect((await request()).status).toBe(200);expect(calls).toBe(1);
});
