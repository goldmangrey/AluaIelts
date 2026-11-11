export const criteria = ['task_response','coherence_cohesion','lexical_resource','grammar'] as const;
export interface Anchor {quote:string;start:number;end:number}
export interface Criterion {name:typeof criteria[number];band:number;rationale_en:string;explanation_ru:string;evidence:Anchor[];improvement:string}
export interface Issue extends Anchor {category:'grammar_error'|'lexical_error'|'coherence'|'style_suggestion';why:string;better:string;explanation_ru:string;corrected_translation_ru:string}
export interface Review {criteria:Criterion[];top_improvements:{action:string;quote:string}[];issues:Issue[];uncertainty:string}
export interface Task {id:string;title:string;topic_id:string;essay_type:string;practice_prompt:string;task_requirements:string[];dataset_version:string}
export interface Attempt {id:string;task_id:string;task:Task;essay:string;version:number;word_count:number;status:'draft'|'submitted';updated_at:string;created_at:string;ai_status:string;assessment:(Review&{estimated_band:number;provider:string;model:string;assessed_at:string;essay_version:number})|null}
export const wordCount=(s:string)=>(s.match(/[\p{L}\p{N}]+(?:['’\-][\p{L}\p{N}]+)*/gu)||[]).length;
function object(v:unknown,keys:string[]):Record<string,unknown>{if(!v||typeof v!=='object'||Array.isArray(v)||Object.keys(v).sort().join()!==keys.sort().join())throw Error('schema');return v as Record<string,unknown>;}
function text(v:unknown){if(typeof v!=='string'||v.length<3||v.length>1200)throw Error('text');}
export function validateReview(output:unknown,essay:string):Review {
 let raw=output as {response?:unknown};if(raw&&typeof raw==='object'&&'response' in raw)raw=raw.response as typeof raw;
 if(typeof raw==='string')raw=JSON.parse(raw);
 const r=object(raw,['criteria','top_improvements','issues','uncertainty']);text(r.uncertainty);
 if(!Array.isArray(r.criteria)||r.criteria.length!==4||!Array.isArray(r.top_improvements)||r.top_improvements.length!==3||!Array.isArray(r.issues)||r.issues.length>8)throw Error('schema');
 const anchor=(a:Record<string,unknown>)=>{text(a.quote);if(!Number.isInteger(a.start)||!Number.isInteger(a.end)||(a.start as number)<0||(a.end as number)<=(a.start as number)||(a.end as number)>essay.length||essay.slice(a.start as number,a.end as number)!==a.quote)throw Error('evidence');};
 r.criteria.forEach((v,i)=>{const c=object(v,['name','band','rationale_en','explanation_ru','evidence','improvement']);if(c.name!==criteria[i]||typeof c.band!=='number'||c.band<1||c.band>9||c.band*2%1)throw Error('criterion');['rationale_en','explanation_ru','improvement'].forEach(k=>text(c[k]));if(!Array.isArray(c.evidence)||!c.evidence.length||c.evidence.length>3)throw Error('evidence');c.evidence.forEach(e=>anchor(object(e,['quote','start','end'])));});
 let end=0;const issues=r.issues.map(v=>{const i=object(v,['quote','start','end','category','why','better','explanation_ru','corrected_translation_ru']);anchor(i);if(!['grammar_error','lexical_error','coherence','style_suggestion'].includes(i.category as string)||i.better===i.quote)throw Error('issue');['why','better','explanation_ru','corrected_translation_ru'].forEach(k=>text(i[k]));return i;}).sort((a,b)=>(a.start as number)-(b.start as number));
 for(const i of issues){if((i.start as number)<end)throw Error('overlap');end=i.end as number;}
 if(new Set(r.top_improvements.map(v=>(v as {action?:string}).action?.trim().toLowerCase())).size!==3)throw Error('duplicate_improvement');
 r.top_improvements.forEach(v=>{const i=object(v,['action','quote']);text(i.action);text(i.quote);if(!essay.includes(i.quote as string))throw Error('quote');});
 const value=r as unknown as Review;
 const generic=/\b(?:use|utili[sz]e|incorporate|employ|add|learn)\b.{0,50}\b(?:more advanced|more sophisticated|advanced academic)\b.{0,30}\b(?:vocabulary|collocations|words|phrases)\b/i;
 if([...value.criteria.map(c=>c.improvement),...value.top_improvements.map(i=>i.action)].some(a=>generic.test(a)))throw Error('generic_complexity_advice');
 if(/^(?:none|no uncertainty)[.! ]*$/i.test(value.uncertainty))throw Error('unsupported_certainty');
 return value;
}
/** Exact UTF-16 source candidates: the model copies anchors rather than inventing offsets. */
export function evidenceCandidates(essay:string):Anchor[]{return Array.from(essay.matchAll(/[^.!?]+(?:[.!?]+|$)/g)).flatMap(m=>{const quote=m[0].trim();if(quote.length<3||quote.length>1200)return [];const start=m.index!+m[0].indexOf(quote);return [{quote,start,end:start+quote.length}];});}

/** Model selects immutable source IDs. Additional/generated quotes or offsets are rejected. */
export function validateModelReview(output:unknown,essay:string):Review {
 let raw=output as {response?:unknown};if(raw&&typeof raw==='object'&&'response' in raw)raw=raw.response as typeof raw;if(typeof raw==='string')raw=JSON.parse(raw);
 const r=object(raw,['criteria','top_improvements','issues','uncertainty']),candidates=evidenceCandidates(essay);
 const resolve=(candidate:Record<string,unknown>)=>{if(typeof candidate.candidate_id!=='string'||!/^s\d+$/.test(candidate.candidate_id))throw Error('candidate_id');const anchor=candidates[Number(candidate.candidate_id.slice(1))];if(!anchor)throw Error('candidate_id');return anchor;};
 if(!Array.isArray(r.criteria)||!Array.isArray(r.issues)||!Array.isArray(r.top_improvements))throw Error('schema');
 const normalized={...r,criteria:r.criteria.map(value=>{const c=object(value,['name','band','rationale_en','explanation_ru','evidence','improvement']);if(!Array.isArray(c.evidence))throw Error('evidence');return {...c,evidence:c.evidence.map(e=>resolve(object(e,['candidate_id'])))};}),issues:r.issues.map(value=>{const i=object(value,['candidate_id','category','why','better','explanation_ru','corrected_translation_ru']),anchor=resolve(i);const {candidate_id:_id,...fields}=i;void _id;return {...fields,...anchor};}),top_improvements:r.top_improvements.map(value=>{const i=object(value,['candidate_id','action']);return {action:i.action,quote:resolve(i).quote};})};
 return validateReview(normalized,essay);
}
