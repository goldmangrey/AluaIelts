"""Build a deterministic, offline evidence browser, documentation and resume queue.

Reads only source/audit inputs. Writes only the audit directory and its summary.
Never promotes recognition agreement or renderer visibility to source verification.
"""
from __future__ import annotations
import collections
import csv
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'docs/reading-content-fidelity-v1'

def load(name):
    return json.loads((OUT / name).read_text())

def save(name, value):
    path = OUT / name
    temporary = path.with_suffix(path.suffix + '.partial')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n')
    temporary.replace(path)

def records(tests):
    for test in tests:
        yield test
        for passage in test['passages']:
            yield passage
            yield from passage['paragraphs']
            for group in passage['groups']:
                yield group
                yield from group['questions']

def main():
    report = load('report.json')
    report['sources'] = load('source-inventory.json')
    all_records = list(records(report['tests']))
    by_id = {r['id']: r for r in all_records}
    assert len(by_id) == len(all_records), 'Duplicate item IDs'
    findings = report['confirmed_findings']
    confirmed = [f for f in findings if f['verification_status'] == 'CORRUPTED']
    ambiguities = [f for f in findings if f['verification_status'] == 'UNRESOLVED']
    coverage = report['coverage']
    coverage['adjudicated_distinct_findings'] = len(findings)
    coverage['confirmed_corruption_issues'] = len(confirmed)
    coverage['source_ambiguity_issues'] = len(ambiguities)
    # Retain the earlier field for compatibility, but state its precise semantics.
    coverage['confirmed_distinct_issues_note'] = 'Legacy field includes adjudicated SOURCE_AMBIGUITY; use confirmed_corruption_issues for confirmed defects.'
    counts = collections.Counter(f['category'] for f in confirmed)
    coverage['confirmed_issue_categories'] = dict(sorted(counts.items()))
    coverage['possible_scoring_impact_issues'] = sum(f.get('possible_scoring_impact') in (True, 'POSSIBLE') for f in confirmed)
    coverage['key_classifications'] = dict(collections.Counter(r['key_status'] for r in all_records if r['kind'] == 'question'))
    for kind, expected in [('test', 72), ('passage', 216), ('group', 613), ('question', 2880)]:
        subset = [r for r in all_records if r['kind'] == kind]
        assert len(subset) == expected
        assert dict(collections.Counter(r['classification'] for r in subset)) == coverage['classifications'][kind]
    manual = load('manual-reviews.json')['records']
    for r in all_records:
        if not r.get('evidence') and manual.get(r['id'], {}).get('evidence'):
            r['evidence'] = manual[r['id']]['evidence']
        if r['classification'] == 'VERIFIED':
            m = manual.get(r['id'], {})
            assert m.get('source_comparison_complete') and m.get('evidence'), r['id']
            assert m.get('pdf_sha256') == r['pdf_sha256'], r['id']
        for ev in [*r.get('evidence', []), *r.get('key_evidence', [])]:
            assert (OUT / ev['reference']).is_file(), ev
    issue_ids = [f['issue_id'] for f in [*findings, *report['unconfirmed_candidates']]]
    assert len(set(issue_ids)) == len(issue_ids), 'Duplicate issue IDs'
    baseline = load('protected-before.json')
    changed = [p for p, h in baseline.items() if not (ROOT / p).is_file() or hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != h]
    assert not changed, f'Protected files changed: {changed}'
    report['safety'] = {'changed': changed, 'production_content_unchanged': True, 'protected_files_checked': len(baseline)}
    queue = []
    for r in all_records:
        if r['classification'] in {'NOT_AUDITED', 'UNRESOLVED', 'BLOCKED'}:
            queue.append({k: r.get(k) for k in ['id', 'kind', 'book', 'test', 'passage', 'question_group', 'question_number', 'classification', 'source_pdf', 'pdf_sha256', 'physical_pdf_pages', 'printed_pages', 'page_mapping_status', 'json_field_path', 'candidate_issues']} | {'required_work': 'Compare complete wording and all required context against visible source; adjudicate any discrepancies; record evidence and source hash. Validate page mapping and edition provenance.'})
    key_queue = [{k: r.get(k) for k in ['id', 'book', 'test', 'question_number', 'source_pdf', 'pdf_sha256', 'key_pdf_pages', 'key_status']} for r in all_records if r['kind'] == 'question' and r['key_status'] != 'KEY_VERIFIED']
    save('resume-queue.json', {'completion': report['completion'], 'note': 'Parent/child work overlaps; do not sum hierarchical item counts as independent defects. OCR cache is regenerable, not source verification.', 'source_comparison': queue, 'answer_keys': key_queue, 'unconfirmed_candidate_ids': [f['issue_id'] for f in report['unconfirmed_candidates']], 'remaining_source_asset_visual_work': 'Every source asset except the explicitly adjudicated cases; automated crop screening is not full image-content verification.'})
    save('coverage.json', coverage)
    save('report.json', report)
    save('checkpoints/safety.json', report['safety'])

    # Add source locators even for candidates; distinguish declared ranges from visually confirmed pages.
    columns = ['issue_id', 'severity', 'category', 'book', 'test', 'passage', 'question_group', 'question_numbers', 'json_paths', 'corrupted_text_excerpt', 'source_confirmed_text_excerpt', 'recognition_source_excerpt', 'source_pdf', 'pdf_sha256', 'physical_pdf_page', 'declared_physical_pdf_pages', 'page_mapping_status', 'printed_page', 'evidence', 'root_cause', 'meaning_changed', 'possible_scoring_impact', 'recommended_repair', 'verification_status']
    with (OUT / 'issues.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for f in [*findings, *report['unconfirmed_candidates']]:
            owner = by_id.get(f['owner_id'], {})
            row = {**owner, **f, 'declared_physical_pdf_pages': owner.get('physical_pdf_pages')}
            for key in ['source_pdf', 'pdf_sha256']:
                if not row.get(key) and f.get('evidence'):
                    row[key] = f['evidence'][0].get(key)
            writer.writerow({k: json.dumps(row.get(k), ensure_ascii=False) if isinstance(row.get(k), (list, dict)) else row.get(k) for k in columns})

    compact = []
    for r in all_records:
        if r['kind'] not in {'test', 'passage', 'group', 'question'}:
            continue
        compact.append({k: r.get(k) for k in ['id', 'kind', 'book', 'test', 'passage', 'question_group', 'question_number', 'question_numbers', 'classification', 'source_pdf', 'pdf_sha256', 'physical_pdf_pages', 'printed_pages', 'page_mapping_status', 'json_field_path', 'source_verification_method', 'source_comparison_complete', 'evidence', 'issues', 'candidate_issues', 'key_status', 'key_binding_status', 'coverage', 'rendering_status']})
    data = {'coverage': coverage, 'items': compact, 'findings': findings, 'candidates': report['unconfirmed_candidates']}
    html = DASHBOARD.replace('__AUDIT_DATA__', json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c'))
    (OUT / 'index.html').write_text(html)
    write_summary(report, all_records, counts, len(key_queue))
    validation = {'inventory': {'tests': 72, 'passages': 216, 'groups': 613, 'questions': 2880}, 'item_ids_unique': True, 'issue_ids_unique': True, 'counts_reconcile': True, 'verified_records_hash_bound_and_evidence_backed': True, 'evidence_files_exist': True, 'production_content_unchanged': True, 'full_fidelity_audit_complete': False}
    save('checkpoints/artifact-validation.json', validation)
    print(json.dumps({'validation': validation, 'coverage': coverage, 'resume_items': len(queue), 'unverified_keys': len(key_queue)}, indent=2))

def write_summary(report, all_records, counts, unverified_keys):
    c = report['coverage']
    q = c['classifications']['question']
    out = [
        '# ALUA READING CONTENT FIDELITY V1 — FORENSIC AUDIT RESULT', '',
        '**Release decision: NO-GO. Full evidence-based comparison is incomplete.**', '',
        'This report covers the entire inventory and automated/browser inspection, but does not certify the entire library. Findings below are a confirmed lower bound. Independent OCR disagreements are a review queue, not confirmed corruption. No correctness percentage is inferred.', '',
        '## Coverage', '',
        '| Work | Actual result |', '|---|---|',
        '| Books / tests inventoried | 18/18 · 72/72 |',
        '| Individual passage / group / question records | 216/216 · 613/613 · 2,880/2,880 |',
        '| Independent recognition | 1,028/1,028 declared Reading physical pages; no recognition errors |',
        '| Browser inspection | 72/72 tests; 2,880 Exam slots and 2,880 Review slots visible in disposable fixtures |',
        '| Complete test comparison against local original-PDF reference | 1/72: Cambridge 7 Test 1 |',
        '| Tests entirely source-verified without defects | 0/72 |',
        '| Passages | 0 VERIFIED · 3 CORRUPTED · 213 NOT_AUDITED |',
        '| Groups | 2 VERIFIED · 12 CORRUPTED · 1 UNRESOLVED · 598 NOT_AUDITED |',
        f'| Questions | {q.get("VERIFIED",0)} VERIFIED · {q.get("CORRUPTED",0)} CORRUPTED · {q.get("UNRESOLVED",0)} UNRESOLVED · {q.get("NOT_AUDITED",0)} NOT_AUDITED · 0 BLOCKED |',
        f'| Original key comparison | {2880-unverified_keys}/2,880 KEY_VERIFIED; {unverified_keys} KEY_UNVERIFIED |',
        f'| Adjudicated findings | {c["confirmed_corruption_issues"]} confirmed corruption issues + {c["source_ambiguity_issues"]} source ambiguities |',
        f'| Recognition/detector candidates requiring adjudication | {c["unconfirmed_candidates"]}; not confirmed defects |', '',
        '“Examined 40/40” in the matrix means individual JSON/recognition/browser records were examined. It does **not** mean 40/40 were compared completely with the original page image. A CORRUPTED question may inherit a confirmed defect in required shared group context even when its own sentence is intact.', '',
        '## Source integrity and provenance', '',
        'All 18 local PDF hashes and all 18 intermediate TXT hashes match the dataset manifest. Hash equality identifies the generator inputs; it does not establish publisher authenticity or content accuracy. No source was downloaded or replaced.', '',
        'The attachment named `Cambridge-IELTS-07(1).pdf` is not accessible as a distinct local attachment, so equivalence with it cannot be certified. Project, Desktop and Downloads C07 copies match each other. A different temporary 129-page C07 PDF was identified and excluded. See [attachment provenance](reading-content-fidelity-v1/attachment-provenance.json).', '',
        'The local C04/C09/C20 files are Word-generated/native-text derivatives or third-party editions; publisher-edition equivalence remains unproven. C09 T3 Q33–37 is UNRESOLVED because the local PDF itself has suspicious wording and extra unnumbered blanks. C07/C08 embedded text is largely watermark text, so embedded text cannot be treated as English source authority. C14 has an ABBYY text layer with recognition artifacts; visible page images take precedence.', '',
        'Physical PDF pages are 1-based. Printed page numbers are separate and recorded only when established; OCR footer candidates are explicitly unadjudicated. Most corpus page ranges come from existing JSON provenance and still require visual validation. Missing pages, source damage, edition equivalence and exact passage boundaries have **not** been exhaustively cleared across all books.', '',
        '| Book | PDF pages | SHA-256 | Reading page profile |', '|---|---:|---|---|'
    ]
    for i, source in enumerate(report['sources'], 4):
        book = re.search(r'IELTS-(\d+)', source['path']).group(1)
        out.append(f'| {book} | {source["page_count"]} | `{source["sha256"]}` | {source.get("reading_page_types",{})} |')
    out += ['', '## Confirmed findings', '', '| Category | Distinct confirmed issues |', '|---|---:|']
    out += [f'| {k} | {v} |' for k,v in sorted(counts.items())]
    out += ['', f'Possible scoring impact: {c["possible_scoring_impact_issues"]} distinct issues. Counts are deduplicated by finding, not by repeated field occurrence. Every affected JSON path is retained in CSV/JSON. Source ambiguities are excluded from confirmed corruption totals.', '',
        '### Cambridge 7 Test 1 — full reference comparison', '',
        'All three passages and all Q1–40 were compared, including instructions, paragraph sequence/labels, choices, shared summaries and required answer context, against physical PDF pages 22–33. The original key on physical page 157 (printed 153) was compared for all 40 answers and matches the existing key. Result: all three passages CORRUPTED; 29 questions CORRUPTED and 11 VERIFIED. The source reference remains the hash-bound local PDF, not an authenticated copy of the unavailable named attachment.', '',
        '- P1 “Let’s Go Bats”: body-title extraction includes graphical rules as punctuation. Paragraph C/E contain meaning-bearing punctuation substitutions; a source paragraph is split at a page boundary. Q1–5 instructions use `Passage |` instead of `Passage 1`.',
        '- Q6–9 “Facial Vision”: leader noise is embedded in the summary, including the fragment around blank 6; four original numbered blanks are not represented as inline answer slots. Full wording, limits and blank locations were visually compared.',
        '- P2: corrupted title and gallon/litre footnote. Q14–20 omit Roman option `v`, merging its text into `iv`; the original Q16 key is `v`, which the UI cannot select. Q19/Q20 prompts are misassigned. The fallback source image itself ends after Q19 and omits Q20 “Paragraph H”.',
        '- Q21–26: original source-image statements are visible, but underlying prompts contain isolated numbers or whole-group fallback text. The original instructions use YES/NO/NOT GIVEN; this is not a TRUE/FALSE defect.',
        '- P3: duplicate title caused by case-sensitive heading suppression; one paragraph is split at the source page break. Q27/Q29/Q34 contain joined words.',
        '- Q37–40: noisy blanks, reordered summary text, lost A–K labels and empty parsed options. Original key correspondence F/H/K/G was verified independently. The report retains short evidence excerpts and the minimum necessary crops.',
        '- The source itself says “seven paragraphs A–H”. This inconsistency is SOURCE_AMBIGUITY, not an importer defect.', '',
        '### Cambridge 6 Test 1 — Q23–26', '',
        'Full surrounding group compared on physical page 26 (printed 25), including instructions, four blank positions and A–K options. `FECUCE 26 ...` corresponds to `reduce [26]`; blank 25’s number is lost. Options lose their labels and no inline blank slots are generated. All four questions are CORRUPTED. Original keys G/B/C/A are KEY_VERIFIED from physical page 153. Other C06 passages/questions are not certified.', '',
        '### Other source-adjudicated cases', '',
        '- C07 T4 Q30–34: noisy summary blanks and lost A–J labels; all five CORRUPTED. Q35–40 was fully compared and all six are VERIFIED; keys remain unverified.',
        '- C14 T2 Q19–26: broken words such as `comi ng ... patie nts sufferi ng` and missing sentence punctuation; eight questions affected by shared context.',
        '- C16 T2 Q17–20: corrupted summary; option C is merged into B and unavailable. Only blank 20 is inline; blanks 17–19 are detached.',
        '- C16 T3 Q20–22: prose beginning “A team of archaeologists…” is parsed as option A, converting ONE WORD ONLY inputs into single-select controls with only A. All three are CORRUPTED.',
        '- C09 T3 Q33–37: UNRESOLVED local-source wording/blank defects. No guessed replacement is asserted.',
        '- Other books have automated disagreement candidates; they have not been converted into confirmed defects without source adjudication.', '',
        '## Pipeline and root causes', '',
        '`Local PDF → earlier OCR/extraction TXT → engine normalization/parsing → repairs/source edits/enrichment → exam JSON → ReadingCatalog/API → React renderer`', '',
        'Confirmed upstream evidence: the critical OCR fragments already exist in intermediate TXT and persist into JSON. Original OCR engine/run is unavailable, so attribution to a particular OCR model remains suspected, not confirmed. Manifest hashes bind the current files to the generator inputs.', '',
        'Confirmed transformation behavior, reproduced without invoking dataset generation:', '',
        '- `backend/scripts/reading_dataset/engine.py`: option detection treats prose starting with “A” as a choice; non-empty parsed options then force single-select input. Broken option labels disappear from parsed options/allowed values.',
        '- `engine.py` rich-text blank recognition relies on underscore-style patterns; corrupted dotted leaders do not become numbered inline slots. Whole-group prompt fallback repeats or misassigns context.',
        '- `backend/scripts/reading_dataset/pdf_support.py`: source-image crop clamps to 93.5% page height; C07 physical page 26 Q20 begins below the resulting crop. Both metadata coordinates and browser image were checked.',
        '- `web/src/features/reading/exam/passage-pane.tsx`: case-sensitive duplicate-heading comparison lets EDUC ATING PSYCHE appear again under its title.',
        '- `question-renderer.tsx` can show generic answer rows when summary slots were not parsed. Image fallback can restore source wording for some groups, but cannot repair missing choices or already clipped source images.', '',
        'Existing validator gaps: structural 40-question coverage, schema validity, file hashes and grader examples cannot verify original wording, option-label fidelity, negation/limits or image-crop completeness. Current local production statuses are 69 `needs_review`, 3 `blocked`, 0 source-verified; these are reported separately from forensic classifications. Existing hash-bound source edits do not provide corpus-wide content verification.', '',
        '## Reproducible method and limitations', '',
        '1. Inventory protected production inputs, SHA-256 PDFs/intermediates, page metadata and declared provenance.',
        '2. Fresh Tesseract recognition of all 1,028 declared Reading pages rendered at 2.5×; embedded text is retained separately. Bounded workers and hash/page checkpoints allow resume. Independent recognition is not proof of source accuracy.',
        '3. Compare all content-bearing fields, including clean-looking text, to recognized source blocks. Normalize harmless whitespace only; retain letters, digits and punctuation. Token operations and normalized offsets are in `checkpoints/diffs-XX.json`. OCR/layout alignment can produce false positives and false negatives.',
        '4. Type-specific automated checks cover all 15 encountered types, including limits, choice labels/reuse, multi-answer grouping and completion slots. Table/flowchart/diagram semantics still require page-image review; generic schema checks do not certify them.',
        '5. Visually adjudicate complete source context, record crop coordinates, source hash, physical/printed pages and every affected field. Only explicit complete, hash-bound review records can set VERIFIED.',
        '6. Inspect unchanged production renderers with disposable Exam/Review fixtures, no DB writes or live user attempts. All 72 tests were inspected in Chromium. This establishes control/context visibility, not full text fidelity or cross-browser equivalence. Full WebKit/mobile source-fidelity validation was not performed.', '',
        'Evidence crops and excerpts are restricted to defects or disputed context; entire copyrighted books are not bundled in this report. Raw OCR remains in `/tmp/alua-reading-fidelity-work` and can be regenerated from the local PDFs. Checkpoints are deterministic; recognition caches and manual source-review records have separate meanings.', '',
        '## Full test / passage matrix', '',
        'V=VERIFIED, C=CORRUPTED, U=UNRESOLVED, N=NOT_AUDITED. Passage status refers to passage content, not a clean bill of health for its question groups. `40/40` is automated/browser record coverage. `Full Q` counts questions whose entire required source context has been compared. Keys are independently source-verified.', '',
        '| Book/Test | Records | P1 | P2 | P3 | Q V/C/U/N | Full Q | Keys | Groups V/C/U/N | Rendering |',
        '|---|---|---|---|---|---|---:|---|---|---|']
    short = {'VERIFIED':'V','CORRUPTED':'C','UNRESOLVED':'U','NOT_AUDITED':'N','BLOCKED':'B'}
    for t in report['tests']:
        cov=t['coverage']; qc=cov['question_classifications']; gc=cov['group_classifications']
        out.append(f'| C{t["book"]:02} T{t["test"]} | {cov["questions_examined"]}/40 | '+ ' | '.join(short[p['classification']] for p in t['passages']) + ' | ' + '/'.join(str(qc.get(s,0)) for s in ['VERIFIED','CORRUPTED','UNRESOLVED','NOT_AUDITED']) + f' | {cov["source_comparison_complete_questions"]}/40 | {cov["key_verified"]}/40 | ' + '/'.join(str(gc.get(s,0)) for s in ['VERIFIED','CORRUPTED','UNRESOLVED','NOT_AUDITED']) + ' | Chromium Exam+Review inspected |')
    out += ['', '## Book totals', '', '| Book | Tests | Passages V/C/N | Questions V/C/U/N | Keys verified |', '|---|---:|---|---|---:|']
    for book in range(4,22):
        rr=[r for r in all_records if r['book']==book]; pc=collections.Counter(r['classification'] for r in rr if r['kind']=='passage'); qc=collections.Counter(r['classification'] for r in rr if r['kind']=='question')
        out.append(f'| {book:02} | 4 | '+ '/'.join(str(pc[s]) for s in ['VERIFIED','CORRUPTED','NOT_AUDITED'])+' | '+ '/'.join(str(qc[s]) for s in ['VERIFIED','CORRUPTED','UNRESOLVED','NOT_AUDITED'])+f' | {sum(r.get("key_status")=="KEY_VERIFIED" for r in rr)} |')
    out += ['', '## Audit dashboard validation', '', 'The offline dashboard was checked separately in Chromium and WebKit at 1366×768 and 390×844: all 72 test entries, item navigation, issue filters, original-source crops, candidate labels and horizontal-overflow checks passed. This validates the report interface only; it does not certify all source text or production UI behavior. See `checkpoints/dashboard-browser-validation.json`.', '', '## Outstanding work / release blockers', '',
        f'- Complete visual source comparison for 213 passages, 598 groups and {q["NOT_AUDITED"]} questions still NOT_AUDITED. These are overlapping hierarchical work units, not independent defect counts.',
        f'- Resolve five C09 questions and the two adjudicated source ambiguities; independently authenticate edition/attachment identity where required.',
        f'- Compare {unverified_keys} remaining original answer-key entries. A valid existing key never substitutes for question wording verification.',
        '- Adjudicate all 2,343 recognition/detector candidates, inspect all diagrams/tables/flowcharts and relevant footnotes, validate all source page ranges/crops, and inspect actual rendered content against the source for each unreviewed item.',
        '- In a separately authorized repair task, prioritize unavailable correct options / incorrect input types, missing questions or blanks, missing choices and limits, then wording/paragraph/typography defects. Preserve keys, grading and existing attempts unless separately authorized.', '',
        '## Artifacts and resume', '',
        '- [Evidence browser](reading-content-fidelity-v1/index.html): all 72 tests, 216 passages, 613 groups and 2,880 questions; filters, stable item anchors, excerpts and crops.',
        '- [Full report](reading-content-fidelity-v1/report.json), [coverage](reading-content-fidelity-v1/coverage.json), [issue inventory](reading-content-fidelity-v1/issues.csv). CSV includes confirmed findings and clearly labeled unconfirmed candidates.',
        '- [Resume queue](reading-content-fidelity-v1/resume-queue.json), [manual reviews](reading-content-fidelity-v1/manual-reviews.json), [source inventory](reading-content-fidelity-v1/source-inventory.json), [browser observations](reading-content-fidelity-v1/browser-observations.json).',
        '- `checkpoints/recognition-all-psm3.json`: page recognition state; `comparison-*.json`: automated comparison state only; `diffs-*.json`: token differences; `pipeline-reproduction.json`: parser reproductions; `safety.json`: protected-file hashes.', '',
        'Run from project root with an isolated Python environment containing PyMuPDF, Pillow and rapidfuzz, plus local Tesseract:', '',
        '```sh',
        'python docs/reading-content-fidelity-v1/scripts/recognize.py --help',
        'python docs/reading-content-fidelity-v1/scripts/source_profile.py',
        'python docs/reading-content-fidelity-v1/scripts/record_visual_review.py',
        'python docs/reading-content-fidelity-v1/scripts/audit.py',
        'python docs/reading-content-fidelity-v1/scripts/build_outputs.py',
        '```', '',
        'The supplied visual-review script reproduces only the recorded adjudications. It does not create new verification for unreviewed material. Regenerate OCR caches if `/tmp` has been cleared; browser fixtures are generated separately by `export_browser.py` / `browser.mjs`. Read their CLI/code before running because their dependencies and temporary paths are explicit.', '',
        f'Protected-file safety: {report["safety"]["protected_files_checked"]} baseline files checked; zero changed during this audit. Production exam content, keys, API, frontend and user results were not edited by this audit. Existing workspace changes from earlier tasks were preserved. No commit, push or deploy.', '',
        '**NO-GO remains in effect: confirmed scoring-affecting defects exist and most source comparison remains outstanding. A successful script or browser run is not a fidelity PASS.**', ''
    ]
    (ROOT / 'docs/READING_CONTENT_FIDELITY_V1.md').write_text('\n'.join(out))

DASHBOARD = r'''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ALUA Reading fidelity — evidence browser</title>
<style>
*{box-sizing:border-box}body{overflow-wrap:anywhere;margin:0;font:14px/1.5 system-ui,sans-serif;background:#f5f5f7;color:#18242c}header{padding:22px 26px;background:#fff;border-bottom:1px solid #ddd}h1{font-size:21px;margin:0 0 8px}h2{font-size:17px}p{margin:8px 0}a{color:#075f85}nav{display:flex;gap:15px;flex-wrap:wrap}.warning{color:#983b20;font-weight:650}.stats{font-size:13px;color:#4b5661}.layout{display:grid;grid-template-columns:270px minmax(0,1fr);gap:16px;padding:16px}aside,main{min-width:0}aside{position:sticky;top:12px;align-self:start;max-height:90vh;overflow:auto}button,input,select{max-width:100%;font:inherit;padding:8px;border:1px solid #bcc5ca;border-radius:6px;background:white;color:inherit}button{cursor:pointer;text-align:left}button:hover,button[aria-current=true]{background:#e3eeea;border-color:#5f8a7a}#tests{display:grid;gap:5px}#tests button{width:100%;font-size:12px}.filters{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}.filters input{flex:1;min-width:160px}article,.panel{background:#fff;border:1px solid #ddd;border-radius:10px;padding:16px;margin-bottom:12px}code{overflow-wrap:anywhere;font-size:12px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f7f7f8;padding:10px;font:13px/1.5 ui-monospace,monospace}.tag{display:inline-block;padding:2px 7px;margin:2px;border-radius:4px;background:#eee;font-size:11px}.CORRUPTED{background:#fbe3dd;color:#842517}.VERIFIED{background:#deeee6;color:#185338}.NOT_AUDITED,.UNRESOLVED{background:#fff1d7;color:#805412}.BLOCKED{background:#eee;color:#444}#items{display:flex;gap:5px;flex-wrap:wrap;max-height:240px;overflow:auto}#items button{font-size:12px;padding:4px 7px}img{display:block;max-width:100%;height:auto;margin:10px 0;border:1px solid #ddd}details{margin:8px 0}summary{cursor:pointer}.muted{color:#65717b;font-size:12px}.evidence-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}@media(max-width:850px){.layout{grid-template-columns:1fr}aside{position:static;max-height:240px}.evidence-grid{grid-template-columns:1fr}}:focus-visible{outline:3px solid #086e9b;outline-offset:2px}
</style>
<header><h1>ALUA Reading Content Fidelity V1</h1><p class="warning">NO-GO · Evidence comparison incomplete. Visibility and OCR agreement do not mean source-verified.</p><p class="stats" id="coverage"></p><nav><a href="../READING_CONTENT_FIDELITY_V1.md">Report</a><a href="report.json">JSON</a><a href="issues.csv">CSV</a><a href="coverage.json">Coverage</a><a href="resume-queue.json">Resume queue</a></nav></header>
<div class="layout"><aside aria-label="72 tests"><h2>All 72 tests</h2><div id="tests"></div></aside><main>
<section class="panel"><h2 id="test-title"></h2><p id="test-coverage"></p><div id="items" aria-label="Passages, groups and questions"></div></section>
<section class="panel" id="item-detail" aria-live="polite"></section>
<section><h2>Findings / unconfirmed candidates</h2><div class="filters"><input id="search" type="search" placeholder="Search excerpts, Q number, issue ID" aria-label="Search findings"><select id="scope" aria-label="Finding scope"><option value="test">Selected test</option><option value="all">All 72 tests</option></select><select id="verification" aria-label="Verification status"><option value="CORRUPTED">Confirmed corruption</option><option value="adjudicated">All adjudicated findings</option><option value="candidate">Unconfirmed candidates</option><option value="all">All findings + candidates</option></select><select id="severity" aria-label="Severity"><option value="">Any severity</option></select><select id="category" aria-label="Corruption type"><option value="">Any corruption type</option></select></div><p id="result-count" class="muted"></p><div id="findings"></div><button id="more" hidden>Show 50 more</button></section>
</main></div>
<script id="audit-data" type="application/json">__AUDIT_DATA__</script>
<script>
'use strict';const D=JSON.parse(document.getElementById('audit-data').textContent),byId=new Map(D.items.map(i=>[i.id,i])),tests=D.items.filter(i=>i.kind==='test'),all=[...D.findings.map(f=>({...f,adjudicated:true})),...D.candidates.map(f=>({...f,adjudicated:false}))];let selected=tests[0],limit=50;
const $=s=>document.getElementById(s);function el(tag,text,cls){const e=document.createElement(tag);if(text!=null)e.textContent=text;if(cls)e.className=cls;return e}function tag(text){return el('span',text,'tag '+text)}function button(text,fn){let e=el('button',text);e.type='button';e.onclick=fn;return e}function count(c){return ['VERIFIED','CORRUPTED','UNRESOLVED','NOT_AUDITED','BLOCKED'].map(s=>(c[s]||0)+' '+s).join(' · ')}
$('coverage').textContent='18 books · 72 tests · 216 passages · 613 groups · 2,880 questions. Full test comparison: 1/72. Questions: '+count(D.coverage.classifications.question)+'.';
for(const t of tests){let b=button('C'+String(t.book).padStart(2,'0')+' · Test '+t.test+' · '+t.classification,()=>select(t.id));b.dataset.test=t.id;b.append(el('div',count(t.coverage.question_classifications),'muted'));$('tests').append(b)}
for(const v of [...new Set(all.map(f=>f.severity))].sort())$('severity').append(new Option(v,v));for(const v of [...new Set(all.map(f=>f.category))].sort())$('category').append(new Option(v,v));
function linkSource(parent,source,page){if(!source)return;let a=el('a','Open local source PDF'+(page?' · physical page '+page:''));a.href='../../'+source+(page?'#page='+page:'');a.target='_blank';a.rel='noopener';parent.append(a)}
function showEvidence(parent,ev){for(const e of ev||[]){let detail=el('details');let title=el('summary','Source evidence · physical '+(e.physical_pdf_page??'asset crop')+' · printed '+(e.printed_page??'unknown'));detail.append(title);if(e.kind!=='SOURCE_PAGE_REFERENCE'){let im=el('img');im.src=e.reference;im.alt='Limited original-source crop for the selected audit finding';im.loading='lazy';detail.append(im)}detail.append(el('p','PDF points '+JSON.stringify(e.crop_box_pdf_points)+' · SHA-256 '+(e.pdf_sha256||'see source asset provenance'),'muted'));linkSource(detail,e.source_pdf,e.physical_pdf_page);parent.append(detail)}}
function select(id){let r=byId.get(id);if(!r)return;selected=tests.find(t=>t.book===r.book&&t.test===r.test);for(const b of $('tests').children)b.setAttribute('aria-current',String(b.dataset.test===selected.id));$('test-title').textContent='Cambridge '+selected.book+' · Test '+selected.test;$('test-coverage').textContent='40/40 individual records examined. Full source question comparisons: '+selected.coverage.source_comparison_complete_questions+'/40. Source-verified keys: '+selected.coverage.key_verified+'/40.';$('items').replaceChildren();for(const i of D.items.filter(i=>i.book===r.book&&i.test===r.test)){let label=i.kind==='test'?'Test':i.kind==='passage'?'Passage '+i.passage:i.kind==='group'?'P'+i.passage+' Q'+(i.question_numbers||[]).join(','):'Q'+i.question_number;let b=button(label,()=>select(i.id));b.className=i.classification;b.setAttribute('aria-current',String(i.id===id));$('items').append(b)}let box=$('item-detail');box.replaceChildren(el('h2',r.id),tag(r.classification),tag(r.key_status||'KEY STATUS N/A'));box.append(el('p','Full source context compared: '+Boolean(r.source_comparison_complete)),el('p','Key binding: '+(r.key_binding_status||'not applicable')),el('p','JSON path: '+r.json_field_path),el('p','PDF SHA-256: '+r.pdf_sha256,'muted'),el('p','Physical page range: '+JSON.stringify(r.physical_pdf_pages)+' · printed: '+JSON.stringify(r.printed_pages)+' · '+r.page_mapping_status,'muted'));linkSource(box,r.source_pdf,(r.physical_pdf_pages||[])[0]);showEvidence(box,r.evidence);let ids=new Set(r.issues||[]);if(r.kind==='question')for(const f of all)if((f.affected_item_ids||[]).includes(r.id))ids.add(f.issue_id);box.append(el('p','Adjudicated issue IDs: '+([...ids].join(', ')||'none; this alone does not establish accuracy')));history.replaceState(null,'','#'+id);limit=50;renderFindings()}
function renderFindings(){let mode=$('verification').value,search=$('search').value.toLowerCase(),found=all.filter(f=>($('scope').value==='all'||(f.book===selected.book&&f.test===selected.test))&&(mode==='all'||mode==='candidate'&&!f.adjudicated||mode==='adjudicated'&&f.adjudicated||mode==='CORRUPTED'&&f.adjudicated&&f.verification_status==='CORRUPTED')&&(!$('severity').value||f.severity===$('severity').value)&&(!$('category').value||f.category===$('category').value)&&(!search||JSON.stringify(f).toLowerCase().includes(search)));$('result-count').textContent=found.length+' matching findings; showing '+Math.min(limit,found.length)+'. Unconfirmed candidates are not confirmed errors.';$('findings').replaceChildren();for(const f of found.slice(0,limit)){let a=el('article');a.id=f.issue_id;a.append(el('h2',f.issue_id+' · C'+f.book+' T'+f.test+' P'+f.passage),tag(f.adjudicated?f.verification_status:'UNCONFIRMED_CANDIDATE'),tag(f.severity),tag(f.category));let b=button('Go to affected item',()=>{select(f.owner_id);$('item-detail').scrollIntoView({block:'start'})});a.append(b,el('p','Questions: '+(f.question_numbers||[]).join(', ')),el('code',(f.json_paths||[]).join('\n')));let grid=el('div',null,'evidence-grid');for(const [label,text]of [['JSON excerpt',f.corrupted_text_excerpt],['Source-confirmed excerpt',f.source_confirmed_text_excerpt]]){let col=el('div');col.append(el('h3',label),el('pre',text||'No source-confirmed transcription. Do not infer correctness.'));grid.append(col)}a.append(grid);if(!f.adjudicated&&f.recognition_source_excerpt)a.append(el('p','Independent recognition only, not source-confirmed:'),el('pre',f.recognition_source_excerpt));a.append(el('p',f.root_cause),el('p','Meaning changed: '+f.meaning_changed+' · Possible scoring impact: '+f.possible_scoring_impact),el('p','Recommended next step: '+f.recommended_repair));showEvidence(a,f.evidence);let owner=byId.get(f.owner_id);if(owner)linkSource(a,owner.source_pdf,f.physical_pdf_page||(owner.physical_pdf_pages||[])[0]);$('findings').append(a)}$('more').hidden=found.length<=limit}
for(const id of ['search','scope','verification','severity','category'])$(id).addEventListener('input',()=>{limit=50;renderFindings()});$('more').onclick=()=>{limit+=50;renderFindings()};let initial=decodeURIComponent(location.hash.slice(1));if(!byId.has(initial)){let f=all.find(f=>f.issue_id===initial);initial=f?f.owner_id:tests[0].id}select(initial);window.addEventListener('hashchange',()=>{let id=decodeURIComponent(location.hash.slice(1));if(byId.has(id))select(id)});
</script></html>'''

if __name__ == '__main__':
    main()
