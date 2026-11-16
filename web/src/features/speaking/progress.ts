export type Practised=Readonly<Record<string,number>>;
const empty:Practised=Object.freeze({});
export function progressStore(uid:string|undefined,allowed:ReadonlySet<string>){
 const key=uid?`alua:speaking:progress:v2:${uid}`:undefined;const listeners=new Set<()=>void>();
 let items:Practised=empty,error=false;
 const read=():Practised=>{if(!key||typeof window==='undefined')return empty;try{const value=JSON.parse(localStorage.getItem(key)??'{}');if(!value||typeof value!=='object'||Array.isArray(value))throw Error('storage');error=false;return Object.fromEntries(Object.entries(value).filter((entry):entry is [string,number]=>allowed.has(entry[0])&&typeof entry[1]==='number'&&Number.isFinite(entry[1])&&entry[1]>0));}catch{error=true;return empty;}};
 items=read();
 const publish=()=>listeners.forEach(f=>f());
 const storage=(e:StorageEvent)=>{if(e.key===key||e.key===null){items=read();publish();}};
 return {get:()=>items,server:()=>empty,failed:()=>error,subscribe:(f:()=>void)=>{listeners.add(f);if(listeners.size===1)window.addEventListener('storage',storage);return()=>{listeners.delete(f);if(!listeners.size)window.removeEventListener('storage',storage);}},toggle:(id:string)=>{if(!key||!allowed.has(id))return;const fresh=read(),next={...(error?items:fresh)};if(next[id])delete next[id];else next[id]=Date.now();items=next;try{localStorage.setItem(key,JSON.stringify(next));error=false;}catch{error=true;}publish();}};
}
