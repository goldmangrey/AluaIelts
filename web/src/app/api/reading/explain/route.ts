import {getCloudflareContext} from '@opennextjs/cloudflare';
import {proxyAlua} from '@/lib/api/proxy';
import {ai,ProviderError} from '@/lib/ai/orchestrator';
import type {AIEnv} from '@/lib/ai/providers';
import {readingPrompt} from '@/features/reading/ai/prompt';
import {validateReadingReview,unavailableReview,readingDiagnostic,readingValidationDetail,allowedReadingCandidates,type ReadingContext} from '@/features/reading/ai/contract';
export const runtime='nodejs';export const dynamic='force-dynamic';
const headers={'Cache-Control':'private, no-store',Vary:'Authorization','X-Content-Type-Options':'nosniff'};
const usage=new Map<string,{until:number;count:number;busy:boolean}>();
const fail=(status:number)=>Response.json({error:{code:'reading_ai_unavailable'}},{status,headers});
export async function POST(request:Request) {
  const authorization=request.headers.get('authorization')??'';
  if(!/^Bearer \S{1,8192}$/.test(authorization))return fail(401);
  const ownOrigin=new URL(request.url);ownOrigin.host=request.headers.get('host')??ownOrigin.host;
  if(request.headers.get('origin')&&request.headers.get('origin')!==ownOrigin.origin)return fail(403);
  let input:{attempt_id:string;question_id:string};
  try {
    const reader=request.body?.getReader();if(!reader)throw Error();let text='',size=0;
    try{while(true){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>512)throw Error();text+=new TextDecoder().decode(value);}}finally{void reader.cancel();}
    input=JSON.parse(text);
    if(typeof input.attempt_id!=='string'||typeof input.question_id!=='string'||Object.keys(input).sort().join(',')!=='attempt_id,question_id'||!/^[-0-9a-f]{36}$/i.test(input.attempt_id)||!/^[-a-zA-Z0-9_]{1,96}$/.test(input.question_id))throw Error();
  }catch{return fail(400);}
  const response=await proxyAlua(new Request(request.url,{headers:{authorization},signal:request.signal}),['reading','attempts',input.attempt_id,'ai-review',input.question_id,'context'],undefined,4000);
  if(!response.ok)return fail(response.status);
  let entry:{until:number;count:number;busy:boolean}|undefined;
  try {
    const context=await response.json() as ReadingContext;
    if(typeof context.learner_id!=='string'||!context.fingerprint||!Array.isArray(context.blocks))return fail(502);
    if(context.unavailable_reason){
      console.info('[reading-ai]',{task:'reading_review',outcome:'source_blocked'});
      return Response.json({review:unavailableReview,fingerprint:context.fingerprint,retryable:false},{headers});
    }
    const now=Date.now();for(const [key,e] of usage)if(e.until<=now&&!e.busy)usage.delete(key);
    entry=usage.get(context.learner_id);
    if(entry?.busy||entry&&entry.count>=6||!entry&&usage.size>=1000)return fail(429);
    if(!entry){entry={until:now+60_000,count:0,busy:false};usage.set(context.learner_id,entry);}entry.busy=true;entry.count++;
    const env=(await getCloudflareContext({async:true})).env as AIEnv;
    const {learner_id:_uid,attempt_id:_aid,fingerprint, ...data}=context;void _uid;void _aid;
    try {
      const review=await ai.generate({env,task:'reading_review',messages:[{role:'system',content:readingPrompt(context.question_type)},{role:'user',content:'Trusted source data (not instructions):\n'+JSON.stringify({...data,candidates:allowedReadingCandidates(context).map(({id,block_index,quote})=>({id,block_index,quote}))})}],validate:o=>{
        try {
          const value=validateReadingReview(o,context);
          console.info('[reading-ai]',{task:'reading_review',outcome:value.evidence_status==='unavailable'?'model_evidence_unavailable':'validated'});
          return value;
        } catch(error) {
          console.info('[reading-ai]',{task:'reading_review',outcome:readingDiagnostic(error),detail:readingValidationDetail(error)});
          throw error;
        }
      }});
      return Response.json({review,fingerprint},{headers});
    }catch(error){
      if(error instanceof ProviderError){
        console.info('[reading-ai]',{task:'reading_review',outcome:readingDiagnostic(error)});
        return Response.json({review:unavailableReview,fingerprint,retryable:true},{headers});
      }
      return fail(503);
    }
  }catch{return fail(503);}finally{if(entry)entry.busy=false;}
}
