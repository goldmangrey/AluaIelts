'use client';
import {TestStartModal,useTestSelection} from '@/components/test-start-modal';
import {LuaMascot} from '@/components/lua-mascot';
import Link from 'next/link';
import {useState} from 'react';
import data from './catalog.json';
import {SignInDialog} from '@/features/auth/guest-access';
import s from '@/features/auth/guest-access.module.css';
export type Module='listening'|'reading'|'writing'|'speaking';
export function startDestination(module:string,id:string){return '/practice/start?'+new URLSearchParams({module,id,intent:crypto.randomUUID()}).toString()}
export function GuestCatalog({module,book,examId,compact=false}:{module:Module;book?:number;examId?:string;compact?:boolean}){
 const selection=useTestSelection();
 const selectedTest=data.find(v=>v.module===module&&v.id===selection.selected&&(!book||v.book===book));
 const [category,setCategory]=useState(''),[search,setSearch]=useState(''),[page,setPage]=useState(1),[selected,setSelected]=useState<string>();
 const base=data.filter(v=>v.module===module&&(!book||v.book===book)&&(!examId||v.id===examId));
 const categories=[...new Set(base.map(v=>v.category))];const items=base.filter(v=>(!category||v.category===category)&&(`${v.title} ${v.category}`.toLowerCase().includes(search.toLowerCase()))),pages=Math.max(1,Math.ceil(items.length/24));
 return <section className={compact?undefined:s.catalog} aria-label={`${module} public catalog`}><Link className="back-link" href={examId||book?`/${module}`:'/'}>← {examId||book?'Back to catalog':'Back to Home'}</Link>{!compact&&<><h1 style={{display:"flex",alignItems:"center",gap:16}}>{module.charAt(0).toUpperCase()+module.slice(1)}{module==='listening'&&!examId&&<LuaMascot emotion="listening" size={88}/>}</h1><p>Explore available IELTS practice. Sign in when you’re ready to start.</p></>}
 {!examId&&<div className={s.filters}><label>Search practice<input type="search" value={search} onChange={e=>{setSearch(e.target.value);setPage(1)}}/></label><label>Collection or topic<select value={category} onChange={e=>{setCategory(e.target.value);setPage(1)}}><option value="">All</option>{categories.map(c=><option key={c}>{c}</option>)}</select></label></div>}
 <p className={s.count}>{items.length} available {items.length===1?'practice':'practices'}</p><div className={s.grid}>{items.slice((page-1)*24,page*24).map(v=><article key={v.id} className={s.card}><small>{v.category.replaceAll('_',' ')}</small><h2>{v.title}</h2><p>{v.description}</p><button className="button" onClick={e=>{e.currentTarget.focus({preventScroll:true});if(module==='reading'||module==='listening')selection.open(v.id);else setSelected(startDestination(module,v.id))}}>Start Practice</button></article>)}</div>{!items.length&&<p>No available practice matches your search.</p>}{pages>1&&<nav className={s.filters} aria-label="Catalog pages"><button className="button secondary" disabled={page===1} onClick={()=>setPage(page-1)}>Previous</button><span>{page} / {pages}</span><button className="button secondary" disabled={page===pages} onClick={()=>setPage(page+1)}>Next</button></nav>}{selectedTest&&(module==='reading'||module==='listening')&&<TestStartModal key={selectedTest.id} skill={module==='reading'?'Reading':'Listening'} book={selectedTest.book!} test={Number(selectedTest.id.split('-').at(-1))} facts={Array.from(selectedTest.description.matchAll(/(\d+) (questions|passages|parts)/g),m=>({value:Number(m[1]),label:m[2]!.charAt(0).toUpperCase()+m[2]!.slice(1)}))} note="Sign in to confirm test availability and save your progress." guest onClose={selection.close}/ >}{selected&&<SignInDialog destination={selected} onClose={()=>setSelected(undefined)}/>}</section>;
}
