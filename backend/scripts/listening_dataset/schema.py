"""Closed JSON contracts shared by the offline importer and Stage 2 consumers."""

import json
from pathlib import Path


def obj(properties, required=None):
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties) if required is None else required,
        "additionalProperties": False,
    }


def arr(item, **kw):
    return {"type": "array", "items": item, **kw}


S = {"type": "string"}
INTEGER = {"type": "integer"}
B = {"type": "boolean"}
NULL_S = {"type": ["string", "null"]}
POS = {"type": "integer", "minimum": 1, "maximum": 40}
RANGE = arr(POS, minItems=2, maxItems=2)
SOURCE = obj(
    {
        "file": S,
        "line_start": {"type": ["integer", "null"]},
        "line_end": {"type": ["integer", "null"]},
        "pdf_pages": arr(INTEGER),
        "pdf_page_basis": S,
    }
)
VERIFICATION = {
    "type": "object",
    "required": ["status", "method"],
    "properties": {
        "status": {"enum": ["needs_review", "source_required", "source_verified", "key_verified"]},
        "method": S,
    },
    "additionalProperties": True,
}
OPTION = obj(
    {
        "label": S,
        "text": NULL_S,
        "source_line": INTEGER,
        "visual_reference": obj({"asset_ids": arr(S, minItems=1), "original_label": S}),
        "source_range": S,
    },
    ["label", "text"],
)
CONSTRAINTS = obj(
    {
        "max_words": {"type": ["integer", "null"]},
        "max_numbers": {"type": ["integer", "null"]},
        "allows_number": B,
        "instruction": S,
        "normalization": S,
        "spelling": S,
        "required_choices": {"type": ["integer", "null"]},
    },
    ["max_words", "max_numbers", "allows_number", "instruction", "normalization", "spelling"],
)
ASSET = obj(
    {
        "asset_id": S,
        "relative_path": S,
        "sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
        "byte_size": INTEGER,
        "width": {"type": "integer", "minimum": 1},
        "height": {"type": "integer", "minimum": 1},
    }
)
ANCHOR = obj(
    {
        "line": INTEGER,
        "start": INTEGER,
        "end": INTEGER,
        "text": S,
        "kind": S,
        "pdf_page": INTEGER,
        "locator": S,
    },
    ["line", "start", "end", "text", "kind"],
)
QUESTION = obj(
    {
        "question_id": S,
        "question_number": POS,
        "prompt": NULL_S,
        "input_type": {"enum": ["text", "select", "multi_select", "unresolved"]},
        "options": arr(OPTION),
        "answer_bank_id": NULL_S,
        "blank_references": arr(ANCHOR, minItems=1),
        "constraints": CONSTRAINTS,
        "parsed": B,
        "renderable": B,
        "verification": VERIFICATION,
        "issues": arr(S),
        "visual_binding": obj(
            {
                "asset_ids": arr(S, minItems=1),
                "printed_question_number": POS,
                "source_location": NULL_S,
                "presentation": S,
            }
        ),
    },
    [
        "question_id",
        "question_number",
        "prompt",
        "input_type",
        "options",
        "answer_bank_id",
        "blank_references",
        "constraints",
        "parsed",
        "renderable",
        "verification",
        "issues",
    ],
)
BLANK = obj({"question_number": POS, "start": INTEGER, "end": INTEGER})
BLOCK = {
    "oneOf": [
        obj(
            {
                "kind": {"const": "source_line"},
                "text": S,
                "source_line": INTEGER,
                "blanks": arr(BLANK),
            }
        ),
        obj({"kind": {"const": "original_source_image"}, "asset_id": S}),
        obj({"kind": {"const": "answer_field"}, "question_id": S}),
    ]
}
KINDS = [
    "multiple_choice_single",
    "multiple_choice_multiple",
    "matching",
    "form_completion",
    "note_completion",
    "table_completion",
    "flow_chart_completion",
    "summary_completion",
    "sentence_completion",
    "short_answer",
    "map_labelling",
    "plan_labelling",
    "diagram_labelling",
    "completion_with_word_bank",
    "unclassified",
]
GROUP = obj(
    {
        "group_id": S,
        "question_range": RANGE,
        "question_type": {"enum": KINDS},
        "instructions": S,
        "constraints": CONSTRAINTS,
        "presentation_mode": {"enum": ["structured", "image_backed"]},
        "answer_bank": {
            "anyOf": [{"type": "null"}, obj({"bank_id": S, "options": arr(OPTION, minItems=2)})]
        },
        "selection": {
            "anyOf": [
                {"type": "null"},
                obj(
                    {
                        "answer_slots": arr(POS, minItems=1, uniqueItems=True),
                        "distinct": B,
                        "order": {"enum": ["unordered", "needs_review", "key_controls"]},
                        "minimum_selected": INTEGER,
                        "maximum_selected": INTEGER,
                    }
                ),
            ]
        },
        "supporting_assets": arr(S),
        "content_blocks": arr(BLOCK, minItems=1),
        "structured_layout": {
            "anyOf": [
                {"type": "null"},
                obj(
                    {
                        "kind": {"const": "table"},
                        "rows": arr(
                            obj(
                                {
                                    "source_line": INTEGER,
                                    "cells": arr(
                                        obj({"text": S, "question_numbers": arr(POS)}), minItems=2
                                    ),
                                }
                            ),
                            minItems=2,
                        ),
                    }
                ),
            ]
        },
        "source_reference": SOURCE,
        "questions": arr(QUESTION),
    }
)
PART = obj(
    {
        "part_number": {"type": "integer", "minimum": 1, "maximum": 4},
        "question_range": RANGE,
        "display_order": INTEGER,
        "instructions": arr(S),
        "source_reference": SOURCE,
        "supporting_assets": arr(S),
        "audio_mapping_key": obj(
            {
                "book": INTEGER,
                "printed_test_number": INTEGER,
                "local_ordinal": INTEGER,
                "part_number": INTEGER,
            }
        ),
        "groups": arr(GROUP, minItems=1),
    }
)
# Optional for existing immutable attempt snapshots. New imports carry the
# reviewed canonical materials; alternatives remain public, content-addressed IDs.
PART["properties"]["visual_materials"] = arr(
    obj(
        {
            "asset_id": S,
            "question_range": RANGE,
            "display_order": INTEGER,
            "asset_role": {"enum": ["source_page", "task_image"]},
            "alternative_asset_ids": arr(S, uniqueItems=True),
        }
    )
)
VALIDATION = obj(
    {
        "parsed_questions": INTEGER,
        "interactive_questions": INTEGER,
        "source_verified_questions": INTEGER,
        "keys_present": INTEGER,
        "key_verified_positions": INTEGER,
        "missing_positions": arr(POS),
        "blocked_positions": arr(POS),
        "complete_question_content": B,
        "complete_verified_keys": B,
        "ready_for_stage2": B,
    }
)
EXAM = obj(
    {
        "schema_version": S,
        "exam_id": S,
        "book": {"type": "integer", "minimum": 4, "maximum": 21},
        "printed_test_number": INTEGER,
        "local_ordinal": {"type": "integer", "minimum": 1, "maximum": 4},
        "module": {"const": "listening"},
        "parts": arr(PART, minItems=4, maxItems=4),
        "assets": arr(ASSET),
        "validation": VALIDATION,
    }
)
KEY_ENTRY = obj(
    {
        "question_id": S,
        "question_number": POS,
        "official_answer": S,
        "source_notation": S,
        "explicit_slash_forms": arr(S),
        "parenthetical_notation_requires_source_interpretation": B,
        "unordered_group": NULL_S,
        "source_reference": obj({"file": S, "line": INTEGER, "evidence_assets": arr(S)}),
        "verification": VERIFICATION,
    }
)
KEY = obj(
    {
        "exam_id": S,
        "visibility": {"const": "private"},
        "answers": arr(KEY_ENTRY, maxItems=40),
        "unordered_groups": arr(
            obj(
                {
                    "group_id": S,
                    "question_numbers": arr(POS, minItems=2, uniqueItems=True),
                    "expected_units": arr(S, minItems=2, uniqueItems=True),
                    "order": {"const": "unordered"},
                    "distinct": {"const": True},
                    "evidence": S,
                }
            )
        ),
        "source_header": S,
        "unordered_evidence": arr(
            obj({"question_numbers": arr(POS, minItems=2), "source_line": INTEGER, "text": S})
        ),
        "within_position_rules": arr(
            obj(
                {
                    "question_number": POS,
                    "question_id": S,
                    "kind": {"const": "all_components_required"},
                    "order": {"const": "unordered"},
                    "marks": {"const": 1},
                    "components": arr(
                        obj({"explicit_slash_forms": arr(S, minItems=1)}), minItems=2
                    ),
                    "source_notation": S,
                }
            )
        ),
    }
)


def write(output: Path):
    directory = output / "schemas"
    directory.mkdir(parents=True, exist_ok=True)
    for name, schema in [
        ("listening_exam.schema.json", EXAM),
        ("listening_private_key.schema.json", KEY),
    ]:
        schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", **schema}
        (directory / name).write_text(
            json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
