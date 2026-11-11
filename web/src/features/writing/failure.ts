import {ApiError} from '@/lib/api/client';
export type FailureKind='rate_limited'|'provider_unavailable'|'invalid_response'|'pending'|'configuration_error'|'transport_error';
export interface WritingFailure {kind:FailureKind;source:'application'|'provider'|'environment'|'transport';retryAt?:number;retryable:boolean;requestId?:string;attemptLimit?:boolean}
export class WritingAIError extends ApiError {constructor(status:number,code:string,readonly failure:WritingFailure){super(status,code);}}
const key=(uid:string,id:string)=>JSON.stringify(['alua:writing:failure:v1',uid,id]);
export function rememberFailure(uid:string,id:string,failure:WritingFailure){try{sessionStorage.setItem(key(uid,id),JSON.stringify({failure,expires:Date.now()+86400000}));}catch{}}
export function savedFailure(uid:string,id:string):WritingFailure|undefined{try{const value=JSON.parse(sessionStorage.getItem(key(uid,id))??'null');if(value?.expires>Date.now()&&['rate_limited','provider_unavailable','invalid_response','pending','configuration_error','transport_error'].includes(value?.failure?.kind))return value.failure;}catch{}return undefined;}
export function forgetFailure(uid:string,id:string){try{sessionStorage.removeItem(key(uid,id));}catch{}}
export function responseFailure(status:number,body:unknown,headers:Headers,now=Date.now()):{code:string;failure:WritingFailure}{
 const data=body as {error?:{code?:unknown;kind?:unknown;source?:unknown;retryable?:unknown;retry_after_seconds?:unknown}};
 const code=typeof data?.error?.code==='string'?data.error.code:'AI_UNAVAILABLE';
 const knownKind=data?.error?.kind;
 const kind:FailureKind=status===429?'rate_limited':code==='assessment_pending'?'pending':knownKind==='invalid_response'||code==='invalid_assessment'?'invalid_response':knownKind==='configuration_error'?'configuration_error':knownKind==='transport_error'?'transport_error':'provider_unavailable';
 const source= data?.error?.source==='provider'?'provider':data?.error?.source==='environment'?'environment':data?.error?.source==='transport'?'transport':'application';
 const raw=headers.get('retry-after');let ms=raw&&/^\d+(?:\.\d+)?$/.test(raw)?Number(raw)*1000:raw?Date.parse(raw)-now:0;
 if(!Number.isFinite(ms)||ms<0||ms>86400000)ms=0;
 const requestId=headers.get('x-request-id');
 return {code,failure:{kind,source,retryable:typeof data?.error?.retryable==='boolean'?data.error.retryable:status!==429,...(ms>0?{retryAt:now+ms}:{}),...(requestId&&/^[A-Za-z0-9:_-]{1,160}$/.test(requestId)?{requestId}:{}),...(code==='writing_attempt_limit'?{attemptLimit:true}:{})}};
}
