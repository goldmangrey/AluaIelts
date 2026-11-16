"use client";
import {AITypewriter} from "@/components/ai-typewriter";
import {LuaMascot} from '@/components/lua-mascot';
import {useEffect,useRef,useState} from 'react';
import {practiceApi} from '@/features/practice/history/api';
import {getIdToken} from '@/lib/firebase/client';
import r from './review.module.css';
export interface AIExplanationData {cached?:boolean;what_happened:string;why:string;next_time:string;evidence:{available:boolean;reason:string|null;part:number;quote:string|null;segment_ids:string[];clip_start:number|null;clip_end:number|null}}
// Owner/attempt/question-scoped transient promises survive accordion remounts, never browser storage.
const requests=new Map<string,{until:number;promise:Promise<AIExplanationData>;generating:boolean;listeners:Set<()=>void>}>();
function load(uid:string,attemptId:string,number:number,onGenerating:()=>void) {
 const key=JSON.stringify([uid,attemptId,number]),now=Date.now();
 for(const [k,v]of requests)if(v.until<now)requests.delete(k);
 const existing=requests.get(key);if(existing){existing.listeners.add(onGenerating);if(existing.generating)onGenerating();return existing.promise;}
 if(requests.size>=120)throw Error('busy');
 const promise=(async()=>{
  const abort=new AbortController(),timer=setTimeout(()=>abort.abort(),55_000);
  try{
   const stored=await practiceApi(uid)(`/practice/reviews/listening/${attemptId}?question=${number}`,abort.signal) as {response:AIExplanationData|null};
   if(stored.response)return stored.response;
   const token=await getIdToken(false,uid);abort.signal.throwIfAborted();if(!token)throw Error();
   const flight=requests.get(key);if(flight){flight.generating=true;for(const listener of flight.listeners)listener();}
   const response=await fetch('/api/listening/review',{method:'POST',headers:{Authorization:`Bearer ${token}`,'Content-Type':'application/json'},body:JSON.stringify({attempt_id:attemptId,question_number:number}),signal:abort.signal,cache:'no-store',redirect:'error'});
   if(!response.ok)throw Error();const data=await response.json() as AIExplanationData;
   if(!data||![data.what_happened,data.why,data.next_time].every(v=>typeof v==='string')||typeof data.evidence?.available!=='boolean')throw Error();
   return data;
  }finally{clearTimeout(timer);const flight=requests.get(key);if(flight){flight.generating=false;flight.listeners.clear();}}
 })();requests.set(key,{until:now+60_000,promise,generating:false,listeners:new Set([onGenerating])});void promise.catch(()=>{if(requests.get(key)?.promise===promise)requests.delete(key)});return promise;
}
export function AIExplanation({uid,attemptId,number,initial,onLoaded,onPlay,looping,showMascot=true}:{showMascot?:boolean;uid:string;attemptId:string;number:number;initial?:AIExplanationData;onLoaded:(data:AIExplanationData)=>void;onPlay:(data:AIExplanationData,loop:boolean)=>void;looping:boolean}){
 const owner=JSON.stringify([uid,attemptId,number]);
 const [state,setState]=useState<{owner:string;data?:AIExplanationData;error?:boolean;generating?:boolean}>({owner,data:initial}),[revision,setRevision]=useState(0);
 const callback=useRef(onLoaded);useEffect(()=>{callback.current=onLoaded},[onLoaded]);
 useEffect(()=>{let active=true;if(initial)return;void Promise.resolve().then(()=>load(uid,attemptId,number,()=>{if(active)setState({owner,generating:true})})).then(data=>{if(active){setState({owner,data});callback.current(data)}}).catch(()=>{if(active)setState({owner,error:true})});return()=>{active=false}},[uid,attemptId,number,owner,initial,revision]);
 const data=initial??(state.owner===owner?state.data:undefined),error=state.owner===owner&&state.error;
 return <section className={r.aiExplanation} aria-label={`AI explanation for question ${number}`}>
 {showMascot&&(data||state.owner===owner&&state.generating&&!error)&&<LuaMascot context="review" emotion={data?"aha":"thinking"} size={60}/>}
 {!data?(error?<p role="status">Не удалось загрузить разбор. <button type="button" onClick={()=>{setState({owner});setRevision(v=>v+1)}}>Retry</button></p>:<p role="status">Готовим разбор…</p>):<>
 <AITypewriter key={owner} identity={owner} content={JSON.stringify([data.what_happened,data.why,data.next_time])} active={showMascot}><p>{data.what_happened}</p><p>{data.why}</p><p className={r.aiTip}>{data.next_time}</p></AITypewriter>
 {data.evidence.available&&typeof data.evidence.clip_start==='number'&&typeof data.evidence.clip_end==='number'&&<div className={r.aiActions}><button type="button" onPointerDown={e=>e.preventDefault()} onClick={e=>{e.currentTarget.focus({preventScroll:true});onPlay(data,false)}}>Play Moment</button><button type="button" aria-pressed={looping} onPointerDown={e=>e.preventDefault()} onClick={e=>{e.currentTarget.focus({preventScroll:true});onPlay(data,true)}}>Loop Moment</button></div>}
 {data.evidence.available&&data.evidence.quote&&<details><summary>Transcript quote</summary><blockquote>{data.evidence.quote}</blockquote></details>}
 </>}
 </section>;
}
