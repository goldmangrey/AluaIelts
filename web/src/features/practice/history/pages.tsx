'use client';
import {AuthRequired} from '@/features/auth/guest-access';
import Link from 'next/link';
import {useEffect,useMemo,useState} from 'react';
import {PageShell} from '@/components/page-shell';
import {StatusPanel} from '@/components/status-panel';
import {useSession} from '@/features/auth/session';
import {ListeningPage} from '@/features/listening/pages';
import {RecordsPage} from '@/features/reading/exam/records-page';
import {WritingPage} from '@/features/writing/pages';
import {practiceApi,dateLabel,type HistoryData,type Module} from './api';
import s from './practice.module.css';
import {Drafts} from './learning';

function Gate({loading=false}:{loading?:boolean}){return loading?<p role="status">Loading your practice…</p>:<AuthRequired title="Your practice history, all in one place."/>;}
export function HistoryPage({day}:{day?:string}){
 const session=useSession();if(session.status!=='ready')return <PageShell><Gate loading={session.status==='loading'}/></PageShell>;return <PageShell><section className={s.shell}><p className={s.eyebrow}>YOUR LEARNING RECORD</p><h1>My Practice History</h1><p className={s.muted}>Every session is a step forward. Revisit your results and saved AI reviews.</p>{session.status==='ready'&&session.user?<HistoryList key={`${session.user.uid}:${session.generation}`} uid={session.user.uid} day={day}/>:<Gate/>}</section></PageShell>;
}
function HistoryList({uid,day}:{uid:string;day?:string}){
 const [status,setStatus]=useState('completed');
 const api=useMemo(()=>practiceApi(uid),[uid]);const [module,setModule]=useState('all'),[order,setOrder]=useState('desc'),[page,setPage]=useState(1),[reload,setReload]=useState(0);
 const [loaded,setLoaded]=useState<{key:string;data:HistoryData}>(),[error,setError]=useState('');const key=`${module}:${order}:${page}:${reload}:${day}:${status}`;
 useEffect(()=>{if(status!=='completed')return;const abort=new AbortController();void api(`/practice/history?module=${module}&page=${page}&order=${order}${day?`&day=${encodeURIComponent(day)}`:''}`,abort.signal).then(value=>{setLoaded({key,data:value as HistoryData});setError('');}).catch(()=>{if(!abort.signal.aborted)setError('Your history could not load. Please try again.');});return()=>abort.abort();},[api,module,page,order,key,day,status]);
 const data=loaded?.key===key?loaded.data:null;
 const tabs=<div className={s.filters} role="group" aria-label="Practice status"><button className="button secondary" aria-pressed={status==='completed'} onClick={()=>setStatus('completed')}>Completed</button><button className="button secondary" aria-pressed={status==='progress'} onClick={()=>setStatus('progress')}>In Progress</button></div>;
 if(status==='progress')return <>{tabs}<Drafts uid={uid}/></>;
 return <>{tabs}{day&&<p>Completed on {day} · Asia/Almaty · <Link href="/practice/history">Clear date filter</Link></p>}<div className={s.filters}><label>Practice type<select value={module} onChange={e=>{setModule(e.target.value);setPage(1);}}>{['all','listening','reading','writing','speaking'].map(v=><option key={v} value={v}>{v==='all'?'All practice':v.charAt(0).toUpperCase()+v.slice(1)}</option>)}</select></label><label>Sort by date<select value={order} onChange={e=>{setOrder(e.target.value);setPage(1);}}><option value="desc">Newest first</option><option value="asc">Oldest first</option></select></label><Link href="/profile">View activity →</Link></div>
 {error?<div role="alert"><p>{error}</p><button className="button secondary" onClick={()=>setReload(n=>n+1)}>Retry</button></div>:!data?<p role="status">Loading your history…</p>:!data.items.length?<div className={s.empty}><h2>Your story starts with a session</h2><p>Completed practice will appear here. Choose a skill and take your first step.</p><Link className="button" href="/">Choose your practice</Link></div>:<>
 <p className={s.muted}>{data.total} completed {data.total===1?'session':'sessions'}</p><div className={s.historyList}>{data.items.map(item=><article className={s.historyRow} key={`${item.module}:${item.id}`}><div><span className={`${s.badge} ${s[item.module]}`}>{item.module}</span><h2>{item.title}</h2><p className={s.muted}>{item.completed_at?dateLabel(item.completed_at):'Date unavailable'}{item.completed_at?' · Asia/Almaty':''}</p><div className={s.historyMeta}>{item.correct_count!==null?<strong className={s.historyScore}>{item.correct_count}/{item.total_questions}</strong>:null}{item.estimated_band!==null&&<strong className={s.historyScore}>AI Band Estimate {item.estimated_band.toFixed(1)}</strong>}</div>
 {item.correct_count!==null?<p className={s.resultDetail}>{item.correct_count} correct{item.incorrect_count!==null?` · ${item.incorrect_count} incorrect`:''}{item.unanswered_count!==null?` · ${item.unanswered_count} unanswered`:''}</p>:item.estimated_band===null&&<p className={s.resultDetail}>{item.module==='speaking'?'Self-directed speaking practice':item.module==='writing'?'Submitted · assessment not saved yet':'Completed · score unavailable'}</p>}
 <small className={s.muted}>{item.module==='writing'&&item.ai_status==='saved'?'Saved AI assessment':`${item.saved_explanations} saved AI ${item.saved_explanations===1?'explanation':'explanations'}`} · AI Review: {item.ai_status==='saved'?'Saved':item.ai_status==='pending'?'In progress':item.ai_status==='not_available'?'Unavailable':['not_requested','idle'].includes(item.ai_status)?'Not generated':'Unavailable'}</small></div><Link className="button secondary" href={`/practice/history/${item.id}`}>View Results →</Link></article>)}</div>
 <nav className={s.pagination} aria-label="History pages"><button className="button secondary" disabled={data.page===1} onClick={()=>setPage(data.page-1)}>Previous</button><span>{data.page} / {Math.ceil(data.total/data.limit)}</span><button className="button secondary" disabled={data.page*data.limit>=data.total} onClick={()=>setPage(data.page+1)}>Next</button></nav></>}
 </>;
}
interface Detail{module:Module;task?:{prompt:string;part?:number;bullets?:string[];closing?:string};completed_at:string|null}
export function HistoryDetail({attemptId}:{attemptId:string}){
 const session=useSession();return session.status==='ready'&&session.user?<OwnedDetail key={`${session.user.uid}:${session.generation}:${attemptId}`} uid={session.user.uid} id={attemptId}/>:<PageShell><Gate loading={session.status==='loading'}/></PageShell>;
}
function OwnedDetail({uid,id}:{uid:string;id:string}){
 const api=useMemo(()=>practiceApi(uid),[uid]);const [detail,setDetail]=useState<Detail>(),[error,setError]=useState(false);
 useEffect(()=>{const abort=new AbortController();void api(`/practice/history/${id}?include_reviews=false`,abort.signal).then(v=>setDetail(v as Detail)).catch(()=>{if(!abort.signal.aborted)setError(true);});return()=>abort.abort();},[api,id]);
 if(error)return <PageShell backHref="/practice/history" backLabel="My Practice History"><StatusPanel title="This result is unavailable">It may not exist or may belong to another account.</StatusPanel></PageShell>;
 if(!detail)return <PageShell><p role="status">Loading saved result…</p></PageShell>;
 // View Results opens the saved score; its Review action retains the rich question UI.
 if(detail.module==='listening')return <ListeningPage kind="result" id={id}/>;
 if(detail.module==='reading')return <RecordsPage id={id}/>;
 if(detail.module==='writing')return <WritingPage kind="result" id={id}/>;
 return <PageShell backHref="/practice/history" backLabel="My Practice History"><section className={s.shell}><p className={s.eyebrow}>SPEAKING · SELF-DIRECTED PRACTICE</p><h1>Saved speaking session</h1>{detail.completed_at&&<p className={s.muted}>{dateLabel(detail.completed_at)}</p>}<article className={s.panel}><h2>{detail.task?.prompt}</h2>{detail.task?.bullets&&<ul>{detail.task.bullets.map(b=><li key={b}>{b}</li>)}</ul>}{detail.task?.closing&&<p>{detail.task.closing}</p>}<p className={s.muted}>This session records completed self-directed practice. No recording or AI assessment was produced.</p></article></section></PageShell>;
}
