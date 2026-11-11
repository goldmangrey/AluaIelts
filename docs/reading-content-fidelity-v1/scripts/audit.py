"""Resumable forensic inventory/comparison/report. NEVER imports the dataset generator.
No heuristic, recognition score or browser success can set VERIFIED.
Only explicit hash-bound visual-review records may do that.
"""
from __future__ import annotations
import argparse,collections,csv,difflib,hashlib,html,json,re,sys
from pathlib import Path
from rapidfuzz.fuzz import partial_ratio_alignment
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/reading-content-fidelity-v1';BASE=ROOT/'backend/app/content/reading_v1';WORK=Path('/tmp/alua-reading-fidelity-work')
STATES=['VERIFIED','CORRUPTED','UNRESOLVED','BLOCKED','NOT_AUDITED']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p,default=None):return json.loads(p.read_text()) if p.exists() else default
def save(p,obj):
 p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix(p.suffix+'.partial');t.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True));t.replace(p)
def norm(s):return ' '.join(s.split())
def strings(obj,path='$'):
 if isinstance(obj,str):yield path,obj
 elif isinstance(obj,list):
  for i,v in enumerate(obj):yield from strings(v,f'{path}[{i}]')
 elif isinstance(obj,dict):
  for k,v in obj.items():
   if k not in {'id','question_id','group_id','source_reference','assets','verification','source_verified','source_pages','question_numbers','number','type','representation','answer_input_type','normalization_rules'}:yield from strings(v,f'{path}.{k}')
def content_fields(obj,path):
 return [(p,s) for p,s in strings(obj,path) if any(x in p for x in ['.content[','.title','.subtitle','.instructions','.content_blocks[','.prompt','.options['])]
def issue_id(owner,category,tag=''):return 'RCF1-'+hashlib.sha256(f'{owner}|{category}|{tag}'.encode()).hexdigest()[:12].upper()
def token_diff(target,source,page):
 t=norm(target);s=norm(source)
 if len(t)<18 or not s:return None
 # Compare full fields, including clean-looking text. The alignment score is not a fidelity percentage.
 a=partial_ratio_alignment(t,s);span=s[a.dest_start:a.dest_end];ta=list(re.finditer(r'\w+|[^\w\s]',t));sb=list(re.finditer(r'\w+|[^\w\s]',span))
 op=[]
 for tag,i,j,u,v in difflib.SequenceMatcher(None,[x.group() for x in ta],[x.group() for x in sb],autojunk=False).get_opcodes():
  if tag=='equal':continue
  ts=[ta[i].start() if i<len(ta) else len(t),ta[j-1].end() if j else 0];ss=[a.dest_start+(sb[u].start() if u<len(sb) else len(span)),a.dest_start+(sb[v-1].end() if v else 0)]
  op.append({'operation':tag,'json_normalized_offsets':ts,'source_normalized_offsets':ss,'json_token_change':' '.join(x.group() for x in ta[i:j]),'recognition_token_change':' '.join(x.group() for x in sb[u:v]),'json_excerpt':t[max(0,ts[0]-30):min(len(t),max(ts[1],ts[0])+30)][:180],'source_excerpt':s[max(0,ss[0]-30):min(len(s),max(ss[1],ss[0])+30)][:180]})
 return {'physical_page':page,'alignment_score_internal':round(a.score,3),'source_span_normalized':[a.dest_start,a.dest_end],'differences':op,'status':'RECOGNITION_COMPARISON_ONLY','normalization':'whitespace/line wrapping only; punctuation, letters and digits retained'}

PATTERNS={
 'OCR_LEADER_NOISE':re.compile(r'\b\w*(?:e{4,}|s{4,})\w*|[.·:,]{3,}\s*[A-Za-z]{2,}|\d{1,2}\.0\.0[.]|FECUCE',re.I),
 'WATERMARK_CONTAMINATION':re.compile(r'https?://|www\.|hujiang|topsage|QQ\s*[:：]|[\u4e00-\u9fff]{2,}',re.I),
 'DECORATIVE_PUNCTUATION':re.compile(r'(?:[—]{2,}[^\n]{0,20}){2,}|[=~]{2,}\s*[A-Za-z]'),
 'SUSPICIOUS_WORD_JOIN':re.compile(r'\b(?:Asan|aparticular|wecan|them\.The|inafew)\b'),
}
COMPLETION={'summary_completion','sentence_completion','note_completion','table_completion','flow_chart_completion','diagram_labelling'}
OPTION_TYPES={'matching_headings','matching_features','matching_sentence_endings','multiple_choice_single','multiple_choice_multiple'}

def main():
 manifest=load(BASE/'manifest.json');invent=load(OUT/'source-inventory.json',[]);pdfs={r['path']:r for r in invent};manual=load(OUT/'manual-reviews.json',{'records':{},'findings':[]});reviews=manual['records'];findings=list(manual['findings']);candidates=[];tests=[];type_counts=collections.Counter();ocr_cache={};diff_index={}
 browser=load(OUT/'browser-observations.json',{})
 def recognize(pdf,pages):
  result=[]
  token=pdfs[pdf]['sha256'] if pdf in pdfs else None
  for n in pages:
   key=(token,n)
   if key not in ocr_cache:ocr_cache[key]=load(WORK/'ocr'/str(token)/f'{n:03}-psm3.json')
   if ocr_cache[key]:result.append(ocr_cache[key])
  return result
 def candidate(owner,cat,paths,excerpt,detail,severity='MEDIUM',tag='',recognition=None):
  candidates.append({'issue_id':issue_id(owner,cat,tag),'owner_id':owner,'severity':severity,'category':cat,'json_paths':paths,'corrupted_text_excerpt':excerpt[:220],'source_confirmed_text_excerpt':None,'recognition_source_excerpt':recognition,'verification_status':'UNRESOLVED','detail':detail,'meaning_changed':'UNKNOWN','possible_scoring_impact':'UNKNOWN','root_cause':'Requires original-page comparison; detector is not evidence of corruption.','recommended_repair':'Inspect full source group/page before proposing a repair.'})
 def record(identifier,kind,e,p=None,g=None,q=None,path='$'):
  src=(q or g or p or e).get('source_reference') or (p or {}).get('source_reference') or e['source_references'][0];pdf=src['pdf_file'];pages=src.get('pdf_pages',[])
  r={'id':identifier,'kind':kind,'book':e['source_book'],'test':e['source_test_number'],'test_ordinal':e['test_ordinal'],'passage':p['number'] if p else None,'question_group':g['id'] if g else None,'question_number':q['number'] if q else None,'source_pdf':pdf,'pdf_sha256':pdfs.get(pdf,{}).get('sha256'),'physical_pdf_pages':pages,'printed_pages':None,'json_field_path':path,'source_verification_method':['inventory','full-field automated detector'],'classification':'NOT_AUDITED','source_comparison_complete':False,'evidence':[],'issues':[],'key_status':'KEY_UNVERIFIED' if q else None}
  ds=recognize(pdf,pages);r['recognition_pages_complete']=len(ds);r['recognition_pages_expected']=len(set(pages));r['page_mapping_status']='DECLARED_JSON_PROVENANCE_ONLY'
  if not (ROOT/pdf).exists():r.update(classification='BLOCKED',blocker='Original PDF unavailable')
  if identifier in reviews:
   m=reviews[identifier]
   if m['pdf_sha256']!=r['pdf_sha256']:raise ValueError('Stale manual evidence '+identifier)
   r.update(m)
  if q:
   entry=next(x for x in manifest['exams'] if x['id']==e['id']);key=load(BASE/entry['answer_key_path']);answer=next((a for a in key['answers'] if a['number']==q['number']),None)
   key_rows=[]
   for kd in recognize(pdf,answer['source_reference'].get('pdf_pages',[]) if answer else []):
    for line in kd['lines']:
     if re.match(rf'^\s*{q["number"]}\s+\S',line['text']):key_rows.append({'physical_page':kd['physical_page'],'excerpt':line['text'][:110],'bbox':line['bbox']})
   r['key_recognition_candidates']=key_rows
   r['key_recognition_status']='ROW_CANDIDATES_NOT_VISUALLY_VERIFIED' if key_rows else 'NO_UNAMBIGUOUS_ROW_RECOGNIZED'
   r['key_record_present']=answer is not None
   r['key_json_question_id_matches']=bool(answer and answer['question_id']==q['id'])
   options=q['options'] or g['options'];allowed=[o['label'] for o in options] or q['constraints']['allowed_values'] or g['constraints']['allowed_values']
   r['key_binding_status']='KEY_UNVERIFIED';r['key_pdf_pages']=answer['source_reference'].get('pdf_pages',[]) if answer else []
   if answer and allowed and answer['canonical_answer'] not in allowed and all(v not in allowed for v in answer['accepted_answers']):
    r['key_binding_status']='KEY_MISMATCH';candidate(identifier,'KEY_OPTION_BINDING',[path+'.options',path+'.constraints.allowed_values'],answer['canonical_answer'],'Key letter is unavailable among parsed choices; source key still needs independent verification.','HIGH')
   elif answer:r['key_binding_status']='INTERNALLY_COMPATIBLE_NOT_SOURCE_VERIFIED'
   if q['id'] in reviews:r.update({k:v for k,v in reviews[q['id']].items() if k.startswith('key_')})
  fields=content_fields(q or g or p or e,path) if kind not in {'test'} else []
  if kind=='passage':fields=[(x,t) for x,t in fields if '.question_groups[' not in x]
  if kind=='group':fields=[(x,t) for x,t in fields if '.questions[' not in x]
  evidence=[]
  for fp,text in fields:
   matches=[token_diff(text,d['text'],d['physical_page']) for d in ds];matches=[x for x in matches if x]
   if matches:
    best=max(matches,key=lambda z:z['alignment_score_internal']);evidence.append({'json_path':fp,**best})
  if identifier not in reviews:
   owner=g['id'] if q and g else identifier
   for comparison in evidence:
    if comparison['alignment_score_internal']<92 or len(comparison['differences'])>14:continue
    for delta in comparison['differences']:
     left=delta.get('json_token_change','');right=delta.get('recognition_token_change','')
     if delta['operation']=='equal' or not re.search(r'[A-Za-z]{3}',left+right) or max(len(left),len(right))>95:continue
     # An independent OCR disagreement is a queue entry, never confirmed wording.
     candidate(owner,'SOURCE_WORD_DIFFERENCE',[comparison['json_path']],delta['json_excerpt'],f"Recognition disagreement on physical page {comparison['physical_page']}; normalized source offsets {delta['source_normalized_offsets']}. Visual adjudication required.",tag=left+'|'+right,recognition=delta['source_excerpt'])
  r['automated_fields_compared']=len(evidence);r['automated_field_count']=len(fields)
  r['recognition_comparison_reference']=f'checkpoints/diffs-{e["source_book"]:02}.json#{identifier}'
  diff_index.setdefault(e['source_book'],{})[identifier]=evidence
  r['rendering_status']='NOT_AUDITED'
  b=browser.get(e['id'])
  if b:
   r['rendering_status']='BROWSER_EXAM_AND_REVIEW_INSPECTED_NOT_SOURCE_VERIFIED' if len(b.get('modes',{}))==2 else 'BROWSER_INCOMPLETE'
   if q:
    r['browser_observations']={mode:next((v for pp in d['passages'] for v in pp['questions'] if v['number']==q['number']),None) for mode,d in b.get('modes',{}).items()}
  return r
 for entry in manifest['exams']:
  e=load(BASE/entry['exam_path']);t=record(e['id'],'test',e);t['exam_json']=str((BASE/entry['exam_path']).relative_to(ROOT));t['exam_sha256']=sha(BASE/entry['exam_path']);t['key_sha256']=sha(BASE/entry['answer_key_path']);t['historical_content_status_current_file']=e['content_status'];t['passages']=[];t['questions_records_examined']=0
  for pi,p in enumerate(e['passages']):
   pp=f'$.passages[{pi}]';pr=record(p['id'],'passage',e,p,path=pp);pr['title']=p['title'];pr['paragraphs']=[];pr['groups']=[]
   for i,block in enumerate(p['content']):
    bid=f'{p["id"]}:content:{i}';br={**{k:pr[k] for k in ['book','test','test_ordinal','passage','source_pdf','pdf_sha256','physical_pdf_pages','printed_pages']},'id':bid,'kind':'paragraph' if block['type']=='paragraph' else 'heading','json_field_path':f'{pp}.content[{i}]','label':block.get('label'),'classification':'NOT_AUDITED','source_comparison_complete':False,'evidence':[]}
    if bid in reviews:br.update(reviews[bid])
    pr['paragraphs'].append(br)
   for gi,g in enumerate(p['question_groups']):
    gp=f'{pp}.question_groups[{gi}]';gr=record(g['id'],'group',e,p,g,path=gp);gr['question_type']=g['type'];gr['question_numbers']=g['question_numbers'];gr['representation']=g['representation'];gr['questions']=[];gr['type_specific_checks']=[];type_counts[g['type']]+=len(g['questions'])
    allfields=content_fields(g,gp)
    for cat,pat in PATTERNS.items():
     matches=[(fp,m.group()) for fp,text in allfields for m in pat.finditer(text)]
     if matches:candidate(g['id'],cat,sorted(set(x[0] for x in matches)),' | '.join(dict.fromkeys(x[1] for x in matches)),f'{len(matches)} field occurrences; repeated representations deduplicated by group/failure family.')
    gt=g['type'];options=g['options'];labels=[o['label'] for o in options];blank_numbers=[int(m.group(1)) for m in re.finditer(r'"type": "blank", "number": (\d+)',json.dumps(g['content_blocks']))]
    if g['assets']:
     omissions=[]
     for d in recognize(pr['source_pdf'],sorted({a['pdf_page'] for a in g['assets']})):
      boxes=[a['crop_box'] for a in g['assets'] if a['pdf_page']==d['physical_page']]
      for line in d['lines']:
       m=re.match(r'^(\d{1,2})(?:[.)]?\s+[A-Za-z]|\s*$)',line['text'])
       if not m or int(m[1]) not in g['question_numbers'] or line['bbox'][1]>=d['page_size'][1]*.97:continue
       x0,y0,x1,y1=line['bbox']
       if not any(b[0]<=x0+3 and b[1]<=y0+2 and b[2]>=x1-3 and b[3]>=y1-2 for b in boxes):omissions.append({'question':int(m[1]),'physical_page':d['physical_page'],'bbox':line['bbox'],'ocr_excerpt':line['text']})
     gr['asset_crop_source_screening']=omissions
     if omissions:candidate(g['id'],'SOURCE_CROP_CUTOFF',[gp+'.assets'],str(omissions)[:200],'Source-recognized question label lies outside every production crop on that page. Inspect original and asset.','HIGH')
    if gt in COMPLETION and g['constraints']['max_words'] is not None and g['options']:
     candidate(g['id'],'WORD_COMPLETION_WITH_OPTIONS',[gp+'.options',gp+'.questions[*].answer_input_type'],str(g['options'])[:140],'Word-limited completion contains a parsed option list; ordinary prose may have been misread as labels.','HIGH')
    if gt in COMPLETION:
     gr['type_specific_checks'].append({'rule':'explicit_blank_positions','expected':g['question_numbers'],'found':blank_numbers,'source_check':'PENDING unless manual evidence below'})
     if not blank_numbers and g['representation']=='structured_text':candidate(g['id'],'UNANCHORED_COMPLETION_BLANKS',[gp+'.content_blocks'],g['instructions'][:120],'Completion has answer records but no explicit blank segments; may be intentionally standalone sentences. Check original positions.','HIGH')
    if gt in OPTION_TYPES or re.search(r'list of words.*[A-Z][–-][A-Z]',g['instructions'],re.I):
     gr['type_specific_checks'].append({'rule':'option_inventory','labels':labels,'per_question_labels':{str(q['number']):[o['label'] for o in q['options']] for q in g['questions']}})
     if gt not in {'multiple_choice_single'} and not options:candidate(g['id'],'MISSING_PARSED_OPTIONS',[gp+'.options'],g['instructions'][:120],'Option-dependent instruction has no parsed shared choice list; original image fallback may or may not supply it.','HIGH')
    if gt in {'true_false_not_given','yes_no_not_given'}:
     expected=['TRUE','FALSE','NOT GIVEN'] if gt=='true_false_not_given' else ['YES','NO','NOT GIVEN'];gr['type_specific_checks'].append({'rule':'truth_vs_writer_claim_labels','expected_labels':expected,'question_labels':[[o['label'] for o in q['options']] for q in g['questions']]})
    if gt=='multiple_choice_multiple':gr['type_specific_checks'].append({'rule':'selection_grouping','selection_count':g['constraints']['selection_count'],'question_numbers':g['question_numbers'],'reuse_allowed':g['constraints']['reuse_allowed']})
    if gt in {'table_completion','flow_chart_completion','diagram_labelling'}:gr['type_specific_checks'].append({'rule':'geometry_and_asset_evidence','assets':[{'id':a['id'],'pdf_page':a.get('pdf_page'),'crop_box':a.get('crop_box'),'sha256_matches':sha(BASE/a['path'])==a['sha256']} for a in g['assets']],'visual_geometry_check':'NOT_AUDITED unless manual evidence below'})
    if gt in {'matching_headings','matching_information','matching_features','matching_sentence_endings'}:gr['type_specific_checks'].append({'rule':'label_order_reuse_and_paragraph_binding','reuse_allowed':g['constraints']['reuse_allowed'],'allowed_values':g['constraints']['allowed_values'],'source_check':'PENDING unless manual evidence below'})
    if gt in {'short_answer','sentence_completion','summary_completion','note_completion','table_completion','flow_chart_completion','diagram_labelling'}:gr['type_specific_checks'].append({'rule':'word_and_numeric_limit','parsed':g['constraints'],'source_check':'PENDING unless manual evidence below'})
    for qi,q in enumerate(g['questions']):
     qr=record(q['id'],'question',e,p,g,q,f'{gp}.questions[{qi}]');gr['questions'].append(qr);t['questions_records_examined']+=1
    pr['groups'].append(gr)
   pfields=[(fp,s) for fp,s in content_fields(p,pp) if '.question_groups[' not in fp]
   for cat,pat in PATTERNS.items():
    matches=[(fp,m.group()) for fp,text in pfields for m in pat.finditer(text)]
    if matches:candidate(p['id'],cat,sorted(set(x[0] for x in matches)),' | '.join(dict.fromkeys(x[1] for x in matches)),'Passage-field detector only; compare original before confirming.')
   duplicates=[f'{pp}.content[{i}].text' for i,b in enumerate(p['content']) if norm(b['text']).casefold()==norm(p['title']).casefold() and b['type']=='paragraph']
   if duplicates:candidate(p['id'],'DUPLICATED_PASSAGE_TITLE',[pp+'.title',*duplicates],p['title'],'Renderer prints title as h1 and paragraph content; source layout must be checked.','LOW')
   t['passages'].append(pr)
  tests.append(t)
  save(OUT/'checkpoints'/f'comparison-{e["id"]}.json',{'exam_sha256':t['exam_sha256'],'pdf_sha256':t['pdf_sha256'],'records_examined':t['questions_records_examined'],'recognition_only':True,'complete_source_comparison':False})
  print(f'Compared fields: {len(tests)}/72 {e["id"]}',flush=True)
 # Join confirmed evidence onto individual records without propagating a group finding into unreviewed wording.
 allrecords=[]
 for t in tests:
  allrecords.append(t)
  for p in t['passages']:
   allrecords.append(p);allrecords+=p['paragraphs']
   for g in p['groups']:allrecords.append(g);allrecords+=g['questions']
 byid={r['id']:r for r in allrecords}
 confirmed_owners={(f['owner_id'],f['category']) for f in findings}
 for c in candidates:
  owner=byid.get(c['owner_id']);c.update({k:owner.get(k) for k in ['book','test','passage','question_group']} if owner else {})
 covered={'OCR_LEADER_NOISE':'OCR_ARTIFACT','DECORATIVE_PUNCTUATION':'OCR_ARTIFACT','SUSPICIOUS_WORD_JOIN':'CHANGED_WORDING','UNANCHORED_COMPLETION_BLANKS':'INCORRECT_BLANKS','MISSING_PARSED_OPTIONS':'WRONG_MISSING_OPTIONS','DUPLICATED_PASSAGE_TITLE':'STRUCTURAL_RENDERING','SOURCE_CROP_CUTOFF':'MISSING_CONTENT','WORD_COMPLETION_WITH_OPTIONS':'INVENTED_OPTIONS'}
 candidates=[c for c in candidates if (c['owner_id'],c['category']) not in confirmed_owners and (c['owner_id'],covered.get(c['category'])) not in confirmed_owners]
 # Multiple equivalent field occurrences are one candidate; preserve every path.
 dedup={}
 for c in candidates:
  if c['issue_id'] in dedup:dedup[c['issue_id']]['json_paths']=sorted(set(dedup[c['issue_id']]['json_paths']+c['json_paths']))
  else:dedup[c['issue_id']]=c
 candidates=sorted(dedup.values(),key=lambda c:c['issue_id'])
 for f in findings:
  f.setdefault('issue_id',issue_id(f['owner_id'],f['category'],f.get('tag','')))
  for owner in [f['owner_id'],*f.get('affected_item_ids',[])]:
   if owner in byid:byid[owner]['issues'].append(f['issue_id'])
 for c in candidates:
  if c['owner_id'] in byid:byid[c['owner_id']].setdefault('candidate_issues',[]).append(c['issue_id'])
 def count(kind):return dict(collections.Counter(r['classification'] for r in allrecords if r['kind']==kind))
 for t in tests:
  qs=[q for p in t['passages'] for g in p['groups'] for q in g['questions']];gs=[g for p in t['passages'] for g in p['groups']]
  t['coverage']={'question_classifications':dict(collections.Counter(q['classification'] for q in qs)),'passage_classifications':dict(collections.Counter(p['classification'] for p in t['passages'])),'group_classifications':dict(collections.Counter(g['classification'] for g in gs)),'questions_examined':len(qs),'source_comparison_complete_questions':sum(q['source_comparison_complete'] for q in qs),'key_verified':sum(q['key_status']=='KEY_VERIFIED' for q in qs),'rendering_status':browser.get(t['id'],{}).get('errors',[])}
  t['classification']='VERIFIED' if all(q['classification']=='VERIFIED' for q in qs) and all(p['classification']=='VERIFIED' for p in t['passages']) else 'CORRUPTED' if any(q['classification']=='CORRUPTED' for q in qs) or any(p['classification']=='CORRUPTED' for p in t['passages']) else 'NOT_AUDITED'
  t['source_comparison_complete']=all(q['source_comparison_complete'] for q in qs) and all(p['source_comparison_complete'] for p in t['passages'])
 coverage={'books_inventoried':len({t['book'] for t in tests}),'tests_inventoried':len(tests),'passages_individually_classified':sum(len(t['passages']) for t in tests),'questions_individually_classified':sum(t['questions_records_examined'] for t in tests),'groups_individually_classified':sum(len(p['groups']) for t in tests for p in t['passages']),'classifications':{k:count(k) for k in ['test','passage','group','question','paragraph','heading']},'tests_full_source_comparison':sum(t['source_comparison_complete'] for t in tests),'tests_fully_source_verified':sum(t['classification']=='VERIFIED' for t in tests),'confirmed_distinct_issues':len(findings),'unconfirmed_candidates':len(candidates),'question_types':dict(type_counts),'browser_tests_inspected':len(browser),'browser_exam_question_records':sum(b.get('modes',{}).get('exam',{}).get('visible_question_records',0) for b in browser.values()),'browser_review_question_records':sum(b.get('modes',{}).get('review',{}).get('visible_question_records',0) for b in browser.values()),'current_exam_file_statuses':dict(collections.Counter(t['historical_content_status_current_file'] for t in tests)),'note':'Inspected/recognized is NOT source-verified. NOT_AUDITED includes every item lacking complete original-source comparison. No correctness percentage is calculated.'}
 assert coverage['tests_inventoried']==72 and coverage['passages_individually_classified']==216 and coverage['questions_individually_classified']==2880
 baseline=load(OUT/'protected-before.json');changed=[p for p,h in baseline.items() if not (ROOT/p).exists() or sha(ROOT/p)!=h];safety={'protected_files_checked':len(baseline),'changed':changed,'production_content_unchanged':not changed}
 report={'audit':'ALUA READING CONTENT FIDELITY V1','completion':'INCOMPLETE_EVIDENCE_COMPARISON','release_decision':'NO-GO','coverage':coverage,'safety':safety,'sources':invent,'attachment_provenance':load(OUT/'attachment-provenance.json',{}),'tests':tests,'confirmed_findings':sorted(findings,key=lambda x:x['issue_id']),'unconfirmed_candidates':candidates,'outstanding_work':'Complete human visual source comparison for every NOT_AUDITED passage, paragraph, question, group and answer key, adjudicate all recognition discrepancies, validate every source crop and page range.'}
 for b,data in diff_index.items():save(OUT/'checkpoints'/f'diffs-{b:02}.json',data)
 save(OUT/'report.json',report);save(OUT/'coverage.json',coverage);save(OUT/'checkpoints'/'safety.json',safety)
 columns=['issue_id','severity','category','book','test','passage','question_group','question_numbers','json_paths','corrupted_text_excerpt','source_confirmed_text_excerpt','physical_pdf_page','printed_page','evidence','root_cause','meaning_changed','possible_scoring_impact','recommended_repair','verification_status']
 with (OUT/'issues.csv').open('w',newline='') as fp:
  writer=csv.DictWriter(fp,fieldnames=columns);writer.writeheader()
  for f in [*report['confirmed_findings'],*candidates]:
   owner=byid.get(f['owner_id'],{});row={**{k:owner.get(k) for k in ['book','test','passage','question_group']},**f};writer.writerow({k:json.dumps(row.get(k),ensure_ascii=False) if isinstance(row.get(k),(dict,list)) else row.get(k) for k in columns})
 print(json.dumps(coverage,ensure_ascii=False,indent=2));print('Protected files changed:',changed)
if __name__=='__main__':main()
