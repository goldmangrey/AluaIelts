"use client";

import {useLayoutEffect,useRef,useState,type CSSProperties} from "react";
import type {Exam,Group} from "./models";
import {Asset,Input} from "./questions";
import {displayedPart,sourceMaterial} from "./source-material";
import s from "./listening.module.css";
import w from "./workspace.module.css";

function Bank({group}:{group:Group}) {
  if (!group.answer_bank) return null;
  return <details className={s.bank} open><summary>Answer bank</summary><div>
    {group.answer_bank.options.map(op=><p key={op.label}><b>{op.label}</b>
      {op.text&&op.text!==op.label?` · ${op.text}`:op.visual_reference?" · position in the original image":""}
    </p>)}
  </div></details>;
}

export function WorkspaceQuestions({exam,part,current,navigation,uid,id,answers,onAnswer,onFocus,disabled}: {
  exam:Exam;part:number;current:number;navigation:number;uid:string;id:string;answers:Record<string,string>;
  onAnswer:(id:string,value:string)=>void;onFocus:(number:number)=>void;disabled:boolean;
}) {
  const selectedPart=displayedPart(exam,current,part);
  const groups=selectedPart.groups;
  const active=groups.find(g=>g.questions.some(q=>q.question_number===current))||groups[0]!;
  const material=sourceMaterial(exam,selectedPart,active);
  const split=material.hasMaterial;
  const [mobile,setMobile]=useState<{panel:"source"|"questions";navigation:number}>({panel:"questions",navigation});
  const panel=mobile.navigation===navigation?mobile.panel:"questions";
  const [width,setWidth]=useState(55);
  const panels=useRef<HTMLDivElement>(null);
  const source=useRef<HTMLElement>(null);
  const pane=useRef<HTMLDivElement>(null);
  const lastNavigation=useRef<string>(null);
  const following=useRef(false);
  const navigationKey=`${selectedPart.part_number}:${navigation}`;

  useLayoutEffect(()=>{if(source.current)source.current.scrollTop=0;},[active.group_id]);

  useLayoutEffect(()=>{
    if(lastNavigation.current===navigationKey)return;
    lastNavigation.current=navigationKey;
    following.current=false;
    const el=pane.current,target=document.getElementById(`question-${current}`);
    if(el&&target){el.scrollTop+=target.getBoundingClientRect().top-el.getBoundingClientRect().top-24;if(navigation>0)target.focus({preventScroll:true});}
  },[navigationKey,current,navigation]);

  // Match Reading's independent panes: scrolling questions selects the corresponding source.
  function followScroll() {
    const el=pane.current;
    if (!el?.clientHeight||!following.current) return;
    const top=el.getBoundingClientRect().top+48;
    const sections=Array.from(el.querySelectorAll<HTMLElement>("[data-question-group]"));
    const visible=sections.find(section=>section.getBoundingClientRect().bottom>top);
    const group=groups.find(g=>g.group_id===visible?.dataset.questionGroup);
    if (group&&group.group_id!==active.group_id) {
      onFocus(group.questions[0]!.question_number);
    }
  }

  return <>
    {split&&<nav className={w.mobilePanels} aria-label="Listening panels">
      <button type="button" aria-pressed={panel==="source"} onClick={()=>setMobile({panel:"source",navigation})}>Source material</button>
      <button type="button" aria-pressed={panel==="questions"} onClick={()=>setMobile({panel:"questions",navigation})}>Questions</button>
    </nav>}
    <div ref={panels} style={{"--source-width":`${width}%`} as CSSProperties} className={w.panels} data-layout={split?"split":"single"} data-mobile-panel={panel}>
      {split&&<section ref={source} className={w.sourcePane} aria-label="Listening source material" tabIndex={0}>
        <header className={w.sourceHeading}><span className={s.eyebrow}>Questions {active.question_range.join("–")}</span><p>{material.assets.length?`${material.usingPartPages?`Original Part ${selectedPart.part_number} pages`:"Original source"} · select an image to enlarge`:"Source material · shared context and options"}</p></header>
        {(material.unavailable||material.missing.length>0)&&<p role="alert" className={s.instructions}>The original source image is missing from this exam’s data. Your answers are safe. Please report Cambridge {exam.book}, Test {exam.printed_test_number}, Part {selectedPart.part_number}, Questions {active.question_range.join("–")}{material.missing.length?` (${material.missing.join(", ")})`:""}.</p>}
        <Bank group={active}/>
        {material.assets.map(asset=><Asset key={asset} uid={uid} id={id} asset={asset}/>)}
        {material.lines.length>0&&<div className={s.source}>{material.lines.map((block,i)=><p key={i}>{block.text}</p>)}</div>}
      </section>}
      {split&&<div className={w.divider} role="separator" aria-label="Resize Listening panels" aria-orientation="vertical" aria-valuemin={30} aria-valuemax={70} aria-valuenow={Math.round(width)} tabIndex={0}
        onDoubleClick={()=>setWidth(55)}
        onKeyDown={e=>{if(["ArrowLeft","ArrowRight","Home","End"].includes(e.key)){e.preventDefault();setWidth(v=>e.key==="Home"?30:e.key==="End"?70:Math.max(30,Math.min(70,v+(e.key==="ArrowLeft"?-2:2))));}}}
        onPointerDown={e=>{e.preventDefault();e.currentTarget.setPointerCapture(e.pointerId);}}
        onPointerMove={e=>{if(!e.currentTarget.hasPointerCapture(e.pointerId))return;const rect=panels.current!.getBoundingClientRect();setWidth(Math.max(30,Math.min(70,(e.clientX-rect.left)/rect.width*100)));}}
        onPointerUp={e=>{if(e.currentTarget.hasPointerCapture(e.pointerId))e.currentTarget.releasePointerCapture(e.pointerId);}}><span/></div>}
      <div key={selectedPart.part_number} ref={pane} className={w.questionsPane} role="region" aria-label="Listening questions" tabIndex={0} onScroll={followScroll}
        onWheel={()=>{following.current=true;}} onTouchStart={()=>{following.current=true;}}
        onPointerDown={()=>{following.current=true;}} onKeyDown={event=>{if(["ArrowUp","ArrowDown","PageUp","PageDown","Home","End"].includes(event.key))following.current=true;}}>
        <div className={w.questionContent}>{groups.map(group=><section className={w.questionGroup} key={group.group_id} data-question-group={group.group_id}>
          <header><span className={s.eyebrow}>Questions {group.question_range.join("–")}</span><p className={s.instructions}>{group.instructions}</p></header>
          <div className={s.fields}>{group.questions.map(q=><div key={q.question_id} id={`question-${q.question_number}`} className={`${s.question} ${w.question}`} tabIndex={-1} data-current={current===q.question_number} onFocus={()=>{following.current=false;onFocus(q.question_number);}}>
            <label className={s.questionTitle} htmlFor={q.question_id}><strong>{q.question_number}</strong>{q.prompt&&!/^\s*\d+\s*[_]/.test(q.prompt)&&<span>{q.prompt}</span>}</label>
            <Input q={q} group={group} value={answers[q.question_id]||""} change={v=>onAnswer(q.question_id,v)} disabled={disabled} taken={group.selection?.distinct?group.questions.filter(other=>other.question_id!==q.question_id).map(other=>answers[other.question_id]||""):[]}/>
          </div>)}</div>
        </section>)}</div>
      </div>
    </div>
  </>;
}
