"use client";
import {TestStartModal,useTestSelection} from "@/components/test-start-modal";
import {LuaMascot} from '@/components/lua-mascot';
import {GuestCatalog} from "@/features/guest/catalog";
import {AuthRequired} from "@/features/auth/guest-access";
import Link from "next/link";
import {ResultCard,ResultPage} from "@/features/results/result-card";
import {retakeTest} from "@/features/results/retake";
import {useRouter} from "next/navigation";
import {useEffect,useRef,useState,useSyncExternalStore} from "react";
import {useSession,retrySession} from "@/features/auth/session";
import {api,attempt,catalog,details,message,results} from "./api";
import type {Attempt,Entry,Exam,Result} from "./models";
import {ListeningDraft} from "./draft";
import {Player} from "./player";
import {ListeningReview} from "./review";
import {WorkspaceNavigator} from "./workspace-navigator";
import {displayedPart} from "./source-material";
import {WorkspaceQuestions} from "./workspace-questions";
import w from "./workspace.module.css";
import s from "./listening.module.css";
export function ListeningPage({kind,id,reviewQuestion}:{reviewQuestion?:number;kind:"library"|"prepare"|"attempt"|"result"|"review";id?:string}){const session=useSession();const [loaded,setLoaded]=useState<{owner:number;resource:string;data:Entry[]|{exam:Exam;metadata:Entry}|Attempt|Result;editor?:ListeningDraft}>(),[error,setError]=useState<{value:unknown;resource:string;owner:number}>(),[revision,setRevision]=useState(0);
 useEffect(()=>{if(session.status!=="ready"||!session.user)return;let live=true;let editor:ListeningDraft|undefined;const uid=session.user.uid;const promise=kind==="library"?catalog(uid):kind==="prepare"?details(uid,id!):kind==="attempt"?attempt(uid,id!):results(uid,id!,true);promise.then(async data=>{if(!live)return;if(kind==="attempt"&&(data as Attempt).status==="in_progress"){editor=new ListeningDraft(data as Attempt,uid);await editor.initialize();if(!live){editor.dispose();return;}}setLoaded({owner:session.generation,resource:`${kind}:${id||""}`,data,editor});}).catch(e=>{if(live)setError({value:e,resource:`${kind}:${id||""}`,owner:session.generation});});return()=>{live=false;editor?.dispose();};},[kind,id,revision,session.status,session.user,session.generation]);
 const retry=()=>{setError(undefined);setLoaded(undefined);setRevision(n=>n+1);};
 if(session.status==="signed_out")return <main id="main">{kind==='library'||kind==='prepare'?<GuestCatalog module="listening" examId={kind==='prepare'?id:undefined}/>:<AuthRequired destination={`/listening/attempts/${id}${kind==='result'?'/results':kind==='review'?'/review':''}`}/>}</main>;
 if(session.status==="error")return <main id="main" className={s.shell}><h1>Your session couldn’t load</h1><button onClick={()=>void retrySession().catch(()=>{})}>Try again</button></main>;
 if(error&&error.resource===`${kind}:${id||""}`&&error.owner===session.generation)return <main id="main" className={s.shell}><h1>Listening</h1><p role="alert">{message(error.value)}</p><button onClick={retry}>Try again</button><Link href="/listening">Back to library</Link></main>;
 if(!loaded||loaded.owner!==session.generation||loaded.resource!==`${kind}:${id||""}`||!session.user)return <main id="main" className={s.shell} role="status">Loading your Listening practice…</main>;
 const uid=session.user.uid;
 if(kind==="library")return <Library entries={loaded.data as Entry[]}/>;
 if(kind==="prepare")return <Preparation data={loaded.data as {exam:Exam;metadata:Entry}} uid={uid}/>;
 if(kind==="attempt"){const a=loaded.data as Attempt;return a.status==="submitted"?<main id="main" className={s.shell}><h1>Practice completed</h1><Link href={`/listening/attempts/${a.id}/results`}>View results</Link></main>:<Workspace key={`${a.id}:${session.generation}`} initial={a} editor={loaded.editor!} uid={uid}/>;}
 return kind==="review"?<ListeningReview key={`${id}:${session.generation}`} result={loaded.data as Result} uid={uid} initialQuestion={reviewQuestion}/>:<Records result={loaded.data as Result} uid={uid} onRetry={retry}/>;
}
function Library({entries}:{entries:Entry[]}){
 const selection=useTestSelection(),session=useSession();
 const [selected,setSelected]=useState<{id:string;owner:number;data?:{exam:Exam;metadata:Entry};error?:string}>();
 useEffect(()=>{if(!selection.selected||!session.user)return;let live=true;const id=selection.selected,owner=session.generation;
 details(session.user.uid,id).then(data=>{if(data.exam.exam_id!==id||data.metadata.exam_id!==id)throw Error();if(live)setSelected({id,owner,data});}).catch(err=>{if(live)setSelected({id,owner,error:message(err)});});return()=>{live=false;};
 },[selection.selected,session.user,session.generation]);
 const item=entries.find(e=>e.exam_id===selection.selected),current=selected?.id===selection.selected&&selected.owner===session.generation?selected:undefined;
 return <> <main id="main" className={s.shell}><Link className={s.back} href="/">← All sections</Link><header className={s.hero}><span className={s.eyebrow}>IELTS Academic</span><h1 style={{display:"flex",alignItems:"center",gap:16}}>Listening <LuaMascot emotion="listening" size={88}/></h1><p>Four parts. Forty questions. Space to practise at your own pace.</p></header><div className={s.volumeList}>{Array.from({length:18},(_,i)=>i+4).map(book=><section key={book} className={s.volume}><h2>Cambridge {String(book).padStart(2,"0")}</h2><div className={s.tests}>{entries.filter(e=>e.book===book).map(e=><Link className={s.test} href={`?test=${e.exam_id}`} scroll={false} onClick={e=>e.currentTarget.focus({preventScroll:true})} onNavigate={event=>{event.preventDefault();selection.open(e.exam_id);}} key={e.exam_id}><div><h3>Test {e.printed_test_number}</h3></div><p>{e.active_attempt_id?`${e.answered_count}/40 answered · Resume`:e.content_mode==="blocked"?"Source material incomplete":!e.audio.technically_available?"Audio awaiting server setup":e.completed_count?`${e.completed_count} completed · Practise again`:"40 questions · 4 parts"}</p><span aria-hidden="true">↗</span></Link>)}</div></section>)}</div></main>{selection.selected&&<Preparation key={`${selection.selected}:${session.generation}`} data={current?.data} entry={item} loading={!current} loadError={current?.error} uid={session.user!.uid} onClose={selection.close}/>}</>;
}
function Preparation({data,entry,loading,loadError,uid,onClose}:{data?:{exam:Exam;metadata:Entry};entry?:Entry;loading?:boolean;loadError?:string;uid:string;onClose?:()=>void}){
 const router=useRouter(),lock=useRef(false);const [busy,setBusy]=useState(false),[error,setError]=useState<string>();const exam=data?.exam,e=data?.metadata??entry;
 async function start(){if(lock.current||!exam)return;lock.current=true;setBusy(true);setError(undefined);
 try{const key=`alua:listening:start:${uid}:${exam.exam_id}`;
 const run=async()=>{const latest=await details(uid,exam.exam_id);if(latest.metadata.active_attempt_id)return latest.metadata.active_attempt_id;
 let event=localStorage.getItem(key);if(!event){event=crypto.randomUUID();localStorage.setItem(key,event);}
 const created=await api(uid)("/listening/attempts",undefined,{method:"POST",body:{event_id:event,exam_id:exam.exam_id,reuse_active:true}}) as Attempt;
 if(!created.id||created.exam_id!==exam.exam_id)throw Error("Unexpected start response");
 localStorage.removeItem(key);return created.id;};
 const id=typeof navigator.locks?.request==="function"?await navigator.locks.request(`alua:listening:start:${uid}:${exam.exam_id}`,run):await run();
 router.push(`/listening/attempts/${id}`);
 }catch(err){setError(message(err));lock.current=false;setBusy(false);}}
 return <TestStartModal skill="Listening" book={e?.book??0} test={e?.printed_test_number??0} facts={exam&&e?[{value:exam.parts.length,label:"Parts"},{value:e.question_count,label:"Questions"}]:[]} loading={loading}
 onClose={()=>onClose?onClose():router.replace("/listening")} error={error??loadError??(!e?"This test is unavailable.":!e.can_start&&!e.active_attempt_id?e.block_reason??"This test is unavailable.":undefined)}
 note={e&&e.content_mode!=="verified"?"Practice material · Not fully verified":undefined}>
 {e?.active_attempt_id?<Link href={`/listening/attempts/${e.active_attempt_id}`}>Continue Listening <span aria-hidden="true">→</span></Link>:<button onClick={()=>void start()} disabled={busy||!exam||!e?.can_start}>{busy?"Opening test…":"Start Listening →"}</button>}
 </TestStartModal>;
}
function Workspace({initial,editor,uid}:{initial:Attempt;editor:ListeningDraft;uid:string}){const router=useRouter();const draft=useSyncExternalStore(editor.subscribe,editor.get,editor.get);const state=draft.state;const exam=initial.exam!;const visiblePart=displayedPart(exam,state.current_question,state.displayed_part).part_number;const confirm=useRef<HTMLDialogElement>(null);const [error,setError]=useState<string>();const [finishing,setFinishing]=useState(false);const finishPending=useRef(false);const [syncIssue,setSyncIssue]=useState(()=>editor.get().status.startsWith("Offline"));const [navigation,setNavigation]=useState(0);const count=Object.values(draft.answers).filter(v=>v.trim()).length;
 useEffect(()=>{const leave=(e:BeforeUnloadEvent)=>{if(editor.hasUnsaved()){e.preventDefault();e.returnValue="";}};const online=()=>{void editor.flush().catch(()=>{});};const hidden=()=>{if(document.hidden)online();};window.addEventListener("beforeunload",leave);window.addEventListener("online",online);document.addEventListener("visibilitychange",hidden);window.addEventListener("pagehide",online);return()=>{window.removeEventListener("beforeunload",leave);window.removeEventListener("online",online);document.removeEventListener("visibilitychange",hidden);window.removeEventListener("pagehide",online);};},[editor]);
 useEffect(()=>editor.subscribe(()=>{const status=editor.get().status;if(status.startsWith("Offline"))setSyncIssue(true);else if(status==="All changes saved")setSyncIssue(false);}),[editor]);
 async function finish(){if(finishPending.current)return;finishPending.current=true;setFinishing(true);setError(undefined);try{await editor.submit();router.push(`/listening/attempts/${initial.id}/results`);}catch(err){setError(message(err));}finally{finishPending.current=false;setFinishing(false);}}
 const notice=!draft.storage?"Your answers couldn't be saved on this device":draft.conflict?"Conflict detected":draft.otherTab?"Open in another tab · Read only":draft.status.startsWith("Submission not confirmed")?"Submission not confirmed":finishing?"Finishing…":error|| (syncIssue?(draft.localSaving?"Couldn't sync your answers — saving on this device…":typeof navigator!=="undefined"&&!navigator.onLine?"Offline — answers saved on this device":"Couldn't sync your answers — saved on this device"):draft.status.startsWith("Submit rejected")?"Submit rejected — your answers are retained. Edit or retry Finish.":"");
 const lastQuestions=useRef(new Map<number,number>());
 function viewPart(p:number){lastQuestions.current.set(visiblePart,state.current_question);go(lastQuestions.current.get(p)||(p-1)*10+1);}
 function go(n:number){setNavigation(v=>v+1);editor.changeState({displayed_part:Math.ceil(n/10),current_question:n});}
 return <main id="main" className={`${s.workspace} ${w.workspace}`} data-exam-mode="compact"><div className={w.topbar}><div className={`${s.examHead} ${w.examHead}`}><Link href="/listening" onNavigate={e=>{if(editor.hasUnsaved()){e.preventDefault();void editor.flush().then(()=>{if(!editor.hasUnsaved())router.push("/listening");}).catch(()=>{});}}}>← Library</Link><span className={w.examIdentity}>Cambridge {exam.book} · Test {exam.printed_test_number}</span>
 <WorkspaceNavigator placement="header" navigation={navigation} current={state.current_question} onGo={go}
 questions={Array.from({length:40},(_,i)=>{const number=i+1,answered=!!draft.answers[`${exam.exam_id}-q${String(number).padStart(2,"0")}`]?.trim();return {number,answered,title:answered?"Answered":"Unanswered"};})}
 description={`${count}/40 answered`} legend="Green: answered"
/>
 <button type="button" className={w.headerFinish} onClick={()=>confirm.current?.showModal()} disabled={finishing||!draft.ready||!draft.storage||draft.otherTab||!!draft.conflict}>{finishing?"Finishing…":draft.submitting?"Retry Finish":"Finish"}</button></div>
 <div className={w.audio}><Player compact uid={uid} attemptId={initial.id} examId={exam.exam_id} initialPart={state.audio_part} position={state.playback_seconds} visiblePart={visiblePart} onVisiblePart={viewPart} progress={editor.audioProgress} onCheckpoint={(p,seconds)=>editor.changeState({audio_part:p,playback_seconds:seconds})} onPart={p=>go((p-1)*10+1)}/></div></div>
 {notice&&<aside className={w.examNotice} role={finishing?"status":"alert"}><p>{notice}</p>
 {!draft.storage?<button type="button" onClick={()=>void editor.retryStorage().catch(()=>{})}>Retry device save</button>:draft.conflict?(draft.conflict.status==="submitted"?<Link href={`/listening/attempts/${initial.id}/results`}>View finished result</Link>:<><button type="button" onClick={()=>editor.resolve(true)}>Keep my local answers</button><button type="button" onClick={()=>editor.resolve(false)}>Use server answers</button></>):syncIssue&&!draft.submitting?<button type="button" onClick={()=>void editor.flush().catch(()=>{})}>Retry save</button>:null}
 {editor.canReturnToTest()&&<button type="button" onClick={()=>void editor.returnToTest()}>Return to test</button>}</aside>}

 <WorkspaceQuestions contentHash={initial.content_hash} exam={exam} part={visiblePart} current={state.current_question} navigation={navigation} uid={uid} id={initial.id} answers={draft.answers} onAnswer={(q,v)=>editor.changeAnswer(q,v)} onFocus={n=>{if(editor.get().state.current_question!==n)editor.changeState({current_question:n});}} disabled={!draft.ready||!draft.storage||draft.otherTab||draft.submitting||!!draft.conflict}/>


 <dialog className={s.finishDialog} ref={confirm} aria-labelledby="listening-finish-title"><h2 id="listening-finish-title">Finish this practice?</h2><p>{40-count} unanswered questions. Your saved answers will become read-only.</p><button type="button" onClick={()=>confirm.current?.close()}>Keep practising</button><button className={s.primary} type="button" disabled={finishing||!draft.storage||!!draft.conflict} onClick={()=>{confirm.current?.close();void finish();}}>Finish and view results</button></dialog></main>;
}
function Records({result,uid,onRetry}:{result:Result;uid:string;onRetry:()=>void}){
 const router=useRouter();
 // Only complete, internally consistent server verdicts may produce summary counts.
 const confirmed=result.total_questions===40&&result.graded_count===40&&Number.isInteger(result.correct_count)&&result.correct_count!==null&&result.correct_count>=0&&result.correct_count<=40&&result.questions.length===40&&new Set(result.questions.map(q=>q.question_id)).size===40&&result.questions.every(q=>typeof q.correct==="boolean"&&!q.grading_issue)&&result.questions.filter(q=>q.correct).length===result.correct_count;
 const band=confirmed&&result.band_table_version?result.estimated_band:null;
 const exam=result.exam!;
 return <ResultPage><ResultCard title={`Cambridge ${exam.book} · Test ${exam.printed_test_number}`}
 total={result.total_questions} onRetry={onRetry} band={band} correct={confirmed?result.correct_count:null} incorrect={confirmed?result.questions.filter(q=>q.correct===false&&q.user_answer.trim()).length:null} unanswered={confirmed?result.questions.filter(q=>!q.user_answer.trim()).length:null}
 status={!confirmed?"Grading not confirmed":band===null?(result.band_table_version?"Score below the available band range":"Band estimate unavailable for this attempt"):undefined}
 reviewHref={`/listening/attempts/${result.attempt_id}/review`}
 onRetake={async()=>{const next=await retakeTest("listening",uid,result.attempt_id,exam.exam_id,body=>api(uid)("/listening/attempts",undefined,{method:"POST",body}));router.push(`/listening/attempts/${next}`);}} /></ResultPage>;
}
