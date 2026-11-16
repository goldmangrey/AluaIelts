"""Normalize formatting artifacts only. Never edit source or rewrite synthetic labels/text."""
import argparse
import hashlib
import html
import json
import math
import re
from pathlib import Path

DEV = set('e01,e03,e04,e05,e06,e07,e09,e11,e12,e13,e15,e16,e17,e19'.split(','))
HOLDOUT = set('e02,e08,e10,e14,e18,e20,e21,e22,e23,e24'.split(','))

def prepare(source, output):
    original = source.read_bytes()
    decoded = html.unescape(original.decode('utf-8-sig'))
    # A backslash immediately before a physical newline is a transport artifact,
    # unlike literal JSON \\n escapes inside the essay string.
    cleaned, count = re.subn(r'\\\r?\n', '', decoded)
    decoder = json.JSONDecoder()
    records, sections, leftovers = [], [], []
    pos = 0
    while pos < len(cleaned):
        start = cleaned.find('[', pos)
        if start < 0:
            leftovers.append(cleaned[pos:]); break
        leftovers.append(cleaned[pos:start])
        value, end = decoder.raw_decode(cleaned, start)
        if not isinstance(value, list) or not all(isinstance(v, dict) for v in value):
            raise ValueError('Expected a top-level array of records')
        records.extend(value); sections.append(len(value)); pos = end
    if any(re.sub(r'[\s\\`]', '', fragment) not in ('', 'json') for fragment in leftovers):
        raise ValueError('Unrecognised text outside JSON arrays; inspect rather than guessing')
    ids = [r.get('id') for r in records]
    if len(ids) != len(set(ids)) or set(ids) != DEV | HOLDOUT:
        raise ValueError(f'Expected exactly unique e01-e24, got {ids}')
    anomalies = []; metadata = []
    for r in records:
        rid = r['id']
        for field in ('prompt', 'essay'):
            if not isinstance(r.get(field), str) or len(r[field].strip()) < 40:
                raise ValueError(f'{rid}: missing/incomplete {field}')
        wc = len(re.findall(r"[^\W_]+(?:['’\-][^\W_]+)*", r['essay'], re.UNICODE))
        scores = r['intended_scores']
        if set(scores) != {'TR', 'CC', 'LR', 'GRA'} or any(not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= 9 or v * 2 % 1 for v in scores.values()):
            raise ValueError(f'{rid}: invalid synthetic scores')
        mean = sum(scores.values()) / 4
        overall = math.floor(mean * 2 + .5) / 2
        if r.get('intended_overall') != overall:
            anomalies.append(dict(id=rid, type='overall_mismatch', supplied=r.get('intended_overall'), recomputed=overall))
        if wc < 250: anomalies.append(dict(id=rid, type='underlength', word_count=wc))
        for criterion, note in r.get('criteria_notes', {}).items():
            for quote in note.get('evidence', []):
                if quote not in r['essay']: anomalies.append(dict(id=rid, type='quote_mismatch', location=f'criteria_notes.{criterion}', quote=quote))
        for index, error in enumerate(r.get('error_list', [])):
            if not isinstance(error, dict) or not all(isinstance(error.get(k), str) for k in ('quote', 'type', 'correction')):
                anomalies.append(dict(id=rid, type='invalid_error_label', index=index)); continue
            if error['quote'] not in r['essay']: anomalies.append(dict(id=rid, type='quote_mismatch', location=f'error_list.{index}', quote=error['quote']))
            if error['quote'] == error['correction']: anomalies.append(dict(id=rid, type='unchanged_error_label', index=index))
        metadata.append(dict(id=rid, split='development' if rid in DEV else 'holdout', word_count=wc, recomputed_mean=mean, recomputed_overall=overall))
    output.mkdir(parents=True, exist_ok=True)
    (output / 'source.txt').write_bytes(original)
    (output / 'dataset.json').write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n')
    manifest = dict(source_sha256=hashlib.sha256(original).hexdigest(), records=len(records), array_sizes=sections, physical_line_continuations_removed=count, html_entities_decoded=decoded != original.decode('utf-8-sig'), labels='SYNTHETIC; not examiner calibration', records_metadata=metadata)
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    (output / 'anomalies.json').write_text(json.dumps(anomalies, ensure_ascii=False, indent=2) + '\n')
    assert source.read_bytes() == original
    print(json.dumps(dict(records=len(records), arrays=sections, underlength=sum(a['type']=='underlength' for a in anomalies), quote_mismatches=sum(a['type']=='quote_mismatch' for a in anomalies), overall_mismatches=sum(a['type']=='overall_mismatch' for a in anomalies), development=len(DEV), holdout=len(HOLDOUT))))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--source', type=Path, default=Path.home()/'Downloads/data-set-writing.txt'); parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1]/'tests/fixtures/writing-v4'); args=parser.parse_args(); prepare(args.source,args.output)
