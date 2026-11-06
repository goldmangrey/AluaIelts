"""Validate all 72 imports. Default checks technical integrity; --require-ready
also fails for incomplete editorial/source/key verification. Audio is excluded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from importer import DEFAULT_OUTPUT, HERE, ROOT
from jsonschema import Draft202012Validator
from PIL import Image
from visual_materials import REGISTRY as VISUAL_REGISTRY


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(root, require_ready=False, input_root=None):
    errors = []
    warnings = []

    def check(condition, location, message):
        if not condition:
            errors.append({"location": location, "message": message})

    manifest = read(root / "manifest.json")
    assets = {a["asset_id"]: a for a in read(root / "qa/assets.json")["assets"]}
    exam_schema = Draft202012Validator(read(root / "schemas/listening_exam.schema.json"))
    key_schema = Draft202012Validator(read(root / "schemas/listening_private_key.schema.json"))
    expected = {
        f"cambridge-{b:02}-test-{t:02}"
        for b in range(4, 22)
        for t in (range(5, 9) if b == 12 else range(1, 5))
    }
    exams = {p.stem: p for p in (root / "exams").glob("*.json")}
    check(set(exams) == expected, "exams", "Exactly 72 canonical exam IDs required")
    check(
        {p.stem for p in (root / "keys").glob("*.json")} == expected,
        "keys",
        "Private keys must cover exactly the canonical exam IDs",
    )
    check(
        {e["exam_id"] for e in manifest["exams"]} == expected, "manifest", "Catalog/exam IDs differ"
    )
    check(
        manifest["stage"] == 1 and manifest["audio_in_scope"] is False,
        "manifest",
        "Stage 1 must not require audio",
    )
    for name, hashed in manifest["generator_sha256"].items():
        check(
            digest(HERE / name) == hashed,
            "generator/" + name,
            "Generator/review file changed; rebuild required",
        )
    if "visual_materials_sha256" in manifest:
        check(
            digest(root / "qa/visual_materials.json") == manifest["visual_materials_sha256"],
            "visual_materials",
            "Visual registry changed; rebuild required",
        )
        if VISUAL_REGISTRY.exists():
            check(
                digest(VISUAL_REGISTRY) == manifest["visual_materials_sha256"],
                "visual_materials/input",
                "Editorial visual input changed; rebuild required",
            )
    for name, hashed in manifest["schema_sha256"].items():
        check(
            digest(root / "schemas" / name) == hashed,
            "schemas/" + name,
            "Schema changed since generation",
        )
    # Verify every deduplicated source artifact, not merely existence.
    for aid, a in assets.items():
        p = root / a["relative_path"]
        check(p.resolve().is_relative_to(root.resolve()), aid, "Asset path escapes dataset")
        check(p.exists(), aid, "Missing asset")
        if not p.exists():
            continue
        check(
            p.stat().st_size == a["byte_size"] and digest(p) == a["sha256"],
            aid,
            "Asset bytes/hash mismatch",
        )
        with Image.open(p) as im:
            check(list(im.size) == [a["width"], a["height"]], aid, "Image dimensions mismatch")
            im.verify()
        check(a["visibility"] in ("public", "private"), aid, "Unknown asset visibility")
        check(
            a["relative_path"].startswith("assets/" + a["visibility"] + "/"),
            aid,
            "Visibility/path mismatch",
        )
        if "answer_key_evidence" in a["roles"]:
            check(a["visibility"] == "private", aid, "Official key image is public")
    all_ids = set()
    summaries = []
    for eid, path in sorted(exams.items()):
        d = read(path)
        key = read(root / "keys" / path.name)
        qa = read(root / "qa/exams" / path.name)
        for label, doc, sv in [("exam", d, exam_schema), ("key", key, key_schema)]:
            for err in sv.iter_errors(doc):
                errors.append(
                    {
                        "location": eid + "/" + label + "/" + ".".join(map(str, err.path)),
                        "message": err.message,
                    }
                )
        check(d["exam_id"] == key["exam_id"] == eid, eid, "Document ID mismatch")
        check(
            [p["part_number"] for p in d["parts"]] == [1, 2, 3, 4],
            eid,
            "Four ordered parts required",
        )
        check(
            d["printed_test_number"] == d["local_ordinal"] + (4 if d["book"] == 12 else 0),
            eid,
            "Printed/local ordinal mapping mismatch",
        )
        public_assets = {a["asset_id"] for a in d["assets"]}
        for a in d["assets"]:
            check(a["asset_id"] in assets, eid, "Unregistered public image")
            if a["asset_id"] in assets:
                check(
                    assets[a["asset_id"]]["visibility"] == "public",
                    eid,
                    "Private image leaked into public exam",
                )
                check(
                    a["sha256"] == assets[a["asset_id"]]["sha256"],
                    eid,
                    "Public image digest mismatch",
                )

        def no_leak(node, location):
            if isinstance(node, dict):
                for k, v in node.items():
                    check(
                        k
                        not in {
                            "official_answer",
                            "source_notation",
                            "expected_units",
                            "explicit_slash_forms",
                            "correct_answer",
                            "correct_option",
                            "answer_key",
                            "source_header",
                        },
                        location,
                        "Private answer field leaked: " + k,
                    )
                    no_leak(v, location + "." + k)
            elif isinstance(node, list):
                for ix, v in enumerate(node):
                    no_leak(v, location + f"[{ix}]")
            elif isinstance(node, str):
                check(
                    "/Users/" not in node
                    and not re.search(
                        r"\b(?:NEEDS_REVIEW|SOURCE_REQUIRED|TODO|TBD|placeholder)\b", node
                    ),
                    location,
                    "Absolute local path or unresolved placeholder leaked",
                )
                check("assets/private/" not in node, location, "Private asset path leaked")

        no_leak(d, eid)
        qs = []
        groupids = set()
        for part in d["parts"]:
            pn = part["part_number"]
            lo, hi = (pn - 1) * 10 + 1, pn * 10
            check(part["question_range"] == [lo, hi], eid, "Part range mismatch")
            materials = part.get("visual_materials")
            if materials is not None:
                canonical = [m["asset_id"] for m in materials]
                alternatives = [a for m in materials for a in m["alternative_asset_ids"]]
                check(
                    len(set(canonical + alternatives)) == len(canonical + alternatives),
                    eid,
                    "Visual alternatives overlap",
                )
                check(
                    set(canonical + alternatives) <= public_assets,
                    eid,
                    "Missing reviewed visual asset",
                )
                check(
                    part["supporting_assets"] == canonical,
                    eid,
                    "Part images differ from reviewed material order",
                )
                check(
                    [m["display_order"] for m in materials] == list(range(1, len(materials) + 1)),
                    eid,
                    "Visual display order is not explicit/unique",
                )
                for m in materials:
                    check(
                        lo <= m["question_range"][0] <= m["question_range"][1] <= hi,
                        eid,
                        "Visual material outside Part",
                    )
            check(
                part["audio_mapping_key"]
                == {
                    "book": d["book"],
                    "printed_test_number": d["printed_test_number"],
                    "local_ordinal": d["local_ordinal"],
                    "part_number": pn,
                },
                eid,
                "Future audio identity mismatch",
            )
            declared = []
            for group in part["groups"]:
                gid = group["group_id"]
                check(gid not in groupids, eid, "Duplicate group ID")
                groupids.add(gid)
                gl, gh = group["question_range"]
                declared.extend(range(gl, gh + 1))
                check(lo <= gl <= gh <= hi, gid, "Group outside part")
                if materials is not None:
                    expected_images = [
                        m["asset_id"]
                        for m in materials
                        if m["question_range"][0] <= gh and gl <= m["question_range"][1]
                    ]
                    check(
                        group["supporting_assets"] == expected_images,
                        gid,
                        "Group has out-of-range/unordered visual material",
                    )
                check(bool(group["instructions"].strip()), gid, "Missing instructions")
                check(set(group["supporting_assets"]) <= public_assets, gid, "Missing group image")
                if group["presentation_mode"] == "image_backed":
                    check(
                        bool(group["supporting_assets"]),
                        gid,
                        "Image-backed group has no original image",
                    )
                bank = group["answer_bank"]
                opts = bank["options"] if bank else []
                if opts:
                    check(
                        len({o["label"] for o in opts}) == len(opts),
                        gid,
                        "Repeated shared bank labels",
                    )
                    letter_range = re.search(
                        r"\b([A-K])\s*[-–—]\s*([A-K])\b", group["instructions"]
                    )
                    if letter_range:
                        expected_labels = {
                            chr(c) for c in range(ord(letter_range[1]), ord(letter_range[2]) + 1)
                        }
                        check(
                            {o["label"] for o in opts} == expected_labels,
                            gid,
                            "Shared bank is incomplete relative to the printed label range",
                        )
                for q in group["questions"]:
                    n = q["question_number"]
                    qid = q["question_id"]
                    qs.append(q)
                    check(qid == eid + f"-q{n:02}", qid, "Unstable question ID")
                    check(qid not in all_ids, qid, "Duplicate question ID")
                    all_ids.add(qid)
                    check(gl <= n <= gh, qid, "Question outside group range")
                    check(
                        q["prompt"] is not None or bool(q.get("visual_binding")),
                        qid,
                        "Neither real prompt nor typed visual binding",
                    )
                    if q["renderable"]:
                        check(
                            not q["issues"] and q["input_type"] != "unresolved",
                            qid,
                            "Renderable question has unresolved issues/type",
                        )
                        if q["input_type"] in ("select", "multi_select"):
                            effective = q["options"] or opts
                            check(
                                len(effective) >= 2,
                                qid,
                                "Choice input without a complete option bank",
                            )
                            if group["question_type"] == "multiple_choice_single" and re.search(
                                r"\bA\s*,\s*B\s*(?:,\s*)?or\s*C\b",
                                group["instructions"],
                            ):
                                check(
                                    {o["label"] for o in effective} == {"A", "B", "C"},
                                    qid,
                                    "Single choice lost one of the printed A/B/C options",
                                )
                            for op in effective:
                                check(
                                    bool(op["text"]) or bool(op.get("visual_reference")),
                                    qid,
                                    "Invented empty choice label without spatial evidence",
                                )
                            check(
                                q["answer_bank_id"]
                                == (bank["bank_id"] if bank and not q["options"] else None),
                                qid,
                                "Shared answer-bank reference mismatch",
                            )
                        else:
                            c = q["constraints"]
                            check(
                                c["max_words"] is not None or c["max_numbers"] is not None,
                                qid,
                                "Text input lacks established word/number limits",
                            )
                    if q["verification"]["status"] == "source_verified":
                        check(
                            q["verification"].get("pdf_pages") and q["verification"].get("pdf"),
                            qid,
                            "Source-verified without source page evidence",
                        )
                    for span in q["blank_references"]:
                        check(
                            span["line"] >= group["source_reference"]["line_start"]
                            and span["line"] <= group["source_reference"]["line_end"],
                            qid,
                            "Blank anchor outside source group",
                        )
                        check(
                            span["start"] >= 0 and span["end"] > span["start"],
                            qid,
                            "Invalid blank span",
                        )
                    for op in q["options"]:
                        check(bool(op["text"]), qid, "MCQ option has no original text")
                if group["selection"]:
                    sel = group["selection"]
                    check(
                        sel["answer_slots"] == list(range(gl, gh + 1)),
                        gid,
                        "Multiple answers lost an answer position",
                    )
                    check(
                        sel["maximum_selected"] == sel["minimum_selected"],
                        gid,
                        "Selection cardinality mismatch",
                    )
                    check(
                        sel["maximum_selected"] >= gh - gl + 1,
                        gid,
                        "Too few choices for multi-answer slots",
                    )
                for block in group["content_blocks"]:
                    if block["kind"] == "source_line":
                        for blank in block["blanks"]:
                            check(
                                gl <= blank["question_number"] <= gh,
                                gid,
                                "Blank token references another group",
                            )
                            check(
                                0 <= blank["start"] < blank["end"] <= len(block["text"]),
                                gid,
                                "Blank token exceeds source string",
                            )
            check(
                declared == list(range(lo, hi + 1)),
                eid + f"/p{pn}",
                "Group ranges have missing/duplicate positions",
            )
            check(
                set(part["supporting_assets"]) <= public_assets,
                eid,
                "Part references an absent image",
            )
        numbers = [q["question_number"] for q in qs]
        check(len(set(numbers)) == len(numbers), eid, "Duplicate positions")
        missing = sorted(set(range(1, 41)) - set(numbers))
        blocked = sorted(q["question_number"] for q in qs if not q["renderable"])
        # Incomplete data are acceptable ONLY with precise, persisted exceptions.
        for n in missing:
            check(
                any(
                    i.get("question_number") == n and i["severity"] == "critical"
                    for i in qa["issues"]
                ),
                eid,
                f"Unreported missing position {n}",
            )
        for n in blocked:
            check(
                any(
                    i.get("question_number") == n and i["severity"] == "critical"
                    for i in qa["issues"]
                ),
                eid,
                f"Unreported blocked position {n}",
            )
        ans = key["answers"]
        ansnums = [a["question_number"] for a in ans]
        check(len(set(ansnums)) == len(ansnums), eid, "Duplicate answer-key position")
        for a in ans:
            check(
                a["question_id"] == eid + f"-q{a['question_number']:02}",
                eid,
                "Key alignment mismatch",
            )
            check(bool(a["official_answer"].strip()), eid, "Empty official key")
            for aid in a["source_reference"]["evidence_assets"]:
                check(
                    aid in assets and assets[aid]["visibility"] == "private",
                    eid,
                    "Key evidence absent or exposed publicly",
                )
            if a["verification"]["status"] == "key_verified":
                check(
                    bool(a["source_reference"]["evidence_assets"]),
                    eid,
                    "Verified key lacks actual official image",
                )
        for kg in key["unordered_groups"]:
            check(
                len(kg["question_numbers"]) == len(kg["expected_units"]),
                eid,
                "Unordered set cardinality mismatch",
            )
            check(
                all(
                    next((a for a in ans if a["question_number"] == n), {}).get("unordered_group")
                    == kg["group_id"]
                    for n in kg["question_numbers"]
                ),
                eid,
                "Unordered key-group references are not reciprocal",
            )
        counts = {
            "parsed_questions": len(qs),
            "interactive_questions": sum(q["renderable"] for q in qs),
            "source_verified_questions": sum(
                q["verification"]["status"] == "source_verified" for q in qs
            ),
            "keys_present": len(ans),
            "key_verified_positions": sum(
                a["verification"]["status"] == "key_verified" for a in ans
            ),
            "missing_positions": missing,
            "blocked_positions": blocked,
        }
        counts["complete_question_content"] = counts["interactive_questions"] == 40
        counts["complete_verified_keys"] = counts["key_verified_positions"] == 40
        counts["ready_for_stage2"] = (
            counts["complete_question_content"]
            and counts["source_verified_questions"] == 40
            and counts["complete_verified_keys"]
        )
        check(d["validation"] == counts, eid, "Stored exam statistics are incorrect")
        check(qa["counts"] == counts, eid, "QA counts differ")
        if missing or blocked or not counts["ready_for_stage2"]:
            warnings.append({"exam_id": eid, "counts": counts})
        summaries.append({"exam_id": eid, **counts})
    totals = {
        name: sum(s[name] for s in summaries)
        for name in [
            "parsed_questions",
            "interactive_questions",
            "source_verified_questions",
            "keys_present",
            "key_verified_positions",
            "complete_question_content",
            "complete_verified_keys",
            "ready_for_stage2",
        ]
    }
    for name, total in totals.items():
        check(manifest["totals"][name] == total, "totals/" + name, "Manifest statistics mismatch")
    if input_root:
        for book in read(root / "qa/input_inventory.json"):
            for source in book["files"]:
                p = input_root / source["file"]
                check(
                    p.exists() and digest(p) == source["sha256"],
                    source["file"],
                    "Original input changed",
                )
            if book["pdf"]:
                pdf = ROOT / book["pdf"]["file"]
                check(
                    pdf.exists() and digest(pdf) == book["pdf"]["sha256"],
                    book["pdf"]["file"],
                    "Original PDF changed",
                )
    ready = totals["ready_for_stage2"] == 72
    return {
        "technical_integrity": not errors,
        "all_question_positions_present": totals["parsed_questions"] == 2880,
        "all_official_keys_present": totals["keys_present"] == 2880,
        "stage1_all_ready": ready,
        "audio_checked": False,
        "totals": totals,
        "errors": errors,
        "exams_requiring_editorial_review": len(warnings),
        "exit_code": 1 if errors or (require_ready and not ready) else 0,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--require-ready", action="store_true")
    ap.add_argument("--verify-input", type=Path)
    ap.add_argument("--report", type=Path)
    args = ap.parse_args()
    result = validate(args.dataset, args.require_ready, args.verify_input)
    if args.report:
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(result["exit_code"])


if __name__ == "__main__":
    main()
