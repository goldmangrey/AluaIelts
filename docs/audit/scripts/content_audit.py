#!/usr/bin/env python3
"""Offline checks for Alua's canonical lexicon, grammar, and curriculum."""

from __future__ import annotations

import collections
import json
import random
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
LEXICON = ROOT / "backend/app/content/vocabulary_v2/lexicon.jsonl"
CURRICULUM = ROOT / "backend/app/content/curriculum/curriculum_v1.json"
GRAMMAR = ROOT / "backend/app/content/grammar"
SEED = 20261028


def main() -> None:
    rows = [json.loads(line) for line in LEXICON.read_text().splitlines() if line.strip()]
    ids = {row["id"] for row in rows}
    kinds = collections.Counter(row.get("kind") for row in rows)
    cefr = collections.Counter((row.get("kind"), row.get("cefr") or "MISSING") for row in rows)
    duplicate_groups: dict[tuple[str, str], list[str]] = collections.defaultdict(list)
    for row in rows:
        key = ((row.get("lemma") or row["term"]).casefold().strip(), row.get("part_of_speech", "other"))
        duplicate_groups[key].append(row["id"])
    duplicates = {key: values for key, values in duplicate_groups.items() if len(values) > 1}
    missing_links = [
        (row["id"], linked)
        for row in rows
        for field in ("related_item_ids", "related_ids")
        for linked in row.get(field, [])
        if linked not in ids
    ]
    latin = [row for row in rows if re.search(r"[A-Za-z]", row.get("translation_ru", ""))]
    suspect_ipa = [
        row for row in rows
        if row.get("ipa") and not re.fullmatch(r"[/\[].+[/\]]", row["ipa"].strip())
    ]
    print(f"records={len(rows)} kinds={dict(sorted(kinds.items()))}")
    print(f"ipa_present={sum(bool(r.get('ipa')) for r in rows)} ipa_ratio={sum(bool(r.get('ipa')) for r in rows)/len(rows):.4%}")
    print(f"empty_translation={sum(not str(r.get('translation_ru', '')).strip() for r in rows)}")
    print(f"latin_translation={len(latin)} long_translation_gt100={sum(len(r.get('translation_ru', '')) > 100 for r in rows)}")
    print(f"missing_source_tags={sum(not r.get('source_tags') for r in rows)} missing_provenance={sum(not r.get('provenance') for r in rows)}")
    print(f"duplicate_id_count={len(rows)-len(ids)} duplicate_lemma_pos_groups={len(duplicates)} duplicate_extra_records={sum(len(v)-1 for v in duplicates.values())}")
    print(f"missing_related_links={len(missing_links)} suspect_ipa_format={len(suspect_ipa)}")
    print("cefr_by_kind=" + json.dumps({f"{k[0]}:{k[1]}": v for k, v in sorted(cefr.items())}, ensure_ascii=False))
    print("latin_translation_examples=" + json.dumps([(r["id"], r["term"], r["translation_ru"]) for r in latin[:20]], ensure_ascii=False))
    print("duplicate_examples=" + json.dumps(list(duplicates.items())[:20], ensure_ascii=False))

    curriculum = json.loads(CURRICULUM.read_text())
    stages = curriculum["stages"]
    nodes = []
    for stage in stages:
        nodes.extend(stage.get("grammar_nodes", []))
        nodes.extend(stage.get("vocabulary_nodes", []))
        if stage.get("reinforcement_node"):
            nodes.append(stage["reinforcement_node"])
    node_ids = [node["id"] for node in nodes]
    node_id_set = set(node_ids)
    prerequisites = {
        node["id"]: set(node.get("prerequisites") or ()) for node in nodes
    }
    dangling = [(node, dep) for node, deps in prerequisites.items() for dep in deps if dep not in node_id_set]
    visiting: set[str] = set()
    visited: set[str] = set()
    cycles: list[list[str]] = []

    def visit(node: str, path: list[str]) -> None:
        if node in visiting:
            cycles.append(path[path.index(node):] + [node])
            return
        if node in visited:
            return
        visiting.add(node)
        for dep in prerequisites.get(node, ()):
            if dep in node_id_set:
                visit(dep, path + [dep])
        visiting.remove(node)
        visited.add(node)

    for node in node_ids:
        visit(node, [node])
    roots = {node for node, deps in prerequisites.items() if not deps}
    reachable = set(roots)
    changed = True
    while changed:
        changed = False
        for node, deps in prerequisites.items():
            if node not in reachable and deps <= reachable:
                reachable.add(node)
                changed = True
    grammar_rows = []
    for path in sorted(GRAMMAR.glob("*.json")):
        if path.name != "manifest.json":
            grammar_rows.extend(json.loads(path.read_text()))
    grammar_ids = [row.get("id") for row in grammar_rows]
    print(f"curriculum_stages={len(stages)} curriculum_nodes={len(nodes)} duplicate_node_ids={len(node_ids)-len(node_id_set)}")
    print(f"dangling_prerequisites={len(dangling)} cycles={len(cycles)} unreachable_nodes={len(node_id_set-reachable)}")
    print(f"grammar_lessons={len(grammar_rows)} duplicate_lesson_ids={len(grammar_ids)-len(set(grammar_ids))}")
    print(f"grammar_examples={sum(len(r.get('examples', [])) for r in grammar_rows)} common_errors={sum(len(r.get('common_errors', [])) for r in grammar_rows)} contrasts={sum(len(r.get('contrasts', [])) for r in grammar_rows)}")

    words = [row for row in rows if row.get("kind") == "word"]
    sample = random.Random(SEED).sample(words, 100)
    print(f"curator_sample_seed={SEED}")
    for row in sample:
        flags = []
        translation = row.get("translation_ru", "")
        if re.search(r"[A-Za-z]", translation):
            flags.append("latin-in-translation")
        if ";" not in translation and "," not in translation and len(row.get("synonyms", [])) >= 4:
            flags.append("many-synonyms-single-translation")
        if not translation.strip():
            flags.append("empty")
        print(json.dumps({"id": row["id"], "term": row["term"], "translation_ru": translation, "flags": flags}, ensure_ascii=False))


if __name__ == "__main__":
    main()
