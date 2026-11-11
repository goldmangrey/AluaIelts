"use client";

import Link from "next/link";
import { useRef, useState, type ReactNode } from "react";
import styles from "./result-card.module.css";

export function ResultPage({ children }: { children: ReactNode }) {
  return <main id="main" className={styles.page}>{children}</main>;
}

export function ResultCard({ title, band, correct, total, status, reviewHref, onRetake }: {
  title: string; band: number | null; correct: number | null; total: number;
  status?: string; reviewHref: string; onRetake: () => Promise<void>;
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
  const hasBand = band !== null && Number.isFinite(band) && band >= 0 && band <= 9;
  return <section className={styles.card} aria-label="Test result">
    <h1 className={styles.title}>{title}</h1>
    <p className={styles.label}>Estimated IELTS band</p>
    <p className={styles.band} aria-label="Estimated IELTS band score">{hasBand ? band.toFixed(1) : "—"}</p>
    <p className={styles.summary}>{correct !== null ? `${correct} correct · ${total - correct} incorrect` : status || "Grading not confirmed"}</p>
    {correct !== null && !hasBand && status && <p className={styles.status}>{status}</p>}
    <div className={styles.actions}>
      <Link className={styles.primary} href={reviewHref} prefetch={false}><span>Review test</span><span className={styles.badge} aria-label="AI review"><svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M8 1L9.8 6.2L15 8L9.8 9.8L8 15L6.2 9.8L1 8L6.2 6.2L8 1Z" fill="currentColor"/></svg>AI</span></Link>
      <button className={styles.secondary} type="button" onClick={()=>void retake()} disabled={busy} aria-busy={busy}>{busy ? "Starting…" : "Retake test"}</button>
    </div>
    {error && <p className={styles.error} role="alert">Couldn’t start a new attempt. Please retry Retake test.</p>}
  </section>;
}
