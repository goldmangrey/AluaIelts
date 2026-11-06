"""Import inventory and sniff local media; never claims decode/content proof.

Run with PYTHONPATH=backend python -m scripts.listening_media.import_inventory
INVENTORY --root LOCAL_AUDIO_ROOT. Original media must be available for MIME detection.
"""

import hashlib
import json
import re
from pathlib import Path

from app.modules.listening.catalog import audio_mime, confined

ROOT = Path(__file__).resolve().parents[3]


def parse(path, audio_root):
    records = []
    identities = set()
    paths = set()
    for line in path.read_text().splitlines():
        relative, size = line.rsplit("\t", 1)
        if Path(relative).is_absolute() or ".." in Path(relative).parts:
            raise ValueError("Unsafe inventory path")
        book = re.search(r"Listening-(\d{2})/", relative)
        match = re.search(r"IELTS(\d{2})-Test\s*(\d+)-Section\s*(\d)\.(mp3|m4a)$", relative, re.I)
        if not match or not book or book[1] != match[1]:
            raise ValueError(relative)
        b, t, p = int(match[1]), int(match[2]), int(match[3])
        # Reviewed transcript QA: Cambridge 05 physical filenames transpose Test/Section.
        if b == 5:
            t, p = p, t
        ordinal = t - 4 if b == 12 else t
        identity = (b, t, p)
        if (
            identity in identities
            or relative in paths
            or not (4 <= b <= 21 and 1 <= ordinal <= 4 and 1 <= p <= 4)
            or int(size) <= 0
        ):
            raise ValueError(relative)
        identities.add(identity)
        paths.add(relative)
        media = confined(audio_root, relative)
        if media.stat().st_size != int(size):
            raise ValueError("Audio inventory size mismatch")
        records.append(
            {
                "exam_id": f"cambridge-{b:02}-test-{t:02}",
                "book": b,
                "printed_test_number": t,
                "local_ordinal": ordinal,
                "part_number": p,
                "audio_id": f"cambridge-{b:02}-test-{t:02}-part-{p:02}",
                "relative_path": relative,
                "byte_size": int(size),
                "mime_type": audio_mime(media),
                "duration": None,
                "sha256": None,
                "file_inventory_verified": True,
                "decode_verified": False,
                "content_mapping_verified": False,
            }
        )
    expected = {
        (b, t, p)
        for b in range(4, 22)
        for t in (range(5, 9) if b == 12 else range(1, 5))
        for p in range(1, 5)
    }
    if identities != expected:
        raise ValueError("Missing/extra audio identities")
    return {
        "version": 1,
        "inventory_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "verification": "inventory names and sizes only",
        "items": sorted(
            records, key=lambda r: (r["book"], r["printed_test_number"], r["part_number"])
        ),
    }


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("inventory", type=Path)
    ap.add_argument("--root", type=Path, required=True, help="Root holding original audio files")
    args = ap.parse_args()
    target = ROOT / "backend/app/content/listening_audio_v1/audio_manifest.json"
    manifest = parse(args.inventory, args.root)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(target)
