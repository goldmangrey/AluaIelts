"""Targeted image repair regressions; no backend, import or network."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from image_repairs import load_repairs, render_crop
from importer import DEFAULT_OUTPUT, ROOT
from PIL import Image
from repair_images import check
from visual_materials import load_registry


class ImageRepairTest(unittest.TestCase):
    def test_all_approved_bytes_bindings_and_full_page_fallbacks(self):
        self.assertEqual(check(DEFAULT_OUTPUT)["new_assets"], 45)
        recipes = {r["finding_id"]: r for r in load_repairs()}
        self.assertNotIn("C014", recipes)  # Original instruction is not fully verifiable.
        self.assertNotIn("C028", recipes)  # Uncertain edge; retain complete original.
        registry = load_registry()["parts"]
        self.assertEqual(
            registry["cambridge-07-test-04-p1"]["materials"][0]["asset_role"], "source_page"
        )
        self.assertEqual(
            registry["cambridge-06-test-03-p3"]["materials"][-1]["asset_role"], "source_page"
        )

    def test_original_source_pixels_not_reconstructed_or_rescaled(self):
        recipe = next(r for r in load_repairs() if r["finding_id"] == "C020")
        records = {
            r["asset_id"]: r
            for r in json.loads((DEFAULT_OUTPUT / "qa/assets.json").read_text())["assets"]
        }
        source = DEFAULT_OUTPUT / records[recipe["source_asset_id"]]["relative_path"]
        data = render_crop(recipe, source_path=source)
        self.assertEqual("asset-" + hashlib.sha256(data).hexdigest(), recipe["new_asset_id"])
        with (
            Image.open(source) as full,
            Image.open(DEFAULT_OUTPUT / records[recipe["new_asset_id"]]["relative_path"]) as crop,
        ):
            pad = recipe["padding_px"]
            self.assertEqual(
                crop.crop((pad, pad, pad + full.width, pad + 100)).tobytes(),
                full.convert("RGB").crop((0, 0, full.width, 100)).tobytes(),
            )

    def test_pdf_render_is_reproducible_and_rejects_wrong_source(self):
        recipe = next(r for r in load_repairs() if r["finding_id"] == "C003")
        pdf = ROOT / "ieltsbooks/Cambridge-IELTS-21.pdf"
        if not pdf.exists():
            self.skipTest("Pinned local Cambridge PDF not available")
        self.assertEqual(
            "asset-" + hashlib.sha256(render_crop(recipe, pdf)).hexdigest(), recipe["new_asset_id"]
        )
        with tempfile.TemporaryDirectory() as directory:
            wrong = Path(directory) / "wrong.pdf"
            wrong.write_bytes(b"not the reviewed PDF")
            with self.assertRaisesRegex(ValueError, "Unreviewed PDF"):
                render_crop(recipe, wrong)


if __name__ == "__main__":
    unittest.main()
