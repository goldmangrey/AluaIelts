import { readFileSync } from "node:fs";
import type { Page } from "@playwright/test";
import type { Exam } from "../src/features/reading/exam/models";
import { allQuestions } from "../src/features/reading/exam/models";
export const fixtures: { exams: Exam[]; now: string; deadline: string; samples: Record<string,string> } = JSON.parse(readFileSync(process.env.ALUA_C_FIXTURES!, "utf8"));
export async function openExam(page: Page, id="cambridge-18-test-01") {
  const exam=fixtures.exams.find((e)=>e.id===id)!;
  const first=allQuestions(exam)[0]!;
  let version=7;
  let answers:Record<string,string>=first.answer_input_type==="text"?{[first.id]:"restored draft"}:{};
  const events: { event_id:string; expected_version:number; answers:Record<string,string> }[]=[];
  const replays=new Map();
  await page.route("**/reading-qa/save",async(route)=>{
    const event=route.request().postDataJSON();events.push(event);
    if(replays.has(event.event_id)){await route.fulfill({json:replays.get(event.event_id)});return;}
    if(event.expected_version!==version){await route.fulfill({status:409});return;}
    answers={...answers,...event.answers};version++;
    const ack={id:"11111111-2222-4333-8444-555555555555",exam_id:id,mode:"full_exam",status:"in_progress",version,content_hash:"fixture-hash",server_now:fixtures.now,deadline_at:fixtures.deadline,answers,state:{current_passage:1,checked_question_ids:[]},not_fully_proofread:true,mutation_applied:true};
    replays.set(event.event_id,ack);await route.fulfill({json:ack});
  });
  await page.goto(`/reading-qa/${id}`);
  await page.getByRole("button",{name:"All 40",exact:true}).waitFor();
  return {exam,events};
}
