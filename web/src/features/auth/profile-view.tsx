'use client';
import {AuthRequired} from './guest-access';
import {LearningProgress} from '@/features/practice/history/learning';
import Image from 'next/image';
import Link from 'next/link';
import {useRouter} from 'next/navigation';
import {useEffect,useMemo,useRef,useState,type CSSProperties} from 'react';
import {StatusPanel} from '@/components/status-panel';
import {logout,retrySession,useSession} from './session';
import {practiceApi,avatarRequest,type Activity,type Profile} from '@/features/practice/history/api';
import s from '@/features/practice/history/practice.module.css';

export function ProfileView(){
 const session=useSession();
 if(session.status==='signed_out')return <AuthRequired title="Your IELTS progress, at a glance." description="Sign in to see your activity, saved practice and learning progress."/>;
 if(session.status==='loading')return <p role="status">Loading your profile…</p>;
 if(session.status!=='ready'||!session.user)return <StatusPanel title="Your profile couldn’t load." retry={()=>void retrySession().catch(()=>{})}>Sign in to see your personal practice and activity.</StatusPanel>;
 return <ProfileDashboard key={`${session.user.uid}:${session.generation}`} uid={session.user.uid} email={session.user.email}/>;
}
function ActivityCalendar({activity}:{activity:Activity}){
 const router=useRouter();const [selected,setSelected]=useState('');const scroll=useRef<HTMLDivElement>(null);
 const first=activity.days[0]?.date;
 const leading=first?(new Date(first+'T12:00:00Z').getUTCDay()+6)%7:0;
 const weeks=Math.ceil((leading+activity.days.length)/7);
 const months=activity.days.flatMap((day,i)=>i===0||day.date.slice(0,7)!==activity.days[i-1]!.date.slice(0,7)?[{date:day.date,column:Math.floor((leading+i)/7)}]:[]);
 useEffect(()=>{if(scroll.current)scroll.current.scrollLeft=scroll.current.scrollWidth;},[first]);
 return <section className={s.panel} aria-labelledby="activity-title"><div className={s.panelHeader}><h2 id="activity-title">Your practice activity</h2><span className={s.muted}>Last 12 months · Asia/Almaty</span></div>
 <div className={s.calendarScroll} ref={scroll} tabIndex={0} role="region" aria-label="Activity calendar, scroll horizontally to see the full year"><div className={s.calendar} style={{'--weeks':weeks} as CSSProperties} role="group" aria-label="Completed practice sessions by day">
 {months.map((month,i)=>{const span=(months[i+1]?.column??weeks)-month.column;return span>=2?<span key={month.date} className={s.monthLabel} style={{gridColumn:`${month.column+2} / span ${span}`,gridRow:1}} aria-hidden="true">{new Intl.DateTimeFormat('en-US',{month:'short',timeZone:'Asia/Almaty'}).format(new Date(month.date+'T12:00:00Z'))}</span>:null;})}
 {['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].map((day,i)=><span className={s.dayLabel} key={day} style={{gridColumn:1,gridRow:i+2}} aria-hidden="true">{day}</span>)}
 {activity.days.map((day,i)=>{const date=new Intl.DateTimeFormat('en-GB',{day:'numeric',month:'long',year:'numeric',timeZone:'Asia/Almaty'}).format(new Date(day.date+'T12:00:00Z'));const label=`${date} — ${day.count} practice ${day.count===1?'session':'sessions'}`;const level=day.count>=5?4:day.count>=3?3:day.count;return <button key={day.date} type="button" className={s.heatCell} data-date={day.date} data-level={level} style={{gridColumn:Math.floor((leading+i)/7)+2,gridRow:(leading+i)%7+2}} title={label} aria-label={day.count>0?`${label}. View completed sessions`:label} onMouseEnter={()=>setSelected(label)} onFocus={()=>setSelected(label)} onClick={()=>{setSelected(label);if(day.count>0)router.push(`/practice/history?day=${day.date}`);}}/>;})}</div></div>
 <div className={s.calendarFooter}><p className={s.calendarMessage} aria-live="polite">{selected||(activity.days.some(d=>d.count>0)?'Every completed session counts.':'No completed practice in the last 12 months. Start with one session.')}</p><button type="button" className={s.latestDay} onClick={()=>{scroll.current?.scrollTo({left:scroll.current.scrollWidth,behavior:'smooth'});scroll.current?.querySelector<HTMLButtonElement>('button:last-child')?.focus({preventScroll:true});}}>Latest day →</button></div>
 <div className={s.legend}><span>Less</span>{[0,1,2,3,4].map(v=><i key={v} data-level={v}/>)}<span>More</span></div><div className={s.activitySummary}><span>Current streak: <b>{activity.current_streak} {activity.current_streak===1?'day':'days'}</b></span><span>Longest streak: <b>{activity.longest_streak} {activity.longest_streak===1?'day':'days'}</b></span><span>Active days: <b>{activity.active_days} / 30 days</b></span></div>
 {activity.undated_sessions>0&&<p className={s.muted}>{activity.undated_sessions} {activity.undated_sessions===1?'older session has':'older sessions have'} no recorded completion date and are excluded from the calendar.</p>}
 </section>;
}

function ProfileDashboard({uid,email}:{uid:string;email:string|null}){
 const api=useMemo(()=>practiceApi(uid),[uid]),router=useRouter();
 const [data,setData]=useState<{profile:Profile;activity:Activity}>(),[error,setError]=useState(''),[reload,setReload]=useState(0);
 const [avatar,setAvatar]=useState<string|null>(null),[avatarReload,setAvatarReload]=useState(0);
 const [editing,setEditing]=useState(false),[name,setName]=useState(''),[band,setBand]=useState(''),[busy,setBusy]=useState(false);
 const [crop,setCrop]=useState<{url:string;width:number;height:number}>(),[zoom,setZoom]=useState(1),[offsetX,setOffsetX]=useState(0),[offsetY,setOffsetY]=useState(0);
 const cropImage=useRef<HTMLImageElement|null>(null),lock=useRef(false);
 useEffect(()=>{const abort=new AbortController();void Promise.all([api('/me',abort.signal),api('/practice/activity',abort.signal)]).then(([profile,activity])=>{setData({profile:profile as Profile,activity:activity as Activity});setError('');}).catch(()=>{if(!abort.signal.aborted)setError('Your profile could not load. Please try again.');});return()=>abort.abort();},[api,reload]);
 useEffect(()=>{let live=true;let url:string|undefined;const abort=new AbortController();void avatarRequest(uid,'GET',undefined,abort.signal).then(blob=>{if(blob){url=URL.createObjectURL(blob);if(live)setAvatar(url);else URL.revokeObjectURL(url);}else if(live)setAvatar(null);}).catch(()=>{if(live)setError('Your avatar could not load. You can retry.');});return()=>{live=false;abort.abort();if(url)URL.revokeObjectURL(url);};},[uid,avatarReload]);
 useEffect(()=>()=>{if(crop)URL.revokeObjectURL(crop.url);},[crop]);
 async function choose(file?:File){
  if(!file)return;if(file.size>2*1024*1024||!['image/jpeg','image/png','image/webp'].includes(file.type)){setError('Choose a PNG, JPEG or WebP up to 2 MB.');return;}
  const url=URL.createObjectURL(file),image=new window.Image();image.onload=()=>{if(Math.min(image.naturalWidth,image.naturalHeight)<32||Math.max(image.naturalWidth,image.naturalHeight)>4096){URL.revokeObjectURL(url);setError('Choose an image between 32 and 4096 pixels.');return;}cropImage.current=image;setZoom(1);setOffsetX(0);setOffsetY(0);setCrop({url,width:image.naturalWidth,height:image.naturalHeight});setError('');};image.onerror=()=>{URL.revokeObjectURL(url);setError('This image could not be opened.');};image.src=url;
 }
 async function run(operation:()=>Promise<void>){if(lock.current)return;lock.current=true;setBusy(true);setError('');try{await operation();}catch{setError('Could not save your changes. Please try again.');}finally{lock.current=false;setBusy(false);}}
 async function saveAvatar(){
  if(!crop||!cropImage.current)return;const canvas=document.createElement('canvas');canvas.width=canvas.height=256;const context=canvas.getContext('2d');if(!context)throw Error();
  const side=Math.min(crop.width,crop.height)/zoom,x=(crop.width-side)/2*(1+offsetX/100),y=(crop.height-side)/2*(1+offsetY/100);context.drawImage(cropImage.current,x,y,side,side,0,0,256,256);
  const blob=await new Promise<Blob>((resolve,reject)=>canvas.toBlob(b=>b?resolve(b):reject(Error()),'image/webp',.88));await avatarRequest(uid,'PUT',blob);setCrop(undefined);setAvatarReload(n=>n+1);
 }
 const profile=data?.profile,activity=data?.activity;const initials=(profile?.display_name||email||'A').split(/[\s@]+/).filter(Boolean).slice(0,2).map(s=>s[0]).join('').toUpperCase();
 const side=crop?Math.min(crop.width,crop.height)/zoom:1;
 return <section className={s.shell}>
 <p className={s.eyebrow}>YOUR ALUA PROFILE</p>
 {error&&<div className={s.alert} role="alert">{error} <button className="button secondary" disabled={busy} onClick={()=>{setReload(n=>n+1);setAvatarReload(n=>n+1);}}>Retry</button></div>}
 {!data?<p role="status">Loading your practice…</p>:<>
 <header className={s.profileHeader}><div className={s.avatar}>{avatar?<Image src={avatar} alt="Your avatar" width={96} height={96} unoptimized/>:<span aria-label="Initials avatar">{initials}</span>}</div><div><h1>{profile?.display_name||'Your profile'}</h1><p className={s.muted}>{email||profile?.email}</p>{profile?.target_ielts_band&&<p className={s.muted}>Target IELTS Band <b>{profile.target_ielts_band.toFixed(1)}</b></p>}</div><button className="button secondary" disabled={busy} onClick={()=>{setName(profile?.display_name??'');setBand(profile?.target_ielts_band?.toString()??'');setEditing(v=>!v);}} aria-expanded={editing}>Edit Profile</button></header>
 {editing&&<section className={s.panel}><h2>Edit your profile</h2><form className={s.editForm} onSubmit={e=>{e.preventDefault();void run(async()=>{const p=await api('/me',undefined,{method:'PATCH',body:{display_name:name.trim(),target_ielts_band:band?Number(band):null}}) as Profile;setData(d=>d?{...d,profile:p}:d);setEditing(false);});}}><label>Name<input value={name} maxLength={80} required onChange={e=>setName(e.target.value)}/></label><label>Target IELTS Band<input type="number" min="4" max="9" step="0.5" value={band} onChange={e=>setBand(e.target.value)}/></label><div><button className="button" disabled={busy}>Save profile</button><button className="button secondary" type="button" onClick={()=>setEditing(false)}>Cancel</button></div></form>
 <h2 style={{marginTop:28}}>Profile photo</h2><p className={s.muted}>PNG, JPEG or WebP · up to 2 MB · 32–4096 pixels</p><label className={s.fileLabel}>Choose avatar <input aria-label="Choose avatar" type="file" accept="image/png,image/jpeg,image/webp" disabled={busy} onChange={e=>{void choose(e.target.files?.[0]);e.target.value='';}}/></label>
 {crop&&<div className={s.cropControls}><div className={s.cropPreview}><Image src={crop.url} alt="Avatar crop preview" width={crop.width} height={crop.height} unoptimized style={{width:220*crop.width/side,height:220*crop.height/side,left:-(crop.width-side)/2*(1+offsetX/100)*220/side,top:-(crop.height-side)/2*(1+offsetY/100)*220/side}}/></div><label>Zoom<input type="range" min="1" max="3" step="0.05" value={zoom} onChange={e=>setZoom(Number(e.target.value))}/></label><label>Horizontal position<input type="range" min="-100" max="100" value={offsetX} onChange={e=>setOffsetX(Number(e.target.value))}/></label><label>Vertical position<input type="range" min="-100" max="100" value={offsetY} onChange={e=>setOffsetY(Number(e.target.value))}/></label><button className="button" disabled={busy} onClick={()=>void run(saveAvatar)}>Save avatar</button><button className="button secondary" disabled={busy} onClick={()=>setCrop(undefined)}>Cancel crop</button></div>}
 {avatar&&!crop&&<button className="button secondary" disabled={busy} onClick={()=>void run(async()=>{await avatarRequest(uid,'DELETE');setAvatarReload(n=>n+1);})}>Remove avatar</button>}
 </section>}
 {activity&&<><div className={s.stats}>{[[activity.total_practice_sessions,'Practice Sessions'],[activity.current_streak,'Study Streak'],[activity.active_days,'Active Days · 30 days'],[activity.longest_streak,'Longest Streak · days']].map(([value,label])=><article className={s.stat} key={label}><strong>{value}</strong><span>{label}</span></article>)}</div><ActivityCalendar activity={activity}/></>}
 <LearningProgress uid={uid}/>
 <nav className={s.profileLinks}><Link className="button" href="/practice/history">My Practice History →</Link><Link className="button secondary" href="/">Continue practice</Link><button className="button secondary" disabled={busy} onClick={()=>void run(async()=>{await logout();router.replace('/');router.refresh();})}>Log out</button></nav>
 </>}
 </section>;
}
