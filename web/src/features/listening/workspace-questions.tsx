"use client";

import {useEffect,useLayoutEffect,useMemo,useRef,useState,type CSSProperties,type ReactNode} from "react";
import type {Exam,Group,Question} from "./models";
import {ListeningAssetCache} from "./asset-cache";
import {AnswerBank,Asset,Input} from "./questions";
import {displayedPart,visibleSourceMaterial} from "./source-material";
import s from "./listening.module.css";
import w from "./workspace.module.css";

export function WorkspaceQuestions({exam,part,current,navigation,uid,id,answers,onAnswer,onFocus,disabled,renderAnswer,visibleQuestions,questionStatus,contentHash,toolbar,revealOnNavigate=false}: {
  revealOnNavigate?:boolean;toolbar?:ReactNode;contentHash?:string;exam:Exam;part:number;current:number;navigation:number;uid:string;id:string;answers:Record<string,string>;
  onAnswer:(id:string,value:string)=>void;onFocus:(number:number)=>void;disabled:boolean;
  questionStatus?:(question:Question)=>string;renderAnswer?:(question:Question,group:Group)=>ReactNode;visibleQuestions?:ReadonlySet<number>;
}) {
  const cache=useMemo(()=>new ListeningAssetCache(uid,id,contentHash||JSON.stringify(exam.assets)),[uid,id,contentHash,exam.assets]);
  useEffect(()=>{const release=cache.retain();cache.prefetch(exam.parts.flatMap(p=>visibleSourceMaterial(exam,p,p.groups).assets));return release;},[cache,exam]);
  const views=useRef(new Map<string,{source:number;questions:number;current:number;panel:"source"|"questions"}>());
  const selectedPart=displayedPart(exam,current,part);
  const groups=selectedPart.groups.filter(g=>!visibleQuestions||g.questions.some(q=>visibleQuestions.has(q.question_number)));
  const material=visibleSourceMaterial(exam,selectedPart,groups);
  const numbers=groups.flatMap(group=>group.questions.filter(q=>!visibleQuestions||visibleQuestions.has(q.question_number)).map(q=>q.question_number));
  const sourceRange=numbers.length?[numbers[0]!,numbers[numbers.length-1]!]:[];
  const split=material.hasMaterial;
  const scope=JSON.stringify([selectedPart.part_number,groups.map(g=>g.group_id)]);
  const [panelsByPart,setPanelsByPart]=useState<Record<number,{panel:"source"|"questions";navigation:number}>>({});
  const chosen=panelsByPart[selectedPart.part_number];
  const panel=chosen&&(!revealOnNavigate||chosen.navigation===navigation)?chosen.panel:"questions";
  function saveView(patch:Partial<{source:number;questions:number;current:number;panel:"source"|"questions"}>){views.current.set(scope,{source:0,questions:0,current,panel,...views.current.get(scope),...patch});}
  const [widths,setWidths]=useState<Record<number,number>>({});
  const width=widths[selectedPart.part_number]??55;
  const setWidth=(next:number|((value:number)=>number))=>setWidths(values=>({...values,[selectedPart.part_number]:typeof next==="number"?next:next(values[selectedPart.part_number]??55)}));
  const panels=useRef<HTMLDivElement>(null);
  const source=useRef<HTMLElement>(null);
  const pane=useRef<HTMLDivElement>(null);
  const lastNavigation=useRef<string>(null);
  const navigationInset=toolbar?52:24;
  const navigationKey=`${selectedPart.part_number}:${navigation}`;

  // Focus changes the answer context, not the visible source set. Keep manual
  // source scrolling while navigating the same Part/filter scope.
  const materialKey=JSON.stringify([selectedPart.part_number,material.segments.map(segment=>segment.id),groups.map(group=>group.group_id)]);
  useLayoutEffect(()=>{
    const view=views.current.get(scope);
    if(source.current)source.current.scrollTop=view?.source||0;
    if(pane.current)pane.current.scrollTop=view?.questions||0;
  },[materialKey,scope,panel]);

  useLayoutEffect(()=>{
    if(lastNavigation.current===navigationKey)return;
    lastNavigation.current=navigationKey;
    const el=pane.current,target=document.getElementById(`question-${current}`);
    const saved=views.current.get(scope);
    if(saved?.current===current)return;
    if(el&&target){el.scrollTop+=target.getBoundingClientRect().top-el.getBoundingClientRect().top-navigationInset;if(navigation>0)target.focus({preventScroll:true});}
  },[navigationKey,current,navigation,scope,navigationInset]);

  // Passive scrolling never changes current/group/source. Explicit navigation and
  // focusing an answer remain the only ways to select another question context.

  return <>
    {split&&<nav className={w.mobilePanels} aria-label="Listening panels">
      <button type="button" aria-pressed={panel==="source"} onClick={()=>{setPanelsByPart(v=>({...v,[selectedPart.part_number]:{panel:"source",navigation}}));saveView({panel:"source"});}}>Source material</button>
      <button type="button" aria-pressed={panel==="questions"} onClick={()=>{setPanelsByPart(v=>({...v,[selectedPart.part_number]:{panel:"questions",navigation}}));saveView({panel:"questions"});}}>Questions</button>
    </nav>}
    <div ref={panels} style={{"--source-width":`${width}%`} as CSSProperties} className={w.panels} data-layout={split?"split":"single"} data-mobile-panel={panel}>
      {split&&<section ref={source} className={w.sourcePane} onScroll={e=>saveView({source:e.currentTarget.scrollTop})} aria-label="Listening source material" tabIndex={0}>
        <header className={w.sourceHeading}><p>{material.assets.length?`${material.usingPartPages?`Original Part ${selectedPart.part_number} pages`:"Original source"} · select an image to enlarge`:"Source material · shared context and options"}</p></header>
        {(material.unavailable||material.missing.length>0)&&<p role="alert" className={s.instructions}>The original source image is missing from this exam’s data. Your answers are safe. Please report Cambridge {exam.book}, Test {exam.printed_test_number}, Part {selectedPart.part_number}, Questions {sourceRange.join("–")}{material.missing.length?` (${material.missing.join(", ")})`:""}.</p>}
        {material.segments.map(segment=><div key={segment.id} data-source-segment={segment.id} data-source-kind={segment.kind} data-source-range={segment.questionRange.join("-")}>
          {segment.kind==="image"&&segment.assetId?<Asset uid={uid} id={id} asset={segment.assetId} cache={cache} dimensions={exam.assets.find(a=>a.asset_id===segment.assetId)}/>:segment.kind==="text"?<section className={s.source} aria-label={`Original material Questions ${segment.questionRange.join("–")}`}>
            {segment.instructions&&<p>{segment.instructions}</p>}{segment.lines?.map((block,i)=><p key={`${block.source_line}:${i}`}>{block.text}</p>)}
          </section>:segment.kind==="options"?<AnswerBank group={groups.find(g=>g.group_id===segment.sourceGroupId)!}/>:null}
        </div>)}
      </section>}
      {split&&<div className={w.divider} role="separator" aria-label="Resize Listening panels" aria-orientation="vertical" aria-valuemin={30} aria-valuemax={70} aria-valuenow={Math.round(width)} tabIndex={0}
        onDoubleClick={()=>setWidth(55)}
        onKeyDown={e=>{if(["ArrowLeft","ArrowRight","Home","End"].includes(e.key)){e.preventDefault();setWidth(v=>e.key==="Home"?30:e.key==="End"?70:Math.max(30,Math.min(70,v+(e.key==="ArrowLeft"?-2:2))));}}}
        onPointerDown={e=>{e.preventDefault();e.currentTarget.setPointerCapture(e.pointerId);}}
        onPointerMove={e=>{if(!e.currentTarget.hasPointerCapture(e.pointerId))return;const rect=panels.current!.getBoundingClientRect();setWidth(Math.max(30,Math.min(70,(e.clientX-rect.left)/rect.width*100)));}}
        onPointerUp={e=>{if(e.currentTarget.hasPointerCapture(e.pointerId))e.currentTarget.releasePointerCapture(e.pointerId);}}><span/></div>}
      <div key={selectedPart.part_number} ref={pane} style={renderAnswer?{overflowAnchor:"none"}:undefined} className={w.questionsPane} onScroll={e=>saveView({questions:e.currentTarget.scrollTop})} role="region" aria-label="Listening questions" tabIndex={0}>
        {toolbar}
        <div className={w.questionContent}>{!groups.length&&<p className={s.instructions} role="status">No matching questions in this part. Choose another part or show all questions.</p>}{groups.map(group=><section className={w.questionGroup} key={group.group_id} data-question-group={group.group_id}>
          <header><span className={s.eyebrow}>Questions {group.question_range.join("–")}</span><p className={s.instructions}>{group.instructions}</p></header>
          <AnswerBank group={group}/>
          <div className={s.fields}>{group.questions.filter(q=>!visibleQuestions||visibleQuestions.has(q.question_number)).map(q=><div key={q.question_id} id={`question-${q.question_number}`} className={`${s.question} ${w.question}`} tabIndex={-1} data-current={current===q.question_number} data-review-status={questionStatus?.(q)} onFocus={()=>{saveView({current:q.question_number});onFocus(q.question_number);}}>
            <label className={s.questionTitle} htmlFor={q.question_id}><strong>{q.question_number}</strong>{q.prompt&&!/^\s*\d+\s*[_]/.test(q.prompt)&&<span>{q.prompt}</span>}</label>
            {renderAnswer?renderAnswer(q,group):<Input q={q} group={group} value={answers[q.question_id]||""} change={v=>onAnswer(q.question_id,v)} disabled={disabled} taken={group.selection?.distinct?group.questions.filter(other=>other.question_id!==q.question_id).map(other=>answers[other.question_id]||""):[]}/>}
          </div>)}</div>
        </section>)}</div>
      </div>
    </div>
  </>;
}
