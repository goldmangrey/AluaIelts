"""Read-only editorial source enrichment for semantically identical snapshots.

Never changes questions, stored snapshots, keys, result/answer formats or ownership.
Only content-addressed public images explicitly canonical for this same exam enter
an existing attempt's source projection; unrelated exams/images remain forbidden.
"""

import copy

VISUAL_KEYS = {
    "supporting_assets",
    "visual_materials",
    "source_reference",
    "visual_binding",
    "asset_ids",
}


def semantic_source(value):
    if isinstance(value, dict):
        return {key: semantic_source(item) for key, item in value.items() if key not in VISUAL_KEYS}
    if isinstance(value, list):
        return [
            semantic_source(item)
            for item in value
            if not isinstance(item, dict) or item.get("kind") != "original_source_image"
        ]
    return value


def enrich_sources(snapshot, current):
    if current is None or snapshot.get("exam_id") != current.get("exam_id"):
        return snapshot
    if semantic_source(snapshot["parts"]) != semantic_source(current["parts"]):
        return snapshot
    out = copy.deepcopy(snapshot)
    allowed = {a["asset_id"]: a for a in out["assets"]}
    current_assets = {a["asset_id"]: a for a in current["assets"]}
    for old, fresh in zip(out["parts"], current["parts"], strict=True):
        materials = fresh.get("visual_materials")
        if materials is None:
            continue
        old["visual_materials"] = copy.deepcopy(materials)
        old["supporting_assets"] = [m["asset_id"] for m in materials]
        for material in materials:
            aid = material["asset_id"]
            record = current_assets.get(aid)
            if record and record["relative_path"].startswith("assets/public/"):
                allowed[aid] = copy.deepcopy(record)
        for group, new_group in zip(old["groups"], fresh["groups"], strict=True):
            group["supporting_assets"] = list(new_group["supporting_assets"])
            # Retain old lines/answer fields; only source-image references are projected.
            blocks = [b for b in group["content_blocks"] if b["kind"] != "original_source_image"]
            group["content_blocks"] = blocks + [
                copy.deepcopy(b)
                for b in new_group["content_blocks"]
                if b["kind"] == "original_source_image"
            ]
            for q, new_q in zip(group["questions"], new_group["questions"], strict=True):
                if "visual_binding" in new_q:
                    q["visual_binding"] = copy.deepcopy(new_q["visual_binding"])
    out["assets"] = [allowed[aid] for aid in sorted(allowed)]
    return out
