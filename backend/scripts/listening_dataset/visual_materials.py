"""Apply reviewed, content-addressed visual choices; no filename/OCR inference.

The registry is editorial input like source_reviews.json. Unknown image bytes fail
closed during import, rather than silently inheriting a filename's Test/Part.
All original public bytes and exam asset allowlists remain available to snapshots.
"""

import json
from functools import lru_cache
from pathlib import Path

REGISTRY = Path(__file__).resolve().parents[3] / "web/src/features/listening/visual-materials.json"


@lru_cache(maxsize=1)
def load_registry():
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def overlaps(left, right):
    return left[0] <= right[1] and right[0] <= left[1]


def apply_visual_materials(exam, registry=None):
    registry = registry or load_registry()
    allowed = {a["asset_id"] for a in exam["assets"]}
    for part in exam["parts"]:
        key = f"{exam['exam_id']}-p{part['part_number']}"
        policy = registry["parts"][key]
        materials = policy["materials"]
        fidelity = policy.get("source_fidelity", {})
        if (
            fidelity.get("update_source_reference")
            and fidelity.get("pdf_pages")
            and "source_reference" in part
        ):
            part["source_reference"]["pdf_pages"] = fidelity["pdf_pages"]
            part["source_reference"]["pdf_page_basis"] = (
                "source_fidelity_v2_original_pdf_boundaries"
            )
        covered = {a for m in materials for a in [m["asset_id"], *m["alternative_asset_ids"]]}
        excluded = set(policy.get("excluded_asset_ids", []))
        actual = set(part["supporting_assets"])
        if not actual <= covered | excluded or not covered <= allowed:
            raise ValueError(f"Unreviewed/missing visual material: {key}")
        part["visual_materials"] = [dict(m) for m in materials]
        part["supporting_assets"] = [m["asset_id"] for m in materials]
        for group in part["groups"]:
            selected = [
                m["asset_id"]
                for m in materials
                if overlaps(m["question_range"], group["question_range"])
            ]
            if group["presentation_mode"] == "image_backed" and not selected:
                raise ValueError(f"Image-backed group lost material: {group['group_id']}")
            group["supporting_assets"] = selected
            # Keep source text/answer fields in place; replace only image bindings.
            blocks = []
            inserted = False
            for block in group["content_blocks"]:
                if block["kind"] != "original_source_image":
                    blocks.append(block)
                elif not inserted:
                    blocks.extend(
                        {"kind": "original_source_image", "asset_id": a} for a in selected
                    )
                    inserted = True
            group["content_blocks"] = blocks
            for question in group["questions"]:
                if question.get("visual_binding"):
                    question["visual_binding"]["asset_ids"] = selected
    return exam


def reviewed_associations(asset_id, book, registry=None):
    """Return reviewed ownership, independently of misleading input filenames."""
    registry = registry or load_registry()
    found = []
    for key, policy in registry["parts"].items():
        exam_id, part = key.rsplit("-p", 1)
        if int(exam_id.split("-")[1]) != book:
            continue
        if any(
            asset_id in [m["asset_id"], *m["alternative_asset_ids"]] for m in policy["materials"]
        ):
            found.append((int(exam_id.split("-")[-1]), int(part)))
    return found


def apply_existing(root):
    """Metadata-only update; retain question text, key documents and image bytes."""
    import hashlib
    import shutil

    from schema import write as write_schemas

    def dump(path, value):
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    registry = load_registry()
    # Deployment validation uses the packaged input, not a frontend checkout.
    shutil.copyfile(REGISTRY, root / "qa/visual_materials.json")
    for path in sorted((root / "exams").glob("*.json")):
        exam = json.loads(path.read_text())
        dump(path, apply_visual_materials(exam, registry))
    assets_path = root / "qa/assets.json"
    assets = json.loads(assets_path.read_text())
    for asset in assets["assets"]:
        ownership = reviewed_associations(
            asset["asset_id"], asset["associations"][0]["book"], registry
        )
        if ownership:
            # Page identity remains provenance; filename-derived ownership does not.
            book = asset["associations"][0]["book"]
            valid = [
                a
                for a in asset["associations"]
                if (a["printed_test_number"], a["part_number"]) in ownership
                or a["printed_test_number"] is None
                or a["part_number"] is None
            ]
            pages = list(dict.fromkeys(a["pdf_page"] for a in valid or asset["associations"]))
            asset["associations"] = [
                {"book": book, "printed_test_number": test, "part_number": part, "pdf_page": page}
                for test, part in ownership
                for page in pages
            ]
        asset["associations"].sort(key=lambda a: json.dumps(a, sort_keys=True))
    dump(assets_path, assets)
    write_schemas(root)
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["generator_sha256"] = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(Path(__file__).parent.glob("*"))
        if p.suffix in (".py", ".json")
    }
    manifest["schema_sha256"] = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((root / "schemas").glob("*.json"))
    }
    manifest["visual_materials_sha256"] = hashlib.sha256(REGISTRY.read_bytes()).hexdigest()
    dump(manifest_path, manifest)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", type=Path, required=True, help="Local listening_v1 root")
    apply_existing(parser.parse_args().apply)
