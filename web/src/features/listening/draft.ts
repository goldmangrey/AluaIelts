import {ApiError} from "@/lib/api/client";
import {api,attempt} from "./api";
import type {Attempt,State,Sync} from "./models";
type Pending={body:Sync;serial:number};
export class ListeningDraft {
  private listeners=new Set<()=>void>(); private timer:ReturnType<typeof setTimeout>|undefined;private busy=false;private stopped=false;private serial=0;private savedSerial=0;
  private pending?:Pending;private submitBody?:{event_id:string;expected_version:number};private base:Attempt;private key:string;private failures=0;
  snapshot:{answers:Record<string,string>;state:State;status:string;conflict:Attempt|null;submitting:boolean;storage:boolean};
  constructor(public initial:Attempt,private uid:string){this.base=initial;this.key=`alua:listening:${uid}:${initial.id}:${initial.content_hash}`;this.snapshot={answers:{...initial.answers},state:structuredClone(initial.state),status:"Saved",conflict:null,submitting:false,storage:true};}
  get=()=>this.snapshot;subscribe=(fn:()=>void)=>{this.listeners.add(fn);return()=>{this.listeners.delete(fn)}};
  private publish(patch:Partial<typeof this.snapshot>){this.snapshot={...this.snapshot,...patch};this.listeners.forEach(fn=>fn());}
  private persist(){try{localStorage.setItem(this.key,JSON.stringify({base:this.base,answers:this.snapshot.answers,state:this.snapshot.state,serial:this.serial,savedSerial:this.savedSerial,pending:this.pending,submitBody:this.submitBody}));}catch{this.publish({storage:false});}}
  initialize(){try{const raw=localStorage.getItem(this.key);if(raw){const d=JSON.parse(raw);if(d.base?.id===this.initial.id&&d.base?.content_hash===this.initial.content_hash&&Number.isSafeInteger(d.serial)&&d.answers&&d.state&&d.base.version<=this.initial.version){this.base=d.base;this.serial=d.serial;this.savedSerial=d.savedSerial??0;this.pending=d.pending;this.submitBody=d.submitBody;this.publish({answers:d.answers,state:d.state,status:d.serial<=(d.savedSerial??0)&&!d.pending?"Saved":"Restored local draft",submitting:!!d.submitBody});if(!this.pending&&!this.submitBody&&this.base.version!==this.initial.version)this.merge(this.initial);}}}catch{this.publish({storage:false});}if(!this.submitBody)this.schedule(0);}
  changeAnswer(qid:string,value:string){if(this.snapshot.submitting||this.snapshot.conflict)return;this.edit({answers:{...this.snapshot.answers,[qid]:value}});}
  changeState(patch:Partial<State>){if(this.snapshot.submitting||this.snapshot.conflict)return;this.edit({state:{...this.snapshot.state,...patch}});}
  private edit(patch:Partial<typeof this.snapshot>){this.serial++;this.publish({...patch,status:"Saving…"});this.persist();this.schedule(450);}
  private schedule(ms:number){if(this.stopped||this.snapshot.conflict||this.submitBody)return;clearTimeout(this.timer);this.timer=setTimeout(()=>{void this.flush().catch(()=>{});},ms);}
  private merge(remote:Attempt){const base=this.base.answers,local=this.snapshot.answers;const answers={...remote.answers};let conflict=false;for(const qid of new Set([...Object.keys(base),...Object.keys(local)])){if((local[qid]??"")!==(base[qid]??"")){if((remote.answers[qid]??"")!==(base[qid]??"")&&(remote.answers[qid]??"")!==(local[qid]??""))conflict=true;answers[qid]=local[qid]??"";}}
    if(remote.status==="submitted"){this.publish({conflict:remote,status:"This attempt has finished on another device."});return;}
    if(conflict){this.publish({conflict:remote,status:"Conflicting answers from another device. Choose which draft to keep."});return;}
    const state={...remote.state};for(const key of Object.keys(state) as (keyof State)[]){if(JSON.stringify(this.snapshot.state[key])!==JSON.stringify(this.base.state[key]))Object.assign(state,{[key]:this.snapshot.state[key]});}this.base=remote;this.serial++;this.publish({answers,state,status:"Merged newer server answers; saving…"});this.persist();}
  resolve(local:boolean){const remote=this.snapshot.conflict;if(!remote||remote.status==="submitted")return;this.base=remote;this.pending=undefined;this.serial++;this.publish({answers:local?this.snapshot.answers:{...remote.answers},state:local?this.snapshot.state:remote.state,conflict:null,status:"Saving reconciled draft…"});this.persist();this.schedule(0);}
  async flush():Promise<void>{if(this.busy){while(this.busy&&!this.stopped)await new Promise(r=>setTimeout(r,25));if(this.snapshot.conflict)throw Error("Conflict");if(this.pending||this.serial>this.savedSerial)return this.flush();return;}
    if(this.stopped||this.snapshot.conflict||this.submitBody)return;
    if(!this.pending&&this.serial<=this.savedSerial)return;
    this.busy=true;
    try{this.pending??={body:{event_id:crypto.randomUUID(),expected_version:this.base.version,answers:structuredClone(this.snapshot.answers),state:structuredClone(this.snapshot.state)},serial:this.serial};this.persist();const pending=this.pending;
      const saved=await api(this.uid)(`/listening/attempts/${this.initial.id}/sync`,undefined,{method:"POST",body:pending.body}) as Attempt;
      this.base={...this.base,...saved};this.savedSerial=pending.serial;this.pending=undefined;this.failures=0;this.publish({status:this.serial>this.savedSerial?"Saving…":"Saved"});this.persist();
    }catch(error){if(error instanceof ApiError&&error.status===409){this.pending=undefined;const latest=await attempt(this.uid,this.initial.id);this.merge(latest);}else{this.publish({status:"Offline or save interrupted · retrying"});this.failures++;}throw error;
    }finally{this.busy=false;if(!this.stopped&&(this.pending||this.serial>this.savedSerial))this.schedule(Math.min(8000,800*2**this.failures));}}
  async submit(){if(this.snapshot.conflict)throw Error("Resolve draft conflict first");if(!this.submitBody){await this.flush();if(this.pending||this.serial>this.savedSerial)throw Error("Save still pending");this.submitBody={event_id:crypto.randomUUID(),expected_version:this.base.version};this.publish({submitting:true,status:"Finishing…"});this.persist();}
    try{const ended=await api(this.uid)(`/listening/attempts/${this.initial.id}/submit`,undefined,{method:"POST",body:this.submitBody}) as Attempt;try{localStorage.removeItem(this.key);}catch{}return ended;}catch(error){if(error instanceof ApiError&&error.status===409){this.submitBody=undefined;this.publish({submitting:false});this.merge(await attempt(this.uid,this.initial.id));}else this.publish({status:"Finish not confirmed · retry to confirm safely"});throw error;}}
  hasUnsaved=()=>!!this.pending||this.serial>this.savedSerial||!!this.submitBody;
  dispose(){this.persist();this.stopped=true;clearTimeout(this.timer);this.listeners.clear();}
}
