import {proxyAlua} from '@/lib/api/proxy';
export const dynamic='force-dynamic';export const runtime='nodejs';
export async function POST(request:Request){
 const headers={'Cache-Control':'private, no-store'};
 const authorization=request.headers.get('authorization')||'';
 if(!/^Bearer \S{1,8192}$/.test(authorization))return Response.json({}, {status:401,headers});
 if(request.headers.get('origin')&&request.headers.get('origin')!==new URL(request.url).origin)return Response.json({}, {status:403,headers});
 let input:{attempt_id:string;question_number:number};
 try{
  const reader=request.body?.getReader();if(!reader)throw Error();let raw='',size=0;
  try{while(true){const {done,value}=await reader.read();if(done)break;size+=value.length;if(size>400)throw Error();raw+=new TextDecoder().decode(value);}}finally{await reader.cancel();}
  input=JSON.parse(raw);
  if(Object.keys(input).sort().join(',')!=='attempt_id,question_number'||!/^[-0-9a-f]{36}$/i.test(input.attempt_id)||!Number.isInteger(input.question_number)||input.question_number<1||input.question_number>40)throw Error();
 }catch{return Response.json({}, {status:400,headers});}
 return proxyAlua(new Request(request.url,{method:'POST',headers:{authorization},signal:request.signal}),['listening','attempts',input.attempt_id,'ai-review',String(input.question_number)],undefined,55_000);
}
