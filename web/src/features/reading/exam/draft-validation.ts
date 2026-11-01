import type { Attempt } from "./models";
import { allQuestions } from "./models";
import type { Draft } from "./draft-storage";
/** Local persistence is versioned/untrusted input too. Never overwrite an unreadable draft. */
export function validateDraft(value:Draft,attempt:Attempt,uid:string) {
 const fail=()=>{throw new Error("The saved draft is unreadable. It has been retained; keep this page open and contact support.")};
 const integer=(n:unknown,max=Number.MAX_SAFE_INTEGER)=>typeof n==="number"&&Number.isSafeInteger(n)&&n>=0&&n<=max;
 const ids=new Set(allQuestions(attempt.exam!).map(q=>q.id));
 const answers=(v:unknown)=>!!v&&typeof v==="object"&&!Array.isArray(v)&&Object.keys(v).length<=40&&Object.entries(v).every(([id,s])=>ids.has(id)&&typeof s==="string"&&s.length<=500);
 const event=(v:{event_id:string;expected_version:number})=>/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(v.event_id)&&integer(v.expected_version);
 if(value.uid!==uid||value.attemptId!==attempt.id||value.hash!==attempt.content_hash||!integer(value.version)||!integer(value.revision)||!answers(value.base)||!answers(value.answers))fail();
 if(value.pending&&(!event(value.pending)||!answers(value.pending.answers)||!Object.keys(value.pending.answers).length))fail();
 if(value.submit&&!event(value.submit))fail();
 if(value.conflicts&&(!Array.isArray(value.conflicts)||value.conflicts.length>40||value.conflicts.some(c=>!ids.has(c.id)||typeof c.local!=="string"||typeof c.server!=="string")))fail();
 const view=value.view;if(!view)return;
 const passages=attempt.exam!.passages;
 if(!passages.some(p=>p.number===view.passage)||typeof view.size!=="number"||view.size<14||view.size>22||typeof view.split!=="number"||view.split<40||view.split>60||!["passage","questions"].includes(view.mobile)||!Array.isArray(view.review)||view.review.length>40||view.review.some(id=>!ids.has(id))||!Array.isArray(view.views)||view.views.length>3||!Array.isArray(view.highlights)||view.highlights.length>300)fail();
 for(const [number,scroll] of view.views)if(!passages.some(p=>p.number===number&&p.id===scroll.passageId)||!integer(Math.floor(scroll.textScrollTop),10000000)||!integer(Math.floor(scroll.questionsScrollTop),10000000)||scroll.lastFocusedQuestionId!==null&&!ids.has(scroll.lastFocusedQuestionId))fail();
 for(const h of view.highlights){const p=passages.find(p=>p.id===h.passageId);const block=p?.content[h.block];if(!block||block.type!=="paragraph"||!integer(h.block)||!integer(h.start)||!integer(h.end)||h.start>=h.end||block.text.slice(h.start,h.end)!==h.quote)fail()}
}
