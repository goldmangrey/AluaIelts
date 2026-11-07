export interface SubmissionEvent {event_id:string;expected_version:number;answers?:Record<string,string>;answers_checksum?:string;local_revision?:number}
export function canonicalAnswers(ids:readonly string[],answers:Record<string,string>){return Object.fromEntries([...ids].sort().map(id=>[id,answers[id]??""]));}
export async function answersChecksum(answers:Record<string,string>){
  const ascii=JSON.stringify(Object.entries(answers).sort(([a],[b])=>a<b?-1:a>b?1:0)).replace(/[\u007f-\uffff]/g,c=>`\\u${c.charCodeAt(0).toString(16).padStart(4,"0")}`);
  return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(ascii))),v=>v.toString(16).padStart(2,'0')).join('');
}
