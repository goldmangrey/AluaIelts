'use client';
import {LuaMascot} from '@/components/lua-mascot';
import {AuthRequired} from './guest-access';
import {LearningProgress,ProfileActions} from '@/features/practice/history/profile-analytics';
import Image from 'next/image';
import {useRouter} from 'next/navigation';
import {useEffect,useMemo,useRef,useState,type CSSProperties} from 'react';
import {ProfileEditor} from './profile-editor';
import editorStyles from './profile-editor.module.css';
import {StatusPanel} from '@/components/status-panel';
import {retrySession,useSession} from './session';
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
 return <section className={`${s.panel} ${s.activityPanel}`} aria-labelledby="activity-title"><div className={s.panelHeader}><h2 id="activity-title">Your practice activity</h2><span className={s.muted}>Last 12 months · Asia/Almaty</span></div>
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
 const api=useMemo(()=>practiceApi(uid),[uid]);
 const [data,setData]=useState<{profile:Profile;activity:Activity}>(),[error,setError]=useState(''),[reload,setReload]=useState(0);
 const [avatar,setAvatar]=useState<string|null>(null),[avatarReload,setAvatarReload]=useState(0);
 const [editing,setEditing]=useState(false),[savedMessage,setSavedMessage]=useState('');
 const busy=false;
 const editorAvatarUrl=useRef<string|null>(null);
 useEffect(()=>{const abort=new AbortController();void Promise.all([api('/me',abort.signal),api('/practice/activity',abort.signal)]).then(([profile,activity])=>{setData({profile:profile as Profile,activity:activity as Activity});setError('');}).catch(()=>{if(!abort.signal.aborted)setError('Your profile could not load. Please try again.');});return()=>abort.abort();},[api,reload]);
 useEffect(()=>{let live=true;let url:string|undefined;const abort=new AbortController();void avatarRequest(uid,'GET',undefined,abort.signal).then(blob=>{if(blob){url=URL.createObjectURL(blob);if(live)setAvatar(url);else URL.revokeObjectURL(url);}else if(live)setAvatar(null);}).catch(()=>{if(live)setError('Your avatar could not load. You can retry.');});return()=>{live=false;abort.abort();if(url)URL.revokeObjectURL(url);};},[uid,avatarReload]);
 useEffect(()=>()=>{if(editorAvatarUrl.current)URL.revokeObjectURL(editorAvatarUrl.current);},[]);
 const profile=data?.profile,activity=data?.activity;const initials=(profile?.display_name||email||'A').split(/[\s@]+/).filter(Boolean).slice(0,2).map(s=>s[0]).join('').toUpperCase();
 return <section className={s.shell}>
 <p className={s.eyebrow}>YOUR ALUA PROFILE</p>
 {error&&<div className={s.alert} role="alert">{error} <button className="button secondary" disabled={busy} onClick={()=>{setReload(n=>n+1);setAvatarReload(n=>n+1);}}>Retry</button></div>}
 {!data?<p role="status">Loading your practice…</p>:<>
 <header className={s.profileHeader}><div className={s.avatar}>{avatar?<Image src={avatar} alt="Your avatar" width={96} height={96} unoptimized/>:<span aria-label="Initials avatar">{initials}</span>}</div><div><h1>{profile?.display_name||'Your profile'}</h1><p className={s.muted}>{email||profile?.email}</p>{profile?.target_ielts_band&&<p className={s.muted}>Target IELTS Band <b>{profile.target_ielts_band.toFixed(1)}</b></p>}</div><button className={`button secondary ${s.editProfile}`} disabled={busy} onClick={e=>{e.currentTarget.focus();setSavedMessage('');setEditing(true);}} aria-expanded={editing}>Edit Profile<span className={s.editArrow} aria-hidden="true">↗</span></button></header>
 {savedMessage&&<p role="status" className={editorStyles.savedMessage}>{savedMessage}</p>}
 {editing&&profile&&<ProfileEditor uid={uid} profile={profile} avatar={avatar} initials={initials}
   onClose={()=>setEditing(false)} onProfileSaved={p=>setData(d=>d?{...d,profile:p}:d)}
   onAvatarSaved={blob=>{if(editorAvatarUrl.current)URL.revokeObjectURL(editorAvatarUrl.current);editorAvatarUrl.current=blob?URL.createObjectURL(blob):null;setAvatar(editorAvatarUrl.current);setAvatarReload(n=>n+1);}}
   onComplete={()=>{setEditing(false);setSavedMessage('Profile updated.');}}/>}
 {activity&&<><div className={s.stats}>{[[activity.total_practice_sessions,'Practice Sessions'],[activity.current_streak,'Study Streak'],[activity.active_days,'Active Days · 30 days'],[activity.longest_streak,'Longest Streak · days']].map(([value,label])=><article className={s.stat} key={label}><strong>{value}</strong><span>{label}</span>{label==='Study Streak'&&activity.current_streak>0&&<LuaMascot emotion="proud" size={36} className={s.streakLua}/>}</article>)}</div><ActivityCalendar activity={activity}/></>}
 <LearningProgress uid={uid}/>
 <ProfileActions uid={uid}/>
 </>}
 </section>;
}
