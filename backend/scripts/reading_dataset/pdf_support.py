"""Local-only OCR cache and reproducible, tightly bounded PDF question crops."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

import fitz

CACHE = Path(tempfile.gettempdir()) / "alua-reading-pdf-cache"


def page_lines(pdf, page, psm=3):
    token = hashlib.sha256(pdf.read_bytes()).hexdigest()[:16]
    cache = CACHE / token
    cache.mkdir(parents=True, exist_ok=True)
    dest = cache / (f"{page}.json" if psm == 3 else f"{page}-{psm}.json")
    if dest.exists():
        return json.loads(dest.read_text())
    with fitz.open(pdf) as doc:
        p = doc[page - 1]
        w, h = p.rect.width, p.rect.height
        image = cache / f"{page}.png"
        p.get_pixmap(matrix=fitz.Matrix(2, 2)).save(image)
    env = dict(os.environ, OMP_THREAD_LIMIT="1")
    r = subprocess.run(
        ["tesseract", str(image), "stdout", "-l", "eng", "--psm", str(psm), "tsv"],
        capture_output=True,
        text=True,
        env=env,
        check=True,
        timeout=60,
    )
    grouped = {}
    for row in csv.DictReader(io.StringIO(r.stdout), delimiter="\t", quoting=csv.QUOTE_NONE):
        if row.get("level") != "5" or not row.get("text", "").strip():
            continue
        k = (row["block_num"], row["par_num"], row["line_num"])
        x, y, bw, bh = [int(row[n]) / 2 for n in ["left", "top", "width", "height"]]
        word = {"text": row["text"], "bbox": [x, y, x + bw, y + bh]}
        grouped.setdefault(k, []).append(word)
    lines = []
    for words in grouped.values():
        lines.append(
            {
                "text": " ".join(x["text"] for x in words),
                "bbox": [
                    min(x["bbox"][0] for x in words),
                    min(x["bbox"][1] for x in words),
                    max(x["bbox"][2] for x in words),
                    max(x["bbox"][3] for x in words),
                ],
            }
        )
    result = {"width": w, "height": h, "lines": lines}
    dest.write_text(json.dumps(result))
    return result


def headings(data):
    out = []
    for line in data["lines"]:
        m = re.search(r"^Questions?\s*(\d{1,2})\s*(?:[-–—]|and)\s*(\d{1,2})\b", line["text"], re.I)
        if not m:
            m = re.search(r"^Question\s*(\d{1,2})\b", line["text"], re.I)
        if m:
            a = int(m[1])
            b = int(m[2]) if m.lastindex == 2 else a
            if 1 <= a <= b <= 40:
                out.append((a, b, line["bbox"][1]))
    return sorted(out, key=lambda x: x[2])


def crop_group(pdf, pp, nums, base, group_id, *, allow_continuation=False):
    review_path = Path(__file__).with_name("source_reviews.json")
    reviews = json.loads(review_path.read_text())
    for crop in reviews["crops"]:
        if crop["group_id"] == group_id:
            n = crop["pdf_page"]
            rect = crop["crop_box"]
            path = (
                f"assets/cambridge_{int(group_id.split('-')[1]):02}/"
                f"{group_id}-pdf-{n:03}-diagram.png"
            )
            dest = base / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            with fitz.open(pdf) as doc:
                pix = doc[n - 1].get_pixmap(matrix=fitz.Matrix(2.5, 2.5), clip=fitz.Rect(rect))
                pix.save(dest)
            return [
                {
                    "id": f"{group_id}-asset-{n}-diagram",
                    "path": path,
                    "mime_type": "image/png",
                    "pdf_file": str(pdf),
                    "pdf_page": n,
                    "crop_box": rect,
                    "coordinate_system": "pdf_points_top_left",
                    "render_scale": 2.5,
                    "width": pix.width,
                    "height": pix.height,
                    "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
                    "verification_status": "visually_verified",
                    "question_numbers": nums,
                }
            ]
    assets = []
    wanted = set(nums)
    for n in pp:
        data = page_lines(pdf, n)
        hs = headings(data)
        for ix, (a, b, y) in enumerate(hs):
            if not wanted.intersection(range(a, b + 1)):
                continue
            # Reject incidental prose references. Task headings have a dedicated line.
            line = next(line for line in data["lines"] if line["bbox"][1] == y)
            if len(line["text"]) > 65:
                continue
            ymax = hs[ix + 1][2] - 8 if ix + 1 < len(hs) else data["height"] * 0.935
            ymin = max(0, y - 6)
            relevant = [line for line in data["lines"] if ymin <= line["bbox"][1] <= ymax]
            if not relevant:
                continue
            # Include content width between margins, preserving diagrams outside OCR text bounds.
            xmin = max(0, min(line["bbox"][0] for line in relevant) - 10)
            xmax = min(data["width"], max(line["bbox"][2] for line in relevant) + 10)
            # Diagram/table geometry can extend beyond recognized text; use content-width margins.
            xmin = min(xmin, data["width"] * 0.07)
            xmax = max(xmax, data["width"] * 0.99)
            rect = [round(xmin, 2), round(ymin, 2), round(xmax, 2), round(ymax, 2)]
            path = (
                f"assets/cambridge_{int(group_id.split('-')[1]):02}/{group_id}-pdf-{n:03}-{ix}.png"
            )
            dest = base / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            with fitz.open(pdf) as doc:
                pix = doc[n - 1].get_pixmap(matrix=fitz.Matrix(2.5, 2.5), clip=fitz.Rect(rect))
                pix.save(dest)
            assets.append(
                {
                    "id": f"{group_id}-asset-{n}-{ix}",
                    "path": path,
                    "mime_type": "image/png",
                    "pdf_file": str(pdf),
                    "pdf_page": n,
                    "crop_box": rect,
                    "coordinate_system": "pdf_points_top_left",
                    "render_scale": 2.5,
                    "width": pix.width,
                    "height": pix.height,
                    "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
                    "verification_status": "extracted_needs_visual_review",
                    "question_numbers": [v for v in nums if a <= v <= b],
                }
            )
    return (
        add_continuations(pdf, pp, nums, base, group_id, assets) if allow_continuation else assets
    )


def add_continuations(pdf, pp, nums, base, group_id, assets):
    started = {a["pdf_page"] for a in assets}
    for page in sorted(pp):
        if page in started or page - 1 not in started:
            continue
        data = page_lines(pdf, page)
        hs = headings(data)
        end = hs[0][2] - 8 if hs else data["height"] * 0.94
        lines = [
            line
            for line in data["lines"]
            if data["height"] * 0.05 < line["bbox"][1] < end
            and not re.fullmatch(r"(?:Test\s+\d+|Reading|\d+)", line["text"], re.I)
        ]
        if not lines:
            continue
        detected = {
            int(m[0]) for line in lines for m in re.finditer(r"(?<!\d)\d{1,2}(?!\d)", line["text"])
        }
        if not detected.intersection(nums):
            continue
        start = min(line["bbox"][1] for line in lines) - 8
        rect = [
            round(data["width"] * 0.06, 2),
            round(start, 2),
            round(data["width"] * 0.95, 2),
            round(end, 2),
        ]
        path = (
            f"assets/cambridge_{int(group_id.split('-')[1]):02}/"
            f"{group_id}-pdf-{page:03}-continuation.png"
        )
        dest = base / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        with fitz.open(pdf) as doc:
            pix = doc[page - 1].get_pixmap(matrix=fitz.Matrix(2.5, 2.5), clip=fitz.Rect(rect))
            pix.save(dest)
        assets.append(
            {
                "id": f"{group_id}-asset-{page}-continuation",
                "path": path,
                "mime_type": "image/png",
                "pdf_file": str(pdf),
                "pdf_page": page,
                "crop_box": rect,
                "coordinate_system": "pdf_points_top_left",
                "render_scale": 2.5,
                "width": pix.width,
                "height": pix.height,
                "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
                "verification_status": "extracted_needs_visual_review",
                "question_numbers": sorted(set(nums) & detected),
            }
        )
    return assets
