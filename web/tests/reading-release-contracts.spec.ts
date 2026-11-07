import type {SubmissionEvent} from "../src/features/exam-reliability/final-snapshot";
import {test,expect} from "@playwright/test";
import {ReliableAnswers} from "../src/features/reading/exam/reliable-answers";
import type {Draft,DraftStore} from "../src/features/reading/exam/draft-storage";
import type {Attempt} from "../src/features/reading/exam/models";
import {ApiError} from "../src/lib/api/client";
import {fixtures} from "./reading-fixture";
import type {SaveEvent} from "../src/features/reading/exam/answers";
import {parseResult} from "../src/features/reading/exam/results";
function environment(){
 const exam=fixtures.exams.find(e=>e.id==="cambridge-18-test-01")!;
 const q=exam.passages.flatMap(p=>p.question_groups.flatMap(g=>g.questions));
 let server:Attempt={id:"11111111-2222-4333-8444-555555555555",exam_id:exam.id,exam,content_hash:"hash",status:"in_progress",mode:"full_exam",version:0,server_now:fixtures.now,deadline_at:fixtures.deadline,state:{current_passage:1,checked_question_ids:[]},not_fully_proofread:true,answers:{}};
 let draft:Draft|undefined,online=true,failLocal=false,unknown=false,unknownSubmit=false;
 const events:SaveEvent[]=[],submits:{event_id:string;expected_version:number}[]=[],replays=new Map<string,Attempt>();
 const store:DraftStore={acquire:async()=>true,release:async()=>{},read:async()=>structuredClone(draft),write:async v=>{if(failLocal)throw Error("quota");draft=structuredClone(v)}};
 const options={uid:"A",store,online:()=>online,get:async()=>structuredClone(server),save:async(e:SaveEvent)=>{
   expect(draft?.pending).toEqual(e);events.push(structuredClone(e));
   if(replays.has(e.event_id))return structuredClone(replays.get(e.event_id)!);
   if(e.expected_version!==server.version)throw new ApiError(409,"reading_version_conflict");
   if(server.status!=="in_progress")return structuredClone(server);
   server={...server,version:server.version+1,answers:{...server.answers,...e.answers},mutation_applied:true};replays.set(e.event_id,structuredClone(server));
   if(unknown)throw new ApiError(0,"timeout");return structuredClone(server);
 },submit:async(e:SubmissionEvent)=>{
   expect(draft?.submit).toEqual(e);submits.push(e);
   if(replays.has(e.event_id))return structuredClone(replays.get(e.event_id)!);
   if(e.expected_version!==server.version)throw new ApiError(409,"reading_version_conflict");
   server={...server,status:"submitted",version:server.version+1,answers:e.answers||server.answers,answers_checksum:e.answers_checksum,final_snapshot_accepted:true};replays.set(e.event_id,structuredClone(server));
   if(unknownSubmit)throw new ApiError(0,"timeout");return structuredClone(server);
 }};
 return {q,options,events,submits,session:()=>new ReliableAnswers(structuredClone(server),options),server:()=>server,setServer:(a:Partial<Attempt>)=>{server={...server,...a}},draft:()=>draft,offline:(v:boolean)=>{online=!v},failLocal:()=>{failLocal=true},unknown:(v:boolean)=>{unknown=v},unknownSubmit:(v:boolean)=>{unknownSubmit=v}};
}

test("durable draft and exact outbox survive unknown save + reopen without reverting later typing",async()=>{
 const e=environment();let s=e.session();try{
 await s.initialize();e.unknown(true);s.change({[e.q[0]!.id]:"a"});await s.flush();
 s.change({[e.q[0]!.id]:"ab"});await new Promise(r=>setTimeout(r,0));expect(e.draft()!.answers[e.q[0]!.id]).toBe("ab");s.dispose();
 e.unknown(false);s=e.session();await s.initialize();await s.flush();expect(e.events[1]).toEqual(e.events[0]);
 expect(e.server().answers[e.q[0]!.id]).toBe("ab");expect(s.snapshot().dirty).toBe(0);
 }finally{s.dispose()}
});
test("offline edits persist and automatically flush when explicitly reconnected",async()=>{
 const e=environment(),s=e.session();try{await s.initialize();e.offline(true);s.change({[e.q[0]!.id]:"local"});await s.flush();
 expect(s.snapshot().offline).toBe(true);expect(e.events).toHaveLength(0);expect(e.draft()!.answers[e.q[0]!.id]).toBe("local");
 e.offline(false);await s.refresh();await s.flush();expect(e.server().answers[e.q[0]!.id]).toBe("local");expect(s.snapshot().dirty).toBe(0);
 }finally{s.dispose()}
});
test("three-way reconciliation merges independent answers and preserves both incompatible versions",async()=>{
 const e=environment(),s=e.session();try{await s.initialize();s.change({[e.q[0]!.id]:"mine"});
 e.setServer({answers:{[e.q[1]!.id]:"theirs"},version:1});await s.flush();expect(s.snapshot().answers[e.q[1]!.id]).toBe("theirs");expect(e.server().answers[e.q[0]!.id]).toBe("mine");
 s.change({[e.q[0]!.id]:"local revision"});e.setServer({answers:{...e.server().answers,[e.q[0]!.id]:"remote revision"},version:3});await s.flush();
 expect(s.snapshot().conflicts).toEqual([{id:e.q[0]!.id,local:"local revision",server:"remote revision"}]);expect(e.draft()!.answers[e.q[0]!.id]).toBe("local revision");
 s.resolve({[e.q[0]!.id]:"server"});await s.flush();expect(s.snapshot().answers[e.q[0]!.id]).toBe("remote revision");
 }finally{s.dispose()}
});
test("local quota failure prevents transmitting an unreplayable event",async()=>{
 const e=environment(),s=e.session();try{await s.initialize();e.failLocal();s.change({[e.q[0]!.id]:"safe"});await s.flush();expect(e.events).toHaveLength(0);expect(s.snapshot().localError).toBeTruthy();expect(s.snapshot().dirty).toBe(1)}finally{s.dispose()}
});
test("finish drains answers, persists one submit UUID, handles unknown outcome across refresh",async()=>{
 const e=environment();let s=e.session();try{await s.initialize();s.change({[e.q[0]!.id]:"final"});e.unknownSubmit(true);await s.finish();
 expect(e.server().answers[e.q[0]!.id]).toBe("final");expect(s.snapshot().phase).toBe("submission_unknown");expect(e.submits).toHaveLength(1);expect(e.draft()!.submit).toEqual(e.submits[0]);
 s.change({[e.q[0]!.id]:"late"});expect(s.snapshot().answers[e.q[0]!.id]).toBe("final");s.dispose();
 s=e.session();await s.initialize();expect(s.snapshot().phase).toBe("terminal");expect(e.submits).toHaveLength(1);
 }finally{s.dispose()}
});
test("expiry preserves rejected local draft without false Saved or late submit",async()=>{
 const e=environment(),s=e.session();try{await s.initialize();s.change({[e.q[0]!.id]:"too late"});e.setServer({status:"expired",version:1});await s.flush();expect(s.snapshot().terminal).toBe(true);expect(s.snapshot().dirty).toBe(1);expect(e.draft()!.answers[e.q[0]!.id]).toBe("too late");expect(e.submits).toHaveLength(0)}finally{s.dispose()}
});
test("401 refresh retries the identical event and never changes identity",async()=>{
 const e=environment();let calls=0,refresh=0;const send=e.options.save;
 const s=new ReliableAnswers(e.server(),{...e.options,tokenRefresh:async()=>{refresh++},save:async event=>{calls++;if(calls===1)throw new ApiError(401,"session_expired");return send(event)}});
 try{await s.initialize();s.change({[e.q[0]!.id]:"answer"});await s.flush();expect(refresh).toBe(1);expect(s.snapshot().dirty).toBe(0);expect(e.events).toHaveLength(1)}finally{s.dispose()}
});
test("result parser and submission reject wrong ownership/content acknowledgements",async()=>{
 const e=environment();expect(()=>parseResult({},e.server())).toThrow();
 e.setServer({status:"submitted"});expect(()=>parseResult({attempt_id:"other"},e.server())).toThrow();
 const other=environment();const s=new ReliableAnswers(other.server(),{...other.options,submit:async()=>({...other.server(),status:"submitted",id:"22222222-2222-4333-8444-555555555555"})});
 try{await s.initialize();await s.finish();expect(s.snapshot().terminal).toBe(false);expect(s.snapshot().phase).toBe("submission_unknown")}finally{s.dispose()}
});

test("unresolved conflicts survive a refresh and cannot silently auto-select the local answer",async()=>{
 const e=environment();let s=e.session();try{await s.initialize();s.change({[e.q[0]!.id]:"local"});e.setServer({answers:{[e.q[0]!.id]:"remote"},version:1});await s.flush();expect(s.snapshot().conflicts).toHaveLength(1);s.dispose();
 s=e.session();await s.initialize();await s.flush();expect(s.snapshot().conflicts).toEqual([{id:e.q[0]!.id,local:"local",server:"remote"}]);expect(e.server().answers[e.q[0]!.id]).toBe("remote");
 }finally{s.dispose()}
});

test("monotonic/server clock handles skew, suspension, backward and forward local clock changes",async()=>{
 const {elapsedSeconds,remainingSeconds}=await import("../src/features/reading/exam/clock");
 const now="2026-11-01T00:00:00Z",deadline="2026-11-01T01:00:00Z";
 expect(remainingSeconds(deadline,now,0)).toBe(3600);
 expect(elapsedSeconds(100,1000000,1100,1001000)).toBe(1);
 expect(elapsedSeconds(100,1000000,1100,1600000)).toBe(600);
 expect(elapsedSeconds(100,1000000,1100,0)).toBe(1);
 expect(remainingSeconds(deadline,now,elapsedSeconds(0,0,1,7200000))).toBe(0);
 expect(remainingSeconds(deadline,"2026-11-01T00:54:00Z",0)).toBe(360);
});

test("a rejected refreshed session retains the exact durable draft for reauthentication",async()=>{
 const e=environment();let refresh=0,rejected=0;const events:SaveEvent[]=[];
 const s=new ReliableAnswers(e.server(),{...e.options,tokenRefresh:async()=>{refresh++},onUnauthorized:()=>{rejected++},save:async event=>{events.push(event);throw new ApiError(401,"session_expired")}});
 try{await s.initialize();s.change({[e.q[0]!.id]:"keep me"});await s.flush();expect(refresh).toBe(1);expect(rejected).toBe(1);expect(events[0]).toEqual(events[1]);expect(e.draft()?.answers[e.q[0]!.id]).toBe("keep me");expect(s.snapshot().dirty).toBe(1)}finally{s.dispose()}
});

test("corrupted local drafts are retained without overwrite or network mutation",async()=>{
 const e=environment(),seed=e.session();await seed.initialize();const corrupt=structuredClone(e.draft()!);seed.dispose();corrupt.answers={foreign_question:"private draft"};let writes=0;
 const s=new ReliableAnswers(e.server(),{...e.options,store:{...e.options.store,read:async()=>corrupt,write:async()=>{writes++}}});
 try{await s.initialize();expect(s.snapshot().localError).toBeTruthy();s.change({[e.q[0]!.id]:"overwrite"});await s.flush();expect(writes).toBe(0);expect(e.events).toHaveLength(0);expect(corrupt.answers.foreign_question).toBe("private draft")}finally{s.dispose()}
});
