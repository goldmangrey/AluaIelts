"use client";
import Link from "next/link";
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
  if (session.status === "signed_out") return <CatalogError error={new ApiError(401, "sign_in_required")} retry={() => {}} returnPath={pathname} />;
  if (session.status === "error") return <CatalogError error={session.error instanceof ApiError ? session.error : new ApiError(0, "network_error")} retry={() => { void retrySession().catch(() => {}); }} returnPath={pathname} />;
  if (session.status === "loading" || state.kind === "loading" || state.owner !== session.generation) return <p className="loading-text" role="status">Loading practice tests…</p>;
  if (state.kind === "error") return <CatalogError returnPath={pathname} error={state.error} retry={() => { setState({ kind: "loading" }); setRevision((r) => r + 1); }} />;
  const book = state.books.find((book) => book.book_number === bookNumber);
  if (bookNumber && !book) return <StatusPanel title="Collection unavailable." href="/reading" label="Back to Reading">
    This collection has no available practice tests.
  </StatusPanel>;
  if (examId) {
    const exam = book?.exams.find((exam) => exam.exam_id === examId);
    if (!exam) return <StatusPanel title="Test unavailable." href="/reading" label="Back to Reading">
      This test is currently unavailable for practice.
    </StatusPanel>;
    const hasAttempt = exam.in_progress_attempt_ids.length > 0;
    return <section className="test-preparation" aria-label="Test details">
      <dl className="test-facts"><div><dt>Time</dt><dd>60 <span>minutes</span></dd></div>
        <div><dt>Reading</dt><dd>{exam.passage_count} <span>passages</span></dd></div>
        <div><dt>Questions</dt><dd>{exam.question_count} <span>questions</span></dd></div></dl>
      {exam.not_fully_proofread && <p className="small-note">This test is available for private practice and has not been fully proofread.</p>}
      {hasAttempt && <p className="small-note">You have an unfinished attempt. Your existing progress is preserved.</p>}
      <StartButton examId={exam.exam_id} uid={session.user!.uid} learnerId={session.profile!.uid} hasAttempt={hasAttempt} />
    </section>;
  }
  if (book) return <nav className="test-list" aria-label="Available tests">{book.exams.map((exam) =>
    <Link className="list-row" key={exam.exam_id} href={`/reading/cambridge-${book.book_number}/${exam.exam_id}`}>
      <span>Test {exam.source_test_number}</span><span className="row-end">{exam.in_progress_attempt_ids.length > 0 && <small>In progress</small>}<span aria-hidden="true">→</span></span>
    </Link>)}
  </nav>;
  if (!state.books.length) return <StatusPanel title="No practice tests available.">Please check back soon.</StatusPanel>;
  return <nav className="book-grid" aria-label="Cambridge IELTS collections">{state.books.map((book) =>
    <Link className="book-card" key={book.book_number} href={`/reading/cambridge-${book.book_number}`}>
      <span>Cambridge {String(book.book_number).padStart(2, "0")}</span><span aria-hidden="true">→</span>
    </Link>)}
  </nav>;
}
