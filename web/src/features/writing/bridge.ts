import {createHmac} from 'node:crypto';
import {readFile, lstat} from 'node:fs/promises';
import {homedir} from 'node:os';
export async function bridge(authorization:string,id:string,action:'claim'|'complete',data:unknown={},configuredKey?:string) {
 let key=configuredKey??process.env.WRITING_BRIDGE_SECRET;
 if(!key&&process.env.ALUA_LOCAL_STACK==='true'){
  const path=`${homedir()}/.local/share/alua/local-stack/writing-bridge.key`,stat=await lstat(path);
  if(stat.isSymbolicLink()||stat.mode&0o077)throw Error('bridge');key=(await readFile(path,'utf8')).trim();
 }
 if(!key||key.length<32)throw Error('bridge');
 let stage='url';
 try {
 const base=new URL(process.env.NEXT_PUBLIC_API_BASE_URL!);
 if(base.protocol!=='https:'&&!(base.protocol==='http:'&&['localhost','127.0.0.1'].includes(base.hostname)))throw Error('bridge');
 const url=new URL(`${base.href.replace(/\/$/,'')}/writing/attempts/${id}/assessment/${action}`),body=JSON.stringify(data),stamp=String(Math.floor(Date.now()/1000));
 stage='signature';
 const signature=createHmac('sha256',key).update(`${stamp}\n${url.pathname}\n${body}`).digest('hex');
 stage='fetch';
 const response=await fetch(url,{method:'POST',headers:{authorization,'Content-Type':'application/json','X-Writing-Time':stamp,'X-Writing-Signature':signature},body,cache:'no-store',redirect:'manual',signal:AbortSignal.timeout(8000)});
 if(response.status>=300&&response.status<400){await response.body?.cancel();throw Error('writing_bridge_redirect_rejected');}
 return response;
 } catch(error) {console.info('[writing-bridge]',{stage,error_type:error instanceof Error?error.name:'unknown',diagnostic:/redirect/i.test(String((error as Error)?.message))?'redirect':/url/i.test(String((error as Error)?.message))?'url':/network|fetch|connect/i.test(String((error as Error)?.message))?'network':/crypto|hmac|key/i.test(String((error as Error)?.message))?'signature':'other'});throw error;}
}
