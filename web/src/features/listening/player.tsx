"use client";
import {useCallback,useEffect,useId,useMemo,useRef,useState} from "react";
import {authorize} from "./api";
import {AudioProgress} from "./audio-progress";
import {loadWaveform,type WaveformTrack} from "./waveform";
import v from "./player.module.css";

function Waveform({examId,part,current,duration,onSeek}:{examId:string;part:number;current:number;duration:number;onSeek:(seconds:number)=>void}){
  const clip=useId(),container=useRef<HTMLDivElement>(null);
  const [count,setCount]=useState(160),[data,setData]=useState<{part:number;track:WaveformTrack}|null>(null);
  const peaks=data?.part===part?data.track.peaks:undefined;
  useEffect(()=>{
    const el=container.current;if(!el)return;
    const resize=new ResizeObserver(([entry])=>setCount(Math.max(24,Math.min(480,Math.floor((entry?.contentRect.width||480)/3)))));
    resize.observe(el);return()=>resize.disconnect();
  },[]);
  useEffect(()=>{let live=true;void loadWaveform(examId,part).then(track=>{if(live)setData({part,track});}).catch(()=>{/* Keep a usable, honest seek rail when peaks are unavailable. */});return()=>{live=false;};},[examId,part]);
  const progress=duration>0?Math.max(0,Math.min(1,current/duration)):0;
  const bars=useMemo(()=>peaks?Array.from({length:count},(_,i)=>{
    const from=Math.floor(i*peaks.length/count),to=Math.floor((i+1)*peaks.length/count);
    const level=peaks.slice(from,to).reduce((a,b)=>a+b,0)/(to-from)/255;
    const height=2+level*34;
    return <rect key={i} x={i*3+.6} y={20-height/2} width="1.8" height={height} rx=".9"/>;
  }):null,[peaks,count]);
  return <div ref={container} className={v.waveSeek} data-waveform="soft-capsules" data-waveform-source={peaks?"audio":"unavailable"}>
    <svg className={v.capsules} viewBox={`0 0 ${count*3} 40`} preserveAspectRatio="none" aria-hidden="true">
      <defs><clipPath id={clip}><rect data-waveform-progress width={progress*count*3} height="40"/></clipPath></defs>
      {bars?<><g className={v.remaining}>{bars}</g><g className={v.played} clipPath={`url(#${clip})`}>{bars}</g></>:<rect className={v.remaining} x="0" y="19" width={count*3} height="2" rx="1"/>}
    </svg>
    <span className={v.playhead} style={{left:`${progress*100}%`}} aria-hidden="true"/>
    <input aria-label="Audio progress" aria-valuetext={`${time(current)} of ${time(duration)}`} type="range" min="0" max={duration||1} step="0.1" value={Math.min(current,duration||1)} onChange={e=>onSeek(Number(e.target.value))}/>
  </div>;
}
const time=(n:number)=>`${Math.floor((Number.isFinite(n)?n:0)/60).toString().padStart(2,"0")}:${Math.floor((Number.isFinite(n)?n:0)%60).toString().padStart(2,"0")}`;
function Skip({forward=false}:{forward?:boolean}){return <svg width="30" height="30" viewBox="0 0 32 32" aria-hidden="true"><g transform={forward?"translate(32 0) scale(-1 1)":undefined}><path d="M8 9H3V4M3.5 9a12 12 0 1 1-.4 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></g><text x="16" y="21" textAnchor="middle" fontSize="12" fontWeight="600" fill="currentColor">5</text></svg>}
function PlayIcon({playing}:{playing:boolean}){return <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true" fill="currentColor">{playing?<><rect x="5" y="4" width="5" height="16" rx="1"/><rect x="14" y="4" width="5" height="16" rx="1"/></>:<path d="M7 4.8a1 1 0 0 1 1.5-.86l12 7.2a1 1 0 0 1 0 1.72l-12 7.2A1 1 0 0 1 7 19.2Z"/>}</svg>}
export interface Moment {request:number;part:number;start:number;end:number;loop:boolean}
interface Props {
  uid:string;attemptId:string;examId:string;initialPart:number;position:number;
  visiblePart:number;onVisiblePart:(part:number)=>void;
  onCheckpoint:(part:number,seconds:number)=>void;onPart:(part:number)=>void;
  compact?:boolean;progress?:AudioProgress;moment?:Moment;onMomentStop?:()=>void;
}

/** Viewing questions never changes the audio source. Only an explicit audio action,
 * natural end or an explicitly requested AI moment can change audioPart. */
export function Player({uid,attemptId,examId,initialPart,position,visiblePart,onVisiblePart,onCheckpoint,onPart,progress:provided,moment,onMomentStop,compact=false}:Props){
  const [progress]=useState(()=>provided||new AudioProgress(uid,attemptId,examId,initialPart,position));
  const [audioPart,setAudioPart]=useState(progress.activePart);
  const [current,setCurrent]=useState(0),[duration,setDuration]=useState(0),[playing,setPlaying]=useState(false),[status,setStatus]=useState("Preparing audio…"),[authorized,setAuthorized]=useState(false);
  const audio=useRef<HTMLAudioElement>(null),preload=useRef<HTMLAudioElement>(null);
  const callbacks=useRef({onCheckpoint,onPart,onMomentStop});
  const binding=useRef<{part:number;ready:boolean}|null>(null),active=useRef(audioPart),autoplay=useRef(false),lastSave=useRef(0);
  const clip=useRef<Moment|undefined>(undefined),origin=useRef<{part:number;seconds:number}|null>(null);
  const finishRef=useRef<()=>void>(()=>{}),clipReadyCleanup=useRef<()=>void>(()=>{});
  useEffect(()=>{callbacks.current={onCheckpoint,onPart,onMomentStop};},[onCheckpoint,onPart,onMomentStop]);

  const save=useCallback(()=>{
    const el=audio.current,bound=binding.current;
    if(!el||!bound?.ready||bound.part!==active.current||origin.current||!Number.isFinite(el.currentTime))return;
    progress.set(bound.part,el.currentTime);callbacks.current.onCheckpoint(bound.part,el.currentTime);
  },[progress]);

  const finishMoment=useCallback(()=>{
    const saved=origin.current,el=audio.current;
    if(!saved)return;
    // Retire the temporary session before any asynchronous pause/seek events.
    clipReadyCleanup.current();el?.pause();clip.current=undefined;autoplay.current=false;
    active.current=saved.part;origin.current=null;
    if(binding.current?.part===saved.part&&binding.current.ready&&el){el.currentTime=saved.seconds;setCurrent(saved.seconds);}
    else setAudioPart(saved.part);
    callbacks.current.onMomentStop?.();
  },[]);
  useEffect(()=>{finishRef.current=finishMoment;},[finishMoment]);

  const startClip=useCallback(()=>{
    const el=audio.current,m=clip.current;
    if(!el||!m||!binding.current?.ready||binding.current.part!==m.part||active.current!==m.part)return;
    if(!Number.isFinite(m.start)||!Number.isFinite(m.end)||m.start<0||m.end<=m.start||m.end>el.duration+.05){finishRef.current();setStatus("This audio moment is unavailable.");return;}
    clipReadyCleanup.current();el.pause();
    let retries=0;
    const cleanup=()=>{el.removeEventListener("seeked",ready);el.removeEventListener("canplay",ready);};
    const ready=()=>{
      if(clip.current?.request!==m.request||active.current!==m.part){cleanup();return;}
      if(el.seeking||el.readyState<2)return;
      if(Math.abs(el.currentTime-m.start)>.15){
        if(retries++<2){el.currentTime=m.start;return;}
        cleanup();finishRef.current();setStatus("This audio moment is unavailable.");return;
      }
      cleanup();setCurrent(el.currentTime);
      void el.play().catch(()=>{finishRef.current();setStatus("Press Play to listen again.");});
    };
    clipReadyCleanup.current=cleanup;
    el.addEventListener("seeked",ready);el.addEventListener("canplay",ready);
    el.currentTime=m.start;setCurrent(m.start);
    if(!el.seeking&&el.readyState>=2)ready();
  },[]);

  useEffect(()=>{
    let live=true;
    const refresh=()=>authorize(uid,attemptId).then(()=>{if(live){setAuthorized(true);setStatus("");}}).catch(()=>{if(live)setStatus("Audio access interrupted. Press Play to reconnect.");});
    void refresh();const timer=setInterval(()=>{void refresh();},600000);
    const visible=()=>{if(document.visibilityState==="visible")void refresh();};
    document.addEventListener("visibilitychange",visible);
    return()=>{live=false;clipReadyCleanup.current();clearInterval(timer);document.removeEventListener("visibilitychange",visible);};
  },[uid,attemptId]);

  useEffect(()=>{
    if(!authorized||!audio.current)return;
    const el=audio.current,session={part:audioPart,ready:false};binding.current=session;
    setPlaying(false);setDuration(0);setCurrent(progress.get(audioPart));setStatus("Loading audio…");lastSave.current=0;
    const boundary=()=>{
      const m=clip.current;if(!m||m.part!==session.part)return false;
      if(el.currentTime>=m.end-.025||el.ended){
        if(m.loop)startClip();
        else finishRef.current();
      }
      return true;
    };
    const metadata=()=>{
      session.ready=true;setDuration(Number.isFinite(el.duration)?el.duration:0);
      if(clip.current?.part===audioPart){startClip();return;}
      const seconds=Math.max(0,Math.min(progress.get(audioPart),Number.isFinite(el.duration)?el.duration:0));
      el.currentTime=seconds;setCurrent(seconds);setStatus("");save();
      const shouldPlay=autoplay.current;autoplay.current=false;
      if(shouldPlay)void el.play().catch(()=>setStatus("Part ready. Press Play to continue."));
    };
    const update=()=>{
      boundary();setCurrent(el.currentTime);setPlaying(!el.paused);
      if(Math.abs(el.currentTime-lastSave.current)>=5){lastSave.current=el.currentTime;save();}
    };
    const ended=()=>{
      // WebKit may queue ended after a seek at EOF. Handle an active loop
      // unconditionally; ignore stale ended events after restoring normal time.
      const m=clip.current;
      if(m?.part===session.part){
        if(m.loop)startClip();
        else finishRef.current();
        return;
      }
      if(!el.ended&&el.currentTime<el.duration-.1)return;
      save();
      if(audioPart<4){active.current=audioPart+1;autoplay.current=true;setAudioPart(audioPart+1);callbacks.current.onPart(audioPart+1);}
      else setStatus("All four parts complete.");
    };
    const play=()=>{setPlaying(!el.paused);setStatus("");};
    const pause=()=>{setPlaying(!el.paused);setCurrent(el.currentTime);save();};
    const seeked=()=>{save();};
    const events:Record<string,EventListener>={loadedmetadata:metadata,timeupdate:update,seeked,ended,playing:play,pause,waiting:()=>setStatus("Buffering…"),canplay:()=>setStatus(""),error:()=>setStatus("Audio couldn’t load. Press Play to retry.")};
    for(const [name,fn] of Object.entries(events))el.addEventListener(name,fn);
    el.src=`/api/listening/audio/${attemptId}/${audioPart}`;el.load();
    const timer=setInterval(()=>{if(!el.paused&&clip.current)boundary();},40);
    const visibility=()=>{if(document.visibilityState==="hidden"){save();if(origin.current)finishRef.current();}};
    const pagehide=()=>{save();};
    document.addEventListener("visibilitychange",visibility);window.addEventListener("pagehide",pagehide);
    return()=>{
      save();for(const [name,fn] of Object.entries(events))el.removeEventListener(name,fn);
      clipReadyCleanup.current();clearInterval(timer);document.removeEventListener("visibilitychange",visibility);window.removeEventListener("pagehide",pagehide);el.pause();session.ready=false;
    };
  },[authorized,attemptId,audioPart,progress,save,startClip]);

  useEffect(()=>{if(authorized&&audioPart<4&&preload.current){preload.current.src=`/api/listening/audio/${attemptId}/${audioPart+1}`;preload.current.load();}},[authorized,attemptId,audioPart]);

  useEffect(()=>{
    if(!moment){if(origin.current)finishMoment();return;}
    if(!origin.current){
      save();const el=audio.current;
      origin.current={part:active.current,seconds:binding.current?.ready&&el?el.currentTime:progress.get(active.current)};
    }
    clip.current=moment;
    if(active.current!==moment.part){audio.current?.pause();active.current=moment.part;setAudioPart(moment.part);}
    else startClip();
  },[moment,finishMoment,save,progress,startClip]);

  function switchAudio(part:number){
    if(part===active.current)return;
    if(origin.current)finishMoment();
    save();audio.current?.pause();active.current=part;autoplay.current=true;setAudioPart(part);
  }
  async function toggle(){
    const el=audio.current;if(!el)return;
    if(origin.current){finishMoment();return;}
    if(!el.paused){el.pause();return;}
    try{
      if(!authorized||el.error){await authorize(uid,attemptId);autoplay.current=true;if(!authorized)setAuthorized(true);else{save();if(binding.current)binding.current.ready=false;el.load();}return;}
      await el.play();
    }catch{setStatus("Press Play again when your connection is restored.");}
  }
  function seek(seconds:number){
    if(origin.current){finishMoment();return;}
    const el=audio.current;if(!el||!binding.current?.ready||!Number.isFinite(el.duration))return;
    el.currentTime=Math.min(el.duration,Math.max(0,seconds));setCurrent(el.currentTime);save();
  }
  useEffect(()=>{
    const key=(e:KeyboardEvent)=>{
      if(e.defaultPrevented||(e.target as HTMLElement).closest("input,textarea,select,button,a,[contenteditable=true],[role=slider]"))return;
      if(e.code==="Space"){e.preventDefault();void toggle();}
      else if(e.key==="ArrowLeft"||e.key==="ArrowRight"){e.preventDefault();seek((audio.current?.currentTime||0)+(e.key==="ArrowLeft"?-5:5));}
    };window.addEventListener("keydown",key);return()=>window.removeEventListener("keydown",key);
  });

  return <section className={`${v.player} ${compact?v.compact:""}`} aria-label="Listening audio player" data-audio-part={audioPart} data-visible-part={visiblePart} data-playing={playing}>
    <audio ref={audio} preload="metadata"/><audio ref={preload} preload="metadata" aria-hidden="true"/>
    <div className={v.controls} data-player="controls">
      <button type="button" aria-label="Back 5 seconds" onClick={()=>seek((audio.current?.currentTime||0)-5)}><Skip/></button>
      <button type="button" className={v.play} aria-label={playing?"Pause":"Play"} onClick={()=>void toggle()}><PlayIcon playing={playing}/></button>
      <button type="button" aria-label="Forward 5 seconds" onClick={()=>seek((audio.current?.currentTime||0)+5)}><Skip forward/></button>
    </div>
    <div className={v.seek} data-player="seek"><time>{time(current)}</time><Waveform key={examId} examId={examId} part={audioPart} current={current} duration={duration} onSeek={seek}/><time>{time(duration)}</time></div>
    <nav className={v.parts} aria-label="Listening parts">{[1,2,3,4].map(p=><div className={v.segment} data-selected={visiblePart===p} key={p}>
      <button type="button" aria-pressed={visiblePart===p} onClick={()=>onVisiblePart(p)}>Part {p}{audioPart===p&&<span className={v.audioDot} aria-label="Current audio"/>}</button>
      {visiblePart===p&&audioPart!==p&&<button className={v.listenPart} type="button" aria-label={`Listen to Part ${p}`} title={`Listen to Part ${p}`} onClick={()=>switchAudio(p)}><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M5 3 13 8 5 13Z" fill="currentColor"/></svg></button>}
    </div>)}</nav>
    <span className={v.status} data-issue={/interrupted|couldn’t|retry|reconnect|restored|Press Play/.test(status)} role="status">{status}</span>
  </section>;
}
