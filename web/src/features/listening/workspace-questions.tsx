"use client";

import {useLayoutEffect,useRef,useState} from "react";
import type {Exam,Group} from "./models";
import {Asset,Input} from "./questions";
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
  const groups=exam.parts[part-1]!.groups;
  const active=groups.find(g=>g.questions.some(q=>q.question_number===current))||groups[0]!;
  const split=active.supporting_assets.length>0;
  const [mobile,setMobile]=useState<{panel:"source"|"questions";navigation:number}>({panel:"questions",navigation});
  const panel=mobile.navigation===navigation?mobile.panel:"questions";
  const pane=useRef<HTMLDivElement>(null);
  const lastNavigation=useRef<string>(null);
  const following=useRef(false);
  const navigationKey=`${part}:${navigation}`;

  useLayoutEffect(()=>{
    if(lastNavigation.current===navigationKey)return;
    lastNavigation.current=navigationKey;
    following.current=false;
    const el=pane.current,target=document.getElementById(`question-${current}`);
    if(el&&target)el.scrollTop+=target.getBoundingClientRect().top-el.getBoundingClientRect().top-24;
  },[navigationKey,current]);

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
    <div className={w.panels} data-layout={split?"split":"single"} data-mobile-panel={panel}>
      {split&&<section key={active.group_id} className={w.sourcePane} aria-label="Listening source material" tabIndex={0}>
        <header className={w.sourceHeading}><span className={s.eyebrow}>Questions {active.question_range.join("–")}</span><p>Original source · select an image to enlarge</p></header>
        <Bank group={active}/>
        {active.supporting_assets.map(asset=><Asset key={asset} uid={uid} id={id} asset={asset}/>)}
      </section>}
      <div key={part} ref={pane} className={w.questionsPane} role="region" aria-label="Listening questions" tabIndex={0} onScroll={followScroll}
        onWheel={()=>{following.current=true;}} onTouchStart={()=>{following.current=true;}}
        onPointerDown={()=>{following.current=true;}} onKeyDown={event=>{if(["ArrowUp","ArrowDown","PageUp","PageDown","Home","End"].includes(event.key))following.current=true;}}>
        <div className={w.questionContent}>{groups.map(group=><section className={w.questionGroup} key={group.group_id} data-question-group={group.group_id}>
          <header><span className={s.eyebrow}>Questions {group.question_range.join("–")}</span><p className={s.instructions}>{group.instructions}</p></header>
          {!group.supporting_assets.length&&<>
            {group.content_blocks.some(b=>b.kind==="source_line"&&b.text.trim())&&<div className={s.source}>
              {group.content_blocks.map((block,i)=>block.kind==="source_line"&&<p key={i}>{block.text}</p>)}
            </div>}
            <Bank group={group}/>
          </>}
          <div className={s.fields}>{group.questions.map(q=><div key={q.question_id} id={`question-${q.question_number}`} className={`${s.question} ${w.question}`} onFocus={()=>{following.current=false;onFocus(q.question_number);}}>
            <label className={s.questionTitle} htmlFor={q.question_id}><strong>{q.question_number}</strong>{q.prompt&&!/^\s*\d+\s*[_]/.test(q.prompt)&&<span>{q.prompt}</span>}</label>
            <Input q={q} group={group} value={answers[q.question_id]||""} change={v=>onAnswer(q.question_id,v)} disabled={disabled} taken={group.selection?.distinct?group.questions.filter(other=>other.question_id!==q.question_id).map(other=>answers[other.question_id]||""):[]}/>
          </div>)}</div>
        </section>)}</div>
      </div>
    </div>
  </>;
}
