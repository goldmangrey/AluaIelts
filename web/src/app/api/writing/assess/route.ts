import {getCloudflareContext} from '@opennextjs/cloudflare';
import {ai,ProviderError} from '@/lib/ai/orchestrator';
import {candidates} from '@/lib/ai/tasks';
import type {AIEnv} from '@/lib/ai/adapters/common';
import {proxyAlua} from '@/lib/api/proxy';
import {bridge} from '@/features/writing/bridge';
import {validateModelReview,evidenceCandidates,type Task,type Attempt} from '@/features/writing/contract';
import {writingPrompt} from '@/features/writing/prompt';
export const runtime='nodejs';export const dynamic='force-dynamic';
const privateHeaders={'Cache-Control':'private, no-store',Vary:'Authorization','X-Content-Type-Options':'nosniff'};
export async function POST(request:Request){
 const requestId=crypto.randomUUID(),headers={...privateHeaders,'X-Request-ID':requestId};
 const fail=(status:number,code:string,kind='provider_unavailable',source='application',retryable=true,retryAfterMs=0,providerRequestId?:string)=>{
  const wait=Number.isFinite(retryAfterMs)&&retryAfterMs>0?Math.ceil(retryAfterMs/1000):0;
  return Response.json({error:{code,kind,source,retryable}},{status,headers:{...headers,...(wait?{'Retry-After':String(wait)}:{}),...(providerRequestId&&/^[A-Za-z0-9:_-]{1,160}$/.test(providerRequestId)?{'X-Provider-Request-ID':providerRequestId}:{})}});
 };
 const authorization=request.headers.get('authorization')??'';
 if(!/^Bearer \S{1,8192}$/.test(authorization))return fail(401,'unauthorized');
 const origin=request.headers.get('origin'),url=new URL(request.url);url.host=request.headers.get('host')??url.host;
 if(origin&&origin!==url.origin)return fail(403,'forbidden');
 let id:string;
 try{
  const reader=request.body?.getReader();if(!reader)throw Error();let body='',size=0;
  try{while(true){const v=await reader.read();if(v.done)break;size+=v.value.byteLength;if(size>200)throw Error();body+=new TextDecoder().decode(v.value);}}finally{void reader.cancel();}
  const value=JSON.parse(body);if(Object.keys(value).join()!=='attempt_id'||!/^[-a-f0-9]{36}$/i.test(value.attempt_id))throw Error();id=value.attempt_id;
 }catch{return fail(400,'invalid_request');}
 let phase='ownership',lease:string|undefined,failureProtocol=false,providerCalls=0;
 const upstreamFailure=async(response:Response)=>{
  let code='writing_upstream_unavailable',retryable=true;
  try{const body=await response.json();if(typeof body?.error?.code==='string'&&/^[A-Za-z0-9_]{1,64}$/.test(body.error.code))code=body.error.code;if(typeof body?.error?.retryable==='boolean')retryable=body.error.retryable;}catch{}
  // Legacy backend uses one code for hourly and permanent attempt caps. No reliable retry time.
  if(response.status===429&&code==='ai_rate_limit')retryable=false;
  const raw=response.headers.get('retry-after'),seconds=raw&&/^\d+$/.test(raw)?Number(raw):0;
  console.info('[writing-ai]',{request_id:requestId,stage:phase,outcome:'blocked',http_status:response.status,code,provider_calls:providerCalls});
  return fail(response.status,code,response.status===429?'rate_limited':code==='assessment_pending'?'pending':'provider_unavailable','application',retryable,seconds>0&&seconds<=86400?seconds*1000:0);
 };
 try{
  // Ownership and cached results precede environment work; no quota is claimed for a setup error.
  const own=await proxyAlua(new Request(request.url,{headers:{authorization},signal:request.signal}),['writing','attempts',id],undefined,8000);
  if(!own.ok)return await upstreamFailure(own);
  const attempt=await own.json() as Attempt;
  if(attempt.assessment)return Response.json(attempt,{headers});
  if(attempt.status!=='submitted')return fail(409,'writing_not_submitted');
  phase='environment';
  const env=(await getCloudflareContext({async:true})).env as AIEnv;
  const available=candidates('writing_assessment',env).some(c=>c.provider==='cloudflare'?!!env.AI:!!env[c.provider==='groq'?'GROQ_API_KEY':c.provider==='gemini'?'GEMINI_API_KEY':'OPENROUTER_API_KEY']?.trim());
  if(!available)throw new ProviderError(503,false,'configuration_failure');
  phase='claim';const claimed=await bridge(authorization,id,'claim');if(!claimed.ok)return await upstreamFailure(claimed);
  const context=await claimed.json() as {cached:boolean;attempt?:Attempt;lease:string;essay:string;task:Task;failure_protocol?:number};
  if(context.cached)return Response.json(context.attempt,{headers});lease=context.lease;failureProtocol=context.failure_protocol===1;
  phase='inference';let metadata={provider:'',model:''};
  const review=await ai.generate({env,task:'writing_assessment',messages:[{role:'system',content:writingPrompt},{role:'user',content:JSON.stringify({task:context.task,essay:context.essay,evidence_candidates:evidenceCandidates(context.essay).map((anchor,i)=>({candidate_id:`s${i}`,quote:anchor.quote}))})}],validate:o=>validateModelReview(o,context.essay),onSuccess:e=>{metadata={provider:e.provider,model:e.model};},onAttempt:()=>{providerCalls++;}});
  phase='persistence';const saved=await bridge(authorization,id,'complete',{lease,review,...metadata});if(!saved.ok)return await upstreamFailure(saved);
  console.info('[writing-ai]',{request_id:requestId,stage:phase,outcome:'saved',provider_calls:providerCalls,...metadata});
  return Response.json(await saved.json(),{headers});
 }catch(error){
  const providerError=error instanceof ProviderError?error:undefined;
  const invalid=providerError&&['invalid_output','invalid_model_json','invalid_translation','invalid_json','empty_output','output_too_large'].includes(providerError.reason);
  const kind=phase==='environment'?'configuration_error':invalid?'invalid_response':providerError?.status===429?'rate_limited':phase==='ownership'||phase==='claim'||phase==='persistence'?'transport_error':'provider_unavailable';
  const source=phase==='environment'?'environment':kind==='transport_error'?'transport':'provider';
  const code=kind==='rate_limited'?'writing_provider_rate_limited':kind==='invalid_response'?'writing_invalid_response':kind==='configuration_error'?'writing_configuration_unavailable':kind==='transport_error'?'writing_transport_error':'writing_provider_unavailable';
  if(lease&&phase!=='persistence')try{await bridge(authorization,id,'complete',{lease,...(failureProtocol?{failure_kind:kind}:{})});}catch{}
  console.info('[writing-ai]',{request_id:requestId,stage:phase,outcome:'failed',code,provider_calls:providerCalls,...(phase==='environment'?{environment_diagnostic:providerError?.reason??(/module|import|require/i.test(String((error as Error)?.message))?'module_resolution':/closed|disposed/i.test(String((error as Error)?.message))?'closed_context':'context_initialization')}:{ }),...(providerError?{provider_reason:providerError.reason,provider_request_id:providerError.requestId}: {})});
  return fail(kind==='rate_limited'?429:kind==='invalid_response'?502:503,code,kind,source,phase!=='persistence',providerError?.retryAfterMs,providerError?.requestId);
 }
}
