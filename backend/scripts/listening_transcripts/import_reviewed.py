"""Import only reviewed JSON + QA metadata; original archive/audio remain untouched."""

import csv
import hashlib
import io
import json
import math
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def build(archive):
    documents = {}
    with zipfile.ZipFile(archive) as z:
        audit = {
            (int(r["book"]), int(r["canonical_test"]), int(r["canonical_section"])): r
            for r in csv.DictReader(io.StringIO(z.read("QA/all_288_sections_audit.csv").decode()))
        }
        for name in z.namelist():
            if not name.endswith(".json"):
                continue
            match = re.fullmatch(
                r"Cambridge_IELTS_(\d+)/Test_(\d+)/IELTS\d+-Test \d+-Section (\d).json", name
            )
            if not match:
                raise ValueError("Unexpected JSON path")
            identity = tuple(map(int, match.groups()))
            d = json.loads(z.read(name))
            if identity != (d["book"], d["test"], d["section"]) or identity in documents:
                raise ValueError("Transcript identity mismatch")
            qa = audit[identity]
            if (
                d["source_audio"] != qa["source_audio"]
                or d["timestamp_origin"] != "start of this section file"
            ):
                raise ValueError("Transcript audio origin mismatch")
            segments = []
            for i, s in enumerate(d["segments"]):
                if (
                    not all(
                        isinstance(s[k], (int, float)) and math.isfinite(s[k])
                        for k in ("start", "end")
                    )
                    or not 0 <= s["start"] < s["end"]
                    or not s["text"].strip()
                    or segments
                    and s["start"] < segments[-1]["start"]
                ):
                    raise ValueError("Invalid segment")
                segments.append({"id": f"seg-{i + 1:04}", **s})
            if not segments or abs(segments[-1]["end"] - float(qa["duration_reviewed_sec"])) > 0.05:
                raise ValueError("QA timing mismatch")
            documents[identity] = {
                **d,
                "segments": segments,
                "complete": "incomplete_at_pause" not in qa["flags"],
                "qa_flags": qa["flags"].split(";"),
                "audio_verified": False,
            }
    expected = {
        (b, t, p)
        for b in range(4, 22)
        for t in (range(5, 9) if b == 12 else range(1, 5))
        for p in range(1, 5)
    }
    if set(documents) != expected:
        raise ValueError("Expected 288 canonical Parts")
    return documents


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    target = ROOT / "backend/app/content/listening_transcripts_v1"
    target.mkdir(parents=True, exist_ok=True)
    docs = build(args.archive)
    manifest = {
        "version": 1,
        "archive_sha256": hashlib.sha256(args.archive.read_bytes()).hexdigest(),
        "items": [],
    }
    for (b, t, p), doc in sorted(docs.items()):
        filename = f"cambridge-{b:02}-test-{t:02}-part-{p:02}.json"
        data = (json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
        (target / filename).write_bytes(data)
        manifest["items"].append(
            {
                "file": filename,
                "sha256": hashlib.sha256(data).hexdigest(),
                "complete": doc["complete"],
            }
        )
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(
        f"Imported {len(docs)} Parts; {sum(not d['complete'] for d in docs.values())} "
        "incomplete; no audio verification claimed"
    )
