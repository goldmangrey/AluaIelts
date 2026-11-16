export interface Topic {id:string;name_en:string;name_ru:string;main_category:string}
export interface Question {id:string;part:number;topic_ids:string[];source_ids:string[];provenance_ids:string[];origin:string;prompt:string;bullets?:string[];closing?:string;related_ids?:string[]}
export interface PracticeSet {id:string;type:string;topic_id:string;ids:string[];original_count:number;source_ids:string[];country:string|null;reported_period:string|null}
export interface Source {id:string;url:string;publisher:string;page_title:string;source_type:string}
export interface Content {version:string;topics:Topic[];questions:Question[];sets:PracticeSet[];sources:Source[]}
export const partNames=['All parts','Part 1 — Interview','Part 2 — Cue Card','Part 3 — Discussion'];
export function originLabel(origin:string){return origin==='official_sample'?'Official sample source · Adapted practice':'Reported topics · Adapted practice';}
export function setLabel(type:string){return type==='OFFICIAL_SAMPLE_SET'?'Official sample source':type==='CURATED_FROM_REAL_QUESTIONS'?'Editorial practice set':'Candidate-reported linked topics';}
