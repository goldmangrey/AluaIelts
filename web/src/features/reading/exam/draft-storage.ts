import type {SubmissionEvent} from "@/features/exam-reliability/final-snapshot";
import type { SaveEvent } from "./answers";
export interface Highlight { id: string; passageId: string; block: number; start: number; end: number; quote: string }
export interface ViewDraft { passage: number; current: string | null; review: string[]; size: number; split: number; mobile: "passage" | "questions"; views: [number, { passageId: string; textScrollTop: number; questionsScrollTop: number; lastFocusedQuestionId: string | null }][]; highlights: Highlight[] }
export interface Draft {
  key: string; uid: string; attemptId: string; hash: string; revision: number; modified: number;
  version: number; base: Record<string,string>; answers: Record<string,string>; pending?: SaveEvent; pendingRevision?:number;
  submit?: SubmissionEvent; rejectedSubmit?:SubmissionEvent; legacySubmit?:SubmissionEvent; listening?:unknown; finalizing?: boolean; finalAnswers?:Record<string,string>; conflicts?:{id:string;local:string;server:string}[]; view?: ViewDraft;
}
export interface DraftStore { read(): Promise<Draft | undefined>; write(value: Draft): Promise<void>; acquire(): Promise<boolean>; release(): Promise<void> }
const revoked = new Set<string>();
let database: Promise<IDBDatabase> | undefined;
function db() {
  return database ??= new Promise<IDBDatabase>((resolve,reject) => {
    const timer=setTimeout(()=>{database=undefined;reject(new Error("Local storage timed out. Keep this page open and retry."))},5000);
    const req = indexedDB.open("alua-reading-drafts",1);
    req.onupgradeneeded = () => { req.result.createObjectStore("drafts",{keyPath:"key"}); req.result.createObjectStore("leases",{keyPath:"key"}); };
    req.onsuccess = () => {clearTimeout(timer);req.result.onversionchange=()=>{req.result.close();database=undefined};resolve(req.result)};
    req.onerror = () => {clearTimeout(timer);database=undefined;reject(req.error)};
    req.onblocked = () => {clearTimeout(timer);reject(new Error("Local storage is blocked. Close other Alua tabs and retry."))};
  });
}
async function transaction<T>(name: string, run: (store: IDBObjectStore, done:(value:T)=>void) => void): Promise<T> {
  const database = await db();
  return new Promise<T>((resolve,reject) => {
    const tx=database.transaction(name,"readwrite"); let result:T;
    const timer=setTimeout(()=>{tx.abort();reject(new Error("Local storage timed out"))},5000);
    run(tx.objectStore(name), value=>{result=value});
    tx.oncomplete=()=>{clearTimeout(timer);resolve(result)};tx.onerror=()=>{clearTimeout(timer);reject(tx.error)};tx.onabort=()=>{clearTimeout(timer);reject(tx.error ?? new Error("Local storage unavailable"))};
  });
}
export function allowDraftOwner(uid:string) { revoked.delete(uid); }
export async function clearDraftOwner(uid:string) {
  revoked.add(uid);
  if(typeof indexedDB==="undefined")return;
  for(const name of ["drafts","leases"]) await transaction<void>(name,(store,done)=>{
    const req=store.openCursor();req.onsuccess=()=>{const cursor=req.result;if(!cursor){done();return}if(cursor.value.uid===uid)cursor.delete();cursor.continue()};
  });
}
export function browserDraftStore(uid:string, id:string, hash:string, owner:string):DraftStore {
  const key=JSON.stringify([uid,id,hash]);
  return {
    read:()=>transaction<Draft|undefined>("drafts",(store,done)=>{const r=store.get(key);r.onsuccess=()=>done(r.result)}),
    write:async(value)=>{
      if(revoked.has(uid))throw Error("Account changed");
      const database=await db();
      await new Promise<void>((resolve,reject)=>{
        const tx=database.transaction(["drafts","leases"],"readwrite");const r=tx.objectStore("leases").get(key);
        r.onsuccess=()=>{if(revoked.has(uid)||r.result?.owner!==owner||r.result.expires<=Date.now()){tx.abort();return}const drafts=tx.objectStore("drafts");const previous=drafts.get(key);previous.onsuccess=()=>{if(previous.result&&previous.result.revision>value.revision){tx.abort();return}drafts.put({...value,key})}};
        const timer=setTimeout(()=>{tx.abort();reject(new Error("Local storage timed out"))},5000);
        tx.oncomplete=()=>{clearTimeout(timer);resolve()};tx.onerror=()=>{clearTimeout(timer);reject(tx.error)};tx.onabort=()=>{clearTimeout(timer);reject(new Error("Local draft lease expired. Reload to recover safely."))};
      });
    },
    acquire:()=>transaction<boolean>("leases",(store,done)=>{const r=store.get(key);r.onsuccess=()=>{
      const lease=r.result;const now=Date.now();
      if(lease && lease.owner!==owner && lease.expires>now){done(false);return}
      store.put({key,uid,owner,expires:now+3000});done(true);
    }}),
    release:()=>transaction<void>("leases",(store,done)=>{const r=store.get(key);r.onsuccess=()=>{if(r.result?.owner===owner)store.delete(key);done()}}),
  };
}
