import {createApiClient,ApiError} from '@/lib/api/client';
import {getIdToken} from '@/lib/firebase/client';
export type Module='listening'|'reading'|'writing'|'speaking';
export interface HistoryItem{id:string;module:Module;title:string;completed_at:string|null;correct_count:number|null;incorrect_count:number|null;unanswered_count:number|null;total_questions:number|null;estimated_band:number|null;ai_status:string;saved_explanations:number;is_test:boolean}
export interface HistoryData{items:HistoryItem[];total:number;page:number;limit:number}
export interface Activity{timezone:string;tests_completed:number;total_practice_sessions:number;current_streak:number;longest_streak:number;active_days:number;days:{date:string;count:number}[];undated_sessions:number}
export interface Profile{uid:string;display_name:string|null;email:string|null;target_ielts_band:number|null}
export function practiceApi(uid:string){return createApiClient(force=>getIdToken(force,uid));}
export async function avatarRequest(uid:string,method='GET',body?:Blob,signal?:AbortSignal){
 const token=await getIdToken(false,uid);if(!token)throw new ApiError(401,'sign_in_required');
 const response=await fetch('/api/alua/practice/avatar',{method,headers:{Authorization:`Bearer ${token}`,...(body?{'Content-Type':body.type}:{})},body,signal,cache:'no-store',credentials:'omit',redirect:'error'});
 if(method==='GET'&&response.status===404)return null;
 if(!response.ok)throw new ApiError(response.status,'avatar_request_failed');
 return method==='GET'?await response.blob():null;
}
export function dateLabel(value:string){return new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Almaty',day:'numeric',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'}).format(new Date(value));}
