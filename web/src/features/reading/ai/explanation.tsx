"use client";
import {useCallback,useEffect,useLayoutEffect,useRef,useState} from 'react';
import {getIdToken} from '@/lib/firebase/client';
import type {Exam,Question} from '../exam/models';
import type {ReviewResponse} from './contract';
import styles from './review.module.css';
export function parseReviewResponse(value:unknown,qid:string,exam:Exam):ReviewResponse {
  const data=value as ReviewResponse;
  if(!data||data.question_id!==qid||typeof data.fingerprint!=='string'||!data.review||!['found','unavailable'].includes(data.review.evidence_status)||!Array.isArray(data.review.evidence)||data.review.evidence.length>3)throw Error();
  for(const field of ['why_user_answer_wrong','why_correct_answer_works','ielts_tip'] as const)if(typeof data.review[field]!=='string'||data.review[field].length>1800)throw Error();
  const passage=exam.passages.find(p=>p.question_groups.some(g=>g.questions.some(q=>q.id===qid)));
  for(const e of data.review.evidence){const text=passage?.content[e.block_index]?.text;if(e.passage_id!==passage?.id||typeof text!=='string'||!Number.isInteger(e.start)||!Number.isInteger(e.end)||e.start<0||e.end<=e.start||text.slice(e.start,e.end)!==e.quote||text.indexOf(e.quote)!==e.start||text.indexOf(e.quote,e.start+1)>=0)throw Error();}
  if(data.review.evidence_status==='unavailable'&&data.review.evidence.length||data.review.evidence_status==='found'&&!data.review.evidence.length)throw Error();
  return data;
}
export function useReadingAI(uid:string,attemptId:string,exam:Exam,current:string|null) {
  const owner=JSON.stringify([uid,attemptId]);
  const flightQuestion=useRef<string|null>(null);
  const cache=useRef(new Map<string,ReviewResponse>()),inflight=useRef<AbortController|null>(null);
  const [state,setState]=useState<{owner?:string;questionId:string|null;loading:boolean;data?:ReviewResponse;error?:'rate'|'unavailable';cached?:boolean}>({questionId:null,loading:false});
  const currentRef=useRef(current);useEffect(()=>{currentRef.current=current;if(flightQuestion.current!==current)inflight.current?.abort();},[current]);
  const open=useCallback(async(qid:string)=>{
    inflight.current?.abort();currentRef.current=qid;flightQuestion.current=qid;
    const saved=cache.current.get(JSON.stringify([owner,qid]));if(saved){setState({owner,questionId:qid,loading:false,data:saved,cached:true});return;}
    const abort=new AbortController();inflight.current=abort;
    setState({owner,questionId:qid,loading:true});let timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;abort.abort();},55_000);
    try {
      let cancel:(()=>void)|undefined;
      const token=await Promise.race([getIdToken(false,uid),new Promise<never>((_,reject)=>{cancel=()=>reject(Error());abort.signal.addEventListener('abort',cancel,{once:true});})]).finally(()=>{if(cancel)abort.signal.removeEventListener('abort',cancel);});
      abort.signal.throwIfAborted();if(!token)throw Error();
      const response=await fetch('/api/reading/review',{method:'POST',headers:{Authorization:`Bearer ${token}`,'Content-Type':'application/json'},body:JSON.stringify({attempt_id:attemptId,question_id:qid}),cache:'no-store',credentials:'omit',redirect:'error',signal:abort.signal});
      if(!response.ok){if(response.status===429)throw new Error('rate');throw Error();}
      const data=parseReviewResponse(await response.json(),qid,exam);
      cache.current.set(JSON.stringify([owner,qid]),data);
      if(inflight.current===abort&&currentRef.current===qid)setState({owner,questionId:qid,loading:false,data,cached:data.cached});
    }catch(error){if((!abort.signal.aborted||timedOut)&&inflight.current===abort&&currentRef.current===qid)setState({owner,questionId:qid,loading:false,error:error instanceof Error&&error.message==='rate'?'rate':'unavailable'});}
    finally{clearTimeout(timer);}
  },[uid,attemptId,exam,owner]);
  useEffect(()=>()=>inflight.current?.abort(),[]);
  const close=()=>{inflight.current?.abort();setState({owner,questionId:null,loading:false});};
  return {state:state.owner===owner?state:{...state,questionId:null,loading:false,data:undefined,error:undefined},open,close,active:state.owner===owner&&state.questionId===current};
}
export type ReadingAIState=ReturnType<typeof useReadingAI>;
export function ReadingAIExplanation({question,ai,onShow,verdict}:{question:Question;ai:ReadingAIState;onShow:()=>void;verdict?:{is_correct:boolean;unanswered:boolean}}) {
  const {state}=ai,data=state.data,review=data?.review,region=useRef<HTMLElement>(null);
  useLayoutEffect(()=>{
    const card=region.current,scroll=card?.closest<HTMLElement>('.questions-scroll');
    if(card&&scroll&&scroll.clientHeight){scroll.scrollTop+=card.getBoundingClientRect().top-scroll.getBoundingClientRect().top-52;card.focus({preventScroll:true});}
  },[question.id,state.loading]);
  const close=()=>{
    const scroll=region.current?.closest<HTMLElement>('.questions-scroll'),trigger=scroll?.querySelector<HTMLElement>(`[aria-controls="reading-ai-${question.id}"]`);
    ai.close();if(scroll&&trigger){scroll.scrollTop+=trigger.getBoundingClientRect().top-scroll.getBoundingClientRect().top-60;trigger.focus({preventScroll:true});}
  };
  return <section ref={region} tabIndex={-1} id={`reading-ai-${question.id}`} className={styles.card} aria-label={`AI explanation for question ${question.number}`} aria-busy={state.loading}>
    <header><span aria-hidden="true">✦</span><h4>AI explanation <span>· Q{question.number}</span></h4>{state.cached&&<small>Saved explanation</small>}<button className={styles.close} type="button" aria-label="Close AI explanation" onClick={close}>×</button></header>
    <div aria-live="polite">{state.loading?<p className={styles.loading} role="status">Сопоставляем вопрос с текстом…</p>:state.error?<><p role="alert">{state.error==='rate'?'Слишком много запросов. Попробуйте через минуту.':'AI-разбор временно недоступен. Ваши ответы и результат сохранены.'}</p><button type="button" onClick={()=>void ai.open(question.id)}>Retry</button></>:review?<>
      <h5>{verdict?.is_correct?'Your answer is correct':verdict?.unanswered?'Finding the answer':'Why your answer is wrong'}</h5><p>{review.why_user_answer_wrong}</p>
      <h5>Why the correct answer works</h5><p>{review.why_correct_answer_works}</p>
      {review.evidence_status==='found'?<><h5>{review.evidence.every(e=>e.kind==='relevant_context')?'Relevant context':'Evidence in passage'}</h5>{review.evidence.map((e,i)=><blockquote key={i}>{e.quote}</blockquote>)}<button type="button" className={styles.show} onClick={onShow}>↗ Show in passage</button></>:<p className={styles.limitation}>Не удалось надёжно подтвердить фрагмент текста для этого вопроса. Подсветка недоступна.</p>}
      <h5>IELTS tip</h5><p>{review.ielts_tip}</p>
      {data?.source_status!=='ready'&&<small className={styles.source}>Используется сохранённый текст. Источник ещё не полностью выверен по PDF.</small>}
    </>:null}</div>
  </section>;
}
