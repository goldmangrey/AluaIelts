export const criteria = ['task_response','coherence_cohesion','lexical_resource','grammar'] as const;
export interface Anchor {quote:string;start:number;end:number}
export const QUALITY_POLICY = 'writing-accuracy-v4' as const;
export interface Target {original:string;replacement:string}
export interface Limitation {description:string;impact:'minor'|'substantial'}
export interface TaskUnderstanding {essay_type:string;position:string;position_development:string;position_claims:{claim:string;development:'developed'|'asserted'|'unclear';basis:string}[];requirements:{requirement:string;coverage:'addressed'|'partial'|'missing';explanation:string}[]}
export interface Criterion {name:typeof criteria[number];band:number;rationale_en?:string;explanation_ru?:string;strength?:string;limitation?:string|null;improvement_quote?:string|null;evidence:Anchor[];improvement?:string|null;target?:Target|null;strengths?:string[];limitations?:Limitation[];descriptor_fit?:string}
export interface Issue extends Anchor {category:'grammar_error'|'lexical_error'|'coherence'|'style_suggestion';why:string;better:string;explanation_ru?:string;corrected_translation_ru?:string;target?:Target;correction_type?:'required'|'optional';necessity?:string}
export interface Review {criteria:Criterion[];top_improvements:{action:string;quote:string;target?:Target|null}[];issues:Issue[];uncertainty:string;quality_policy?:typeof QUALITY_POLICY|'writing-accuracy-v3'|'writing-accuracy-v2';task_understanding?:TaskUnderstanding}
export interface Task {id:string;title:string;topic_id:string;essay_type:string;practice_prompt:string;task_requirements:string[];dataset_version:string}
export interface Attempt {id:string;task_id:string;task:Task;essay:string;version:number;word_count:number;status:'draft'|'submitted';updated_at:string;created_at:string;ai_status:string;assessment:(Review&{estimated_band:number;provider:string;model:string;assessed_at:string;essay_version:number})|null}
export const wordCount=(s:string)=>(s.match(/[\p{L}\p{N}]+(?:['’\-][\p{L}\p{N}]+)*/gu)||[]).length;
function object(v:unknown,keys:string[],optional:string[]=[]):Record<string,unknown>{if(!v||typeof v!=='object'||Array.isArray(v)||Object.keys(v).some(k=>!keys.includes(k)&&!optional.includes(k))||keys.some(k=>!(k in v)))throw Error('schema');return v as Record<string,unknown>;}
function text(v:unknown){if(typeof v!=='string'||v.length<3||v.length>1200)throw Error('text');}
export function validateReview(output:unknown,essay:string):Review {
 let raw=output as {response?:unknown};if(raw&&typeof raw==='object'&&'response' in raw)raw=raw.response as typeof raw;
 if(typeof raw==='string')raw=JSON.parse(raw);
 if(raw&&typeof raw==='object'&&(raw as Record<string,unknown>).quality_policy===QUALITY_POLICY)return validateV4Review(raw,essay);
 const r=object(raw,['criteria','top_improvements','issues','uncertainty'],['quality_policy','task_understanding']);text(r.uncertainty);
 const v3=r.quality_policy==='writing-accuracy-v3',v2=v3||r.quality_policy==='writing-accuracy-v2';if(r.quality_policy!==undefined&&!v2)throw Error('quality_policy');if(v3)validateUnderstanding(r.task_understanding);else if(r.task_understanding!==undefined)throw Error('schema');
 if(!Array.isArray(r.criteria)||r.criteria.length!==4||!Array.isArray(r.top_improvements)||r.top_improvements.length>3||!Array.isArray(r.issues)||r.issues.length>8)throw Error('schema');
 const anchor=(a:Record<string,unknown>)=>{text(a.quote);if(!Number.isInteger(a.start)||!Number.isInteger(a.end)||(a.start as number)<0||(a.end as number)<=(a.start as number)||(a.end as number)>essay.length||essay.slice(a.start as number,a.end as number)!==a.quote)throw Error('evidence');};
 r.criteria.forEach((v,i)=>{const c=object(v,['name','band','rationale_en','explanation_ru','evidence'],['improvement','target','strengths','limitations','descriptor_fit']);if(c.name!==criteria[i]||typeof c.band!=='number'||!Number.isFinite(c.band)||c.band<(v2?0:1)||c.band>9||c.band*2%1)throw Error('criterion');['rationale_en','explanation_ru'].forEach(k=>text(c[k]));if(c.improvement!=null)text(c.improvement);if(!Array.isArray(c.evidence)||!c.evidence.length||c.evidence.length>3)throw Error('evidence');c.evidence.forEach(e=>anchor(object(e,['quote','start','end'])));if(v2){if(!('target' in c))throw Error('target');if(c.improvement==null&&c.target!==null)throw Error('target');validateTarget(c.target,(c.evidence as Anchor[]).map(e=>e.quote));}if(v3)validateAnalysis(c);else if(['strengths','limitations','descriptor_fit'].some(k=>k in c))throw Error('schema');});
 let end=0;const issues=r.issues.map(v=>{const i=object(v,['quote','start','end','category','why','better','explanation_ru','corrected_translation_ru'],v2?['target','correction_type','necessity']:[]);anchor(i);if(!['grammar_error','lexical_error','coherence','style_suggestion'].includes(i.category as string)||i.better===i.quote)throw Error('issue');['why','better','explanation_ru','corrected_translation_ru'].forEach(k=>text(i[k]));if(v2){validateTarget(i.target,[i.quote as string],i.better as string,true);text(i.necessity);if(i.correction_type!==(i.category==='style_suggestion'?'optional':'required'))throw Error('correction_type');}return i;}).sort((a,b)=>(a.start as number)-(b.start as number));
 for(const i of issues){if((i.start as number)<end)throw Error('overlap');end=i.end as number;}
 if(new Set(r.top_improvements.map(v=>(v as {action?:string}).action?.trim().toLowerCase())).size!==r.top_improvements.length)throw Error('duplicate_improvement');
 r.top_improvements.forEach(v=>{const i=object(v,['action','quote'],v2?['target']:[]);text(i.action);text(i.quote);if(!essay.includes(i.quote as string))throw Error('quote');if(v2){if(!('target' in i))throw Error('target');validateTarget(i.target,[i.quote as string]);}});
 const value=r as unknown as Review;
 const generic=/\b(?:use|utili[sz]e|incorporate|employ|add|learn)\b.{0,50}\b(?:more advanced|more sophisticated|advanced academic)\b.{0,30}\b(?:vocabulary|collocations|words|phrases)\b/i;
 if([...value.criteria.map(c=>c.improvement),...value.top_improvements.map(i=>i.action)].some(a=>a!=null&&generic.test(a)))throw Error('generic_complexity_advice');
 if(/^(?:none|no uncertainty)[.! ]*$/i.test(value.uncertainty))throw Error('unsupported_certainty');
 return value;
}
function validateUnderstanding(value:unknown){
 const t=object(value,['essay_type','position','position_development','position_claims','requirements']);['essay_type','position','position_development'].forEach(k=>text(t[k]));
 if(!Array.isArray(t.position_claims)||!t.position_claims.length||t.position_claims.length>4)throw Error('position_claims');t.position_claims.forEach(v=>{const c=object(v,['claim','development','basis']);text(c.claim);text(c.basis);if(!['developed','asserted','unclear'].includes(c.development as string))throw Error('position_claims');});
 if(!Array.isArray(t.requirements)||!t.requirements.length||t.requirements.length>6)throw Error('task_understanding');
 t.requirements.forEach(v=>{const r=object(v,['requirement','coverage','explanation']);text(r.requirement);text(r.explanation);if(!['addressed','partial','missing'].includes(r.coverage as string))throw Error('task_coverage');});
}
function validateAnalysis(c:Record<string,unknown>){
 if(!Array.isArray(c.strengths)||!c.strengths.length||c.strengths.length>3||!Array.isArray(c.limitations)||c.limitations.length>3)throw Error('analysis');
 c.strengths.forEach(text);text(c.descriptor_fit);
 c.limitations.forEach(v=>{const l=object(v,['description','impact']);text(l.description);if(!['minor','substantial'].includes(l.impact as string))throw Error('limitation_impact');if(c.band===9&&l.impact==='substantial')throw Error('rubric_contradiction');});
}
/** Mechanical alignment only; does not verify linguistic correctness or prose semantics. */
function validateTarget(value:unknown,quotes:string[],better?:string,required=false){
 if(value===null&&!required)return;
 const t=object(value,['original','replacement']);
 for(const key of ['original','replacement'])if(typeof t[key]!=='string'||!(t[key] as string).trim()||(t[key] as string).length>1200)throw Error('target');
 if(!quotes.some(q=>q.includes(t.original as string)))throw Error('target_source_mismatch');
 if(t.original===t.replacement)throw Error('unchanged_target');
 if(better!==undefined&&!better.includes(t.replacement as string))throw Error('target_replacement_mismatch');
}
/** Exact UTF-16 source candidates: the model copies anchors rather than inventing offsets. */
export function evidenceCandidates(essay:string):Anchor[]{return Array.from(essay.matchAll(/[^.!?]+(?:[.!?]+|$)/g)).flatMap(m=>{const quote=m[0].trim();if(quote.length<3||quote.length>1200)return [];const start=m.index!+m[0].indexOf(quote);return [{quote,start,end:start+quote.length}];});}

/** Model selects immutable source IDs. Additional/generated quotes or offsets are rejected. */
export function validateLegacyModelReview(output:unknown,essay:string):Review {
 let raw=output as {response?:unknown};if(raw&&typeof raw==='object'&&'response' in raw)raw=raw.response as typeof raw;if(typeof raw==='string')raw=JSON.parse(raw);
 const r=object(raw,['task_understanding','criteria','top_improvements','issues','uncertainty']),candidates=evidenceCandidates(essay);
 const resolve=(candidate:Record<string,unknown>)=>{if(typeof candidate.candidate_id!=='string'||!/^s\d+$/.test(candidate.candidate_id))throw Error('candidate_id');const anchor=candidates[Number(candidate.candidate_id.slice(1))];if(!anchor)throw Error('candidate_id');return anchor;};
 if(!Array.isArray(r.criteria)||!Array.isArray(r.issues)||!Array.isArray(r.top_improvements))throw Error('schema');
 const normalized={...r,quality_policy:'writing-accuracy-v3',criteria:r.criteria.map(value=>{const c=object(value,['name','strengths','limitations','descriptor_fit','band','rationale_en','explanation_ru','evidence'],['improvement','target']);if(['strengths','limitations','descriptor_fit','evidence'].some(k=>Object.keys(c).indexOf(k)>Object.keys(c).indexOf('band')))throw Error('analysis_before_band');if(!Array.isArray(c.evidence))throw Error('evidence');return {...c,...(c.improvement==null&&c.target===undefined?{target:null}:{}),evidence:c.evidence.map(e=>resolve(object(e,['candidate_id'])))};}),issues:r.issues.map(value=>{const i=object(value,['candidate_id','category','why','better','explanation_ru','corrected_translation_ru','target','correction_type','necessity']),anchor=resolve(i);const {candidate_id:_id,...fields}=i;void _id;return {...fields,...anchor};}),top_improvements:r.top_improvements.map(value=>{const i=object(value,['candidate_id','action','target']);return {action:i.action,quote:resolve(i).quote,target:i.target};})};
 return validateReview(normalized,essay);
}

/** V4 compact wire. IDs and exact original fragments are resolved by the server, never by the model. */
export function validateModelReview(output:unknown,essay:string):Review {
 let raw=output as {response?:unknown};if(raw&&typeof raw==='object'&&'response' in raw)raw=raw.response as typeof raw;if(typeof raw==='string')raw=JSON.parse(raw);
 const r=object(raw,['criteria','issues']),byName=object(r.criteria,[...criteria]),anchors=evidenceCandidates(essay);
 const resolve=(id:unknown)=>{if(typeof id!=='string'||!/^s(?:0|[1-9]\d*)$/.test(id))throw Error('candidate_id');const a=anchors[Number(id.slice(1))];if(!a)throw Error('candidate_id');return a;};
 const top:Review['top_improvements']=[];
 const rows=criteria.map(name=>{const c=object(byName[name],['strength','limitation','descriptor_fit','evidence','band','improvement']);
  ['strength','descriptor_fit'].forEach(k=>text(c[k]));if(c.limitation!==null)text(c.limitation);
  if(!Array.isArray(c.evidence)||!c.evidence.length||new Set(c.evidence).size!==c.evidence.length)throw Error('evidence');
  const evidence=c.evidence.map(resolve);let action:null|string=null,quote:null|string=null;
  if(c.improvement!==null){const i=object(c.improvement,['candidate_id','action']);text(i.action);if(!c.evidence.includes(i.candidate_id))throw Error('improvement_evidence');action=i.action as string;quote=resolve(i.candidate_id).quote;if(top.length<3)top.push({action,quote});}
  return {name,strength:c.strength,limitation:c.limitation,descriptor_fit:c.descriptor_fit,evidence:displayEvidence(evidence,quote),band:c.band,improvement:action,improvement_quote:quote};
 });
 if(!Array.isArray(r.issues)||r.issues.length>8)throw Error('issues');
 const issues=r.issues.map(value=>{const i=object(value,['candidate_id','original','correction','category','why']),a=resolve(i.candidate_id);shortText(i.original);shortText(i.correction);text(i.why);const original=i.original as string,at=a.quote.indexOf(original);if(at<0||at!==a.quote.lastIndexOf(original))throw Error('issue_source');return {quote:original,start:a.start+at,end:a.start+at+original.length,category:i.category,why:i.why,better:i.correction};});
 return validateV4Review({quality_policy:QUALITY_POLICY,criteria:rows,top_improvements:top,issues,uncertainty:'AI Task 2 estimate based on a limited sample. Examiner calibration and feedback semantics are not verified.'},essay);
}
// Validate the complete source list before selecting display anchors. Keep the action's source visible.
function displayEvidence(evidence:Anchor[],quote:unknown):Anchor[]{
 const visible=evidence.slice(0,3),selected=evidence.find(a=>a.quote===quote);
 if(selected&&!visible.some(a=>a.quote===quote))visible[visible.length-1]=selected;
 return visible;
}
function shortText(v:unknown){if(typeof v!=='string'||!v.trim()||v.length>1200)throw Error('text');}
function validateV4Review(raw:unknown,essay:string):Review {
 const r=object(raw,['quality_policy','criteria','top_improvements','issues','uncertainty']);text(r.uncertainty);
 if(r.quality_policy!==QUALITY_POLICY||!Array.isArray(r.criteria)||r.criteria.length!==4||!Array.isArray(r.issues)||r.issues.length>8||!Array.isArray(r.top_improvements)||r.top_improvements.length>3)throw Error('schema');
 const anchor=(v:unknown)=>{const a=object(v,['quote','start','end']);shortText(a.quote);if(!Number.isInteger(a.start)||!Number.isInteger(a.end)||(a.start as number)<0||(a.end as number)<=(a.start as number)||(a.end as number)>essay.length||essay.slice(a.start as number,a.end as number)!==a.quote)throw Error('evidence');return a;};
 r.criteria.forEach((v,n)=>{const c=object(v,['name','strength','limitation','descriptor_fit','evidence','band','improvement','improvement_quote']);if(c.name!==criteria[n]||typeof c.band!=='number'||!Number.isFinite(c.band)||c.band<0||c.band>9||c.band*2%1)throw Error('criterion');text(c.strength);text(c.descriptor_fit);if(c.limitation!==null)text(c.limitation);if(!Array.isArray(c.evidence)||!c.evidence.length)throw Error('evidence');c.evidence.forEach(anchor);if(new Set((c.evidence as Anchor[]).map(a=>`${a.start}:${a.end}`)).size!==c.evidence.length)throw Error('duplicate_evidence');if(c.improvement===null){if(c.improvement_quote!==null)throw Error('improvement_evidence');}else{text(c.improvement);if(!c.evidence.some(e=>(e as Anchor).quote===c.improvement_quote))throw Error('improvement_evidence');}c.evidence=displayEvidence(c.evidence as Anchor[],c.improvement_quote);});
 let end=0;const issues=r.issues.map(v=>{const i=object(v,['quote','start','end','category','why','better']);anchor({quote:i.quote,start:i.start,end:i.end});text(i.why);shortText(i.better);if(!['grammar_error','lexical_error'].includes(i.category as string)||i.better===i.quote)throw Error('issue');return i;}).sort((a,b)=>(a.start as number)-(b.start as number));for(const i of issues){if((i.start as number)<end)throw Error('overlap');end=i.end as number;}
 const expected=(r.criteria as unknown as Criterion[]).filter(c=>c.improvement!==null).slice(0,3).map(c=>({action:c.improvement,quote:c.improvement_quote}));if(r.top_improvements.length!==expected.length)throw Error('improvement_consistency');r.top_improvements.forEach((v,n)=>{const i=object(v,['action','quote']);if(i.action!==expected[n]!.action||i.quote!==expected[n]!.quote)throw Error('improvement_consistency');});
 return r as unknown as Review;
}
