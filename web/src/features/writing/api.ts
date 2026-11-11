import {createApiClient,ApiError} from '@/lib/api/client';
import {getIdToken} from '@/lib/firebase/client';
import type {Attempt} from './contract';
import {WritingAIError,responseFailure,rememberFailure,forgetFailure} from './failure';
export const api=(uid:string)=>createApiClient(force=>getIdToken(force,uid));
const inFlight=new Map<string,Promise<Attempt>>();
export function assess(uid:string,id:string):Promise<Attempt>{
 const key=JSON.stringify([uid,id]),existing=inFlight.get(key);if(existing)return existing;
 const promise=(async()=>{try{const token=await getIdToken(false,uid);if(!token)throw new ApiError(401,'unauthorized');
 const response=await fetch('/api/writing/assess',{method:'POST',headers:{Authorization:`Bearer ${token}`,'Content-Type':'application/json'},body:JSON.stringify({attempt_id:id}),cache:'no-store',signal:AbortSignal.timeout(85000)});
 if(!response.ok){let body:unknown;try{body=await response.json();}catch{}const {code,failure}=responseFailure(response.status,body,response.headers);rememberFailure(uid,id,failure);throw new WritingAIError(response.status,code,failure);}
 const result=await response.json() as Attempt;forgetFailure(uid,id);return result;
 }catch(error){if(error instanceof ApiError)throw error;const failure={kind:'transport_error' as const,source:'transport' as const,retryable:true};rememberFailure(uid,id,failure);throw new WritingAIError(0,'writing_transport_error',failure);}})();
 inFlight.set(key,promise);void promise.finally(()=>{if(inFlight.get(key)===promise)inFlight.delete(key)}).catch(()=>{});return promise;
}
