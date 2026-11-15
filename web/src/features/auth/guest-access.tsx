'use client';
import Link from 'next/link';
import {useEffect,useRef,useState} from 'react';
import {usePathname,useRouter} from 'next/navigation';
import {prepareGoogleAuth,retrySession,useSession} from './session';
import {safeReturnPath} from './redirect';
import {authMessage} from './messages';
import s from './guest-access.module.css';
export function AuthRequired({title='Keep your IELTS practice in one place.',description='Sign in to revisit your results, saved AI explanations and learning progress.',destination,cancel}:{title?:string;description?:string;destination?:string;cancel?:()=>void}){
 const session=useSession(),path=usePathname(),router=useRouter(),next=safeReturnPath(destination??path),run=useRef<null|(()=>Promise<void>)>(null),lock=useRef(false);
 const [ready,setReady]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState('');
 useEffect(()=>{let live=true;void prepareGoogleAuth('sign-in',next).then(fn=>{if(live){run.current=fn;setReady(true)}}).catch(e=>{if(live)setError(authMessage(e))});return()=>{live=false}},[next]);
 useEffect(()=>{if(session.status==='ready'&&session.user&&destination)router.replace(next)},[session.status,session.user,destination,next,router]);
 async function connect(){if(lock.current||!run.current)return;lock.current=true;setBusy(true);setError('');try{await run.current();router.replace(next);router.refresh()}catch(e){setError(authMessage(e))}finally{lock.current=false;setBusy(false)}}
 if(session.status==='loading')return <p role="status">Checking your session…</p>;
 return <section className={s.panel} aria-label="Sign in to Alua"><h1 tabIndex={-1}>{title}</h1><p>{description}</p><div className={s.actions}><button className={s.control} disabled={!ready||busy} onClick={()=>void connect()}>{busy?'Signing in…':'Continue with Google'}</button>{cancel?<button className={`${s.control} ${s.secondary}`} disabled={busy} onClick={cancel}>Not now</button>:<Link className={`${s.control} ${s.secondary}`} href="/">Explore IELTS practice</Link>}</div>{(error||session.status==='error')&&<p className={s.error} role="alert">{error||authMessage(session.error)}</p>}{session.status==='error'&&<button className="text-button" onClick={()=>void retrySession().catch(e=>setError(authMessage(e)))}>Retry session</button>}<p className={s.hint}>Using Instagram or Threads? If Google sign-in is blocked, open this page in Safari or Chrome using your browser menu.</p><Link className={s.options} href={`/login?next=${encodeURIComponent(next)}`}>More sign-in options</Link></section>;
}
export function SignInDialog({destination,onClose}:{destination:string;onClose:()=>void}){const ref=useRef<HTMLDialogElement>(null);useEffect(()=>{
 const dialog=ref.current;if(!dialog)return;
 const previous=document.activeElement instanceof HTMLElement?document.activeElement:null;
 const y=window.scrollY,body=document.body,html=document.documentElement;
 const saved={overflow:body.style.overflow,position:body.style.position,top:body.style.top,width:body.style.width,htmlOverflow:html.style.overflow};
 Object.assign(body.style,{overflow:'hidden',position:'fixed',top:`-${y}px`,width:'100%'});html.style.overflow='hidden';
 dialog.showModal();dialog.querySelector<HTMLElement>('h1')?.focus({preventScroll:true});
 return()=>{dialog.close();Object.assign(body.style,{overflow:saved.overflow,position:saved.position,top:saved.top,width:saved.width});html.style.overflow=saved.htmlOverflow;window.scrollTo(0,y);previous?.focus({preventScroll:true})};
 },[]);return <dialog ref={ref} className={s.dialog} onKeyDown={e=>{
 if(e.key!=='Tab')return;
 const items=[...e.currentTarget.querySelectorAll<HTMLElement>('button:not(:disabled), a[href], input:not(:disabled), [tabindex="0"]')].filter(el=>el.getClientRects().length>0);
 if(!items.length)return;e.preventDefault();const index=items.indexOf(document.activeElement as HTMLElement);
 const next=index<0?(e.shiftKey?items.length-1:0):(index+(e.shiftKey?-1:1)+items.length)%items.length;items[next]?.focus();
 }} onCancel={e=>{e.preventDefault();onClose()}} aria-label="Start your practice"><AuthRequired title="Ready to practise?" description="Sign in to start your practice and save your progress." destination={destination} cancel={onClose}/></dialog>}
export function PersonalNavigation({className}:{className?:string}){const session=useSession();return <nav className={className??s.nav} aria-label="Your account">{session.status==='loading'?<span className={s.loading} role="status" aria-label="Checking session"/>:session.status==='error'?<button className="button secondary" onClick={()=>void retrySession().catch(()=>{})}>Retry session</button>:session.status==='ready'&&session.user?<><Link href="/practice/history">History</Link><Link href="/practice/mistakes">My Mistakes</Link><Link href="/profile">Profile</Link></>:<Link className="button secondary" href="/login">Get started</Link>}</nav>}
export function PersonalLink({href,children}:{href:string;children:React.ReactNode}){const session=useSession();return session.status==='ready'&&session.user?<Link href={href}>{children}</Link>:null}
