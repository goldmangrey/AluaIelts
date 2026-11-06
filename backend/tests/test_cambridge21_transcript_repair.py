"""Targeted regression for the nine repaired Cambridge 21 transcript tails."""

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1] / "app/content/listening_transcripts_v1"
CASES = [
    (
        "cambridge-21-test-01-part-01.json",
        47,
        "f6ea6391168129e6f35d8a82f0dbc2d21ecc31c6685c2e4cdf011a79da1fbe30",
        467.3045,
        406.9,
    ),
    (
        "cambridge-21-test-01-part-02.json",
        35,
        "8024ebe81e23484b80ad94a5cb2c1f7134a3b69f0c04df55aaa437b786d64a79",
        445.518375,
        415.0,
    ),
    (
        "cambridge-21-test-01-part-03.json",
        26,
        "790bfa68f1f9164ac9a5750982c7215b92d1ed53f7fe912e54e8f27e00e68b0b",
        416.5746875,
        386.0,
    ),
    (
        "cambridge-21-test-02-part-02.json",
        31,
        "467fe8d4e52c7961ba33d27177933799069967f99cafa204155cfc7e82e65d77",
        368.0914375,
        337.56,
    ),
    (
        "cambridge-21-test-02-part-03.json",
        49,
        "2b1b74e2a0634376dcfc5c2088b9bab9e96bc442d96f271c502366e97d8baabc",
        446.0146875,
        415.46,
    ),
    (
        "cambridge-21-test-03-part-02.json",
        28,
        "ac7c33605c1d0686a9f2636b9a43fc12bd8e2527e971fac6e3ac016fb275efa3",
        410.5143125,
        379.98,
    ),
    (
        "cambridge-21-test-03-part-03.json",
        25,
        "90218188318f171ab53a793277826418e2e3deab5e9ea0da9d138ee43cd20193",
        391.94125,
        361.4,
    ),
    (
        "cambridge-21-test-04-part-02.json",
        25,
        "888861e949346391c0fe471398b649b10e143ea63bc93f4ff90e6a110e6d28e2",
        432.9535,
        402.4,
    ),
    (
        "cambridge-21-test-04-part-03.json",
        22,
        "dba6f965e9ff14ef5f97e2c9ce15bbe3005281746ca6344918424a84fde4144b",
        390.321625,
        359.755,
    ),
]


@pytest.mark.parametrize("name,old_count,prefix_sha,duration,expected_end", CASES)
def test_repaired_tail_preserves_original_segments(
    name, old_count, prefix_sha, duration, expected_end
):
    doc = json.loads((ROOT / name).read_text())
    assert doc["complete"] and "incomplete_at_pause" not in doc["qa_flags"]
    prefix = json.dumps(doc["segments"][:old_count], sort_keys=True, separators=(",", ":")).encode()
    assert hashlib.sha256(prefix).hexdigest() == prefix_sha
    assert len(doc["segments"]) > old_count
    assert doc["segments"][-1]["end"] == expected_end
    assert "check your answers" in " ".join(s["text"] for s in doc["segments"][-2:]).lower()
    for i, segment in enumerate(doc["segments"], 1):
        assert segment["id"] == f"seg-{i:04}"
        assert 0 <= segment["start"] < segment["end"] <= duration
        if i > 1:
            assert segment["start"] >= doc["segments"][i - 2]["start"]
    manifest = json.loads((ROOT / "manifest.json").read_text())
    item = next(item for item in manifest["items"] if item["file"] == name)
    assert item["complete"]
    assert item["sha256"] == hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
