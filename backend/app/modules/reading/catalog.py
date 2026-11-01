"""Fail-closed, versioned local catalog. Never imports the PDF pipeline."""

import copy
import hashlib
import json
import re
import struct
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

from app.core.exceptions import NotFoundError

DATASET = Path(__file__).resolve().parents[2] / "content/reading_v1"
POLICY_VERSION = "private-practice-v1"
CRITICAL_ISSUES = {
    "paragraph_labels_missing",
    "paragraph_labels_ambiguous",
    "source_obscured_by_watermark",
    "source_option_label_anomaly",
    "suspected_question_corruption",
    "missing_options",
    "missing_diagram",
    "unknown_type",
    "question_positions",
    "key_positions",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def questions(exam: dict) -> dict:
    return {
        q["id"]: (p, g, q)
        for p in exam["passages"]
        for g in p["question_groups"]
        for q in g["questions"]
    }


class ReadingCatalog:
    def __init__(self, base: Path = DATASET):
        self.base = base.resolve()
        self.manifest = self.read("manifest.json")
        self.audit = self.read("audit_report.json")
        self.exams: dict[str, dict] = {}
        self.keys: dict[str, dict] = {}
        self.entries: dict[str, dict] = {}
        self.assets: dict[str, dict] = {}
        schemas = []
        for name in ("reading_exam.schema.json", "reading_answer_key.schema.json"):
            raw = self.path("schema/" + name).read_bytes()
            if digest(raw) != self.manifest["schema_sha256"][name]:
                raise ValueError("Reading schema hash mismatch")
            schema = json.loads(raw)
            Draft202012Validator.check_schema(schema)
            schemas.append(Draft202012Validator(schema))
        for entry in self.manifest["exams"]:
            eid = entry["id"]
            reasons = []
            warnings = [i for i in self.audit["issues"] if i["exam_id"] == eid]
            try:
                exam, key = self.read(entry["exam_path"]), self.read(entry["answer_key_path"])
                for field, expected in (
                    ("exam_path", "sha256"),
                    ("answer_key_path", "answer_key_sha256"),
                ):
                    if digest(self.path(entry[field]).read_bytes()) != entry[expected]:
                        reasons.append("hash_mismatch:" + field)
                schemas[0].validate(exam)
                schemas[1].validate(key)
                reasons.extend(self.check(exam, key, entry))
                self.exams[eid], self.keys[eid] = exam, key
            except (ValueError, KeyError, OSError, TypeError) as exc:
                reasons.append("invalid_content:" + type(exc).__name__)
            except Exception as exc:
                # jsonschema.ValidationError: isolate the broken exam, not the whole library.
                from jsonschema.exceptions import ValidationError

                if not isinstance(exc, ValidationError):
                    raise
                reasons.append("schema_validation_failed:" + exc.json_path)
            reasons.extend(i["code"] for i in warnings if i["code"] in CRITICAL_ISSUES)
            if entry["content_status"] == "blocked":
                reasons.append("content_status_blocked")
            self.entries[eid] = {
                "exam_id": eid,
                "source_book": entry["source_book"],
                "source_test_number": entry["source_test_number"],
                "test_ordinal": entry["test_ordinal"],
                "dataset_version": self.manifest["dataset_version"],
                "content_revision": self.manifest["content_revision"],
                "content_hash": entry["sha256"],
                "answer_key_hash": entry["answer_key_sha256"],
                "content_status": entry["content_status"],
                "enabled_for_private_practice": not reasons,
                "not_fully_proofread": entry["content_status"] != "ready",
                "question_count": entry["question_count"],
                "passage_count": entry["passage_count"],
                "exclusion_reasons": sorted(set(reasons)),
                "warnings": warnings,
                "practice_policy_version": POLICY_VERSION,
            }

    def path(self, relative: str) -> Path:
        path = (self.base / relative).resolve()
        if not path.is_relative_to(self.base):
            raise ValueError("Content path escapes dataset")
        return path

    def read(self, relative: str) -> dict:
        return json.loads(self.path(relative).read_bytes())

    def check(self, exam: dict, key: dict, entry: dict) -> list[str]:
        issues = []
        eid = entry["id"]
        qs = questions(exam)
        ks = {a["question_id"]: a for a in key["answers"]}
        if (
            exam["id"] != eid
            or key["exam_id"] != eid
            or exam["dataset_version"] != self.manifest["dataset_version"]
            or key["dataset_version"] != exam["dataset_version"]
        ):
            issues.append("identity_version_mismatch")
        if (
            len(exam["passages"]) != 3
            or len(qs) != 40
            or len(key["answers"]) != 40
            or set(qs) != set(ks)
            or exam["question_count"] != 40
            or sorted(q[2]["number"] for q in qs.values()) != list(range(1, 41))
        ):
            issues.append("incomplete_exam")
        if re.search(
            r'OFFICIAL ANSWERS|ANSWER KEY|"canonical_answer"|"accepted_answers"',
            json.dumps(exam),
            re.I,
        ):
            issues.append("private_key_in_public_content")
        previous = 0
        asset_paths = []
        ids = set()
        if sorted(p["number"] for p in exam["passages"]) != [1, 2, 3]:
            issues.append("passage_numbering")
        for p in exam["passages"]:
            if p["id"] in ids:
                issues.append("duplicate_id")
            ids.add(p["id"])
            if not p["content"] or not "".join(b["text"] for b in p["content"]).strip():
                issues.append("empty_passage")
            nums = [q["number"] for g in p["question_groups"] for q in g["questions"]]
            if (
                sorted(nums) != p["question_numbers"]
                or not nums
                or min(nums) <= previous
                or (p["source_question_range"] and nums != p["source_question_range"])
            ):
                issues.append("passage_question_linkage")
            previous = max(nums, default=previous)
            for g in p["question_groups"]:
                if g["id"] in ids:
                    issues.append("duplicate_id")
                ids.add(g["id"])
                aids = {a["id"] for a in g["assets"]}
                if any(
                    b["type"] == "image" and b["asset_id"] not in aids for b in g["content_blocks"]
                ):
                    issues.append("dangling_image_block")
                if any(
                    b["type"] == "table" and any(len(row) != len(b["columns"]) for row in b["rows"])
                    for b in g["content_blocks"]
                ):
                    issues.append("ragged_table")
                if g["type"] == "matching_information":
                    expected = set(g["constraints"]["allowed_values"])
                    actual = {b["label"] for b in p["content"] if b["label"]}
                    if expected - actual:
                        issues.append("paragraph_labels_missing")
                if (
                    not g["instructions"].strip()
                    or g["type"] == "unknown"
                    or g["question_numbers"] != [q["number"] for q in g["questions"]]
                ):
                    issues.append("invalid_question_group")
                if (
                    g["type"] == "diagram_labelling"
                    or g["representation"] == "source_image_with_inputs"
                ) and not g["assets"]:
                    issues.append("missing_required_image")
                for a in g["assets"]:
                    raw = self.path(a["path"]).read_bytes()
                    if (
                        digest(raw) != a["sha256"]
                        or raw[:8] != b"\x89PNG\r\n\x1a\n"
                        or struct.unpack(">II", raw[16:24]) != (a["width"], a["height"])
                    ):
                        issues.append("invalid_asset:" + a["id"])
                    self.assets[a["id"]] = a
                    asset_paths.append(a["path"])
                for q in g["questions"]:
                    if q["id"] in ids:
                        issues.append("duplicate_id")
                    ids.add(q["id"])
                    if (
                        q["id"] != f"{eid}-q-{q['number']:02}"
                        or q["group_id"] != g["id"]
                        or q["type"] != g["type"]
                    ):
                        issues.append("question_identity_mismatch")
                    if q["answer_input_type"] in {"single_select", "multi_select"} and not (
                        q["options"]
                        or g["options"]
                        or g["assets"]
                        or q["constraints"]["allowed_values"]
                    ):
                        issues.append("missing_options:" + q["id"])
        if sorted(asset_paths) != sorted(entry["assets"]):
            issues.append("asset_manifest_mismatch")
        for a in key["answers"]:
            if a["question_id"] != f"{eid}-q-{a['number']:02}":
                issues.append("key_identity_mismatch")
            group = a["grading_group"]
            if group:
                members = [
                    x
                    for x in key["answers"]
                    if x["grading_group"] and x["grading_group"]["id"] == group["id"]
                ]
                if (
                    len(group["expected_units"]) != len(group["question_numbers"])
                    or sorted(x["number"] for x in members) != group["question_numbers"]
                    or any(x["grading_group"] != group for x in members)
                ):
                    issues.append("invalid_grading_group")
        return issues

    def enabled(self, eid: str) -> dict:
        entry = self.entries.get(eid)
        if not entry or not entry["enabled_for_private_practice"]:
            raise NotFoundError(
                "Exam is unavailable for private practice.", "reading_exam_unavailable"
            )
        return entry

    @staticmethod
    def public_exam(exam: dict) -> dict:
        # Explicit schema projection: private schemas and filesystem metadata cannot leak.
        data = {
            k: copy.deepcopy(exam[k])
            for k in (
                "id",
                "dataset_version",
                "source_book",
                "source_test_number",
                "test_ordinal",
                "module",
                "duration_seconds",
                "question_count",
                "content_status",
                "passages",
            )
        }
        for p in data["passages"]:
            p.pop("source_reference", None)
            p.pop("source_pages", None)
            p.pop("source_question_range", None)
            p["text_range_contract"] = "unicode-codepoints:content-block-text-v1"
            for g in p["question_groups"]:
                g.pop("source_reference", None)
                g.pop("source_verified", None)
                g["assets"] = [
                    {
                        "id": a["id"],
                        "mime_type": a["mime_type"],
                        "width": a["width"],
                        "height": a["height"],
                        "sha256": a["sha256"],
                        "url": "/api/v1/reading/assets/" + a["id"],
                    }
                    for a in g["assets"]
                ]
                for q in g["questions"]:
                    q.pop("source_reference", None)
        return data


@lru_cache
def get_catalog() -> ReadingCatalog:
    return ReadingCatalog()
