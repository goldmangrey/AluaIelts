"""Source-confirmed section-label overlays and explicit detection of missing labels."""

from __future__ import annotations

import json
import re
from pathlib import Path


def required_labels(passage):
    wanted = set()
    for group in passage["question_groups"]:
        if group["type"] not in {"matching_headings", "matching_information"}:
            continue
        text = "".join(
            segment.get("text", "")
            for block in group["content_blocks"]
            if block["type"] == "rich_text"
            for segment in block["segments"]
        )
        match = re.search(
            r"(?:paragraphs|sections)[^\n]*?\b([A-Z])\s*[-–—]\s*([A-Z])\b", text, re.I
        )
        if match:
            wanted.update(chr(c) for c in range(ord(match[1].upper()), ord(match[2].upper()) + 1))
        wanted.update(m[1] for m in re.finditer(r"(?:Paragraph|Section) ([A-Z])\b", text))
    return wanted


def overlays():
    path = Path(__file__).with_name("paragraph_labels.json")
    return json.loads(path.read_text()) if path.exists() else []


def apply_labels(passage):
    selected = [row for row in overlays() if row["passage_id"] == passage["id"]]
    if not selected:
        return
    blocks = passage["content"]
    for row in selected:
        pattern = re.compile(r"\s+".join(re.escape(word) for word in row["anchor"].split()))
        matches = [(idx, pattern.search(block["text"])) for idx, block in enumerate(blocks)]
        matches = [(idx, m) for idx, m in matches if m]
        if not matches and "\n\n" in row["anchor"]:
            prefix_pattern = re.compile(
                r"\s+".join(re.escape(word) for word in row["anchor"].split("\n\n")[0].split())
            )
            matches = [
                (idx, prefix_pattern.search(block["text"])) for idx, block in enumerate(blocks)
            ]
            matches = [(idx, match) for idx, match in matches if match]
        if len(matches) != 1:
            raise ValueError(
                f"Label overlay anchor is not unique: {row['passage_id']} {row['label']}"
            )
        for prior in blocks:
            if prior["label"] == row["label"]:
                prior["label"] = None
        idx, match = matches[0]
        block = blocks[idx]
        start = match.start()
        prefix = block["text"][:start]
        # An existing unparsed margin label is metadata, not part of the preceding paragraph.
        old = re.search(r"(?:^|\n)" + row["label"] + r"[_.\s]*$", prefix)
        cut = old.start() if old else start
        before = block["text"][:cut].strip()
        after = block["text"][start:]
        if before and not re.search(r"\w", before):
            after = before + after
            before = ""
        replacement = []
        if before:
            replacement.append({**block, "text": before})
        replacement.append({"type": "paragraph", "text": after, "label": row["label"]})
        blocks[idx : idx + 1] = replacement
