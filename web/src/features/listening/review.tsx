"use client";
import Link from "next/link";
import {useCallback,useRef,useState} from "react";
import type {Group,Question,Result,ResultRow} from "./models";
import {AudioProgress} from "./audio-progress";
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
    <div className={r.answerHeading}><p className={r.answerLine}><span>Your answer</span>{" "}<span className={r.answerValue} data-status={status}>{answer.trim()?answer:"No answer saved"}</span></p><span className={r.status} data-status={status}>{status==="correct"?"✓ ":status==="incorrect"?"× ":""}{reviewStatusLabel[status]}</span></div>
    {inlineOptions.length>0&&<ul className={r.options} aria-label={`Options for question ${question.question_number}`}>{inlineOptions.map(option=><li key={option.label} data-selected={selected.includes(option.label)}><span aria-hidden="true">{selected.includes(option.label)?"●":"○"}</span><b>{option.label}</b><span>{option.text&&option.text!==option.label?option.text:option.visual_reference?"Position in the original image":""}</span>{selected.includes(option.label)&&<span className={r.selectedLabel}>Your choice</span>}</li>)}</ul>}
    {(status==="incorrect"||status==="unanswered")&&key&&<div className={r.expected}><span>Correct answer</span><p>{key}</p></div>}
    {notGraded&&<p className={r.keyNotice}>{row?.grading_issue?`Not graded · ${row.grading_issue}. No reliable correction available.`:"Not graded · no reliable official answer key is available."}</p>}
  </div>;
}

/** Review owns only local navigation/playback state. It never creates a ListeningDraft. */
export function ListeningReview({result,uid}:{result:Result;uid:string}) {
  const [opened,setOpened]=useState<Set<number>>(()=>new Set()),[moment,setMoment]=useState<(Moment&{question:number})|undefined>();
  const explanationCache=useRef(new Map<string,AIExplanationData>()),momentRequest=useRef(0);
  const stopMoment=useCallback(()=>setMoment(undefined),[]);
  const [current,setCurrent]=useState(result.questions[0]?.question_number||1);
  const [navigation,setNavigation]=useState(0);
  const [filter,setFilter]=useState<Filter>("all");
  const [audioProgress]=useState(()=>new AudioProgress(uid,result.attempt_id,result.exam?.exam_id||result.attempt_id));
  const rows=new Map(result.questions.map(q=>[q.question_number,q]));
  const byId=new Map(result.questions.map(q=>[q.question_id,q]));
  const counts:Record<ReviewStatus,number>={correct:0,incorrect:0,unanswered:0,ungraded:0};
  result.questions.forEach(q=>counts[reviewStatus(q)]++);
  const filtered=result.questions.filter(q=>filter==="all"||reviewStatus(q)===filter);
  const visible=filter==="all"?undefined:new Set(filtered.map(q=>q.question_number));
  const part=rows.get(current)?.part_number||Math.ceil(current/10);
  const exam=result.exam;
  const graded=result.correct_count!==null;
  function focus(n:number){
    // Retire only a temporary AI clip; Player restores its saved origin.
    // Normal question/Part navigation leaves ordinary playback untouched.
    if(n!==current)setMoment(undefined);
    setCurrent(n);
  }
  function playMoment(number:number,data:AIExplanationData,loop:boolean){
    const e=data.evidence;if(!e.available||e.clip_start===null||e.clip_end===null)return;
    if(loop&&moment?.loop&&moment.question===number){setMoment(undefined);return;}
    setMoment({request:++momentRequest.current,part:e.part,start:e.clip_start,end:e.clip_end,loop,question:number});
  }
  const lastQuestions=useRef(new Map<number,number>());
  function viewPart(p:number){lastQuestions.current.set(part,current);const saved=lastQuestions.current.get(p);const next=filtered.find(q=>q.part_number===p&&q.question_number===saved)||filtered.find(q=>q.part_number===p)||result.questions.find(q=>q.part_number===p);if(next)go(next.question_number);}
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
      <div className={r.identity}><Link href={`/listening/attempts/${result.attempt_id}/results`}>← Results</Link><span className={r.testName}>· {exam?`Cambridge ${exam.book} · Test ${exam.printed_test_number}`:"Listening practice"}</span>
          <WorkspaceNavigator placement="header" navigation={navigation} current={current} onGo={go} questions={Array.from({length:result.total_questions},(_,i)=>{const number=i+1,row=rows.get(number),status=reviewStatus(row);return {number,answered:!!row?.user_answer.trim(),status,title:`Question ${number} · ${reviewStatusLabel[status]}`};})}
      description={`${result.answered_count}/${result.total_questions} answered${filter!=="all"?` · Showing ${filter}`:""}`} legend={graded?"Green: correct · Red: incorrect · Grey: unanswered · Blue: not graded":"Grey: unanswered · Blue: not graded"}
/></div>
      {exam&&<div className={w.audio}><Player compact uid={uid} attemptId={result.attempt_id} examId={exam.exam_id} initialPart={1} position={0} progress={audioProgress} visiblePart={part} onVisiblePart={viewPart} onCheckpoint={ignoreAnswer} onPart={p=>go((p-1)*10+1)} moment={moment} onMomentStop={stopMoment}/></div>}
    </header>
    {exam?<WorkspaceQuestions revealOnNavigate toolbar={<nav className={r.filters} aria-label="Review filters">{(["all","incorrect","unanswered"] as const).map(value=><button key={value} type="button" aria-pressed={filter===value} onClick={()=>applyFilter(value)}>{value==="all"?"All":value==="incorrect"?"Incorrect":"Unanswered"}{value!=="all"&&<span>{counts[value]}</span>}</button>)}</nav>} contentHash={result.content_hash} exam={exam} part={part} current={current} navigation={navigation} uid={uid} id={result.attempt_id} answers={Object.fromEntries(result.questions.map(q=>[q.question_id,q.user_answer]))} onAnswer={ignoreAnswer} onFocus={focus} disabled visibleQuestions={visible} questionStatus={q=>reviewStatus(byId.get(q.question_id))} renderAnswer={(question,group)=><><SavedAnswer row={byId.get(question.question_id)} question={question} group={group}/>{reviewStatus(byId.get(question.question_id))==="incorrect"&&reviewKey(byId.get(question.question_id))&&<div className={r.aiReview}><button type="button" aria-expanded={opened.has(question.question_number)} onClick={()=>{focus(question.question_number);setOpened(v=>{const next=new Set(v);if(next.has(question.question_number))next.delete(question.question_number);else next.add(question.question_number);return next;});}}><span aria-hidden="true">✧ </span>Explain with AI</button>{opened.has(question.question_number)&&<AIExplanation key={question.question_id} uid={uid} attemptId={result.attempt_id} number={question.question_number} initial={explanationCache.current.get(JSON.stringify([uid,result.attempt_id,question.question_number]))} onLoaded={data=>explanationCache.current.set(JSON.stringify([uid,result.attempt_id,question.question_number]),data)} onPlay={(data,loop)=>playMoment(question.question_number,data,loop)} looping={!!moment?.loop&&moment.question===question.question_number}/>}</div>}</>}/>:<section className={r.unavailable} role="status">Original question material is unavailable for this saved result. <Link href={`/listening/attempts/${result.attempt_id}/results`}>View the saved answer breakdown</Link>.</section>}

  </main>;
}
