import {readFileSync} from "node:fs";
import type {BrowserContext} from "@playwright/test";
import type {Attempt,Exam} from "../src/features/reading/exam/models";
import type {ReadingResult} from "../src/features/reading/exam/results";
export const data=JSON.parse(readFileSync(process.env.ALUA_C_FIXTURES!,"utf8")) as {exams:Exam[];release_hash:string;assets:Record<string,string>;release_results:{answers:Record<string,string>;result:ReadingResult}[]};
export const attemptId="11111111-2222-4333-8444-555555555555";
export const exam=data.exams.find(e=>e.id==="cambridge-18-test-01")!;
export async function releaseBackend(context:BrowserContext,{existing=true,seconds=3600}={}) {
 let created=existing,deadline=Date.now()+seconds*1000,fail=false,unknownSave=false,unknownSubmit=false;
 let a:Attempt={id:attemptId,exam_id:exam.id,mode:"full_exam",status:"in_progress",version:0,content_hash:data.release_hash,server_now:new Date().toISOString(),deadline_at:new Date(deadline).toISOString(),answers:{},state:{current_passage:1,checked_question_ids:[]},not_fully_proofread:true,exam,started_at:new Date(Date.now()-120000).toISOString(),submitted_at:null};
 const events:{path:string;body:Record<string,unknown>}[]=[],replays=new Map<string,Attempt>();
 function view(){if(a.status==="in_progress"&&Date.now()>=deadline){a={...a,status:"expired",version:a.version+1,submitted_at:a.deadline_at}}return {...structuredClone(a),server_now:new Date().toISOString()}}
 await context.route("**/api/alua/**",async route=>{
   const request=route.request(),path=new URL(request.url()).pathname.replace("/api/alua","");
   const error=async(status:number,code:string)=>route.fulfill({status,json:{error:{code}}});
   if(request.headers().authorization!=="Bearer fixture-A"){await error(404,"reading_attempt_not_found");return}
   if(path==="/reading/books"){await route.fulfill({json:{dataset_version:"1",items:[{book_number:18,exams:[{exam_id:exam.id,source_book:18,source_test_number:1,test_ordinal:1,enabled_for_private_practice:true,content_status:"needs_review",not_fully_proofread:true,question_count:40,passage_count:3,in_progress_attempt_ids:created&&view().status==="in_progress"?[attemptId]:[]}]}]}});return}
   if(path.startsWith("/reading/assets/")){const id=decodeURIComponent(path.split("/").at(-1)!);await route.fulfill({path:data.assets[id],contentType:"image/png"});return}
   if(path===`/reading/attempts/${attemptId}/result`){if(view().status==="in_progress"){await error(409,"reading_result_unavailable");return}
     const sample=data.release_results.find(r=>Object.keys({...r.answers,...a.answers}).every(q=>(r.answers[q]??"")===(a.answers[q]??"")));
     if(!sample)throw Error("No real backend-generated result fixture for these answers");
     await route.fulfill({json:{...sample.result,attempt_id:attemptId,completion_reason:a.status==="expired"?"deadline":"submitted"}});return;
   }
   if(path==="/reading/attempts"&&request.method()==="GET"){const history:Partial<Attempt>=view();delete history.answers;delete history.state;delete history.exam;const offset=Number(new URL(request.url()).searchParams.get("offset"));await route.fulfill({json:{items:created&&!offset?[{...history,raw_score:a.status==="in_progress"?null:0,estimated_band:null}]:[],limit:20,offset}});return}
   if(path===`/reading/attempts/${attemptId}`&&request.method()==="GET"){await route.fulfill({json:view()});return}
   if(request.method()==="POST"){
     const body=request.postDataJSON();events.push({path,body});
     if(replays.has(body.event_id)){if(path.endsWith("/submit")&&unknownSubmit){await error(503,"unknown_submit");return}await route.fulfill({json:replays.get(body.event_id)});return}
     if(path==="/reading/attempts"){if(!body.reuse_active)throw Error("Missing safety flag");created=true;replays.set(body.event_id,view());await route.fulfill({status:201,json:view()});return}
     if(fail){await error(503,"temporary_unavailable");return}
     view();if(a.status!=="in_progress"){await route.fulfill({json:{...view(),mutation_applied:false}});return}
     if(body.expected_version!==a.version){await error(409,"reading_version_conflict");return}
     if(path.endsWith("/sync")){a={...a,answers:{...a.answers,...body.answers},version:a.version+1};replays.set(body.event_id,{...view(),mutation_applied:true});if(unknownSave){await route.abort("failed");return}await route.fulfill({json:{...view(),mutation_applied:true}});return}
     if(path.endsWith("/submit")){a={...a,status:"submitted",version:a.version+1,submitted_at:new Date().toISOString()};replays.set(body.event_id,view());if(unknownSubmit){await error(503,"unknown_submit");return}await route.fulfill({json:view()});return}
   }
   await error(404,"missing_fixture_route");
 });
 return {events,server:()=>a,fail:(v:boolean)=>{fail=v},unknownSave:(v:boolean)=>{unknownSave=v},unknownSubmit:(v:boolean)=>{unknownSubmit=v},remote:(answers:Record<string,string>)=>{a={...a,answers:{...a.answers,...answers},version:a.version+1}},expire:()=>{deadline=Date.now()-1;a.deadline_at=new Date(deadline).toISOString()}};
}
