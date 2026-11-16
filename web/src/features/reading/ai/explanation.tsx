"use client";
import {AITypewriter} from "@/components/ai-typewriter";
import {LuaMascot} from '@/components/lua-mascot';
import {useCallback,useEffect,useRef,useState} from 'react';
import {practiceApi} from '@/features/practice/history/api';
import {getIdToken} from '@/lib/firebase/client';
import type {Exam,Question} from '../exam/models';
import type {ReviewResponse} from './contract';
import styles from './review.module.css';
export function parseReviewResponse(value:unknown,qid:string,exam:Exam):ReviewResponse {
  const data=value as ReviewResponse;
  if(!data||data.question_id!==qid||typeof data.fingerprint!=='string'||!data.review||!['found','unavailable'].includes(data.review.evidence_status)||!Array.isArray(data.review.evidence)||data.review.evidence.length>3)throw Error();
  for(const field of ['why_user_answer_wrong','why_correct_answer_works','ielts_tip'] as const)if(typeof data.review[field]!=='string'||data.review[field].length>1800)throw Error();
  const passage=exam.passages.find(p=>p.question_groups.some(g=>g.questions.some(q=>q.id===qid)));
  for(const e of data.review.evidence){const text=passage?.content[e.block_index]?.text;if(e.passage_id!==passage?.id||typeof text!=='string'||!Number.isInteger(e.start)||!Number.isInteger(e.end)||e.start<0||e.end<=e.start||text.slice(e.start,e.end)!==e.quote)throw Error();}
  if(data.review.evidence_status==='unavailable'&&data.review.evidence.length||data.review.evidence_status==='found'&&!data.review.evidence.length)throw Error();
  return data;
}
type State={questionId:string|null;loading:boolean;generating?:boolean;data?:ReviewResponse;error?:'rate'|'unavailable';cached?:boolean};
export function useReadingAI(uid:string,attemptId:string,exam:Exam,current:string|null,enabled=true) {
  const owner=JSON.stringify([uid,attemptId]);
  const [stored,setStored]=useState<string[]>([]);
  const flights=useRef(new Map<string,AbortController>()),saved=useRef(new Map<string,ReviewResponse>());
  const [store,setStore]=useState<{owner:string;states:Record<string,State>;opened:Set<string>}>(()=>({owner,states:{},opened:new Set()}));
  useEffect(()=>()=>{for(const f of flights.current.values())f.abort();flights.current.clear();saved.current.clear();},[owner]);
  const update=useCallback((qid:string,value:State)=>setStore(s=>({owner,opened:s.owner===owner?s.opened:new Set(),states:{...(s.owner===owner?s.states:{}),[qid]:value}})),[owner]);
  useEffect(()=>{if(!enabled)return;const abort=new AbortController();void practiceApi(uid)(`/practice/reviews/reading/${attemptId}`,abort.signal).then(v=>{const questions=(v as {questions:unknown}).questions;if(Array.isArray(questions)&&questions.every(q=>typeof q==='string'))setStored(questions);}).catch(()=>{});return()=>abort.abort();},[uid,attemptId,enabled]);
  const open=useCallback(async(qid:string,generateIfMissing=true)=>{
    const key=JSON.stringify([owner,qid]);
    setStore(s=>({owner,states:s.owner===owner?s.states:{},opened:new Set([...(s.owner===owner?s.opened:[]),qid])}));
    if(saved.current.has(key)){update(qid,{questionId:qid,loading:false,data:saved.current.get(key),cached:true});return;}
    if(flights.current.has(key))return;
    const abort=new AbortController();flights.current.set(key,abort);update(qid,{questionId:qid,loading:true});
    const timer=setTimeout(()=>abort.abort(),55_000);
    try {
      const existing=await practiceApi(uid)(`/practice/reviews/reading/${attemptId}?question=${encodeURIComponent(qid)}`,abort.signal) as {response:unknown};
      if(existing.response){const data=parseReviewResponse(existing.response,qid,exam);saved.current.set(key,data);update(qid,{questionId:qid,loading:false,data,cached:true});return;}
      if(!generateIfMissing){update(qid,{questionId:qid,loading:false,error:'unavailable'});return;}
      const token=await getIdToken(false,uid);abort.signal.throwIfAborted();if(!token)throw Error();
      update(qid,{questionId:qid,loading:true,generating:true});
      const response=await fetch('/api/reading/review',{method:'POST',headers:{Authorization:`Bearer ${token}`,'Content-Type':'application/json'},body:JSON.stringify({attempt_id:attemptId,question_id:qid}),cache:'no-store',credentials:'omit',redirect:'error',signal:abort.signal});
      if(!response.ok)throw Error(response.status===429?'rate':'unavailable');
      const data=parseReviewResponse(await response.json(),qid,exam);abort.signal.throwIfAborted();
      if(data.review.evidence_status==='found'){saved.current.set(key,data);setStored(v=>v.includes(qid)?v:[...v,qid]);}update(qid,{questionId:qid,loading:false,data,cached:data.cached});
    }catch(error){if(flights.current.get(key)===abort)update(qid,{questionId:qid,loading:false,error:error instanceof Error&&error.message==='rate'?'rate':'unavailable'});}
    finally{clearTimeout(timer);if(flights.current.get(key)===abort)flights.current.delete(key);}
  },[uid,attemptId,exam,owner,update]);
  useEffect(()=>{let live=true;if(current&&stored.includes(current))void Promise.resolve().then(()=>{if(live)void open(current,false);});return()=>{live=false;};},[current,stored,open]);
  const forQuestion=(qid:string|null)=>({revealKey:JSON.stringify([owner,qid]),state:store.owner===owner&&qid?store.states[qid]??{questionId:qid,loading:false}:{questionId:null,loading:false},open,
    close:()=>setStore(s=>{const opened=new Set(s.opened);if(qid)opened.delete(qid);return {...s,opened};}),
    active:store.owner===owner&&!!qid&&store.opened.has(qid)});
  return {...forQuestion(current),forQuestion,isSaved:(qid:string)=>stored.includes(qid)};
}
export type ReadingAIState=ReturnType<ReturnType<typeof useReadingAI>['forQuestion']>;
export function ReadingAIExplanation({question,ai,onShow,verdict,showMascot=true}:{showMascot?:boolean;question:Question;ai:ReadingAIState;onShow:()=>void;verdict?:{is_correct:boolean;unanswered:boolean}}) {
  const {state}=ai,data=state.data,review=data?.review,region=useRef<HTMLElement>(null);
  const close=()=>ai.close();
  return <section ref={region} tabIndex={-1} id={`reading-ai-${question.id}`} className={styles.card} aria-label={`AI explanation for question ${question.number}`} aria-busy={state.loading}>
    <header><span aria-hidden="true">✦</span><h4>AI explanation <span>· Q{question.number}</span></h4><button className={styles.close} type="button" aria-label="Close AI explanation" onClick={close}>×</button></header>
    <div aria-live="polite">{showMascot&&(review||state.generating)&&<LuaMascot context="review" emotion={review?"aha":"thinking"} size={60}/>} {state.loading?<p className={styles.loading} role="status">Сопоставляем вопрос с текстом…</p>:state.error?<><p role="alert">{state.error==='rate'?'Слишком много запросов. Попробуйте через минуту.':'AI-разбор временно недоступен. Ваши ответы и результат сохранены.'}</p><button type="button" onClick={()=>void ai.open(question.id)}>Retry</button></>:review?<AITypewriter key={`${ai.revealKey}:${data.fingerprint}`} identity={ai.revealKey} content={JSON.stringify(review)} active={showMascot}>
      <h5>{verdict?.is_correct?'Your answer is correct':verdict?.unanswered?'Finding the answer':'Why your answer is wrong'}</h5><p>{review.why_user_answer_wrong}</p>
      <h5>Why the correct answer works</h5><p>{review.why_correct_answer_works}</p>
      {review.evidence_status==='found'?<><h5>{review.evidence.every(e=>e.kind==='relevant_context')?'Relevant context':'Evidence in passage'}</h5>{review.evidence.map((e,i)=><blockquote key={i}>{e.quote}</blockquote>)}<button type="button" className={styles.show} onClick={onShow}>↗ Show in passage</button></>:<><p className={styles.limitation}>Не удалось надёжно подтвердить фрагмент текста для этого вопроса. Подсветка недоступна.</p>{data?.retryable===true&&<button type="button" onClick={()=>void ai.open(question.id)}>Retry</button>}</>}
      <h5>IELTS tip</h5><p>{review.ielts_tip}</p>
      {data?.source_status!=='ready'&&<small data-ai-static className={styles.source}>В исходном тексте возможны неточности.</small>}
    </AITypewriter>:null}</div>
  </section>;
}
