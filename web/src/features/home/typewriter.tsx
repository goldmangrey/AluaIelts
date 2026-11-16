'use client';

import {useEffect, useState} from 'react';
import s from './hero.module.css';

const questions=['Why was my answer wrong?','What did I miss?','How can I improve?'] as const;

export function AIQuestion(){
  // Identical server/initial client text; only this small line needs hydration.
  const [state,setState]=useState<{text:string;active:boolean}>({text:questions[0],active:true});
  useEffect(()=>{
    const motion=window.matchMedia('(prefers-reduced-motion: reduce)');
    let timer:ReturnType<typeof setTimeout>|undefined;
    function type(index:number,characters=0){
      const phrase=questions[index%questions.length]!;
      const complete=characters===phrase.length,finished=index===6&&complete;
      setState({text:phrase.slice(0,characters),active:!finished});
      if(finished)return;
      timer=setTimeout(()=>complete?type(index+1):type(index,characters+1),complete?2500:52);
    }
    function start(){
      clearTimeout(timer);
      if(motion.matches)return;
      // The first phrase starts fully readable, then two quiet rotations finish on it.
      timer=setTimeout(()=>type(1),3000);
    }
    function changed(){
      clearTimeout(timer);
      setState({text:questions[0],active:!motion.matches});
      start();
    }
    start();
    motion.addEventListener('change',changed);
    return()=>{clearTimeout(timer);motion.removeEventListener('change',changed);};
  },[]);
  return <p className={s.question}>
    <span className={s.accessible}>Why was my answer wrong? What did I miss? How can I improve?</span>
    <span className={s.reserve} aria-hidden="true">{questions[0]}<span className={s.cursor}>▍</span></span>
    <span className={s.typed} aria-hidden="true" data-active={state.active}>{state.text}<span className={s.cursor}>▍</span></span>
    <span className={s.static} aria-hidden="true">{questions[0]}</span>
  </p>;
}
