import manifest from './waveform-manifest.json';

/** Local companion to ListeningDraft. No extra fields enter the backend State. */
export class AudioProgress {
  private positions:Record<number,number>={};
  activePart:number;
  readonly key:string;
  constructor(uid:string,attemptId:string,examId:string,initialPart=1,initialSeconds=0){
    const version=(manifest.exams as Record<string,{sha256:string}>)[examId]?.sha256||'v1';
    this.key=`alua:listening:audio:v1:${uid}:${attemptId}:${examId}:${version}`;
    this.activePart=initialPart;
    this.positions[initialPart]=initialSeconds;
    try{
      const saved=JSON.parse(localStorage.getItem(this.key)||'null');
      if(saved?.version===1){
        for(const part of [1,2,3,4])if(Number.isFinite(saved.positions?.[part])&&saved.positions[part]>=0)this.positions[part]=saved.positions[part];
        if([1,2,3,4].includes(saved.activePart))this.activePart=saved.activePart;
      }
    }catch{/* Private browsing/storage failures retain the in-memory positions. */}
  }
  get(part:number){return this.positions[part]||0;}
  set(part:number,seconds:number){
    if(![1,2,3,4].includes(part)||!Number.isFinite(seconds)||seconds<0)return;
    this.positions[part]=seconds;this.activePart=part;
    try{localStorage.setItem(this.key,JSON.stringify({version:1,activePart:part,positions:this.positions}));}catch{/* Playback remains usable without storage. */}
  }
}
