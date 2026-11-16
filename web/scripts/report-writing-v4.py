"""Separate schema reliability, source alignment, human semantic review and synthetic agreement."""
import argparse
import json
import statistics
import re
from pathlib import Path
from jsonschema import Draft202012Validator

KEYS = dict(task_response='TR', coherence_cohesion='CC', lexical_resource='LR', grammar='GRA')

def report(root, fixtures):
    dataset = {r['id']:r for r in json.loads((fixtures/'dataset.json').read_text())}
    metadata = {r['id']:r for r in json.loads((fixtures/'manifest.json').read_text())['records_metadata']}
    schema = json.loads((root/'schema.json').read_text()); validator = Draft202012Validator(schema)
    rows = [json.loads(p.read_text()) for p in sorted(root.glob('result-*.json'))]
    manual = json.loads((root/'manual-review.json').read_text()) if (root/'manual-review.json').exists() else {}
    errors={k:[] for k in KEYS}; overall=[]; labels=[]; cases=[]; span_hits=0; span_total=0
    for row in rows:
        wire = row.get('wire'); schema_ok = wire is not None and not list(validator.iter_errors(wire))
        source_ok = False
        if schema_ok:
            source = dataset.get(row['id'])
            if row['id'] == 'advertising': source = json.loads((fixtures.parent/'writing-advertising-v2.json').read_text())
            if source:
                candidates = [m.group().strip() for m in re.finditer(r'[^.!?]+(?:[.!?]+|$)', source['essay']) if 3 <= len(m.group().strip().encode('utf-16-le'))//2 <= 1200]
                def resolve(candidate):
                    if not isinstance(candidate,str) or not re.fullmatch(r's(?:0|[1-9]\d*)',candidate): return None
                    index=int(candidate[1:]); return candidates[index] if index<len(candidates) else None
                source_ok = all(resolve(candidate) is not None for criterion in wire['criteria'].values() for candidate in criterion['evidence']) and all(resolve(issue['candidate_id']) is not None and bool(issue['original'].strip()) and resolve(issue['candidate_id']).count(issue['original'])==1 for issue in wire['issues'])
        c = dict(number=row['number'], id=row['id'], schema_valid=schema_ok,exact_source_references_valid=source_ok,evidence_and_contract_valid=row.get('contract')=='PASS', provider_failure=row.get('provider_failure',False), manual_semantics=manual.get(str(row['number']),manual.get(row['id'],{})).get('status','NOT VERIFIED'))
        if row.get('review') and row['id'] in dataset:
            d=dataset[row['id']]; review=row['review']; differences={}
            for criterion in review['criteria']:
                name=criterion['name']; diff=criterion['band']-d['intended_scores'][KEYS[name]];errors[name].append(diff);differences[name]=diff
            mean=sum(c['band'] for c in review['criteria'])/4
            import math
            score=math.floor(mean*2+.5)/2;overall.append(score-d['intended_overall']);labels.append(row['id'])
            c.update(split=metadata[row['id']]['split'], synthetic_differences=differences, predicted_task2_estimate=score, synthetic_overall=d['intended_overall'])
            # Matching annotated spans is not proof of correct linguistic diagnosis.
            for error in d.get('error_list',[]):
                quote=error.get('quote','')
                if quote and quote in d['essay']:
                    span_total+=1
                    if any(quote in issue['quote'] or issue['quote'] in quote for issue in review['issues']):span_hits+=1
        cases.append(c)
    def metrics(values):
        return dict(n=len(values),mae=statistics.mean(map(abs,values)) if values else None,bias=statistics.mean(values) if values else None,within_05=sum(abs(v)<=.5 for v in values)/len(values) if values else None,within_10=sum(abs(v)<=1 for v in values)/len(values) if values else None)
    count=len(rows);success=sum(c['schema_valid'] for c in cases);aligned=sum(c['evidence_and_contract_valid'] for c in cases)
    result=dict(dataset_size=24,scored_dataset_records=len(labels),unscored_dataset_records=sorted(set(dataset)-set(labels)),attempted_requests=count,schema_success_rate=success/count if count else None,exact_source_reference_validity_rate_among_schema_valid=sum(c['exact_source_references_valid'] for c in cases)/success if success else None,end_to_end_contract_validity_rate_among_schema_valid=aligned/success if success else None,assessment_contract_success_rate=aligned/count if count else None,provider_failure_rate=sum(c['provider_failure'] for c in cases)/count if count else None,synthetic_agreement=dict(warning='Diagnostics against synthetic intended labels, NOT IELTS accuracy. Only successfully validated assessed records are included.',criterion={k:metrics(v) for k,v in errors.items()},overall=metrics(overall),scored_ids=labels),annotated_error_span_overlap=dict(hits=span_hits,total=span_total,interpretation='Unverified synthetic labels; span overlap alone does not establish correct error detection.'),semantic_review=dict(confirmed_false_criticism=sum(r.get('false_criticism_count',0) for r in manual.values()) if manual else None,verified_known_error_detections=sum(r.get('verified_known_error_detections',0) for r in manual.values()) if manual else None,status='HUMAN_REVIEWED' if len(manual)==len(rows) and rows else 'NOT VERIFIED'),latency_ms=dict(model_responses_mean=statistics.mean(r['latency_ms'] for r in rows if 'wire' in r) if any('wire' in r for r in rows) else None,validated_mean=statistics.mean(r['latency_ms'] for r in rows if r.get('contract')=='PASS') if any(r.get('contract')=='PASS' for r in rows) else None,mean=statistics.mean(r.get('latency_ms',r.get('wall_latency_ms',0)) for r in rows) if rows else None,max=max((r.get('latency_ms',r.get('wall_latency_ms',0)) for r in rows),default=None)),tokens=dict(prompt=sum((r.get('usage') or {}).get('prompt_tokens',0) for r in rows),completion=sum((r.get('usage') or {}).get('completion_tokens',0) for r in rows),available_responses=sum(r.get('usage') is not None for r in rows)),expert_agreement=dict(status='NOT VERIFIED',reference_criterion_scores=None),cases=cases)
    (root/'benchmark.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['attempted_requests','scored_dataset_records','schema_success_rate','assessment_contract_success_rate','provider_failure_rate','semantic_review','latency_ms','tokens']}))

if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--qa-dir',type=Path,default=Path('/tmp/alua-writing-v4'));parser.add_argument('--fixtures',type=Path,default=Path(__file__).resolve().parents[1]/'tests/fixtures/writing-v4');args=parser.parse_args();report(args.qa_dir,args.fixtures)
