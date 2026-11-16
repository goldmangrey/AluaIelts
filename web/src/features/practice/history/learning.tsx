'use client';
import {LuaMascot} from '@/components/lua-mascot';
import {AuthRequired} from '@/features/auth/guest-access';
import Link from 'next/link';
import {useEffect,useState,type ReactNode} from 'react';
import {useSession} from '@/features/auth/session';
import {PageShell} from '@/components/page-shell';
import {practiceApi,dateLabel,type Module} from './api';
import s from './practice.module.css';
import {ContinuePracticeCard} from './continue-practice-card';

type Draft={id:string;module:Module;title:string;position:string;answered:number;href:string;updated_at:string;deadline_at:string|null};
type Page<T>={items:T[];total:number;page:number;limit:number};
function useResource<T>(uid:string|undefined,path:string){
 const [state,setState]=useState<{key:string;data?:T;error?:boolean}>(),[revision,reload]=useState(0);const key=`${uid}:${path}:${revision}`;
 useEffect(()=>{if(!uid)return;const abort=new AbortController();void practiceApi(uid)(path as `/${string}`,abort.signal).then(data=>{if(!abort.signal.aborted)setState({key,data:data as T});}).catch(()=>{if(!abort.signal.aborted)setState({key,error:true});});return()=>abort.abort();},[uid,path,key]);
 return {data:state?.key===key?state.data:undefined,error:state?.key===key&&state.error,reload:()=>reload(n=>n+1)};
}
function Owned({children}:{children:(uid:string)=>ReactNode}){const session=useSession();return session.status==='ready'&&session.user?<>{children(session.user.uid)}</>:<p>{session.status==='loading'?'Loading your practice…':<Link href="/login?next=%2Fpractice%2Fhistory">Log in to view your own practice.</Link>}</p>;}
function Trouble({retry}:{retry:()=>void}){return <p role="alert">Could not load your practice. <button className="button secondary" onClick={retry}>Retry</button></p>;}
export function ContinuePractice(){
 const session=useSession(),uid=session.status==='ready'?session.user?.uid:undefined;
 const {data}=useResource<Page<Draft>>(uid,'/practice/drafts?limit=1');
 if(!data?.items?.length)return null;const d=data.items[0]!;
 return <ContinuePracticeCard draft={d} otherSessions={data.total-1}/>;
}
export function ContinuePage(){const session=useSession();if(session.status!=='ready')return <PageShell>{session.status==='loading'?<p role="status">Loading your practice…</p>:<AuthRequired/>}</PageShell>;return <PageShell><section className={s.shell}><p className={s.eyebrow}>YOUR SAVED PRACTICE</p><h1>Continue Practice</h1><Owned>{uid=><Drafts key={uid} uid={uid}/>}</Owned></section></PageShell>;}
export function Drafts({uid}:{uid:string}){
 const [page,setPage]=useState(1),{data,error,reload}=useResource<Page<Draft>>(uid,`/practice/drafts?page=${page}`);
 return error?<Trouble retry={reload}/>:!data?<p role="status">Loading unfinished sessions…</p>:<>{!data.items.length?<p className={s.empty}>No unfinished sessions. <Link href="/">Choose a skill to practise.</Link></p>:<><LuaMascot emotion="happy" size={72}/><div className={s.historyList}>{data.items.map(d=><article className={s.historyRow} key={`${d.module}:${d.id}`}><div><span className={`${s.badge} ${s[d.module]}`}>{d.module}</span><h2>{d.title}</h2><p>{d.position}{d.module!=='writing'?` · ${d.answered} answered`:''}</p><p className={s.muted}>Saved {dateLabel(d.updated_at)}</p>{d.deadline_at&&<small>Original timer continues · Deadline {dateLabel(d.deadline_at)}</small>}</div><Link className="button secondary" href={d.href}>Continue practice →</Link></article>)}</div></>}<Pager page={page} total={data.total} limit={data.limit} setPage={setPage}/><p className={s.muted}>Speaking currently has no unfinished recording or text draft to restore. Completed self-directed practice remains in History.</p></>;
}
function Pager({page,total,limit,setPage}:{page:number;total:number;limit:number;setPage:(n:number)=>void}){return total>limit?<nav className={s.pagination} aria-label="Practice pages"><button className="button secondary" disabled={page===1} onClick={()=>setPage(page-1)}>Previous</button><span>{page} / {Math.ceil(total/limit)}</span><button className="button secondary" disabled={page*limit>=total} onClick={()=>setPage(page+1)}>Next</button></nav>:null;}
export {LearningProgress} from './profile-analytics';
