'use client';

import Link from 'next/link';
import {useEffect, useState, type ReactNode} from 'react';
import {LuaMascot} from '@/components/lua-mascot';
import {useSession} from '@/features/auth/session';
import {practiceApi, type HistoryData} from '@/features/practice/history/api';
import type {Analytics} from '@/features/practice/history/analytics-model';
import s from './lua-message.module.css';

type Context = {history?: HistoryData; analytics?: Analytics; drafts?: {total:number}; now:number};
type Message = {emotion:'support'|'celebration'|'wave'|'proud'; title:string; detail:string; href?:string; link?:string};
const neutral:Message = {emotion:'support', title:'A little practice goes a long way.', detail:'Choose a skill below and keep learning at your own pace.'};

/** Only timestamped completions from the last hour qualify as a current event. */
export function selectLuaMessage({history, analytics, drafts, now}:Context):Message {
  const latest = history?.items.find(item => {
    const age = now - Date.parse(item.completed_at ?? '');
    return age >= 0 && age < 60 * 60 * 1000;
  });
  if (latest) return {emotion:'celebration', title:"That's another test completed!", detail:'Your latest results are ready whenever you want to revisit them.', href:`/practice/history/${encodeURIComponent(latest.id)}`, link:'View results →'};
  const total = analytics?.mistakes.total, reviewed = analytics?.mistakes.reviewed;
  if (Number.isSafeInteger(total) && Number.isSafeInteger(reviewed) && total! >= reviewed! && reviewed! >= 0) {
    const remaining = total! - reviewed!;
    if (remaining > 0) return {emotion:'support', title:'I found something worth reviewing.', detail:`You have ${remaining} ${remaining === 1 ? 'mistake' : 'mistakes'} ready for another look.`, href:'/practice/mistakes', link:'Review mistakes →'};
    if (total! > 0) return {emotion:'proud', title:"You've reviewed your mistakes.", detail:"Ready to put what you've learned into practice?"};
  }
  if (history?.total === 0 && drafts?.total === 0 && analytics && Object.values(analytics.counts).every(count => count === 0) && total === 0) {
    return {emotion:'wave', title:"Let's find your starting point.", detail:'Choose a skill below and start your first practice.'};
  }
  return neutral;
}

function LuaMessage({uid}:{uid:string}) {
  const [message, setMessage] = useState<Message>(neutral);
  useEffect(() => {
    let disposed = false, request:AbortController|undefined;
    async function load() {
      request?.abort();
      const abort = new AbortController(); request = abort;
      const api = practiceApi(uid);
      const results = await Promise.allSettled([
        api('/practice/history?limit=5&order=desc', abort.signal),
        api('/practice/analytics?period=all', abort.signal),
        api('/practice/drafts?limit=1', abort.signal),
      ]);
      if (disposed || abort.signal.aborted) return;
      setMessage(selectLuaMessage({
        history:results[0].status === 'fulfilled' ? results[0].value as HistoryData : undefined,
        analytics:results[1].status === 'fulfilled' ? results[1].value as Analytics : undefined,
        drafts:results[2].status === 'fulfilled' ? results[2].value as {total:number} : undefined,
        now:Date.now(),
      }));
    }
    const refresh = () => {if (!document.hidden) void load();};
    void load();
    window.addEventListener('focus', refresh);
    return () => {disposed = true; request?.abort(); window.removeEventListener('focus', refresh);};
  }, [uid]);
  return <section className={s.message} aria-labelledby="lua-message-title">
    <LuaMascot mode="static" emotion={message.emotion} size={112} priority className={s.lua}/>
    <div className={s.bubble}>
      <p className={s.label}>LUA SAYS</p>
      <h1 id="lua-message-title">{message.title}</h1>
      <p className={s.detail}>{message.detail}</p>
      {message.href && <Link className={s.link} href={message.href}>{message.link}</Link>}
    </div>
  </section>;
}

export function HomeWelcome({children}:{children:ReactNode}) {
  const session = useSession();
  // Firebase resolves before choosing either composition: a restored session never sees the guest hero.
  if (session.status === 'loading') return <div className={s.pending} role="status" aria-label="Loading your home"/>;
  if (session.user) return <LuaMessage key={session.user.uid} uid={session.user.uid}/>;
  return <>{children}</>;
}
