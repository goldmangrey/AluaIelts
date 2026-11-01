"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useSession, retrySession, rejectSession } from "@/features/auth/session";
import { StatusPanel } from "@/components/status-panel";
import { ReadingExam } from "./reading-exam";
import { getAttempt, readingApi, eventId } from "./api";
import { parseAttempt } from "./parse";
import { ReliableAnswers } from "./reliable-answers";
import { browserDraftStore } from "./draft-storage";
import { getIdToken } from "@/lib/firebase/client";
import { readingMessage } from "./messages";
import type { Attempt } from "./models";

export function AttemptPage({ id }: { id: string }) {
  const session = useSession();
  const [state, setState] = useState<{ attempt?: Attempt; error?: unknown; owner?: number; controller?:ReliableAnswers }>({});
  const [revision, retry] = useState(0);
  useEffect(() => {
    if (session.status !== "ready" || !session.user || !session.profile) return;
    const controller = new AbortController(); const owner = session.generation; let editor:ReliableAnswers|undefined;
    getAttempt(id, session.user.uid, controller.signal).then(async (attempt) => {
      if (!controller.signal.aborted) {
        try { localStorage.removeItem(`alua:reading:start:${session.profile!.uid}:${attempt.exam_id}`); } catch { /* Resume does not require local storage. */ }
        if(attempt.status==="in_progress") {
          const uid=session.user!.uid;
          editor=new ReliableAnswers(attempt,{uid,store:browserDraftStore(uid,id,attempt.content_hash,eventId()),get:()=>getAttempt(id,uid),
            save:async event=>parseAttempt(await readingApi(uid)(`/reading/attempts/${id}/sync`,undefined,{method:"POST",body:event})),
            submit:async event=>parseAttempt(await readingApi(uid)(`/reading/attempts/${id}/submit`,undefined,{method:"POST",body:event})),
            tokenRefresh:()=>getIdToken(true,uid),online:()=>navigator.onLine,onUnauthorized:()=>rejectSession(owner)});
          await editor.initialize();
        }
        if(controller.signal.aborted){editor?.dispose();return}
        setState({ attempt, owner, controller:editor });
      }
    }).catch((error: unknown) => { if (!controller.signal.aborted) setState({ error, owner }); });
    return () => {controller.abort();editor?.dispose();};
  }, [id, revision, session.status, session.generation, session.user, session.profile]);
  if (session.status === "signed_out") return <main id="main" className="page-shell"><StatusPanel title="Log in to continue your test." href={`/login?next=${encodeURIComponent(`/reading/attempts/${id}`)}`} label="Log in">Your existing attempt is preserved.</StatusPanel></main>;
  if (session.status === "error") return <main id="main" className="page-shell"><StatusPanel title="Your session couldn’t load." retry={() => { void retrySession().catch(() => {}); }}>{readingMessage(session.error)} <Link href={`/login?next=${encodeURIComponent(`/reading/attempts/${id}`)}`}>Log in</Link></StatusPanel></main>;
  if (session.status !== "ready" || state.owner !== session.generation) return <main id="main" className="exam-loading" role="status">Loading your Reading attempt…</main>;
  if (state.error || !state.attempt) return <main id="main" className="page-shell"><StatusPanel title="This attempt couldn’t load." retry={() => { setState({}); retry((n) => n + 1); }}>{readingMessage(state.error)}</StatusPanel><Link className="text-link" href="/reading">Back to Reading</Link></main>;
  if (state.attempt.status !== "in_progress") return <main id="main" className="page-shell"><StatusPanel title="This attempt has finished." href={`/reading/attempts/${id}/result`} label="View result">Your saved attempt is preserved.</StatusPanel></main>;
  return <ReadingExam key={`${state.attempt.id}:${session.generation}`} attempt={state.attempt} uid={session.user!.uid} controller={state.controller} />;
}
