"""Apply/check only the reviewed Stage 2 image repairs; never import questions/keys.

python repair_images.py [--apply] [--pdf-root PATH]
Existing PDFs must match pinned hashes. Original image files are never overwritten.
"""

import argparse
import copy
import hashlib
import json
from pathlib import Path

from image_repairs import add_repaired_assets, load_repairs
from importer import DEFAULT_OUTPUT, ROOT, Assets
from PIL import Image
from visual_materials import REGISTRY, apply_visual_materials


def read(path):
    return json.loads(path.read_text())


def dump_changed(path, value):
    data = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
    if not path.exists() or path.read_bytes() != data:
        path.write_bytes(data)


def apply(root, pdf_root):
    recipes = load_repairs()
    registry = read(REGISTRY)
    assets = Assets(root, root)
    old = read(root / "qa/assets.json")
    assets.records = {r["asset_id"]: r for r in old["assets"]}
    for book in sorted({r["book"] for r in recipes}):
        add_repaired_assets(assets, pdf_root / f"Cambridge-IELTS-{book:02}.pdf", book)
    touched = set()
    for r in recipes:
        policy = registry["parts"][f"{r['exam_id']}-p{r['part']}"]
        material = next(
            m
            for m in policy["materials"]
            if r["source_asset_id"] in [m["asset_id"], *m["alternative_asset_ids"]]
        )
        assert material["question_range"] == r["question_range"]
        if material["asset_id"] != r["new_asset_id"]:
            assert material["asset_id"] == r["source_asset_id"]
            material["alternative_asset_ids"] = [
                material["asset_id"],
                *material["alternative_asset_ids"],
            ]
            material["asset_id"] = r["new_asset_id"]
            material["asset_role"] = "task_image"
        touched.add(r["exam_id"])
    dump_changed(REGISTRY, registry)
    dump_changed(root / "qa/visual_materials.json", registry)
    for exam_id in sorted(touched):
        path = root / "exams" / f"{exam_id}.json"
        exam = read(path)
        original = copy.deepcopy(exam)
        allowlist = {a["asset_id"]: a for a in exam["assets"]}
        for r in recipes:
            if r["exam_id"] == exam_id:
                allowlist[r["new_asset_id"]] = assets.public_record(r["new_asset_id"])
        exam["assets"] = [allowlist[k] for k in sorted(allowlist)]
        apply_visual_materials(exam, registry)

        # Question content/answers are outside this operation. Only image bindings
        # can change. Check this before writing, including all untouched Parts.
        def strip_visuals(document):
            result = copy.deepcopy(document)
            result.pop("assets")
            for part in result["parts"]:
                part.pop("visual_materials", None)
                part.pop("supporting_assets")
                for group in part["groups"]:
                    group.pop("supporting_assets")
                    group["content_blocks"] = [
                        b for b in group["content_blocks"] if b["kind"] != "original_source_image"
                    ]
                    for q in group["questions"]:
                        q.pop("visual_binding", None)
            return result

        assert strip_visuals(exam) == strip_visuals(original), exam_id
        dump_changed(path, exam)
    dump_changed(
        root / "qa/assets.json", {"assets": [assets.records[k] for k in sorted(assets.records)]}
    )
    manifest = read(root / "manifest.json")
    manifest["visual_materials_sha256"] = hashlib.sha256(REGISTRY.read_bytes()).hexdigest()
    manifest["generator_sha256"] = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(Path(__file__).parent.iterdir())
        if p.suffix in (".py", ".json")
    }
    dump_changed(root / "manifest.json", manifest)
    return len(touched)


def check(root):
    recipes = load_repairs()
    registry = read(REGISTRY)
    assert read(root / "qa/visual_materials.json") == registry
    records = {r["asset_id"]: r for r in read(root / "qa/assets.json")["assets"]}
    ids = set()
    for r in recipes:
        aid = r["new_asset_id"]
        assert aid not in ids
        ids.add(aid)
        asset = records[aid]
        path = root / asset["relative_path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == aid[6:] == asset["sha256"]
        with Image.open(path) as image:
            image.load()
            assert image.size == (asset["width"], asset["height"])
            assert min(image.size) > 500
            padding = r["padding_px"]
            assert image.crop((0, 0, image.width, padding)).getextrema() == ((255, 255),) * 3
            assert (
                image.crop((0, image.height - padding, image.width, image.height)).getextrema()
                == ((255, 255),) * 3
            )
        exam = read(root / "exams" / f"{r['exam_id']}.json")
        assert apply_visual_materials(copy.deepcopy(exam), registry) == exam
        part = exam["parts"][r["part"] - 1]
        material = next(m for m in part["visual_materials"] if m["asset_id"] == aid)
        assert material["alternative_asset_ids"][0] == r["source_asset_id"]
        assert r["old_asset_id"] in material["alternative_asset_ids"]
        assert material["question_range"] == r["question_range"]
        allowed = {a["asset_id"] for a in exam["assets"]}
        assert {aid, r["old_asset_id"], r["source_asset_id"]} <= allowed
        for original in [r["old_asset_id"], r["source_asset_id"]]:
            assert (root / records[original]["relative_path"]).exists()
    manifest = read(root / "manifest.json")
    assert manifest["visual_materials_sha256"] == hashlib.sha256(REGISTRY.read_bytes()).hexdigest()
    assert all(
        manifest["generator_sha256"][p.name] == hashlib.sha256(p.read_bytes()).hexdigest()
        for p in Path(__file__).parent.iterdir()
        if p.suffix in (".py", ".json")
    )
    return {
        "new_assets": len(ids),
        "affected_exams": len({r["exam_id"] for r in recipes}),
        "affected_parts": len(recipes),
        "hash_decode_dimensions_padding": "PASS",
        "registry_allowlists_fallbacks_idempotency": "PASS",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--pdf-root", type=Path, default=ROOT / "ieltsbooks")
    args = parser.parse_args()
    if args.apply:
        apply(args.root, args.pdf_root)
    print(json.dumps(check(args.root), indent=2))
