import type {Exam,Group,Part} from "./models";

/** Structured is a rendering mode, not evidence that the original pages are absent.
 * The importer retains those pages on the part even when a group's asset list is empty.
 * Never borrow pages from another part or filter originals by optional image metadata.
 */
export function sourceMaterial(exam:Exam,part:Part,group:Group) {
  const direct=[...new Set([
    ...group.supporting_assets,
    ...group.content_blocks.flatMap(block=>block.kind==="original_source_image"?[block.asset_id]:[]),
    ...group.questions.flatMap(question=>question.visual_binding?.asset_ids||[]),
  ])];
  const assets=direct.length?direct:[...new Set(part.supporting_assets)];
  const lines=direct.length?[]:group.content_blocks.flatMap(block=>block.kind==="source_line"&&block.text.trim()?[block]:[]);
  const expectsImage=group.presentation_mode==="image_backed"||group.answer_bank?.options.some(option=>option.visual_reference)
    ||group.questions.some(question=>question.options.some(option=>option.visual_reference)||question.visual_binding?.asset_ids.length);
  const missing=assets.filter(id=>!exam.assets.some(asset=>asset.asset_id===id));
  const unavailable=!!expectsImage&&!assets.length;
  return {assets,lines,missing,unavailable,usingPartPages:!direct.length&&assets.length>0,hasMaterial:!!(assets.length||lines.length||group.answer_bank||unavailable)};
}

export function displayedPart(exam:Exam,current:number,fallback:number) {
  return exam.parts.find(part=>part.groups.some(group=>group.questions.some(question=>question.question_number===current)))
    ||exam.parts.find(part=>part.part_number===fallback)||exam.parts[0]!;
}
