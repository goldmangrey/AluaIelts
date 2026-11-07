"""Deterministic Stage 1 import. No network, audio, API, database or OCR.

A state machine handles duplicated printed headers, then group and inline-token
parsers retain source spans. Unsupported layouts stay image-backed or blocked;
JSON parsing is deliberately independent from editorial source verification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
from collections import defaultdict
from pathlib import Path

import fitz
from image_repairs import add_repaired_assets
from PIL import Image
from schema import write as write_schemas
from source_fidelity import add_source_fidelity_assets
from visual_materials import REGISTRY as VISUAL_REGISTRY
from visual_materials import apply_visual_materials, reviewed_associations

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DEFAULT_INPUT = Path.home() / "Desktop/ListTest"
DEFAULT_OUTPUT = ROOT / "backend/app/content/listening_v1"
SCHEMA_VERSION = "1.0.0-stage1"
DASH = r"[-–—−]"
TEST = re.compile(r"^(?:CAMBRIDGE IELTS 12\s*[—–-]\s*)?TEST\s+([1-8])(?:\s*(?:[—–|:-].*)?)?$", re.I)
PART = re.compile(r"^(?:SECTION|PART)\s+([1-4])\b.*AUDIO PART\s*([1-4])", re.I)
HEADER = re.compile(
    r"^\s*(?:Test\s+\d\s*[—–-]\s*)?Questions?\s*(\d{1,2})(?:\s*(?:"
    + DASH
    + r"|and|&)\s*(\d{1,2}))?",
    re.I,
)
OPTION = re.compile(r"^\s*([A-K])(?:[.)]\s*|\s{1,})(\S.*)$")
KEYLINE = re.compile(r"^\s*(\d{1,2})(?:[.)]\s*|\s{1,})(\S.*)$")
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}
WORDS = {
    "ONE": 1,
    "TWO": 2,
    "THREE": 3,
    "FOUR": 4,
    "FIVE": 5,
    "SIX": 6,
    "SEVEN": 7,
    "EIGHT": 8,
    "NINE": 9,
    "TEN": 10,
}
KEY_PAGES = {
    5: [153, 155, 157, 159],
    6: [152, 154, 156, 158],
    7: [156, 158, 160, 162],
    8: [151, 153, 155, 157],
    9: [147, 149, 151, 153],
    10: [143, 145, 147, 149],
    11: [122, 124, 126, 128],
    12: [116, 118, 120, 122],
    13: [119, 121, 123, 125],
    14: [119, 121, 123, 125],
    15: [121, 123, 125, 127],
    16: [123, 125, 127, 129],
    17: [112, 114, 116, 118],
    18: [121, 123, 125, 127],
    19: [119, 121, 123, 125],
    20: [10, 46, 85, 121],
    21: [118, 120, 122, 124],
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def dump(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def split_tests(text: str):
    """Only section wrappers advance a part. Repeated PDF headings do not."""
    result = defaultdict(lambda: defaultdict(list))
    test = part = None
    for line_number, line in enumerate(text.splitlines(), 1):
        tm = TEST.fullmatch(line.strip())
        pm = PART.match(line.strip())
        if tm and (
            line.strip().startswith("TEST") or line.strip().startswith("CAMBRIDGE IELTS 12")
        ):
            candidate = int(tm[1])
            if candidate != test:
                test, part = candidate, None
            continue
        if pm:
            if pm[1] != pm[2]:
                raise ValueError(f"Part/audio wrapper disagreement at line {line_number}")
            part = int(pm[1])
        if test is not None and part is not None:
            result[test][part].append((line_number, line))
    return result


def choose_txt(book_dir, name, inventory):
    candidates = sorted(book_dir.rglob(name))
    if not candidates:
        raise ValueError(f"Missing {name}")
    preferred = book_dir / name
    selected = preferred if preferred in candidates else candidates[0]
    hashes = {str(p.relative_to(book_dir)): sha(p.read_bytes()) for p in candidates}
    inventory["canonical_files"][name] = {
        "selected": str(selected.relative_to(book_dir)),
        "copies": hashes,
        "identical": len(set(hashes.values())) == 1,
    }
    return selected


def page_numbers(text):
    pages = set()
    for line in text.splitlines():
        if re.search(r"answer[ -]?key|official key|answer pages?", line, re.I):
            continue
        # Read only PDF page metadata, never printed page numbers or question ranges.
        for m in re.finditer(
            r"(?:PDF\s+PAGES?(?:\(S\))?|PDF\s+PAGE\(S\)|PDF\s+\bpages?\b)\s*[:=]?\s*(\d{1,3}(?:(?:\s*[,;–—-]\s*)\d{1,3})*)",
            line,
            re.I,
        ):
            spec = m[1]
            for token in re.split(r"[,;]", spec):
                ns = [int(x) for x in re.findall(r"\d+", token)]
                if len(ns) == 2 and ns[1] >= ns[0]:
                    pages.update(range(ns[0], ns[1] + 1))
                else:
                    pages.update(ns)
    return sorted(pages)


def is_metadata(line):
    s = line.strip()
    return (
        not s
        or "NEEDS_REVIEW" in s
        or bool(re.fullmatch(r"[-=#_*─━]{3,}", s))
        or bool(PART.match(s))
        or bool(
            re.match(
                r"^(?:SECTION\s*\d|PART\s*\d|LISTENING$|Test\s+\d\s*(?:[—–-]\s*LISTENING)?$)",
                s,
                re.I,
            )
        )
        or bool(
            re.match(
                r"^(?:\[?(?:BEGIN|END|ORIGINAL|SOURCE|GRAPHICAL|IMAGE|NEEDS_REVIEW|TEST .*ANSWERS)"
                r"|PDF page|SOURCE_|Original (?:PDF|page)|Source:|Source PDF|PDF PAGES"
                r"|ORIGINAL PDF|NEEDS_REVIEW|NOTE: NEEDS_REVIEW)",
                s,
                re.I,
            )
        )
        or bool(re.search(r"\.(?:png|jpg|jpeg|webp)\b", s, re.I))
        or s.startswith("END OF TEST")
        or s.startswith("Answers: See")
        or s.startswith("Official answer key")
    )


def group_ranges(lines, first, last):
    """Use declared subranges; collapse duplicate wrappers and printed headings."""
    headings = []
    for i, (_, line) in enumerate(lines):
        m = HEADER.match(line.strip())
        if not m:
            continue
        lo, hi = int(m[1]), int(m[2] or m[1])
        if first <= lo <= hi <= last:
            headings.append((i, lo, hi))
    # Entire-part headers are metadata when actual subgroup boundaries follow.
    sub = [h for h in headings if (h[1], h[2]) != (first, last)]
    selected = sub if sub else headings[:1]
    unique = []
    for h in selected:
        if unique and h[1:] == unique[-1][1:]:
            continue
        unique.append(h)
    if not unique:
        unique = [(0, first, last)]
    elif unique[0][1] > first:
        unique.insert(0, (0, first, unique[0][1] - 1))
    groups = []
    for ix, (start, lo, hi) in enumerate(unique):
        stop = unique[ix + 1][0] if ix + 1 < len(unique) else len(lines)
        # Some source headings claim 1–6, but the next distinct group begins at 5.
        if ix + 1 < len(unique) and unique[ix + 1][1] <= hi:
            hi = unique[ix + 1][1] - 1
        if hi < lo:
            continue
        groups.append((lo, hi, lines[start:stop]))
    return groups


def constraints(instruction):
    u = instruction.upper()
    m = re.search(r"(?:NO MORE THAN\s+)?(ONE|TWO|THREE|FOUR|\d+)\s+WORDS?\b", u)
    limit = WORDS.get(m[1], int(m[1]) if m and m[1].isdigit() else None) if m else None
    n = bool(re.search(r"NUMBER|NUMBERS", u))
    nm = re.search(r"\b(A|ONE|TWO|THREE|\d+)\s+NUMBERS?", u)
    max_numbers = (
        (1 if nm[1] == "A" else WORDS.get(nm[1], int(nm[1]) if nm[1].isdigit() else None))
        if nm
        else None
    )
    return {
        "max_words": limit,
        "max_numbers": max_numbers,
        "allows_number": n,
        "instruction": instruction,
        "normalization": "unicode_nfc_casefold_trim_collapse_spaces",
        "spelling": "exact_official_alternatives_only",
    }


def question_kind(text):
    t = text.lower()
    if re.search(r"complete.*?using words from the box", t):
        return "completion_with_word_bank", "select"
    if (
        re.search(r"choose\s+(?:two|three|four|five)\s+(?:letters|answers)", t)
        and "from the box" not in t
    ):
        return "multiple_choice_multiple", "select"
    if "choose the correct letter" in t or re.search(r"choose\s+(?:the correct|one)\s+answer", t):
        return "multiple_choice_single", "select"
    if re.search(r"(?:label|complete) (?:the |this )?(?:map|plan|diagram|chart|drawing)", t):
        k = next(
            (v for v in ("map", "plan", "diagram") if re.search(r"label (?:the |this )?" + v, t)),
            "diagram",
        )
        return k + "_labelling", "select" if re.search(
            r"letter|from the box|answers from", t
        ) else "text"
    if re.search(
        r"(?:write|choose).*?(?:correct letter|answers (?:from|for) the box|letters [a-k])"
        r"|match.*?(?:letter|box)",
        t,
        re.S,
    ):
        for word, completion_type in (
            ("flow", "flow_chart_completion"),
            ("table", "table_completion"),
            ("summary", "summary_completion"),
            ("note", "note_completion"),
        ):
            if re.search(r"complete[^.\n]*" + word, t):
                return completion_type, "select"
        return "matching", "select"
    for word, kind in [
        ("flow", "flow_chart_completion"),
        ("table", "table_completion"),
        ("form", "form_completion"),
        ("summary", "summary_completion"),
        ("sentenc", "sentence_completion"),
        ("note", "note_completion"),
    ]:
        if re.search(r"complete[^.\n]*" + word, t):
            return kind, "text"
    if re.search(r"answer (?:the )?(?:questions|following questions)", t) or (
        "write " in t and "words" in t
    ):
        return "short_answer", "text"
    return "unclassified", None


def clean_lines(lines):
    return [
        (n, line_text)
        for n, line_text in lines
        if not is_metadata(line_text) and not HEADER.match(line_text.strip())
    ]


def option_list(lines):
    """Letters plus original text, retaining wrapped continuations."""
    options = []
    continuation_active = False
    for n, line in lines:
        inline = list(re.finditer(r"(?:^|\s{2,})([A-K])(?:[.)]\s*|\s+)(?=\S)", line))
        if len(inline) >= 2:
            for index, match in enumerate(inline):
                stop = inline[index + 1].start() if index + 1 < len(inline) else len(line)
                options.append(
                    {
                        "label": match[1],
                        "text": line[match.end() : stop].strip(),
                        "source_line": n,
                    }
                )
            continuation_active = True
            continue
        m = OPTION.match(line)
        if m:
            options.append({"label": m[1], "text": m[2].strip(), "source_line": n})
            continuation_active = True
        elif (
            continuation_active
            and options
            and line.strip()
            and not re.match(r"^\s*(?:\d|\[\d|\(\d)", line)
            and not re.match(
                r"^(?:Questions|Write|Choose|Complete|Answer|Label)", line.strip(), re.I
            )
            and len(line) - len(line.lstrip()) >= 4
            and re.search(r"[A-Za-z]", line)
        ):
            options[-1]["text"] += "\n" + line.strip()
        else:
            continuation_active = False
    return options


def marker_spans(lines, lo, hi, input_type):
    found = defaultdict(list)
    for line_number, line in lines:
        # An indented table row labelled A may itself contain numbered blanks.
        # Numbered blanks can appear inside notes, prices and table cells.
        for m in re.finditer(
            r"(?<![\w\d])(?:\[(\d{1,2})\]|\((\d{1,2})\)|(\d{1,2}))[.)]?\s*['\"£$€]?\s*\[?(?:_{2,}|\.{3,}|…+)\]?",
            line,
        ):
            number = int(next(x for x in m.groups()[:3] if x))
            if lo <= number <= hi:
                found[number].append(
                    {
                        "line": line_number,
                        "start": m.start(),
                        "end": m.end(),
                        "text": line,
                        "kind": "numbered_blank",
                    }
                )
        # MCQ/matching/short-answer/form layouts also put the number at row start.
        m = re.match(r"^\s*(?:\[(\d{1,2})\]|\((\d{1,2})\)|(\d{1,2}))[.)]?\s+(\S.*)", line)
        if m:
            number = int(next(x for x in m.groups()[:3] if x))
            if lo <= number <= hi and not found[number]:
                if not re.match(r"^[-–—]\s*\d", m[4]):
                    found[number].append(
                        {
                            "line": line_number,
                            "start": m.start(),
                            "end": m.end(),
                            "text": line,
                            "kind": "numbered_row",
                        }
                    )
        if input_type == "text":
            for m in re.finditer(r"(?:_{2,}|\.{3,})\s*\((\d{1,2})\)", line):
                number = int(m[1])
                if lo <= number <= hi and not found[number]:
                    found[number].append(
                        {
                            "line": line_number,
                            "start": m.start(),
                            "end": m.end(),
                            "text": line,
                            "kind": "numbered_blank",
                        }
                    )
            for m in re.finditer(
                r"(?<![\w\d])(?:\[(\d{1,2})\]|\((\d{1,2})\)|(\d{1,2}))(?=\s{2,}|\s*$)", line
            ):
                number = int(next(x for x in m.groups() if x))
                if lo <= number <= hi and not found[number]:
                    found[number].append(
                        {
                            "line": line_number,
                            "start": m.start(),
                            "end": m.end(),
                            "text": line,
                            "kind": "source_space_blank",
                        }
                    )
            for m in re.finditer(r"(?<![\w\d])(\d{1,2})[£$€](?!\d)", line):
                number = int(m[1])
                if lo <= number <= hi and not found[number]:
                    found[number].append(
                        {
                            "line": line_number,
                            "start": m.start(),
                            "end": m.end(),
                            "text": line,
                            "kind": "source_space_blank",
                        }
                    )
    return found


def body_blocks(lines, markers):
    by_line = defaultdict(list)
    for number, spans in markers.items():
        for span in spans:
            by_line[span["line"]].append((number, span))
    result = []
    for line_number, line in lines:
        spans = sorted(by_line.get(line_number, []), key=lambda x: x[1]["start"])
        # Full source line retained, tokens bind blanks without deleting context.
        result.append(
            {
                "kind": "source_line",
                "text": line,
                "source_line": line_number,
                "blanks": [
                    {"question_number": n, "start": s["start"], "end": s["end"]}
                    for n, s in spans
                    if s["kind"] == "numbered_blank"
                ],
            }
        )
    return result


def table_layout(lines, markers):
    """Only preserve tables whose explicit TXT column separators agree.

    Spatial inference from plain whitespace would be unsafe; other layouts
    retain the original image and numbered controls.
    """
    rows = []
    for line_number, line in lines:
        if "|" not in line or re.fullmatch(r"[\s|:—-]+", line):
            continue
        columns = line.split("|")
        cursor = 0
        cells = []
        for index, text in enumerate(columns):
            start, end = cursor, cursor + len(text)
            cursor = end + 1
            if not text.strip() and index in (0, len(columns) - 1):
                continue
            positions = [
                number
                for number, spans in markers.items()
                if any(
                    span["line"] == line_number and start <= span["start"] < end for span in spans
                )
            ]
            cells.append({"text": text.strip(), "question_numbers": sorted(positions)})
        rows.append({"source_line": line_number, "cells": cells})
    if len(rows) >= 2 and len({len(row["cells"]) for row in rows}) == 1:
        return {"kind": "table", "rows": rows}
    return None


class Assets:
    def __init__(self, input_root, output):
        self.input_root, self.output = input_root, output
        self.records = {}
        self.by_source = {}

    def add(self, path, book, role, test=None, part=None, page=None):
        data = path.read_bytes()
        digest = sha(data)
        aid = "asset-" + digest
        public = role in ("task_image", "source_page")
        relative = f"assets/{'public' if public else 'private'}/{digest}{path.suffix.lower()}"
        with Image.open(path) as im:
            width, height = im.size
            im.verify()
        if aid not in self.records:
            target = self.output / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                target.write_bytes(data)
            self.records[aid] = {
                "asset_id": aid,
                "relative_path": relative,
                "sha256": digest,
                "byte_size": len(data),
                "width": width,
                "height": height,
                "visibility": "public" if public else "private",
                "roles": [],
                "associations": [],
                "sources": [],
            }
        record = self.records[aid]
        if (record["visibility"] == "private") != (not public):
            raise ValueError("Same bytes classified as both question material and key evidence")
        source = (
            str(path.relative_to(self.input_root))
            if path.is_relative_to(self.input_root)
            else str(path.relative_to(ROOT))
            if path.is_relative_to(ROOT)
            else "ieltsbooks/" + path.name
        )
        if source not in record["sources"]:
            record["sources"].append(source)
        if role not in record["roles"]:
            record["roles"].append(role)
        # Filenames are discovery hints, not authority for reviewed image bytes.
        # In particular C18 T2 PDF_035 is Q6–10 despite its Part_4 filename.
        ownership = reviewed_associations(aid, book) if public else []
        for owner_test, owner_part in ownership or [(test, part)]:
            assoc = {
                "book": book,
                "printed_test_number": owner_test,
                "part_number": owner_part,
                "pdf_page": page,
            }
            if assoc not in record["associations"]:
                record["associations"].append(assoc)
        self.by_source[path] = aid
        return aid

    def public_record(self, aid):
        r = self.records[aid]
        return {
            k: r[k] for k in ("asset_id", "relative_path", "sha256", "byte_size", "width", "height")
        }


def source_ref(path, root, lines, pages):
    return {
        "file": str(path.relative_to(root)),
        "line_start": lines[0][0] if lines else None,
        "line_end": lines[-1][0] if lines else None,
        "pdf_pages": pages,
        "pdf_page_basis": "prepared_source_metadata_not_independently_confirmed",
    }


def import_group(exam_id, part, lo, hi, lines, src, pages, asset_ids, review):
    gid = f"{exam_id}-p{part}-g{lo:02}-{hi:02}"
    group_review = review.get("groups", {}).get(gid, {})
    lines = [
        (n, group_review.get("line_overrides", {}).get(str(n), line_text)) for n, line_text in lines
    ]
    cleaned = clean_lines(lines)
    text = "\n".join(line_text for _, line_text in cleaned)
    instruction_lines = []
    for ix, (_, line) in enumerate(cleaned):
        if re.match(r"^(?:Complete|Write|Choose|Label|Answer|What |Which )", line.strip(), re.I):
            instruction_lines.append(line.strip())
            # Source constraints occasionally wrap at "for / each answer".
            if re.search(r"\bfor\s*$", line.strip(), re.I) and ix + 1 < len(cleaned):
                instruction_lines.append(cleaned[ix + 1][1].strip())
    instruction = "\n".join(instruction_lines)
    instruction = group_review.get("instructions_override", instruction)
    kind, input_type = question_kind(instruction)
    if kind == "unclassified":
        kind, input_type = question_kind(text)
    marks = marker_spans(cleaned, lo, hi, input_type)
    multi = kind == "multiple_choice_multiple"
    choose_match = re.search(
        r"Choose\s+(TWO|THREE|FOUR|FIVE)\s+(?:letters|answers)", instruction, re.I
    )
    choice_count = WORDS[choose_match[1].upper()] if choose_match else None
    if multi and choice_count and choice_count > hi - lo + 1:
        input_type = "multi_select"
    allopts = option_list(cleaned)
    bank = (
        allopts
        if input_type in ("select", "multi_select") and kind != "multiple_choice_single"
        else []
    )
    if kind == "completion_with_word_bank":
        first_question = min((s["line"] for ss in marks.values() for s in ss), default=10**9)
        bank = [
            {"label": line_text.strip(), "text": line_text.strip(), "source_line": n}
            for n, line_text in cleaned
            if n < first_question
            and line_text.startswith("    ")
            and re.fullmatch(r"[A-Za-z][A-Za-z -]+", line_text.strip())
        ]
    if bank and len({o["label"] for o in bank}) != len(bank):
        bank = []
    # Spatial labels have no invented textual descriptions: their meaning is
    # their original position in the map. The printed range is the source.
    if (
        kind in ("map_labelling", "plan_labelling", "diagram_labelling")
        and input_type == "select"
        and not bank
        and asset_ids
    ):
        match = re.search(r"\b([A-K])\s*[-–—]\s*([A-K])\b", instruction)
        if match:
            bank = [
                {
                    "label": chr(c),
                    "text": None,
                    "visual_reference": {"asset_ids": asset_ids, "original_label": chr(c)},
                    "source_range": match[0],
                }
                for c in range(ord(match[1]), ord(match[2]) + 1)
            ]
    issues = []
    questions = []
    for q in range(lo, hi + 1):
        qissues = []
        spans = marks.get(q, [])
        opts = []
        if kind == "multiple_choice_single" and spans:
            start = next(i for i, (n, _) in enumerate(cleaned) if n == spans[0]["line"])
            end = next(
                (
                    i
                    for i, (n, _) in enumerate(cleaned[start + 1 :], start + 1)
                    if any(s["line"] == n for other, ss in marks.items() if other != q for s in ss)
                ),
                len(cleaned),
            )
            opts = option_list(cleaned[start + 1 : end])
        if not spans and (
            (multi and bank) or (lo == hi and kind == "multiple_choice_single" and allopts)
        ):
            # Explicit group number ranges define genuine separate slots.
            spans = [
                {
                    "line": lines[0][0],
                    "start": 0,
                    "end": len(lines[0][1]),
                    "text": lines[0][1],
                    "kind": "explicit_multi_answer_range",
                }
            ]
            if lo == hi and kind == "multiple_choice_single":
                opts = allopts
        if not spans:
            qissues.append("No unambiguous numbered row/blank found in prepared TXT")
        if not instruction:
            qissues.append("Missing recoverable instructions")
        if input_type is None:
            qissues.append("Question input type not established from source instructions")
        if input_type in ("select", "multi_select"):
            effective = opts or bank
            if (
                not effective
                or len(effective) < 2
                or len(set(o["label"] for o in effective)) != len(effective)
            ):
                qissues.append("Incomplete or duplicate option labels/text")
        if re.search(r"NEEDS_REVIEW", "\n".join(line_text for _, line_text in lines), re.I):
            qissues.append("Prepared source flags require original-page review")
        override = review.get("questions", {}).get(f"{exam_id}-q{q:02}", {})
        if override.get("anchor"):
            spans = [override["anchor"]]
            marks[q] = spans
            qissues = [x for x in qissues if not x.startswith("No unambiguous")]
        if override.get("resolved_source_flag"):
            qissues = [
                x for x in qissues if x != "Prepared source flags require original-page review"
            ]
        if override.get("blocked_reason"):
            qissues = [
                issue
                for issue in qissues
                if issue != "Prepared source flags require original-page review"
            ]
            qissues.append(override["blocked_reason"])
        prompt = spans[0]["text"].strip() if spans else None
        if not spans:
            issues.append(
                {
                    "question_number": q,
                    "severity": "critical",
                    "code": "missing_question_anchor",
                    "reason": "; ".join(qissues),
                }
            )
            continue  # No fabricated question objects for missing positions.
        renderable = not qissues
        verification = override.get(
            "verification", {"status": "needs_review", "method": "prepared_txt_only"}
        )
        questions.append(
            {
                "question_id": f"{exam_id}-q{q:02}",
                "question_number": q,
                "prompt": prompt,
                "input_type": input_type or "unresolved",
                "options": opts,
                "answer_bank_id": gid + "-bank"
                if bank and input_type in ("select", "multi_select")
                else None,
                "blank_references": spans,
                "constraints": {
                    **constraints(instruction),
                    "required_choices": choice_count
                    if input_type == "multi_select"
                    else 1
                    if input_type == "select"
                    else None,
                },
                "parsed": True,
                "renderable": renderable,
                "verification": verification,
                "issues": qissues,
            }
        )
        for reason in qissues:
            issues.append(
                {
                    "question_number": q,
                    "severity": "critical",
                    "code": "question_needs_review",
                    "reason": reason,
                }
            )
    complex_layout = kind in (
        "map_labelling",
        "plan_labelling",
        "diagram_labelling",
        "flow_chart_completion",
        "table_completion",
        "form_completion",
    )
    mode = "image_backed" if complex_layout and asset_ids else "structured"
    mode = group_review.get("presentation_mode", mode)
    for question in questions:
        if mode == "image_backed":
            question["visual_binding"] = {
                "asset_ids": asset_ids,
                "printed_question_number": question["question_number"],
                "source_location": question["verification"].get("source_location"),
                "presentation": "original_image_with_numbered_response_field",
            }
    if complex_layout and not asset_ids:
        for question in questions:
            question["renderable"] = False
            question["issues"].append("Required layout image missing")
        issues.append(
            {
                "question_number": None,
                "severity": "critical",
                "code": "layout_image_missing",
                "reason": "No reliable original layout asset linked",
            }
        )
    blocks = body_blocks(cleaned, marks)
    if group_review.get("original_image_is_authoritative"):
        blocks = [{"kind": "original_source_image", "asset_id": a} for a in asset_ids] + [
            {"kind": "answer_field", "question_id": q["question_id"]} for q in questions
        ]
        for q in questions:
            q["prompt"] = None
    else:
        inline = {blank["question_number"] for block in blocks for blank in block.get("blanks", [])}
        # A completion row can have its numbered anchor outside the blank;
        # keep an explicit response field rather than dropping that position.
        blocks.extend(
            {"kind": "answer_field", "question_id": q["question_id"]}
            for q in questions
            if q["question_number"] not in inline
        )
    return {
        "group_id": gid,
        "question_range": [lo, hi],
        "question_type": kind,
        "instructions": instruction,
        "constraints": constraints(instruction),
        "presentation_mode": mode,
        "answer_bank": {"bank_id": gid + "-bank", "options": bank} if bank else None,
        "selection": {
            "answer_slots": list(range(lo, hi + 1)),
            "distinct": True,
            "order": "key_controls",
            "minimum_selected": choice_count or hi - lo + 1,
            "maximum_selected": choice_count or hi - lo + 1,
        }
        if multi
        else None,
        "supporting_assets": asset_ids if mode == "image_backed" else [],
        "content_blocks": blocks,
        "structured_layout": table_layout(cleaned, marks) if kind == "table_completion" else None,
        "source_reference": src,
        "questions": questions,
    }, issues


def answer_tests(text):
    result = defaultdict(list)
    current = None
    for n, line in enumerate(text.splitlines(), 1):
        m = TEST.fullmatch(line.strip())
        if m:
            current = int(m[1])
            continue
        if current is not None:
            result[current].append((n, line))
    return result


def supplemental_keys(path):
    """Validate the supplied 60-test compilation; it never confers verification.

    Existing keys always win. Cambridge 12 uses printed Tests 5-8, not ordinals.
    Convert only explicit unordered/two-required notation to the existing format.
    """
    text = path.read_text(encoding="utf-8-sig")
    sections = re.split(r"BOOK (\d+) \| LISTENING TEST (\d+) \| QUESTIONS 01–40", text)
    result = {}
    for i in range(1, len(sections), 3):
        book, test = int(sections[i]), int(sections[i + 1])
        if book == 12 and test < 5:
            test += 4
        eid = f"cambridge-{book:02}-test-{test:02}"
        rows = []
        for number, line in enumerate(sections[i + 2].splitlines(), 1):
            match = re.fullmatch(r"(\d{2})\. (.+)", line.strip())
            if not match:
                continue
            n, answer = int(match[1]), match[2]
            unordered = re.search(
                r"\[(?:either|any) order(?: pair)? (\d+)[-–](\d+)\]", answer, re.I
            )
            if unordered:
                body = answer.split("[")[0].strip().replace(",", " | ")
                answer = f"{body} [{unordered[1]}-{unordered[2]}: IN EITHER ORDER]"
            elif "[two required]" in answer:
                answer = answer.split("[")[0].strip().replace(",", " + ") + " (IN EITHER ORDER)"
            rows.append((number, f"{n}. {answer}"))
        if eid in result or [int(KEYLINE.match(line)[1]) for _, line in rows] != list(range(1, 41)):
            raise ValueError(f"Supplemental key numbering is not exactly 1-40: {eid}")
        result[eid] = rows
    expected = {
        f"cambridge-{b:02}-test-{t:02}"
        for b in range(4, 19)
        for t in (range(5, 9) if b == 12 else range(1, 5))
    }
    if set(result) != expected:
        raise ValueError("Supplemental keys must cover exactly Cambridge 04-18")
    return result


def import_keys(exam_id, lines, source, root, key_assets, reviews):
    answers = []
    issues = []
    seen = set()
    expanded = []
    for n, line in lines:
        ranged = re.match(r"^\s*(\d{1,2})\s*[-–—]\s*(\d{1,2})[.]?\s+(.+)", line)
        if ranged:
            lo, hi = int(ranged[1]), int(ranged[2])
            raw = ranged[3]
            if 1 <= lo <= hi <= 40 and re.search(r"IN (?:EITHER|ANY) ORDER", raw, re.I):
                units = re.findall(r"\b[A-K]\b", re.split(r"\[|\s*[—–]\s*IN", raw)[0])
                if len(units) == hi - lo + 1:
                    expanded.extend(
                        (n, f"{q}. " + " | ".join(units) + f" [{lo}-{hi}: IN EITHER ORDER]")
                        for q in range(lo, hi + 1)
                    )
                    continue
        expanded.append((n, line))
    for n, line in expanded:
        m = KEYLINE.match(line)
        if not m:
            continue
        q = int(m[1])
        raw = m[2].strip()
        if not 1 <= q <= 40:
            continue
        if q in seen:
            issues.append(
                {
                    "question_number": q,
                    "severity": "critical",
                    "code": "duplicate_key",
                    "reason": f"Duplicate answer line {n}",
                }
            )
            continue
        seen.add(q)
        if re.search(r"NOT AVAILABLE|NOT PROVIDED|SOURCE_REQUIRED|MISSING|not supplied", raw, re.I):
            issues.append(
                {"question_number": q, "severity": "critical", "code": "key_missing", "reason": raw}
            )
            continue
        # Preserve printed notation verbatim; do not expand parentheses by guesses.
        answer = re.split(r"\s*\[", raw, maxsplit=1)[0].strip()
        alternative_separator = "/" if "/" in answer else None
        alternatives = [v.strip() for v in answer.split("/")] if alternative_separator else [answer]
        if "|" in answer:
            alternatives = []  # Group units, not alternatives for one slot.
        verification = reviews.get("keys", {}).get(
            f"{exam_id}-q{q:02}", {"status": "needs_review", "method": "prepared_answer_txt_only"}
        )
        if verification.get("official_answer_override"):
            answer = verification["official_answer_override"]
            alternatives = verification.get("alternatives", [answer])
        answers.append(
            {
                "question_id": f"{exam_id}-q{q:02}",
                "question_number": q,
                "official_answer": answer,
                "source_notation": raw,
                "explicit_slash_forms": alternatives,
                "parenthetical_notation_requires_source_interpretation": "(" in answer,
                "unordered_group": None,
                "source_reference": {
                    "file": str(source.relative_to(root))
                    if source.is_relative_to(root)
                    else str(source.relative_to(ROOT)),
                    "line": n,
                    "evidence_assets": key_assets,
                },
                "verification": verification,
            }
        )
    for q in sorted(set(range(1, 41)) - {a["question_number"] for a in answers}):
        issues.append(
            {
                "question_number": q,
                "severity": "critical",
                "code": "key_missing",
                "reason": "No official answer entry in prepared answer TXT",
            }
        )
    unordered_evidence = []
    for n, line in lines:
        m = re.search(r"Questions?\s*(\d{1,2})\s*(?:[-–—&]|and)\s*(\d{1,2})", line, re.I)
        if m and re.search(r"IN (?:EITHER|ANY) ORDER", line, re.I):
            unordered_evidence.append(
                {
                    "question_numbers": list(range(int(m[1]), int(m[2]) + 1)),
                    "source_line": n,
                    "text": line,
                }
            )
    return {
        "exam_id": exam_id,
        "visibility": "private",
        "answers": answers,
        "unordered_groups": [],
        "unordered_evidence": unordered_evidence,
        "within_position_rules": [],
    }, issues


def link_key_groups(key, exam):
    byq = {a["question_number"]: a for a in key["answers"]}
    for part in exam["parts"]:
        for g in part["groups"]:
            if not g["selection"] or len(g["selection"]["answer_slots"]) < 2:
                continue
            ns = g["selection"]["answer_slots"]
            entries = [byq[n] for n in ns if n in byq]
            if len(entries) != len(ns):
                continue
            # Require explicit unordered evidence in key TXT or its source header.
            explicit = (
                any(re.search(r"(?:EITHER|ANY) ORDER", a["source_notation"], re.I) for a in entries)
                or bool(re.search(r"(?:EITHER|ANY) ORDER", key.get("source_header", ""), re.I))
                or any(e["question_numbers"] == ns for e in key["unordered_evidence"])
            )
            keyid = g["group_id"] + "-keyset"
            units = []
            for a in entries:
                candidates = [v.strip() for v in re.split(r"\s*[|/]\s*", a["official_answer"])]
                for c in candidates:
                    c = re.sub(r"\s*\(?IN (?:EITHER|ANY) ORDER\)?.*", "", c, flags=re.I).strip()
                    if c and c not in units:
                        units.append(c)
            if explicit and len(units) == len(ns):
                key["unordered_groups"].append(
                    {
                        "group_id": keyid,
                        "question_numbers": ns,
                        "expected_units": units,
                        "order": "unordered",
                        "distinct": True,
                        "evidence": (
                            "explicit key notation or scoped key-document introduction "
                            "with multi-answer task instruction"
                        ),
                    }
                )
                for a in entries:
                    a["unordered_group"] = keyid
                g["selection"]["order"] = "unordered"
            else:
                g["selection"]["order"] = "needs_review"
    # Unordered answers also occur in ordinary text-completion slots, not only
    # letter choices. E.g. Cambridge 06 T1 Q26–27: laptops and printers.
    for answer in key["answers"]:
        raw = answer["source_notation"]
        if not re.search(r"IN (?:EITHER|ANY) ORDER", raw, re.I):
            continue
        matched = re.search(r"\[Q?(\d{1,2})\s*[-–—]\s*(\d{1,2})\s*:", raw, re.I)
        if matched:
            numbers = list(range(int(matched[1]), int(matched[2]) + 1))
            entries = [byq[n] for n in numbers if n in byq]
            units = list(
                dict.fromkeys(v.strip() for a in entries for v in a["official_answer"].split("|"))
            )
            if len(entries) == len(numbers) == len(units) and not any(
                a["unordered_group"] for a in entries
            ):
                gid = key["exam_id"] + f"-keyset-{numbers[0]:02}-{numbers[-1]:02}"
                key["unordered_groups"].append(
                    {
                        "group_id": gid,
                        "question_numbers": numbers,
                        "expected_units": units,
                        "order": "unordered",
                        "distinct": True,
                        "evidence": raw,
                    }
                )
                for entry in entries:
                    entry["unordered_group"] = gid
        elif "|" in answer["official_answer"] or "+" in answer["official_answer"]:
            body = re.split(r"\s*\(IN (?:EITHER|ANY) ORDER", answer["official_answer"], flags=re.I)[
                0
            ]
            units = re.split(r"\s*[|+]\s*", body)
            if len(units) >= 2:
                key["within_position_rules"].append(
                    {
                        "question_number": answer["question_number"],
                        "question_id": answer["question_id"],
                        "kind": "all_components_required",
                        "order": "unordered",
                        "marks": 1,
                        "components": [
                            {"explicit_slash_forms": [v.strip() for v in unit.split("/")]}
                            for unit in units
                        ],
                        "source_notation": raw,
                    }
                )


def run(input_root, output, pdf_root):
    if output.exists() and (output / "manifest.json").exists():
        old = json.loads((output / "manifest.json").read_text())
        if old.get("producer") != "listtest-stage1":
            raise ValueError(
                "Existing dataset from another producer: archive and compare provenance "
                "explicitly before import"
            )
    output.mkdir(parents=True, exist_ok=True)
    write_schemas(output)
    (output / "qa").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(VISUAL_REGISTRY, output / "qa/visual_materials.json")
    assets = Assets(input_root, output)
    reviews = json.loads((HERE / "source_reviews.json").read_text())
    for rel, digest in reviews.get("pinned_sources", {}).items():
        path = ROOT / rel if rel.startswith(("ieltsbooks/", "backend/")) else input_root / rel
        if not path.exists() or sha(path.read_bytes()) != digest:
            raise ValueError(f"Reviewed source changed: {rel}; explicit re-review required")
    supplement_path = HERE / "sources/answer_keys_04_18.txt"
    supplements = supplemental_keys(supplement_path)
    recovered_by_part = {}
    for record in reviews.get("recovered_assets", []):
        aid = assets.add(
            ROOT / record["file"],
            record["book"],
            "source_page",
            record["test"],
            record["part"],
            record["pdf_page"],
        )
        recovered_by_part.setdefault((record["book"], record["test"], record["part"]), []).append(
            (aid, record)
        )
    all_issues = []
    catalog = []
    inventories = []
    book12 = []
    for b in range(4, 22):
        directory = input_root / f"Cambridge_IELTS_{b:02}"
        inv = {"book": b, "canonical_files": {}, "files": [], "pdf": None}
        task = choose_txt(directory, f"Cambridge_IELTS_{b:02}_Listening.txt", inv)
        answer = choose_txt(directory, f"Cambridge_IELTS_{b:02}_Listening_Answers.txt", inv)
        texts = split_tests(task.read_text(encoding="utf-8-sig"))
        keys = answer_tests(answer.read_text(encoding="utf-8-sig"))
        expected_tests = list(range(5, 9)) if b == 12 else list(range(1, 5))
        if sorted(texts) != expected_tests:
            raise ValueError(f"Book {b}: unexpected test IDs {sorted(texts)}")
        pdfs = sorted(pdf_root.rglob(f"Cambridge-IELTS-{b:02}.pdf"))
        if pdfs:
            inv["pdf"] = {
                "file": str(pdfs[0].relative_to(ROOT))
                if pdfs[0].is_relative_to(ROOT)
                else pdfs[0].name,
                "sha256": sha(pdfs[0].read_bytes()),
            }
        images = []
        for p in sorted(directory.rglob("*")):
            if not p.is_file() or p.name.startswith("."):
                continue
            inv["files"].append(
                {
                    "file": str(p.relative_to(input_root)),
                    "sha256": sha(p.read_bytes()),
                    "bytes": p.stat().st_size,
                }
            )
            if p.suffix.lower() in IMAGE_EXT:
                images.append(p)
        image_ids = {}
        for path in images:
            rel = str(path.relative_to(directory))
            name = path.name
            tm = re.search(r"Test[_\s-]*(\d)", name, re.I)
            pm = re.search(r"(?:Section|Part)[_\s-]*(\d)", name, re.I)
            pagem = re.search(r"PDF(?:_Page)?[_\s-]*(\d{1,3})", name, re.I)
            t = int(tm[1]) if tm else None
            p = int(pm[1]) if pm else None
            page = int(pagem[1]) if pagem else None
            private = bool(re.search(r"answer|key", rel, re.I)) or (
                page in KEY_PAGES.get(b, []) and not pm
            )
            role = "answer_key_evidence" if private else ("source_page" if pagem else "task_image")
            try:
                aid = assets.add(path, b, role, t, p, page)
            except (OSError, ValueError):
                if not pdfs or page is None:
                    raise
                # Recovery is limited to the exact broken supplied image page.
                with tempfile.TemporaryDirectory(prefix="alua-listtest-image-") as temporary:
                    recovered = Path(temporary) / f"Cambridge-IELTS-{b:02}-page-{page:03}.png"
                    with fitz.open(pdfs[0]) as doc:
                        doc[page - 1].get_pixmap(matrix=fitz.Matrix(2, 2)).save(recovered)
                    aid = assets.add(recovered, b, role, t, p, page)
                assets.records[aid]["recovery"] = {
                    "reason": "Supplied image fails image decoding",
                    "original_source": str(path.relative_to(input_root)),
                    "source_pdf": inv["pdf"],
                    "page": page,
                    "method": "PyMuPDF 2x original page render; no OCR",
                }
                assets.records[aid]["sources"] = [str(path.relative_to(input_root))]
            image_ids[path] = aid
        # Reviewed Stage 2 derivatives enter the same asset registry/allowlist.
        # Missing or changed original PDFs fail closed instead of reviving old crops.
        repair_ids = add_repaired_assets(assets, pdfs[0] if pdfs else None, b)
        repair_ids += add_source_fidelity_assets(assets, pdfs[0] if pdfs else None, b)
        for ordinal, t in enumerate(expected_tests, 1):
            eid = f"cambridge-{b:02}-test-{t:02}"
            if b == 12:
                book12.append(
                    {
                        "exam_id": eid,
                        "local_ordinal": ordinal,
                        "printed_test_number": t,
                        "basis": "explicit TEST 5–8 headings in prepared source",
                    }
                )
            exam = {
                "schema_version": SCHEMA_VERSION,
                "exam_id": eid,
                "book": b,
                "printed_test_number": t,
                "local_ordinal": ordinal,
                "module": "listening",
                "parts": [],
                "assets": [],
                "validation": {},
            }
            exam_issues = []
            used_assets = set()
            for p in range(1, 5):
                lines = texts[t].get(p, [])
                raw = "\n".join(line_text for _, line_text in lines)
                pages = page_numbers(raw)
                selected = []
                for path, aid in image_ids.items():
                    record = assets.records[aid]
                    if record["visibility"] != "public":
                        continue
                    matching = path.name in raw
                    assoc = record["associations"]
                    matching = matching or any(
                        a["printed_test_number"] == t and a["part_number"] == p for a in assoc
                    )
                    matching = matching or any(
                        a["pdf_page"] in pages and a["pdf_page"] is not None for a in assoc
                    )
                    if matching and aid not in selected:
                        selected.append(aid)
                for aid, recovery in recovered_by_part.get((b, t, p), []):
                    replaced = recovery.get("replaces_pages")
                    selected = (
                        [
                            old
                            for old in selected
                            if not any(
                                association["book"] == b and association["pdf_page"] in replaced
                                for association in assets.records[old]["associations"]
                            )
                        ]
                        if replaced
                        else []
                    )
                    selected.append(aid)
                used_assets.update(selected)
                for aid in selected:
                    rec = assets.records[aid]
                    ownership = reviewed_associations(aid, b)
                    if ownership and (t, p) not in ownership:
                        continue
                    pg = next(
                        (
                            a["pdf_page"]
                            for a in rec["associations"]
                            if a["book"] == b and a["pdf_page"] in pages
                        ),
                        None,
                    )
                    association = {
                        "book": b,
                        "printed_test_number": t,
                        "part_number": p,
                        "pdf_page": pg,
                    }
                    if association not in rec["associations"]:
                        rec["associations"].append(association)
                ref = source_ref(task, input_root, lines, pages)
                part = {
                    "part_number": p,
                    "question_range": [(p - 1) * 10 + 1, p * 10],
                    "display_order": p,
                    "instructions": [],
                    "source_reference": ref,
                    "supporting_assets": selected,
                    "audio_mapping_key": {
                        "book": b,
                        "printed_test_number": t,
                        "local_ordinal": ordinal,
                        "part_number": p,
                    },
                    "groups": [],
                }
                for lo, hi, glines in group_ranges(lines, (p - 1) * 10 + 1, p * 10):
                    gref = source_ref(task, input_root, glines, pages)
                    group, issues = import_group(
                        eid, p, lo, hi, glines, gref, pages, selected, reviews
                    )
                    part["groups"].append(group)
                    for issue in issues:
                        exam_issues.append(
                            {
                                **issue,
                                "part_number": p,
                                "group_id": group["group_id"],
                                "source_reference": gref,
                            }
                        )
                exam["parts"].append(part)
            used_assets.update(
                aid for aid in repair_ids
                if any(a["printed_test_number"] == t for a in assets.records[aid]["associations"])
            )
            exam["assets"] = [assets.public_record(aid) for aid in sorted(used_assets)]
            apply_visual_materials(exam)
            key_assets = [
                aid
                for aid, r in assets.records.items()
                if r["visibility"] == "private"
                and any(
                    a["book"] == b
                    and (
                        a["printed_test_number"] == t
                        or a["pdf_page"] == KEY_PAGES.get(b, [None] * 4)[ordinal - 1]
                    )
                    for a in r["associations"]
                )
            ]
            key, kissues = import_keys(
                eid, keys.get(t, []), answer, input_root, sorted(key_assets), reviews
            )
            if not key["answers"] and eid in supplements:
                key, kissues = import_keys(
                    eid, supplements[eid], supplement_path, input_root, sorted(key_assets), reviews
                )
            key["source_header"] = (
                answer.read_text(encoding="utf-8-sig").split("TEST 1")[0].split("TEST 5")[0]
            )
            link_key_groups(key, exam)
            for issue in kissues:
                exam_issues.append(
                    {
                        **issue,
                        "part_number": (issue["question_number"] - 1) // 10 + 1,
                        "source_reference": {"file": str(answer.relative_to(input_root))},
                    }
                )
            questions = [q for p in exam["parts"] for g in p["groups"] for q in g["questions"]]
            v = {
                "parsed_questions": len(questions),
                "interactive_questions": sum(q["renderable"] for q in questions),
                "source_verified_questions": sum(
                    q["verification"]["status"] == "source_verified" for q in questions
                ),
                "keys_present": len(key["answers"]),
                "key_verified_positions": sum(
                    a["verification"]["status"] == "key_verified" for a in key["answers"]
                ),
                "missing_positions": sorted(
                    set(range(1, 41)) - {q["question_number"] for q in questions}
                ),
                "blocked_positions": sorted(
                    q["question_number"] for q in questions if not q["renderable"]
                ),
            }
            v["complete_question_content"] = v["interactive_questions"] == 40
            v["complete_verified_keys"] = v["key_verified_positions"] == 40
            v["ready_for_stage2"] = (
                v["complete_question_content"]
                and v["source_verified_questions"] == 40
                and v["complete_verified_keys"]
            )
            exam["validation"] = v
            dump(output / "exams" / f"{eid}.json", exam)
            dump(output / "keys" / f"{eid}.json", key)
            qa = {
                "exam_id": eid,
                "book": b,
                "printed_test_number": t,
                "counts": v,
                "issues": exam_issues,
                "source_findings": [
                    n for n in reviews.get("review_notes", []) if n["book"] == b and n["test"] == t
                ],
                "key_quality": {
                    "present": len(key["answers"]),
                    "source_verified": v["key_verified_positions"],
                    "missing": sorted(
                        set(range(1, 41)) - {a["question_number"] for a in key["answers"]}
                    ),
                    "unverified": sorted(
                        a["question_number"]
                        for a in key["answers"]
                        if a["verification"]["status"] != "key_verified"
                    ),
                    "ambiguous": [],
                },
                "editorial_review_pending": {
                    "question_numbers": [
                        q["question_number"]
                        for q in questions
                        if q["verification"]["status"] != "source_verified"
                    ],
                    "key_numbers": [
                        a["question_number"]
                        for a in key["answers"]
                        if a["verification"]["status"] != "key_verified"
                    ],
                },
            }
            dump(output / "qa/exams" / f"{eid}.json", qa)
            all_issues.extend(
                {"exam_id": eid, "book": b, "printed_test_number": t, **i} for i in exam_issues
            )
            catalog.append(
                {"exam_id": eid, "book": b, "printed_test_number": t, "local_ordinal": ordinal, **v}
            )
        inventories.append(inv)
        print(
            f"Book {b:02d}: "
            + ", ".join(
                f"T{c['printed_test_number']} {c['interactive_questions']}/40"
                for c in catalog
                if c["book"] == b
            ),
            flush=True,
        )
    for record in assets.records.values():
        record["sources"].sort()
        record["roles"].sort()
        record["associations"].sort(key=lambda a: json.dumps(a, sort_keys=True))
    totals = {
        key: sum(c[key] for c in catalog)
        for key in (
            "parsed_questions",
            "interactive_questions",
            "source_verified_questions",
            "keys_present",
            "key_verified_positions",
            "complete_question_content",
            "complete_verified_keys",
            "ready_for_stage2",
        )
    }
    totals.update(
        {
            "books_processed": 18,
            "exams_processed": 72,
            "parts_processed": 288,
            "missing_questions": sum(len(c["missing_positions"]) for c in catalog),
            "blocked_questions": sum(len(c["blocked_positions"]) for c in catalog),
            "critical_issues": len([i for i in all_issues if i["severity"] == "critical"]),
        }
    )
    dump(
        output / "manifest.json",
        {
            "producer": "listtest-stage1",
            "schema_version": SCHEMA_VERSION,
            "stage": 1,
            "audio_in_scope": False,
            "source_policy": [
                "visual_original_pdf",
                "official_key_image",
                "prepared_txt",
                "supporting_manifest",
            ],
            "totals": totals,
            "exams": catalog,
            "generator_sha256": {
                p.name: sha(p.read_bytes())
                for p in sorted(HERE.glob("*"))
                if p.suffix in (".py", ".json")
            },
            "schema_sha256": {
                p.name: sha(p.read_bytes()) for p in sorted((output / "schemas").glob("*.json"))
            },
            "visual_materials_sha256": sha(VISUAL_REGISTRY.read_bytes()),
        },
    )
    dump(output / "qa/input_inventory.json", inventories)
    dump(output / "qa/assets.json", {"assets": [assets.records[a] for a in sorted(assets.records)]})
    dump(output / "qa/issues.json", all_issues)
    dump(output / "qa/cambridge12_mapping.json", book12)
    dump(
        output / "qa/source_review_policy.json",
        {
            "independent_verification": (
                "Only explicit reviewed positions in source_reviews.json can receive "
                "source_verified/key_verified. Supplied manifest claims and copied images "
                "do not confer verification."
            ),
            "private_assets": (
                "Never serve assets/private or keys or qa via a static public mount. "
                "Public API must allowlist exams and referenced public assets only."
            ),
            "pdf_presence": "Finding a PDF or matching metadata is not visual verification.",
        },
    )
    return totals


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--pdf-root", type=Path, default=ROOT / "ieltsbooks")
    args = parser.parse_args()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    previous = None
    if (output / "manifest.json").exists():
        previous = json.loads((output / "manifest.json").read_text())
        if previous.get("producer") != "listtest-stage1":
            raise ValueError("Refusing to replace a different Listening dataset producer")
    with tempfile.TemporaryDirectory(prefix=".listening-stage1-", dir=output.parent) as temporary:
        staged = Path(temporary) / "dataset"
        totals = run(args.input.resolve(), staged, args.pdf_root.resolve())
        if previous:
            if (output / "qa/history").exists():
                shutil.copytree(output / "qa/history", staged / "qa/history")
            changed = []
            for category in ("exams", "keys"):
                for old in sorted((output / category).glob("*.json")):
                    new = staged / category / old.name
                    if not new.exists() or old.read_bytes() != new.read_bytes():
                        changed.append(f"{category}/{old.name}")
            if changed:
                revision = sha((output / "manifest.json").read_bytes())
                history = staged / "qa/history" / revision
                for category in ("exams", "keys", "schemas"):
                    shutil.copytree(output / category, history / category)
                for rel in ("manifest.json", "qa/assets.json", "qa/input_inventory.json"):
                    target = history / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(output / rel, target)
                dump(
                    history / "comparison.json",
                    {
                        "previous_manifest_sha256": revision,
                        "changed_documents": changed,
                        "policy": (
                            "Original exam/key documents, schemas and provenance retained "
                            "before replacement. Old content-addressed image bytes retained."
                        ),
                    },
                )
                # Historical documents can continue to resolve their old assets.
                for old in (output / "assets").rglob("*"):
                    if old.is_file():
                        new = staged / old.relative_to(output)
                        if not new.exists():
                            new.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(old, new)
        from validator import validate

        validation = validate(staged)
        dump(staged / "qa/validation.json", validation)
        if not validation["technical_integrity"]:
            raise ValueError(json.dumps(validation["errors"], ensure_ascii=False, indent=2))
        from report import position_audit

        position_audit(staged)
        # Same-filesystem rename; restore the old directory if replacement fails.
        old_path = Path(temporary) / "previous"
        if output.exists():
            os.replace(output, old_path)
        try:
            os.replace(staged, output)
        except BaseException:
            if old_path.exists():
                os.replace(old_path, output)
            raise
        print(json.dumps(totals, indent=2))


if __name__ == "__main__":
    main()
