'use client';
import {useSyncExternalStore} from 'react';
function subscribe(f:()=>void){window.addEventListener('hashchange',f);window.addEventListener('popstate',f);return()=>{window.removeEventListener('hashchange',f);window.removeEventListener('popstate',f)}}
export function usePracticeLocation(){return new URLSearchParams(useSyncExternalStore(subscribe,()=>window.location.hash,()=>'').replace(/^#/,''))}
export function navigatePractice(values:Record<string,string>={}){window.location.hash=new URLSearchParams(values).toString();window.scrollTo({top:0,behavior:'instant'})}
