"use client";
import {useEffect,useState,type ReactNode} from "react";
import s from "./listening.module.css";
import w from "./workspace.module.css";

export interface NavigatorQuestion {
  number:number;
  answered:boolean;
  marked?:boolean;
  status?:string;
  title:string;
}

/** Shared compact footer. Review supplies status metadata, never editor actions. */
export function WorkspaceNavigator({questions,current,navigation,onGo,description,legend,leading,trailing,error}: {
  questions:NavigatorQuestion[];current:number;navigation:number;onGo:(n:number)=>void;description:string;legend:string;
  leading?:ReactNode;trailing?:ReactNode;error?:string;
}) {
  const [expanded,setExpanded]=useState<number|null>(null);
  const open=expanded===navigation;
  useEffect(()=>{
    if(!open)return;
    const close=(event:KeyboardEvent)=>{if(event.key==="Escape"&&!document.querySelector("dialog[open]"))setExpanded(null);};
    document.addEventListener("keydown",close);
    return()=>document.removeEventListener("keydown",close);
  },[open]);
  const count=questions.filter(q=>q.answered).length;
  function go(n:number){setExpanded(null);onGo(n);}
  return <footer className={`${s.footer} ${w.footer}`} onKeyDown={e=>{if(e.key==="Escape")setExpanded(null);}}>
    <div className={w.toolbar}>
      <button type="button" className={w.gridToggle} aria-expanded={open} aria-controls="listening-question-grid" onClick={()=>setExpanded(v=>v===navigation?null:navigation)}>Questions <span>{count}/{questions.length}</span> <span aria-hidden="true">{open?"⌄":"⌃"}</span></button>
      {leading}
      <div className={w.steps}><button type="button" aria-label="Previous question" disabled={current<=1} onClick={()=>go(current-1)}>←</button><span>{current} / {questions.length}</span><button type="button" aria-label="Next question" disabled={current>=questions.length} onClick={()=>go(current+1)}>→</button></div>
      {trailing}
    </div>
    <div id="listening-question-grid" className={w.gridPanel} hidden={!open}>
      <div className={w.gridHeading}><span>{description}</span><span>{legend}</span></div>
      <nav className={`${s.questionMap} ${w.questionMap}`} aria-label="Questions">{questions.map(q=><button type="button" key={q.number} aria-label={`Go to question ${q.number}`} aria-current={current===q.number?"true":undefined} title={q.title} data-answered={q.answered} data-marked={q.marked} data-review-status={q.status} onClick={()=>go(q.number)}>{q.number}</button>)}</nav>
    </div>
    {error&&<p role="alert">{error}</p>}
  </footer>;
}
