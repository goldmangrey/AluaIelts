"use client";
import {LuaMascot} from '@/components/lua-mascot';
import Link from 'next/link';
import {useSearchParams} from 'next/navigation';
import {useEffect,useRef,useState} from 'react';
import {useSession} from '@/features/auth/session';
import {AuthRequired} from '@/features/auth/guest-access';
import {PageShell} from '@/components/page-shell';
import {ListeningPage} from '@/features/listening/pages';
import {RecordsPage} from '@/features/reading/exam/records-page';
import {Player,type Moment} from '@/features/listening/player';
import {practiceApi,dateLabel,type Module} from './api';
import s from './practice.module.css';
import ui from './mistakes.module.css';

type Page<T>={items:T[];total:number;page:number;limit:number};
type SavedReview={what_happened?:string;why?:string;next_time?:string;evidence?:{available:boolean;part:number;clip_start:number|null;clip_end:number|null};review?:Record<string,unknown>};
type Mistake={module:Module;attempt_id:string;item_key:string;title:string;number:string|null;category:string|null;completed_at:string|null;answer:string|null;correct_answer:string|null;feedback:Record<string,unknown>|null;reviewed:boolean;review_key:string|null;has_saved_review:boolean;saved_review:SavedReview|null;href:string};

function human(v:string){return v.replace(/_/g,' ').replace(/^./,c=>c.toUpperCase());}
function listDate(value:string){return new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Almaty',day:'numeric',month:'short',year:'numeric'}).format(new Date(value));}
function listTitle(m:Mistake){return `${m.title}${m.number?` · Question ${m.number}`:''}`;}
function listHref(m:Mistake,page:number){return `/practice/mistakes?${new URLSearchParams({page:String(page),skill:m.module,attempt:m.attempt_id,item:m.item_key})}`;}
function listBack(page:number){return page>1?`/practice/mistakes?page=${page}`:'/practice/mistakes';}

export function MistakesPage(){
 const session=useSession(),params=useSearchParams();
 const value=Number(params.get('page')??1),page=Number.isSafeInteger(value)&&value>0?value:1;
 if(session.status!=='ready'||!session.user)return <PageShell>{session.status==='loading'?<p role="status">Loading your practice…</p>:<AuthRequired title="Turn your mistakes into progress." description="Sign in to revisit your answers and saved explanations."/>}</PageShell>;
 return <Mistakes key={session.user.uid} uid={session.user.uid} page={page} selected={{module:params.get('skill'),attempt:params.get('attempt'),item:params.get('item')}}/>;
}
function Mistakes({uid,page,selected}:{uid:string;page:number;selected:{module:string|null;attempt:string|null;item:string|null}}){
 const [state,setState]=useState<{key:string;data?:Page<Mistake>;error?:boolean}>(),[revision,setRevision]=useState(0);
 const key=`${uid}:${page}:${selected.item??''}:${revision}`;
 useEffect(()=>{const abort=new AbortController();void practiceApi(uid)(`/practice/mistakes?order=newest&page=${page}&include_reviews=false`,abort.signal).then(data=>{if(!abort.signal.aborted)setState({key,data:data as Page<Mistake>});}).catch(()=>{if(!abort.signal.aborted)setState({key,error:true});});return()=>abort.abort();},[uid,page,key]);
 const data=state?.key===key?state.data:undefined,error=state?.key===key&&state.error;
 const retry=()=>setRevision(n=>n+1);
 const item=data?.items.find(m=>m.module===selected.module&&m.attempt_id===selected.attempt&&m.item_key===selected.item);
 if(selected.item&&item){
   if((item.module==='listening'||item.module==='reading')&&item.review_key)return <div className={ui.detail}>
     <ReviewActions key={`${item.module}:${item.attempt_id}:${item.item_key}`} uid={uid} item={item} back={listBack(page)}/>
     <div className={ui.reviewHost}>{item.module==='listening'?<ListeningPage kind="review" id={item.attempt_id} reviewQuestion={Number(item.review_key)}/>:<RecordsPage id={item.attempt_id} review reviewQuestionId={item.review_key}/>}</div>
   </div>;
   return <PageShell backHref={listBack(page)} backLabel="My Mistakes"><section className={s.shell}><MistakeCard key={`${item.module}:${item.attempt_id}:${item.item_key}`} uid={uid} item={item} onChanged={()=>{}}/></section></PageShell>;
 }
 return <div className={ui.page}><PageShell backHref={selected.item?listBack(page):'/'} backLabel={selected.item?'My Mistakes':'All sections'}><section className={ui.shell}>
   <h1>My Mistakes</h1>
   {error?<p role="alert">Could not load your mistakes. <button type="button" onClick={retry}>Retry</button></p>:!data?<p className={ui.count} role="status">Loading your mistakes…</p>:selected.item?<p>This mistake is not on this page. <Link href={listBack(page)}>Back to My Mistakes</Link></p>:<>
     <p className={ui.count}>{data.total} {data.total===1?'item':'items'}</p>
     {data.items.length?<div className={ui.list}>{data.items.map(m=><Link key={`${m.module}:${m.attempt_id}:${m.item_key}`} className={ui.row} href={listHref(m,data.page)} prefetch={false}>
       <span className={`${ui.badge} ${ui[m.module]}`}>{m.module}</span>
       <div className={ui.content}><h2>{listTitle(m)}</h2><p>{[m.completed_at?listDate(m.completed_at):'Date unavailable',m.category?human(m.category):null].filter(Boolean).join(' · ')}</p></div>
       <span className={ui.chevron} aria-hidden="true"/>
     </Link>)}</div>:<p className={ui.empty}>No saved mistakes here yet.</p>}
     {data.total>data.limit&&<nav className={ui.pagination} aria-label="Mistake pages">
       {data.page>1?<Link href={listBack(data.page-1)}>Previous</Link>:<span>Previous</span>}<span>{data.page} / {Math.ceil(data.total/data.limit)}</span>{data.page*data.limit<data.total?<Link href={listBack(data.page+1)}>Next</Link>:<span>Next</span>}
     </nav>}
   </>}
 </section></PageShell></div>;
}
function useReviewedCompanion(){
 const [wink,setWink]=useState(false),timer=useRef<ReturnType<typeof setTimeout>|undefined>(undefined);
 useEffect(()=>()=>clearTimeout(timer.current),[]);
 return {wink,celebrate:()=>{clearTimeout(timer.current);setWink(true);timer.current=setTimeout(()=>setWink(false),2200);}};
}
function ReviewActions({uid,item,back}:{uid:string;item:Mistake;back:string}){
 const companion=useReviewedCompanion();
 const [reviewed,setReviewed]=useState(item.reviewed),[busy,setBusy]=useState(false),[error,setError]=useState(false),lock=useRef(false);
 async function mark(){if(lock.current)return;lock.current=true;setBusy(true);setError(false);try{await practiceApi(uid)('/practice/mistakes/state',undefined,{method:'PUT',body:{module:item.module,attempt_id:item.attempt_id,item_key:item.item_key,reviewed:!reviewed}});if(!reviewed)companion.celebrate();setReviewed(v=>!v);}catch{setError(true);}finally{lock.current=false;setBusy(false);}}
 return <div className={ui.reviewBar}><Link href={back}>← My Mistakes</Link><LuaMascot emotion={companion.wink?"wink":"support"} context="detail" size={56}/><div><span role="status">{reviewed?'Reviewed':'To Review'}</span><button type="button" disabled={busy} onClick={()=>void mark()}>{busy?'Saving…':reviewed?'Return to To Review':'Mark as reviewed'}</button></div>{error&&<p role="alert">Could not save review status. Please try again.</p>}</div>;
}

function feedbackText(value:unknown):string[]{
 if(!value||typeof value!=='object')return [];const record=value as Record<string,unknown>;
 return ['what_happened','why_user_answer_wrong','why_correct_answer_works','why','next_time','ielts_tip','explanation_ru','necessity'].flatMap(key=>typeof record[key]==='string'&&record[key].trim()?[record[key] as string]:[]);
}

function MistakeCard({uid,item:m,onChanged}:{uid:string;item:Mistake;onChanged:()=>void}){
 const companion=useReviewedCompanion();
 const [reviewed,setReviewed]=useState(m.reviewed),[busy,setBusy]=useState(false),[error,setError]=useState(false),[open,setOpen]=useState(false),[moment,setMoment]=useState<Moment>(),request=useRef(0),lock=useRef(false);
 async function mark(){if(lock.current)return;lock.current=true;setBusy(true);setError(false);try{await practiceApi(uid)('/practice/mistakes/state',undefined,{method:'PUT',body:{module:m.module,attempt_id:m.attempt_id,item_key:m.item_key,reviewed:!reviewed}});if(!reviewed)companion.celebrate();setReviewed(!reviewed);onChanged();}catch{setError(true);}finally{lock.current=false;setBusy(false);}}
 const [saved,setSaved]=useState(m.saved_review),[loading,setLoading]=useState(false),[loadError,setLoadError]=useState(false);
 async function show(){if(open){setOpen(false);return;}setOpen(true);if(saved||!m.has_saved_review||!m.review_key)return;setLoading(true);setLoadError(false);try{const value=await practiceApi(uid)(`/practice/reviews/${m.module}/${m.attempt_id}?question=${encodeURIComponent(m.review_key)}`) as {response:SavedReview|null};setSaved(value.response);}catch{setLoadError(true);}finally{setLoading(false);}}
 const explanation=saved?.review??saved??m.feedback,evidence=saved?.evidence;
 function play(loop:boolean){if(!evidence?.available||evidence.clip_start===null||evidence.clip_end===null)return;setMoment({request:++request.current,part:evidence.part,start:evidence.clip_start,end:evidence.clip_end,loop});}
 return <article className={s.mistakeCard}><LuaMascot emotion={companion.wink?"wink":"support"} context="detail" size={64}/><div className={s.mistakeHeading}><span className={`${s.badge} ${s[m.module]}`}>{m.module}</span><span className={s.reviewBadge} data-reviewed={reviewed}>{reviewed?'Reviewed':'To Review'}</span></div><h2>{m.title}{m.number?` · Question ${m.number}`:''}</h2><p className={s.muted}>{m.completed_at?dateLabel(m.completed_at):'Date unavailable'}{m.category?` · ${human(m.category)}`:''}</p><p className={s.muted}>{m.module==='writing'?'Saved assessment feedback':`AI explanation: ${m.has_saved_review?'Saved':'Not generated'}`}</p>
 {m.answer&&<p><span className={s.muted}>{m.module==='writing'?'Original text':'Your answer'}:</span> {m.answer}</p>}{m.correct_answer&&<p><span className={s.muted}>{m.module==='writing'?'Suggested correction':'Correct answer'}:</span> <strong>{m.correct_answer}</strong></p>}
 {m.feedback&&feedbackText(m.feedback).map((text,i)=><p key={i}>{text}</p>)}{m.module==='writing'&&Array.isArray(m.feedback?.assessment_criteria)&&<details><summary>Saved IELTS criteria</summary>{(m.feedback.assessment_criteria as {name:string;band:number;rationale_en?:string;descriptor_fit?:string}[]).map(c=><p key={c.name}><strong>{human(c.name)} · {c.band.toFixed(1)}</strong><br/>{c.descriptor_fit??c.rationale_en}</p>)}</details>}
 <div className={s.mistakeActions}><Link href={m.href}>View original attempt →</Link><button type="button" disabled={loading} onClick={()=>void show()} aria-expanded={open}>Review explanation</button><button type="button" disabled={busy} onClick={()=>void mark()}>{busy?'Saving…':reviewed?'Mark as needs practice':'Mark as reviewed'}</button></div>
 {error&&<p role="alert">Could not save review status. Please retry.</p>}
 {open&&<section className={s.savedExplanation} aria-label="Saved explanation">{loading?<p role="status">Loading saved explanation…</p>:loadError?<p role="alert">Could not load the saved explanation. Close and retry.</p>:explanation?<><small>Saved AI Review · no new generation</small>{feedbackText(explanation).map((text,i)=><p key={i}>{text}</p>)}{m.module==='listening'&&evidence?.available&&evidence.clip_start!==null&&evidence.clip_end!==null&&<div className={s.mistakeActions}><button type="button" onClick={()=>play(false)}>Play Moment</button><button type="button" onClick={()=>play(true)}>Loop Moment</button></div>}</>:<p>No saved AI explanation for this question. You can request one explicitly in the original review.</p>}</section>}
 {moment&&<Player uid={uid} attemptId={m.attempt_id} examId={m.item_key.replace(/-q\d+$/,'')} initialPart={moment.part} position={moment.start} visiblePart={moment.part} onVisiblePart={()=>{}} onCheckpoint={()=>{}} onPart={()=>{}} moment={moment} onMomentStop={()=>setMoment(undefined)}/>}</article>;
}
