"use client";

import {useEffect, useId, useRef, useState, useSyncExternalStore, type ReactNode} from "react";
import {AuthRequired} from "@/features/auth/guest-access";
import s from "./test-start-modal.module.css";

const change = "alua:test-selection";
function subscribe(listener: () => void) {
  window.addEventListener("popstate", listener);
  window.addEventListener(change, listener);
  return () => { window.removeEventListener("popstate", listener); window.removeEventListener(change, listener); };
}
export function useTestSelection() {
  const selected = useSyncExternalStore(subscribe, () => new URLSearchParams(location.search).get("test") ?? "", () => "");
  return {selected, open: (id: string) => {
    const url = new URL(location.href); url.searchParams.set("test", id);
    history.pushState({...history.state, aluaTestModal: true}, "", url);
    window.dispatchEvent(new Event(change));
  }, close: () => {
    if (history.state?.aluaTestModal) history.back();
    else {
      const url = new URL(location.href); url.searchParams.delete("test");
      history.replaceState(history.state, "", url); window.dispatchEvent(new Event(change));
    }
  }};
}

export function TestStartModal({skill, book, test, facts, note, loading, error, onClose, children, guest = false}: {
  skill: "Reading" | "Listening"; book: number; test: number;
  facts: {value: number; label: string}[]; note?: string; loading?: boolean; error?: string;
  onClose: () => void; children?: ReactNode; guest?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null), title = useId(), description = useId();
  const [signIn, setSignIn] = useState(false);
  useEffect(() => {
    const dialog = ref.current!;
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const y = window.scrollY, body = document.body, html = document.documentElement;
    const saved = {overflow: body.style.overflow, position: body.style.position, top: body.style.top, width: body.style.width, htmlOverflow: html.style.overflow};
    Object.assign(body.style, {overflow: "hidden", position: "fixed", top: `-${y}px`, width: "100%"}); html.style.overflow = "hidden";
    dialog.showModal(); dialog.querySelector<HTMLElement>("h2")?.focus({preventScroll: true});
    return () => {
      dialog.close(); Object.assign(body.style, {overflow: saved.overflow, position: saved.position, top: saved.top, width: saved.width}); html.style.overflow = saved.htmlOverflow;
      window.scrollTo(0, y); previous?.focus({preventScroll: true});
    };
  }, []);
  return <dialog ref={ref} className={s.dialog} aria-labelledby={title} aria-describedby={description}
    onCancel={e => {e.preventDefault(); onClose();}} onKeyDown={e => {
      if(e.key !== "Tab") return;
      const controls = [...e.currentTarget.querySelectorAll<HTMLElement>('button:not(:disabled),a[href],input:not(:disabled),[tabindex="0"]')].filter(el => el.getClientRects().length > 0);
      if(!controls.length) return;
      e.preventDefault(); const index = controls.indexOf(document.activeElement as HTMLElement);
      controls[index < 0 ? (e.shiftKey ? controls.length-1 : 0) : (index + (e.shiftKey ? -1 : 1) + controls.length) % controls.length]?.focus();
    }}>
    <div className={s.top}><p>CAMBRIDGE {String(book).padStart(2,"0")} / TEST {String(test).padStart(2,"0")}</p>
      <button className={s.close} aria-label="Close test details" onClick={onClose}>×</button></div>
    <h2 id={title} tabIndex={-1}>Ready for {skill}?</h2>
    <p id={description} className={s.description}>{skill === "Reading" ? "Focus on the questions. We'll help you understand your results afterward." : "Listen at your own pace. We'll help you understand your results afterward."}</p>
    {loading ? <p className={s.note} role="status">Loading test details…</p> : <dl className={s.facts}>{facts.map(f => <div key={f.label}><dt>{f.label}</dt><dd>{String(f.value).padStart(2,"0")}</dd></div>)}</dl>}
    {note && <p className={s.note}>{note}</p>}
    {error && <p role="alert" className={s.note}>{error}</p>}
    <div className={s.actions}>{guest ? signIn ? <AuthRequired title="Save your practice progress" description="Sign in, then confirm Start for this test." destination={typeof window === "undefined" ? "/" : location.pathname + location.search} cancel={() => setSignIn(false)}/> : <button onClick={() => setSignIn(true)}>Start {skill} <span aria-hidden="true">→</span></button> : children}</div>
  </dialog>;
}
