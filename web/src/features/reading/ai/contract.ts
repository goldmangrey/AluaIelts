/** Task/domain checks, deliberately outside the provider orchestrator. */
import {modelJSON,ProviderError} from '@/lib/ai/providers';
export interface Evidence {passage_id:string; block_index:number; start:number; end:number; quote:string; kind:'support'|'contradiction'|'relevant_context'}
export interface ReadingReview {why_user_answer_wrong:string; why_correct_answer_works:string; ielts_tip:string; evidence_status:'found'|'unavailable'; evidence:Evidence[]; reason:string|null}
export interface ReviewResponse {question_id:string; fingerprint:string; review:ReadingReview; cached:boolean; source_status:string; retryable?:boolean}
export interface ReadingContext {
  attempt_id?:string; learner_id:string; fingerprint:string; passage_id:string; blocks:{type:string; text:string; label:string|null}[];
  candidates:{id:string;block_index:number;quote:string;start:number;end:number}[];
  question_type:string; correct_answer:string; user_answer:string; is_correct:boolean; not_given:boolean;
  allowed_evidence_kinds?:Evidence['kind'][];
  unavailable_reason:string|null; grounding:{mode:string; targets:string[]; focus?:string[]|null};
}
export function allowedEvidenceKinds(context:ReadingContext):Evidence['kind'][] {
  if(context.not_given)return ['relevant_context'];
  if(['FALSE','NO'].includes(context.correct_answer))return ['contradiction'];
  if(['TRUE','YES'].includes(context.correct_answer))return ['support'];
  return ['support','contradiction','relevant_context'];
}
export function allowedReadingCandidates(context:ReadingContext) {
  return context.candidates.filter(c=>!['heading','paragraph'].includes(context.grounding.mode)||context.grounding.targets.includes(context.blocks[c.block_index]?.label??''));
}
const validationDetails=new Set(['unknown_candidate_id','candidate_outside_allowed_set','wrong_paragraph','duplicate_or_overlap','source_quote_mismatch','prose_reference','anchor','evidence','kind','schema','prose','status']);
export function readingValidationDetail(error:unknown) {
  return error instanceof Error&&validationDetails.has(error.message)?error.message:'other';
}
export function readingDiagnostic(error:unknown) {
  if(error instanceof ProviderError) {
    if(error.reason==='model_abstained')return 'model_abstained';
    if(['deadline','timeout'].includes(error.reason))return 'deadline';
    if(['invalid_model_json','invalid_json'].includes(error.reason))return 'invalid_prose';
    return 'provider_unavailable';
  }
  const reason=error instanceof Error?error.message:'';
  if(reason==='kind')return 'invalid_evidence_kind';
  if(['unknown_candidate_id','candidate_outside_allowed_set','wrong_paragraph','duplicate_or_overlap','source_quote_mismatch','prose_reference','anchor','evidence'].includes(reason))return 'invalid_candidate';
  return 'invalid_prose';
}
export const unavailableReview = {why_user_answer_wrong:'Не удалось надёжно подтвердить фрагмент текста для этого вопроса.',
  why_correct_answer_works:'Сравните сохранённый ответ с ключом. Подтверждённого объяснения по доступному тексту сейчас нет.',
  ielts_tip:'Сопоставьте условие задания с полным контекстом соответствующего абзаца.', evidence:[],evidence_status:'unavailable'} as const;
export function validateReadingReview(output:unknown, context:ReadingContext) {
  const raw=modelJSON(output) as Record<string,unknown>;
  if(!raw||Object.keys(raw).sort().join(',')!=='evidence,evidence_status,ielts_tip,why_correct_answer_works,why_user_answer_wrong')throw Error('schema');
  for(const key of ['why_user_answer_wrong','why_correct_answer_works','ielts_tip']) {
    const text=raw[key];if(typeof text!=='string'||!text.trim()||[...text].length>900||!/[А-Яа-яЁё]/.test(text)||/[<>\x00-\x08]|https?:\/\//.test(text)||/(?:^|[^\p{L}\p{N}_])(?:ты|вы|ученик)(?![\p{L}\p{N}_])[^.!?]{0,70}(?:невнимател|не замет|подум|перепут|не уч[её]л|не понял)/iu.test(text))throw Error('prose');
  }
  if(!Array.isArray(raw.evidence)||raw.evidence.length>3)throw Error('evidence');
  if(raw.evidence_status==='unavailable'&&!raw.evidence.length)throw new ProviderError(502,true,'model_abstained');
  if(raw.evidence_status!=='found'||!raw.evidence.length||context.unavailable_reason)throw Error('status');
  let previousIndex=-1,previousEnd=0;
  for(const value of raw.evidence) {
    if(!value||typeof value!=='object'||Object.keys(value).sort().join(',')!=='candidate_id,kind')throw Error('anchor');
    const {candidate_id,kind}=value as {candidate_id:string;kind:string};
    const candidate=context.candidates.find(c=>c.id===candidate_id);
    if(!candidate)throw Error('unknown_candidate_id');
    if(!allowedReadingCandidates(context).some(c=>c.id===candidate_id))throw Error('candidate_outside_allowed_set');
    if(!allowedEvidenceKinds(context).includes(kind as Evidence['kind']))throw Error('kind');
    const {block_index:index,quote,start:at,end}=candidate,block=context.blocks[index];
    if(block?.type!=='paragraph'||!Number.isInteger(at)||!Number.isInteger(end)||at<0||end<=at||end>block.text.length||block.text.slice(at,end)!==quote)throw Error('source_quote_mismatch');
    if(index<previousIndex||index===previousIndex&&at<previousEnd)throw Error('duplicate_or_overlap');
    if(['heading','paragraph'].includes(context.grounding.mode)&&(!context.grounding.targets.length||!context.grounding.targets.includes(block.label??'')))throw Error('wrong_paragraph');
    previousIndex=index;previousEnd=end;
  }
  const labels=raw.evidence.map((e:{candidate_id:string})=>{const c=context.candidates.find(c=>c.id===e.candidate_id)!;return (context.blocks[c.block_index]?.label??'').toUpperCase();});
  const prose=['why_user_answer_wrong','why_correct_answer_works','ielts_tip'].map(k=>raw[k]).join(' ');
  if([...prose.matchAll(/(?:paragraph|абзац(?:е|а)?)\s+([A-Z])(?![\p{L}\p{N}_])/giu)].some(m=>!labels.includes(m[1]!.toUpperCase())))throw Error('prose_reference');
  return raw;
}
