"use client";
import {useEffect,useRef,useState,type ReactNode} from "react";
import s from "./listening.module.css";
import w from "./workspace.module.css";

export interface NavigatorQuestion {
  number:number;
  answered:boolean;
  status?:string;
  title:string;
}

/** Shared compact footer. Review supplies status metadata, never editor actions. */
export function WorkspaceNavigator({questions,current,navigation,onGo,description,legend,leading,trailing,error,placement="footer"}: {
  questions:NavigatorQuestion[];current:number;navigation:number;onGo:(n:number)=>void;description:string;legend:string;
  leading?:ReactNode;trailing?:ReactNode;error?:string;placement?:"footer"|"header";
}) {
  const dialog=useRef<HTMLDialogElement>(null);const trigger=useRef<HTMLButtonElement>(null);const jumping=useRef(false);
  const [expanded,setExpanded]=useState<number|null>(null);
  const open=expanded===navigation;
  useEffect(()=>{
    if(!open)return;
    const close=(event:KeyboardEvent)=>{if(event.key==="Escape"&&!document.querySelector("dialog[open]"))setExpanded(null);};
    document.addEventListener("keydown",close);
    return()=>document.removeEventListener("keydown",close);
  },[open]);
  function go(n:number){setExpanded(null);onGo(n);}
  if(placement==="header")return <>
    <button type="button" ref={trigger} className={w.headerQuestions} aria-label="Question navigator" aria-haspopup="dialog" onClick={()=>{dialog.current?.showModal();dialog.current?.querySelector<HTMLButtonElement>('[aria-current="true"]')?.focus();}}><svg width="14" height="14" viewBox="0 0 16 16" aria-hidden="true" fill="currentColor"><path d="M1 1h5v5H1zm9 0h5v5h-5zM1 10h5v5H1zm9 0h5v5h-5z"/></svg>Questions</button>
    <dialog ref={dialog} className={w.navigatorDialog} aria-label="Questions" onClose={()=>{if(!jumping.current)trigger.current?.focus({preventScroll:true});jumping.current=false;}} onClick={e=>{if(e.target===e.currentTarget){const r=e.currentTarget.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.currentTarget.close();}}}>
      <div className={w.navigatorHeading}><span>{description}</span><button type="button" aria-label="Close question navigator" onClick={()=>dialog.current?.close()}>×</button></div>
      <nav className={`${s.questionMap} ${w.headerQuestionMap}`} aria-label="Questions">{questions.map(q=><button type="button" key={q.number} aria-label={`Go to question ${q.number}`} aria-current={current===q.number?"true":undefined} title={q.title} data-answered={q.answered} onClick={()=>{jumping.current=true;dialog.current?.close();onGo(q.number);}}>{q.number}</button>)}</nav>
      <p className={w.navigatorLegend}>{legend}</p>
    </dialog>
  </>;
  return <footer className={`${s.footer} ${w.footer}`} onKeyDown={e=>{if(e.key==="Escape")setExpanded(null);}}>
    <div className={w.toolbar}>
      <button type="button" className={w.gridToggle} aria-label="Question navigator" aria-expanded={open} aria-controls="listening-question-grid" onClick={()=>setExpanded(v=>v===navigation?null:navigation)}>Questions <span aria-hidden="true">{open?"⌄":"⌃"}</span></button>
      {leading}
      <div className={w.steps}><button type="button" aria-label="Previous question" disabled={current<=1} onClick={()=>go(current-1)}>←</button><button type="button" aria-label="Next question" disabled={current>=questions.length} onClick={()=>go(current+1)}>→</button></div>
      {trailing}
    </div>
    <div id="listening-question-grid" className={w.gridPanel} hidden={!open}>
      <div className={w.gridHeading}><span>{description}</span><span>{legend}</span></div>
      <nav className={`${s.questionMap} ${w.questionMap}`} aria-label="Questions">{questions.map(q=><button type="button" key={q.number} aria-label={`Go to question ${q.number}`} aria-current={current===q.number?"true":undefined} title={q.title} data-answered={q.answered} data-review-status={q.status} onClick={()=>go(q.number)}>{q.number}</button>)}</nav>
    </div>
    {error&&<p role="alert">{error}</p>}
  </footer>;
}
