/** Task/domain checks, deliberately outside the provider orchestrator. */
import {modelJSON} from '@/lib/ai/providers';
export interface Evidence {passage_id:string; block_index:number; start:number; end:number; quote:string; kind:'support'|'contradiction'|'relevant_context'}
export interface ReadingReview {why_user_answer_wrong:string; why_correct_answer_works:string; ielts_tip:string; evidence_status:'found'|'unavailable'; evidence:Evidence[]; reason:string|null}
export interface ReviewResponse {question_id:string; fingerprint:string; review:ReadingReview; cached:boolean; source_status:string}
export interface ReadingContext {
  attempt_id?:string; learner_id:string; fingerprint:string; passage_id:string; blocks:{type:string; text:string; label:string|null}[];
  question_type:string; correct_answer:string; user_answer:string; is_correct:boolean; not_given:boolean;
  unavailable_reason:string|null; grounding:{mode:string; targets:string[]; focus?:string[]|null};
}
export const unavailableReview = {why_user_answer_wrong:'Не удалось надёжно подтвердить фрагмент текста для этого вопроса.',
  why_correct_answer_works:'Сравните сохранённый ответ с ключом. Подтверждённого объяснения по доступному тексту сейчас нет.',
  ielts_tip:'Сопоставьте условие задания с полным контекстом соответствующего абзаца.', evidence:[],evidence_status:'unavailable'} as const;
const words=(text:string)=>new Set((text.toLowerCase().match(/[a-z]{3,}/g)??[]).filter(w=>!['the','and','that','this','with','from','which','for','are','was','were','has','have','not','given','paragraph'].includes(w)));
export function validateReadingReview(output:unknown, context:ReadingContext) {
  const raw=modelJSON(output) as Record<string,unknown>;
  if(!raw||Object.keys(raw).sort().join(',')!=='evidence,evidence_status,ielts_tip,why_correct_answer_works,why_user_answer_wrong')throw Error('schema');
  for(const key of ['why_user_answer_wrong','why_correct_answer_works','ielts_tip']) {
    const text=raw[key];if(typeof text!=='string'||!text.trim()||text.length>900||!/[А-Яа-яЁё]/.test(text)||/[<>\x00-\x08]|https?:\/\//.test(text)||/(?:^|[^\p{L}])(?:ты|вы|ученик)(?=$|[^\p{L}])[^.!?]{0,70}(?:невнимател|не замет|подум|перепут|не уч[её]л|не понял)/iu.test(text))throw Error('prose');
  }
  if(!Array.isArray(raw.evidence)||raw.evidence.length>3)throw Error('evidence');
  if(raw.evidence_status==='unavailable'&&!raw.evidence.length)return raw;
  if(raw.evidence_status!=='found'||!raw.evidence.length||context.unavailable_reason)throw Error('status');
  let previousIndex=-1,previousEnd=0;const quotes:string[]=[];
  for(const value of raw.evidence) {
    if(!value||typeof value!=='object'||Object.keys(value).sort().join(',')!=='block_index,kind,quote')throw Error('anchor');
    const {block_index:index,quote,kind}=value as {block_index:number; quote:string; kind:string};
    if(!Number.isInteger(index)||index<0||typeof quote!=='string'||quote.length<8||quote.length>1200||!['support','contradiction','relevant_context'].includes(kind))throw Error('anchor');
    const block=context.blocks[index],at=block?.text.indexOf(quote)??-1;
    if(block?.type!=='paragraph'||at<0||block.text.indexOf(quote,at+1)>=0||context.blocks.some((b,n)=>n!==index&&b.text.includes(quote))||index<previousIndex||index===previousIndex&&at<previousEnd)throw Error('quote');
    if(context.not_given&&kind!=='relevant_context'||!context.not_given&&['FALSE','NO'].includes(context.correct_answer)&&kind==='support')throw Error('kind');
    if(context.grounding.mode==='heading'&&(quote.length<.6*block.text.length||context.grounding.targets.length&&!context.grounding.targets.includes(block.label??'')))throw Error('main_idea');
    quotes.push(quote);previousIndex=index;previousEnd=at+quote.length;
  }
  const labels=raw.evidence.map((e:{block_index:number})=>(context.blocks[e.block_index]?.label??'').toUpperCase());
  const prose=['why_user_answer_wrong','why_correct_answer_works','ielts_tip'].map(k=>raw[k]).join(' ');
  if([...prose.matchAll(/(?:paragraph|абзац(?:е|а)?)\s+([A-Z])\b/giu)].some(m=>!labels.includes(m[1]!.toUpperCase())))throw Error('paragraph_reference');
  const combined=quotes.join(' '),{mode,targets}=context.grounding;
  if(mode==='text'&&!targets.some(t=>new RegExp(`(?<![\\p{L}\\p{N}_])${t.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')}(?![\\p{L}\\p{N}_])`,'iu').test(combined)))throw Error('key');
  if(mode==='text'&&context.grounding.focus&&!context.grounding.focus.some(w=>words(combined).has(w)))throw Error('blank_context');
  if(mode==='paragraph'&&!raw.evidence.some((e:{block_index:number})=>targets.includes(context.blocks[e.block_index]!.label??'')))throw Error('paragraph');
  if(!['text','paragraph','heading'].includes(mode)) {
    const concepts=words(targets.join(' ')),source=words(combined);
    if(!concepts.size||[...concepts].filter(w=>source.has(w)).length<Math.min(2,concepts.size))throw Error('key_context');
  }
  return raw;
}
