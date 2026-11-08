"""Publish only the six hash-bound confirmed-hotfix exams; never a corpus import.

Default is a dry run. Keys, sources and historical snapshots are never written.
"""

import argparse
import copy
import hashlib
import json
from pathlib import Path

from confirmed_hotfixes import apply_confirmed_hotfixes, records
from engine import DEST, digest, write
from jsonschema import Draft202012Validator


def apply(*, publish=False):
    data = records()
    manifest = json.loads((DEST / "manifest.json").read_text())
    schema = Draft202012Validator(
        json.loads((DEST / "schema/reading_exam.schema.json").read_text())
    )
    ids = {r["exam_id"] for r in data["repairs"]}
    patches = []
    for entry in manifest["exams"]:
        if entry["id"] not in ids:
            continue
        path = DEST / entry["exam_path"]
        if digest(path) != entry["sha256"]:
            raise ValueError("Existing exam manifest mismatch: " + entry["id"])
        original = json.loads(path.read_text())
        patched = copy.deepcopy(original)
        apply_confirmed_hotfixes(patched, DEST)
        schema.validate(patched)
        # The source-audit status is intentionally unchanged: this is not library certification.
        if patched != original:
            patches.append((path, patched))
        if digest(DEST / entry["answer_key_path"]) != entry["answer_key_sha256"]:
            raise ValueError("Existing answer key changed")
    if len(ids) != 6:
        raise ValueError("Confirmed hotfix scope must be exactly six exams")
    if not publish:
        return {"exams_to_write": len(patches), "issue_count": 41, "dry_run": True}
    for path, exam in patches:
        write(path, exam)
    for entry in manifest["exams"]:
        if entry["id"] in ids:
            entry["sha256"] = digest(DEST / entry["exam_path"])
            exam = json.loads((DEST / entry["exam_path"]).read_text())
            entry["assets"] = [
                a["path"]
                for p in exam["passages"]
                for g in p["question_groups"]
                for a in g["assets"]
            ]
    manifest["retained_assets"] = data["retained_assets"]
    manifest["generator_sha256"] = {
        p.name: digest(p)
        for p in sorted(Path(__file__).parent.iterdir())
        if p.suffix in {".py", ".json", ".txt"}
    }
    manifest["content_revision"] = hashlib.sha256(
        json.dumps(
            {
                "sources": manifest["sources"],
                "exams": manifest["exams"],
                "generator": manifest["generator_sha256"],
                "schemas": manifest["schema_sha256"],
                "retained_assets": manifest["retained_assets"],
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    write(DEST / "manifest.json", manifest)
    correction_path = DEST / "corrections.jsonl"
    corrections = [json.loads(line) for line in correction_path.read_text().splitlines() if line]
    corrections = [r for r in corrections if r.get("kind") != "confirmed_fidelity_v1"]
    corrections += [dict(row, kind="confirmed_fidelity_v1") for row in data["repairs"]]
    correction_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in corrections)
    )
    return {"exams_written": len(patches), "issue_count": 41, "dry_run": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write the six reviewed exam patches")
    print(json.dumps(apply(publish=parser.parse_args().apply), indent=2))
