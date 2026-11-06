"""Permanent regressions against real imported Cambridge material (no fixtures).
Run: python -m unittest discover -s backend/scripts/listening_dataset -p 'test_*.py'
"""

import copy
import json
import unittest

from importer import (
    DEFAULT_OUTPUT,
    HERE,
    KEY_PAGES,
    constraints,
    marker_spans,
    split_tests,
    supplemental_keys,
)
from jsonschema import Draft202012Validator
from schema import EXAM
from validator import validate


def exam(book, test):
    return json.loads(
        (DEFAULT_OUTPUT / "exams" / f"cambridge-{book:02}-test-{test:02}.json").read_text()
    )


def groups(document):
    return [group for part in document["parts"] for group in part["groups"]]


class ListeningContract(unittest.TestCase):
    def test_all_books_and_assets_pass_technical_gate(self):
        result = validate(DEFAULT_OUTPUT)
        self.assertEqual(result["errors"], [])
        self.assertFalse(result["stage1_all_ready"])
        self.assertFalse(result["audio_checked"])
        self.assertEqual(result["totals"]["parsed_questions"], 2880)

    def test_cambridge12_printed_tests_and_future_audio_identity(self):
        for ordinal, printed in enumerate(range(5, 9), 1):
            d = exam(12, printed)
            self.assertEqual(d["local_ordinal"], ordinal)
            self.assertEqual(d["printed_test_number"], printed)
            self.assertEqual(
                [p["audio_mapping_key"]["part_number"] for p in d["parts"]], [1, 2, 3, 4]
            )
            self.assertFalse(any("audio_path" in p for p in d["parts"]))

    def test_multiple_choice_contains_original_option_text(self):
        g = next(g for g in groups(exam(14, 1)) if g["question_range"] == [21, 25])
        self.assertEqual(len(g["questions"][0]["options"]), 3)
        self.assertEqual(
            g["questions"][0]["options"][0]["text"], "contain nearly half the world's population."
        )

    def test_matching_shared_bank_is_not_repeated_as_empty_buttons(self):
        g = next(g for g in groups(exam(12, 5)) if g["question_range"] == [17, 20])
        self.assertEqual(
            [o["text"] for o in g["answer_bank"]["options"]],
            [
                "training courses",
                "food stocks",
                "first aid",
                "breakages",
                "staff discounts",
                "timetables",
            ],
        )
        self.assertTrue(
            all(q["answer_bank_id"] == g["answer_bank"]["bank_id"] for q in g["questions"])
        )

    def test_choose_two_preserves_two_slots_and_unordered_units(self):
        d = exam(20, 4)
        g = next(g for g in groups(d) if g["question_range"] == [11, 12])
        self.assertEqual([q["question_number"] for q in g["questions"]], [11, 12])
        self.assertEqual(g["selection"]["order"], "unordered")
        key = json.loads((DEFAULT_OUTPUT / "keys" / f"{d['exam_id']}.json").read_text())
        kg = next(g for g in key["unordered_groups"] if g["question_numbers"] == [11, 12])
        self.assertEqual(set(kg["expected_units"]), {"B", "C"})

    def test_single_number_can_require_two_choices(self):
        g = next(g for g in groups(exam(4, 3)) if g["question_range"] == [40, 40])
        self.assertEqual(len(g["questions"]), 1)
        self.assertEqual(g["questions"][0]["input_type"], "multi_select")
        self.assertEqual(g["questions"][0]["constraints"]["required_choices"], 2)
        self.assertEqual(len(g["answer_bank"]["options"]), 5)

    def test_text_completion_preserves_unordered_word_slots(self):
        key = json.loads((DEFAULT_OUTPUT / "keys/cambridge-06-test-01.json").read_text())
        pair = next(g for g in key["unordered_groups"] if g["question_numbers"] == [26, 27])
        self.assertEqual(set(pair["expected_units"]), {"laptops", "printers"})
        questions = [q for g in groups(exam(6, 1)) for q in g["questions"]]
        self.assertEqual(len([q for q in questions if q["question_number"] in (26, 27)]), 2)

    def test_two_components_inside_one_position_are_not_split(self):
        key = json.loads((DEFAULT_OUTPUT / "keys/cambridge-09-test-01.json").read_text())
        rule = next(r for r in key["within_position_rules"] if r["question_number"] == 33)
        self.assertEqual(rule["marks"], 1)
        self.assertEqual(
            rule["components"],
            [
                {"explicit_slash_forms": ["plants"]},
                {"explicit_slash_forms": ["animals", "fish", "fishes"]},
            ],
        )

    def test_word_bank_has_original_words_and_no_invented_letters(self):
        g = next(g for g in groups(exam(4, 2)) if g["question_range"] == [6, 8])
        self.assertEqual(
            [o["label"] for o in g["answer_bank"]["options"]],
            ["Art Gallery", "Cathedral", "Castle", "Gardens", "Markets"],
        )
        self.assertTrue(all(q["input_type"] == "select" for q in g["questions"]))

    def test_inline_flowchart_bank_preserves_all_eight_columns(self):
        g = next(g for g in groups(exam(13, 1)) if g["question_range"] == [26, 30])
        self.assertEqual(g["question_type"], "flow_chart_completion")
        self.assertEqual(
            [o["text"] for o in g["answer_bank"]["options"]],
            ["container", "soil", "weight", "condition", "height", "colour", "types", "depths"],
        )
        self.assertTrue(all(q["input_type"] == "select" for q in g["questions"]))

    def test_missing_option_in_txt_is_recovered_only_from_pdf(self):
        g = next(g for g in groups(exam(16, 2)) if g["question_range"] == [11, 15])
        q = g["questions"][0]
        self.assertEqual([o["label"] for o in q["options"]], ["A", "B", "C"])
        self.assertEqual(q["options"][1]["text"], "a private home.")
        self.assertEqual(q["verification"]["pdf_pages"], [35])

    def test_diagram_has_three_verified_spatial_anchors(self):
        g = next(g for g in groups(exam(9, 4)) if g["question_range"] == [11, 13])
        self.assertEqual(g["presentation_mode"], "image_backed")
        self.assertEqual(
            [q["blank_references"][0]["pdf_page"] for q in g["questions"]], [86, 86, 86]
        )
        self.assertTrue(g["supporting_assets"])

    def test_plan_has_actual_visual_options(self):
        d = exam(14, 2)
        g = next(g for g in groups(d) if g["question_type"] == "plan_labelling")
        self.assertTrue(g["supporting_assets"])
        self.assertTrue(
            all(o["text"] or o.get("visual_reference") for o in g["answer_bank"]["options"])
        )

    def test_table_form_flowchart_and_numeric_limits(self):
        self.assertIn("form_completion", [g["question_type"] for g in groups(exam(14, 1))])
        self.assertIn("table_completion", [g["question_type"] for g in groups(exam(21, 1))])
        flow = next(g for g in groups(exam(16, 2)) if g["question_type"] == "flow_chart_completion")
        self.assertEqual([q["question_number"] for q in flow["questions"]], list(range(25, 31)))
        self.assertTrue(all(q["renderable"] for q in flow["questions"]))
        self.assertEqual(
            constraints("Write NO MORE THAN TWO NUMBERS for each answer.")["max_numbers"], 2
        )

    def test_recovered04_keys_are_complete_but_not_falsely_verified(self):
        for t in range(1, 5):
            key = json.loads(
                (DEFAULT_OUTPUT / "keys" / f"cambridge-04-test-{t:02}.json").read_text()
            )
            self.assertEqual([a["question_number"] for a in key["answers"]], list(range(1, 41)))
            self.assertTrue(
                all(a["verification"]["status"] == "needs_review" for a in key["answers"])
            )
            self.assertTrue(
                all(
                    "sources/answer_keys_04_18.txt" in a["source_reference"]["file"]
                    for a in key["answers"]
                )
            )
        d = exam(4, 1)
        self.assertEqual(d["validation"]["missing_positions"], [])
        q = next(q for g in groups(d) for q in g["questions"] if q["question_number"] == 34)
        self.assertEqual(q["blank_references"][0]["pdf_page"], 12)
        self.assertTrue(q["renderable"])

    def test_compilation_coverage_and_cambridge12_mapping(self):
        keys = supplemental_keys(HERE / "sources/answer_keys_04_18.txt")
        self.assertEqual(len(keys), 60)
        self.assertEqual(sum(map(len, keys.values())), 2400)
        self.assertIn("cambridge-12-test-05", keys)
        self.assertNotIn("cambridge-12-test-01", keys)

    def test_single_position_two_required_keys_are_composite_not_unordered_slots(self):
        key = json.loads((DEFAULT_OUTPUT / "keys/cambridge-04-test-03.json").read_text())
        self.assertTrue(all(len(g["question_numbers"]) > 1 for g in key["unordered_groups"]))
        self.assertEqual({r["question_number"] for r in key["within_position_rules"]}, {38, 40})

    def test_19_and_21_keys_have_original_private_evidence(self):
        for book in (19, 21):
            for test in range(1, 5):
                d = exam(book, test)
                self.assertEqual(d["validation"]["key_verified_positions"], 40)
                self.assertEqual(d["validation"]["interactive_questions"], 40)
                # The key review does not promote the unreviewed question pages.
                self.assertEqual(d["validation"]["ready_for_stage2"], test == 1)

    def test_09_and_20_original_key_images_are_private_and_verified(self):
        for b in [9, 20]:
            for t in range(1, 5):
                d = exam(b, t)
                self.assertEqual(d["validation"]["key_verified_positions"], 40)
                self.assertFalse(any("private/" in a["relative_path"] for a in d["assets"]))

    def test_private_key_page_references_do_not_become_task_sources(self):
        for path in (DEFAULT_OUTPUT / "exams").glob("*.json"):
            d = json.loads(path.read_text())
            private_pages = set(KEY_PAGES.get(d["book"], []))
            for part in d["parts"]:
                self.assertFalse(set(part["source_reference"]["pdf_pages"]) & private_pages)

    def test_damaged_original_not_promoted_to_ready(self):
        d = exam(14, 3)
        self.assertEqual(d["validation"]["blocked_positions"], [])
        self.assertEqual(d["validation"]["interactive_questions"], 40)
        self.assertTrue(
            all(
                q["verification"]["status"] == "needs_review"
                for q in d["parts"][0]["groups"][0]["questions"]
            )
        )
        self.assertFalse(d["validation"]["ready_for_stage2"])

    def test_closed_public_schema_rejects_answer_injection(self):
        d = copy.deepcopy(exam(14, 1))
        d["parts"][0]["groups"][0]["questions"][0]["official_answer"] = "leak"
        self.assertTrue(list(Draft202012Validator(EXAM).iter_errors(d)))

    def test_duplicate_wrappers_do_not_create_extra_parts(self):
        text = (
            "TEST 1\nSECTION 1 — AUDIO PART 1\nfirst\nSECTION 1 — AUDIO PART 1\n"
            "second\nSECTION 2 — AUDIO PART 2\nthird"
        )
        parsed = split_tests(text)
        self.assertEqual(sorted(parsed), [1])
        self.assertEqual(sorted(parsed[1]), [1, 2])
        self.assertTrue(any(line == "second" for _, line in parsed[1][1]))

    def test_bracketed_and_postfixed_blanks_are_bound_without_inference(self):
        parsed = marker_spans([(1, "cost 7 £[____]; then ........(8) were invited")], 7, 8, "text")
        self.assertEqual(set(parsed), {7, 8})


if __name__ == "__main__":
    unittest.main()
