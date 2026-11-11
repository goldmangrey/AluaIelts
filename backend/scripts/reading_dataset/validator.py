"""Strict schema, referential, release and integrity gates for Reading datasets."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sys
from pathlib import Path

import jsonschema
from engine import DEST, ROOT, structural_issues
from grading import grade_exam
from PIL import Image


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(base=DEST):
    manifest = json.loads((base / "manifest.json").read_text())
    audit = json.loads((base / "audit_report.json").read_text())
    errors = []
    content = []
    all_ids = set()
    books = collections.Counter()
    counts = collections.Counter()
    schema = json.loads((base / "schema/reading_exam.schema.json").read_text())
    ks = json.loads((base / "schema/reading_answer_key.schema.json").read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.Draft202012Validator.check_schema(ks)
    ev = jsonschema.Draft202012Validator(schema)
    kv = jsonschema.Draft202012Validator(ks)

    def error(msg):
        errors.append(msg)

    def identity(value):
        if value in all_ids:
            error("Duplicate ID " + value)
        all_ids.add(value)

    for entry in manifest["exams"]:
        eid = entry["id"]
        identity(eid)
        books[entry["source_book"]] += 1
        e = json.loads((base / entry["exam_path"]).read_text())
        k = json.loads((base / entry["answer_key_path"]).read_text())
        for label, validator, data in [("exam", ev, e), ("key", kv, k)]:
            for problem in validator.iter_errors(data):
                error(f"{eid} {label} {list(problem.path)}: {problem.message}")
        if e["id"] != eid or k["exam_id"] != eid:
            error(eid + " identity mismatch")
        if (
            e["dataset_version"] != manifest["dataset_version"]
            or k["dataset_version"] != manifest["dataset_version"]
        ):
            error(eid + " version mismatch")
        if (
            sha(base / entry["exam_path"]) != entry["sha256"]
            or sha(base / entry["answer_key_path"]) != entry["answer_key_sha256"]
        ):
            error(eid + " hash mismatch")
        if e["source_book"] == 12:
            if e["source_test_number"] != e["test_ordinal"] + 4:
                error(eid + " source test numbering changed")
        elif e["source_test_number"] != e["test_ordinal"]:
            error(eid + " source test/ordinal mismatch")
        public_text = json.dumps(e, ensure_ascii=False).upper()
        if re.search(r"OFFICIAL ANSWERS|ANSWER KEY|CANONICAL_ANSWER|ACCEPTED_ANSWERS", public_text):
            error(eid + " private answer material in public payload")
        qs = []
        previous = 0
        gids = set()
        assets = []
        for p in e["passages"]:
            identity(p["id"])
            pnums = []
            if not "".join(x["text"] for x in p["content"]).strip():
                error(eid + " empty passage")
            for g in p["question_groups"]:
                identity(g["id"])
                gids.add(g["id"])
                gnums = []
                if not g["instructions"].strip():
                    error(g["id"] + " missing instructions")
                if g["representation"] == "source_image_with_inputs" and not g["assets"]:
                    error(g["id"] + " missing image fallback")
                aid = {a["id"] for a in g["assets"]}
                for b in g["content_blocks"]:
                    if b["type"] == "image" and b["asset_id"] not in aid:
                        error(g["id"] + " dangling image block")
                    if b["type"] == "table" and any(
                        len(row) != len(b["columns"]) for row in b["rows"]
                    ):
                        error(g["id"] + " ragged table")
                for q in g["questions"]:
                    identity(q["id"])
                    qs.append(q)
                    pnums.append(q["number"])
                    gnums.append(q["number"])
                    if (
                        q["id"] != f"{eid}-q-{q['number']:02}"
                        or q["group_id"] != g["id"]
                        or q["type"] != g["type"]
                    ):
                        error(q["id"] + " bad question linkage")
                    expected = (
                        "boolean"
                        if q["type"] in ["true_false_not_given", "yes_no_not_given"]
                        else "multi_select"
                        if q["type"] == "multiple_choice_multiple"
                        else "single_select"
                        if q["type"].startswith("matching") or q["type"] == "multiple_choice_single"
                        else None
                    )
                    if expected and q["answer_input_type"] != expected:
                        error(q["id"] + " incompatible input type")
                    if re.search(
                        r"canonical_answer|accepted_answers|normalization_rules", json.dumps(q)
                    ):
                        error(q["id"] + " private answer field in public payload")
                if gnums != g["question_numbers"]:
                    error(g["id"] + " group positions mismatch")
                for a in g["assets"]:
                    identity(a["id"])
                    assets.append(a["path"])
                    path = base / a["path"]
                    if path.resolve().is_relative_to(base.resolve()) is False:
                        error(a["id"] + " asset escapes dataset")
                    if not path.exists():
                        error(a["id"] + " missing asset")
                        continue
                    if sha(path) != a["sha256"]:
                        error(a["id"] + " asset hash mismatch")
                    with Image.open(path) as image:
                        if image.size != (a["width"], a["height"]):
                            error(a["id"] + " image dimensions mismatch")
                        image.verify()
                    if not set(a["question_numbers"]) <= set(gnums):
                        error(a["id"] + " asset positions mismatch")
            if sorted(pnums) != p["question_numbers"]:
                error(p["id"] + " passage positions mismatch")
            if pnums and min(pnums) <= previous:
                error(p["id"] + " questions overlap previous passage")
            if pnums:
                previous = max(pnums)
        if sorted(assets) != sorted(entry["assets"]):
            error(eid + " manifest asset mismatch")
        qids = {q["id"] for q in qs}
        if qids != {a["question_id"] for a in k["answers"]}:
            error(eid + " question/key set mismatch")
        if len(k["answers"]) != len(qs) or e["question_count"] != len(qs):
            error(eid + " counted positions mismatch")
        knums = [a["number"] for a in k["answers"]]
        if sorted(knums) != list(range(1, 41)):
            error(eid + " keys not exactly 1–40")
        for a in k["answers"]:
            if a["question_id"] != f"{eid}-q-{a['number']:02}":
                error(eid + " key number/ID mismatch")
            group = a["grading_group"]
            if group:
                if len(group["expected_units"]) != len(group["question_numbers"]):
                    error(eid + " grading unit count mismatch")
                members = [
                    x
                    for x in k["answers"]
                    if x["grading_group"] and x["grading_group"]["id"] == group["id"]
                ]
                if sorted(x["number"] for x in members) != sorted(group["question_numbers"]):
                    error(eid + " incomplete grading group")
        probs = structural_issues(e, k, base)
        content.extend(probs)
        if e["content_status"] == "ready":
            if (
                probs
                or not e["source_verified"]
                or any(v != "source_verified" for v in e["verification"].values())
            ):
                error(eid + " invalid ready status")
        if e["content_status"] != entry["content_status"]:
            error(eid + " stale manifest status")
        # Empty responses and exact official variants exercise the complete loader/scorer.
        try:
            zero = grade_exam(e, k, {}, allow_unreleased=True)
            if zero["score"] != 0:
                error(eid + " blank submission scores points")
            sample = {a["question_id"]: a["accepted_answers"][0] for a in k["answers"]}
            result = grade_exam(e, k, sample, allow_unreleased=True)
            if not 0 <= result["score"] <= 40:
                error(eid + " score outside range")
        except (ValueError, KeyError) as ex:
            error(eid + " scorer: " + str(ex))
        counts["exams"] += 1
        counts["passages"] += len(e["passages"])
        counts["questions"] += len(qs)
        counts["answers"] += len(k["answers"])
        counts["assets"] += len(assets)
    if sorted(books) != list(range(4, 22)) or any(n != 4 for n in books.values()):
        error("Expected books 04–21 with exactly 4 tests each")
    expected = {"exams": 72, "passages": 216, "questions": 2880, "answers": 2880}
    for name, value in expected.items():
        if counts[name] != value:
            error(f"{name}: expected {value}, got {counts[name]}")
        if audit["counts"].get(name) != counts[name]:
            error("Stale audit count " + name)
    source_counts = collections.Counter(Path(src).suffix for src in manifest["sources"])
    if source_counts != {".txt": 18, ".pdf": 18}:
        error("Expected exactly 18 TXT and 18 PDF sources")
    for name, expected_hash in manifest["schema_sha256"].items():
        if sha(base / "schema" / name) != expected_hash:
            error("Schema hash mismatch " + name)
    for name, expected_hash in manifest["generator_sha256"].items():
        if sha(Path(__file__).parent / name) != expected_hash:
            error("Generator changed since build: " + name)
    revision = hashlib.sha256(
        json.dumps(
            {
                "sources": manifest["sources"],
                "exams": manifest["exams"],
                "generator": manifest["generator_sha256"],
                "schemas": manifest["schema_sha256"],
                **(
                    {"retained_assets": manifest["retained_assets"]}
                    if "retained_assets" in manifest
                    else {}
                ),
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    if revision != manifest["content_revision"]:
        error("Content revision mismatch")
    for src, h in manifest["sources"].items():
        if sha(ROOT / src) != h:
            error("Original source hash changed " + src)
    result = {
        "artifact_validation_passed": not errors,
        "counts": dict(counts),
        "errors": errors,
        "content_gate_issues": len(content),
        "source_hashes_verified": len(manifest["sources"]),
        "schema_documents_validated": counts["exams"] * 2,
        "release_ready": sum(x["content_status"] == "ready" for x in manifest["exams"]),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", type=Path, default=DEST)
    args = ap.parse_args()
    sys.exit(0 if validate(args.dataset)["artifact_validation_passed"] else 1)
