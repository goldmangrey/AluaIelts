"""Conservative source metadata, PDF layout fallbacks and bounded enrichment."""

import json
import re
import unicodedata
from pathlib import Path

from pdf_support import crop_group


def needs_layout(g):
    return (
        g["type"] in ["table_completion", "flow_chart_completion", "diagram_labelling"]
        or (
            g["type"] == "multiple_choice_single"
            and any(len(q["options"]) < 2 for q in g["questions"])
        )
        or (
            g["type"]
            in {
                "true_false_not_given",
                "yes_no_not_given",
                "matching_headings",
                "matching_information",
                "matching_features",
                "matching_sentence_endings",
                "short_answer",
            }
            and len(g["questions"]) > 1
            and any(q["prompt"] == text(g) for q in g["questions"])
        )
        or (g["type"] == "multiple_choice_multiple" and len(g["options"]) <= len(g["questions"]))
        or bool(re.search(r"following diagrams|following figures", text(g), re.I))
    )


def text(g):
    return "".join(
        s.get("text", "")
        for b in g["content_blocks"]
        if b["type"] == "rich_text"
        for s in b["segments"]
    )


def enrich_exam(e, k, base):
    from engine import ROOT, expand_pages, options
    from labels import apply_labels

    reviews = json.loads(Path(__file__).with_name("source_reviews.json").read_text())
    location = reviews["key_page_locations"].get(str(e["source_book"]))
    if location:
        for answer in k["answers"]:
            answer["source_reference"]["pdf_pages"] = [location[e["test_ordinal"] - 1]]
    for review in reviews["keys"]:
        if review["exam_id"] == e["id"]:
            for answer in k["answers"]:
                if answer["number"] in review["question_numbers"]:
                    answer["verification_status"] = "source_verified"
                    answer["source_reference"]["pdf_pages"] = [review["pdf_page"]]
                    override = review["accepted_answer_overrides"].get(str(answer["number"]))
                    if override:
                        answer["accepted_answers"] = override
            e["verification"]["keys"] = "source_verified"
    for p in e["passages"]:
        apply_labels(p)
        src = p["source_reference"]
        if not p["source_pages"] and e["source_book"] == 13:
            lines = Path(ROOT / src["txt_file"]).read_text().splitlines()
            meta = "\n".join(lines[src["line_start"] - 1 : src["line_start"] + 8])
            m = re.search(r"Source printed pages:\s*([^\n]+)", meta)
            if m:
                p["source_pages"] = [n + 1 for n in expand_pages(m[1])]
                src["pdf_pages"] = p["source_pages"]
        for g in p["question_groups"]:
            if g["type"] == "matching_information":
                match = re.search(r"\b([A-Z])\s*[-–—]+\s*([A-Z])\b", text(g))
                if match:
                    labels = [chr(value) for value in range(ord(match[1]), ord(match[2]) + 1)]
                    g["options"] = [{"label": label, "text": label} for label in labels]
                    g["constraints"]["allowed_values"] = labels
                    for question in g["questions"]:
                        question["constraints"]["allowed_values"] = labels
            # Unicode Roman labels are equivalent, not an editorial content repair.
            if g["type"] == "matching_headings":
                g["options"] = options(unicodedata.normalize("NFKC", text(g)).lower(), True)
                for q in g["questions"]:
                    q["constraints"]["allowed_values"] = [o["label"] for o in g["options"]]
            if needs_layout(g):
                g["assets"] = crop_group(
                    ROOT / src["pdf_file"],
                    p["source_pages"],
                    g["question_numbers"],
                    base,
                    g["id"],
                    allow_continuation=g["type"]
                    in {"table_completion", "flow_chart_completion", "diagram_labelling"},
                )
                for a in g["assets"]:
                    a["pdf_file"] = src["pdf_file"]
                if g["assets"]:
                    g["representation"] = "source_image_with_inputs"
                    g["content_blocks"] += [
                        {
                            "type": "image",
                            "asset_id": a["id"],
                            "alt": f"Original task, questions {a['question_numbers']}",
                        }
                        for a in g["assets"]
                    ]
            rows = []
            records = re.split(r"(?m)^Stepwell: ", text(g))[1:]
            if records:
                for record in records:
                    lines = record.strip().splitlines()
                    fields = {}
                    fields["Stepwell"] = lines[0]
                    for line in lines[1:]:
                        if ": " in line:
                            name, value = line.split(": ", 1)
                            fields[name] = value
                    columns = ["Stepwell", "Date", "Features", "Other notes"]
                    if all(c in fields for c in columns):
                        from engine import rich_text

                        rows.append(
                            [
                                {"segments": rich_text(fields[c], g["question_numbers"])}
                                for c in columns
                            ]
                        )
                if len(rows) == len(records):
                    g["content_blocks"].append({"type": "table", "columns": columns, "rows": rows})
            bullets = [
                line.lstrip("•- ").strip()
                for line in text(g).splitlines()
                if re.match(r"^\s*[•-]\s+\S", line)
            ]
            if bullets:
                from engine import rich_text

                g["content_blocks"].append(
                    {
                        "type": "list",
                        "items": [rich_text(v, g["question_numbers"]) for v in bullets],
                    }
                )
            # Missing paragraph-number labels are never reconstructed by blind ordinal assignment.
            for q in g["questions"]:
                if q["answer_input_type"] == "boolean":
                    q["options"] = [
                        {"label": v, "text": v} for v in q["constraints"]["allowed_values"]
                    ]
    e["source_references"][0]["pdf_pages"] = sorted(
        {n for p in e["passages"] for n in p["source_pages"]}
    )


def content_issues(e, k):
    issues = []

    def add(code, detail, p=None, q=None, pp=None):
        issues.append(
            {
                "code": code,
                "detail": detail,
                "exam_id": e["id"],
                "book": e["source_book"],
                "test": e["source_test_number"],
                "passage": p,
                "question": q,
                "pdf_pages": pp if pp is not None else e["source_references"][0]["pdf_pages"],
            }
        )

    if e["id"] == "cambridge-07-test-02":
        add(
            "source_obscured_by_watermark",
            (
                "Blue advertising watermark over passage paragraph on page 45 "
                "obscures words. No guessed reconstruction supplied."
            ),
            1,
            None,
            [45],
        )
    if e["id"] == "cambridge-10-test-01":
        add(
            "binding_obscures_text",
            (
                "Stepwells page 9 has partially obscured letters near binding; "
                "repaired transcription requires final proofreading."
            ),
            1,
            None,
            [9],
        )
    if e["source_book"] == 9:
        add(
            "key_source_unavailable",
            (
                "TXT states keys came from an external copy, not supplied local "
                "PDF; cannot locally source-verify."
            ),
            pp=[],
        )
    if e["id"] == "cambridge-20-test-03":
        add(
            "source_option_label_anomaly",
            (
                "PDF p.94 labels stem A and options B–F despite A–E instructions. "
                "Official key labels cannot be resolved safely."
            ),
            2,
            [22, 23],
            [94],
        )
    if e["id"] == "cambridge-04-test-03":
        add(
            "source_range_typo",
            (
                "PDF p.82 prints Questions 13; actual numbered Section A–D tasks "
                "and answer boxes are 14–17. Metadata uses actual tasks."
            ),
            2,
            [14, 15, 16, 17],
            [82],
        )
    unlocated = [a["number"] for a in k["answers"] if not a["source_reference"]["pdf_pages"]]
    if unlocated and e["source_book"] != 9:
        add(
            "key_page_unlocated",
            (
                "Exact local PDF key page has not been established; original TXT "
                "key lines are preserved."
            ),
            q=unlocated,
            pp=[],
        )
    for p in e["passages"]:
        body = "\n".join(x["text"] for x in p["content"])
        if re.search(
            (
                "[\\u3400-\\u9fff\\ufffd]|\\b[A-Za-z]+[!$=][A-Za-z]+|\\b\\w*[_=]{2,}\\w+|"
                "\\b(?:REVIEW FLAG|REVIEW NOTE|watermark|obscur|unreadable|unclear)"
                "\\b"
            ),
            body,
            re.I,
        ):
            add(
                "suspected_text_corruption",
                (
                    "Passage contains OCR artifacts or an explicit uncertainty note; "
                    "inspect referenced source pages."
                ),
                p["number"],
                pp=p["source_pages"],
            )
        if p["title"].isdigit() or p["title"].lower().startswith("untitled"):
            add(
                "title_needs_review",
                "Original title missing or not established; do not display an invented heading.",
                p["number"],
                pp=p["source_pages"],
            )
        for g in p["question_groups"]:
            raw = text(g)
            if needs_layout(g) and not g["assets"]:
                add(
                    "layout_not_recovered",
                    "Original layout requires a PDF crop or verified typed structure.",
                    p["number"],
                    g["question_numbers"],
                    p["source_pages"],
                )
            if g["assets"] and any(
                a["verification_status"] != "visually_verified" for a in g["assets"]
            ):
                add(
                    "asset_visual_review_required",
                    (
                        "Crop boundaries were found locally by OCR; compare crop with PDF "
                        "before release."
                    ),
                    p["number"],
                    g["question_numbers"],
                    sorted({a["pdf_page"] for a in g["assets"]}),
                )
            if g["type"] == "multiple_choice_single" and any(
                len(q["options"]) < 2 for q in g["questions"]
            ):
                add(
                    "options_via_source_image",
                    (
                        "OCR lost numeric labels or option labels; use the original task "
                        "image and separate answer positions. Typed per-question options "
                        "need review."
                    ),
                    p["number"],
                    g["question_numbers"],
                    p["source_pages"],
                )
            if (
                g["type"].startswith("matching")
                and not g["options"]
                and g["type"] != "matching_information"
            ):
                add(
                    "matching_options_missing",
                    "Shared option list not reliably segmented.",
                    p["number"],
                    g["question_numbers"],
                    p["source_pages"],
                )
            if re.search(
                (
                    "\\[(?:REVIEW|.*unclear|.*unreadable)|[\\u3400-\\u9fff\\ufffd]|\\b(?:o{"
                    "3,}|c{3,}|[a-z]+[=!$][a-z]+)\\b"
                ),
                raw,
                re.I,
            ):
                add(
                    "suspected_question_corruption",
                    "Question group contains OCR artifacts or explicit review note.",
                    p["number"],
                    g["question_numbers"],
                    p["source_pages"],
                )
    return issues
