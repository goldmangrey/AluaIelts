"use client";
import {useCallback,useEffect,useId,useRef,useState,type CSSProperties} from "react";
import {authorize} from "./api";
import s from "./listening.module.css";
import v from "./player.module.css";

// Decorative rhythm only; playback progress always comes from the native audio element.
const capsules=Array.from({length:48},(_,i)=>Math.round(8+10*(.5+.5*Math.sin(i*.58))* (.55+.45*Math.sin(i*.23+1)**2)));
function Waveform({current,duration,playing,onSeek}:{current:number;duration:number;playing:boolean;onSeek:(seconds:number)=>void}){
  const clip=useId();
  const progress=duration>0?Math.max(0,Math.min(1,current/duration)):0;
  const bars=capsules.map((height,i)=><line key={i} x1={5+i*10} x2={5+i*10} y1={16-height/2} y2={16+height/2} style={{"--capsule-delay":`${-(i%7)*.31}s`} as CSSProperties} vectorEffect="non-scaling-stroke"/>);
  return <div className={v.waveSeek} data-waveform="soft-capsules" data-playing={playing}>
    <svg className={v.capsules} viewBox="0 0 480 32" preserveAspectRatio="none" aria-hidden="true">
      <defs><clipPath id={clip}><rect data-waveform-progress width={progress*480} height="32"/></clipPath></defs>
      <g className={v.remaining}>{bars}</g><g className={v.played} clipPath={`url(#${clip})`}>{bars}</g>
    </svg>
    <input aria-label="Audio progress" aria-valuetext={`${time(current)} of ${time(duration)}`} type="range" min="0" max={duration||1} step="0.1" value={Math.min(current,duration||1)} onChange={e=>onSeek(Number(e.target.value))}/>
  </div>;
}
const time=(n:number)=>`${Math.floor((Number.isFinite(n)?n:0)/60).toString().padStart(2,"0")}:${Math.floor((Number.isFinite(n)?n:0)%60).toString().padStart(2,"0")}`;
function Skip({forward=false}:{forward?:boolean}){return <svg width="30" height="30" viewBox="0 0 32 32" aria-hidden="true"><g transform={forward?"translate(32 0) scale(-1 1)":undefined}><path d="M8 9H3V4M3.5 9a12 12 0 1 1-.4 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></g><text x="16" y="21" textAnchor="middle" fontSize="12" fontWeight="600" fill="currentColor">5</text></svg>}
function PlayIcon({playing}:{playing:boolean}){return <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true" fill="currentColor">{playing?<><rect x="5" y="4" width="5" height="16" rx="1"/><rect x="14" y="4" width="5" height="16" rx="1"/></>:<path d="M7 4.8a1 1 0 0 1 1.5-.86l12 7.2a1 1 0 0 1 0 1.72l-12 7.2A1 1 0 0 1 7 19.2Z"/>}</svg>}
export interface Moment {request:number;part:number;start:number;end:number;loop:boolean}
export function Player({uid,attemptId,book,part,position,onCheckpoint,onPart,moment,onMomentStop}:{uid:string;attemptId:string;book:number;part:number;position:number;onCheckpoint:(part:number,seconds:number)=>void;onPart:(part:number)=>void;moment?:Moment;onMomentStop?:()=>void}){
  const audio=useRef<HTMLAudioElement>(null);const preload=useRef<HTMLAudioElement>(null);const callbacks=useRef({onCheckpoint,onPart});const resume=useRef(position);const lastSave=useRef(0);const continuePlay=useRef<number|null>(null);
  const [current,setCurrent]=useState(0),[duration,setDuration]=useState(0),[playing,setPlaying]=useState(false),[status,setStatus]=useState("Preparing audio…"),[authorized,setAuthorized]=useState(false);
  const momentRef=useRef<Moment|undefined>(undefined),momentStop=useRef(onMomentStop),startedMoment=useRef<number|undefined>(undefined),momentOnly=useRef(false);
  useEffect(()=>{momentStop.current=onMomentStop;},[onMomentStop]);
  const cancelMoment=useCallback(()=>{if(momentRef.current){momentRef.current=undefined;startedMoment.current=undefined;momentStop.current?.();}},[]);
  const momentEnd=useCallback(()=>{const el=audio.current,m=momentRef.current;if(!el||!m||m.part!==part)return false;
    if(el.currentTime>=m.end-.025||el.ended){
      if(m.loop){el.currentTime=m.start;void el.play().catch(()=>{cancelMoment();setStatus("Press Play to listen again.");});}
      else{el.pause();el.currentTime=m.end;setCurrent(m.end);cancelMoment();}
      return true;
    }return false;
  },[part,cancelMoment]);
  useEffect(()=>{callbacks.current={onCheckpoint,onPart};},[onCheckpoint,onPart]);
  useEffect(()=>{let live=true;const refresh=()=>authorize(uid,attemptId).then(()=>{if(live){setAuthorized(true);setStatus("");}}).catch(()=>{if(live)setStatus("Audio access interrupted. Press Play to reconnect.");});void refresh();const timer=setInterval(()=>{void refresh()},600000);const visible=()=>{if(document.visibilityState==="visible")void refresh();};document.addEventListener("visibilitychange",visible);return()=>{live=false;clearInterval(timer);document.removeEventListener("visibilitychange",visible);};},[uid,attemptId]);
  useEffect(()=>{if(!authorized||!audio.current)return;const el=audio.current;setPlaying(false);setCurrent(0);setDuration(0);setStatus("Loading audio…");lastSave.current=0;el.src=`/api/listening/audio/${attemptId}/${part}`;el.load();const save=()=>{callbacks.current.onCheckpoint(part,el.currentTime||0);};const metadata=()=>{setDuration(el.duration||0);el.currentTime=Math.min(resume.current,Number.isFinite(el.duration)?el.duration:resume.current);resume.current=0;setCurrent(el.currentTime);setStatus("");const autoplay=continuePlay.current===part;continuePlay.current=null;if(autoplay){void el.play().catch(()=>setStatus("Part ready. Press Play to continue."));}};
    const update=()=>{momentEnd();setCurrent(el.currentTime);if(Math.abs(el.currentTime-lastSave.current)>=5){lastSave.current=el.currentTime;save();}};
    const ended=()=>{if(momentOnly.current){if(momentRef.current)momentEnd();return;}save();if(part<4){continuePlay.current=part+1;resume.current=0;callbacks.current.onPart(part+1);}else setStatus("All four parts complete.");};
    const wait=()=>setStatus("Buffering…"),can=()=>setStatus(""),error=()=>setStatus("Audio couldn’t load. Press Play to retry."),play=()=>{setPlaying(true);setStatus("");},pause=()=>{setPlaying(false);setCurrent(el.currentTime);save();};
    const events:{[name:string]:EventListener}={loadedmetadata:metadata,timeupdate:update,seeked:save,ended,waiting:wait,canplay:can,error,playing:play,pause};for(const [key,fn]of Object.entries(events))el.addEventListener(key,fn);
    const visibility=()=>{if(document.visibilityState==="hidden")save();};document.addEventListener("visibilitychange",visibility);
    return()=>{save();for(const [key,fn]of Object.entries(events))el.removeEventListener(key,fn);document.removeEventListener("visibilitychange",visibility);el.pause();};
  },[authorized,attemptId,part,momentEnd]);
  useEffect(()=>{if(authorized&&part<4&&preload.current){preload.current.src=`/api/listening/audio/${attemptId}/${part+1}`;preload.current.load();}},[authorized,attemptId,part]);
  useEffect(()=>{
    const el=audio.current;
    if(!moment){if(momentRef.current){el?.pause();momentRef.current=undefined;}startedMoment.current=undefined;return;}
    momentRef.current=moment;
    if(!el||!authorized||moment.part!==part||!duration||el.readyState<1||!Number.isFinite(el.duration))return;
    if(!Number.isFinite(moment.start)||!Number.isFinite(moment.end)||moment.start<0||moment.start>=moment.end||moment.start>=el.duration||moment.end>el.duration+.05){void Promise.resolve().then(()=>{if(momentRef.current===moment){cancelMoment();setStatus("This audio moment is unavailable.");}});return;}
    momentRef.current={...moment,end:Math.min(moment.end,el.duration)};
    if(startedMoment.current!==moment.request){startedMoment.current=moment.request;momentOnly.current=true;el.currentTime=moment.start;void el.play().catch(()=>{cancelMoment();setStatus("Press Play to listen again.");});}
    const timer=setInterval(()=>{if(!el.paused)momentEnd();},40);
    const hidden=()=>{if(document.visibilityState==='hidden'){el.pause();cancelMoment();}};
    document.addEventListener('visibilitychange',hidden);
    return()=>{clearInterval(timer);document.removeEventListener('visibilitychange',hidden);};
    // Native media events plus this bounded timer protect the end boundary, including seek/end.
  },[moment,part,authorized,duration,momentEnd,cancelMoment]);
  async function toggle(){momentOnly.current=false;const el=audio.current;if(!el)return;if(!el.paused){cancelMoment();el.pause();return;}try{if(!authorized||el.error){await authorize(uid,attemptId);continuePlay.current=part;if(!authorized)setAuthorized(true);else{resume.current=el.currentTime;el.load();}return;}await el.play();}catch{setStatus("Press Play again when your connection is restored.");}}
  function seek(value:number){momentOnly.current=false;cancelMoment();const el=audio.current;if(!el||!Number.isFinite(el.duration))return;el.currentTime=Math.min(el.duration,Math.max(0,value));setCurrent(el.currentTime);callbacks.current.onCheckpoint(part,el.currentTime);}
  useEffect(()=>{const key=(e:KeyboardEvent)=>{const target=e.target as HTMLElement;if(target.closest("input,textarea,select,button,a,[contenteditable=true],[role=slider]"))return;if(e.code==="Space"){e.preventDefault();void toggle();}else if(e.key==="ArrowLeft"||e.key==="ArrowRight"){e.preventDefault();const el=audio.current;if(el&&Number.isFinite(el.duration)){momentOnly.current=false;cancelMoment();el.currentTime=Math.min(el.duration,Math.max(0,el.currentTime+(e.key==="ArrowLeft"?-5:5)));}}};window.addEventListener("keydown",key);return()=>window.removeEventListener("keydown",key);});
  return <section className={s.player} aria-label="Listening audio player"><div className={s.playerTitle} data-player="title">Cambridge {book} · Listening · Part {part} of 4</div><audio ref={audio} preload="metadata"/><audio ref={preload} preload="metadata" aria-hidden="true"/><div className={s.seek} data-player="seek"><time>{time(current)}</time><Waveform current={current} duration={duration} playing={playing} onSeek={seek}/><time>{time(duration)}</time></div><div className={s.controls} data-player="controls"><button type="button" aria-label="Back 5 seconds" onClick={()=>seek((audio.current?.currentTime||0)-5)}><Skip/></button><button type="button" className={s.play} aria-label={playing?"Pause":"Play"} onClick={()=>void toggle()}><PlayIcon playing={playing}/></button><button type="button" aria-label="Forward 5 seconds" onClick={()=>seek((audio.current?.currentTime||0)+5)}><Skip forward/></button></div><div className={s.audioStatus} data-player="status" data-issue={/interrupted|couldn’t|retry|reconnect|restored|Press Play again/.test(status)} role="status">{status||(!playing&&position>0?`Saved position ${time(position)} · press Play to continue`:" ")}</div></section>;
}
