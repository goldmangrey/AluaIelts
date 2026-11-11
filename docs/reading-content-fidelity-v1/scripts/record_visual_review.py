"""Encode this audit's explicit visual adjudications; never edits source material.
Each finding is backed by a bounded original-PDF crop and exact local PDF SHA-256.
"""
import hashlib,json,re,sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/reading-content-fidelity-v1';BASE=ROOT/'backend/app/content/reading_v1'
sys.path.insert(0,str(Path(__file__).parent));from audit import issue_id,strings,save
previous=json.loads((OUT/'manual-reviews.json').read_text()) if (OUT/'manual-reviews.json').exists() else {'records':{},'findings':[]};records=dict(previous['records']);findings=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def source(book):return ROOT/f'ieltsbooks/Cambridge-IELTS-{book:02}.pdf'
def crop(book,page,rect,label):
 path=OUT/'evidence'/f'c{book:02}-pdf{page:03}-{label}.png'
 with fitz.open(source(book)) as d:d[page-1].get_pixmap(matrix=fitz.Matrix(2,2),clip=fitz.Rect(rect)).save(path)
 return {'reference':str(path.relative_to(OUT)),'source_pdf':str(source(book).relative_to(ROOT)),'pdf_sha256':sha(source(book)),'physical_pdf_page':page,'printed_page':page-({7:4,6:1,16:2,14:0}.get(book,0)),'crop_box_pdf_points':rect,'coordinate_system':'PDF points, top-left','render_scale':2}
def finding(e,owner,cat,tag,excerpt,original,ev,paths,qs=None,severity='HIGH',meaning=True,scoring=True,cause=None):
 p=next((p for p in e['passages'] if owner.startswith(p['id'])),None)
 f={'issue_id':issue_id(owner,cat,tag),'owner_id':owner,'book':e['source_book'],'test':e['source_test_number'],'passage':p['number'] if p else None,'question_group':owner if '-g-' in owner else None,'question_numbers':qs or [],'severity':severity,'category':cat,'tag':tag,'json_paths':paths,'corrupted_text_excerpt':excerpt,'source_confirmed_text_excerpt':original,'physical_pdf_page':ev['physical_pdf_page'],'printed_page':ev['printed_page'],'evidence':[ev],'root_cause':cause or 'Confirmed in original intermediate TXT, then retained by importer; OCR-origin attribution inferred from extraction header, original OCR engine/run unavailable.','meaning_changed':meaning,'possible_scoring_impact':scoring,'recommended_repair':'Re-transcribe the complete source block, recover structure/options, then source-validate and browser-test in a separate repair task.','verification_status':'CORRUPTED','affected_item_ids':[]}
 if qs:f['affected_item_ids']=[q['id'] for p in e['passages'] for g in p['question_groups'] for q in g['questions'] if q['number'] in qs]
 findings.append(f);return f

e=json.loads((BASE/'exams/cambridge_07/test_01.json').read_text());hash7=sha(source(7))
# Every paragraph/block and every Q1–40 was compared across physical pages 22–33.
# Correctness is established by visual review, not inferred from an OCR alignment score.
verified_q={10,11,12,13,28,30,31,32,33,35,36}
qpages={**{q:24 for q in range(1,10)},**{q:25 for q in range(10,14)},**{q:26 for q in range(14,21)},**{q:29 for q in range(21,27)},**{q:32 for q in range(27,31)},**{q:33 for q in range(31,41)}}
page_refs={24:crop(7,24,[40,45,480,270],'q1-q5-instructions'),25:crop(7,25,[25,45,485,260],'q10-q13-watermark-readable'),26:crop(7,26,[110,220,440,440],'headings-list-v'),29:crop(7,29,[25,45,485,290],'q21-q26'),32:crop(7,32,[40,120,485,410],'mcq-options'),33:crop(7,33,[25,45,485,340],'q31-q36')}
for pi,p in enumerate(e['passages']):
 records[p['id']]={'pdf_sha256':hash7,'classification':'CORRUPTED','source_comparison_complete':True,'source_verification_method':['fresh source OCR alignment','visual inspection of every paragraph and original page layout','original frontend DOM inspection'],'physical_pdf_pages':[22,23] if pi==0 else [27,28] if pi==1 else [30,31],'printed_pages':[18,19] if pi==0 else [23,24] if pi==1 else [26,27],'page_mapping_status':'VISUALLY_CONFIRMED','title_field_status':'VERIFIED','subtitle_field_status':'VERIFIED','paragraph_labels_status':'VERIFIED','evidence':[]}
 for i,b in enumerate(p['content']):
  records[f'{p["id"]}:content:{i}']={'pdf_sha256':hash7,'classification':'VERIFIED','source_comparison_complete':True,'source_verification_method':['whole paragraph OCR-to-JSON alignment','visual source-page comparison'],'physical_pdf_pages':records[p['id']]['physical_pdf_pages'],'printed_pages':records[p['id']]['printed_pages'],'evidence':[]}
 for g in p['question_groups']:
  gr=g['question_numbers'];records[g['id']]={'pdf_sha256':hash7,'classification':'VERIFIED' if gr==[10,11,12,13] else 'CORRUPTED','source_comparison_complete':True,'source_verification_method':['visual original question wording/instructions/options/blank positions','all content-bearing JSON fields','frontend Exam and Review inspection'],'physical_pdf_pages':sorted({qpages[q] for q in gr}),'printed_pages':sorted({qpages[q]-4 for q in gr}),'page_mapping_status':'VISUALLY_CONFIRMED','evidence':[page_refs[qpages[gr[0]]]]}
  for q in g['questions']:
   n=q['number'];records[q['id']]={'pdf_sha256':hash7,'classification':'VERIFIED' if n in verified_q else 'CORRUPTED','source_comparison_complete':True,'source_verification_method':['visual comparison of full original wording, choices, instructions and required context','all content-bearing JSON fields','browser control/context check'],'physical_pdf_pages':[qpages[n]],'printed_pages':[qpages[n]-4],'page_mapping_status':'VISUALLY_CONFIRMED','evidence':[page_refs[qpages[n]]],'key_status':'KEY_VERIFIED','key_source_physical_page':157,'key_source_printed_page':153,'key_binding_status':'KEY_MISMATCH' if n in [16,37,38,39,40] else 'SOURCE_AND_RECORD_COMPATIBLE'}
# Printed key was independently read in full; equality assertions prevent accidental paraphrase.
expected=['B','A','A','E','D','phantom','echoes/obstacles','depth','submarines','natural selection','radio waves/echoes','mathematical theories','zoologist','xi','vii','v','i','ix','ii','x','NO','YES','NOT GIVEN','NO','YES','NOT GIVEN','D','A','B','C','FALSE','FALSE','TRUE','NOT GIVEN','NOT GIVEN','TRUE','F','H','K','G']
k=json.loads((BASE/'answer_keys/cambridge_07/test_01.json').read_text());assert [a['canonical_answer'] for a in k['answers']]==expected
keyev=crop(7,157,[25,65,345,340],'reading-key-q1-q40')
for q in records:
 if '-q-' in q:records[q]['key_evidence']=[keyev]
p1,p2,p3=e['passages'];g1,g6,g10=p1['question_groups'];g14,g21=p2['question_groups'];g27,g31,g37=p3['question_groups']
def paths(g,pat):return [f for f,t in strings(g,'$') if re.search(pat,t,re.I)]
# Limited crops establish each confirmed failure, not entire book reproduction.
ev=crop(7,22,[185,150,420,265],'decorative-title')
finding(e,p1['id'],'OCR_ARTIFACT','title-separators','——Let’s / ——— Go / —__— Bats','Let’s Go Bats',ev,['$.passages[0].content[2].text'],severity='MEDIUM',meaning=False,scoring=False)
records[f'{p1["id"]}:content:2']['classification']='CORRUPTED'
ev=crop(7,22,[45,120,485,150],'timing-question-range')
finding(e,p1['id'],'CHANGED_WORDING','range-I-versus-1','Questions I-13','Questions 1–13',ev,['$.passages[0].content[1].text'],severity='LOW',meaning=False,scoring=False)
records[f'{p1["id"]}:content:1']['classification']='CORRUPTED'
ev=crop(7,22,[50,575,485,620],'p1-c-punctuation')
finding(e,p1['id'],'CHANGED_PUNCTUATION','itself-period','the light source itself, However','the light source itself. However',ev,['$.passages[0].content[5].text'],severity='LOW',meaning=False,scoring=False)
records[f'{p1["id"]}:content:5']['classification']='CORRUPTED'
ev=crop(7,23,[40,325,490,390],'p1-e-punctuation')
finding(e,p1['id'],'CHANGED_PUNCTUATION','sonar-period','It is sonar But','It is sonar. But',ev,['$.passages[0].content[8].text'],severity='LOW',meaning=False,scoring=False)
records[f'{p1["id"]}:content:8']['classification']='CORRUPTED'
finding(e,g1['id'],'CHANGED_WORDING','passage-number-glyph','Reading Passage | has five paragraphs','Reading Passage 1 has five paragraphs',page_refs[24],['$.passages[0].question_groups[0].instructions'],list(range(1,6)),severity='LOW',meaning=False,scoring=False)
ev6=crop(7,24,[45,285,490,520],'facial-vision-q6-q9')
finding(e,g6['id'],'OCR_ARTIFACT','facial-vision-leaders','@ 6 ........ eee; 7 ..........:::::ceeeeees; 8 ...........eeee; 9 ..........eseeees','pain from a [6] arm or leg; perceiving [7]; the [8] of the seabed; finding [9]',ev6,paths(g6,r'ceeeee|\.\.\.eeee|@\s*6'),list(range(6,10)))
finding(e,g6['id'],'INCORRECT_BLANKS','no-inline-slots','content_blocks has 0 blank segments for Q6–9','Four numbered blanks occur inside the summary sentences.',ev6,['$.passages[0].question_groups[1].content_blocks'],list(range(6,10)),cause='TRANSFORMATION_CORRUPTION: engine.rich_text recognizes underscore leaders only; dotted/corrupted original OCR leaders survive as text. Renderer then uses standalone fallback rows.')
ev=crop(7,27,[25,45,320,115],'making-every-drop-title')
finding(e,p2['id'],'OCR_ARTIFACT','stylized-title','MAKING SV SiR a / DROP COUNT','MAKING EVERY DROP COUNT',ev,['$.passages[1].content[0].text'],meaning=False,scoring=False,severity='MEDIUM');records[f'{p2["id"]}:content:0']['classification']='CORRUPTED'
ev=crop(7,28,[40,600,220,632],'gallon-footnote')
finding(e,p2['id'],'CHANGED_WORDING','unit-footnote','* 4 Wallan: A BAF litrac','* 1 gallon: 4.546 litres',ev,['$.passages[1].content[10].text'],meaning=True,scoring='POSSIBLE');records[f'{p2["id"]}:content:10']['classification']='CORRUPTED'
finding(e,g14['id'],'WRONG_MISSING_OPTIONS','heading-v-lost','i, ii, iii, iv, vi, vii, viii, ix, x, xi; iv includes "vy Environmental effects"','v Environmental effects (separate from iv)',page_refs[26],['$.passages[1].question_groups[0].options','$.passages[1].question_groups[0].constraints.allowed_values','$.passages[1].question_groups[0].questions[*].constraints.allowed_values'],list(range(14,21)),severity='CRITICAL',cause='Source TXT already misreads v as vy; enrich.options accepts Roman labels, drops v and merges its text into iv. Source image fallback restores the visual list but not the interactive choices.')
finding(e,g14['id'],'MISSING_CONTENT','q20-paragraph-h','Q20 falls back to the entire question group; Q19 includes "M3 Daracranh H"','20 Paragraph H',page_refs[26],['$.passages[1].question_groups[0].questions[5].prompt','$.passages[1].question_groups[0].questions[6].prompt'],[19,20],cause='Source OCR loses number 20 / Paragraph H; per-question parser fallback substitutes the whole group. Original-image fallback mitigates visible prompt loss.')
finding(e,g21['id'],'CHANGED_WORDING','q21-q26-column-order','Q21 prompt="22"; Q23 prompt="24"; several prompts contain the whole group','Q21–26 are six distinct complete statements in source order.',page_refs[29],['$.passages[1].question_groups[1].questions[*].prompt'],list(range(21,27)),cause='Column/line-order corruption exists in intermediate TXT, then numeric-line parser assigns neighbouring numbers as prompts. Original-image fallback mitigates visible text loss.')
finding(e,g27['id'],'CHANGED_WORDING','q27-word-join','aparticular technique','a particular technique',page_refs[32],['$.passages[2].question_groups[0].questions[0].options[1].text'],[27],severity='LOW',meaning=False,scoring=False)
finding(e,g27['id'],'CHANGED_WORDING','q29-word-join','wecan remember','we can remember',page_refs[32],['$.passages[2].question_groups[0].questions[2].options[3].text'],[29],severity='LOW',meaning=False,scoring=False)
finding(e,g31['id'],'CHANGED_WORDING','q34-word-join','Asan indirect benefit','As an indirect benefit',page_refs[33],['$.passages[2].question_groups[1].questions[3].prompt'],[34],severity='LOW',meaning=False,scoring=False)
ev37=crop(7,33,[25,340,490,610],'educating-psyche-q37-q40')
finding(e,g37['id'],'OCR_ARTIFACT','psyche-leaders','ceeeeeeeeeeaeeeeaeeeeees; 38.0.0...; 39 wee; 40 we','37 [blank]; 38 [blank]; 39 [blank]; 40 [blank]',ev37,paths(g37,r'ceeeee|38\.0|39 wee|40 we'),list(range(37,41)))
finding(e,g37['id'],'CHANGED_WORDING','psyche-summary-order','"been 40" and option fragments precede ", the results of most other teachers ..."','Although Lozanov’s method has become quite [39], the results of most other teachers using this method have been [40].',ev37,paths(g37,r'become quite'),list(range(37,41)))
finding(e,g37['id'],'WRONG_MISSING_OPTIONS','psyche-a-k','Shared options []; labels A, B, D, E, G, H, J, K absent from their texts.','A spectacular; B teaching; C lesson; D authoritarian; E unpopular; F ritual; G unspectacular; H placebo; I involved; J appropriate; K well known',ev37,['$.passages[2].question_groups[2].options','$.passages[2].question_groups[2].constraints.allowed_values',*paths(g37,r'spectacular')],list(range(37,41)),severity='CRITICAL')
finding(e,g37['id'],'INCORRECT_BLANKS','psyche-no-inline-slots','0 explicit blank segments; four generic answer rows','Four blanks anchored in the complete summary, before the A–K choice box.',ev37,['$.passages[2].question_groups[2].content_blocks'],list(range(37,41)),cause='TRANSFORMATION_CORRUPTION: underscore-only slot recognizer cannot recover dotted OCR leaders. Source image fallback was not selected for this summary type.')
# Structure-only confirmed defects: page-break continuation is not a new source paragraph.
for p,indices,pages in [(p1,[5,6],[22,23]),(p3,[5,6],[30,31])]:
 ev=crop(7,pages[-1],[40,45,485,100],f'p{p["number"]}-continuation')
 finding(e,p['id'],'STRUCTURAL_RENDERING','page-break-paragraph-split','One source paragraph is split into two JSON paragraph blocks at the PDF page break.','Continuation belongs to the same original paragraph.',ev,[f'$.passages[{p["number"]-1}].content[{i}]' for i in indices],severity='LOW',meaning=False,scoring=False,cause='TRANSFORMATION_CORRUPTION: page-extraction boundaries become blank-line paragraph boundaries; PassagePane renders each block as a separate p element.')
# Title retained as body paragraph causes a second displayed title; PDF has one title.
for p,n in [(p2,27),(p3,30)]:
 ev=crop(7,n,[25,45,430,150],f'p{p["number"]}-single-title')
 finding(e,p['id'],'STRUCTURAL_RENDERING','duplicate-title','Title is an h1 plus a body paragraph (P2 body title is additionally OCR-corrupted).','Single original passage title.',ev,[f'$.passages[{p["number"]-1}].title',f'$.passages[{p["number"]-1}].content[0]'],severity='LOW',meaning=False,scoring=False,cause=('Importer retains the damaged title as a paragraph in addition to the title field.' if p['number']==2 else 'RENDERING_CORRUPTION: heading text EDUCATING PSYCHE differs in case from title Educating Psyche; PassagePane suppresses duplicate headings with case-sensitive comparison only.'))
 records[f'{p3["id"]}:content:0']['classification']='CORRUPTED'
# Source itself says seven despite A–H. Record it as source ambiguity, not extraction corruption.
f=finding(e,g14['id'],'SOURCE_AMBIGUITY','seven-versus-eight','Reading Passage 2 has seven paragraphs, A-H.','The original PDF itself says "seven paragraphs, A–H".',page_refs[26],['$.passages[1].question_groups[0].instructions'],list(range(14,21)),severity='LOW',meaning='SOURCE_EDITORIAL_INCONSISTENCY',scoring=False,cause='Present in the original source; do not silently correct or attribute to OCR.')
f['verification_status']='UNRESOLVED'
# Direct source key versus available UI options; this is NOT a claim the printed key is wrong.
finding(e,next(q['id'] for q in p2['question_groups'][0]['questions'] if q['number']==16),'KEY_OPTION_BINDING','key-v-unselectable','Source key Q16=v, but the actual Exam offers i,ii,iii,iv,vi,...,xi only.','Q16 v; option v Environmental effects.',keyev,['$.passages[1].question_groups[0].options'],[16],severity='CRITICAL',cause='Confirmed source key and browser control inventory disagree because option v was lost during normalization/parsing.')
# Cambridge 6 Test 1: compare the COMPLETE surrounding summary and every A–K entry.
e6=json.loads((BASE/'exams/cambridge_06/test_01.json').read_text());p=e6['passages'][1];g=p['question_groups'][-1];hash6=sha(source(6));ev=crop(6,26,[35,145,485,405],'transport-summary-q23-q26');kev=crop(6,153,[270,120,350,175],'key-q23-q26')
records[g['id']]={'pdf_sha256':hash6,'classification':'CORRUPTED','source_comparison_complete':True,'source_verification_method':['visual full original summary, four blank positions, A–K option mapping and printed key','all JSON fields and browser group inspection'],'physical_pdf_pages':[26],'printed_pages':[25],'page_mapping_status':'VISUALLY_CONFIRMED','evidence':[ev]}
for q,answer in zip(g['questions'],['G','B','C','A']):
 records[q['id']]={'pdf_sha256':hash6,'classification':'CORRUPTED','source_comparison_complete':True,'source_verification_method':['visual full source group and key','all JSON content fields','actual browser rendering'],'physical_pdf_pages':[26],'printed_pages':[25],'page_mapping_status':'VISUALLY_CONFIRMED','evidence':[ev],'key_status':'KEY_VERIFIED','key_source_physical_page':153,'key_source_printed_page':152,'key_evidence':[kev],'key_binding_status':'MISSING_PARSED_OPTIONS'}
 actual=next(a for a in json.loads((BASE/'answer_keys/cambridge_06/test_01.json').read_text())['answers'] if a['number']==q['number']);assert actual['canonical_answer']==answer
finding(e6,g['id'],'OCR_ARTIFACT','reduce-leader','FECUCE 26 ..,.nssssvesersosesereee','reduce [26]',ev,paths(g,r'FECUCE|nssss'),list(range(23,27)))
finding(e6,g['id'],'MISSING_CONTENT','blank-25-number-lost','The introduction of / has meant that bulk cargo ...','The introduction of [25] has meant that bulk cargo ...',ev,paths(g,r'introduction of'),list(range(23,27)))
finding(e6,g['id'],'WRONG_MISSING_OPTIONS','transport-a-k','[]; tariffs components C container ships / output employees F insurance costs ...','A tariffs; B components; C container ships; D output; E employees; F insurance costs; G trade; H freight; I fares; J software; K international standards',ev,['$.passages[1].question_groups[2].options',*paths(g,r'tariffs')],list(range(23,27)),severity='CRITICAL')
finding(e6,g['id'],'INCORRECT_BLANKS','transport-unanchored','0 explicit blank segments; Q25 number missing in content','Four ordered and positioned blanks 23,24,25,26.',ev,['$.passages[1].question_groups[2].content_blocks'],list(range(23,27)),cause='OCR loses dotted leaders/number 25; underscore-only parser does not reconstruct any inline slots; renderer falls back to detached input rows.')
# The original-image fallback itself cuts off Q20 at a fixed 93.5% page-height bound.
ev=crop(7,26,[40,585,245,632],'q20-below-production-crop')
f=finding(e,g14['id'],'MISSING_CONTENT','q20-cropped-out-of-image','Production asset ends at PDF y=611.49; Q20 starts at y=612.4 and is absent.','20 Paragraph H',ev,['$.passages[1].question_groups[0].assets[0].crop_box'],[20],severity='CRITICAL',cause='TRANSFORMATION_CORRUPTION: pdf_support.crop_group clamps the final crop to page height × 0.935, above the final numbered question. Browser image fallback therefore cannot recover Q20.')
from PIL import Image
asset=BASE/g14['assets'][0]['path'];im=Image.open(asset);box=[0,max(0,im.height-230),im.width,im.height];tail=OUT/'evidence/production-c07-q20-missing-tail.png';im.crop(box).save(tail)
f['evidence'].append({'reference':str(tail.relative_to(OUT)),'source_asset':str(asset.relative_to(ROOT)),'source_asset_sha256':sha(asset),'crop_box_pixels':box,'note':'Bottom of the unchanged production fallback image: ends after Q19.'})
# Resolve paths relative to their actual owner group into globally addressable JSON paths.
for f in findings:
 owner=f['owner_id'];exam=e6 if owner.startswith('cambridge-06') else e
 for pi,p in enumerate(exam['passages']):
  for gi,g in enumerate(p['question_groups']):
   if owner==g['id']:f['json_paths']=[f'$.passages[{pi}].question_groups[{gi}]'+x[1:] if x.startswith('$.') and not x.startswith('$.passages') else x for x in f['json_paths']]
# Add short excerpt-to-intermediate provenance, without assuming a particular unavailable OCR model.
for f in findings:
 exam=e6 if f['book']==6 else e;src=exam['source_references'][0]['txt_file'];lines=(ROOT/src).read_text().splitlines();needle=f['corrupted_text_excerpt'].split(';')[0].split(' / ')[0]
 matches=[i+1 for i,line in enumerate(lines) if needle and needle in line]
 f['intermediate_txt']=src;f['intermediate_line_matches']=matches[:12]
# Additional full-group visual comparisons; no extrapolation to the rest of their tests.
for book,test,pn,start,page,rect in [(7,4,3,30,103,[25,45,490,485]),(16,3,2,20,69,[30,295,475,650]),(16,2,2,17,47,[30,50,475,450]),(14,2,2,19,45,[35,70,545,500])]:
 ex=json.loads((BASE/f'exams/cambridge_{book:02}/test_{test:02}.json').read_text());passage=ex['passages'][pn-1];group=next(g for g in passage['question_groups'] if g['question_numbers'][0]==start);hh=sha(source(book));ev=crop(book,page,rect,f't{test}-g{start}-complete-group');nums=group['question_numbers']
 records[group['id']]={'pdf_sha256':hh,'classification':'CORRUPTED','source_comparison_complete':True,'source_verification_method':['visual full original question group and all required context','all content-bearing JSON fields','actual frontend control inventory'],'physical_pdf_pages':[page],'printed_pages':[ev['printed_page']],'page_mapping_status':'VISUALLY_CONFIRMED','evidence':[ev]}
 for q in group['questions']:records[q['id']]={'pdf_sha256':hh,'classification':'CORRUPTED','source_comparison_complete':True,'source_verification_method':['full original group visual comparison including instructions/options/blank positions','all content-bearing JSON fields'],'physical_pdf_pages':[page],'printed_pages':[ev['printed_page']],'page_mapping_status':'VISUALLY_CONFIRMED','evidence':[ev]}
 if book==7:
  finding(ex,group['id'],'OCR_ARTIFACT','noise-experiment-leaders','30 .....0..; 31.0...; 32 ............:ccce; 33.0...; 34 oe.','Five numbered gaps 30–34 in source order; ordinary dotted leaders only.',ev,paths(group,r'31\.0|:ccce'),nums)
  finding(ex,group['id'],'WRONG_MISSING_OPTIONS','noise-a-j','Shared options=[]; final text "a= TOA DADAMS"; all option labels lost.','A no control over; B unexpected; C intense; D the same amount of; E performed better than; F performed at about the same level as; G no; H showed more irritation than; I made more mistakes than; J different types of',ev,['$.options','$.constraints.allowed_values',*paths(group,r'no control over')],nums,severity='CRITICAL')
  finding(ex,group['id'],'INCORRECT_BLANKS','noise-unanchored','0 explicit blank segments','Five inline numbered summary slots.',ev,['$.content_blocks'],nums,cause='Original dotted leaders become corrupted OCR tokens; underscore-only slot parsing leaves the whole summary unanchored.')
 elif book==16 and test==3:
  finding(ex,group['id'],'OCR_ARTIFACT','archaeology-leaders','agaiNst 20. ecssssssseesemeeneeeeeenee 9; MOUNEAINS AN 21 oes; 22 once ON LOWEr','against [20]; mountains and [21] gathered; attacked by [22] on lower ground',ev,paths(group,r'ecssss|MOUNEAINS|ON LOWEr'),nums)
  finding(ex,group['id'],'INVENTED_OPTIONS','article-a-parsed-as-option','One option A="team of archaeologists have been working ..."; allowed_values=["A"]','The source has a normal sentence beginning "A team of archaeologists...", not an A-labelled option list.',ev,['$.options','$.constraints.allowed_values'],nums,severity='CRITICAL',cause='TRANSFORMATION_CORRUPTION: capital A at the beginning of ordinary summary prose is accepted by the generic option parser and injected into answer constraints.')
  finding(ex,group['id'],'WRONG_INPUT_TYPE','word-answer-becomes-A','Q20–22 answer_input_type=single_select; only option A is selectable.','Choose ONE WORD ONLY from the passage for each answer.',ev,['$.questions[*].answer_input_type','$.questions[*].constraints.allowed_values'],nums,severity='CRITICAL',cause='False option A changes all three answer controls from text completion into single_select. Printed source does not contain such choices.')
  finding(ex,group['id'],'INCORRECT_BLANKS','archaeology-unanchored','0 explicit blank segments','Three numbered and positioned word blanks 20,21,22.',ev,['$.content_blocks'],nums)
 elif book==16:
  finding(ex,group['id'],'OCR_ARTIFACT','microbes-summary','t0 17 occ «ANd; On 18 wesscscmcaresneacceneane s; POOF 19 uu... .sssesssssee » OUP; FOCUS ON 20 ______ eee','lead to [17]. And; based on [18].; Our poor [19], our overuse ...; focus on [20] are upsetting...',ev,paths(group,r'wessc|POOF|sssess'),nums)
  finding(ex,group['id'],'WRONG_MISSING_OPTIONS','microbes-option-c','B="partnership C_ destruction"; parsed choices omit C.','B partnership; C destruction (separate labelled options).',ev,['$.options','$.constraints.allowed_values'],nums,severity='HIGH',cause='Source TXT mixes the option C label with an underscore. Generic option parsing merges C into B rather than preserving the source 3-column A–H box.')
  finding(ex,group['id'],'INCORRECT_BLANKS','microbes-only-one-slot','Only blank 20 is represented; 17,18,19 remain detached fallback fields.','Four numbered inline gaps 17,18,19,20.',ev,['$.content_blocks'],nums)
 else:
  finding(ex,group['id'],'CHANGED_WORDING','hospital-word-splits','comi ng from patie nts sufferi ng','coming from patients suffering',ev,paths(group,r'comi ng|patie nts|sufferi ng'),nums,severity='MEDIUM',meaning=False,scoring='POSSIBLE',cause='The intermediate TXT already contains within-word OCR/text-layer spacing; importer preserves it in instructions/content blocks and repeated prompts.')
  finding(ex,group['id'],'CHANGED_PUNCTUATION','hospital-sentence-period','known as 25__________ / These were blamed','known as [25]. These were blamed',ev,paths(group,r'known as'),nums,severity='LOW',meaning=False,scoring=False)
 # Resolve these additional relative group paths immediately.
 for f in findings:
  if f['owner_id']==group['id']:
   gi=passage['question_groups'].index(group);f['json_paths']=[f'$.passages[{pn-1}].question_groups[{gi}]'+path[1:] if path.startswith('$.') and not path.startswith('$.passages') else path for path in f['json_paths']]
# Clean-looking C07 T4 matching group was also fully compared, not merely scanned for noise.
ex=json.loads((BASE/'exams/cambridge_07/test_04.json').read_text());group=ex['passages'][2]['question_groups'][-1];ev=crop(7,104,[40,45,490,470],'t4-q35-q40-and-researchers')
for obj in [group,*group['questions']]:records[obj['id']]={'pdf_sha256':hash7,'classification':'VERIFIED','source_comparison_complete':True,'source_verification_method':['visual complete source wording and A–E researcher list including reuse rule','all JSON fields; repeated option appendix intentionally represented','browser rendering'],'physical_pdf_pages':[104],'printed_pages':[100],'page_mapping_status':'VISUALLY_CONFIRMED','evidence':[ev]}
# Source ambiguity: this local Word-generated derivative itself contains dubious wording/blank layout.
ex=json.loads((BASE/'exams/cambridge_09/test_03.json').read_text());group=ex['passages'][2]['question_groups'][1] if False else next(g for g in ex['passages'][2]['question_groups'] if g['question_numbers'][0]==33);ev=crop(9,78,[60,270,550,600],'voyager-derivative-ambiguity');ev['printed_page']=None
for obj in [group,*group['questions']]:records[obj['id']]={'pdf_sha256':sha(source(9)),'classification':'UNRESOLVED','source_comparison_complete':False,'local_reference_comparison_complete':True,'source_verification_method':['visual local PDF comparison','metadata/edition provenance inspection'],'physical_pdf_pages':[78],'printed_pages':None,'page_mapping_status':'LOCAL_DERIVATIVE_ONLY','evidence':[ev],'unresolved_reason':'Local source is a Word-generated, reformatted PDF; itself prints "switchover toll place" and secondary unnumbered gaps. An authenticated original Cambridge facsimile is needed to establish exact wording/blank layout.'}
f=finding(ex,group['id'],'SOURCE_AMBIGUITY','voyager-local-source','switchover toll place; secondary unnumbered gaps beside Q33 and Q35','Local PDF repeats these forms; exact original Cambridge wording is not established.',ev,['$.passages[2].question_groups[1].instructions'],group['question_numbers'],severity='HIGH',meaning='UNKNOWN',scoring='POSSIBLE',cause='Present in local native-text Word-generated reference PDF; cannot attribute to the JSON importer or silently infer replacement words.')
f['verification_status']='UNRESOLVED'
# Correct the evidence pointers for the required C07 summary regressions.
for gid,ev,nums in [(g6['id'],ev6,list(range(6,10))),(g37['id'],ev37,list(range(37,41)))]:
 records[gid]['evidence']=[ev]
 for n in nums:
  qid=next(q['id'] for p in e['passages'] for g in p['question_groups'] for q in g['questions'] if q['number']==n);records[qid]['evidence']=[ev]
# Finish provenance for newly appended findings.
for f in findings:
 if 'intermediate_txt' not in f:
  ex=json.loads((BASE/f'exams/cambridge_{f["book"]:02}/test_{f["test"]:02}.json').read_text());src=ex['source_references'][0]['txt_file'];f['intermediate_txt']=src;f['intermediate_line_matches']=[]
findings=list({f['issue_id']:f for f in [*previous['findings'],*findings]}.values())
for identifier, reviewed in records.items():
 if reviewed.get('source_comparison_complete') and not reviewed.get('evidence'):
  book=int(identifier.split('-')[1]);pages=reviewed.get('physical_pdf_pages',[]);printed=reviewed.get('printed_pages',[])
  reviewed['evidence']=[{'kind':'SOURCE_PAGE_REFERENCE','reference':'../../'+str(source(book).relative_to(ROOT)),'source_pdf':str(source(book).relative_to(ROOT)),'pdf_sha256':reviewed['pdf_sha256'],'physical_pdf_page':page,'printed_page':printed[i] if i<len(printed) else None,'note':'Full page visually compared; no complete passage reproduction is bundled.'} for i,page in enumerate(pages)]
save(OUT/'manual-reviews.json',{'method':'Explicit visual adjudication of C07 T1 physical PDF pages 22–33 and 157; complete C06 T1 Q23–26 group at page 26 and keys at 153. Other items not certified.','records':records,'findings':findings})
# The exact named attachment is absent; identical local filename copies do not prove attachment identity.
save(OUT/'attachment-provenance.json',{'requested_attachment_name':'Cambridge-IELTS-07(1).pdf','attachment_sha256_available':False,'attachment_identity':'UNRESOLVED','local_reference':str(source(7).relative_to(ROOT)),'local_sha256':hash7,'manifest_source_hash_matches':True,'same_hash_local_copies':['/Users/yeskendir/Desktop/ieltsbooks/Cambridge-IELTS-07.pdf','/Users/yeskendir/Downloads/Cambridge-IELTS-07.pdf'],'different_hash_artifact':{'path':'/tmp/alua-final-source-release/c07.pdf','sha256':sha(Path('/tmp/alua-final-source-release/c07.pdf')),'pages':129,'used_as_reference':False},'missing_evidence':'Bytes or SHA-256 of the exact conversation attachment are not exposed in this session. No equivalence is assumed.'})
print(len(records),'explicit visual records;',len(findings),'distinct adjudicated findings')
