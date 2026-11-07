// Public, read-only release gate. No auth/attempt mutations and no secrets.
import {createHash} from 'node:crypto';
const url=process.argv[2];if(!url)throw Error('Pass the backend /openapi.json URL');
const r=await fetch(url,{redirect:'error'});if(!r.ok)throw Error('OpenAPI HTTP '+r.status);
const document=await r.json(),cases=[];
for(const kind of ['listening','reading']){
 const op=Object.entries(document.paths).find(([p])=>p.includes('/'+kind+'/attempts/{')&&p.endsWith('/submit'))?.[1].post;
 const ref=op?.requestBody?.content?.['application/json']?.schema?.$ref;
 const schema=document.components.schemas[ref?.split('/').pop()]||{};
 const expected=['event_id','expected_version','answers','answers_checksum','local_revision',...(kind==='listening'?['state']:[])];
 const missing=expected.filter(k=>!schema.properties?.[k]);cases.push({kind,schema:ref,missing,status:missing.length?'FAIL':'PASS'});
}
console.log(JSON.stringify({url,openapi_sha256:createHash('sha256').update(JSON.stringify(document)).digest('hex'),cases},null,2));if(cases.some(c=>c.status==='FAIL'))process.exitCode=1;
