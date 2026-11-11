import {browserDraftStore,type DraftStore} from '@/features/reading/exam/draft-storage';
import {api} from './api';
import type {Attempt} from './contract';
/** One writer queue: late responses advance the base version, never replace local text. */
export class WritingDraft {
 private value:{essay:string;version:number;status:string;conflict:boolean};
 private listeners=new Set<()=>void>();private timer?:ReturnType<typeof setTimeout>;private pending?:Promise<void>;private stopped=false;private store:DraftStore;private pulse?:ReturnType<typeof setInterval>;private revision=0;private base:string;private localQueue=Promise.resolve();
 constructor(readonly initial:Attempt,private uid:string){this.base=initial.essay;this.store=browserDraftStore(uid,initial.id,'writing-v2',crypto.randomUUID());this.value={essay:initial.essay,version:initial.version,status:'saved',conflict:false};}
 async initialize(){let acquired=false;for(let n=0;n<5;n++){if(await this.store.acquire()){acquired=true;break;}await new Promise(r=>setTimeout(r,800));}if(!acquired)throw Error('draft_locked');const old=await this.store.read();if(old){this.revision=old.revision;if(old.answers.essay!==this.initial.essay){this.value={...this.value,essay:old.answers.essay??this.initial.essay,status:'unsaved',conflict:old.base.essay!==this.initial.essay};}}this.pulse=setInterval(()=>{void this.store.acquire().then(ok=>{if(!ok)this.publish({conflict:true,status:'error'})}).catch(()=>this.publish({status:'error'}));},1000);}
 private persist(){const snapshot=this.value,revision=++this.revision,base=this.base;this.localQueue=this.localQueue.catch(()=>{}).then(()=>this.store.write({key:'',uid:this.uid,attemptId:this.initial.id,hash:'writing-v2',revision,modified:Date.now(),version:snapshot.version,base:{essay:base},answers:{essay:snapshot.essay}}));void this.localQueue.catch(()=>this.publish({status:'error'}));}
 get=()=>this.value;
 subscribe=(fn:()=>void)=>{this.listeners.add(fn);return()=>{this.listeners.delete(fn)}};
 private publish(p:Partial<typeof this.value>){this.value={...this.value,...p};this.listeners.forEach(fn=>fn());}
 change(essay:string){this.publish({essay,status:'unsaved'});this.persist();clearTimeout(this.timer);this.timer=setTimeout(()=>{void this.flush().catch(()=>{})},700);}
 flush=async():Promise<void>=>{
  clearTimeout(this.timer);if(this.pending){await this.pending;if(this.value.status!=='saved')return this.flush();return;}
  if(this.value.conflict)throw Error('draft_conflict');if(this.value.status==='saved')return;
  const essay=this.value.essay,version=this.value.version;this.publish({status:'saving'});
  this.pending=(async()=>{try{const saved=await api(this.uid)(`/writing/attempts/${this.initial.id}`,undefined,{method:'PUT',body:{expected_version:version,essay}}) as Attempt;this.base=saved.essay;this.publish({version:saved.version,status:this.value.essay===essay?'saved':'unsaved'});this.persist();}catch(e){this.publish({status:'error',conflict:!!e&&typeof e==='object'&&'status' in e&&e.status===409});throw e;}finally{this.pending=undefined;}})();
  await this.pending;
  if(this.value.status==='unsaved')return this.flush();
 };
 dirty=()=>this.value.status!=='saved';
 dispose(){clearTimeout(this.timer);clearInterval(this.pulse);if(!this.stopped){this.stopped=true;void this.flush().catch(()=>{}).finally(()=>this.localQueue.catch(()=>{}).then(()=>this.store.release()));}this.listeners.clear();}
}
