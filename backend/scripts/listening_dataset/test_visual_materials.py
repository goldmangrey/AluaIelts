"""Source ownership and unique/shared visual context regressions (offline)."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from importer import DEFAULT_OUTPUT, Assets
from visual_materials import apply_visual_materials, load_registry


def exam(book, test):
    return json.loads(
        (DEFAULT_OUTPUT / "exams" / f"cambridge-{book:02}-test-{test:02}.json").read_text()
    )


class VisualMaterialsTest(unittest.TestCase):
    def test_wrong_filename_cannot_create_part4_ownership(self):
        records = json.loads((DEFAULT_OUTPUT / "qa/assets.json").read_text())["assets"]
        bad_name = next(
            a for a in records if any("Test_2_Part_4_PDF_035" in s for s in a["sources"])
        )
        self.assertEqual({a["part_number"] for a in bad_name["associations"]}, {1})
        with tempfile.TemporaryDirectory() as directory:
            assets = Assets(DEFAULT_OUTPUT, Path(directory))
            aid = assets.add(
                DEFAULT_OUTPUT / bad_name["relative_path"], 18, "source_page", 2, 4, 35
            )
            self.assertEqual({a["part_number"] for a in assets.records[aid]["associations"]}, {1})
        self.assertNotIn(bad_name["asset_id"], exam(18, 2)["parts"][3]["supporting_assets"])
        self.assertIn(bad_name["asset_id"], {a["asset_id"] for a in exam(18, 2)["assets"]})

    def test_split_matching_group_keeps_unique_information_from_both_pages(self):
        part = exam(9, 2)["parts"][1]
        first, second = part["supporting_assets"]
        self.assertEqual(
            [m["question_range"] for m in part["visual_materials"]], [[11, 15], [16, 20]]
        )
        self.assertEqual(
            [g["supporting_assets"] for g in part["groups"]], [[first], [first, second], [second]]
        )

    def test_table_keeps_instruction_page_and_continuation(self):
        part = exam(4, 3)["parts"][3]
        table = next(g for g in part["groups"] if g["question_range"] == [33, 37])
        self.assertEqual(table["supporting_assets"], part["supporting_assets"])
        standalone = next(g for g in part["groups"] if g["question_range"] == [39, 39])
        self.assertEqual(standalone["supporting_assets"], [])
        self.assertTrue(any(b["kind"] == "source_line" for b in standalone["content_blocks"]))

    def test_metadata_application_is_idempotent_and_rejects_unknown_material(self):
        document = exam(19, 3)
        before = copy.deepcopy(document)
        apply_visual_materials(document)
        self.assertEqual(document, before)
        document["parts"][0]["supporting_assets"].append("asset-unreviewed")
        with self.assertRaisesRegex(ValueError, "Unreviewed/missing"):
            apply_visual_materials(document)

    def test_good_complete_crop_is_preferred_without_deleting_original(self):
        preferred = load_registry()["provenance"]["preferred_complete_crops"]
        self.assertEqual(len(preferred), 3)
        for asset in preferred:
            materials = [
                m
                for p in load_registry()["parts"].values()
                for m in p["materials"]
                if m["asset_id"] == asset
            ]
            self.assertEqual(len(materials), 1)
            self.assertTrue(materials[0]["alternative_asset_ids"])


if __name__ == "__main__":
    unittest.main()
