// Controlled pending bodies and virtual deadlines; no network or production data.
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
import {createRequire} from 'node:module';
import assert from 'node:assert/strict';
const require=createRequire(import.meta.url),ts=require('typescript');
const code=ts.transpileModule(readFileSync(new URL('../src/lib/api/proxy.ts',import.meta.url),'utf8'),{compilerOptions:{module:1,target:99}}).outputText;
const image=['listening','attempts','00000000-0000-4000-8000-000000000001','assets','asset-'+'a'.repeat(64)];
function harness(){
 const cell={exports:{}},timers=[];let fulfill;
 const body=new ReadableStream({start(controller){fulfill=()=>{controller.enqueue(new Uint8Array([1,2,3]));controller.close();};}});
 const scope={module:cell,exports:cell.exports,require,Request,Response,Headers,URL,AbortController,Uint8Array,process:{env:{}},setTimeout:(fn,ms)=>{const task={fn,ms};timers.push(task);return task;},clearTimeout:task=>{task.cleared=true;},fetch:async(_url,options)=>{assert.equal(options.headers.get('authorization'),'Bearer fixture');assert.equal(options.cache,'no-store');assert.equal(options.redirect,'manual');return new Response(body,{headers:{'Content-Type':'image/png'}});}};
 runInNewContext(code,scope);return {proxy:cell.exports.proxyAlua,timers,fulfill};
}
const cases=[];
{
 const h=harness(),pending=h.proxy(new Request('https://alua.invalid/api/alua/'+image.join('/'),{headers:{Authorization:'Bearer fixture'}}),image,'https://origin.invalid/api/v1');
 await Promise.resolve();await Promise.resolve();assert.equal(h.timers[0].ms,60_000,'Only authenticated Listening image reads need the longer bounded body budget');
 // At the old JSON deadline the complete image is still pending, not rejected.
 assert(h.timers[0].ms>12_000);h.fulfill();const response=await pending;assert.equal(response.status,200);assert.deepEqual([...new Uint8Array(await response.arrayBuffer())],[1,2,3]);assert.equal(response.headers.get('cache-control'),'private, no-store');assert.equal(h.timers[0].cleared,true);cases.push('Listening image body after JSON budget: PASS');
}
for(const path of [['listening','attempts',image[2],'submit'],['reading','attempts',image[2],'assets',image[4]]]){
 const h=harness(),pending=h.proxy(new Request('https://alua.invalid/api/alua/'+path.join('/'),{headers:{Authorization:'Bearer fixture'}}),path,'https://origin.invalid/api/v1');await Promise.resolve();await Promise.resolve();assert.equal(h.timers[0].ms,12_000);h.timers[0].fn();assert.equal((await pending).status,504);cases.push(path[0]+'/'+path.at(-1)+': original deadline PASS');
}
{
 const h=harness(),pending=h.proxy(new Request('https://alua.invalid/api/alua/'+image.join('/'),{headers:{Authorization:'Bearer fixture'}}),image,'https://origin.invalid/api/v1',4);await Promise.resolve();await Promise.resolve();assert.equal(h.timers[0].ms,4);h.timers[0].fn();assert.equal((await pending).status,504);cases.push('Explicit test deadline/cancellation: PASS');
}
console.log(JSON.stringify({cases}));
{
 const cacheCode=ts.transpileModule(readFileSync(new URL('../src/features/listening/asset-cache.ts',import.meta.url),'utf8'),{compilerOptions:{module:1,target:99}}).outputText;
 const cell={exports:{}};let budget;
 runInNewContext(cacheCode,{module:cell,exports:cell.exports,require:()=>({api:(_uid,timeout)=>{budget=timeout;return async()=>new Blob(['image']);}}),navigator:{userAgent:'fixture'},performance,URL,AbortController,Blob});
 const cache=new cell.exports.ListeningAssetCache('uid','attempt','hash');await cache.load('asset');assert.equal(budget,75_000);cache.dispose();console.log('Scoped image client budget and URL cleanup: PASS');
}
