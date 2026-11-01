import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { parseExam, parseAttempt } from "../src/features/reading/exam/parse";
import { questionTypes, allQuestions, type Attempt, type Exam } from "../src/features/reading/exam/models";
import { QuestionGroup, multipleSelection, type QuestionActions } from "../src/features/reading/exam/question-renderer";
import { AnswerSession, type SaveEvent } from "../src/features/reading/exam/answers";
import { findOrStart } from "../src/features/reading/exam/start";
import { ApiError } from "../src/lib/api/client";
import type { ReadingEntry } from "../src/features/reading/contracts";

const fixtures = JSON.parse(readFileSync(process.env.ALUA_C_FIXTURES!, "utf8"));
const exams: Exam[] = fixtures.exams.map(parseExam);
function attempt(exam = exams[0]!): Attempt {
  return { id: "11111111-2222-4333-8444-555555555555", exam_id: exam.id, exam, mode: "full_exam", status: "in_progress", version: 7, content_hash: "fixture-hash", server_now: fixtures.now, deadline_at: fixtures.deadline, answers: {}, state: { current_passage: 2, checked_question_ids: [] }, not_fully_proofread: true };
}
function ack(event: SaveEvent) { return { ...attempt(), version: event.expected_version + 1, answers: event.answers, mutation_applied: true }; }

test("all enabled real public exams parse and every real group renders without answer keys", () => {
  expect(exams).toHaveLength(63);
  const types = new Set<string>();
  let groups = 0;
  const actions: QuestionActions = { answers: {}, review: new Set(), locked: new Set(), disabled: false, change: () => {}, toggleReview: () => {}, register: () => {}, focus: () => {} };
  for (const exam of exams) {
    expect(allQuestions(exam).map((q) => q.number).sort((a,b) => a-b)).toEqual(Array.from({length:40},(_,i)=>i+1));
    for (const p of exam.passages) for (const g of p.question_groups) {
      const html = renderToStaticMarkup(createElement(QuestionGroup, { group: g, actions, uid: "fixture", active: false }));
      expect(html).toContain(`data-question-type="${g.type}"`);
      types.add(g.type); groups++;
    }
  }
  expect([...types].sort()).toEqual([...questionTypes].sort());
  expect(groups).toBe(538);
});

test("malformed/unsupported/private content fail closed, saved answers and passage survive parsing", () => {
  const exam = exams[0]!;
  const a = attempt(exam); a.answers[allQuestions(exam)[0]!.id] = "my previous answer";
  expect(parseAttempt(a, true).answers).toEqual(a.answers);
  expect(parseAttempt(a, true).state.current_passage).toBe(2);
  for (const value of [{...exam,passages:[]},{...exam,question_count:41},{...exam,accepted_answers:["private"]}]) expect(()=>parseExam(value)).toThrow(ApiError);
  const unknown = structuredClone(exam); unknown.passages[0]!.question_groups[0]!.type = "unsupported" as never;
  expect(()=>parseExam(unknown)).toThrow(ApiError);
  expect(()=>parseAttempt({...a,exam:undefined},true)).toThrow(ApiError);
});

test("multiple choice maps chosen letters into separate scored positions without duplicates", () => {
  const group = exams.flatMap((e)=>e.passages.flatMap((p)=>p.question_groups)).find((g)=>g.type==="multiple_choice_multiple" && g.options.length)!;
  let answers = multipleSelection(group,{},group.options[0]!.label);
  answers = {...answers,...multipleSelection(group,answers,group.options[1]!.label)};
  expect(answers[group.questions[0]!.id]).toBe(group.options[0]!.label);
  expect(answers[group.questions[1]!.id]).toBe(group.options[1]!.label);
  answers = {...answers,...multipleSelection(group,answers,group.options[0]!.label)};
  expect(answers[group.questions[0]!.id]).toBe(group.options[1]!.label);
  expect(answers[group.questions[1]!.id]).toBe("");
});

test("serial save preserves typing during flight and advances CAS versions", async () => {
  let release!: ()=>void; const events:SaveEvent[]=[];
  const session = new AnswerSession(attempt(),async(event)=>{events.push(event);if(events.length===1)await new Promise<void>((resolve)=>release=resolve);return ack(event)});
  try {
    session.change({q:"a"});const saved=session.flush();
    session.change({q:"ab"}); release();await saved;
    expect(events.map((e)=>e.expected_version)).toEqual([7,8]);
    expect(events.map((e)=>e.answers.q)).toEqual(["a","ab"]);
    expect(session.snapshot().dirty).toBe(0);expect(session.snapshot().answers.q).toBe("ab");
  } finally {session.dispose()}
});

test("failed save retains draft, retries exact UUID/payload, conflict never overwrites server", async () => {
  const events:SaveEvent[]=[];
  const session = new AnswerSession(attempt(),async(event)=>{events.push(event);if(events.length===1)throw new ApiError(0,"network_error");return ack(event)});
  try {
    session.change({q:"first"});await session.flush();expect(session.snapshot().dirty).toBe(1);
    session.change({q:"second"});await session.flush();
    expect(events[1]).toEqual(events[0]);expect(events[2]?.answers.q).toBe("second");expect(session.snapshot().dirty).toBe(0);
  } finally {session.dispose()}
  const conflict = new AnswerSession(attempt(),async()=>{throw new ApiError(409,"reading_version_conflict")});
  try {conflict.change({q:"mine"});await conflict.flush();conflict.change({q:"overwrite"});expect(conflict.snapshot().answers.q).toBe("mine");expect(conflict.snapshot().dirty).toBe(1);}finally{conflict.dispose()}
});

test("resume never creates; unknown start retries reuse event; disabled tests do not start", async () => {
  const exam=exams[0]!;
  const entry:ReadingEntry={exam_id:exam.id,source_book:exam.source_book,source_test_number:exam.source_test_number,test_ordinal:1,enabled_for_private_practice:true,content_status:"needs_review",not_fully_proofread:true,question_count:40,passage_count:3,in_progress_attempt_ids:[attempt().id]};
  const catalog=async()=>({dataset_version:"1",items:[{book_number:exam.source_book,exams:[entry]}]});
  let saved:string|null=null;const events:unknown[]=[];
  const storage={getItem:()=>saved,setItem:(_key:string,value:string)=>{saved=value}};
  const services={catalog,storage,create:async(body:unknown)=>{events.push(body);if(events.length===1)throw new ApiError(0,"timeout");return attempt(exam)}};
  expect(await findOrStart(exam.id,"key",services)).toEqual([attempt().id]);expect(events).toHaveLength(0);
  entry.in_progress_attempt_ids=[];
  await expect(findOrStart(exam.id,"key",services)).rejects.toThrow();
  await expect(findOrStart(exam.id,"key",services)).resolves.toEqual([attempt().id]);expect(events[0]).toEqual(events[1]);
  entry.enabled_for_private_practice=false;
  await expect(findOrStart(exam.id,"key",services)).rejects.toMatchObject({status:404});expect(events).toHaveLength(2);
});
