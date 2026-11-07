"use client";
/* Native images deliberately preserve original Cambridge diagrams and page geometry. */
/* eslint-disable @next/next/no-img-element */
import {useEffect,useRef,useState} from "react";
import {ListeningAssetCache} from "./asset-cache";
import type {Exam,Group,Question} from "./models";
import s from "./listening.module.css";
export function Asset({uid,id,asset,cache,dimensions}:{uid:string;id:string;asset:string;cache?:ListeningAssetCache;dimensions?:{width:number;height:number}}){
 const [own]=useState(()=>cache||new ListeningAssetCache(uid,id,"legacy"));const images=cache||own;
 const [loaded,setLoaded]=useState<{asset:string;src:string;cache:ListeningAssetCache}>(),[error,setError]=useState(false),[retry,setRetry]=useState(0);
 const src=images.peek(asset)||(loaded?.asset===asset&&loaded.cache===images?loaded.src:undefined),dialog=useRef<HTMLDialogElement>(null);
 useEffect(()=>images.retain(),[images]);
 useEffect(()=>{let live=true;const release=images.acquire(asset);images.load(asset).then(url=>{if(live)setLoaded({asset,src:url,cache:images});}).catch(()=>{if(live)setError(true);});return()=>{live=false;release();};},[images,asset,retry]);
 return <div className={s.asset} data-source-asset={asset}>{src?<><button type="button" className={s.imageButton} onClick={()=>dialog.current?.showModal()} aria-label="Enlarge source image"><img src={src} width={dimensions?.width} height={dimensions?.height} alt="Original Cambridge question page or diagram"/></button><dialog className={s.imageDialog} ref={dialog}><button type="button" onClick={()=>dialog.current?.close()}>Close image</button><img src={src} alt="Enlarged original Cambridge source"/></dialog></>:error?<div role="alert"><p>Original Cambridge source image could not load. Your answers are safe.</p><button onClick={()=>{setError(false);setRetry(n=>n+1);}}>Retry image</button></div>:<p role="status">Loading original image…</p>}</div>;
}
/** The bank stays open beside every group's answers, including on mobile. */
export function AnswerBank({group}:{group:Group}) {
 const bank=group.answer_bank;
 if(!bank)return null;
 return <section className={s.bank} aria-label="Answer bank"><h3>Answer bank</h3><div>{bank.options.map(op=><p key={op.label}><b>{op.label}</b>{op.text&&op.text!==op.label?` · ${op.text}`:op.visual_reference?" · position in the original image":""}</p>)}</div></section>;
}

export function Input({q,group,value,change,disabled,taken=[]}:{q:Question;group:Group;value:string;change:(v:string)=>void;disabled:boolean;taken?:string[]}) {
 const options=q.options.length?q.options:group.answer_bank?.options||[];
 if(q.input_type==="text")return <input aria-label={`Question ${q.question_number}`} id={q.question_id} value={value} onChange={e=>change(e.target.value)} maxLength={500} autoComplete="off" autoCorrect="off" autoCapitalize="off" spellCheck={false} disabled={disabled} placeholder="Your answer"/>;
 const multiple=q.input_type==="multi_select";
 const selected=multiple?value.split(/\s+/).filter(Boolean):[value];
 const compact=!group.question_type.startsWith("multiple_choice");
 return <div id={q.question_id} role={multiple?"group":"radiogroup"} aria-label={`Question ${q.question_number}`} className={s.answerControl}>
   <div className={`${s.options} ${compact?s.choiceChips:""}`}>
     {options.map(op=>{
       const checked=selected.includes(op.label);
       const inBank=group.answer_bank?.options.some(item=>item.label===op.label&&item.text===op.text);
       const text=op.text&&op.text!==op.label?op.text:op.visual_reference?"Position shown in the original image":"";
       return <label key={op.label}>
         <input type={multiple?"checkbox":"radio"} name={q.question_id} value={op.label} checked={checked}
           aria-label={compact&&inBank&&text?`${op.label} · ${text}`:undefined}
           disabled={disabled||(multiple?!checked&&selected.length>=(q.constraints.required_choices||2):taken.includes(op.label))}
           onChange={()=>change(multiple?(checked?selected.filter(v=>v!==op.label):[...selected,op.label]).join(" "):op.label)}/>
         <b>{op.label}</b>{(!compact||!inBank)&&text&&<span>{text}</span>}
       </label>;
     })}
   </div>
   {value&&<button className={s.clearAnswer} type="button" disabled={disabled} onClick={()=>change("")}>Clear selection</button>}
 </div>;
}
export function QuestionGroups({exam,part,uid,id,answers,onAnswer,disabled=false,onFocus}:{exam:Exam;part:number;uid:string;id:string;answers:Record<string,string>;onAnswer:(id:string,value:string)=>void;disabled?:boolean;onFocus?:(n:number)=>void}){
 const data=exam.parts[part-1]!;return <div className={s.groups}>{data.groups.map(group=><section className={s.group} key={group.group_id}><header><span className={s.eyebrow}>Questions {group.question_range[0]}{group.question_range[1]!==group.question_range[0]?`–${group.question_range[1]}`:""}</span><p className={s.instructions}>{group.instructions}</p></header>
 {group.presentation_mode==="image_backed"?<div className={s.images}>{group.supporting_assets.map(asset=><Asset key={asset} uid={uid} id={id} asset={asset}/>)}</div>:<div className={s.source}>{group.content_blocks.filter(b=>b.kind==="source_line").map((block,i)=>block.kind==="source_line"&&<p key={i}>{block.text}</p>)}</div>}
 <AnswerBank group={group}/>
 <div className={s.fields}>{group.questions.map(q=><div key={q.question_id} id={`question-${q.question_number}`} className={s.question} onFocus={()=>onFocus?.(q.question_number)}><label className={s.questionTitle} htmlFor={q.question_id}><strong>{q.question_number}</strong>{q.prompt&&!/^\s*\d+\s*[_]/.test(q.prompt)&&<span>{q.prompt}</span>}</label><Input q={q} group={group} value={answers[q.question_id]||""} change={v=>onAnswer(q.question_id,v)} disabled={disabled} taken={group.selection?.distinct?group.questions.filter(other=>other.question_id!==q.question_id).map(other=>answers[other.question_id]||""):[]}/></div>)}</div></section>)}</div>;
}
