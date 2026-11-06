"use client";
import Link from "next/link";
import {useCallback,useRef,useState} from "react";
import type {Group,Question,Result,ResultRow} from "./models";
import {Player,type Moment} from "./player";
import {AIExplanation,type AIExplanationData} from "./ai-explanation";
import {WorkspaceQuestions} from "./workspace-questions";
import {WorkspaceNavigator} from "./workspace-navigator";
import {reviewKey,reviewStatus,reviewStatusLabel,type ReviewStatus} from "./review-status";
import s from "./listening.module.css";
import w from "./workspace.module.css";
import r from "./review.module.css";

type Filter="all"|"incorrect"|"unanswered";
const ignoreAnswer=()=>{};

function SavedAnswer({row,question,group}: {row?:ResultRow;question:Question;group:Group}) {
  const status=reviewStatus(row),key=reviewKey(row);
  const answer=row?.user_answer||"";
  const options=question.options.length?question.options:group.answer_bank?.options||[];
  const selected=question.input_type==="multi_select"?answer.trim().split(/\s+/):[answer];
  const inlineOptions=group.answer_bank?options.filter(option=>selected.includes(option.label)):options;
  const notGraded=!row||row.correct===null||!!row.grading_issue;
  return <div className={r.savedAnswer}>
    <div className={r.answerHeading}><span>Your answer</span><span className={r.status} data-status={status}>{status==="correct"?"✓ ":status==="incorrect"?"× ":""}{reviewStatusLabel[status]}</span></div>
    <p className={r.answerValue} data-status={status}>{answer.trim()?answer:"No answer saved"}</p>
    {inlineOptions.length>0&&<ul className={r.options} aria-label={`Options for question ${question.question_number}`}>{inlineOptions.map(option=><li key={option.label} data-selected={selected.includes(option.label)}><span aria-hidden="true">{selected.includes(option.label)?"●":"○"}</span><b>{option.label}</b><span>{option.text&&option.text!==option.label?option.text:option.visual_reference?"Position in the original image":""}</span>{selected.includes(option.label)&&<span className={r.selectedLabel}>Your choice</span>}</li>)}</ul>}
    {(status==="incorrect"||status==="unanswered")&&key&&<div className={r.expected}><span>Correct answer</span><p>{key}</p></div>}
    {notGraded&&<p className={r.keyNotice}>{row?.grading_issue?`Not graded · ${row.grading_issue}. No reliable correction available.`:"Not graded · no reliable official answer key is available."}</p>}
  </div>;
}

/** Review owns only local navigation/playback state. It never creates a ListeningDraft. */
export function ListeningReview({result,uid}:{result:Result;uid:string}) {
  const [opened,setOpened]=useState<number|null>(null),[moment,setMoment]=useState<(Moment&{question:number})|undefined>();
  const explanationCache=useRef(new Map<number,AIExplanationData>()),momentRequest=useRef(0);
  const cacheExplanation=useCallback((data:AIExplanationData)=>{if(opened!==null)explanationCache.current.set(opened,data);},[opened]);
  const stopMoment=useCallback(()=>setMoment(undefined),[]);
  const [current,setCurrent]=useState(result.questions[0]?.question_number||1);
  const [navigation,setNavigation]=useState(0);
  const [filter,setFilter]=useState<Filter>("all");
  const [audioOpen,setAudioOpen]=useState(false),[audioPart,setAudioPart]=useState(1),[replay,setReplay]=useState(0);
  const rows=new Map(result.questions.map(q=>[q.question_number,q]));
  const byId=new Map(result.questions.map(q=>[q.question_id,q]));
  const counts:Record<ReviewStatus,number>={correct:0,incorrect:0,unanswered:0,ungraded:0};
  result.questions.forEach(q=>counts[reviewStatus(q)]++);
  const filtered=result.questions.filter(q=>filter==="all"||reviewStatus(q)===filter);
  const visible=filter==="all"?undefined:new Set(filtered.map(q=>q.question_number));
  const part=rows.get(current)?.part_number||Math.ceil(current/10);
  const exam=result.exam;
  const graded=result.correct_count!==null;
  function focus(n:number){if(n!==current){setOpened(null);setMoment(undefined);}setCurrent(n);}
  function playMoment(data:AIExplanationData,loop:boolean){
    const e=data.evidence;if(!e.available||e.clip_start===null||e.clip_end===null||opened===null)return;
    if(loop&&moment?.loop&&moment.question===opened){setMoment(undefined);return;}
    setAudioOpen(true);setAudioPart(e.part);setMoment({request:++momentRequest.current,part:e.part,start:e.clip_start,end:e.clip_end,loop,question:opened});
  }
  function go(n:number) {
    if(visible&&!visible.has(n))setFilter("all");
    focus(n);setNavigation(v=>v+1);
  }
  function applyFilter(value:Filter) {
    setFilter(value);
    const matches=result.questions.filter(q=>value==="all"||reviewStatus(q)===value);
    if(value!=="all"&&!matches.some(q=>q.question_number===current))focus(matches.find(q=>q.part_number===part)?.question_number||matches[0]?.question_number||current);
    setNavigation(v=>v+1);
  }
  return <main id="main" className={`${s.workspace} ${w.workspace} ${r.review}`}>
    <header className={w.topbar}>
      <div className={r.identity}><Link href={`/listening/attempts/${result.attempt_id}/results`}>← Results</Link><h1>Review your answers</h1><span>{exam?`Cambridge ${exam.book} · Test ${exam.printed_test_number}`:"Listening practice"}</span><Link className={r.library} href="/listening">Library ↗</Link></div>
      <dl className={r.metrics} aria-label="Listening review result">
        <div><dt>Score</dt><dd>{graded?`${result.correct_count} / ${result.total_questions}`:"Not scored"}</dd></div>
        {result.estimated_band!==null&&<div><dt>Estimated Band</dt><dd>{result.estimated_band.toFixed(1)}</dd></div>}
        <div><dt>Correct</dt><dd data-status={graded?"correct":undefined}>{graded?counts.correct:"—"}</dd></div>
        <div><dt>Incorrect</dt><dd data-status={graded?"incorrect":undefined}>{graded?counts.incorrect:"—"}</dd></div>
        <div><dt>Unanswered</dt><dd>{counts.unanswered}</dd></div>
        {counts.ungraded>0&&<div><dt>Not graded</dt><dd>{counts.ungraded}</dd></div>}
      </dl>
      {result.graded_count<result.total_questions&&<p className={r.keyNotice}>Partial score · {result.graded_count}/{result.total_questions} questions graded.</p>}
      <div className={r.controls}>
        <nav className={s.tabs} aria-label="Review parts">{[1,2,3,4].map(p=><button type="button" key={p} aria-pressed={part===p} onClick={()=>{const next=filtered.find(q=>q.part_number===p)||result.questions.find(q=>q.part_number===p);if(next)go(next.question_number);setMoment(undefined);setAudioPart(p);}}>Part {p}</button>)}</nav>
        <nav className={r.filters} aria-label="Review filters"><button type="button" aria-pressed={filter==="all"} onClick={()=>applyFilter("all")}>All</button>{counts.incorrect>0&&<button type="button" aria-pressed={filter==="incorrect"} onClick={()=>applyFilter("incorrect")}>Incorrect <span>{counts.incorrect}</span></button>}{counts.unanswered>0&&<button type="button" aria-pressed={filter==="unanswered"} onClick={()=>applyFilter("unanswered")}>Unanswered <span>{counts.unanswered}</span></button>}</nav>
        {exam&&<button type="button" className={r.audioToggle} aria-expanded={audioOpen} aria-controls="review-audio" onClick={()=>{setMoment(undefined);setAudioOpen(v=>!v);}}>{audioOpen?"Hide audio":"Listen again"}<span aria-hidden="true"> {audioOpen?"⌃":"⌄"}</span></button>}
      </div>
      {audioOpen&&exam&&<div id="review-audio" className={r.audioRow}><div className={r.audioPart}><label htmlFor="review-audio-part">Audio</label><select id="review-audio-part" value={audioPart} onChange={e=>{setMoment(undefined);setAudioPart(Number(e.target.value));}}>{[1,2,3,4].map(p=><option key={p} value={p}>Part {p}</option>)}</select><button type="button" onClick={()=>{setMoment(undefined);setReplay(v=>v+1);}}>Replay part</button></div><div className={w.audio}><Player key={replay} uid={uid} attemptId={result.attempt_id} book={exam.book} part={audioPart} position={0} onCheckpoint={ignoreAnswer} onPart={p=>{setMoment(undefined);setAudioPart(p);}} moment={moment} onMomentStop={stopMoment}/></div></div>}
    </header>
    {exam?<WorkspaceQuestions exam={exam} part={part} current={current} navigation={navigation} uid={uid} id={result.attempt_id} answers={Object.fromEntries(result.questions.map(q=>[q.question_id,q.user_answer]))} onAnswer={ignoreAnswer} onFocus={focus} disabled visibleQuestions={visible} questionStatus={q=>reviewStatus(byId.get(q.question_id))} renderAnswer={(question,group)=><><SavedAnswer row={byId.get(question.question_id)} question={question} group={group}/>{reviewStatus(byId.get(question.question_id))==="incorrect"&&<div className={r.aiReview}><button type="button" aria-expanded={opened===question.question_number} onClick={()=>{focus(question.question_number);setMoment(undefined);setOpened(v=>v===question.question_number?null:question.question_number);}}>Explain with AI</button>{opened===question.question_number&&<AIExplanation key={question.question_id} uid={uid} attemptId={result.attempt_id} number={question.question_number} initial={explanationCache.current.get(question.question_number)} onLoaded={cacheExplanation} onPlay={playMoment} looping={!!moment?.loop&&moment.question===question.question_number}/>}</div>}</>}/>:<section className={r.unavailable} role="status">Original question material is unavailable for this saved result. <Link href={`/listening/attempts/${result.attempt_id}/results`}>View the saved answer breakdown</Link>.</section>}
    <WorkspaceNavigator navigation={navigation} current={current} onGo={go} questions={Array.from({length:result.total_questions},(_,i)=>{const number=i+1,row=rows.get(number),status=reviewStatus(row);return {number,answered:!!row?.user_answer.trim(),status,title:`Question ${number} · ${reviewStatusLabel[status]}`};})}
      description={`${result.answered_count}/${result.total_questions} answered${filter!=="all"?` · Showing ${filter}`:""}`} legend={graded?"Green: correct · Red: incorrect · Grey: unanswered · Blue: not graded":"Grey: unanswered · Blue: not graded"}
      leading={<span className={r.readOnly}>Read-only review</span>}/>
  </main>;
}
