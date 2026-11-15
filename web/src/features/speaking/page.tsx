'use client';
import {GuestCatalog} from '@/features/guest/catalog';
import Link from 'next/link';
import {useEffect,useMemo,useRef,useState,useSyncExternalStore} from 'react';
import {SiteHeader} from '@/components/site-header';
import {useSession} from '@/features/auth/session';
import raw from './content.json';
import {type Content,partNames,originLabel} from './model';
import {progressStore} from './progress';
import {practiceApi} from '@/features/practice/history/api';
import s from './speaking.module.css';
import u from '@/features/practice/soft.module.css';
import {PracticeCard,PracticeHeader} from '@/features/practice/ui';
import {usePracticeLocation,navigatePractice as navigate} from '@/features/practice/location';
import {speakingTasks} from './navigation';
const data=raw as Content,byId=new Map(data.questions.map(q=>[q.id,q])),allowed=new Set(byId.keys()),byTopic=new Map(data.topics.map(t=>[t.id,t]));
const tasks=speakingTasks(data);
function Timer({seconds,label}:{seconds:number;label:string}){
 const [remaining,setRemaining]=useState(seconds),[running,setRunning]=useState(false),deadline=useRef(0);
 useEffect(()=>{if(!running)return;const tick=()=>{const next=Math.max(0,Math.ceil((deadline.current-Date.now())/1000));setRemaining(next);if(!next)setRunning(false);};const id=setInterval(tick,200);return()=>clearInterval(id);},[running]);
 function start(){deadline.current=Date.now()+remaining*1000;setRunning(true);}
 function pause(){setRemaining(Math.max(0,Math.ceil((deadline.current-Date.now())/1000)));setRunning(false);}
 return <section className={s.timer} aria-label={`${label} timer`}><div><h3>{label}</h3><output role="timer" aria-label={`${label} time remaining`}>{String(Math.floor(remaining/60)).padStart(2,'0')}:{String(remaining%60).padStart(2,'0')}</output></div><div className={s.timerActions}><button onClick={running?pause:start} disabled={!remaining}>{running?'Pause':'Start'}</button><button onClick={()=>{setRunning(false);setRemaining(seconds);}}>Reset</button></div>{remaining===0&&<p role="status">Time is up. Continue at your own pace.</p>}</section>;
}
function Sources({ids}:{ids:string[]}){const sources=data.sources.filter(v=>ids.includes(v.id));return <details className={s.sources}><summary>Sources & provenance</summary><p>These are independently written practice adaptations. Source links describe reported topics or sample material; they do not verify the wording of a live exam.</p>{sources.map(v=><a key={v.id} href={v.url} target="_blank" rel="noreferrer">{v.publisher} · {v.page_title} ↗</a>)}</details>;}
export function SpeakingPage(){
 const session=useSession(),uid=session.status==='ready'?session.user?.uid:undefined;
 const store=useMemo(()=>progressStore(uid,allowed),[uid]),practised=useSyncExternalStore(store.subscribe,store.get,store.server),params=usePracticeLocation();
 const topicId=params.get('topic'),qid=params.get('q'),legacyCue=params.get('cue'),legacyCard=params.get('card');
 const legacyQuestion=byId.get(qid??''),legacyId=params.get('set')??legacyCue??legacyCard??(legacyQuestion?(legacyQuestion.part===2?legacyQuestion.id:`${legacyQuestion.part===1?'interview':'discussion'}:${topicId??legacyQuestion.topic_ids[0]}`):undefined);
 const preferredTopic=topicId??byId.get(params.get('task')??legacyId??'')?.topic_ids[0];
 const task=tasks.find(t=>t.id===(params.get('task')??legacyId)&&(!preferredTopic||t.topicId===preferredTopic));
 const topic=byTopic.get(topicId??task?.topicId??''),topicTasks=tasks.filter(t=>t.topicId===topic?.id);
 const parts=task?[...new Set(task.questions.map(q=>q.part))].sort():[],requested=Number(params.get('part'));
 const activePart=parts.includes(requested)?requested:parts.includes(legacyQuestion?.part??0)?legacyQuestion!.part:parts[0];
 const queue=task?.questions.filter(q=>q.part===activePart)??[],index=Math.max(0,queue.findIndex(q=>q.id===qid)),q=queue[index];
 function openTask(id:string){navigate({topic:topic!.id,task:id})}
 function goQuestion(id:string,part=String(activePart)){navigate({topic:topic!.id,task:task!.id,part,q:id})}
 const [saving,setSaving]=useState(false),[saveError,setSaveError]=useState('');
 const completion=useRef<{qid:string;event:string}|null>(null),savingLock=useRef(false);
 async function complete(){
  if(!uid||!q||savingLock.current)return;savingLock.current=true;setSaving(true);setSaveError('');
  const event=completion.current?.qid===q.id?completion.current.event:crypto.randomUUID();completion.current={qid:q.id,event};
  try{await practiceApi(uid)('/practice/speaking/attempts',undefined,{method:'POST',body:{task_id:q.id,event_id:event}});if(!practised[q.id])store.toggle(q.id);completion.current=null;}
  catch{setSaveError('Could not confirm this session was saved. Retry is safe.');}
  finally{savingLock.current=false;setSaving(false);}
 }
 const publishedTopics=data.topics.filter(t=>data.questions.some(q=>q.topic_ids.includes(t.id))).sort((a,b)=>a.name_en.localeCompare(b.name_en));
 if(session.status==='signed_out')return <><SiteHeader/><main id="main"><GuestCatalog module="speaking"/></main></>;
 if(session.status==='loading')return <><SiteHeader/><main id="main"><p role="status">Loading Speaking…</p></main></>;
 return <><SiteHeader/><div className={u.page}><main id="main" className={`${u.shell} ${s.shell}`}>
 {task&&topic?<button className={u.back} onClick={()=>navigate({topic:topic.id})}>← {topic.name_en}</button>:topic?<button className={u.back} onClick={()=>navigate()}>← All topics</button>:<Link className={u.back} href="/">← All sections</Link>}
 <PracticeHeader title={task?'Speaking practice':topic?.name_en??'Speaking'} subtitle={task?'Speak freely. Take your time and develop your ideas.':topic?'Choose a speaking practice.':'Choose a topic and practise speaking at your own pace.'}/>
 {!topic&&!task?<div className={u.grid}>{publishedTopics.map(t=>{const count=tasks.filter(v=>v.topicId===t.id).length;return <PracticeCard key={t.id} category={t.main_category} title={t.name_en} meta={`${count} ${count===1?'practice':'practices'} available`} action="Explore topic" onClick={()=>navigate({topic:t.id})}/>})}</div>:!task?<><div className={u.grid}>{topicTasks.map((v,n)=>{const parts=[...new Set(v.questions.map(q=>q.part))].sort(),count=v.questions.filter(q=>practised[q.id]).length;return <PracticeCard key={v.id} number={n+1} title={v.title} meta={`Part${parts.length>1?'s':''} ${parts.join(' · ')} · ${v.questions.length} questions${v.partial?' · Partial sequence':''}`} action={count?'Continue practice':'Start practice'} onClick={()=>openTask(v.id)}>{count>0&&<span className={u.meta}>{count} / {v.questions.length} practised</span>}</PracticeCard>})}</div></>:q?<section className={s.practice} aria-label="Speaking practice question">
 {parts.length>1?<nav className={u.tabs} aria-label="Available speaking parts">{parts.map(p=><button key={p} aria-pressed={p===activePart} onClick={()=>goQuestion(task.questions.find(q=>q.part===p)!.id,String(p))}>Part {p}</button>)}</nav>:null}
 <div className={s.questionMeta}><span>{partNames[q.part]}</span><span>Question {index+1} of {queue.length}</span></div>
 <article className={`${s.question} ${q.part===2?s.cue:''}`} key={`question:${q.id}`}><p className={s.tag}>{q.part===2?'Your cue card':q.part===1?'Everyday conversation':'Ideas and opinions'}</p><h2 tabIndex={-1} aria-live="polite">{q.prompt}</h2>{q.part===2&&<><p className={s.should}>You should say:</p><ul>{q.bullets!.map(b=><li key={b}>{b};</li>)}</ul><p className={s.closing}>{q.closing}</p></>}</article>
 {q.part===2&&<div className={s.timers} key={`timers:${q.id}`}><Timer seconds={60} label="Preparation"/><Timer seconds={120} label="Speaking"/></div>}
 <div className={s.practiceActions}><button className={s.mark} disabled={!uid||saving} onClick={()=>void complete()}>{saving?'Saving…':practised[q.id]?'Complete another practice':'Mark as practised'}</button>{q.part===3&&task.kind==='cue'&&<button className={s.secondary} onClick={()=>goQuestion(task.questions.find(q=>q.part===2)!.id,'2')}>← Back to Cue Card</button>}</div>
 {saveError&&<p className={s.warning} role="alert">{saveError}</p>}
 <nav className={s.questionNav} aria-label="Question navigation"><button disabled={index===0} onClick={()=>goQuestion(queue[index-1]!.id)}>← Previous</button><span>{index+1} / {queue.length}</span><button disabled={index===queue.length-1} onClick={()=>goQuestion(queue[index+1]!.id)}>Next →</button></nav>
 <p className={u.note}>{originLabel(q.origin)}. Answer aloud at your own pace.</p><Sources ids={q.source_ids}/>
 </section>:<p role="status">This practice is unavailable. Choose another task in this topic.</p>}
 {(task||topic)&&<p className={u.note}>{uid?'New completed sessions are saved to My Practice History across devices. Earlier practice marks remain on this device.':<> <Link href="/login?next=%2Fspeaking">Sign in</Link> to save progress on this device.</>}</p>}
 {store.failed()&&<p className={s.warning} role="alert">Device storage is unavailable. Your marks may not survive a reload.</p>}
 </main></div></>;
}
