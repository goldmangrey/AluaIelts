"use client";
import {useCallback,useEffect,useState} from 'react';
import {getIdToken} from '@/lib/firebase/client';
import r from './review.module.css';
export interface AIExplanationData {what_happened:string;why:string;next_time:string;evidence:{available:boolean;reason:string|null;part:number;quote:string|null;segment_ids:string[];clip_start:number|null;clip_end:number|null}}
export function AIExplanation({uid,attemptId,number,initial,onLoaded,onPlay,looping}:{uid:string;attemptId:string;number:number;initial?:AIExplanationData;onLoaded:(data:AIExplanationData)=>void;onPlay:(data:AIExplanationData,loop:boolean)=>void;looping:boolean}){
 const [data,setData]=useState(initial),[error,setError]=useState(false),[revision,setRevision]=useState(0);
 const load=useCallback(async(signal:AbortSignal)=>{
  const token=await getIdToken(false,uid);
  if(!token)throw Error();
  const response=await fetch('/api/listening/review',{method:'POST',headers:{Authorization:`Bearer ${token}`,'Content-Type':'application/json'},body:JSON.stringify({attempt_id:attemptId,question_number:number}),signal,cache:'no-store',redirect:'error'});
  if(!response.ok)throw Error();
  const result=await response.json() as AIExplanationData;
  if(!result||![result.what_happened,result.why,result.next_time].every(v=>typeof v==='string')||typeof result.evidence?.available!=='boolean')throw Error();
  if(!signal.aborted){setData(result);onLoaded(result);}
 },[uid,attemptId,number,onLoaded]);
 useEffect(()=>{if(initial)return;const abort=new AbortController();void Promise.resolve().then(()=>{if(!abort.signal.aborted)return load(abort.signal);}).catch(()=>{if(!abort.signal.aborted)setError(true);});return()=>abort.abort();},[initial,load,revision]);
 return <section className={r.aiExplanation} aria-label={`AI explanation for question ${number}`}>
  {!data?(error?<p role="status">Не удалось загрузить разбор. <button type="button" onClick={()=>{setError(false);setRevision(v=>v+1);}}>Retry</button></p>:<p role="status">Готовим разбор…</p>):<>
   <p>{data.what_happened}</p><p>{data.why}</p><p className={r.aiTip}>{data.next_time}</p>
   {data.evidence.available&&typeof data.evidence.clip_start==='number'&&typeof data.evidence.clip_end==='number'&&<div className={r.aiActions}><button type="button" onClick={()=>onPlay(data,false)}>Play Moment</button><button type="button" aria-pressed={looping} onClick={()=>onPlay(data,true)}>Loop Moment</button></div>}
   {data.evidence.available&&data.evidence.quote&&<details><summary>Transcript quote</summary><blockquote>{data.evidence.quote}</blockquote></details>}
  </>}
 </section>;
}
