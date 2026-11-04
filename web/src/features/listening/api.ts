import {createApiClient,ApiError} from "@/lib/api/client";
import {getIdToken} from "@/lib/firebase/client";
import type {Attempt,Entry,Exam,Result} from "./models";
export function api(uid:string) {return createApiClient(force=>getIdToken(force,uid));}
export async function attempt(uid:string,id:string):Promise<Attempt>{const data=await api(uid)(`/listening/attempts/${id}`) as Attempt;if(data.id!==id||!data.exam||!Number.isInteger(data.version))throw new ApiError(502,"unexpected_response");return data;}
export async function catalog(uid:string){const data=await api(uid)("/listening/exams") as {items:Entry[]};if(!Array.isArray(data.items)||data.items.length!==72)throw new ApiError(502,"unexpected_response");return data.items;}
export async function details(uid:string,id:string){return await api(uid)(`/listening/exams/${id}`) as {exam:Exam;metadata:Entry};}
export async function results(uid:string,id:string,review=false){return await api(uid)(`/listening/attempts/${id}/${review?"review":"result"}`) as Result;}
export async function authorize(uid:string,id:string){const token=await getIdToken(false,uid);if(!token)throw new ApiError(401,"sign_in_required");const response=await fetch("/api/listening/authorize",{method:"POST",headers:{Authorization:`Bearer ${token}`,"Content-Type":"application/json"},body:JSON.stringify({attempt_id:id}),cache:"no-store",redirect:"error"});if(!response.ok)throw new ApiError(response.status,"playback_authorization_failed");}
export const modeLabel=(mode:string)=>({verified:"Verified practice",preliminary:"Preliminary practice",ungraded:"Ungraded practice",blocked:"Unavailable"}[mode]||mode);
export const message=(error:unknown)=>error instanceof ApiError?(error.status===409?"A newer save exists. Reconcile your draft to continue.":error.status===401?"Your session has expired. Log in again; your local draft is preserved.":error.status===404?"This attempt or media is unavailable.":error.status===422?"This exam is not available on the backend yet.":"Connection interrupted. Your draft is preserved; try again."):"Couldn’t connect. Please try again.";
