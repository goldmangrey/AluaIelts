import manifest from './waveform-manifest.json';
export interface WaveformTrack {audio_id:string;source_sha256:string;duration:number;peaks:number[]}
interface Envelope {version:number;exam_id:string;parts:Record<string,WaveformTrack>}
const cache=new Map<string,Promise<Envelope>>();

/** Only compact, precomputed JSON is fetched. No audio download or browser decode. */
export async function loadWaveform(examId:string,part:number):Promise<WaveformTrack> {
  const entry=(manifest.exams as Record<string,{url:string;sha256:string}>)[examId];
  if(!entry)throw Error('Waveform source unavailable');
  let request=cache.get(entry.url);
  if(!request){
    request=fetch(entry.url).then(async response=>{
      if(!response.ok)throw Error('Waveform unavailable');
      const body=await response.json() as Envelope;
      if(body.version!==1||body.exam_id!==examId)throw Error('Waveform identity mismatch');
      return body;
    }).catch(error=>{cache.delete(entry.url);throw error;});
    if(cache.size>=8)cache.delete(cache.keys().next().value!);
    cache.set(entry.url,request);
  }
  const track=(await request).parts[part];
  if(!track||!Number.isFinite(track.duration)||!Array.isArray(track.peaks)||track.peaks.length!==2048||!track.peaks.every(p=>Number.isInteger(p)&&p>=0&&p<=255))throw Error('Invalid waveform');
  return track;
}
