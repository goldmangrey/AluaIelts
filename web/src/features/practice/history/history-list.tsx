'use client';

import {LuaMascot} from '@/components/lua-mascot';
import Link from 'next/link';
import {useEffect, useState} from 'react';
import {practiceApi, dateLabel, type HistoryItem, type Module} from './api';
import ui from './mistakes.module.css';
import s from './history-list.module.css';

type Draft = {id:string;module:Module;title:string;position:string;answered:number;href:string;updated_at:string|null};
type Page<T> = {items:T[];total:number;page:number;limit:number};
type Loaded = {key:string;completed?:Page<HistoryItem>;drafts?:Page<Draft>;error?:boolean};

function score(item:HistoryItem){
  if((item.module==='reading'||item.module==='listening')&&item.correct_count!==null&&item.total_questions!==null)return `${item.correct_count}/${item.total_questions}`;
  return item.estimated_band!==null?`Band ${item.estimated_band.toFixed(1)}`:null;
}

export function HistoryList({uid,day}:{uid:string;day?:string}){
  const [status,setStatus]=useState<'completed'|'progress'>('completed');
  const [page,setPage]=useState(1),[revision,setRevision]=useState(0),[loaded,setLoaded]=useState<Loaded>();
  const key=`${uid}:${status}:${page}:${day??''}:${revision}`;
  useEffect(()=>{
    const abort=new AbortController();
    const path:`/${string}`=status==='completed'?`/practice/history?module=all&order=desc&page=${page}${day?`&day=${encodeURIComponent(day)}`:''}`:`/practice/drafts?page=${page}`;
    void practiceApi(uid)(path,abort.signal).then(value=>{
      if(!abort.signal.aborted)setLoaded(status==='completed'?{key,completed:value as Page<HistoryItem>}:{key,drafts:value as Page<Draft>});
    }).catch(()=>{if(!abort.signal.aborted)setLoaded({key,error:true});});
    return()=>abort.abort();
  },[uid,status,page,day,key]);
  const state=loaded?.key===key?loaded:undefined,data=state?.completed??state?.drafts;
  return <>
    <p className={ui.count} role="status">{data?`${data.total} ${data.total===1?'session':'sessions'}`:state?.error?'History unavailable':'Loading your history…'}</p>
    <div className={s.tabs} role="group" aria-label="Practice status">
      {(['completed','progress'] as const).map(value=><button key={value} type="button" aria-pressed={status===value} onClick={()=>{setStatus(value);setPage(1);}}>{value==='completed'?'Completed':'In Progress'}</button>)}
    </div>
    {day&&status==='completed'&&<p className={s.day}>Completed on {day} · <Link href="/practice/history">Clear date filter</Link></p>}
    {state?.error?<p role="alert">Could not load your history. <button type="button" onClick={()=>setRevision(n=>n+1)}>Retry</button></p>:data&&<>
      {!data.items.length?<p className={ui.empty}>{status==='progress'&&<LuaMascot emotion="sleepy" size={88}/>} {status==='completed'?'No completed sessions yet. Your results will appear here.':'No unfinished sessions. Your saved practice will appear here.'}</p>:<div className={`${ui.list} ${s.list}`}>
        {state?.completed?.items.map(item=><Link key={`${item.module}:${item.id}`} className={ui.row} href={`/practice/history/${item.id}`} prefetch={false}>
          <span className={`${ui.badge} ${ui[item.module]}`}>{item.module}</span>
          <div className={`${ui.content} ${s.details}`}><div><h2>{item.title}</h2>{(item.completed_at||item.saved_explanations>0)&&<p>{[item.completed_at?dateLabel(item.completed_at):null,item.saved_explanations>0?`${item.saved_explanations} AI ${item.saved_explanations===1?'explanation':'explanations'}`:null].filter(Boolean).join(' · ')}</p>}</div>{score(item)&&<span className={s.score}>{score(item)}</span>}</div>
          <span className={ui.chevron} aria-hidden="true"/>
        </Link>)}
        {state?.drafts?.items.map(item=><Link key={`${item.module}:${item.id}`} className={ui.row} href={item.href} prefetch={false}>
          <span className={`${ui.badge} ${ui[item.module]}`}>{item.module}</span>
          <div className={ui.content}><h2>{item.title}</h2><p>{[item.module==='writing'?item.position:`${item.answered} answered${item.position?` · ${item.position}`:''}`,item.updated_at?`Saved ${dateLabel(item.updated_at)}`:null].filter(Boolean).join(' · ')}</p></div>
          <span className={ui.chevron} aria-hidden="true"/>
        </Link>)}
      </div>}
      {data.total>data.limit&&<nav className={`${ui.pagination} ${s.pagination}`} aria-label="History pages">
        <button type="button" disabled={data.page<=1} onClick={()=>setPage(data.page-1)}>Previous</button><span>{data.page} / {Math.ceil(data.total/data.limit)}</span><button type="button" disabled={data.page*data.limit>=data.total} onClick={()=>setPage(data.page+1)}>Next</button>
      </nav>}
    </>}
  </>;
}
