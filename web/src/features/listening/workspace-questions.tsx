"use client";

import {useLayoutEffect,useRef,useState,type CSSProperties,type ReactNode} from "react";
import type {Exam,Group,Question} from "./models";
import {Asset,Input} from "./questions";
import {displayedPart,sourceMaterial,visibleSourceMaterial} from "./source-material";
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

export function WorkspaceQuestions({exam,part,current,navigation,uid,id,answers,onAnswer,onFocus,disabled,renderAnswer,visibleQuestions,questionStatus}: {
  exam:Exam;part:number;current:number;navigation:number;uid:string;id:string;answers:Record<string,string>;
  onAnswer:(id:string,value:string)=>void;onFocus:(number:number)=>void;disabled:boolean;
  questionStatus?:(question:Question)=>string;renderAnswer?:(question:Question,group:Group)=>ReactNode;visibleQuestions?:ReadonlySet<number>;
}) {
  const selectedPart=displayedPart(exam,current,part);
  const groups=selectedPart.groups.filter(g=>!visibleQuestions||g.questions.some(q=>visibleQuestions.has(q.question_number)));
  const active=groups.find(g=>g.questions.some(q=>q.question_number===current))||groups[0]||selectedPart.groups[0]!;
  const context=sourceMaterial(exam,selectedPart,active);
  const material=visibleSourceMaterial(exam,selectedPart,groups);
  const numbers=groups.flatMap(group=>group.questions.filter(q=>!visibleQuestions||visibleQuestions.has(q.question_number)).map(q=>q.question_number));
  const sourceRange=numbers.length?[numbers[0]!,numbers[numbers.length-1]!]:[];
  const split=material.hasMaterial;
  const [mobile,setMobile]=useState<{panel:"source"|"questions";navigation:number}>({panel:"questions",navigation});
  const panel=mobile.navigation===navigation?mobile.panel:"questions";
  const [width,setWidth]=useState(55);
  const panels=useRef<HTMLDivElement>(null);
  const source=useRef<HTMLElement>(null);
  const pane=useRef<HTMLDivElement>(null);
  const lastNavigation=useRef<string>(null);
  const navigationKey=`${selectedPart.part_number}:${navigation}`;

  // Focus changes the answer context, not the visible source set. Keep manual
  // source scrolling while navigating the same Part/filter scope.
  const materialKey=JSON.stringify([selectedPart.part_number,material.assets,groups.map(group=>group.group_id)]);
  useLayoutEffect(()=>{if(source.current)source.current.scrollTop=0;},[materialKey]);

  useLayoutEffect(()=>{
    if(lastNavigation.current===navigationKey)return;
    lastNavigation.current=navigationKey;
    const el=pane.current,target=document.getElementById(`question-${current}`);
    if(el&&target){el.scrollTop+=target.getBoundingClientRect().top-el.getBoundingClientRect().top-24;if(navigation>0)target.focus({preventScroll:true});}
  },[navigationKey,current,navigation]);

  // Passive scrolling never changes current/group/source. Explicit navigation and
  // focusing an answer remain the only ways to select another question context.

  return <>
    {split&&<nav className={w.mobilePanels} aria-label="Listening panels">
      <button type="button" aria-pressed={panel==="source"} onClick={()=>setMobile({panel:"source",navigation})}>Source material</button>
      <button type="button" aria-pressed={panel==="questions"} onClick={()=>setMobile({panel:"questions",navigation})}>Questions</button>
    </nav>}
    <div ref={panels} style={{"--source-width":`${width}%`} as CSSProperties} className={w.panels} data-layout={split?"split":"single"} data-mobile-panel={panel}>
      {split&&<section ref={source} className={w.sourcePane} aria-label="Listening source material" tabIndex={0}>
        <header className={w.sourceHeading}><span className={s.eyebrow}>Questions {sourceRange.join("–")}</span><p>{material.assets.length?`${material.usingPartPages?`Original Part ${selectedPart.part_number} pages`:"Original source"} · select an image to enlarge`:"Source material · shared context and options"}</p></header>
        {(material.unavailable||material.missing.length>0)&&<p role="alert" className={s.instructions}>The original source image is missing from this exam’s data. Your answers are safe. Please report Cambridge {exam.book}, Test {exam.printed_test_number}, Part {selectedPart.part_number}, Questions {sourceRange.join("–")}{material.missing.length?` (${material.missing.join(", ")})`:""}.</p>}
        <Bank group={active}/>
        {material.assets.map(asset=><Asset key={asset} uid={uid} id={id} asset={asset}/>)}
        {context.lines.length>0&&<div className={s.source}>{context.lines.map((block,i)=><p key={i}>{block.text}</p>)}</div>}
      </section>}
      {split&&<div className={w.divider} role="separator" aria-label="Resize Listening panels" aria-orientation="vertical" aria-valuemin={30} aria-valuemax={70} aria-valuenow={Math.round(width)} tabIndex={0}
        onDoubleClick={()=>setWidth(55)}
        onKeyDown={e=>{if(["ArrowLeft","ArrowRight","Home","End"].includes(e.key)){e.preventDefault();setWidth(v=>e.key==="Home"?30:e.key==="End"?70:Math.max(30,Math.min(70,v+(e.key==="ArrowLeft"?-2:2))));}}}
        onPointerDown={e=>{e.preventDefault();e.currentTarget.setPointerCapture(e.pointerId);}}
        onPointerMove={e=>{if(!e.currentTarget.hasPointerCapture(e.pointerId))return;const rect=panels.current!.getBoundingClientRect();setWidth(Math.max(30,Math.min(70,(e.clientX-rect.left)/rect.width*100)));}}
        onPointerUp={e=>{if(e.currentTarget.hasPointerCapture(e.pointerId))e.currentTarget.releasePointerCapture(e.pointerId);}}><span/></div>}
      <div key={selectedPart.part_number} ref={pane} className={w.questionsPane} role="region" aria-label="Listening questions" tabIndex={0}>
        <div className={w.questionContent}>{!groups.length&&<p className={s.instructions} role="status">No matching questions in this part. Choose another part or show all questions.</p>}{groups.map(group=><section className={w.questionGroup} key={group.group_id} data-question-group={group.group_id}>
          <header><span className={s.eyebrow}>Questions {group.question_range.join("–")}</span><p className={s.instructions}>{group.instructions}</p></header>
          <div className={s.fields}>{group.questions.filter(q=>!visibleQuestions||visibleQuestions.has(q.question_number)).map(q=><div key={q.question_id} id={`question-${q.question_number}`} className={`${s.question} ${w.question}`} tabIndex={-1} data-current={current===q.question_number} data-review-status={questionStatus?.(q)} onFocus={()=>onFocus(q.question_number)}>
            <label className={s.questionTitle} htmlFor={q.question_id}><strong>{q.question_number}</strong>{q.prompt&&!/^\s*\d+\s*[_]/.test(q.prompt)&&<span>{q.prompt}</span>}</label>
            {renderAnswer?renderAnswer(q,group):<Input q={q} group={group} value={answers[q.question_id]||""} change={v=>onAnswer(q.question_id,v)} disabled={disabled} taken={group.selection?.distinct?group.questions.filter(other=>other.question_id!==q.question_id).map(other=>answers[other.question_id]||""):[]}/>}
          </div>)}</div>
        </section>)}</div>
      </div>
    </div>
  </>;
}
