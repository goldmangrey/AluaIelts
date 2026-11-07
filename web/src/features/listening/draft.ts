import {rejectedSubmit} from "@/features/exam-reliability/submit-errors";
import {AudioProgress} from "./audio-progress";
import {ApiError} from "@/lib/api/client";
import {api,attempt} from "./api";
import {browserDraftStore,type Draft,type DraftStore} from "@/features/reading/exam/draft-storage";
import {answersChecksum,canonicalAnswers,type SubmissionEvent} from "@/features/exam-reliability/final-snapshot";
import type {Attempt,State,Sync} from "./models";
type Pending={body:Sync;serial:number};
const integer=(v:unknown,min=0,max=Number.MAX_SAFE_INTEGER)=>typeof v==="number"&&Number.isSafeInteger(v)&&v>=min&&v<=max;
const validState=(s:State)=>s&&integer(s.displayed_part,1,4)&&integer(s.audio_part,1,4)&&integer(s.current_question,1,40)&&Number.isFinite(s.playback_seconds)&&s.playback_seconds>=0&&s.playback_seconds<=86400&&Array.isArray(s.marked)&&s.marked.length<=40&&s.marked.every(n=>integer(n,1,40));
const validEvent=(e:SubmissionEvent)=>e&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(e.event_id)&&integer(e.expected_version);
type Final=SubmissionEvent&{state?:State};
interface RecordData {state:State;baseState:State;serial:number;savedSerial:number;pendingSerial?:number;frozen?:Record<string,string>;frozenState?:State}
interface Options {store?:DraftStore;send?:ReturnType<typeof api>;get?:()=>Promise<Attempt>}
export class ListeningDraft {
  readonly audioProgress:AudioProgress;
  private listeners=new Set<()=>void>();private timer?:ReturnType<typeof setTimeout>;private lease?:ReturnType<typeof setInterval>;
  private stopped=false;private serial=0;private savedSerial=0;private revision=0;private failures=0;private ready=false;
  private pending?:Pending;private submitBody?:Final;private rejectedBody?:Final;private frozen?:Record<string,string>;private frozenState?:State;
  private base:Attempt;private key:string;private flight?:Promise<void>;private writes=Promise.resolve();private store:DraftStore;private send:ReturnType<typeof api>;private getRemote:()=>Promise<Attempt>;
  snapshot:{answers:Record<string,string>;state:State;status:string;conflict:Attempt|null;submitting:boolean;storage:boolean;ready:boolean;localSaving:boolean;otherTab:boolean};
  constructor(public initial:Attempt,private uid:string,options:Options={}){
    this.base=structuredClone(initial);this.audioProgress=new AudioProgress(uid,initial.id,initial.exam?.exam_id||initial.id,initial.state.audio_part,initial.state.playback_seconds);
    this.key=`alua:listening:${uid}:${initial.id}:${initial.content_hash}`;
    this.store=options.store||browserDraftStore(uid,`listening:${initial.id}`,initial.content_hash,crypto.randomUUID());this.send=options.send||api(uid);this.getRemote=options.get||(()=>attempt(uid,initial.id));
    this.snapshot={answers:{...initial.answers},state:structuredClone(initial.state),status:"Saving on device…",conflict:null,submitting:false,storage:true,ready:false,localSaving:false,otherTab:false};
  }
  get=()=>this.snapshot;subscribe=(fn:()=>void)=>{this.listeners.add(fn);return()=>{this.listeners.delete(fn)}};
  private ids(){return this.initial.exam!.parts.flatMap(p=>p.groups.flatMap(g=>g.questions.map(q=>q.question_id)));}
  private publish(patch:Partial<typeof this.snapshot>){if(this.stopped)return;this.snapshot={...this.snapshot,...patch};this.listeners.forEach(fn=>fn());}
  private persist(){
    const listening:RecordData={state:structuredClone(this.snapshot.state),baseState:structuredClone(this.base.state),serial:this.serial,savedSerial:this.savedSerial,pendingSerial:this.pending?.serial,frozen:this.frozen,frozenState:this.frozenState};
    const value:Draft={key:JSON.stringify([this.uid,`listening:${this.initial.id}`,this.initial.content_hash]),uid:this.uid,attemptId:this.initial.id,hash:this.initial.content_hash,revision:++this.revision,modified:Date.now(),version:this.base.version,base:{...this.base.answers},answers:{...this.snapshot.answers},pending:this.pending?.body,submit:this.submitBody,rejectedSubmit:this.rejectedBody,finalizing:this.snapshot.submitting,listening};
    this.publish({localSaving:true});const task=this.writes.catch(()=>{}).then(()=>this.store.write(structuredClone(value)));this.writes=task;
    void task.then(()=>{if(this.revision===value.revision)this.publish({localSaving:false,storage:true,status:this.snapshot.conflict?"Conflicting answers · Review before Finish":this.snapshot.submitting?"Finishing…":this.rejectedBody?"Submit rejected · Answers retained; edit or retry Finish":this.serial>this.savedSerial?"Saved on device":"All changes saved"});},()=>this.publish({storage:false,localSaving:false,status:"Save failed · Retry device save"}));return task;
  }
  async initialize(){
    try{
      let acquired=await this.store.acquire();
      for(let retry=0;!acquired&&retry<17&&!this.stopped;retry++){await new Promise(r=>setTimeout(r,200));acquired=await this.store.acquire();}
      if(this.stopped){if(acquired)await this.store.release();return;}
      if(!acquired){this.publish({otherTab:true,status:"Open in another tab · Read only"});return;}
      let d=await this.store.read();
      if(!d){let raw:string|null=null;try{raw=localStorage.getItem(this.key);}catch{/* IndexedDB remains authoritative when localStorage is unavailable. */}if(raw){const old=JSON.parse(raw);if(old.base?.id!==this.initial.id||old.base?.content_hash!==this.initial.content_hash)throw Error("Unreadable legacy draft");d={uid:this.uid,attemptId:this.initial.id,hash:this.initial.content_hash,key:"",revision:old.serial||0,modified:0,version:old.base.version,base:old.base.answers,answers:old.answers,pending:old.pending?.body,submit:old.submitBody,finalizing:!!old.submitBody,listening:{state:old.state,baseState:old.base.state,serial:old.serial,savedSerial:old.savedSerial||0,pendingSerial:old.pending?.serial}};}}
      if(d){
        const ids=new Set(this.ids()),valid=(v:Record<string,string>)=>v&&typeof v==="object"&&!Array.isArray(v)&&Object.entries(v).length<=40&&Object.entries(v).every(([id,a])=>ids.has(id)&&typeof a==='string'&&a.length<=500);
        if(d.uid!==this.uid||d.attemptId!==this.initial.id||d.hash!==this.initial.content_hash||!integer(d.revision)||!valid(d.answers)||!valid(d.base)||!d.listening)throw Error("Unreadable draft retained");
        const l=d.listening as RecordData;if(!Number.isSafeInteger(l.serial)||!Number.isSafeInteger(l.savedSerial)||l.serial<l.savedSerial||l.savedSerial<0||!validState(l.state)||!validState(l.baseState)||!Number.isSafeInteger(d.version)||d.version<0)throw Error("Unreadable draft retained");this.base={...this.base,answers:d.base,state:l.baseState,version:d.version};this.serial=l.serial;this.savedSerial=l.savedSerial;this.revision=d.revision;
        if(d.pending&&(!validEvent(d.pending)||!valid(d.pending.answers)||!validState((d.pending as Sync).state)||!integer(l.pendingSerial)||l.pendingSerial!>l.serial||d.pending.expected_version!==d.version))throw Error("Unreadable outbox retained");
        if(d.submit&&(!validEvent(d.submit)||d.submit.answers&&(!valid(d.submit.answers)||!validState((d.submit as Final).state!)||!integer(d.submit.local_revision)||Object.keys(d.submit.answers).length!==ids.size||await answersChecksum(d.submit.answers)!==d.submit.answers_checksum)))throw Error("Unreadable submission retained");
        if(l.frozen&&(!valid(l.frozen)||Object.keys(l.frozen).length!==ids.size)||l.frozenState&&!validState(l.frozenState))throw Error("Unreadable final snapshot retained");
        this.pending=d.pending?{body:d.pending as Sync,serial:l.pendingSerial??0}:undefined;this.submitBody=d.submit as Final|undefined;this.rejectedBody=d.rejectedSubmit as Final|undefined;this.frozen=l.frozen;this.frozenState=l.frozenState;
        this.publish({answers:d.answers,state:l.state,submitting:!!d.finalizing});
        if(this.submitBody&&!this.submitBody.answers){
          // Legacy submit did not bind answers. Reconcile before upgrading.
          const remote=await this.getRemote();this.submitBody=undefined;this.frozen=canonicalAnswers(this.ids(),d.answers);this.frozenState=l.state;this.merge(remote);
        }
        if(!this.pending&&!this.submitBody)this.merge(this.initial);
      }
      this.ready=true;await this.persist();this.publish({ready:true,otherTab:false});
      this.lease=setInterval(()=>{void this.store.acquire().then(ok=>{if(!ok){this.ready=false;this.publish({otherTab:true,status:"Open in another tab · Read only"});clearTimeout(this.timer);}}).catch(()=>this.publish({storage:false,status:"Save failed · Retry device save"}));},1000);
      if(this.serial>this.savedSerial||this.pending||this.snapshot.submitting)this.schedule(0);
    }catch{this.publish({storage:false,status:"Save failed · Retry device save"});}
  }
  private edit(patch:Partial<typeof this.snapshot>){this.serial++;this.publish({...patch,status:"Saving on device…"});void this.persist().catch(()=>{});this.schedule(450);}
  changeAnswer(qid:string,value:string){if(!this.ready||!this.snapshot.storage||this.snapshot.submitting||this.snapshot.conflict||this.snapshot.otherTab)return;this.edit({answers:{...this.snapshot.answers,[qid]:value}});}
  changeState(patch:Partial<State>){if(!this.ready||!this.snapshot.storage||this.snapshot.submitting||this.snapshot.conflict||this.snapshot.otherTab)return;this.edit({state:{...this.snapshot.state,...patch}});}
  private schedule(ms:number){if(this.stopped||this.snapshot.conflict||this.snapshot.otherTab||this.failures>=5)return;clearTimeout(this.timer);this.timer=setTimeout(()=>{void this.flush().catch(()=>{});},ms);}
  private merge(remote:Attempt){
    if(remote.id!==this.initial.id||remote.content_hash!==this.initial.content_hash)throw Error("Attempt identity changed");
    const answers={...remote.answers};let conflict=remote.status==='submitted';
    for(const qid of new Set([...Object.keys(this.base.answers),...Object.keys(this.snapshot.answers)]))if((this.snapshot.answers[qid]??"")!==(this.base.answers[qid]??"")){
      if((remote.answers[qid]??"")!==(this.base.answers[qid]??"")&&(remote.answers[qid]??"")!==(this.snapshot.answers[qid]??""))conflict=true;
      answers[qid]=this.snapshot.answers[qid]??"";
    }
    if(this.frozen&&JSON.stringify(canonicalAnswers(this.ids(),answers))!==JSON.stringify(this.frozen))conflict=true;
    if(conflict){this.publish({answers,conflict:remote,status:"Conflicting answers · Review before Finish"});return;}
    this.base=remote;this.serial++;this.publish({answers});
  }
  resolve(local:boolean){const remote=this.snapshot.conflict;if(!remote||remote.status==='submitted')return;this.base=remote;this.pending=undefined;this.submitBody=undefined;this.frozen=undefined;this.serial++;this.publish({answers:local?this.snapshot.answers:{...remote.answers},conflict:null,submitting:false});void this.persist().then(()=>this.flush()).catch(()=>{});}
  flush=async():Promise<void>=>{
    clearTimeout(this.timer);
    if(this.flight)return this.flight;
    if(!this.ready||!this.snapshot.storage||this.snapshot.otherTab||this.snapshot.conflict||this.stopped)throw Error("Draft is not ready for safe saving");
    const flight=this.work();this.flight=flight;try{await flight;}finally{if(this.flight===flight)this.flight=undefined;this.publish({});}
  };
  private async work(){
    try{
      await this.writes;
      let conflicts=0;
      while(this.pending||this.serial>this.savedSerial){
        if(this.submitBody)break;
        this.pending??={body:{event_id:crypto.randomUUID(),expected_version:this.base.version,answers:{...this.snapshot.answers},state:structuredClone(this.snapshot.state)},serial:this.serial};
        await this.persist();const event=this.pending;this.publish({status:"Syncing…"});
        try{const saved=await this.send(`/listening/attempts/${this.initial.id}/sync`,undefined,{method:"POST",body:event.body}) as Attempt;
          if(saved.id!==this.initial.id||saved.version!==event.body.expected_version+1)throw Error("Invalid acknowledgement");
          this.base={...this.base,...saved};this.savedSerial=event.serial;this.pending=undefined;await this.persist();
        }catch(error){if(error instanceof ApiError&&error.status===409){this.pending=undefined;this.merge(await this.getRemote());await this.persist();if(this.snapshot.conflict||++conflicts>=3)throw error;}else throw error;}
      }
      if(this.snapshot.submitting){
        if(!this.submitBody){const answers=this.frozen||canonicalAnswers(this.ids(),this.snapshot.answers);this.submitBody={event_id:crypto.randomUUID(),expected_version:this.base.version,answers,answers_checksum:await answersChecksum(answers),local_revision:this.serial,state:this.frozenState||structuredClone(this.snapshot.state)};}
        await this.persist();const event=this.submitBody;
        if(!event.answers){throw Error("Legacy submission requires server reconciliation; draft retained");}
        this.publish({status:"Finishing…"});const remote=await this.getRemote();if(remote.id!==this.initial.id||remote.content_hash!==this.initial.content_hash)throw Error("Attempt identity changed");const confirmed=remote.status==="submitted";const ack=confirmed?remote:await this.send(`/listening/attempts/${this.initial.id}/submit`,undefined,{method:"POST",body:event}) as Attempt;
        if(ack.id!==this.initial.id||ack.content_hash!==this.initial.content_hash||ack.status!=="submitted"||(!confirmed&&ack.final_snapshot_accepted!==true)||ack.answers_checksum!==event.answers_checksum||await answersChecksum(canonicalAnswers(this.ids(),ack.answers))!==event.answers_checksum)throw Error("Final snapshot was not confirmed");
        this.base={...this.base,...ack};this.savedSerial=this.serial;this.submitBody=undefined;this.publish({submitting:false,status:"All changes saved"});await this.persist();
      }
      this.failures=0;this.publish({status:"All changes saved"});
    }catch(error){
      if(this.submitBody&&rejectedSubmit(error)){
        this.rejectedBody=this.submitBody;this.submitBody=undefined;this.frozen=undefined;this.frozenState=undefined;
        this.publish({submitting:false,status:"Submit rejected · Answers retained; edit or retry Finish"});await this.persist();throw error;
      }
      if(this.submitBody&&error instanceof ApiError&&error.status===409){const remote=await this.getRemote();this.submitBody=undefined;this.merge(remote);this.publish({submitting:false,status:"Conflict · Review final answers"});await this.persist();}
      else{this.failures++;this.publish({status:this.snapshot.submitting?"Submission not confirmed · Retry":this.snapshot.storage?"Offline — saved on device":"Save failed"});if(!this.snapshot.submitting)this.schedule(Math.min(16000,1000*2**this.failures));}
      throw error;
    }
  }
  async submit(){
    if(!this.ready||!this.snapshot.storage||this.snapshot.otherTab||this.snapshot.conflict)throw Error("Resolve device save or conflict before Finish");
    if(!this.snapshot.submitting){this.rejectedBody=undefined;this.frozen=canonicalAnswers(this.ids(),this.snapshot.answers);this.frozenState=structuredClone(this.snapshot.state);this.publish({submitting:true,status:"Saving on device…"});await this.persist();}
    if(this.flight)await this.flight;
    if(this.base.status!=='submitted')await this.flush();
    if(this.base.status!=='submitted')throw Error("Submission not confirmed");return this.base;
  }
  retryStorage=async()=>{if(!this.ready){await this.initialize();return;}await this.persist();await this.flush();};
  canReturnToTest=()=>this.snapshot.submitting&&!this.submitBody&&!this.flight&&this.base.status==='in_progress';
  returnToTest=async()=>{if(!this.canReturnToTest())return;try{const remote=await this.getRemote();if(remote.status==='submitted'){this.merge(remote);return;}this.frozen=undefined;this.merge(remote);this.publish({submitting:false});await this.persist();}catch{this.publish({status:"Submission not confirmed · Retry"});}};
  hasUnsaved=()=>this.snapshot.localSaving||!!this.pending||this.serial>this.savedSerial||this.snapshot.submitting;
  dispose(){this.stopped=true;clearTimeout(this.timer);clearInterval(this.lease);this.listeners.clear();void this.writes.catch(()=>{}).then(()=>this.store.release()).catch(()=>{});}
}
