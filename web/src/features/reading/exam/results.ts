import { ApiError } from "@/lib/api/client";
import type { Attempt } from "./models";
import { allQuestions } from "./models";
export interface ResultPosition { question_id:string; number:number; user_answer:string; correct_answer:string; accepted_answers:string[]; is_correct:boolean; unanswered:boolean; passage_number:number; unordered_group?:boolean }
export interface ReadingResult { attempt_id:string; exam_id:string; content_hash:string; raw_score:number; total_questions:number; estimated_band:number|null; elapsed_seconds:number; completion_reason:"deadline"|"submitted"; positions:ResultPosition[] }
export interface HistoryItem {id:string;exam_id:string;status:Attempt["status"];started_at:string;submitted_at:string|null;raw_score:number|null;estimated_band:number|null;mode:Attempt["mode"]}
function fail():never{throw new ApiError(502,"unexpected_reading_response")}
function object(v:unknown):Record<string,unknown>{if(!v||typeof v!=="object"||Array.isArray(v))fail();return v as Record<string,unknown>}
function text(v:unknown){if(typeof v!=="string")fail();return v}
function number(v:unknown,max=100000){if(typeof v!=="number"||!Number.isFinite(v)||v<0||v>max)fail();return v}
function date(v:unknown){const s=text(v);if(!Number.isFinite(Date.parse(s)))fail();return s}
export function parseResult(value:unknown,attempt:Attempt):ReadingResult {
  if(attempt.status==="in_progress"||!attempt.exam)fail();
  const o=object(value);
  if(o.attempt_id!==attempt.id||o.exam_id!==attempt.exam_id||o.content_hash!==attempt.content_hash||!Array.isArray(o.positions))fail();
  const positions=o.positions.map(value=>{
    const p=object(value);if(typeof p.is_correct!=="boolean"||typeof p.unanswered!=="boolean"||!Array.isArray(p.accepted_answers))fail();
    return {question_id:text(p.question_id),number:number(p.number,40),user_answer:text(p.user_answer),correct_answer:text(p.correct_answer),accepted_answers:p.accepted_answers.map(text),is_correct:p.is_correct,unanswered:p.unanswered,passage_number:number(p.passage_number,3),unordered_group:!!p.grading_group&&object(p.grading_group).mode==="unordered_unique"};
  });
  const qs=allQuestions(attempt.exam);
  if(positions.length!==qs.length||new Set(positions.map(p=>p.question_id)).size!==qs.length||positions.some(p=>!qs.some(q=>q.id===p.question_id&&q.number===p.number)))fail();
  const total=number(o.total_questions,40),score=number(o.raw_score,total);
  if(!Number.isInteger(score)||total!==positions.length||positions.filter(p=>p.is_correct).length!==score)fail();
  if(o.completion_reason!=="deadline"&&o.completion_reason!=="submitted")fail();
  return {attempt_id:attempt.id,exam_id:attempt.exam_id,content_hash:attempt.content_hash,positions,raw_score:score,total_questions:total,estimated_band:o.estimated_band===null?null:number(o.estimated_band,9),elapsed_seconds:number(o.elapsed_seconds),completion_reason:o.completion_reason};
}
export function parseHistory(value:unknown):HistoryItem[] {
  const o=object(value);if(!Array.isArray(o.items)||o.items.length>100)fail();
  return o.items.map(v=>{const r=object(v);
    if(!["in_progress","submitted","expired"].includes(text(r.status))||!["full_exam","passage_practice"].includes(text(r.mode))||! /^[0-9a-f-]{36}$/i.test(text(r.id)))fail();
    return {id:text(r.id),exam_id:text(r.exam_id),status:r.status as Attempt["status"],mode:r.mode as Attempt["mode"],started_at:date(r.started_at),submitted_at:r.submitted_at===null?null:date(r.submitted_at),raw_score:r.raw_score===null?null:number(r.raw_score,40),estimated_band:r.estimated_band===null?null:number(r.estimated_band,9)};
  });
}
export function examLabel(id:string){const match=/^cambridge-(\d+)-test-(\d+)$/.exec(id);return match?`Cambridge ${Number(match[1])} · Test ${Number(match[2])}`:id}
