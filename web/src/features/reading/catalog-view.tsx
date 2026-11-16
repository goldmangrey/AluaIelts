"use client";
import {TestStartModal, useTestSelection} from "@/components/test-start-modal";
import {readingApi} from "./exam/api";
import {GuestCatalog} from "@/features/guest/catalog";
import Link from "next/link";
import styles from "./library.module.css";
import { StartButton } from "./exam/start-button";
import { usePathname } from "next/navigation";
import { rejectSession, retrySession, useSession } from "@/features/auth/session";
import { useEffect, useState } from "react";
import { StatusPanel } from "@/components/status-panel";
import { ApiError } from "@/lib/api/client";
import { availableBooks, getReadingCatalog } from "./api";
import type { ReadingBook } from "./contracts";

type State = { kind: "loading" } | { kind: "ready"; books: ReadingBook[]; owner: number } | { kind: "error"; error: ApiError; owner: number };
function CatalogError({ error, retry, returnPath }: { error: ApiError; retry: () => void; returnPath: string }) {
  if (error.status === 401) return <StatusPanel title="Log in to view practice tests." href={`/login?next=${encodeURIComponent(returnPath)}`} label="Log in">
    Your practice tests and progress are linked to your Alua account.
  </StatusPanel>;
  if (["api_not_configured", "auth_not_configured"].includes(error.code)) return <StatusPanel title="Practice tests aren’t available yet." href={`/login?next=${encodeURIComponent(returnPath)}`} label="Log in">
    Account access needs to be configured by the Alua site owner.
  </StatusPanel>;
  if (error.status === 403) return <StatusPanel title="Practice tests aren’t available for this account.">
    Please check your Alua account access.
  </StatusPanel>;
  if (error.status >= 500) return <StatusPanel title="Practice tests are temporarily unavailable." retry={retry}>Please try again in a moment.</StatusPanel>;
  return <StatusPanel title={error.code === "timeout" ? "The connection is taking too long." : "Practice tests couldn’t load."} retry={retry}>
    Check your connection and try again.
  </StatusPanel>;
}
export function CatalogView({ bookNumber, examId }: { bookNumber?: number; examId?: string }) {
  const session = useSession();
  const selection = useTestSelection();
  const [detail, setDetail] = useState<{id:string;owner:number;minutes?:number;error?:string}>();
  useEffect(() => {
    if (!selection.selected || session.status !== "ready" || !session.user) return;
    const abort = new AbortController(), id = selection.selected, owner = session.generation;
    readingApi(session.user.uid)(`/reading/exams/${id}`, abort.signal).then(value => {
      const data = value as {id:string;duration_seconds:number};
      if(data.id !== id || !Number.isSafeInteger(data.duration_seconds) || data.duration_seconds <= 0) throw Error();
      if(!abort.signal.aborted)setDetail({id,owner,minutes:data.duration_seconds/60});
    }).catch(() => {if(!abort.signal.aborted)setDetail({id,owner,error:"Test details couldn’t load. Close and try again."});});
    return () => abort.abort();
  }, [selection.selected, session.status, session.user, session.generation]);
  const pathname = usePathname();
  const [state, setState] = useState<State>({ kind: "loading" });
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    if (session.status !== "ready") return;
    const owner = session.generation;
    const controller = new AbortController();
    getReadingCatalog(controller.signal).then((catalog) => {
      if (!controller.signal.aborted) setState({ kind: "ready", books: availableBooks(catalog), owner });
    }).catch((error: unknown) => {
      if (!controller.signal.aborted) {
        if (error instanceof ApiError && error.status === 401) rejectSession(owner);
        setState({ kind: "error", error: error instanceof ApiError ? error : new ApiError(0, "network_error"), owner });
      }
    });
    return () => controller.abort();
  }, [revision, session.status, session.generation]);
  if (session.status === "signed_out") return <GuestCatalog module="reading" book={bookNumber} examId={examId} compact/>;
  if (session.status === "error") return <CatalogError error={session.error instanceof ApiError ? session.error : new ApiError(0, "network_error")} retry={() => { void retrySession().catch(() => {}); }} returnPath={pathname} />;
  if (session.status === "loading" || state.kind === "loading" || state.owner !== session.generation) return <p className="loading-text" role="status">Loading practice tests…</p>;
  if (state.kind === "error") return <CatalogError returnPath={pathname} error={state.error} retry={() => { setState({ kind: "loading" }); setRevision((r) => r + 1); }} />;
  const book = state.books.find((book) => book.book_number === bookNumber);
  if (bookNumber && !book) return <StatusPanel title="Collection unavailable." href="/reading" label="Back to Reading">
    This collection has no available practice tests.
  </StatusPanel>;
  if (book) {
    const exam = book.exams.find(e => e.exam_id === selection.selected);
    const current = detail?.id === exam?.exam_id && detail?.owner === session.generation ? detail : undefined;
    return <><nav className="test-list" aria-label="Available tests">{book.exams.map(exam =>
      <Link className="list-row" key={exam.exam_id} href={`?test=${exam.exam_id}`} scroll={false} onClick={e=>e.currentTarget.focus({preventScroll:true})} onNavigate={e => {e.preventDefault(); selection.open(exam.exam_id);}}>
        <span>Test {exam.source_test_number}</span><span className="row-end">{exam.in_progress_attempt_ids.length > 0 && <small>In progress</small>}<span aria-hidden="true">→</span></span>
      </Link>)}
    </nav>{selection.selected && (exam ? <TestStartModal key={`${exam.exam_id}:${session.generation}`} skill="Reading" book={book.book_number} test={exam.source_test_number}
      onClose={selection.close} loading={!current} error={current?.error}
      facts={[...(current?.minutes ? [{value:current.minutes,label:"Minutes"}] : []),{value:exam.passage_count,label:"Passages"},{value:exam.question_count,label:"Questions"}]}
      note={exam.not_fully_proofread ? "Practice material · Not fully proofread" : undefined}>
      {current?.minutes && <StartButton examId={exam.exam_id} uid={session.user!.uid} learnerId={session.profile!.uid} hasAttempt={exam.in_progress_attempt_ids.length > 0}/>}
    </TestStartModal> : <TestStartModal skill="Reading" book={book.book_number} test={0} facts={[]} error="This test is unavailable." onClose={selection.close}/>)}</>;
  }
  if (!state.books.length) return <StatusPanel title="No practice tests available.">Please check back soon.</StatusPanel>;
  return <nav className={styles.index} aria-label="Cambridge IELTS collections">{state.books.map((book) =>
    <Link className={styles.row} key={book.book_number} href={`/reading/cambridge-${book.book_number}`}>
      <span className={styles.number}>{String(book.book_number).padStart(2, "0")}</span>
      <span className={styles.name}>Cambridge IELTS</span><span className={styles.arrow} aria-hidden="true">↗</span>
    </Link>)}
  </nav>;
}
