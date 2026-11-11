"""Read-only, bounded, hash-keyed independent PDF recognition. No dataset imports/writes."""
from __future__ import annotations
import argparse,csv,hashlib,io,json,os,re,subprocess,tempfile
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'docs/reading-content-fidelity-v1'
WORK=Path('/tmp/alua-reading-fidelity-work')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def atomic(p,value):
 p.parent.mkdir(parents=True,exist_ok=True); q=p.with_suffix(p.suffix+'.partial');q.write_text(json.dumps(value,ensure_ascii=False,indent=2));q.replace(p)
def task(pdf,page,psm=3):
 token=sha(pdf);dest=WORK/'ocr'/token/f'{page:03}-psm{psm}.json'
 if dest.exists():return json.loads(dest.read_text())
 with fitz.open(pdf) as doc:
  p=doc[page-1];pix=p.get_pixmap(matrix=fitz.Matrix(2.5,2.5));size=[p.rect.width,p.rect.height];embedded=p.get_text('text'); words=p.get_text('words')
  with tempfile.TemporaryDirectory(prefix='alua-fidelity-page-') as temp:
   image=Path(temp)/'page.png';pix.save(image)
   r=subprocess.run(['tesseract',str(image),'stdout','-l','eng','--psm',str(psm),'tsv'],capture_output=True,text=True,check=True,timeout=120,env={**os.environ,'OMP_THREAD_LIMIT':'1'})
 result=[];groups={}
 for row in csv.DictReader(io.StringIO(r.stdout),delimiter='\t',quoting=csv.QUOTE_NONE):
  if row.get('level')!='5' or not row.get('text','').strip():continue
  key=tuple(row[x] for x in ['block_num','par_num','line_num']);x,y,w,h=[int(row[z])/2.5 for z in ['left','top','width','height']]
  groups.setdefault(key,[]).append({'text':row['text'],'bbox':[x,y,x+w,y+h],'confidence':float(row['conf'])})
 offset=0
 for words_in_line in groups.values():
  text=' '.join(w['text'] for w in words_in_line)
  result.append({'text':text,'start':offset,'end':offset+len(text),'bbox':[min(w['bbox'][0] for w in words_in_line),min(w['bbox'][1] for w in words_in_line),max(w['bbox'][2] for w in words_in_line),max(w['bbox'][3] for w in words_in_line)],'words':words_in_line});offset+=len(text)+1
 data={'pdf':str(pdf.relative_to(ROOT)),'pdf_sha256':token,'physical_page':page,'psm':psm,'scale':2.5,'page_size':size,'embedded_text':embedded,'embedded_words':words,'text':'\n'.join(x['text'] for x in result),'lines':result}
 atomic(dest,data);return data

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--workers',type=int,default=3);ap.add_argument('--book',type=int);ap.add_argument('--psm',type=int,default=3);args=ap.parse_args()
 jobs=set();base=ROOT/'backend/app/content/reading_v1';manifest=json.loads((base/'manifest.json').read_text());reviews=json.loads((ROOT/'backend/scripts/reading_dataset/source_reviews.json').read_text())
 for entry in manifest['exams']:
  e=json.loads((base/entry['exam_path']).read_text());book=e['source_book']
  if args.book and book!=args.book:continue
  pdf=ROOT/f'ieltsbooks/Cambridge-IELTS-{book:02}.pdf'
  for p in e['passages']:
   for n in p['source_reference']['pdf_pages']:jobs.add((pdf,n))
  k=json.loads((base/entry['answer_key_path']).read_text())
  for answer in k['answers']:
   for n in answer['source_reference'].get('pdf_pages',[]):jobs.add((pdf,n))
  location=reviews.get('key_page_locations',{}).get(str(book))
  if location:jobs.add((pdf,location[e['test_ordinal']-1]))
 checkpoint=OUT/'checkpoints'/f'recognition-{args.book or "all"}-psm{args.psm}.json'
 done={};errors=[]
 print(f'Independent recognition: {len(jobs)} physical pages, {args.workers} workers, psm {args.psm}',flush=True)
 with ThreadPoolExecutor(max_workers=min(4,max(1,args.workers))) as pool:
  futures={pool.submit(task,p,n,args.psm):(p,n) for p,n in sorted(jobs,key=lambda z:(str(z[0]),z[1]))}
  for f in as_completed(futures):
   p,n=futures[f]
   try:
    d=f.result();done[f'{p.name}:{n}']={'pdf_sha256':d['pdf_sha256'],'physical_page':n,'cache':str(WORK/'ocr'/d['pdf_sha256']/f'{n:03}-psm{args.psm}.json'),'recognition_complete':True}
   except Exception as e:errors.append({'pdf':str(p),'page':n,'error':str(e)})
   atomic(checkpoint,{'total_pages':len(jobs),'completed':len(done),'pages':dict(sorted(done.items())),'errors':errors,'note':'Recognition is not visual verification. No item becomes VERIFIED from OCR alone.'})
   if (len(done)+len(errors))%20==0 or len(done)+len(errors)==len(jobs):print(f'Completed {len(done)}/{len(jobs)}; errors {len(errors)}',flush=True)
if __name__=='__main__':main()
