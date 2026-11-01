"use client";
import Link from "next/link";
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
export function RecordsPage({id,review=false}:{id?:string;review?:boolean}) {
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
    return <><p className="eyebrow">{examLabel(a.exam_id)}</p><h1>{a.status==="expired"?"Time elapsed.":"Completed."}</h1><p className="result-score">{r.raw_score} <span>/ {r.total_questions}</span></p><p>Correct answers</p>{r.estimated_band!==null&&<p className="result-band">Estimated IELTS Academic Reading Band {r.estimated_band}</p>}<p>Time taken: {Math.floor(r.elapsed_seconds/60)} min {r.elapsed_seconds%60} sec</p>{a.submitted_at&&<p>Completed {new Date(a.submitted_at).toLocaleString()}</p>}{state.unsent!==undefined&&state.unsent>0&&<p role="alert">{state.unsent} local answers differ from the server result. They were retained on this device and were not included in this score.</p>}{state.local&&state.local.length>0&&<details><summary>View local answers not included in this score</summary><ul>{state.local.map(p=><li key={p.number}>Question {p.number}: {p.answer||"Blank"}</li>)}</ul></details>}{a.not_fully_proofread&&<p className="small-note">Private practice · This test has not been fully proofread. Band is an estimate.</p>}<div className="dialog-actions"><Link className="text-link" href={`/reading/attempts/${id}/review`}>Review answers</Link><Link className="text-link" href="/reading/history">My attempts</Link><Link className="text-link" href="/reading">Back to Reading</Link></div></>;
  };
  if(review&&session.status==="ready"&&state.owner===session.generation&&state.request===request&&state.attempt&&state.result)return <ReadingExam key={`${id}:${session.generation}`} uid={session.user!.uid} attempt={state.attempt} result={state.result}/>;
  return <><SiteHeader/><main id="main" className="page-shell records-page">{content()}</main></>;
}
