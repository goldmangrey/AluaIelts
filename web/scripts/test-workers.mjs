// Two real workerd runtimes: the normal build (read-only checks) and an isolated
// build pointed at a controlled HTTP transport fixture. No production writes.
import {createServer} from "node:http";
import {mkdtemp,cp,writeFile,rm,readFile} from "node:fs/promises";
import {tmpdir} from "node:os";
import {resolve,dirname,join} from "node:path";
import {fileURLToPath} from "node:url";
import {createRequire} from "node:module";
import {spawn} from "node:child_process";
const root=resolve(dirname(fileURLToPath(import.meta.url)),".."),require=createRequire(import.meta.url);
const adapter=resolve(dirname(require.resolve("@opennextjs/cloudflare")),"../cli/index.js");
const temporary=await mkdtemp(join(tmpdir(),"alua-workers-tests-"));
const env={...process.env,ALUA_WORKERS_TEST_APP:temporary,ALUA_WORKERS_ADAPTER_CLI:adapter,WRANGLER_SEND_METRICS:"false"};
for(const key of Object.keys(env))if(key.startsWith("NEXT_PUBLIC_"))env[key]="";
env.NEXT_PUBLIC_API_BASE_URL="http://127.0.0.1:8899/api/v1";
let redirectHits=0,requests=0;
const png=Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aGQAAAABJRU5ErkJggg==","base64");
const upstream=createServer(async(req,res)=>{
 const url=new URL(req.url,"http://127.0.0.1:8899");
 if(url.pathname==="/observed"){res.setHeader("Content-Type","application/json");res.end(JSON.stringify({redirectHits,requests}));return}
 if(url.pathname==="/redirect-capture"){redirectHits++;res.end("unexpected redirect");return}
 requests++;
 if(req.headers.authorization!=="Bearer transport-fixture-only"){res.writeHead(401,{"Content-Type":"application/json"});res.end(JSON.stringify({error:{code:"fixture_unauthorized"}}));return}
 const scenario=url.searchParams.get("scenario");
 if(scenario==="redirect"){res.writeHead(302,{Location:"http://127.0.0.1:8899/redirect-capture"});res.end();return}
 if(scenario==="stalled-body"){res.writeHead(200,{"Content-Type":"application/json"});res.write('{"unfinished":');return}
 if(url.pathname.endsWith("/assets/transport-fixture")){res.writeHead(200,{"Content-Type":"image/png","Cache-Control":"public,max-age=3600",ETag:'"fixture-png"',"X-Image-Width":"1","X-Image-Height":"1"});res.end(png);return}
 let body="";for await(const chunk of req)body+=chunk;
 const status=Number(url.searchParams.get("status")??200);
 res.writeHead(status,{"Content-Type":"application/json","Cache-Control":"public,max-age=3600","Set-Cookie":"must-not-forward=1"});
 res.end(JSON.stringify({method:req.method,path:url.pathname,query:url.searchParams.get("url"),bearer_forwarded:true,body:body?JSON.parse(body):null,status}));
});
function run(command,args,cwd,environment=env){return new Promise((ok,fail)=>{const child=spawn(command,args,{cwd,env:environment,stdio:"inherit"});child.on("error",fail);child.on("exit",code=>code===0?ok():fail(Error(`Workers verification exited ${code}`)))})}
try{
 await readFile(join(root,".open-next/worker.js"));
 await new Promise((ok,fail)=>{upstream.once("error",fail);upstream.listen(8899,"127.0.0.1",ok)});
 for(const name of ["src","public","package.json","pnpm-lock.yaml","pnpm-workspace.yaml","tsconfig.json","next.config.ts","postcss.config.mjs","open-next.config.ts","wrangler.jsonc"])
   await cp(join(root,name),join(temporary,name),{recursive:true});
 await run("pnpm",["install","--frozen-lockfile"],temporary);
 const config=(await readFile(join(temporary,"wrangler.jsonc"),"utf8")).replaceAll('"alua-ielts"','"alua-workers-fixture"');
 await writeFile(join(temporary,"wrangler.jsonc"),config);
 await run(process.execPath,[adapter,"build"],temporary);
 // Do not replace the real-config build's NEXT_PUBLIC values in the primary runtime.
 const testEnv={...process.env,ALUA_WORKERS_TEST_APP:temporary,ALUA_WORKERS_ADAPTER_CLI:adapter,WRANGLER_SEND_METRICS:"false"};
 await run(process.execPath,[join(dirname(require.resolve("@playwright/test/package.json")),"cli.js"),"test","--config=playwright.workers.config.ts",...process.argv.slice(2)],root,testEnv);
}finally{upstream.closeAllConnections();await new Promise(r=>upstream.close(r));await rm(temporary,{recursive:true,force:true})}
