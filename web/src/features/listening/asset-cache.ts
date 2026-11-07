import {api} from "./api";
interface Entry {url?:string;bytes:number;refs:number;used:number;flight?:Promise<string>}
/** Private, workspace-scoped LRU. Unmounting one image never revokes another's URL. */
export class ListeningAssetCache {
 private entries=new Map<string,Entry>();private owners=0;private stopped=false;private abort?:AbortController;
 readonly budget=typeof navigator!=="undefined"&&/Mobi|Android/i.test(navigator.userAgent)?24*1024*1024:64*1024*1024;
 constructor(readonly uid:string,readonly attempt:string,readonly hash:string){}
 retain(){this.owners++;this.stopped=false;return()=>{this.owners--;queueMicrotask(()=>{if(!this.owners)this.dispose();});};}
 peek(id:string){return this.entries.get(id)?.url;}
 acquire(id:string){let e=this.entries.get(id);if(!e){e={bytes:0,refs:0,used:performance.now()};this.entries.set(id,e);}e.refs++;e.used=performance.now();let live=true;return()=>{if(!live)return;live=false;e.refs--;this.trim();};}
 async load(id:string):Promise<string>{
  if(this.stopped)throw Error("Workspace closed");
  let e=this.entries.get(id);if(!e){e={bytes:0,refs:0,used:performance.now()};this.entries.set(id,e);}e.used=performance.now();if(e.url)return e.url;if(e.flight)return e.flight;
  const entry=e;
  entry.flight=api(this.uid,75_000)(`/listening/attempts/${this.attempt}/assets/${id}`,(this.abort??=new AbortController()).signal,undefined,"blob").then(blob=>{
   if(this.stopped)throw Error("Workspace closed");entry.url=URL.createObjectURL(blob as Blob);entry.bytes=(blob as Blob).size;this.trim(id);return entry.url;
  }).finally(()=>{entry.flight=undefined;});return entry.flight;
 }
 private trim(protect?:string){let bytes=[...this.entries.values()].reduce((n,e)=>n+e.bytes,0);for(const [id,e] of [...this.entries].sort((a,b)=>a[1].used-b[1].used)){if(bytes<=this.budget&&this.entries.size<=48)break;if(e.refs||e.flight||id===protect)continue;if(e.url)URL.revokeObjectURL(e.url);bytes-=e.bytes;this.entries.delete(id);}}
 prefetch(ids:string[]){const connection=(navigator as Navigator&{connection?:{saveData?:boolean;effectiveType?:string}}).connection;if(connection?.saveData||connection?.effectiveType?.includes("2g"))return;
  const queue=[...new Set(ids)];const worker=async()=>{while(queue.length&&!this.stopped){const id=queue.shift()!;try{await this.load(id);}catch{/* Images remain retryable; answer persistence is independent. */}}};void Promise.all([worker(),worker()]);
 }
 dispose(){this.stopped=true;this.abort?.abort();for(const e of this.entries.values())if(e.url)URL.revokeObjectURL(e.url);this.entries.clear();}
}
