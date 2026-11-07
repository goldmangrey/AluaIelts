"""Stage 1 is read-only. Content mode and live filesystem availability are independent."""

import copy
import hashlib
import json
from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings
from app.core.exceptions import NotFoundError, ValidationError
from app.modules.listening.source_materials import enrich_sources

CONTENT = Path(__file__).resolve().parents[2] / "content"


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def questions(exam):
    return {
        q["question_id"]: (p, g, q)
        for p in exam["parts"]
        for g in p["groups"]
        for q in g["questions"]
    }


def confined(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if (
        Path(relative).is_absolute()
        or ".." in Path(relative).parts
        or not path.is_relative_to(root)
    ):
        raise NotFoundError("Media not found.")
    if not path.is_file():
        raise NotFoundError("Media is not available on this server.", "listening_media_unavailable")
    return path


def audio_mime(path):
    """Sniff supported audio containers with bounded reads; never trust a suffix or snapshot."""
    with Path(path).open("rb") as source:
        header = source.read(32)
        # ISO BMFF (M4A/AAC): an ftyp box with a supported major/compatible brand.
        if header[4:8] == b"ftyp":
            size = int.from_bytes(header[:4], "big")
            if 16 <= size <= 65536 and size % 4 == 0:
                source.seek(0)
                box = source.read(size)
                brands = [box[8:12]] + [box[i : i + 4] for i in range(16, len(box), 4)]
                if len(box) == size and any(
                    b in {b"M4A ", b"M4B ", b"isom", b"iso2", b"mp41", b"mp42"} for b in brands
                ):
                    return "audio/mp4"
            raise NotFoundError("Unsupported audio container.", "listening_media_unavailable")
        offset = 0
        if header[:3] == b"ID3":
            if len(header) < 10 or any(b & 0x80 for b in header[6:10]):
                raise NotFoundError("Invalid audio header.", "listening_media_unavailable")
            tag_size = sum(b << shift for b, shift in zip(header[6:10], (21, 14, 7, 0)))
            offset = 10 + tag_size
            if header[3] == 4 and header[5] & 0x10:  # ID3v2.4 footer
                offset += 10
        source.seek(offset)
        data = source.read(65536)
        for i in range(len(data) - 3):
            a, b, c = data[i : i + 3]
            if (
                a == 0xFF
                and b & 0xE0 == 0xE0
                and b & 0x18 != 0x08  # valid MPEG version
                and b & 0x06 == 0x02  # Layer III
                and 0 < c >> 4 < 15
                and c & 0x0C != 0x0C
            ):
                return "audio/mpeg"
    raise NotFoundError("Unsupported audio container.", "listening_media_unavailable")


class ListeningCatalog:
    def __init__(self, root=CONTENT / "listening_v1", audio_root=None, audio_manifest=None):
        self.root = Path(root)
        self.audio_root = Path(audio_root or get_settings().listening_audio_root)
        self.manifest = json.loads((self.root / "manifest.json").read_text())
        self.exams = {
            p.stem: json.loads(p.read_text()) for p in sorted((self.root / "exams").glob("*.json"))
        }
        self.keys = {
            eid: json.loads((self.root / "keys" / f"{eid}.json").read_text()) for eid in self.exams
        }
        media = audio_manifest or json.loads(
            (CONTENT / "listening_audio_v1/audio_manifest.json").read_text()
        )
        self.audio = {}
        for item in media["items"]:
            self.audio.setdefault(item["exam_id"], {})[item["part_number"]] = item
        if len(self.exams) != 72 or sum(len(v) for v in self.audio.values()) != 288:
            raise RuntimeError("Listening catalog/audio identity contract is incomplete")
        for eid, exam in self.exams.items():
            for part in exam["parts"]:
                audio = self.audio[eid][part["part_number"]]
                if any(audio[k] != v for k, v in part["audio_mapping_key"].items()):
                    raise RuntimeError("Audio identity does not match Stage 1")

    def exam(self, eid):
        if eid not in self.exams:
            raise NotFoundError("Listening exam not found.")
        return self.exams[eid]

    def mode(self, eid):
        exam = self.exam(eid)
        qs = questions(exam)
        keys = self.keys[eid]["answers"]
        if (
            len(qs) != 40
            or {q["question_number"] for _, _, q in qs.values()} != set(range(1, 41))
            or any(not q["renderable"] for _, _, q in qs.values())
        ):
            return "blocked"
        for asset in exam["assets"]:
            try:
                if confined(self.root, asset["relative_path"]).stat().st_size != asset["byte_size"]:
                    return "blocked"
            except NotFoundError:
                return "blocked"
        if len(keys) == 0:
            return "ungraded"
        if len(keys) != 40 or {k["question_id"] for k in keys} != set(qs):
            return "blocked"
        if all(q["verification"]["status"] == "source_verified" for _, _, q in qs.values()) and all(
            k["verification"]["status"] == "key_verified" for k in keys
        ):
            return "verified"
        return "preliminary"

    def audio_path(self, record):
        path = confined(self.audio_root, record["relative_path"])
        if path.stat().st_size != record["byte_size"]:
            raise NotFoundError(
                "Audio inventory needs reconciliation.", "listening_media_unavailable"
            )
        return path

    def audio_status(self, eid):
        available = []
        for part in range(1, 5):
            try:
                self.audio_path(self.audio[eid][part])
                available.append(part)
            except NotFoundError:
                pass
        return {
            "available_parts": available,
            "technically_available": len(available) == 4,
            "decode_verified_parts": sum(
                bool(a["decode_verified"]) for a in self.audio[eid].values()
            ),
            "content_mapping_verified_parts": sum(
                bool(a["content_mapping_verified"]) for a in self.audio[eid].values()
            ),
        }

    def entry(self, eid):
        e = self.exam(eid)
        mode = self.mode(eid)
        audio = self.audio_status(eid)
        return {
            "exam_id": eid,
            "book": e["book"],
            "printed_test_number": e["printed_test_number"],
            "local_ordinal": e["local_ordinal"],
            "content_mode": mode,
            "audio": audio,
            "can_start": mode != "blocked" and audio["technically_available"],
            "question_count": len(questions(e)),
            "renderable_count": sum(q["renderable"] for _, _, q in questions(e).values()),
            "content_verified": mode == "verified",
            "recording_content_verified": audio["content_mapping_verified_parts"] == 4,
            "block_reason": "Some original question positions are incomplete."
            if mode == "blocked"
            else None
            if audio["technically_available"]
            else "Audio is not available on this backend yet.",
        }

    def snapshot(self, eid):
        entry = self.entry(eid)
        if not entry["can_start"]:
            raise ValidationError(
                entry["block_reason"] or "Exam unavailable.", "listening_unavailable"
            )
        exam = self.exam(eid)
        key = self.keys[eid]
        return copy.deepcopy(
            {
                "exam": exam,
                "key": key,
                "audio": self.audio[eid],
                "mode": entry["content_mode"],
                "grading_policy": "practice-v2",
                "content_hash": digest(exam),
                "key_hash": digest(key),
                "dataset_version": self.manifest["schema_version"],
            }
        )

    def public_exam(self, exam):
        exam = enrich_sources(exam, self.exams.get(exam["exam_id"]))
        # Explicit top-level allowlist: private keys and QA are never part of this projection.
        return copy.deepcopy(
            {
                k: exam[k]
                for k in (
                    "exam_id",
                    "book",
                    "printed_test_number",
                    "local_ordinal",
                    "parts",
                    "assets",
                    "schema_version",
                )
            }
        )

    def asset(self, exam, aid):
        exam = enrich_sources(exam, self.exams.get(exam["exam_id"]))
        record = next((a for a in exam["assets"] if a["asset_id"] == aid), None)
        if not record or not record["relative_path"].startswith("assets/public/"):
            raise NotFoundError("Image not found.")
        path = confined(self.root, record["relative_path"])
        if hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
            raise NotFoundError("Image integrity failed.")
        return path


@lru_cache
def get_catalog():
    return ListeningCatalog()
