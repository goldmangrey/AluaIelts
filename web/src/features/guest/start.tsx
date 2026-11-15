'use client';
import {useEffect,useRef,useState} from 'react';
import {useRouter,useSearchParams} from 'next/navigation';
import Link from 'next/link';
import {useSession} from '@/features/auth/session';
import {AuthRequired} from '@/features/auth/guest-access';
import {createApiClient} from '@/lib/api/client';
import {getIdToken} from '@/lib/firebase/client';
import catalog from './catalog.json';
export function StartPractice(){const session=useSession(),params=useSearchParams(),router=useRouter(),skill=params.get('module'),id=params.get('id'),item=catalog.find(v=>v.module===skill&&v.id===id),[error,setError]=useState(''),[revision,setRevision]=useState(0),job=useRef<Promise<void>|null>(null);
 const intent=params.get('intent')??'';
 const next='/practice/start?'+new URLSearchParams({module:skill??'',id:id??'',intent});
 useEffect(()=>{if(!item||session.status!=='ready'||!session.user)return;const uid=session.user.uid;let live=true;
 if(!job.current)job.current=(async()=>{
  if(item.module==='speaking'){router.replace('destination' in item?item.destination!:'/speaking');return;}
  const key=`alua:guest-start:${uid}:${item.module}:${item.id}:${intent}`;let event=sessionStorage.getItem(key);if(!event){event=/^[a-f0-9-]{36}$/i.test(intent)?intent:crypto.randomUUID();sessionStorage.setItem(key,event)}
  const api=createApiClient(force=>getIdToken(force,uid));
  const a=await api(`/${item.module}/attempts`,undefined,{method:'POST',body:{event_id:event,...(item.module==='writing'?{task_id:item.id,reuse_draft:true}:{exam_id:item.id,...(item.module==='reading'?{mode:'full_exam'}:{reuse_active:true})})}}) as {id:string};
  // Keep the event key until navigation; repeated mounting safely replays the same start.
  router.replace(`/${item.module}/attempts/${a.id}`);
 })();void job.current.catch(()=>{job.current=null;if(live)setError('Could not open this practice. Retry keeps the same start event.');});return()=>{live=false};
 },[session.status,session.user,item,router,revision,intent]);
 if(!item)return <section><h1>Practice unavailable</h1><Link href="/">Explore IELTS practice</Link></section>;
 if(session.status==='loading')return <p role="status">Checking your session…</p>;
 if(session.status!=='ready')return <AuthRequired title="Start your selected practice" description={`Sign in to start ${item.title} and save your progress.`} destination={next}/>;
 return <section><h1 style={{fontSize:24}}>{item.title}</h1>{error?<><p role="alert">{error}</p><button className="button" onClick={()=>{setError('');setRevision(v=>v+1)}}>Retry</button></>:<p role="status">Opening your practice…</p>}<Link href={`/${item.module}`}>Back to catalog</Link></section>;
}
