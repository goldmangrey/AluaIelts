"""Source-reviewed overlays. Stale transcriptions fail closed instead of drifting silently."""

import copy
import hashlib
import json
from functools import lru_cache
from pathlib import Path


def fingerprint(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()


@lru_cache(maxsize=1)
def records():
    from engine import ROOT

    data = json.loads(Path(__file__).with_name("content_repairs.json").read_text())
    for rows in data.values():
        identifiers = [row.get("group_id", row.get("passage_id")) for row in rows]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("Duplicate content repair/review target")
        for row in rows:
            pdf = (ROOT / row["pdf_file"]).resolve()
            if not pdf.is_relative_to(ROOT / "ieltsbooks"):
                raise ValueError("Repair source must be a local original PDF")
            if hashlib.sha256(pdf.read_bytes()).hexdigest() != row["pdf_sha256"]:
                raise ValueError("Reviewed PDF changed: " + row["pdf_file"])
    return data


def apply_repairs(exam):
    passages = {p["id"]: p for p in exam["passages"]}
    groups = {g["id"]: g for p in exam["passages"] for g in p["question_groups"]}
    for kind, targets, id_field, allowed in (
        ("passages", passages, "passage_id", {"content"}),
        ("groups", groups, "group_id", {
            "instructions", "content_blocks", "constraints", "options", "questions",
            "assets", "representation", "source_reference", "source_verified", "type",
        }),
    ):
        for row in records()[kind]:
            target_id = row[id_field]
            if not target_id.startswith(exam["id"] + "-p-"):
                continue
            target = targets[target_id]
            original = target["content"] if kind == "passages" else target
            if fingerprint(original) != row["expected_sha256"]:
                raise ValueError("Repair target changed; recheck PDF: " + target_id)
            if not set(row["set"]).issubset(allowed):
                raise ValueError("Unsupported repair field: " + target_id)
            before = [(q["id"], q["number"], q["answer_input_type"])
                      for q in target.get("questions", [])]
            target.update(copy.deepcopy(row["set"]))
            after = [(q["id"], q["number"], q["answer_input_type"])
                     for q in target.get("questions", [])]
            if before != after:
                raise ValueError("Repair changed answer identity: " + target_id)
    for row in records()["reviews"]:
        if row["group_id"].startswith(exam["id"] + "-p-"):
            group = groups[row["group_id"]]
            passage = next(p for p in passages.values() if group in p["question_groups"])
            if (fingerprint(group) != row["expected_group_sha256"]
                    or fingerprint(passage["content"]) != row["expected_content_sha256"]):
                raise ValueError("Source review is stale: " + row["group_id"])


def blocked_reviews(exam_id):
    return [row for row in records()["reviews"]
            if row["status"] == "BLOCKED" and row["group_id"].startswith(exam_id + "-p-")]
