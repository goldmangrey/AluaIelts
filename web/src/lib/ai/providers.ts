/** Server-only provider routing. Never return/log provider envelopes or reasoning. */
export interface AIEnv { GROQ_API_KEY?:string; AI?:{run(model:string,input:Record<string,unknown>):Promise<unknown>} }
export class ProviderError extends Error {
  constructor(public status:number,public retryable=false){super('AI provider request failed');}
}
const transient=(status:number)=>status===408||status===429||[500,502,503,504].includes(status);
async function deadline<T>(work:Promise<T>,ms:number):Promise<T>{
  let timer:ReturnType<typeof setTimeout>|undefined;
  try{return await Promise.race([work,new Promise<never>((_,reject)=>{timer=setTimeout(()=>reject(new ProviderError(504,true)),ms);})]);}
  finally{clearTimeout(timer);}
}
export async function cloudflare(env:AIEnv,model:string,input:Record<string,unknown>,ms=18_000){
  if(!env.AI||typeof env.AI.run!=='function')throw new ProviderError(503); // Missing binding is configuration, never a failover trigger.
  try{return await deadline(env.AI.run(model,input),ms);}
  catch(error){
    if(error instanceof ProviderError)throw error;
    const e=error as {status?:number;statusCode?:number;message?:string;name?:string};
    if(e.name==='TimeoutError'||e.name==='AbortError')throw new ProviderError(504,true);
    if(error instanceof TypeError)throw new ProviderError(503,true);
    // Workers AI binding errors may expose only the HTTP code in their message.
    // Extract the status only; never log/persist the message or payload.
    // https://developers.cloudflare.com/workers-ai/platform/errors/
    const internal:Record<number,number>={3036:429,3040:429,3007:408,3008:408,5018:403,5016:403,3023:403,3041:403,5035:403,5007:400,5004:400,3003:400,3042:404};
    const status=Number(e.status??e.statusCode??0);
    const known=Number(/\b(3036|3040|3007|3008|5018|5016|3023|3041|5035|5007|5004|3003|3042)\b/.exec(e.message||'')?.[1]??0);
    const code=status>=100&&status<=599?status:internal[status]??internal[known]??Number(/\b(400|401|403|404|408|422|429|500|502|503|504)\b/.exec(e.message||'')?.[1]??0);
    throw new ProviderError(code||502,transient(code));
  }
}
export async function groq(env:AIEnv,input:Record<string,unknown>,ms=18_000,fetcher:typeof fetch=fetch){
  if(!env.GROQ_API_KEY?.trim())throw new ProviderError(503); // Do not hide a missing/invalid secret.
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),ms);
  const {chat_template_kwargs:_template,max_tokens:_tokens,...groqInput}=input;void _template;void _tokens;
  try{
    const response=await fetcher('https://api.groq.com/openai/v1/chat/completions',{method:'POST',headers:{Authorization:`Bearer ${env.GROQ_API_KEY}`,'Content-Type':'application/json'},body:JSON.stringify({...groqInput,model:'openai/gpt-oss-120b',reasoning_effort:'low',include_reasoning:false,stream:false,max_completion_tokens:Math.max(Number(input.max_completion_tokens)||1600,1200)}),signal:controller.signal,redirect:'manual'});
    if(!response.ok){await response.body?.cancel();throw new ProviderError(response.status,transient(response.status));}
    // Bound the response before parsing; discard all fields except final message content.
    const reader=response.body?.getReader();if(!reader)throw new ProviderError(502);
    let raw='',size=0;const decoder=new TextDecoder();
    try{while(true){const {done,value}=await reader.read();if(done)break;size+=value.length;if(size>64_000)throw new ProviderError(502);raw+=decoder.decode(value,{stream:true});}}finally{await reader.cancel();}
    const data=JSON.parse(raw),content=data?.choices?.[0]?.message?.content;
    if(typeof content!=='string')throw new ProviderError(502);
    return {response:content};
  }catch(error){
    if(error instanceof ProviderError)throw error;
    if(controller.signal.aborted)throw new ProviderError(504,true);
    if(error instanceof TypeError)throw new ProviderError(503,true); // network transport failure
    throw new ProviderError(502); // Invalid data is not a provider outage.
  }finally{clearTimeout(timer);}
}
export async function fallback<T>(primary:()=>Promise<T>,secondary:()=>Promise<T>):Promise<T>{
  try{return await primary();}catch(error){if(!(error instanceof ProviderError)||!error.retryable)throw error;return secondary();}
}
export async function listeningInference(env:AIEnv,input:Record<string,unknown>){return fallback(()=>groq(env,input),()=>cloudflare(env,'@cf/qwen/qwen3-30b-a3b-fp8',{messages:input.messages,temperature:input.temperature,response_format:input.response_format,max_tokens:1800,stream:false}));}
export async function readingInference(env:AIEnv,input:Record<string,unknown>){return fallback(()=>cloudflare(env,'@cf/google/gemma-4-26b-a4b-it',input),()=>groq(env,input));}
export function modelJSON(output:unknown):unknown{
  if(!output||typeof output!=='object')throw new ProviderError(502);
  const o=output as {response?:unknown;choices?:{message?:{content?:unknown}}[]};
  const content=o.choices?.[0]?.message?.content??o.response;
  if(content&&typeof content==='object'&&!Array.isArray(content))return content;
  if(typeof content!=='string'||content.length>12_000)throw new ProviderError(502);
  const text=content.trim(),fence=/^```(?:json)?\s*([\s\S]*?)\s*```$/.exec(text);
  try{return JSON.parse(fence?fence[1]!:text);}catch{throw new ProviderError(502);}
}

export function reviewJSON(output:unknown){
 const parsed=modelJSON(output);
 if(!parsed||typeof parsed!=='object'||Array.isArray(parsed))throw new ProviderError(502);
 const p=parsed as Record<string,unknown>;
 if(Object.keys(p).sort().join(',')!=='next_time,quote,segment_ids,what_happened,why'||!['what_happened','why','next_time','quote'].every(k=>typeof p[k]==='string'&&(p[k] as string).length<=1800)||!Array.isArray(p.segment_ids)||p.segment_ids.length>5||!p.segment_ids.every(id=>typeof id==='string'&&/^seg-\d{4}$/.test(id)))throw new ProviderError(502);
 if(!['what_happened','why','next_time'].every(k=>/[А-Яа-яЁё]/.test(p[k] as string)))throw new ProviderError(502);
 return p;
}
