"""Small, hash-pinned Stage 2 crop recipes. Original PDF pixels only; no OCR/AI.

Used by the importer and targeted local repair/check command. The renderer
version is pinned in requirements.txt. Original assets remain alternatives.
"""

import hashlib
import io
import json
import math
from pathlib import Path

import fitz
from PIL import Image, ImageOps

RECIPES = Path(__file__).with_suffix(".json")


def load_repairs():
    return json.loads(RECIPES.read_text())["repairs"]


def render_crop(recipe, pdf_path=None, source_path=None):
    x0, y0, x1, y1 = recipe["clip_normalized"]
    if recipe.get("source_kind") == "asset":
        if (
            hashlib.sha256(Path(source_path).read_bytes()).hexdigest()
            != recipe["source_asset_id"][6:]
        ):
            raise ValueError(f"Unreviewed full-page pixels for {recipe['finding_id']}")
        with Image.open(source_path) as original:
            width, height = original.size
            image = original.convert("RGB").crop(
                (
                    math.floor(x0 * width),
                    math.floor(y0 * height),
                    math.ceil(x1 * width),
                    math.ceil(y1 * height),
                )
            )
    else:
        digest = hashlib.sha256(Path(pdf_path).read_bytes()).hexdigest()
        if digest != recipe["source_pdf_sha256"]:
            raise ValueError(f"Unreviewed PDF for {recipe['finding_id']}")
        with fitz.open(pdf_path) as document:
            page = document[recipe["pdf_page"] - 1]
            clip = fitz.Rect(
                x0 * page.rect.width,
                y0 * page.rect.height,
                x1 * page.rect.width,
                y1 * page.rect.height,
            )
            pixmap = page.get_pixmap(dpi=recipe["dpi"], clip=clip, alpha=False)
            image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
    image = ImageOps.expand(image, border=recipe["padding_px"], fill="white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", compress_level=9)
    data = buffer.getvalue()
    expected = recipe.get("new_asset_id")
    if expected and "asset-" + hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f"Crop bytes changed for {recipe['finding_id']}; review renderer/recipe")
    return data


def add_repaired_assets(assets, pdf_path, book):
    """Register derived crops before exam public allowlists are assembled."""
    import tempfile

    selected = [r for r in load_repairs() if r["book"] == book]
    if not selected:
        return []
    ids = []
    with tempfile.TemporaryDirectory(prefix="alua-reviewed-crops-") as directory:
        for recipe in selected:
            if recipe["source_asset_id"] not in assets.records:
                raise ValueError(f"Missing reviewed source page: {recipe['finding_id']}")
            path = Path(directory) / f"{recipe['finding_id']}.png"
            source = assets.output / assets.records[recipe["source_asset_id"]]["relative_path"]
            path.write_bytes(render_crop(recipe, pdf_path, source))
            aid = assets.add(
                path, book, "task_image", recipe["test"], recipe["part"], recipe["pdf_page"]
            )
            assets.records[aid]["sources"] = [f"derived/image_repairs/{recipe['finding_id']}.png"]
            assets.records[aid]["recovery"] = dict(
                recipe, method="reviewed original pixel region + white padding; no OCR/AI"
            )
            ids.append(aid)
    return ids
