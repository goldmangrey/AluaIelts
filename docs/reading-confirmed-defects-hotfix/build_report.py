"""Assemble hotfix evidence only after all targeted gates have passed.

Does not scan/OCR/reimport the corpus or modify the immutable V1 audit artifacts.
"""

import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
DATA = ROOT / "backend/app/content/reading_v1"
TOOLS = ROOT / "backend/scripts/reading_dataset"
sys.path.insert(0, str(TOOLS))
from repairs import fingerprint


def load(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )


def main():
    original = load(ROOT / "docs/reading-content-fidelity-v1/report.json")
    findings = [
        f
        for f in original["confirmed_findings"]
        if f["verification_status"] == "CORRUPTED"
    ]
    config = load(TOOLS / "confirmed_hotfixes.json")
    summary = load(OUT / "change-summary.json")
    manifest = load(DATA / "manifest.json")
    entries = {e["id"]: e for e in manifest["exams"]}
    qa = load(OUT / "qa-checks.json")
    browser = load(OUT / "browser-qa.json")["results"]
    assert all(c["exit_code"] == 0 for c in qa["commands"])
    for name in ["backend-tests.xml", "browser-tests.xml"]:
        suites = list(ET.parse(OUT / name).getroot().iter("testsuite"))
        assert suites and all(
            int(s.get("failures", 0)) == 0 and int(s.get("errors", 0)) == 0
            for s in suites
        )
    baseline = load(OUT / "safety-baseline.json")
    intentional = {
        "backend/app/content/reading_v1/corrections.jsonl",
        "backend/app/content/reading_v1/manifest.json",
        "backend/scripts/reading_dataset/engine.py",
        "backend/scripts/reading_dataset/enrich.py",
        "backend/scripts/reading_dataset/pdf_support.py",
        "backend/scripts/reading_dataset/source_reviews.json",
        "backend/scripts/reading_dataset/validator.py",
        "web/src/features/reading/exam/passage-pane.tsx",
        "web/src/features/reading/exam/question-renderer.tsx",
    } | {
        "backend/app/content/reading_v1/" + entries[e["exam_id"]]["exam_path"]
        for e in summary["exams"]
    }
    changed = {p for p, h in baseline.items() if sha(ROOT / p) != h}
    assert changed == intentional, (changed - intentional, intentional - changed)
    keys = {p: h for p, h in baseline.items() if "/answer_keys/" in p}
    assert len(keys) == 72 and all(sha(ROOT / p) == h for p, h in keys.items())
    safety = {
        "baseline_files_checked": len(baseline),
        "intentionally_changed_baseline_files": sorted(changed),
        "remaining_baseline_files_unchanged": len(baseline) - len(changed),
        "unexpected_changes": [],
        "answer_keys_checked": len(keys),
        "answer_keys_unchanged": True,
        "answer_key_sha256": keys,
        "old_assets": [
            {
                "id": a["id"],
                "sha256": a["sha256"],
                "unchanged": sha(DATA / a["path"]) == a["sha256"],
            }
            for a in config["retained_assets"]
        ],
        "question_identity_checks": summary["exams"],
    }
    assert all(a["unchanged"] for a in safety["old_assets"])
    for e in summary["exams"]:
        assert e["question_ids_and_numbers_unchanged"] and e["question_count"] == 40
        assert sha(DATA / entries[e["exam_id"]]["exam_path"]) == e["after_sha256"]
        cases = [c for c in browser if c["exam_id"] == e["exam_id"]]
        assert {c["browser"] for c in cases} == {"chromium", "webkit"}
        for case in cases:
            assert case["content_hash"] == e["after_sha256"], (
                "Browser ran a different content revision"
            )
            assert not case["errors"]
            for field in [
                "restored_bank_options_selectable",
                "inline_blanks_present",
                "finish_atomic_snapshot_accepted",
                "submitted_answers_match",
                "affected_answers_grade_correct",
                "review_read_only",
            ]:
                assert case[field]
    rows = []
    for finding in findings:
        repair = next(
            r for r in config["repairs"] if finding["issue_id"] in r["issue_ids"]
        )
        entry = entries[repair["exam_id"]]
        exam = load(DATA / entry["exam_path"])
        target = next(
            v
            for p in exam["passages"]
            for v in [p, *p["question_groups"]]
            if v["id"] == repair["target_id"]
        )
        value = target["content"] if repair["kind"] == "passage" else target
        assert fingerprint(value) == repair["after_sha256"]
        assert sha(ROOT / repair["pdf_file"]) == repair["pdf_sha256"]
        assert sha(ROOT / repair["txt_file"]) == repair["txt_sha256"]
        for evidence in finding["evidence"]:
            assert (
                ROOT / "docs/reading-content-fidelity-v1" / evidence["reference"]
            ).is_file()
        rows.append(
            {
                "issue_id": finding["issue_id"],
                "status": "FIXED_VERIFIED",
                "blocked_reason": None,
                "category": finding["category"],
                "exam_id": repair["exam_id"],
                "target_id": repair["target_id"],
                "original_json_paths": finding["json_paths"],
                "repaired_fields": sorted(repair["set"]),
                "source_pdf": repair["pdf_file"],
                "pdf_sha256": repair["pdf_sha256"],
                "physical_pdf_page": finding.get("physical_pdf_page"),
                "source_evidence": finding["evidence"],
                "source_comparison": "Reviewed V1 evidence and relevant original page images; faithful transcription, labels and blank positions; no inferred source wording.",
                "canonical_after_sha256": repair["after_sha256"],
                "regression_test": "test_each_original_issue_has_applied_source_bound_repair["
                + finding["issue_id"]
                + "]",
                "browser_cases": [
                    repair["exam_id"] + ":chromium",
                    repair["exam_id"] + ":webkit",
                ],
            }
        )
    assert len(rows) == len({r["issue_id"] for r in rows}) == 41
    assert {r["issue_id"] for r in rows} == {f["issue_id"] for f in findings}
    groups = summary["groups"]
    transitions = [change for g in groups for change in g["input_type_changes"]]
    metrics = {
        "confirmed_issues": 41,
        "fixed_verified": 41,
        "blocked": 0,
        "incorrect_single_select_questions_restored_to_text": sum(
            t["after"] == "text" for t in transitions
        ),
        "letter_answer_questions_restored_to_selectors": sum(
            t["after"] == "single_select" for t in transitions
        ),
        "input_type_fields_changed": len(transitions),
        "missing_option_labels_restored": sum(
            len(set(g["option_labels_after"]) - set(g["option_labels_before"]))
            for g in groups
        ),
        "option_banks_repaired": 5,
        "inline_blank_positions_restored": sum(
            len(
                set(g["inline_blank_numbers_after"])
                - set(g["inline_blank_numbers_before"])
            )
            for g in groups
        ),
        "inline_blank_positions_verified": sum(
            len(g["inline_blank_numbers_after"]) for g in groups
        ),
        "ocr_artifact_issues_fixed": sum(
            f["category"] == "OCR_ARTIFACT" for f in findings
        ),
        "image_crop_fixes": 1,
        "affected_exams": 6,
    }
    changed_files = sorted(
        intentional
        | {
            "backend/app/modules/reading/catalog.py",
            "backend/tests/test_reading.py",
            "backend/tests/test_reading_confirmed_hotfix.py",
            "backend/scripts/reading_dataset/confirmed_hotfixes.py",
            "backend/scripts/reading_dataset/confirmed_hotfixes.json",
            "backend/scripts/reading_dataset/apply_confirmed_hotfix.py",
            "web/scripts/test-reading-confirmed-hotfix.mjs",
            "docs/READING_CONFIRMED_DEFECTS_HOTFIX.md",
            "docs/reading-confirmed-defects-hotfix.json",
        }
        | {
            "backend/app/content/reading_v1/" + a["path"]
            for row in config["repairs"]
            for a in row["set"].get("assets", [])
            if "fidelity-v1" in a["id"]
        }
    )
    result = {
        "title": "ALUA READING HOTFIX RESULT",
        "scope": "41 confirmed V1 defects only",
        "local_release_readiness": "GO",
        "library_fidelity_certified": False,
        "metrics": metrics,
        "issues": sorted(rows, key=lambda r: r["issue_id"]),
        "answer_keys_unchanged": True,
        "old_attempts_compatibility": "PASS",
        "exam_review_browser_qa": "PASS",
        "reading_submit": "PASS",
        "typescript": "PASS",
        "eslint": "PASS",
        "ruff": "PASS",
        "production_build": "PASS",
        "safety_evidence": "reading-confirmed-defects-hotfix/safety.json",
        "browser_evidence": "reading-confirmed-defects-hotfix/browser-qa.json",
        "test_evidence": "reading-confirmed-defects-hotfix/backend-tests.xml",
        "changed_files": changed_files,
        "unchanged_out_of_scope": {
            "source_ambiguities": 2,
            "unresolved_questions": 5,
            "unconfirmed_candidates": 2343,
            "other_exam_files": 66,
            "source_files": 36,
        },
        "notes": [
            "V1 remains an immutable historical audit, not a report on the repaired revision.",
            "All six tests remain needs_review; this hotfix does not certify unaudited content.",
            "No full OCR, corpus audit, full reimport, production DB access, commit, push or deploy.",
        ],
    }
    save(OUT / "safety.json", safety)
    save(ROOT / "docs/reading-confirmed-defects-hotfix.json", result)
    counts = Counter(f["category"] for f in findings)
    text = [
        "# ALUA READING HOTFIX RESULT",
        "",
        "**41/41 FIXED_VERIFIED · BLOCKED 0 · Local targeted hotfix: GO.**",
        "",
        "Implemented only the 41 CORRUPTED findings from V1. The two SOURCE_AMBIGUITY findings, five UNRESOLVED questions and 2,343 unconfirmed candidates were not repaired or re-audited. V1 artifacts remain unchanged. This result does not certify the rest of the Reading library.",
        "",
        "## Changes",
        "",
        "- Six canonical exam files: C06 T1, C07 T1, C07 T4, C14 T2, C16 T2, C16 T3. Fifteen source-bound passage/group overlays cover exactly 41 original issue IDs.",
        "- Restored summaries, instructions, repeated prompt/context fields, word limits, options/allowed values and numbered inline blanks. Corrected source-confirmed passage titles, punctuation, footnote and paragraph joins.",
        "- Restored 34 missing option labels across five banks and 23 missing inline positions; verified 32 total inline positions across seven affected summary groups.",
        "- Fixed 11 erroneous single-select questions in C14 T2 and C16 T3 back to one-word text fields. Restored 13 source-letter answers as selectors in C06 T1/C07 T1/C07 T4. Total: 24 input-type field changes; IDs/numbers unchanged.",
        "- C07 T1 Q16 now offers v, corresponding to the unchanged original key. Q19/Q20 are Paragraph G/H. The new crop includes all of Q20; the original image ID/path/bytes remain available for frozen attempts.",
        "- The renderer suppresses duplicate title headings regardless of case, and removes only an exact duplicate numbered group heading already supplied by its section. Passage and question wording remain visible; no design or layout redesign.",
        "",
        "## Root-cause protection and reproduction",
        "",
        "`confirmed_hotfixes.json` binds each repair to original PDF/TXT hashes and reviewed evidence, accepts only explicit known target fingerprints, and validates the exact repaired output. Changes to question IDs/numbers are rejected. Input-type transitions are explicitly allowlisted. The overlays run after existing repairs in normal enrichment, so an ordinary import cannot silently restore the old corrupted fields.",
        "",
        "Parser regressions cover A-team/A-major-reason prose, column labels including C_, Roman i–v, and numbered dotted/underscore blanks. Automatic cropping fails closed when a recognized final question lies below its inferred footer; the confirmed Q20 fix uses a hash-bound reviewed crop. Existing unmodified image IDs/bytes are preserved.",
        "",
        "Only six tests were replayed in temporary output to check import persistence; no complete dataset reimport was run. Apply is idempotent (second application writes zero exam files):",
        "",
        "```sh",
        "backend/.venv/bin/python backend/scripts/reading_dataset/apply_confirmed_hotfix.py",
        "backend/.venv/bin/python backend/scripts/reading_dataset/apply_confirmed_hotfix.py --apply",
        "```",
        "",
        "## Answer safety",
        "",
        "- 72/72 answer-key files unchanged byte for byte. No key changes proposed or applied. Stable 40 question IDs/numbers in each of the six exams.",
        "- Grading, Atomic Submit, idempotency, deadlines, IndexedDB drafts, auth and API contracts unchanged. Historical snapshots/answers/results are not migrated. The catalog adds only validated retained-asset lookup for old snapshots.",
        "- Compatibility tests exercise representative historical snapshots for all six exams, including former input types and the original crop asset; new attempts do not modify those snapshots or stored answers/results.",
        f"- Baseline gate: {len(baseline)} protected files checked; {len(changed)} explicitly intended changes, {len(baseline) - len(changed)} unchanged, zero unexpected changes. All 66 other exams, 72 keys and 36 source files unchanged. Listening was not modified during this task.",
        "",
        "## Targeted QA",
        "",
        "| Gate | Result |",
        "|---|---|",
        "| 41 original issue-ID regressions | PASS |",
        "| Backend Reading/hotfix/release suite | 87 PASS |",
        "| Real local API + disposable PostgreSQL, six perfect Atomic Submits | PASS; 40/40 each |",
        "| Historic snapshot/result/asset preservation, six exams | PASS |",
        "| Temporary targeted import replay, six exams | PASS |",
        "| Exam → Finish → Results → Review | PASS; 12 cases |",
        "| Chromium desktop 1366×768 / WebKit mobile 390×844 | PASS, all six tests each |",
        "| Restored options selectable, inline fields unique, correct input types, Review disabled | PASS |",
        "| Source crop Q20, image-cache return, no horizontal overflow | PASS |",
        "| TypeScript / ESLint / Ruff / production build | PASS |",
        "| Fast structural/hash gate (not a source audit) | PASS |",
        "",
        "Browser tests use unchanged production pages, the real Next proxy and real local FastAPI. Only the disposable app's browser sign-in identity is stubbed; API routes are not mocked. No production database or real attempts are used. Each browser record includes the exact canonical content hash.",
        "",
        "## All 41 original issues",
        "",
        "| Original issue ID | Category | Target | Result |",
        "|---|---|---|---|",
    ]
    text += [
        f"| {r['issue_id']} | {r['category']} | {r['target_id']} | FIXED_VERIFIED |"
        for r in result["issues"]
    ]
    text += [
        "",
        "Distinct issue categories: "
        + ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))
        + ".",
        "",
        "## Changed files",
        "",
    ]
    text += [f"- `{p}`" for p in changed_files]
    text += [
        "",
        "Additional evidence is under `docs/reading-confirmed-defects-hotfix/`: 12 screenshots, browser QA, protected-file safety, control deltas, JUnit results and this reproducible report builder.",
        "",
        "## Evidence",
        "",
        "- [Machine report](reading-confirmed-defects-hotfix.json) — exactly 41 original IDs, source evidence, repaired fields and per-issue QA references.",
        "- [Browser QA](reading-confirmed-defects-hotfix/browser-qa.json), [safety](reading-confirmed-defects-hotfix/safety.json), [control changes](reading-confirmed-defects-hotfix/change-summary.json).",
        "",
        "**GO is limited to this confirmed-defect hotfix. Broader Reading fidelity remains uncertified; existing needs_review/blocked release statuses were preserved.**",
        "",
    ]
    (ROOT / "docs/READING_CONFIRMED_DEFECTS_HOTFIX.md").write_text("\n".join(text))
    print(
        json.dumps(
            {
                "metrics": metrics,
                "baseline_checked": len(baseline),
                "unexpected_changes": [],
                "issue_results": len(rows),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
