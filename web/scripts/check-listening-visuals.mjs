// Read-only offline regression check: execute the real resolver over all current
// groups and reconstructed legacy bindings. No browser, AI, backend or database.
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {createRequire} from 'node:module';
import {runInNewContext} from 'node:vm';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..'),web=resolve(root,'web');
const require=createRequire(pathToFileURL(resolve(web,'package.json'))),ts=require('typescript');
const read=p=>JSON.parse(readFileSync(resolve(root,p),'utf8'));
const audit=read('docs/listening-visual-audit/audit.json');
const findings=read('docs/listening-visual-audit/reviewed-findings.json').findings;
const policy=read('web/src/features/listening/visual-materials.json');
const path=resolve(web,'src/features/listening/source-material.ts'),resolverModule={exports:{}};
runInNewContext(ts.transpileModule(readFileSync(path,'utf8'),{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,esModuleInterop:true}}).outputText,{exports:resolverModule.exports,module:resolverModule,require:createRequire(pathToFileURL(path)),Set,Map});
const {sourceMaterial}=resolverModule.exports;
const duplicateFindings=findings.filter(f=>f.kind==='duplicate_content'),inversions=findings.filter(f=>f.kind==='order_inversion');
const samePart=(f,p)=>f.book===p.book&&f.test===p.test&&f.part===p.part;
let parts=0,groups=0,duplicates=new Set(),orders=new Set(),missing=0,lost=0,wrong=0,legacyDuplicates=new Set(),additionalDuplicates=0;
const sheets=[];
for(const p of audit.parts){
 const exam=read(`backend/app/content/listening_v1/exams/${p.exam}.json`),part=exam.parts.find(x=>x.part_number===p.part),catalogue=policy.parts[`${p.exam}-p${p.part}`];
 const legacy=structuredClone(exam),oldpart=legacy.parts.find(x=>x.part_number===p.part);delete oldpart.visual_materials;oldpart.supporting_assets=p.part_assets;
 for(const oldgroup of oldpart.groups){const raw=p.raw_groups.find(x=>x.id===oldgroup.group_id);oldgroup.supporting_assets=raw.supporting;oldgroup.content_blocks=[...oldgroup.content_blocks.filter(b=>b.kind!=='original_source_image'),...raw.blocks.map(asset_id=>({kind:'original_source_image',asset_id}))];for(const q of oldgroup.questions){delete q.visual_binding;if(raw.question_assets.length)q.visual_binding={asset_ids:raw.question_assets};}}
 const shown=new Set(),rows=[];
 for(const group of part.groups){
  groups++;const material=sourceMaterial(exam,part,group),before=p.groups.find(g=>g.id===group.group_id),oldmaterial=sourceMaterial(legacy,oldpart,oldpart.groups.find(g=>g.group_id===group.group_id));
  missing+=material.missing.length+Number(material.unavailable)+oldmaterial.missing.length+Number(oldmaterial.unavailable);
  if(before.assets.length&&!material.assets.length&&!material.lines.length&&!group.answer_bank){lost++;console.error('LOST REQUIRED CONTEXT',group.group_id);}
  const suitable=catalogue.materials.filter(m=>m.question_range[0]<=group.question_range[1]&&group.question_range[0]<=m.question_range[1]);
  assert.deepEqual([...material.assets],suitable.map(m=>m.asset_id),`${group.group_id}: unsuitable/missing material`);
  assert.deepEqual([...oldmaterial.assets], [...material.assets],`${group.group_id}: old snapshot rendering differs`);
  material.assets.forEach(id=>shown.add(id));
  for(const f of duplicateFindings.filter(f=>samePart(f,p))){if(f.assets.every(a=>material.assets.includes(a)))duplicates.add(f.id);if(f.assets.every(a=>oldmaterial.assets.includes(a)))legacyDuplicates.add(f.id);}
  for(const f of policy.provenance.additional_reviewed_relations.filter(f=>f.part===`${p.exam}-p${p.part}`))if(material.assets.includes(f.a)&&material.assets.includes(f.b))additionalDuplicates++;
  for(const f of inversions.filter(f=>samePart(f,p)))if(f.assets.every(a=>material.assets.includes(a))&&material.assets.indexOf(f.assets[0])<material.assets.indexOf(f.assets[1]))orders.add(f.id);
  if(p.book===18&&p.test===2&&p.part===4){const forbidden=audit.findings.find(f=>f.kind==='foreign_question_range');wrong+=material.assets.filter(a=>forbidden.assets.includes(a)).length;}
  rows.push({range:group.question_range,assets:material.assets});
 }
 // Every original image survives as itself or as a reviewed content alternative.
 for(const id of p.part_assets){if(catalogue.excluded_asset_ids?.includes(id))continue;const replacement=catalogue.materials.find(m=>m.asset_id===id||m.alternative_asset_ids.includes(id));if(!replacement||!shown.has(replacement.asset_id)){lost++;console.error('LOST ASSET',p.exam,p.part,id);}}
 const ranges=catalogue.materials.map(m=>m.question_range[0]);assert(ranges.every((x,i)=>!i||ranges[i-1]<=x),`${p.exam} P${p.part}: printed order`);
 sheets.push({exam:p.exam,part:p.part,groups:rows});parts++;
}
// All nine named regressions must have known independently reviewed boundaries.
assert.equal(inversions.length,9);assert.equal(duplicateFindings.length,86);
// Printed boundaries reviewed independently of the resolver implementation.
for(const [eid,pn,ranges] of [
 ['cambridge-06-test-02',2,[[11,17],[18,20]]],['cambridge-09-test-02',2,[[11,15],[16,20]]],
 ['cambridge-09-test-04',2,[[11,13],[14,18],[19,20]]],['cambridge-09-test-04',4,[[31,34],[35,40]]],
 ['cambridge-12-test-07',3,[[21,26],[27,30]]],['cambridge-14-test-02',2,[[11,15],[16,20]]],
 ['cambridge-17-test-02',2,[[11,14],[15,20]]],['cambridge-17-test-03',3,[[21,24],[25,30]]],
 ['cambridge-19-test-03',1,[[1,6],[7,10]]],
])assert.deepEqual(policy.parts[`${eid}-p${pn}`].materials.map(m=>m.question_range),ranges,`${eid} Part ${pn}`);
const ownership=read('backend/app/content/listening_v1/qa/assets.json').assets;
const foreign=audit.findings.find(f=>f.kind==='foreign_question_range').assets[0];
assert(ownership.find(a=>a.asset_id===foreign).associations.every(a=>a.part_number===1));
let changedImages=0;for(const asset of Object.values(audit.registry)){const bytes=readFileSync(resolve(root,'backend/app/content/listening_v1',asset.relative_path));if(createHash('sha256').update(bytes).digest('hex')!==asset.sha256)changedImages++;}
const summary={tests:new Set(sheets.map(s=>s.exam)).size,parts,groups,duplicate_pairs:{before:86,after:duplicates.size},order_inversions:{before:9,after:orders.size},wrong_part:{before:1,after:wrong},missing_required_images:missing+lost,legacy_duplicate_pairs:legacyDuplicates.size,changed_image_bytes:changedImages,additional_reviewed_pairs:policy.provenance.additional_reviewed_relations.length,additional_duplicate_pairs_after:additionalDuplicates,stage2:{damaged_crops:26,suspected_crops:21,displayed_damaged_crops:findings.filter(f=>f.kind==='clipped_source'&&f.assets.some(a=>Object.values(policy.parts).some(p=>p.materials.some(m=>m.asset_id===a)))).length,displayed_suspected_crops:findings.filter(f=>f.kind==='crop_edge_risk'&&f.assets.some(a=>Object.values(policy.parts).some(p=>p.materials.some(m=>m.asset_id===a)))).length,status:'physical files unchanged; alternate full pages selected where available'}};
assert.equal(parts,288);assert.equal(groups,568);assert.equal(duplicates.size+orders.size+wrong+missing+lost+legacyDuplicates.size+changedImages+additionalDuplicates,0,JSON.stringify(summary));
const out=resolve(root,'docs/listening-visual-audit/stage1');mkdirSync(out,{recursive:true});writeFileSync(resolve(out,'results.json'),JSON.stringify({summary,parts:sheets},null,2)+'\n');
const esc=x=>String(x).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
writeFileSync(resolve(out,'index.html'),'<!doctype html><meta charset="utf-8"><title>Listening Stage 1 — all groups</title><style>body{font:14px system-ui;margin:24px}section{border-top:1px solid #ccc;padding:16px}figure{display:inline-block;vertical-align:top;width:250px;margin:8px}img{max-width:240px;max-height:380px}figcaption{overflow-wrap:anywhere;font-size:11px}pre{white-space:pre-wrap}</style><h1>Listening Stage 1 — 72 Tests / 288 Parts / 568 groups</h1><p>Exact current resolver output. Original audit remains unchanged. Thumbnails are overview aids, not a complete readability PASS.</p><pre>'+esc(JSON.stringify(summary,null,2))+'</pre>'+sheets.map(p=>'<section><h2>'+esc(p.exam)+' / Part '+p.part+'</h2>'+p.groups.map(g=>'<p>Q'+g.range.join('–')+': '+g.assets.map(a=>esc(a.slice(0,18))).join(' → ')+'</p>').join('')+[...new Set(p.groups.flatMap(g=>g.assets))].map(a=>'<figure><a href="../../../backend/app/content/listening_v1/'+esc(audit.registry[a].relative_path)+'"><img loading="lazy" src="../thumbs/'+a+'.jpg"></a><figcaption>'+esc(audit.registry[a].sources.join(' / '))+'<br>'+esc(a)+'</figcaption></figure>').join('')+'</section>').join(''));
console.log(JSON.stringify(summary,null,2));
// Unknown legacy revisions get no broad multi-page fallback. A genuine single
// image can be shared; unavailable canonical IDs still produce a visible alert.
const unknown=read('backend/app/content/listening_v1/exams/cambridge-09-test-02.json');unknown.exam_id='unknown-legacy-revision';const p=unknown.parts[1],g=p.groups[0];delete p.visual_materials;g.supporting_assets=[];g.content_blocks=g.content_blocks.filter(b=>b.kind!=='original_source_image');g.questions.forEach(q=>delete q.visual_binding);
assert.equal(sourceMaterial(unknown,p,g).assets.length,0);
p.supporting_assets=p.supporting_assets.slice(0,1);assert.equal(sourceMaterial(unknown,p,g).assets.length,1);
