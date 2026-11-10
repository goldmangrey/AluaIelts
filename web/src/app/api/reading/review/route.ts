import {proxyAlua} from '@/lib/api/proxy';
export const runtime='nodejs';export const dynamic='force-dynamic';
const headers={'Cache-Control':'private, no-store',Vary:'Authorization'};
export async function POST(request:Request) {
  const authorization=request.headers.get('authorization')??'';
  if(!/^Bearer \S{1,8192}$/.test(authorization))return Response.json({}, {status:401,headers});
  const ownOrigin=new URL(request.url);ownOrigin.host=request.headers.get('host')??ownOrigin.host;
  if(request.headers.get('origin')&&request.headers.get('origin')!==ownOrigin.origin)return Response.json({}, {status:403,headers});
  let input:{attempt_id:string;question_id:string};
  try {
    const reader=request.body?.getReader();if(!reader)throw Error();let text='',size=0;
    try{while(true){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>512)throw Error();text+=new TextDecoder().decode(value);}}finally{void reader.cancel();}
    input=JSON.parse(text);
    if(typeof input.attempt_id!=='string'||typeof input.question_id!=='string'||Object.keys(input).sort().join(',')!=='attempt_id,question_id'||!/^[-0-9a-f]{36}$/i.test(input.attempt_id)||!/^[-a-zA-Z0-9_]{1,96}$/.test(input.question_id))throw Error();
  }catch{return Response.json({}, {status:400,headers});}
  return proxyAlua(new Request(request.url,{method:'POST',headers:{authorization},signal:request.signal}),['reading','attempts',input.attempt_id,'ai-review',input.question_id],undefined,55_000);
}
