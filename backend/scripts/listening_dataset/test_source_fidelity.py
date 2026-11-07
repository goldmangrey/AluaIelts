"""Original page recipes and metadata replay; no import, answers or network."""

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from image_repairs import render_crop
from importer import DEFAULT_OUTPUT, ROOT, Assets
from source_fidelity import RECIPES, add_source_fidelity_assets
from visual_materials import apply_visual_materials


class SourceFidelityTest(unittest.TestCase):
    def test_clean_c014_source_is_pinned_and_old_damaged_source_is_only_alternative(self):
        record = next(
            r
            for r in json.loads(
                (ROOT / "backend/scripts/listening_dataset/source_reviews.json").read_text()
            )["recovered_assets"]
            if r.get("render_recipe", {}).get("finding_id") == "C014-final-original"
        )
        recipe = record["render_recipe"]
        aid = recipe["new_asset_id"]
        self.assertEqual(hashlib.sha256((ROOT / record["file"]).read_bytes()).hexdigest(), aid[6:])
        part = json.loads((DEFAULT_OUTPUT / "exams/cambridge-07-test-04.json").read_text())[
            "parts"
        ][0]
        self.assertEqual(part["visual_materials"][0]["asset_id"], aid)
        self.assertIn(
            "asset-2d699765d75235aa6ec60a141a5011ed1349bffb7c57443faf06b55459a2f7ec",
            part["visual_materials"][0]["alternative_asset_ids"],
        )
        original = Path("/tmp/alua-final-source-release/c07.pdf")
        if original.exists():
            self.assertEqual(render_crop(recipe, original), (ROOT / record["file"]).read_bytes())

    def test_all_original_pages_regenerate_with_same_ids_and_pixels(self):
        recipes = json.loads(RECIPES.read_text())["new_pages"]
        records = {
            a["asset_id"]: a
            for a in json.loads((DEFAULT_OUTPUT / "qa/assets.json").read_text())["assets"]
        }
        self.assertEqual(len(recipes), 36)
        with tempfile.TemporaryDirectory() as directory:
            assets = Assets(DEFAULT_OUTPUT, Path(directory))
            ids = []
            for book in sorted({r["book"] for r in recipes}):
                pdf = ROOT / f"ieltsbooks/Cambridge-IELTS-{book:02}.pdf"
                ids.extend(add_source_fidelity_assets(assets, pdf, book))
            self.assertEqual(set(ids), {r["new_asset_id"] for r in recipes})
            for recipe in recipes:
                aid = recipe["new_asset_id"]
                old = DEFAULT_OUTPUT / records[aid]["relative_path"]
                regenerated = Path(directory) / assets.records[aid]["relative_path"]
                self.assertEqual(regenerated.read_bytes(), old.read_bytes())
                self.assertEqual(hashlib.sha256(old.read_bytes()).hexdigest(), aid[6:])
                self.assertIn("source_page", assets.records[aid]["roles"])

    def test_wrong_pdf_is_rejected_before_rendering(self):
        recipe = json.loads(RECIPES.read_text())["new_pages"][0]
        with tempfile.TemporaryDirectory() as directory:
            wrong = Path(directory) / "wrong.pdf"
            wrong.write_bytes(b"unverified source")
            with self.assertRaisesRegex(ValueError, "Unreviewed PDF"):
                render_crop(recipe, wrong)

    def test_all_72_metadata_projections_are_idempotent(self):
        exams = list((DEFAULT_OUTPUT / "exams").glob("*.json"))
        self.assertEqual(len(exams), 72)
        for file in exams:
            document = json.loads(file.read_text())
            self.assertEqual(apply_visual_materials(copy.deepcopy(document)), document, file.name)


if __name__ == "__main__":
    unittest.main()
