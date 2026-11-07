"""Rebuild the local source contact sheet and structural evidence (no network).

Run the actual resolver/browser checker first. This script checks its output
against the pinned PDFs and editorial decisions; it does not certify new pages
as semantically correct merely because a path or question exists.
"""

import argparse
import hashlib
import html
import json
from collections import Counter
from pathlib import Path

import fitz
from importer import DEFAULT_OUTPUT, ROOT
from PIL import Image
from source_fidelity import RECIPES
from visual_materials import load_registry

OUT = ROOT / "docs/listening-source-fidelity-v2"


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def thumbnail(image, destination):
    if destination.exists():
        return
    image.thumbnail((360, 520))
    image.convert("RGB").save(destination, "WEBP", quality=83)


def build(before=None):
    registry = load_registry()
    recipes = read(RECIPES)
    supplemental = [
        r
        for r in read(RECIPES.with_name("source_reviews.json"))["recovered_assets"]
        if r.get("render_recipe")
    ]
    component = read(OUT / "component-qa.json")
    baseline = {
        f"{r['exam_id']}-p{r['part']}": r for r in read(OUT / "baseline.json")["parts_detail"]
    }
    browser = read(OUT / "browser-qa.json")
    assets = {a["asset_id"]: a for a in read(DEFAULT_OUTPUT / "qa/assets.json")["assets"]}
    exceptions = registry["provenance"]["source_fidelity_v2"]["exceptions"]
    thumb = OUT / "thumbs"
    thumb.mkdir(exist_ok=True)
    documents = {}
    pdf_hashes = {}
    for book in range(4, 22):
        path = ROOT / f"ieltsbooks/Cambridge-IELTS-{book:02}.pdf"
        pdf_hashes[book] = digest(path)
        documents[book] = fitz.open(path)
    rows, cards = [], []
    for row in component["parts_detail"]:
        eid, part, book = row["exam_id"], row["part"], row["book"]
        key = f"{eid}-p{part}"
        policy = registry["parts"][key]
        proof = policy["source_fidelity"]
        assert proof["pdf_sha256"] == pdf_hashes[book]
        expected_pages = proof["pdf_pages"]
        covered_pages, images = [], []
        for segment in row["ordered_source_segments"]:
            if segment["kind"] != "image":
                continue
            aid = segment["assetId"]
            record = assets[aid]
            path = DEFAULT_OUTPUT / record["relative_path"]
            assert digest(path) == record["sha256"] == aid[6:]
            with Image.open(path) as image:
                image.load()
                assert image.size == (record["width"], record["height"])
                thumbnail(image.copy(), thumb / f"{aid}.webp")
            pages = segment["provenance"]["pdfPages"]
            covered_pages.extend(pages)
            images.append(
                f'<figure><img loading="lazy" src="thumbs/{aid}.webp">'
                f"<figcaption>Q{segment['questionRange']} · PDF {pages}<br>"
                f"{aid}<br>{html.escape(proof['images'][aid]['method'])}</figcaption></figure>"
            )
        missing = sorted(set(expected_pages) - set(covered_pages))
        duplicates = [p for p, count in Counter(covered_pages).items() if count > 1]
        inversions = sum(a > b for a, b in zip(covered_pages, covered_pages[1:]))
        range_coverage = {
            n
            for s in row["ordered_source_segments"]
            for n in range(s["questionRange"][0], s["questionRange"][1] + 1)
        }
        missing_groups = [
            g["id"]
            for g in row["groups"]
            if not set(range(g["range"][0], g["range"][1] + 1)) <= range_coverage
        ]
        exception = exceptions.get(key)
        status = (
            ("BLOCKED" if key == "cambridge-07-test-04-p1" else "UNRESOLVED")
            if exception
            else (
                "REPAIRED_VERIFIED"
                if key in recipes["changed_parts"] and key != "cambridge-04-test-02-p2"
                else "VERIFIED"
            )
        )
        if missing or missing_groups or duplicates or inversions or row["missing_assets"]:
            status = "UNRESOLVED"
        cases = [c for c in browser["cases"] if c["exam_id"] == eid and c["part"] == part]
        record = dict(row)
        record.update(
            status=status,
            repaired_original_pages=[
                r
                for r in recipes["new_pages"]
                if r["book"] == book and r["test"] == row["test"] and r["part"] == part
            ],
            before_active_text_loss_states=baseline[key]["baseline_active_only_text_states"],
            pdf={
                "path": f"ieltsbooks/Cambridge-IELTS-{book:02}.pdf",
                "sha256": pdf_hashes[book],
                "pages": expected_pages,
            },
            missing_pdf_pages=missing,
            missing_groups=missing_groups,
            unverified_segments=[
                s["id"] for s in row["ordered_source_segments"] if not s["provenance"]["verified"]
            ],
            duplicate_page_content=duplicates,
            order_inversions=inversions,
            exception=exception,
            browser_cases=len(cases),
            browser_status="PASS"
            if len(cases) == 8 and all(c["status"] == "PASS" for c in cases)
            else "NOT VERIFIED",
            evidence=proof["images"],
        )
        rows.append(record)
        originals = []
        for page in expected_pages:
            name = f"pdf-{book:02}-{page:03}.webp"
            target = thumb / name
            if not target.exists():
                pix = documents[book][page - 1].get_pixmap(
                    matrix=fitz.Matrix(0.7, 0.7), alpha=False
                )
                thumbnail(Image.frombytes("RGB", (pix.width, pix.height), pix.samples), target)
            originals.append(
                f'<figure><a href="../../ieltsbooks/Cambridge-IELTS-{book:02}.pdf#page={page}">'
                f'<img loading="lazy" src="thumbs/{name}"></a><figcaption>Original PDF '
                f"physical page {page}</figcaption></figure>"
            )
        note = exception or "Original page order/bounds compared; see report limitations."
        cards.append(
            f'<section id="{key}"><h2>{key} · {status}</h2>'
            f"<p>Groups: {html.escape(str(row['groups']))}</p>"
            f"<p>{html.escape(note)}</p>"
            f'<h3>Original pages</h3><div class="strip">{"".join(originals)}</div>'
            "<h3>Actual ordered source model</h3>"
            f'<div class="strip">{"".join(images)}</div></section>'
        )
    from app.modules.listening.source_materials import semantic_source

    def semantic_digest(document):
        content = json.dumps(semantic_source(document["parts"]), sort_keys=True).encode()
        return hashlib.sha256(content).hexdigest()

    baseline_path = OUT / "protected-baseline.json"
    if before:
        saved = {
            "exams": {
                p.name: {"bytes": digest(p), "semantics": semantic_digest(read(p))}
                for p in sorted((before / "exams").glob("*.json"))
            },
            "keys": read(before / "key-hashes.json"),
            "assets": [
                {"path": a["relative_path"], "sha256": a["sha256"]}
                for a in read(before / "assets.json")["assets"]
            ],
        }
        baseline_path.write_text(json.dumps(saved, indent=2) + "\n")
    saved = read(baseline_path)
    changed = []
    for name, hashes in saved["exams"].items():
        path = DEFAULT_OUTPUT / "exams" / name
        assert semantic_digest(read(path)) == hashes["semantics"], name
        if digest(path) != hashes["bytes"]:
            changed.append(name)
    for path, sha in saved["keys"].items():
        assert digest(ROOT / path) == sha
    for asset in saved["assets"]:
        assert digest(DEFAULT_OUTPUT / asset["path"]) == asset["sha256"]
    protected = {
        "question_semantics": "UNCHANGED",
        "keys": "UNCHANGED",
        "existing_asset_bytes": "UNCHANGED",
        "changed_exam_files": changed,
        "old_assets_checked": len(saved["assets"]),
        "baseline": "protected-baseline.json",
    }
    counts = Counter(row["status"] for row in rows)
    report = {
        "scope": {
            "tests": 72,
            "parts": len(rows),
            "groups": component["groups"],
            "canonical_images": sum(len(r["ordered_source_segments"]) for r in rows),
        },
        "status_counts": dict(counts),
        "release_gate": "NO-GO"
        if any(r["status"] in ("UNRESOLVED", "BLOCKED") for r in rows)
        else "GO",
        "defects": {
            "physical_order_found": 1,
            "active_text_loss_parts_before": 7,
            "active_text_loss_states_before": 20,
            "missing_or_partial_page_contexts_repaired": 32,
            "additional_clipped_source_pages_repaired": 2,
            "range_binding_errors_repaired": 2,
            "nondefect_full_page_enhancements": 2,
            "new_assets": len(recipes["new_pages"]) + len(supplemental),
            "current_missing_pdf_pages": sum(len(r["missing_pdf_pages"]) for r in rows),
            "current_order_inversions": sum(r["order_inversions"] for r in rows),
            "current_duplicate_pages": sum(len(r["duplicate_page_content"]) for r in rows),
        },
        "browser": {
            "cases": len(browser["cases"]),
            "errors": browser["errors"],
            "unverified": browser["unverified"],
            "scope": browser["scope"],
        },
        "protected_content": protected,
        "new_asset_recipes": recipes["new_pages"],
        "supplemental_original_pages": supplemental,
        "parts": rows,
        "verification_limitations": [
            "Page pixel/layout comparison and continuation coverage; "
            "not independent transcription of every glyph.",
            "Browser suite uses real UI/images with isolated API/auth/media; "
            "real backend submit is a separate suite.",
            "C14 T3 P1 retains its full recovered retype. Its fields are corroborated, "
            "but the original Cambridge layout cannot be independently established.",
            "Unknown historical question versions are not rewritten or certified "
            "by the compatible-snapshot enrichment.",
        ],
    }
    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    (OUT / "index.html").write_text(
        '<!doctype html><meta charset="utf-8"><title>Listening Source Fidelity V2</title>'
        "<style>body{font:14px system-ui;margin:24px;background:#f4f6f5}section{background:white;"
        "padding:18px;margin:22px 0;border-radius:16px}.strip{display:flex;gap:12px;flex-wrap:wrap}"
        "figure{margin:0;width:360px}img{max-width:100%;height:auto}figcaption{overflow-wrap:anywhere;"
        "font-size:11px}p{overflow-wrap:anywhere}</style>"
        "<h1>Listening Source Fidelity V2 · 288 Parts</h1>"
        "<p>Original PDF left-to-right physical page order; selected source flow below. "
        "Original pixels, no OCR/AI replacement. "
        "Read report.json and the handoff for exceptions.</p>" + "\n".join(cards)
    )
    print(
        json.dumps(
            {
                "scope": report["scope"],
                "status_counts": report["status_counts"],
                "defects": report["defects"],
                "release_gate": report["release_gate"],
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--before", type=Path, help="Optional preserved pre-repair snapshot directory"
    )
    build(parser.parse_args().before)
