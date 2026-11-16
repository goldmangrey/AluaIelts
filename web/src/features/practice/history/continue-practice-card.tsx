import {LuaMascot} from '@/components/lua-mascot';
import Link from 'next/link';
import type {Module} from './api';
import s from './continue-practice-card.module.css';

type ContinuePracticeCardProps = {
  draft: {
    module: Module;
    title: string;
    position?: string;
    answered?: number;
    href: string;
  };
  otherSessions: number;
};

/** Presentation only: the caller owns session selection and the restore URL. */
export function ContinuePracticeCard({draft, otherSessions}: ContinuePracticeCardProps) {
  const writing = draft.module === 'writing';
  const progress = [
    draft.position ? `${draft.position}${writing ? ' written' : ''}` : null,
    writing ? 'Saved draft' :
      (draft.module === 'listening' || draft.module === 'reading') && typeof draft.answered === 'number'
        ? `${draft.answered} answered` : null,
  ].filter(Boolean);

  return <section className={s.card} aria-label="Continue where you left off">
    <div className={s.topRow}>
      <p className={s.label}><span className={s.dot} aria-hidden="true"/>Continue where you left off</p>
      <span className={s.badge}>{draft.module}<span className={s.slash}>/</span>{writing ? 'Draft' : 'In progress'}</span>
    </div>
    <div className={s.main}>
      <LuaMascot emotion="happy" size={64} context="continue"/><div className={s.content}>
        <h2 className={s.title}>{draft.title}</h2>
        {progress.length > 0 && <p className={s.progress}>{progress.map((part, index) =>
          <span key={index}>{index > 0 && <span className={s.separator}>·</span>}{part}</span>
        )}</p>}
      </div>
      <Link className={s.action} href={draft.href}>Continue practice<span className={s.arrow} aria-hidden="true">↗</span></Link>
    </div>
    {otherSessions > 0 && <div className={s.footer}>
      <Link className={s.otherSessions} href="/practice/continue">{otherSessions} other {otherSessions === 1 ? 'session' : 'sessions'}<span aria-hidden="true">↗</span></Link>
    </div>}
  </section>;
}
