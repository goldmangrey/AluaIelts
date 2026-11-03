"use client";
import Link from "next/link";
import type { CSSProperties } from "react";
import styles from "./result.module.css";
import { useEffect, useState } from "react";
import { useSession, retrySession, rejectSession } from "@/features/auth/session";
import { StatusPanel } from "@/components/status-panel";
import { ApiError } from "@/lib/api/client";
import { SiteHeader } from "@/components/site-header";
import { ReadingExam } from "./reading-exam";
import { getAttempt, readingApi } from "./api";
import { readingMessage } from "./messages";
import type { Attempt } from "./models";
import { examLabel, parseHistory, parseResult, type HistoryItem, type ReadingResult } from "./results";
import { browserDraftStore } from "./draft-storage";
export function RecordsPage({id,review=false,reviewQuestionId}:{id?:string;review?:boolean;reviewQuestionId?:string}) {
  const session=useSession(),path=id?`/reading/attempts/${id}/${review?"review":"result"}`:"/reading/history";
  const [offset,setOffset]=useState(0),[retry,setRetry]=useState(0);
  const [state,setState]=useState<{owner?:number;request?:string;attempt?:Attempt;result?:ReadingResult;items?:HistoryItem[];error?:unknown;unsent?:number;local?:{number:number;answer:string}[]}>({});
  const request=`${path}:${offset}:${retry}`;
  useEffect(()=>{
    if(session.status!=="ready"||!session.user)return;
    const abort=new AbortController(),owner=session.generation,uid=session.user.uid;
    void(async()=>{
      if(!id){const items=parseHistory(await readingApi(uid)(`/reading/attempts?limit=20&offset=${offset}`,abort.signal));if(!abort.signal.aborted)setState({owner,request,items});return}
      const attempt=await getAttempt(id,uid,abort.signal);
      if(attempt.status==="in_progress"){if(!abort.signal.aborted)setState({owner,request,attempt});return}
      const result=parseResult(await readingApi(uid)(`/reading/attempts/${id}/result`,abort.signal),attempt);
      let unsent=0;let local:{number:number;answer:string}[]=[];
      try{const draft=await browserDraftStore(uid,id,attempt.content_hash,"read-only-result").read();local=Object.keys(draft?.answers??{}).filter(q=>(draft?.answers[q]??"")!==(attempt.answers[q]??"")).map(q=>({number:result.positions.find(p=>p.question_id===q)?.number??0,answer:draft?.answers[q]??""}));unsent=local.length}catch{/* Results remain accessible if local storage is unavailable. */}
      if(!abort.signal.aborted)setState({owner,request,attempt,result,unsent,local});
    })().catch((error:unknown)=>{if(!abort.signal.aborted){if(error instanceof ApiError&&error.status===401)rejectSession(owner);setState({owner,request,error})}});
    return()=>abort.abort();
  },[id,offset,retry,session.status,session.generation,session.user,request]);
  const content=()=>{
    if(session.status==="signed_out")return <StatusPanel title="Log in to view your Reading." href={`/login?next=${encodeURIComponent(path)}`} label="Log in">Only your own attempts are available.</StatusPanel>;
    if(session.status==="error")return <StatusPanel title="Your session couldn’t load." retry={()=>void retrySession().catch(()=>{})}>{readingMessage(session.error)} <Link href={`/login?next=${encodeURIComponent(path)}`}>Log in</Link></StatusPanel>;
    if(session.status!=="ready"||(state.owner!==session.generation||state.request!==request))return <p role="status">Loading your Reading…</p>;
    if(state.error)return <StatusPanel title="Your Reading couldn’t load." retry={()=>setRetry(n=>n+1)}>{readingMessage(state.error)}</StatusPanel>;
    if(!id)return <><p className="eyebrow">Reading</p><h1>My attempts.</h1>{!state.items?.length?<p>No attempts on this page.</p>:<div className="attempt-history">{state.items.map(item=><article key={item.id}><div><h2>{examLabel(item.exam_id)}</h2><p>{new Date(item.started_at).toLocaleString()} · {item.status==="in_progress"?"In progress":item.status==="expired"?"Expired":"Completed"}{item.mode==="passage_practice"?" · Passage practice":""}</p>{item.raw_score!==null&&<p>{item.raw_score}{item.mode==="full_exam"?" / 40":""} correct{item.estimated_band!==null?` · Estimated band ${item.estimated_band}`:""}</p>}</div><Link className="text-link" href={`/reading/attempts/${item.id}${item.status==="in_progress"?"":"/result"}`}>{item.status==="in_progress"?"Continue":"View result"}</Link></article>)}</div>}<nav className="dialog-actions" aria-label="Attempt history pages"><button disabled={!offset} onClick={()=>setOffset(n=>Math.max(0,n-20))}>Previous</button><button disabled={(state.items?.length??0)<20} onClick={()=>setOffset(n=>n+20)}>Next</button></nav><Link className="text-link" href="/reading">Back to Reading</Link></>;
    if(state.attempt&&!state.result)return <StatusPanel title="This test is still in progress." href={`/reading/attempts/${id}`} label="Continue test">Results are available only after the server completes your attempt.</StatusPanel>;
    const a=state.attempt,r=state.result;if(!a||!r)return null;
    return <ScoreResult attempt={a} result={r} unsent={state.unsent} local={state.local} />;
  };
  if(review&&session.status==="ready"&&state.owner===session.generation&&state.request===request&&state.attempt&&state.result)return <ReadingExam key={`${id}:${session.generation}:${reviewQuestionId??""}`} uid={session.user!.uid} attempt={state.attempt} result={state.result} reviewQuestionId={reviewQuestionId}/>;
  if(id&&!review)return <div className={styles.page}><header className={styles.header}><div className={styles.headerInner}>
    <Link className={styles.wordmark} href="/" aria-label="Alua home">alua<span>.</span></Link><span>Reading results</span>
  </div></header><main id="main" className={styles.main}>{content()}</main></div>;
  return <><SiteHeader/><main id="main" className="page-shell records-page">{content()}</main></>;
}


function ScoreResult({attempt:a,result:r,unsent,local}:{attempt:Attempt;result:ReadingResult;unsent?:number;local?:{number:number;answer:string}[]}) {
  const verdicts=new Map(r.positions.map(position=>[position.question_id,position]));
  // Membership and order come from the saved exam, verdicts only from the server.
  const passages=a.exam!.passages.map(passage=>({passage,positions:passage.question_groups.flatMap(group=>group.questions).map(question=>verdicts.get(question.id)!)}));
  const mistakes=r.positions.filter(position=>!position.is_correct);
  const reviewPath=`/reading/attempts/${a.id}/review`;
  const firstMistake=passages.flatMap(row=>row.positions).find(position=>!position.is_correct);
  const hasBand=r.estimated_band!==null;
  const expired=a.status==="expired"||r.completion_reason==="deadline";
  return <>
    <div className={styles.intro}>
      <p className={styles.eyebrow}>Cambridge IELTS {a.exam!.source_book} · Test {a.exam!.source_test_number}</p>
      <h1>Your result.</h1><p className={styles.subtitle}>{expired?"Time expired":"Completed"} · Academic Reading</p>
    </div>
    <div className={`${styles.scores} ${!hasBand?styles.rawOnly:""}`}>
      {hasBand&&<div><p className={styles.metricLabel}>Estimated IELTS band</p><p className={styles.band}>{r.estimated_band}</p><p className={styles.metricNote}>Band estimate</p></div>}
      <div><p className={styles.metricLabel}>Correct answers</p><p className={styles.raw}>{r.raw_score}<span> / {r.total_questions}</span></p><p className={styles.metricNote}>{Math.round(r.raw_score/r.total_questions*100)}% correct</p></div>
    </div>
    <section className={styles.fingerprint} aria-labelledby="answer-map-title">
      <div className={styles.mapHeading}><h2 id="answer-map-title">Your {r.total_questions} answers</h2><span>{passages.length} passages</span></div>
      <div className={styles.passages}>{passages.map(({passage,positions})=><section key={passage.id} aria-label={`Passage ${passage.number}`}>
        <div className={styles.passageHeading}><h3>Passage {passage.number}</h3><span>{positions.filter(position=>position.is_correct).length} <span className={styles.total}>/ {positions.length}</span></span></div>
        <div className={styles.cells} style={{"--answer-count":positions.length} as CSSProperties}>{positions.map(position=>{
          const status=position.unanswered?"unanswered":position.is_correct?"correct":"incorrect";
          return <Link key={position.question_id} prefetch={false} className={`${styles.cell} ${styles[status]}`} href={`${reviewPath}?question=${encodeURIComponent(position.question_id)}`}
            aria-label={`Question ${position.number}, ${status}`} title={`Question ${position.number} · ${status[0]!.toUpperCase()+status.slice(1)}`}><span aria-hidden="true" /></Link>;
        })}</div>
      </section>)}</div>
      <ul className={styles.legend} aria-label="Answer statuses"><li><span className={styles.correct} aria-hidden="true" />Correct</li><li><span className={styles.incorrect} aria-hidden="true" />Incorrect</li><li><span className={styles.unanswered} aria-hidden="true" />Unanswered</li></ul>
    </section>
    <div className={styles.actions}>
      <Link className={styles.primary} href={firstMistake?`${reviewPath}?question=${encodeURIComponent(firstMistake.question_id)}`:reviewPath}>{mistakes.length?`Review ${mistakes.length} ${mistakes.length===1?"mistake":"mistakes"}`:"Review all answers"}<span aria-hidden="true">↗</span></Link>
      <Link className={styles.back} href="/reading">Back to Reading <span aria-hidden="true">→</span></Link>
    </div>
    <div className={styles.notes}>
      <p>Time taken: {Math.floor(r.elapsed_seconds/60)} min {r.elapsed_seconds%60} sec{a.submitted_at&&<> · <time dateTime={a.submitted_at}>Completed {new Date(a.submitted_at).toLocaleString()}</time></>}</p>
      {a.not_fully_proofread&&<p>Private practice · This test has not been fully proofread.{hasBand?" Band is an estimate.":""}</p>}
      {unsent!==undefined&&unsent>0&&<p role="alert">{unsent} local answers differ from the server result. They were retained on this device and were not included in this score.</p>}
      {local&&local.length>0&&<details><summary>View local answers not included in this score</summary><ul>{local.map(p=><li key={p.number}>Question {p.number}: {p.answer||"Blank"}</li>)}</ul></details>}
    </div>
  </>;
}
