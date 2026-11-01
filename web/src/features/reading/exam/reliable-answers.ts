import { ApiError } from "@/lib/api/client";
import type { Attempt } from "./models";
import type { SaveEvent, SaveAnswers } from "./answers";
import type { Draft, DraftStore, ViewDraft } from "./draft-storage";
import { validateDraft } from "./draft-validation";
import { eventId } from "./api";
export type Phase = "loading" | "in_progress" | "finalizing" | "submission_unknown" | "terminal";
export interface Conflict { id:string; local:string; server:string }
export interface ReliableSnapshot {
  answers: Record<string,string>; dirty:number; saving:boolean; error:unknown; terminal:boolean;
  phase:Phase; localSaving:boolean; localError:unknown; offline:boolean; conflicts:Conflict[]; otherTab:boolean;
  clock: { serverNow:string; deadline:string|null; revision:number }; view?:ViewDraft; version:number;
}
export interface ReliabilityOptions {
  store:DraftStore; uid:string; get:()=>Promise<Attempt>; save:SaveAnswers;
  submit:(event:{event_id:string;expected_version:number})=>Promise<Attempt>;
  tokenRefresh?:()=>Promise<unknown>; online?:()=>boolean; onUnauthorized?:()=>void;
}
/** Durable outbox; the server alone owns acceptance, time and scoring. */
export class ReliableAnswers {
  private state:ReliableSnapshot; private base:Record<string,string>; private pending?:SaveEvent;
  private submission?:{event_id:string;expected_version:number}; private revision=0; private listeners=new Set<()=>void>();
  private flight?:Promise<void>; private writes=Promise.resolve(); private debounce?:ReturnType<typeof setTimeout>;
  private retry?:ReturnType<typeof setTimeout>; private retries=0; private disposed=false; private mounted=0;
  private lease?:ReturnType<typeof setInterval>; private leased=false; private view?:ViewDraft;
  private terminalAttempt?:Attempt; private initialized=false;
  constructor(private attempt:Attempt, private options:ReliabilityOptions) {
    this.base={...attempt.answers};
    this.state={answers:{...attempt.answers},dirty:0,saving:false,error:null,terminal:attempt.status!=="in_progress",phase:"loading",localSaving:false,localError:null,offline:false,conflicts:[],otherTab:false,clock:{serverNow:attempt.server_now,deadline:attempt.deadline_at,revision:0},version:attempt.version};
  }
  snapshot=()=>this.state;
  subscribe=(fn:()=>void)=>{this.listeners.add(fn);return()=>{this.listeners.delete(fn)}};
  private publish(update:Partial<ReliableSnapshot>) {
    if(this.disposed)return;
    this.state={...this.state,...update};
    this.state.dirty=Object.keys(this.state.answers).filter(id=>(this.state.answers[id]??"")!==(this.base[id]??"")).length;
    this.listeners.forEach(fn=>fn());
  }
  private record():Draft {return {key:JSON.stringify([this.options.uid,this.attempt.id,this.attempt.content_hash]),uid:this.options.uid,attemptId:this.attempt.id,hash:this.attempt.content_hash,revision:++this.revision,modified:Date.now(),version:this.state.version,base:{...this.base},answers:{...this.state.answers},pending:this.pending?structuredClone(this.pending):undefined,submit:this.submission,finalizing:this.state.phase==="finalizing"||this.state.phase==="submission_unknown",conflicts:this.state.conflicts,view:this.view}}
  private persist():Promise<void> {
    if(!this.leased || this.disposed)return Promise.reject(new Error("This tab cannot write the local draft."));
    const value=this.record();this.publish({localSaving:true});
    const task=this.writes.catch(()=>{}).then(()=>this.options.store.write(value));
    this.writes=task;
    void task.then(()=>{if(this.revision===value.revision)this.publish({localSaving:false,localError:null})},error=>this.publish({localSaving:false,localError:error}));
    return task;
  }
  async initialize() {
    try {
      this.leased=await this.options.store.acquire();
      for(let retry=0;!this.leased&&retry<17&&!this.disposed;retry++){await new Promise(r=>setTimeout(r,200));this.leased=await this.options.store.acquire()}
      if(!this.leased){this.publish({phase:"in_progress",otherTab:true});return}
      const draft=await this.options.store.read();
      if(this.disposed){await this.options.store.release();return}
      if(draft && draft.uid===this.options.uid && draft.attemptId===this.attempt.id && draft.hash===this.attempt.content_hash) {
        validateDraft(draft,this.attempt,this.options.uid);
        this.base=draft.base;this.pending=draft.pending;this.submission=draft.submit;this.view=draft.view;this.revision=draft.revision;
        this.publish({answers:draft.answers,version:draft.version,view:draft.view,conflicts:draft.conflicts??[],phase:draft.finalizing?"submission_unknown":"in_progress"});
      } else this.publish({phase:"in_progress"});
      if(this.attempt.status!=="in_progress")this.acceptTerminal(this.attempt);
      else if(!this.pending&&!this.submission)this.merge(this.attempt);
      this.initialized=true;
      await this.persist();
      this.lease=setInterval(()=>void this.renew(),1000);
      if(!this.state.terminal && !this.state.conflicts.length&&(this.state.dirty||this.pending||this.submission||this.state.phase!=="in_progress"))void this.flush();
    }catch(error){this.publish({phase:"in_progress",localError:error});}
  }
  private async renew() {if(this.disposed||this.state.otherTab)return;try {const ok=await this.options.store.acquire();if(!ok){this.leased=false;clearInterval(this.lease);this.publish({otherTab:true});clearTimeout(this.debounce);clearTimeout(this.retry)}}catch(error){this.publish({localError:error})}}
  retryStorage=async()=>{try{if(!this.leased||!this.initialized){await this.initialize();return}await this.persist();await this.flush()}catch(error){this.publish({localError:error})}};
  change=(changes:Record<string,string>)=>{
    if(!this.initialized||this.state.localError||this.disposed||this.state.terminal||this.state.otherTab||this.state.phase!=="in_progress"||this.state.conflicts.length)return;
    this.publish({answers:{...this.state.answers,...changes}});
    void this.persist().catch(()=>{});
    clearTimeout(this.debounce);this.debounce=setTimeout(()=>void this.flush(),600);
  };
  saveView=(view:ViewDraft)=>{if(!this.initialized||this.state.localError||this.state.otherTab||this.state.phase==="loading")return;this.view=view;void this.persist().catch(()=>{})};
  private acceptTerminal(server:Attempt) {
    if(server.id!==this.attempt.id||server.exam_id!==this.attempt.exam_id||server.content_hash!==this.attempt.content_hash)throw new ApiError(502,"unexpected_reading_response");
    this.terminalAttempt=server;
    this.base={...server.answers};
    this.publish({terminal:true,phase:"terminal",version:server.version,clock:{serverNow:server.server_now,deadline:server.deadline_at,revision:this.state.clock.revision+1},saving:false});
    // Preserve unaccepted local answers for inspection; never restore them over a result.
  }
  completed=()=>this.terminalAttempt;
  private merge(server:Attempt) {
    if(server.id!==this.attempt.id||server.content_hash!==this.attempt.content_hash)throw new ApiError(409,"reading_content_changed");
    if(server.status!=="in_progress"){this.acceptTerminal(server);return}
    const merged={...server.answers};const conflicts:Conflict[]=[];
    const ids=new Set([...Object.keys(this.base),...Object.keys(this.state.answers),...Object.keys(server.answers)]);
    const conflicted=new Set<string>();
    for(const id of ids){const base=this.base[id]??"",local=this.state.answers[id]??"",remote=server.answers[id]??"";
      if(local!==base){merged[id]=local;if((remote!==base||this.state.conflicts.some(c=>c.id===id))&&local!==remote)conflicted.add(id)}
    }
    // Unordered multi-answer groups are one semantic answer, not independent positions.
    for(const g of this.attempt.exam?.passages.flatMap(p=>p.question_groups)??[])if(g.type==="multiple_choice_multiple"){
      const changedLocal=g.questions.some(q=>(this.state.answers[q.id]??"")!==(this.base[q.id]??""));
      const changedRemote=g.questions.some(q=>(server.answers[q.id]??"")!==(this.base[q.id]??""));
      if((changedLocal&&changedRemote||g.questions.some(q=>this.state.conflicts.some(c=>c.id===q.id)))&&g.questions.some(q=>(this.state.answers[q.id]??"")!==(server.answers[q.id]??"")))g.questions.forEach(q=>conflicted.add(q.id));
    }
    for(const id of conflicted){merged[id]=this.state.answers[id]??"";conflicts.push({id,local:this.state.answers[id]??"",server:server.answers[id]??""})}
    this.base={...server.answers};this.attempt={...this.attempt,...server,exam:this.attempt.exam};
    this.publish({answers:merged,version:server.version,conflicts,clock:{serverNow:server.server_now,deadline:server.deadline_at,revision:this.state.clock.revision+1}});
  }
  resolve=(choices:Record<string,"local"|"server">)=>{
    if(this.state.conflicts.some(c=>!choices[c.id]))return;
    const answers={...this.state.answers};for(const c of this.state.conflicts)answers[c.id]=choices[c.id]==="local"?c.local:c.server;
    this.publish({answers,conflicts:[],error:null});void this.persist().then(()=>this.flush()).catch(()=>{});
  };
  private schedule(error:unknown) {
    if(this.disposed||this.state.terminal||this.state.otherTab)return;
    const transient=!(error instanceof ApiError)||error.status===0||error.status>=500||error.status===429;
    if(transient&&this.retries<5){clearTimeout(this.retry);this.retry=setTimeout(()=>void this.flush(),Math.min(16000,1000*2**this.retries++));}
  }
  flush=async():Promise<void>=>{
    clearTimeout(this.debounce);clearTimeout(this.retry);
    if(this.flight){const previous=this.flight;await previous;if(this.flight===previous)this.flight=undefined;if(!this.state.error&&!this.state.terminal)return this.flush();return}
    if(this.disposed||!this.leased||this.state.otherTab||this.state.phase==="loading"||this.state.terminal||this.state.conflicts.length)return;
    this.flight=(async()=>{
      try{await this.writes}catch(error){this.publish({localError:error,error});return}
      if(this.options.online?.()===false){this.publish({offline:true,error:new ApiError(0,"network_error")});return}
      await this.work();
    })();await this.flight;this.flight=undefined;
  };
  private async send<T>(fn:()=>Promise<T>):Promise<T> {
    try{return await fn()}catch(error){if(error instanceof ApiError&&error.status===401&&this.options.tokenRefresh){await this.options.tokenRefresh();return fn()}throw error}
  }
  private async work() {
    this.publish({saving:true,error:null,offline:false});
    try {
      let conflicts=0;
      while(!this.disposed&&!this.state.terminal&&!this.state.conflicts.length) {
        if(this.submission){await this.persist();const ack=await this.send(()=>this.options.submit(this.submission!));if(ack.status==="in_progress")throw new ApiError(502,"unexpected_reading_response");this.acceptTerminal(ack);await this.persist();break}
        if(!this.state.dirty&&!this.pending)break;
        this.pending??={event_id:eventId(),expected_version:this.state.version,answers:Object.fromEntries(Object.entries(this.state.answers).filter(([id,v])=>v!==(this.base[id]??"")))};
        // Never transmit a mutation before its exact replay data commits locally.
        await this.persist();const event=this.pending;
        try {
          const ack=await this.send(()=>this.options.save(event));
          if(ack.id!==this.attempt.id)throw new ApiError(502,"unexpected_reading_response");
          if(ack.status!=="in_progress"){this.acceptTerminal(ack);await this.persist();break}
          if(ack.mutation_applied!==true||ack.version!==event.expected_version+1)throw new ApiError(409,"reading_version_conflict");
          this.base={...this.base,...event.answers};this.pending=undefined;this.publish({version:ack.version});
          await this.persist();
          // Replayed acknowledgements may predate subsequent writes on another device.
          if(this.options.get)this.merge(await this.options.get());
          await this.persist();
        }catch(error){
          if(error instanceof ApiError&&error.status===409&&error.code==="reading_version_conflict"){
            // 409 explicitly rejects this event; a fresh CAS event is allowed after merge.
            const server=await this.options.get();this.pending=undefined;this.merge(server);await this.persist();if(this.state.conflicts.length||this.state.terminal)break;if(++conflicts>=3)throw new ApiError(409,"reading_version_conflict");continue;
          }
          throw error;
        }
      }
      if(!this.state.terminal&&!this.state.conflicts.length&&this.state.phase!=="in_progress") {
        this.submission={event_id:eventId(),expected_version:this.state.version};await this.persist();
        const ack=await this.send(()=>this.options.submit(this.submission!));if(ack.status==="in_progress")throw new ApiError(502,"unexpected_reading_response");this.acceptTerminal(ack);await this.persist();
      }
      this.retries=0;this.publish({saving:false});
    }catch(error){
      if(this.submission && error instanceof ApiError && error.code==="reading_version_conflict") {
        try{this.submission=undefined;this.merge(await this.options.get());await this.persist();this.publish({saving:false,error:null});this.retry=setTimeout(()=>void this.flush(),0);return}catch(next){error=next}
      }
      if(error instanceof ApiError&&error.status===401)this.options.onUnauthorized?.();
      this.publish({saving:false,error,phase:this.submission?"submission_unknown":this.state.phase});this.schedule(error);
    }
  }
  canReturnToTest=()=>!this.submission&&!this.flight&&this.state.phase==="finalizing";
  returnToTest=()=>{if(!this.canReturnToTest())return;this.publish({phase:"in_progress",error:null});void this.persist().catch(()=>{})};
  finish=async()=>{
    if(this.state.phase!=="in_progress"||this.state.terminal||this.state.otherTab||this.state.conflicts.length)return;
    this.publish({phase:"finalizing"});
    try{await this.persist();await this.flush()}catch(error){this.publish({error,localError:error})}
  };
  refresh=async()=>{
    if(this.flight){await this.flight;return}
    if(this.disposed||this.state.otherTab||this.state.phase==="loading")return;
    if(this.options.online?.()===false){
      try{await this.writes;this.publish({offline:true,error:new ApiError(0,"network_error")})}catch(error){this.publish({localError:error})}
      return;
    }
    // A pending mutation must be replayed before rebasing its expected_version.
    if(this.pending||this.submission){await this.flush();return}
    this.flight=(async()=>{
      try{this.merge(await this.options.get());this.publish({error:null,offline:false});await this.persist()}
      catch(error){if(error instanceof ApiError&&error.status===401)this.options.onUnauthorized?.();this.publish({error,offline:this.options.online?.()===false})}
    })();
    await this.flight;this.flight=undefined;
    if((this.state.dirty||this.state.phase==="finalizing"||this.state.phase==="submission_unknown")&&!this.state.conflicts.length&&!this.state.terminal)void this.flush();
  };
  suspend=()=>{void this.writes.catch(()=>{}).then(()=>this.options.store.release()).catch(()=>{})};
  resume=async()=>{await this.renew();if(this.leased)await this.refresh()};
  mount(){this.mounted++}
  unmount(){this.mounted--;queueMicrotask(()=>{if(!this.mounted)this.dispose()})}
  dispose(){if(this.disposed)return;this.disposed=true;clearTimeout(this.debounce);clearTimeout(this.retry);clearInterval(this.lease);this.listeners.clear();void this.writes.catch(()=>{}).then(()=>this.options.store.release()).catch(()=>{})}
}
