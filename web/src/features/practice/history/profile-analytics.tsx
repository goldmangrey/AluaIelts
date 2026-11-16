'use client';

import Link from 'next/link';
import {useEffect, useRef, useState} from 'react';
import {useRouter} from 'next/navigation';
import {logout} from '@/features/auth/session';
import {practiceApi, dateLabel, type Module} from './api';
import {skills, human, limited, rankFocusAreas, type Analytics, type Chart, type Criterion, type FocusArea} from './analytics-model';
import s from './profile-analytics.module.css';

function useData<T>(uid: string, path: string) {
  const [revision, setRevision] = useState(0);
  const key = `${uid}:${path}:${revision}`;
  const [state, setState] = useState<{key: string; data?: T; error?: boolean}>();
  useEffect(() => {
    const abort = new AbortController();
    void practiceApi(uid)(path as `/${string}`, abort.signal).then(data => {
      if (!abort.signal.aborted) setState({key, data: data as T});
    }).catch(() => {if (!abort.signal.aborted) setState({key, error: true});});
    return () => abort.abort();
  }, [uid, path, key]);
  return {data: state?.key === key ? state.data : undefined, error: state?.key === key && state.error, retry: () => setRevision(v => v + 1)};
}

export function LearningProgress({uid}: {uid: string}) {
  const [period, setPeriod] = useState('30');
  const [selection, setSelection] = useState<{uid: string; skill: Module} | null>(() => {
    try {const value = sessionStorage.getItem(`alua:progress:${uid}`); return skills.includes(value as Module) ? {uid, skill: value as Module} : null;} catch {return null;}
  });
  const {data, error, retry} = useData<Analytics>(uid, `/practice/analytics?period=${period}`);
  const skill = selection?.uid === uid ? selection.skill : skills.find(v => data?.charts[v]?.points.length) ?? 'listening';
  function choose(next: Module) {
    setSelection({uid, skill: next});
    try {sessionStorage.setItem(`alua:progress:${uid}`, next);} catch {}
  }
  return <section className={s.section} aria-labelledby="learning-progress">
    <div className={s.heading}><div><h2 id="learning-progress">Learning Progress</h2><p>See how your saved results change over time.</p></div>
      <label className={s.period}>Period<select aria-label="Progress period" value={period} onChange={e => setPeriod(e.target.value)}><option value="30">Last 30 days</option><option value="90">Last 90 days</option><option value="all">All time</option></select></label>
    </div>
    {error ? <p role="alert">Could not load your progress. <button onClick={retry}>Retry</button></p> : !data ? <p className={s.loading} role="status">Loading your progress…</p> : <>
      <div className={s.counts}>{skills.map(v => <div key={v}><strong>{data.counts[v]}</strong><span>{human(v)} sessions</span></div>)}</div>
      <div className={s.chartCard}>
        <div className={s.tabs} role="group" aria-label="Progress skill">{skills.map(v => <button key={v} type="button" aria-pressed={skill === v} onClick={() => choose(v)}>{human(v)}</button>)}</div>
        <ResultChart key={`${skill}:${period}`} skill={skill} chart={data.charts[skill]}/>
      </div>
      <p className={s.note}>Only dated, saved results are plotted. Listening and Reading show fully graded /40 results. AI band estimates are not official IELTS scores.</p>
      <MistakeSummary uid={uid}/>
      <FocusAreas areas={data.weak_areas} writing={data.writing_criteria}/>
    </>}
  </section>;
}

function ResultChart({skill, chart}: {skill: Module; chart?: Chart}) {
  const [selected, setSelected] = useState<string | null>(null);
  const band = skill === 'writing' || skill === 'speaking';
  const points = chart?.points ?? [], scale = chart?.scale ?? (band ? 9 : 40);
  const coords = points.map((p, i) => ({x: points.length === 1 ? 50 : 5 + i / (points.length - 1) * 90, y: 86 - p.value / scale * 72}));
  const point = points.find(p => p.id === selected);
  return <section className={s.result} aria-label={`${human(skill)} progress`}>
    <div className={s.chartHeading}><h3>{human(skill)}</h3><span>{band ? 'AI Band Estimate' : 'Correct answers /40'}</span></div>
    {!points.length ? <div className={s.empty}><strong>{skill === 'speaking' ? 'No saved Speaking assessment yet' : `No ${human(skill)} results in this period`}</strong><p>{band ? 'Saved AI band estimates will appear here when available.' : 'Complete a fully graded practice to see your progress.'}</p></div> : <>
      <div className={s.plot} aria-label={`Results from oldest to newest, ${points.length} attempts`}>
        <span className={s.axisTop}>{scale}</span><span className={s.axisBottom}>0</span>
        <svg viewBox="0 0 1000 200" preserveAspectRatio="none" aria-hidden="true"><path d="M50 28H950M50 100H950M50 172H950" fill="none" stroke="#e8eee9"/>{points.length > 1 && <polyline points={coords.map(p => `${p.x * 10},${p.y * 2}`).join(' ')} fill="none" stroke="#338568" strokeWidth="2" vectorEffect="non-scaling-stroke"/>}</svg>
        {points.map((p, i) => <button type="button" key={p.id} className={s.point} style={{left: `${coords[i]!.x}%`, top: `${coords[i]!.y}%`}} aria-label={`${p.title}, ${dateLabel(p.date)}, ${p.value}${band ? ' AI Band Estimate' : ' out of 40'}${p.attempt_count > 1 ? `, attempt ${p.attempt_number}` : ''}`} aria-pressed={selected === p.id} onPointerEnter={e => {if (e.pointerType === 'mouse') setSelected(p.id);}} onFocus={() => setSelected(p.id)} onClick={() => setSelected(p.id)}><span/></button>)}
      </div>
      <div className={s.dateRange}><span>{dateLabel(points[0]!.date)}</span>{points.length > 1 && <span>{dateLabel(points.at(-1)!.date)}</span>}</div>
      {points.length > 12 && <label className={s.attemptSelect}>Choose an attempt<select value={selected ?? ''} onChange={e => setSelected(e.target.value)}><option value="" disabled>Select a saved result</option>{points.map(p => <option key={p.id} value={p.id}>{p.title} · {dateLabel(p.date)} · {p.value}{band ? ' band estimate' : '/40'}{p.attempt_count > 1 ? ` · Attempt ${p.attempt_number}` : ''}</option>)}</select></label>}
      <div className={s.pointDetails} aria-live="polite">{point ? <><div><strong>{point.title}</strong><p>{dateLabel(point.date)}{point.attempt_count > 1 && ` · Attempt ${point.attempt_number} of ${point.attempt_count}`}</p></div><div className={s.detailAction}><span>{band ? `${point.value.toFixed(1)} AI Band Estimate` : `${point.value}/40`}</span><Link href={`/practice/history/${point.id}`}>View Results →</Link></div></> : <p>Choose a point to view this attempt.</p>}</div>
      {chart?.truncated && <p className={s.note}>Latest 200 results shown. Repeated attempts remain separate points.</p>}
    </>}
  </section>;
}

function MistakeSummary({uid}: {uid: string}) {
  // My Mistakes is all-time: the review queue must not shrink with the chart period.
  const {data} = useData<{mistakes: {total: number; reviewed: number}}>(uid, '/practice/analytics?period=all');
  const count = data ? data.mistakes.total - data.mistakes.reviewed : 0;
  return count > 0 ? <aside className={s.mistakes}><div><strong>{count} {count === 1 ? 'mistake' : 'mistakes'} to review</strong><p>Return to questions you got wrong.</p></div><Link href="/practice/mistakes">Review mistakes →</Link></aside> : null;
}

const criterionNames: Record<string, string> = {task_response: 'Task Response · TR', coherence_cohesion: 'Coherence & Cohesion · CC', lexical_resource: 'Lexical Resource · LR', grammar: 'Grammar · GRA'};
function FocusAreas({areas, writing}: {areas: FocusArea[]; writing: Criterion[]}) {
  const [expanded, setExpanded] = useState(false);
  const ranked = rankFocusAreas(areas);
  const questionEntries = ranked.map(a => ({kind: 'questions' as const, area: a}));
  const writingEntries = writing.filter(c => criterionNames[c.criterion]).toSorted((a, b) => a.band - b.band).map(c => ({kind: 'writing' as const, criterion: c}));
  const entries = [...questionEntries.filter(e => !limited(e.area)), ...writingEntries.filter(e => e.criterion.assessments >= 2), ...questionEntries.filter(e => limited(e.area)), ...writingEntries.filter(e => e.criterion.assessments < 2)];
  return <section className={s.focus} aria-labelledby="focus-areas"><div className={s.heading}><div><h2 id="focus-areas">Your Focus Areas</h2><p>Understand what to improve next, based on your practice results.</p></div></div>
    {!entries.length ? <p className={s.emptyFocus}>No focus areas yet. Answer and complete practice to build your learning record.</p> : <>
      <div className={s.focusList}>{(expanded ? entries : entries.slice(0, 3)).map(entry => entry.kind === 'questions' ? <FocusCard key={`${entry.area.module}:${entry.area.category}`} area={entry.area}/> : <article className={s.focusCard} key={`writing:${entry.criterion.criterion}`}><div className={s.focusTop}><h3>Writing · {criterionNames[entry.criterion.criterion]}</h3>{entry.criterion.assessments < 2 && <span className={s.limited}>Limited data</span>}</div><p>Mean AI Band Estimate {Number(entry.criterion.band).toFixed(1)} · {entry.criterion.assessments} saved {entry.criterion.assessments === 1 ? 'assessment' : 'assessments'}</p><div className={s.bar} aria-label={`Mean AI band ${entry.criterion.band} of 9`}><span style={{width: `${entry.criterion.band / 9 * 100}%`}}/></div><Link href="/writing">Practice this skill →</Link></article>)}</div>
      {entries.length > 3 && <button type="button" className={s.expand} aria-expanded={expanded} onClick={() => setExpanded(v => !v)}>{expanded ? 'Show fewer focus areas' : 'View all focus areas'}</button>}
    </>}
    <p className={s.note}>Error rates use answered, graded questions only. Unanswered and not graded are separate. Small samples are marked Limited data.</p>
  </section>;
}
function FocusCard({area: a}: {area: FocusArea}) {
  const rate = Math.round(a.incorrect / a.answered * 100);
  return <article className={s.focusCard}><div className={s.focusTop}><h3>{human(a.module)} · {human(a.category)}</h3>{limited(a) && <span className={s.limited}>Limited data</span>}</div><p>{a.incorrect} incorrect / {a.answered} answered and graded · {rate}% error rate</p><div className={s.bar} aria-label={`${rate}% error rate`}><span style={{width: `${rate}%`}}/></div><p>{a.distinct_tests} distinct {a.distinct_tests === 1 ? 'test' : 'tests'} · Errors in {a.incorrect_attempts} {a.incorrect_attempts === 1 ? 'attempt' : 'attempts'}{a.unanswered > 0 && ` · ${a.unanswered} unanswered`}{a.not_graded > 0 && ` · ${a.not_graded} not graded`}</p><Link href={`/${a.module}`}>Practice this skill →</Link></article>;
}

export function ProfileActions({uid}: {uid: string}) {
  const router = useRouter();
  const {data} = useData<{items: {id: string; href: string}[]}>(uid, '/practice/drafts?limit=1');
  const [busy, setBusy] = useState(false), [error, setError] = useState(false);
  const lock = useRef(false);
  async function exit() {
    if (lock.current) return;
    lock.current = true; setBusy(true); setError(false);
    try {await logout(); router.replace('/'); router.refresh();} catch {setError(true);} finally {lock.current = false; setBusy(false);}
  }
  return <footer className={s.actions}><nav aria-label="Practice shortcuts"><Link href="/practice/history">My Practice History →</Link>{data?.items[0] && <Link href={data.items[0].href}>Continue practice →</Link>}</nav><details className={s.settings}><summary>Account settings</summary><button type="button" disabled={busy} onClick={() => void exit()}>{busy ? 'Logging out…' : 'Log out'}</button>{error && <p role="alert">Could not log out. Please try again.</p>}</details></footer>;
}
