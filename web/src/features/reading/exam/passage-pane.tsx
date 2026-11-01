"use client";
import { memo, useRef, useState } from "react";
import type { Passage } from "./models";
import type { Highlight } from "./draft-storage";
import { eventId } from "./api";
export const PassagePane = memo(function PassagePane({ passage, size, highlights=[], onHighlights }: { passage: Passage; size: number; highlights?:Highlight[]; onHighlights?:(value:Highlight[])=>void }) {
  const article=useRef<HTMLElement>(null);
  const [selection,setSelection]=useState<{block:number;start:number;end:number;quote:string}|null>(null);
  function select() {
    if(!onHighlights)return;
    const s=window.getSelection();if(!s||s.isCollapsed||s.rangeCount!==1){setSelection(null);return}
    const range=s.getRangeAt(0);const element=range.startContainer.parentElement?.closest<HTMLElement>("[data-highlight-block]");
    if(!element||!article.current?.contains(element)||!element.contains(range.endContainer)){setSelection(null);return}
    const before=range.cloneRange();before.selectNodeContents(element);before.setEnd(range.startContainer,range.startOffset);
    const block=Number(element.dataset.highlightBlock),start=before.toString().length,quote=range.toString(),end=start+quote.length;
    if(quote.length>10000||!quote.trim()||passage.content[block]?.text.slice(start,end)!==quote){setSelection(null);return}
    setSelection({block,start,end,quote});
  }
  function content(text:string,index:number) {
    const ranges=highlights.filter(h=>h.passageId===passage.id&&h.block===index&&text.slice(h.start,h.end)===h.quote).sort((a,b)=>a.start-b.start);
    let offset=0;const parts=[];
    for(const h of ranges){if(h.start<offset)continue;parts.push(text.slice(offset,h.start));parts.push(<mark key={h.id} title="Click to remove highlight" onClick={()=>onHighlights?.(highlights.filter(v=>v.id!==h.id))}>{text.slice(h.start,h.end)}</mark>);offset=h.end}
    parts.push(text.slice(offset));return parts;
  }
  return <article ref={article} className="passage-article" style={{fontSize:size}} onMouseUp={select} onKeyUp={select}>
    <p className="eyebrow">Reading passage {passage.number}</p><h1>{passage.title}</h1>{passage.subtitle&&<p className="passage-subtitle">{passage.subtitle}</p>}
    {onHighlights&&<div className="highlight-actions">{selection&&<button type="button" onMouseDown={e=>e.preventDefault()} onClick={()=>{
      const value={id:eventId(),passageId:passage.id,...selection};
      onHighlights([...highlights.filter(h=>h.passageId!==passage.id||h.block!==value.block||h.end<=value.start||h.start>=value.end),value].slice(-300));
      window.getSelection()?.removeAllRanges();setSelection(null);
    }}>Highlight</button>}{highlights.some(h=>h.passageId===passage.id)&&<button type="button" onClick={()=>onHighlights(highlights.filter(h=>h.passageId!==passage.id))}>Clear passage highlights</button>}</div>}
    {passage.content.map((b,i)=>b.type==="heading"?b.text.trim()===passage.title.trim()?null:<h2 key={i}>{b.text}</h2>:<p key={i}>{b.label&&<strong className="paragraph-label">{b.label} </strong>}<span data-highlight-block={i}>{content(b.text,i)}</span></p>)}
  </article>;
});
