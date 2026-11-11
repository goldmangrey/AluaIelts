"""Augment the original inventory with read-only source/edition diagnostics."""
import json,re,hashlib
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/reading-content-fidelity-v1';BASE=ROOT/'backend/app/content/reading_v1'
rows=json.loads((OUT/'source-inventory.json').read_text());manifest=json.loads((BASE/'manifest.json').read_text())
for row in rows:
 book=int(re.search(r'(\d+)\.pdf',row['path'])[1]);pages=set()
 for entry in manifest['exams']:
  if entry['source_book']!=book:continue
  exam=json.loads((BASE/entry['exam_path']).read_text());pages.update(n for p in exam['passages'] for n in p['source_reference']['pdf_pages'])
 types={};watermarks=[];printed=[]
 with fitz.open(ROOT/row['path']) as doc:
  for n in sorted(pages):
   page=doc[n-1];english=len(re.findall(r'[A-Za-z]',page.get_text()));area=page.rect.width*page.rect.height;coverage=0
   for image in page.get_images():
    for rect in page.get_image_rects(image[0]):coverage=max(coverage,rect.get_area()/area)
   kind='SCANNED_WITH_WATERMARK_TEXT_ONLY' if coverage>.8 and english<250 else 'MIXED_SEARCHABLE_SCAN' if coverage>.8 else 'DIGITAL_TEXT_OR_RETYPE' if english>250 else 'IMAGE_OR_LOW_TEXT_MIXED'
   types[kind]=types.get(kind,0)+1
   cached=Path('/tmp/alua-reading-fidelity-work/ocr')/row['sha256']/f'{n:03}-psm3.json'
   if cached.exists():
    d=json.loads(cached.read_text())
    if re.search(r'hujiang|topsage|www\.|http|QQ',d['text'],re.I):watermarks.append(n)
    nums=[l['text'].strip() for l in d['lines'] if l['bbox'][1]>page.rect.height*.9 and re.fullmatch(r'\d{1,3}',l['text'].strip())]
    printed.append({'physical_page':n,'printed_page_ocr_candidates':nums,'status':'NOT_VISUALLY_ADJUDICATED'})
 row['declared_reading_physical_pages']=sorted(pages);row['reading_page_types']=types;row['watermark_recognized_pages']=watermarks;row['printed_page_screening']=printed
 row['source_edition_status']='LOCAL_REFERENCE_HASH_MATCHES_GENERATOR_MANIFEST; attachment/publisher-edition identity not independently authenticated'
 if book in [4,9,20]:row['source_edition_warning']='Native-text/Word-generated third-party PDF. It may be a reformatted derivative; original typeset edition equivalence is unproven. Metadata alone is not proof of a wording defect.'
 if book==9:row['source_edition_warning']+=' Visual page 78 itself contains "switchover toll place" and secondary unnumbered gaps; exact original content is unresolved.'
 if book==14:row['source_edition_warning']='ABBYY searchable scan. Embedded OCR text is not independent authoritative wording; use the visible original page image.'
checks=[]
for name,expected in manifest['sources'].items():
 p=ROOT/name;actual=hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None;checks.append({'path':name,'manifest_sha256':expected,'actual_sha256':actual,'matches':actual==expected})
(OUT/'source-inventory.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
(OUT/'checkpoints/source-integrity.json').write_text(json.dumps({'files':checks,'all_match':all(r['matches'] for r in checks)},indent=2))
print('profiled',len(rows),'PDFs;',len(checks),'manifest source hashes checked')
