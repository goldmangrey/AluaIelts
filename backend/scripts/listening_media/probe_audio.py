"""Read-only technical probe, JSONL on stdout. Does not verify spoken exam content.

Run on the machine holding real recordings; ffprobe and ffmpeg must be installed.
No media is modified. Reports actual size/duration/codec and full decode status.
"""

import argparse
import json
import subprocess
from pathlib import Path


def probe(root, record):
    relative = record["relative_path"]
    path = (root / relative).resolve()
    result = {
        "audio_id": record["audio_id"],
        "relative_path": relative,
        "decode_verified": False,
        "content_mapping_verified": False,
    }
    if (
        Path(relative).is_absolute()
        or ".." in Path(relative).parts
        or not path.is_relative_to(root)
    ):
        return {**result, "error": "unsafe_path"}
    try:
        result["byte_size"] = path.stat().st_size
        if result["byte_size"] != record["byte_size"]:
            return {**result, "error": "inventory_size_mismatch"}
        metadata = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration:stream=codec_name,codec_type",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )
        data = json.loads(metadata.stdout)
        result["duration"] = float(data["format"]["duration"])
        result["audio_codecs"] = [
            s["codec_name"] for s in data["streams"] if s["codec_type"] == "audio"
        ]
        decoded = subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-xerror",
                "-i",
                str(path),
                "-map",
                "0:a:0",
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            timeout=180,
        )
        result["decode_verified"] = (
            decoded.returncode == 0 and bool(result["audio_codecs"]) and result["duration"] > 0
        )
        if not result["decode_verified"]:
            result["error"] = "decode_failed"
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        result["error"] = "probe_failed"
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    args = ap.parse_args()
    for item in json.loads(args.manifest.read_text())["items"]:
        print(json.dumps(probe(args.root.resolve(), item), ensure_ascii=False), flush=True)
