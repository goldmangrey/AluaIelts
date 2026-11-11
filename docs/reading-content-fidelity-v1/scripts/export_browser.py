"""Export existing public projections for disposable browser inspection; no DB access."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'backend'))
from app.modules.reading.catalog import ReadingCatalog
from app.modules.reading.grading import result_for
catalog=ReadingCatalog();rows={};assets={}
for entry in catalog.manifest['exams']:
 eid=entry['id'];e=catalog.exams[eid];k=catalog.keys[eid]
 result=result_for({'exam':e,'key':k,'metadata':catalog.entries[eid]},{},'full_exam',None,0,{})
 result.update(attempt_id='11111111-2222-4333-8444-555555555555',completion_reason='submitted')
 rows[eid]={'exam':catalog.public_exam(e),'result':result}
for eid in rows:
 for p in catalog.exams[eid]['passages']:
  for g in p['question_groups']:
   for a in g['assets']:assets[a['id']]=str(catalog.path(a['path']))
path=Path('/tmp/alua-reading-fidelity-work/browser-data.json');path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps({'exams':rows,'assets':assets}));print(len(rows),'tests exported read-only',flush=True)
