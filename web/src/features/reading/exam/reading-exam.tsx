"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useLayoutEffect, useRef, useState, useSyncExternalStore } from "react";
import type { Attempt, PassageViewState, Question } from "./models";
import { allQuestions } from "./models";
import { AnswerSession, type SaveAnswers } from "./answers";
import { readingApi } from "./api";
import { parseAttempt } from "./parse";
import { PassagePane } from "./passage-pane";
import { QuestionGroup, type QuestionActions } from "./question-renderer";
import { readingMessage } from "./messages";
import { ApiError } from "@/lib/api/client";
import type { ReliableAnswers, ReliableSnapshot } from "./reliable-answers";
import type { Highlight } from "./draft-storage";
import { elapsedSeconds,remainingSeconds } from "./clock";
import type { ReadingResult } from "./results";
import styles from "./exam.module.css";
import {browserDraftStore} from "./draft-storage";
import {useReadingAI,ReadingAIExplanation} from "../ai/explanation";
import aiStyles from "../ai/review.module.css";
import { canTranslateAttempt } from "../translate/context";

function Deadline({ deadline, serverNow, expired }: { deadline: string | null; serverNow: string; expired: () => void }) {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    const start = performance.now(), wall = Date.now();
    const tick = () => setElapsed(elapsedSeconds(start,wall,performance.now(),Date.now()));
    const timer = setInterval(tick, 1000);
    const visible = () => { if (!document.hidden) tick(); };
    document.addEventListener("visibilitychange", visible);
    return () => { clearInterval(timer); document.removeEventListener("visibilitychange", visible); };
  }, []);
  const seconds = deadline ? remainingSeconds(deadline,serverNow,elapsed) : null;
  useEffect(() => { if (seconds === 0) expired(); }, [seconds, expired]);
  return <span className="exam-timer" aria-label={seconds === null ? "Untimed practice" : `Time remaining ${Math.floor(seconds / 60)} minutes ${seconds % 60} seconds`}>
    {seconds === null ? "Untimed" : `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`}
  </span>;
}
export function ReadingExam({ attempt, uid, save, controller, result, reviewQuestionId }: { attempt: Attempt; uid: string; save?: SaveAnswers; controller?:ReliableAnswers; result?:ReadingResult; reviewQuestionId?:string }) {
  const router = useRouter();
  const exam = attempt.exam!;
  const translationOwner = JSON.stringify([uid, attempt.id]);
  const [translationCatalog, setTranslationCatalog] = useState<{ owner: string; value: unknown }>();
  useEffect(() => {
    const abort = new AbortController();
    void readingApi(uid)("/reading/books", abort.signal).then(value => {
      if (!abort.signal.aborted) setTranslationCatalog({ owner: translationOwner, value });
    }).catch(() => { /* Translation stays unavailable until the private policy is verified. */ });
    return () => abort.abort();
  }, [uid, translationOwner]);
  const translationAllowed = translationCatalog?.owner === translationOwner && canTranslateAttempt(attempt, translationCatalog.value);
  // Review-only deep links resolve an exact ID against this attempt’s snapshot.
  const reviewQuestion=result&&reviewQuestionId?allQuestions(exam).find(q=>q.id===reviewQuestionId):undefined;
  const reviewPassage=reviewQuestion?exam.passages.find(p=>p.question_groups.some(g=>g.questions.some(q=>q.id===reviewQuestion.id)))?.number:undefined;
  const [legacy] = useState(() => new AnswerSession(attempt, save ?? (async (event) => parseAttempt(await readingApi(uid)(`/reading/attempts/${attempt.id}/sync`, undefined, { method: "POST", body: event })))));
  const editor=controller??legacy;
  const state = useSyncExternalStore<ReturnType<AnswerSession["snapshot"]>|ReliableSnapshot>(editor.subscribe, editor.snapshot, editor.snapshot);
  const advanced=controller?state as ReliableSnapshot:undefined;
  const saved=advanced?.view;
  const [highlights,setHighlights]=useState<Highlight[]>(saved?.highlights??[]);
  const [viewRevision,changeView]=useState(0);
  const scrollTimer=useRef<ReturnType<typeof setTimeout>|undefined>(undefined);
  useEffect(()=>()=>clearTimeout(scrollTimer.current),[]);
  const finishModal=useRef<HTMLDialogElement>(null),finishButton=useRef<HTMLButtonElement>(null);
  const [choices,setChoices]=useState<Record<string,"local"|"server">>({});
  const conflictModal=useRef<HTMLDialogElement>(null);
  useEffect(()=>{if(advanced?.conflicts.length&&!conflictModal.current?.open)conflictModal.current?.showModal();else if(!advanced?.conflicts.length)conflictModal.current?.close()},[advanced?.conflicts]);
  useEffect(()=>{
    if(!controller)return;
    const refresh=()=>{if(!document.hidden)void controller.refresh()};
    window.addEventListener("pagehide",controller.suspend);window.addEventListener("pageshow",controller.resume);
    window.addEventListener("online",refresh);window.addEventListener("focus",refresh);document.addEventListener("visibilitychange",refresh);
    const timer=setInterval(refresh,30000);
    return()=>{window.removeEventListener("pagehide",controller.suspend);window.removeEventListener("pageshow",controller.resume);clearInterval(timer);window.removeEventListener("online",refresh);window.removeEventListener("focus",refresh);document.removeEventListener("visibilitychange",refresh)};
  },[controller]);
  useEffect(()=>{if(advanced?.phase==="terminal"&&!advanced.rejected)router.replace(`/reading/attempts/${attempt.id}/result`)},[advanced?.phase,advanced?.rejected,attempt.id,router]);
  const [passage, setPassage] = useState(reviewPassage ?? saved?.passage ?? exam.passages.find((p) => p.number === attempt.state.current_passage)?.number ?? exam.passages[0]!.number);
  const [navigation, setNavigation] = useState(0);
  const [visited, setVisited] = useState(() => new Set([reviewPassage ?? saved?.passage ?? exam.passages.find((p) => p.number === attempt.state.current_passage)?.number ?? exam.passages[0]!.number]));
  const [current, setCurrent] = useState<string | null>(reviewQuestion?.id??saved?.current??null);
  const ai=useReadingAI(uid,attempt.id,exam,current);
  const [evidenceFor,setEvidenceFor]=useState<string|null>(null);
  const evidenceJump=useRef(false);
  const aiData=result&&ai.active?ai.state.data:undefined;
  useEffect(()=>{
    if(!result)return;let active=true;
    void browserDraftStore(uid,attempt.id,attempt.content_hash,'review-readonly').read().then(d=>{if(active&&d?.view?.highlights)setHighlights(d.view.highlights);}).catch(()=>{});
    return()=>{active=false;};
  },[uid,attempt.id,attempt.content_hash,result]);
  const [review, setReview] = useState<Set<string>>(() => new Set(saved?.review??[]));
  const [size, setSize] = useState(result ? saved?.size??16 : 18); const [split, setSplit] = useState(saved?.split??50);
  const sizeKey = `alua:reading:text-size:v2:${uid}`;
  useEffect(() => {
    if (result) return;
    let active = true;
    queueMicrotask(() => {
      try {
        const stored = Number(localStorage.getItem(sizeKey));
        if (active && [16, 18, 20].includes(stored)) setSize(stored);
      } catch { /* Reading preferences remain optional. */ }
    });
    return () => { active = false; };
  }, [result, sizeKey]);
  function changeSize(value: number) {
    setSize(value);
    try { localStorage.setItem(sizeKey, String(value)); } catch { /* Keep available in memory. */ }
  }

  const [mobile, setMobile] = useState<"passage" | "questions">(reviewQuestion?"questions":saved?.mobile??"passage");
  const [expiredRevision,setExpiredRevision]=useState(-1);
  const timeOver=expiredRevision===(advanced?.clock.revision??0);
  const left = useRef<HTMLDivElement>(null); const right = useRef<HTMLDivElement>(null); const workspace = useRef<HTMLDivElement>(null);
  const view = useRef(new Map<number, PassageViewState>(saved?.views??[]));
  const nodes = useRef(new Map<string, HTMLElement>());
  const jump = useRef<string | null>(reviewQuestion?.id??null); const modal = useRef<HTMLDialogElement>(null); const allButton = useRef<HTMLButtonElement>(null);
  const active = exam.passages.find((p) => p.number === passage)!;
  const questions = allQuestions(exam);
  const expired = useCallback(() => {setExpiredRevision(advanced?.clock.revision??0);if(controller)void controller.refresh()}, [controller,advanced?.clock.revision]);
  const remember = useCallback(() => {
    const previous = view.current.get(passage);
    // A mobile panel with display:none reports scrollTop=0. Preserve its last visible offset.
    view.current.set(passage, { passageId: active.id,
      textScrollTop: left.current?.clientHeight ? left.current.scrollTop : previous?.textScrollTop ?? 0,
      questionsScrollTop: right.current?.clientHeight ? right.current.scrollTop : previous?.questionsScrollTop ?? 0,
      lastFocusedQuestionId: current });
  }, [passage, active.id, current]);
  useEffect(()=>{
    if(controller)controller.saveView({passage,current,review:[...review],size,split,mobile,views:[...view.current],highlights});
  },[controller,passage,current,review,size,split,mobile,highlights,viewRevision]);
  function selectPassage(number: number) { remember(); setVisited((previous) => new Set(previous).add(number)); setPassage(number); setCurrent(view.current.get(number)?.lastFocusedQuestionId ?? null); }
  function go(q: Question) {
    remember(); const next = exam.passages.find((p) => p.question_numbers.includes(q.number))!;
    jump.current = q.id; setVisited((previous) => new Set(previous).add(next.number)); setNavigation((n) => n + 1); setCurrent(q.id); setPassage(next.number); setMobile("questions");
    if (modal.current?.open) { modal.current.close(); allButton.current?.focus({ preventScroll: true }); }
  }
  useLayoutEffect(() => {
    const previous = view.current.get(passage);
    if (left.current) left.current.scrollTop = previous?.textScrollTop ?? 0;
    if (right.current) right.current.scrollTop = previous?.questionsScrollTop ?? 0;
    const id = jump.current;
    if (id) {
      const target = nodes.current.get(id);
      if (target && right.current) {
        right.current.scrollTop += target.getBoundingClientRect().top - right.current.getBoundingClientRect().top - 20;
        if(result)target.focus({preventScroll:true});
        else target.querySelector<HTMLElement>("input,select,button")?.focus({ preventScroll: true });
      }
      jump.current = null;
    }
    if(evidenceJump.current&&left.current){
      const mark=left.current.querySelector<HTMLElement>('[data-reading-ai="true"]');
      if(mark){left.current.scrollTop+=mark.getBoundingClientRect().top-left.current.getBoundingClientRect().top-60;mark.focus({preventScroll:true});}
      evidenceJump.current=false;
    }
  }, [passage, mobile, navigation,result]);

  useEffect(() => {
    const prevent = (event: BeforeUnloadEvent) => { if (editor.snapshot().dirty || editor.snapshot().saving || controller?.snapshot().localSaving) event.preventDefault(); };
    window.addEventListener("beforeunload", prevent);
    return () => { window.removeEventListener("beforeunload", prevent); };
  }, [editor,controller]);
  useEffect(() => { editor.mount(); return () => editor.unmount(); }, [editor]);
  const toggleReview = (id: string) => setReview((previous) => { const next = new Set(previous); if (next.has(id)) next.delete(id); else next.add(id); return next; });
  const verdicts=new Map(result?.positions.map(p=>[p.question_id,p]));
  const actions: QuestionActions = { explain:result?{isOpen:(id)=>ai.forQuestion(id).active,open:(id)=>{setCurrent(id);const card=ai.forQuestion(id);if(card.active)card.close();else void card.open(id);},render:(q)=>ai.forQuestion(q.id).active&&<ReadingAIExplanation key={q.id} verdict={verdicts.get(q.id)} question={q} ai={ai.forQuestion(q.id)} onShow={()=>{remember();setCurrent(q.id);setEvidenceFor(q.id);evidenceJump.current=true;setMobile('passage');setNavigation(n=>n+1);}}/>}:undefined, answers: state.answers, review, locked: new Set(attempt.state.checked_question_ids), disabled: state.terminal || timeOver || !!result || !!advanced?.localError || advanced?.otherTab || advanced?.phase!==undefined&&advanced.phase!=="in_progress" || !!advanced?.conflicts.length || !controller&&state.error instanceof ApiError && state.error.status === 409, results:result?.positions, change: editor.change, toggleReview, register: (id, node) => { if (node) nodes.current.set(id, node); else nodes.current.delete(id); }, focus: setCurrent };
  function chooseConflict(id:string,choice:"local"|"server") {
    const group=exam.passages.flatMap(p=>p.question_groups).find(g=>g.questions.some(q=>q.id===id));
    const ids=group?.type==="multiple_choice_multiple"?group.questions.map(q=>q.id):[id];
    setChoices(v=>({...v,...Object.fromEntries(ids.map(q=>[q,choice]))}));
  }
  function numberButton(q: Question) {
    const answered = !!state.answers[q.id]?.trim(); const marked = review.has(q.id);
    return <button type="button" key={q.id} className={`question-nav-number ${answered ? "answered" : ""} ${marked ? "marked" : ""}`} aria-label={`Question ${q.number}${answered ? ", answered" : ", unanswered"}${marked ? ", marked for review" : ""}`} aria-current={current === q.id ? "true" : undefined} onClick={() => go(q)}>{q.number}{marked && <span aria-hidden="true">·</span>}</button>;
  }
  return <main id="main" className={`reading-exam ${result?"":styles.focus}`} data-mobile-panel={mobile}>
    <header className="exam-header"><Link className="wordmark" href="/reading" aria-label="Back to Reading" onNavigate={(event) => {
      if (state.dirty || state.saving) {
        event.preventDefault();
        void editor.flush().then(() => { if (!editor.snapshot().dirty && !editor.snapshot().error) router.push("/reading"); });
      }
    }}>alua.</Link><span className="exam-title">Cambridge {exam.source_book} <span>· Test {exam.source_test_number}</span></span>{result?<Link className="text-link exam-result-link" href={`/reading/attempts/${attempt.id}/result`}>Result</Link>:<div className="exam-session-actions"><Deadline key={advanced?.clock.revision??0} deadline={advanced?.clock.deadline??attempt.deadline_at} serverNow={advanced?.clock.serverNow??attempt.server_now} expired={expired} />{controller&&<button type="button" className="text-button" ref={finishButton} disabled={state.terminal||advanced?.otherTab||!!advanced?.localError||advanced?.phase!=="in_progress"} onClick={()=>finishModal.current?.showModal()}>Finish</button>}</div>}</header>
    <nav className="passage-tabs" aria-label="Reading passages">{exam.passages.map((p) => <button type="button" key={p.id} aria-current={passage === p.number ? "true" : undefined} onClick={() => selectPassage(p.number)}>Passage {p.number}</button>)}</nav>
    <div className="exam-tools">{result&&<div className="font-controls" aria-label="Passage text size"><button type="button" disabled={size <= 14} onClick={() => setSize((n) => n - 1)} aria-label="Decrease passage text size">A−</button><button type="button" disabled={size >= 22} onClick={() => setSize((n) => n + 1)} aria-label="Increase passage text size">A+</button></div>}
      <span className="save-status" role="status">{result?"Review · Read only":advanced?.rejected?(advanced.rejectionReason==="deadline"?"Deadline passed — local answers were not accepted":"Server result differs — local answers retained"):advanced?.otherTab?"Open in another tab · Read only":advanced?.localError?"Device save failed":advanced?.phase==="submission_unknown"?"Submission unknown — retry safely":advanced?.phase==="finalizing"?"Finishing…":advanced?.conflicts.length?"Conflict":advanced?.localSaving?"Saving on device…":advanced?.offline?"Offline — saved on device":state.error?controller?"Save failed · Retry":"Not saved":state.saving?"Syncing…":advanced?.dirty?"Saved on device":"All changes saved"}</span>
      <div className="mobile-panels"><button type="button" aria-pressed={mobile === "passage"} onClick={() => { remember(); setMobile("passage"); }}>Passage</button><button type="button" aria-pressed={mobile === "questions"} onClick={() => { remember(); setMobile("questions"); }}>Questions</button></div>
    </div>
    {(state.error || advanced?.localError || advanced?.otherTab || timeOver || result && attempt.not_fully_proofread) && <div className="exam-notice">
      {advanced?.rejected?<><span role="alert">{advanced.rejectionReason==="deadline"?"Deadline passed. ":"Another final snapshot was accepted. "}Local unaccepted answers are retained on this device; only server-accepted answers were graded.</span><Link href={`/reading/attempts/${attempt.id}/result`}>View server result</Link></>:advanced?.localError?<><span role="alert">Local storage failed. Keep this page open; answers are not safely stored on this device. Reload only after server save is confirmed.</span><button type="button" onClick={()=>void controller?.retryStorage()}>Retry device save</button></>:advanced?.otherTab?<span role="alert">This attempt is being edited in another tab. Close that tab, then reload here to continue.</span>:state.error ? <><span role="alert">{readingMessage(state.error)}</span>{(!advanced?.conflicts.length && (controller || !(state.error instanceof ApiError && state.error.status === 409))) && <button type="button" onClick={() => void editor.flush()}>Retry save</button>}{controller?.canReturnToTest()&&<button type="button" onClick={controller.returnToTest}>Return to test</button>}</> : timeOver ? <span>Time has elapsed. Editing is paused while the server confirms expiry. Local unsent answers may not be included.</span> : <span>Private practice · This test has not been fully proofread.</span>}
    </div>}
    <div className="exam-workspace" ref={workspace} style={{ "--passage-width": `${split}%` } as React.CSSProperties}>
      <div className="passage-scroll exam-scroll" ref={left} onScroll={()=>{remember();clearTimeout(scrollTimer.current);scrollTimer.current=setTimeout(()=>changeView(n=>n+1),200)}} aria-label="Reading passage" tabIndex={0}>{result&&aiData&&evidenceFor===current&&<button type="button" className={aiStyles.back} onClick={()=>{setMobile('questions');setNavigation(n=>n+1);requestAnimationFrame(()=>{const card=right.current?.querySelector<HTMLElement>(`[id="reading-ai-${current}"]`);if(card&&right.current){right.current.scrollTop+=card.getBoundingClientRect().top-right.current.getBoundingClientRect().top-52;card.focus({preventScroll:true});}});}}>← Back to Q{questions.find(q=>q.id===current)?.number}</button>}<PassagePane evidence={aiData?.review.evidence} evidenceQuestion={questions.find(q=>q.id===current)?.number} comfort={!result?{uid,attemptId:attempt.id,onSizeChange:changeSize}:undefined} passage={active} translation={translationAllowed?{uid,attemptId:attempt.id}:undefined} size={size} highlights={highlights} onHighlights={controller?setHighlights:undefined} /></div>
      <div className="column-separator" role="separator" aria-label="Resize passage and questions" aria-orientation="vertical" aria-valuemin={40} aria-valuemax={60} aria-valuenow={Math.round(split)} tabIndex={0}
        onKeyDown={(e) => { if (["ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key)) { e.preventDefault(); setSplit((n) => e.key === "Home" ? 40 : e.key === "End" ? 60 : Math.max(40, Math.min(60, n + (e.key === "ArrowRight" ? 2 : -2)))); } }}
        onPointerDown={(e) => { e.currentTarget.setPointerCapture(e.pointerId); }} onPointerMove={(e) => { if (!e.currentTarget.hasPointerCapture(e.pointerId) || !workspace.current) return; const rect = workspace.current.getBoundingClientRect(); setSplit(Math.max(40, Math.min(60, (e.clientX - rect.left) / rect.width * 100))); }} onPointerUp={(e) => e.currentTarget.releasePointerCapture(e.pointerId)} />
      <div className="questions-scroll exam-scroll" style={result?{overflowAnchor:"none"}:undefined} ref={right} onScroll={()=>{remember();clearTimeout(scrollTimer.current);scrollTimer.current=setTimeout(()=>changeView(n=>n+1),200)}} aria-label="Reading questions" tabIndex={0}>
        {exam.passages.map((p) => <section key={p.id} hidden={p.number !== passage} aria-label={`Questions for passage ${p.number}`}>
          <p className="eyebrow questions-heading">Questions {p.question_numbers[0]}–{p.question_numbers.at(-1)}</p>
          {p.question_groups.map((g) => <div key={g.id}><QuestionGroup group={g} actions={actions} uid={uid} active={visited.has(p.number)} /></div>)}
        </section>)}
      </div>
    </div>
    <footer className="question-navigation"><nav aria-label="Questions in current passage">{questions.filter((q) => active.question_numbers.includes(q.number)).map(numberButton)}</nav><button type="button" className="all-questions" ref={allButton} onClick={() => modal.current?.showModal()}>All {questions.length}</button></footer>
    <dialog ref={modal} className={`all-questions-dialog ${result?"":styles.navigator}`} aria-labelledby="all-questions-title" onClose={() => allButton.current?.focus({ preventScroll: true })}>
      <div className="dialog-title"><h2 id="all-questions-title">All questions</h2><button type="button" onClick={() => modal.current?.close()} aria-label="Close question overview">×</button></div>
      {!result&&<p className={styles.progress}>{questions.filter(q=>state.answers[q.id]?.trim()).length} of {questions.length} answered</p>}
      {exam.passages.map((p) => <section key={p.id}><h3>Passage {p.number}</h3><div className="question-overview-grid">{questions.filter((q) => p.question_numbers.includes(q.number)).map(numberButton)}</div></section>)}
      {result?<p className="small-note">Review marks are saved on this device when local drafts are available.</p>:<div className={styles.legend} aria-label="Question status legend"><span><i className={styles.answeredKey} aria-hidden="true"/>Answered</span><span><i className={styles.unansweredKey} aria-hidden="true"/>Unanswered</span><span><i className={styles.reviewKey} aria-hidden="true"/>Review</span></div>}
    </dialog>
    {controller&&<dialog ref={finishModal} className={`all-questions-dialog ${styles.finish}`} aria-labelledby="finish-title" aria-describedby="finish-summary finish-warning" onClose={()=>finishButton.current?.focus({preventScroll:true})}>
      <h2 id="finish-title">Finish your test?</h2><p id="finish-summary" className={styles.finishSummary}>{questions.filter(q=>state.answers[q.id]?.trim()).length} of {questions.length} questions answered.</p>
      <p>{questions.filter(q=>!state.answers[q.id]?.trim()).length} unanswered · {review.size} marked for review.</p>
      <p id="finish-warning" className={styles.finishWarning}>Once submitted, this attempt cannot be reopened.</p>
      {(state.dirty>0||state.saving||advanced?.localSaving)&&<p className={styles.pending} role="status">Pending answers must be accepted by the server before submission.</p>}
      <div className="dialog-actions"><button type="button" autoFocus onClick={()=>finishModal.current?.close()}>Return to test</button><button type="button" disabled={!!advanced?.localError||!!advanced?.conflicts.length||advanced?.phase!=="in_progress"} onClick={()=>{finishModal.current?.close();void controller.finish()}}>Finish test</button></div>
    </dialog>}
    {controller&&<dialog ref={conflictModal} className="all-questions-dialog" aria-labelledby="conflict-title" onCancel={e=>e.preventDefault()}>
      <h2 id="conflict-title">Choose which answers to keep</h2><p>Another device changed these answers. Both versions are retained until you choose.</p>
      {advanced?.conflicts.map(c=><fieldset key={c.id}><legend>Question {questions.find(q=>q.id===c.id)?.number}</legend>
        <label><input type="radio" name={`conflict-${c.id}`} checked={choices[c.id]==="local"} onChange={()=>chooseConflict(c.id,"local")}/> This device: {c.local||"Blank"}</label>
        <label><input type="radio" name={`conflict-${c.id}`} checked={choices[c.id]==="server"} onChange={()=>chooseConflict(c.id,"server")}/> Server: {c.server||"Blank"}</label>
      </fieldset>)}<button type="button" disabled={advanced?.conflicts.some(c=>!choices[c.id])} onClick={()=>{controller.resolve(choices);setChoices({})}}>Save chosen answers</button>
    </dialog>}
  </main>;
}
