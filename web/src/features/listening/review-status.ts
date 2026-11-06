import type {ResultRow} from "./models";
export type ReviewStatus="correct"|"incorrect"|"unanswered"|"ungraded";
export const reviewStatusLabel:Record<ReviewStatus,string>={correct:"Correct",incorrect:"Incorrect",unanswered:"Unanswered",ungraded:"Not graded"};

// Backend verdicts are authoritative. Missing/ambiguous keys never become errors.
export function reviewStatus(row:ResultRow|undefined):ReviewStatus {
  if(!row?.user_answer.trim())return "unanswered";
  if(row.grading_issue||(row.correct!==true&&row.correct!==false))return "ungraded";
  return row.correct?"correct":"incorrect";
}
export function reviewKey(row:ResultRow|undefined):string|null {
  if(!row||(row.correct!==true&&row.correct!==false)||row.grading_issue)return null;
  return row.correct_answer?.trim()||null;
}
