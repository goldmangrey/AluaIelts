'use client';
import {AuthRequired} from '@/features/auth/guest-access';
import {useEffect,useMemo,useState} from 'react';
import {PageShell} from '@/components/page-shell';
import {StatusPanel} from '@/components/status-panel';
import {useSession} from '@/features/auth/session';
import {ListeningPage} from '@/features/listening/pages';
import {RecordsPage} from '@/features/reading/exam/records-page';
import {WritingPage} from '@/features/writing/pages';
import {practiceApi,dateLabel,type Module} from './api';
import s from './practice.module.css';
import {HistoryList} from './history-list';
import ui from './mistakes.module.css';

function Gate({loading=false}:{loading?:boolean}){return loading?<p role="status">Loading your practice…</p>:<AuthRequired title="Your practice history, all in one place."/>;}
export function HistoryPage({day}:{day?:string}){
 const session=useSession();
 return <div className={ui.page}><PageShell><section className={ui.shell}><h1>My Practice History</h1>{session.status==='ready'&&session.user?<HistoryList key={`${session.user.uid}:${session.generation}:${day??''}`} uid={session.user.uid} day={day}/>:<Gate loading={session.status==='loading'}/>}</section></PageShell></div>;
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
