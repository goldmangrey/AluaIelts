"use client";

import Link from "next/link";
import { useRef, useState, type ReactNode } from "react";
import styles from "./result-card.module.css";

export function ResultPage({ children }: { children: ReactNode }) {
  return <main id="main" className={styles.page}>{children}</main>;
}

export function ResultCard({ title, band, correct, total, incorrect, unanswered, status, reviewHref, onRetake, onRetry }: {
  title: string; band: number | null; correct: number | null; total: number; incorrect: number | null; unanswered: number | null;
  status?: string; reviewHref: string; onRetake: () => Promise<void>; onRetry?: () => void;
}) {
  const pending = useRef(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);
  async function retake() {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError(false);
    try { await onRetake(); }
    catch { setError(true); pending.current = false; setBusy(false); }
  }
  const hasScore = correct !== null && Number.isInteger(correct) && correct >= 0 && Number.isInteger(total) && total > 0 && correct <= total;
  const hasBand = band !== null && Number.isFinite(band) && band >= 0 && band <= 9;
  return <section className={styles.card} aria-label="Test result">
    <h1 className={styles.title}>{title}</h1>
    <p className={styles.label}>Correct answers</p>
    <p className={styles.score} aria-label="Correct answers score">{hasScore ? `${correct}/${total}` : "Result unavailable"}</p>
    <p className={styles.bandLabel}>IELTS Band Estimate</p>
    <p className={styles.band} aria-label="Estimated IELTS band score">{hasBand ? band.toFixed(1) : "Not available"}</p>
    <p className={styles.summary}>{hasScore ? `${correct} correct${incorrect!==null?` · ${incorrect} incorrect`:""}${unanswered!==null?` · ${unanswered} unanswered`:""}` : status || "Grading not confirmed"}</p>
    {hasScore && !hasBand && status && <p className={styles.status}>{status}</p>}
    {!hasScore && onRetry && <button className={styles.secondary} type="button" onClick={onRetry}>Retry loading result</button>}
    <div className={styles.actions}>
      <Link className={styles.primary} href={reviewHref} prefetch={false}><span>Review test</span><span className={styles.badge} aria-label="AI review"><svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M8 1L9.8 6.2L15 8L9.8 9.8L8 15L6.2 9.8L1 8L6.2 6.2L8 1Z" fill="currentColor"/></svg>AI</span></Link>
      <button className={styles.secondary} type="button" onClick={()=>void retake()} disabled={busy} aria-busy={busy}>{busy ? "Starting…" : "Retake test"}</button>
    </div>
    <nav className={styles.exitLinks} aria-label="Completed practice navigation"><Link href="/" className={styles.home}>← Back to Home</Link><Link href="/practice/history" className={styles.history}>History</Link><Link href="/practice/mistakes">Review Mistakes</Link></nav>
    {error && <p className={styles.error} role="alert">Couldn’t start a new attempt. Please retry Retake test.</p>}
  </section>;
}
