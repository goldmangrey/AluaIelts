import type {Exam,Group,Part,VisualMaterial,SourceSegment} from "./models";
// The same public, content-addressed editorial input drives the offline importer.
// It also repairs rendering of immutable older snapshots without rewriting them.
import reviewedVisuals from "./visual-materials.json";

type Proof={pdf_pages:number[];pdf_sha256?:string;verified:boolean};
type Policy={materials:VisualMaterial[];excluded_asset_ids?:string[];source_fidelity?:{images:Record<string,Proof>;groups?:Record<string,Proof>}};
const policies=reviewedVisuals.parts as Record<string,Policy>;
const intersects=(a:number[],b:number[])=>a[0]!<=b[1]!&&b[0]!<=a[1]!;

export function sourceMaterial(exam:Exam,part:Part,group:Group) {
  const direct=[...new Set([
    ...group.supporting_assets,
    ...group.content_blocks.flatMap(block=>block.kind==="original_source_image"?[block.asset_id]:[]),
    ...group.questions.flatMap(question=>question.visual_binding?.asset_ids||[]),
  ])];
  const policy=policies[`${exam.exam_id}-p${part.part_number}`];
  const owned=new Set([...part.supporting_assets,...direct]);
  const reviewed=new Set(policy?.materials.flatMap(m=>[m.asset_id,...m.alternative_asset_ids])||[]);
  // Unknown historical content keeps its direct references; it must never be
  // mistaken for the current reviewed revision solely because exam_id matches.
  const compatible=policy&&[...owned].every(id=>reviewed.has(id)||policy.excluded_asset_ids?.includes(id));
  const materials=compatible?policy.materials:part.visual_materials;
  const available=new Set(exam.assets.map(asset=>asset.asset_id));
  let assets:string[],usingPartPages=false;
  if(materials) {
    const suitable=materials.filter(m=>intersects(m.question_range,group.question_range))
      .sort((a,b)=>a.display_order-b.display_order||a.question_range[0]!-b.question_range[0]!);
    const matches=(m:VisualMaterial)=>direct.some(id=>id===m.asset_id||m.alternative_asset_ids.includes(id));
    const matching=suitable.filter(matches);
    const chosen=suitable;
    usingPartPages=!matching.length&&chosen.length>0;
    // Prefer the canonical complete material. An older allowlist may contain only
    // its reviewed alternative; retain that compatible reference instead of 404.
    assets=[...new Set(chosen.map(m=>available.has(m.asset_id)?m.asset_id:
      m.alternative_asset_ids.find(id=>available.has(id))||m.asset_id))];
  } else {
    // No range metadata: direct legacy bindings remain valid. A single Part image
    // is unambiguous; never borrow every page from a multi-image Part.
    assets=direct.length?direct:part.supporting_assets.length===1?[part.supporting_assets[0]!]:[];
    usingPartPages=!direct.length&&assets.length>0;
  }
  const unresolved=assets.filter(id=>!available.has(id));
  assets=assets.filter(id=>available.has(id));
  const lines=assets.length&&!unresolved.length?[]:group.content_blocks.flatMap(block=>block.kind==="source_line"&&block.text.trim()?[block]:[]);
  const expectsImage=group.presentation_mode==="image_backed"||group.answer_bank?.options.some(option=>option.visual_reference)
    ||group.questions.some(question=>question.options.some(option=>option.visual_reference)||question.visual_binding?.asset_ids.length);
  const missing=unresolved;
  const unavailable=!!expectsImage&&!assets.length;
  return {assets,lines,missing,unavailable,usingPartPages,hasMaterial:!!(assets.length||lines.length||group.answer_bank||unavailable)};
}

/** Match the source pane to all visible question groups, independently of focus.
 * Keep each group's full context (including instruction/continuation pages).
 * Group resolution remains responsible for ownership and snapshot allowlists.
 */
export function visibleSourceMaterial(exam:Exam,part:Part,groups:readonly Group[]) {
  const contexts=groups.map(group=>sourceMaterial(exam,part,group));
  const ids=[...new Set(contexts.flatMap(context=>context.assets))];
  const policy=policies[`${exam.exam_id}-p${part.part_number}`];
  const known=new Set(policy?.materials.flatMap(m=>[m.asset_id,...m.alternative_asset_ids])||[]);
  const compatible=policy&&ids.every(id=>known.has(id)||policy.excluded_asset_ids?.includes(id));
  const materials=(compatible?policy.materials:part.visual_materials)||[];
  const family=(id:string)=>materials.find(m=>m.asset_id===id||m.alternative_asset_ids.includes(id));
  const canonical=(id:string)=>{
    const material=family(id);
    if(!material)return id;
    // Never introduce an ID that the group resolver did not allow for this snapshot.
    return ids.includes(material.asset_id)?material.asset_id:
      ids.find(candidate=>candidate===material.asset_id||material.alternative_asset_ids.includes(candidate))!;
  };
  const assets=[...new Set(ids.map(canonical))].sort((a,b)=>{
    const left=family(a),right=family(b);
    return (left?.display_order??Infinity)-(right?.display_order??Infinity)
      ||(left?.question_range[0]??Infinity)-(right?.question_range[0]??Infinity)
      ||ids.indexOf(a)-ids.indexOf(b);
  });
  const proof=(asset:string):SourceSegment["provenance"]=>{const p=policy?.source_fidelity?.images[asset];return {pdfPages:p?.pdf_pages||[],pdfSha256:p?.pdf_sha256,verified:p?.verified||false};};
  const segments:SourceSegment[]=assets.map((asset,i)=>({id:`image:${asset}`,part:part.part_number,questionRange:family(asset)?.question_range||part.question_range,order:(family(asset)?.display_order??i+1)*100,kind:"image",assetId:asset,provenance:proof(asset)}));
  const normalize=(s:string)=>s.toLowerCase().replace(/[^\p{L}\p{N}]+/gu,"");
  groups.forEach((group,index)=>{
    const context=contexts[index]!;
    if(!context.lines.length&&!(!context.assets.length&&group.answer_bank))return;
    // Use explicit original-page slots where available, then original group order.
    // Never append every group's text after all images or use the focused group.
    const related=materials.filter(m=>intersects(m.question_range,group.question_range));
    const next=segments.find(segment=>{const owners=groups.filter(g=>contexts[groups.indexOf(g)]!.assets.includes(segment.assetId!));return owners.length&&groups.indexOf(owners[0]!)>index;});
    const order=related.length?Math.min(...related.map(m=>m.display_order))*100:(next?next.order-50+index:((segments.at(-1)?.order||0)+50+index));
    const groupProof=policy?.source_fidelity?.groups?.[group.group_id];
    const provenance={pdfPages:groupProof?.pdf_pages||[],pdfSha256:groupProof?.pdf_sha256,verified:groupProof?.verified||false};
    if(context.lines.length)segments.push({id:`text:${group.group_id}`,part:part.part_number,questionRange:group.question_range,order:order-.1,kind:"text",sourceGroupId:group.group_id,lines:context.lines,instructions:normalize(context.lines.map(l=>l.text).join(" ")).includes(normalize(group.instructions))?undefined:group.instructions,provenance});
    const body=normalize(context.lines.map(l=>l.text).join(" "));
    if(group.answer_bank&&!group.answer_bank.options.every(o=>!!o.text&&body.includes(normalize(o.text))))segments.push({id:`options:${group.group_id}`,part:part.part_number,questionRange:group.question_range,order:order-.05,kind:"options",sourceGroupId:group.group_id,provenance});
  });
  segments.sort((a,b)=>a.order-b.order);
  return {assets,segments,missing:[...new Set(contexts.flatMap(context=>context.missing))],

    unavailable:contexts.some(context=>context.unavailable),
    usingPartPages:contexts.some(context=>context.usingPartPages),
    hasMaterial:contexts.some(context=>context.hasMaterial)};
}

export function displayedPart(exam:Exam,current:number,fallback:number) {
  return exam.parts.find(part=>part.groups.some(group=>group.questions.some(question=>question.question_number===current)))
    ||exam.parts.find(part=>part.part_number===fallback)||exam.parts[0]!;
}
