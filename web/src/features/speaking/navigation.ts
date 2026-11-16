import type {Content,Question} from './model';
export interface SpeakingTask{id:string;topicId:string;title:string;questions:Question[];kind:'interview'|'cue'|'discussion'|'set';partial?:boolean}
export function speakingTasks(data:Content):SpeakingTask[]{
 const byId=new Map(data.questions.map(q=>[q.id,q])),items:SpeakingTask[]=[];
 for(const topic of data.topics){
  const questions=data.questions.filter(q=>q.topic_ids.includes(topic.id));
  const interview=questions.filter(q=>q.part===1),discussion=questions.filter(q=>q.part===3);
  if(interview.length)items.push({id:`interview:${topic.id}`,topicId:topic.id,title:'Everyday conversation',questions:interview,kind:'interview'});
  for(const cue of questions.filter(q=>q.part===2))items.push({id:cue.id,topicId:topic.id,title:cue.prompt,questions:[cue,...(cue.related_ids??[]).map(id=>byId.get(id)).filter((q):q is Question=>!!q)],kind:'cue'});
  if(discussion.length)items.push({id:`discussion:${topic.id}`,topicId:topic.id,title:'Ideas and opinions',questions:discussion,kind:'discussion'});
  for(const set of data.sets.filter(v=>v.topic_id===topic.id)){
   const qs=set.ids.map(id=>byId.get(id)).filter((q):q is Question=>!!q);
   if(qs.length)items.push({id:set.id,topicId:topic.id,title:set.type==='CURATED_FROM_REAL_QUESTIONS'?'Editorial practice sequence':set.type==='OFFICIAL_SAMPLE_SET'?'Sample-linked practice':'Linked topic practice',questions:qs,kind:'set',partial:qs.length<set.original_count});
  }
 }
 return items;
}
