"""Hash-pinned missing original pages; no generated/OCR replacement text.

Recipes are reused by normal import and the targeted existing-dataset updater.
Full pages deliberately retain instructions and continuations. Original assets stay.
"""

import hashlib
import json
import tempfile
from pathlib import Path

from image_repairs import render_crop

RECIPES = Path(__file__).with_suffix(".json")


def add_source_fidelity_assets(assets, pdf_path, book):
    selected = [r for r in json.loads(RECIPES.read_text())["new_pages"] if r["book"] == book]
    ids = []
    with tempfile.TemporaryDirectory(prefix="alua-original-pages-") as directory:
        for recipe in selected:
            path = Path(directory) / (recipe["finding_id"] + ".png")
            path.write_bytes(render_crop(recipe, pdf_path=pdf_path))
            aid = assets.add(
                path, book, "source_page", recipe["test"], recipe["part"], recipe["pdf_page"]
            )
            assert aid == recipe["new_asset_id"]
            assets.records[aid]["sources"] = ["derived/source_fidelity/" + path.name]
            assets.records[aid]["recovery"] = dict(
                recipe, method="Full original PDF page, 250 DPI, white safety margin; no OCR/AI"
            )
            ids.append(aid)
    return ids


def apply_current(root, pdf_root):
    from importer import HERE, ROOT, Assets
    from visual_materials import apply_existing

    source = json.loads((root / "qa/assets.json").read_text())
    assets = Assets(root, root)
    assets.records = {a["asset_id"]: a for a in source["assets"]}
    added = []
    for book in sorted({r["book"] for r in json.loads(RECIPES.read_text())["new_pages"]}):
        added.extend(
            add_source_fidelity_assets(assets, pdf_root / f"Cambridge-IELTS-{book:02}.pdf", book)
        )
    # Verified supplemental pixels are packaged, never whole external books.
    for record in json.loads((HERE / "source_reviews.json").read_text())["recovered_assets"]:
        recipe = record.get("render_recipe")
        if not recipe:
            continue
        aid = assets.add(
            ROOT / record["file"],
            record["book"],
            "source_page",
            record["test"],
            record["part"],
            record["pdf_page"],
        )
        assert aid == recipe["new_asset_id"]
        assets.records[aid]["recovery"] = record
        added.append(aid)
    for file in sorted((root / "exams").glob("*.json")):
        exam = json.loads(file.read_text())
        present = {a["asset_id"] for a in exam["assets"]}
        for aid in added:
            if aid not in present and any(
                a["book"] == exam["book"]
                and a["printed_test_number"] == exam["printed_test_number"]
                for a in assets.records[aid]["associations"]
            ):
                exam["assets"].append(assets.public_record(aid))
        exam["assets"].sort(key=lambda a: a["asset_id"])
        file.write_text(json.dumps(exam, ensure_ascii=False, indent=2) + "\n")
    source["assets"] = [assets.records[aid] for aid in sorted(assets.records)]
    (root / "qa/assets.json").write_text(json.dumps(source, ensure_ascii=False, indent=2) + "\n")
    apply_existing(root)
    assert all(
        hashlib.sha256((root / assets.records[aid]["relative_path"]).read_bytes()).hexdigest()
        == aid[6:]
        for aid in added
    )
    return len(added)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply-current", type=Path, required=True)
    parser.add_argument("--pdf-root", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps({"original_pages_registered": apply_current(args.apply_current, args.pdf_root)})
    )
