// Real resolver/component audit; browser work uses only an isolated local fixture.
import {readFileSync,writeFileSync,readdirSync,mkdirSync,existsSync} from 'node:fs';
import {resolve,dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import {execFileSync,spawn} from 'node:child_process';
import {openSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
import assert from 'node:assert/strict';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..'),req=createRequire(import.meta.url),ts=req('typescript'),feature=join(root,'web/src/features/listening'),out=join(root,'docs/listening-source-fidelity-v2');mkdirSync(out,{recursive:true});
const read=p=>JSON.parse(readFileSync(p,'utf8'));
const registry=read(join(feature,'visual-materials.json'));
const cell={exports:{}};runInNewContext(ts.transpileModule(readFileSync(join(feature,'source-material.ts'),'utf8'),{compilerOptions:{target:99,module:1,esModuleInterop:true}}).outputText,{module:cell,exports:cell.exports,require:id=>id.endsWith('.json')?registry:{}});
const {sourceMaterial,visibleSourceMaterial}=cell.exports;
// Historical mixed/text snapshots exercise the renderer model even though new
// canonical data now uses full pages. No newly introduced asset is borrowed.
{
 const current=read(join(root,'backend/app/content/listening_v1/exams/cambridge-04-test-03.json'));
 const old=structuredClone(current),part=old.parts[1],last=part.visual_materials.at(-1).asset_id;
 const omitted=part.visual_materials[0].asset_id;old.assets=old.assets.filter(a=>a.asset_id!==omitted);
 part.visual_materials=[{...part.visual_materials.at(-1),question_range:[11,20],display_order:1}];part.supporting_assets=[last];part.groups.forEach(g=>{g.supporting_assets=[last];});
 const result=visibleSourceMaterial(old,part,part.groups);assert.deepEqual(JSON.parse(JSON.stringify(result.segments.map(s=>s.kind))),['text','image']);assert.equal(result.segments[0].sourceGroupId,part.groups[0].group_id);assert.equal(result.segments[1].assetId,last);
 const textOnly=structuredClone(current),p=textOnly.parts[2],removed=new Set(p.visual_materials.map(m=>m.asset_id));textOnly.assets=textOnly.assets.filter(a=>!removed.has(a.asset_id));p.visual_materials=[];p.supporting_assets=[];p.groups.forEach(g=>{g.supporting_assets=[];g.content_blocks=g.content_blocks.filter(b=>b.kind!=='original_source_image');});
 const lines=visibleSourceMaterial(textOnly,p,p.groups).segments.filter(s=>s.kind==='text');assert.deepEqual(JSON.parse(JSON.stringify(lines.map(s=>s.questionRange))),[[21,25],[26,30]]);assert(lines.every(s=>s.lines.length>0));
}
const rows=[];let groups=0;
for(const f of readdirSync(join(root,'backend/app/content/listening_v1/exams')).filter(f=>f.endsWith('.json')).sort()){
 const exam=read(join(root,'backend/app/content/listening_v1/exams',f));
 for(const part of exam.parts){
  groups+=part.groups.length;const rendered=visibleSourceMaterial(exam,part,part.groups),segments=JSON.parse(JSON.stringify(rendered.segments));
  assert.equal(new Set(segments.map(s=>s.id)).size,segments.length);
  for(const group of part.groups){const same=visibleSourceMaterial(exam,part,part.groups);assert.equal(JSON.stringify(same.segments),JSON.stringify(rendered.segments));assert(group.questions.length);}
  const textGroups=part.groups.filter(g=>sourceMaterial(exam,part,g).lines.length).map(g=>g.group_id);
  const suppressed=part.groups.map(active=>({active:active.group_id,missing_text_groups:textGroups.filter(id=>id!==active.group_id)})).filter(x=>x.missing_text_groups.length);
  rows.push({exam_id:exam.exam_id,book:exam.book,test:exam.printed_test_number,part:part.part_number,question_range:part.question_range,groups:part.groups.map(g=>({id:g.group_id,range:g.question_range})),ordered_source_segments:segments,missing_assets:rendered.missing,baseline_active_only_text_states:suppressed});
 }
}
const target=process.argv.includes('--baseline')?'baseline.json':'component-qa.json';writeFileSync(join(out,target),JSON.stringify({tests:72,parts:rows.length,groups,parts_with_active_text_loss:rows.filter(r=>r.baseline_active_only_text_states.length).length,active_text_loss_states:rows.reduce((n,r)=>n+r.baseline_active_only_text_states.length,0),parts_detail:rows},null,2)+'\n');
assert.equal(rows.length,288);assert.equal(groups,568);console.log(JSON.stringify({tests:72,parts:rows.length,groups,artifact:target,parts_with_old_active_only_text_loss:rows.filter(r=>r.baseline_active_only_text_states.length).length}));
if(process.argv.includes('--browser')){
 const only=process.argv.find(a=>a.startsWith('--only='))?.slice(7).split(',');const browserOutput=only?'browser-qa-targeted.json':'browser-qa.json';
 const {fixture}=JSON.parse(execFileSync(process.execPath,[join(root,'web/scripts/check-listening-ui.mjs'),'--prepare-only'],{encoding:'utf8'}));
 const pagePath=join(fixture,'src/app/page.tsx');let pageSource=readFileSync(pagePath,'utf8');pageSource=pageSource.replace('const q=await searchParams;return',"const q=await searchParams;const eid=/^cambridge-\\d{2}-test-\\d{2}$/.test(q.exam||'')?q.exam:'cambridge-04-test-01';return");pageSource=pageSource.replace(JSON.stringify(join(root,'backend/app/content/listening_v1/exams/cambridge-04-test-01.json')),JSON.stringify(join(root,'backend/app/content/listening_v1/exams'))+"+'/'+eid+'.json'");writeFileSync(pagePath,pageSource);
 const log=openSync(join(fixture,'source-fidelity.log'),'w'),url='http://127.0.0.1:3399',server=spawn(process.execPath,[req.resolve('next/dist/bin/next'),'dev','--webpack','--hostname','127.0.0.1','--port','3399'],{cwd:fixture,stdio:['ignore',log,log]});
 const previous=process.argv.includes('--resume')&&existsSync(join(out,'browser-qa.json'))?read(join(out,'browser-qa.json')):undefined;
 if(previous){
  for(const file of ['source-material.ts','workspace-questions.tsx','questions.tsx','player.tsx','workspace.module.css'])assert.equal(readFileSync(join(previous.fixture,'src/features/listening',file),'utf8'),readFileSync(join(feature,file),'utf8'),'Resume requires identical frontend source: '+file);
  const oldRegistry=read(join(previous.fixture,'src/features/listening/visual-materials.json'));
  assert.deepEqual(Object.fromEntries(Object.entries(oldRegistry.parts).map(([key,p])=>[key,p.materials])),Object.fromEntries(Object.entries(registry.parts).map(([key,p])=>[key,p.materials])),'Resume requires identical canonical selections');
 }
 const cases=previous?.cases||[],errors=[],unverified=[];let stage='boot';const wait=async fn=>{for(let i=0;i<180;i++){if(await fn())return;await new Promise(r=>setTimeout(r,100));}throw Error('Readiness timeout '+stage);};
 // Synthetic native audio only for source UI QA; real audio has a separate V4 suite.
 const wav=Buffer.alloc(44+16000);wav.write('RIFF');wav.writeUInt32LE(wav.length-8,4);wav.write('WAVEfmt ',8);wav.writeUInt32LE(16,16);wav.writeUInt16LE(1,20);wav.writeUInt16LE(1,22);wav.writeUInt32LE(8000,24);wav.writeUInt32LE(16000,28);wav.writeUInt16LE(2,32);wav.writeUInt16LE(16,34);wav.write('data',36);wav.writeUInt32LE(16000,40);
 try{
  await wait(async()=>{try{return(await fetch(url)).ok;}catch{return false;}});
  for(const engine of ['chromium','webkit']){
   let browser;try{browser=await req('@playwright/test')[engine].launch();}catch(e){unverified.push({engine,error:String(e)});continue;}
   try{for(const mobile of [false,true])for(const mode of ['exam','review']){
    const context=await browser.newContext({viewport:mobile?{width:390,height:844}:{width:1440,height:900}}),page=await context.newPage();page.setDefaultTimeout(25000);let gets=0;
    page.on('pageerror',e=>errors.push(stage+': '+e.message));page.on('request',r=>{if(new URL(r.url()).pathname.startsWith('/asset/'))gets++;});
    await page.route('**/*',route=>new URL(route.request().url()).hostname==='127.0.0.1'||route.request().url().startsWith('blob:')?route.continue():route.abort());await page.route('**/api/listening/authorize',r=>r.fulfill({json:{}}));await page.route('**/api/listening/audio/**',r=>r.fulfill({contentType:'audio/wav',body:wav}));
    const panel=async name=>{const b=page.getByRole('button',{name,exact:true});if(await b.isVisible())await b.click();};
    const ready=async()=>{await page.waitForFunction(()=>{const nodes=[...document.querySelectorAll('[data-source-asset]')];return nodes.length>0&&nodes.every(e=>e.querySelector('img')?.naturalWidth>0);});};
    for(const eid of [...new Set(rows.map(r=>r.exam_id))].filter(e=>!only||only.includes(e))){
     if(cases.filter(c=>c.engine===engine&&c.mobile===mobile&&c.mode===mode&&c.exam_id===eid).length===4)continue;
     for(let i=cases.length-1;i>=0;i--)if(cases[i].engine===engine&&cases[i].mobile===mobile&&cases[i].mode===mode&&cases[i].exam_id===eid)cases.splice(i,1);
     stage=`${engine}/${mobile}/${mode}/${eid}`;await page.goto(url+`/?mode=${mode}&exam=${eid}`);await page.locator('#question-1').waitFor({state:'attached'});const player=page.getByRole('region',{name:'Listening audio player'});
     const go=async p=>{await player.getByRole('button',{name:new RegExp('^Part '+p)}).click();await page.locator('#question-'+((p-1)*10+1)).waitFor({state:'attached'});await ready();};
     for(const p of [1,2,3,4]){
      stage=`${engine}/${mobile}/${mode}/${eid}/P${p}`;await go(p);await panel('Source material');const record=rows.find(r=>r.exam_id===eid&&r.part===p),source=page.getByRole('region',{name:'Listening source material',includeHidden:true}),questionPane=page.getByRole('region',{name:'Listening questions',exact:true});
      const ids=()=>source.locator('[data-source-segment]').evaluateAll(es=>es.map(e=>e.getAttribute('data-source-segment')));const expected=record.ordered_source_segments.map(s=>s.id);assert.deepEqual(await ids(),expected);
      assert.equal(await source.getByText('Loading original image…',{exact:true}).count(),0);assert.equal(await source.locator('[role=alert]').count(),0);
      assert(await source.locator('[data-source-asset] > button img').evaluateAll(es=>es.every(e=>e.naturalWidth>0&&Math.abs(e.clientHeight/e.clientWidth-e.naturalHeight/e.naturalWidth)<.015&&getComputedStyle(e).objectFit!=='cover')));
      if(!mobile){const l=await source.boundingBox(),r=await questionPane.boundingBox();assert(l&&r&&l.x+l.width<=r.x+1);}
      await source.evaluate(e=>{e.scrollTop=130;});const scroll=await source.evaluate(e=>e.scrollTop),text=await source.textContent();await panel('Questions');
      for(const n of [p*10-9,p*10])await page.locator('#question-'+n).focus();assert.deepEqual(await ids(),expected);assert.equal(await source.textContent(),text);await panel('Source material');assert.equal(await source.evaluate(e=>e.scrollTop),scroll);
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      if(engine==='chromium'&&mode==='exam'&&[['cambridge-04-test-03',2],['cambridge-04-test-03',3],['cambridge-07-test-04',2],['cambridge-14-test-02',2],['cambridge-19-test-03',3],['cambridge-20-test-03',2]].some(([e,n])=>e===eid&&n===p))await page.screenshot({path:join(out,`${eid}-p${p}-${mobile?'mobile':'desktop'}.png`)});
      cases.push({exam_id:eid,part:p,engine,mobile,mode,segments:expected.length,dom_order:'PASS',focus_invariance:'PASS',loaded_images:'PASS',scroll:'PASS',overflow:false,status:'PASS'});
     }
     const baseline=gets;for(const p of [1,2,4])await go(p);assert.equal(gets,baseline,'Prepared image GETs on Part return');
     if(cases.length%72===0)console.log(JSON.stringify({progress:cases.length,engine,mobile,mode}));
    }
    await context.close();
   }}finally{await browser.close();}
  }
 }catch(e){errors.push(stage+': '+String(e));process.exitCode=1;}finally{server.kill('SIGTERM');}
 writeFileSync(join(out,browserOutput),JSON.stringify({cases,errors,unverified,fixture,scope:'Actual Listening Exam and Review components; isolated local API/auth/media, no production'},null,2)+'\n');console.log(JSON.stringify({browser_cases:cases.length,errors,unverified}));
}
