import type {ReactNode} from 'react';
import s from './soft.module.css';
export function TopicIcon({category}:{category:string}){
 const c=category.toLowerCase();
 const path=/educat|work|learn/.test(c)?<><path d="m2 9 10-5 10 5-10 5zM6 11v6c4 3 8 3 12 0v-6M22 9v7"/></>:/home|place|build/.test(c)?<><path d="m3 11 9-8 9 8M5 10v11h14V10M9 21v-7h6v7"/></>:/nature|animal|environment/.test(c)?<><path d="M20 4C8 3 3 8 5 15c2 7 16 6 15-11ZM4 21 16 9"/></>:<><rect x="4" y="4" width="16" height="16" rx="4"/><path d="M8 9h8M8 13h8M8 17h4"/></>;
 return <span className={s.icon} aria-hidden="true"><svg viewBox="0 0 24 24">{path}</svg></span>;
}
export function PracticeHeader({title,subtitle}:{title:string;subtitle?:string}){return <header className={s.hero}><h1>{title}</h1>{subtitle&&<p>{subtitle}</p>}</header>}
export function PracticeCard({title,meta,action,category,number,onClick,disabled,children}:{title:string;meta?:string;action:string;category?:string;number?:number;onClick:()=>void;disabled?:boolean;children?:ReactNode}){return <button className={s.card} onClick={onClick} disabled={disabled}>{category&&<TopicIcon category={category}/>} {number!==undefined&&<span className={s.number}>{String(number).padStart(2,'0')}</span>}<h2>{title}</h2>{meta&&<p>{meta}</p>}{children}<span className={s.action}>{action} <span aria-hidden="true">→</span></span></button>}
