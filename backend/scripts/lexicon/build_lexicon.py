import argparse
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pipeline import (
    CanonicalLexicalItem,
    RawLexicalSense,
    choose_primary_sense,
    definition_similarity,
    normalized,
    open_text,
    stable_id,
    valid_term,
    validate_records,
    write_jsonl,
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with open_text(path) as handle:
        return [json.loads(line) for line in handle if line.strip()]


def build(staging: Path, output: Path, legacy: Path) -> None:
    required = [
        staging / "source_manifest.json",
        staging / "headwords.jsonl",
        staging / "kaikki_senses.jsonl.gz",
        staging / "wordnet_synsets.jsonl",
        staging / "tatoeba_examples.jsonl",
        staging / "curated_items.jsonl",
        staging / "curated_relations.jsonl",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit(
            "Missing normalized staging inputs. Run prepare_sources.py first:\n"
            + "\n".join(missing)
        )
    source_manifest = json.loads(required[0].read_text(encoding="utf-8"))
    headwords = read_jsonl(required[1])
    senses = [RawLexicalSense.parse(value) for value in read_jsonl(required[2])]
    wordnet = read_jsonl(required[3])
    examples = {value["normalized_term"]: value["examples"] for value in read_jsonl(required[4])}
    curated = read_jsonl(required[5])
    curated_relations = read_jsonl(required[6])

    items = canonicalize(headwords, senses, examples, source_manifest)
    items.extend(canonicalize_curated(curated, source_manifest))
    items, legacy_map, migration = migrate_legacy(legacy, items)
    items_by_id = {item.id: item for item in items}
    items_by_term: dict[str, list[CanonicalLexicalItem]] = defaultdict(list)
    for item in items:
        items_by_term[item.normalized_term].append(item)

    relations = build_wordnet_relations(wordnet, items_by_term)
    relations.extend(build_curated_relations(curated_relations, items_by_term))
    relations = dedupe_relations(relations)
    apply_relations(items_by_id, relations)
    records = sorted((item.json() for item in items_by_id.values()), key=lambda value: value["id"])
    counts = validate_records(records, relations)

    output.mkdir(parents=True, exist_ok=True)
    write_jsonl(output / "lexicon.jsonl", records)
    write_jsonl(output / "lexical_relations.jsonl", relations)
    (output / "legacy_id_map.json").write_text(
        json.dumps(legacy_map, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "legacy_migration_report.json").write_text(
        json.dumps(migration, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    manifest = make_manifest(records, relations, counts, source_manifest)
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if manifest["coverage"]["learner_ready"] < 3000:
        raise SystemExit(
            "Corpus built but acceptance failed: only "
            f"{manifest['coverage']['learner_ready']} learner-ready items"
        )


def canonicalize(
    headwords: list[dict[str, Any]],
    senses: list[RawLexicalSense],
    examples: dict[str, list[dict[str, str]]],
    source_manifest: dict[str, Any],
) -> list[CanonicalLexicalItem]:
    senses_by_term: dict[str, list[RawLexicalSense]] = defaultdict(list)
    for sense in senses:
        senses_by_term[sense.normalized_term].append(sense)
    seeds_by_term: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for value in headwords:
        seeds_by_term[normalized(value["term"])].append(value)
    output: list[CanonicalLexicalItem] = []
    for term, seeds in sorted(seeds_by_term.items()):
        available = senses_by_term.get(term, [])
        primary = choose_primary_sense(available) if available else None
        display_term = primary.term if primary else seeds[0]["term"]
        pos = primary.part_of_speech if primary else "other"
        provenance = [
            {
                "source": seed["source"],
                "source_id": seed["source_id"],
                "license": seed["license"],
                "attribution": seed["attribution"],
            }
            for seed in seeds
        ]
        if primary:
            provenance.extend(item.__dict__ for item in primary.provenance)
        item_examples = examples.get(term, [])[:3]
        output.append(
            create_item(
                kind="word",
                term=display_term,
                pos=pos,
                primary=primary,
                translation=primary.translation_ru if primary else None,
                definition=primary.definition_en if primary else None,
                ipa=primary.ipa if primary else None,
                usage=None,
                frequency=min(
                    (int(seed["rank"]) for seed in seeds if seed.get("rank") is not None),
                    default=None,
                ),
                academic=any(bool(seed["academic"]) for seed in seeds),
                examples=item_examples,
                provenance=provenance,
                source_tags=sorted(
                    {str(seed["source"]) for seed in seeds}
                    | ({primary.source} if primary else set())
                    | ({"tatoeba"} if item_examples else set())
                ),
            )
        )
    # Only bounded phrase terms selected during preparation are present in senses but not headwords.
    for term in sorted(set(senses_by_term) - set(seeds_by_term)):
        if " " not in term:
            continue
        primary = choose_primary_sense(senses_by_term[term])
        item_examples = examples.get(term, [])[:3]
        output.append(
            create_item(
                kind="phrase",
                term=primary.term,
                pos=primary.part_of_speech,
                primary=primary,
                translation=primary.translation_ru,
                definition=primary.definition_en,
                ipa=primary.ipa,
                usage=None,
                frequency=None,
                academic=False,
                examples=item_examples,
                provenance=[item.__dict__ for item in primary.provenance],
                source_tags=sorted({primary.source} | ({"tatoeba"} if item_examples else set())),
            )
        )
    return output


def canonicalize_curated(
    values: list[dict[str, Any]], source_manifest: dict[str, Any]
) -> list[CanonicalLexicalItem]:
    metadata = source_manifest["licenses"]["alua_curated"]
    output = []
    for value in values:
        pos = value.get("part_of_speech") or "other"
        examples = [
            {
                "text": text,
                "source": "alua_curated",
                "source_id": value["id"],
                "license": metadata["license"],
                "attribution": metadata["attribution"],
            }
            for text in value["examples"][:3]
        ]
        output.append(
            create_item(
                kind=value["kind"],
                term=value["term"],
                pos=pos,
                primary=None,
                translation=value["translation_ru"],
                definition=value["definition_en"],
                ipa=value.get("ipa"),
                usage=value.get("usage_ru"),
                frequency=None,
                academic=value.get("register") in {"academic", "formal"},
                examples=examples,
                provenance=[
                    {
                        "source": "alua_curated",
                        "source_id": value["id"],
                        "license": metadata["license"],
                        "attribution": metadata["attribution"],
                    }
                ],
                source_tags=["alua_curated"],
            )
        )
    return output


def create_item(
    *,
    kind: str,
    term: str,
    pos: str,
    primary: RawLexicalSense | None,
    translation: str | None,
    definition: str | None,
    ipa: str | None,
    usage: str | None,
    frequency: int | None,
    academic: bool,
    examples: list[dict[str, str]],
    provenance: list[dict[str, str]],
    source_tags: list[str],
) -> CanonicalLexicalItem:
    ready = bool(translation and definition and examples)
    score = round(
        0.2
        + (0.25 if translation else 0)
        + (0.2 if definition else 0)
        + (0.15 if examples else 0)
        + (0.1 if ipa else 0)
        + min(0.1, len(provenance) * 0.025),
        3,
    )
    return CanonicalLexicalItem(
        id=stable_id(term, pos),
        kind=kind,
        term=term,
        normalized_term=normalized(term),
        lemma=term,
        part_of_speech=pos,
        primary_raw_sense_id=primary.raw_sense_id if primary else None,
        translation_ru=translation,
        definition_en=definition,
        ipa=ipa,
        usage_ru=usage,
        cefr=None,
        frequency_rank=frequency,
        is_academic=academic,
        examples=examples,
        source_tags=source_tags,
        provenance=provenance,
        learner_ready=ready,
        quality_score=score,
    )


def build_wordnet_relations(
    synsets: list[dict[str, Any]], items_by_term: dict[str, list[CanonicalLexicalItem]]
) -> list[dict[str, Any]]:
    relations = []
    for synset in synsets:
        definition = str(synset["definition"])
        candidates = [
            item
            for lemma in synset["lemmas"]
            for item in items_by_term.get(normalized(lemma), [])
            if item.kind == "word"
            and item.part_of_speech == synset["part_of_speech"]
            and item.definition_en
            and definition_similarity(item.definition_en, definition) >= 0.25
        ]
        for source in candidates:
            for target in candidates:
                if source.id == target.id:
                    continue
                relations.append(
                    relation(
                        source.id,
                        target.id,
                        "synonym",
                        [
                            {
                                "source": "wordnet",
                                "source_id": synset["synset_id"],
                                "license": "Princeton WordNet License",
                                "definition": definition,
                            }
                        ],
                        0.8,
                    )
                )
    return relations


def build_curated_relations(
    values: list[dict[str, Any]], items_by_term: dict[str, list[CanonicalLexicalItem]]
) -> list[dict[str, Any]]:
    output = []
    for value in values:
        sources = items_by_term.get(normalized(value["source_term"]), [])
        targets = items_by_term.get(normalized(value["target_term"]), [])
        if len(sources) != 1 or len(targets) != 1:
            continue
        output.append(
            relation(
                sources[0].id,
                targets[0].id,
                value["relation_type"],
                [
                    {
                        "source": "alua_curated",
                        "source_id": f"{value['source_term']}->{value['target_term']}",
                        "license": "Alua authored content",
                        "context_note": value["context_note"],
                    }
                ],
                1.0,
            )
        )
    return output


def relation(
    source_id: str,
    target_id: str,
    relation_type: str,
    evidence: list[dict[str, Any]],
    quality: float,
) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "target_id": target_id,
        "relation_type": relation_type,
        "evidence": evidence,
        "quality_score": quality,
    }


def dedupe_relations(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique = {
        (value["source_id"], value["target_id"], value["relation_type"]): value for value in values
    }
    return [unique[key] for key in sorted(unique)]


def apply_relations(
    items: dict[str, CanonicalLexicalItem], relations: list[dict[str, Any]]
) -> None:
    for value in relations:
        source = items[value["source_id"]]
        target_id = value["target_id"]
        if value["relation_type"] == "synonym":
            source.synonym_ids.append(target_id)
        elif value["relation_type"] in {"phrase_contains", "collocation_of"}:
            items[target_id].phrase_ids.append(source.id)
            source.related_item_ids.append(target_id)
        else:
            source.related_item_ids.append(target_id)
    for item in items.values():
        item.synonym_ids = sorted(set(item.synonym_ids))
        item.related_item_ids = sorted(set(item.related_item_ids))
        item.phrase_ids = sorted(set(item.phrase_ids))


def migrate_legacy(
    legacy: Path, items: list[CanonicalLexicalItem]
) -> tuple[list[CanonicalLexicalItem], dict[str, str], dict[str, Any]]:
    by_term: dict[str, list[CanonicalLexicalItem]] = defaultdict(list)
    for item in items:
        by_term[item.normalized_term].append(item)
    id_map: dict[str, str] = {}
    rejected: dict[str, str] = {}
    matched = merged = kept = 0
    seen_legacy: set[str] = set()
    for path in sorted(legacy.glob("*.json")):
        if path.name in {
            "manifest.json",
            "lexical_supplement.json",
            "curated_lexical_relations.json",
            "curated_lexical_pos.json",
        }:
            continue
        for track in json.loads(path.read_text(encoding="utf-8")):
            for raw in track.get("items", []):
                old_id = raw["id"]
                if old_id in seen_legacy:
                    continue
                seen_legacy.add(old_id)
                term = normalized(raw.get("lemma", ""))
                candidates = by_term.get(term, [])
                if candidates:
                    target = min(
                        candidates,
                        key=lambda item: (
                            item.part_of_speech != raw.get("part_of_speech", "other"),
                            item.id,
                        ),
                    )
                    id_map[old_id] = target.id
                    matched += 1
                    did_merge = False
                    if not target.translation_ru and raw.get("translation_ru"):
                        target.translation_ru = raw["translation_ru"]
                        did_merge = True
                    if not target.definition_en and raw.get("definition_en"):
                        target.definition_en = raw["definition_en"]
                        did_merge = True
                    if not target.examples and raw.get("example"):
                        target.examples = [
                            {
                                "text": raw["example"],
                                "source": "alua_legacy",
                                "source_id": old_id,
                                "license": "Alua authored content",
                                "attribution": "Alua",
                            }
                        ]
                        did_merge = True
                    if did_merge:
                        merged += 1
                        target.source_tags.append("alua_legacy")
                        target.provenance.append(legacy_provenance(old_id))
                        target.learner_ready = bool(
                            target.translation_ru and target.definition_en and target.examples
                        )
                    continue
                if not valid_term(raw.get("lemma", "")):
                    rejected[old_id] = "invalid_term"
                    continue
                if not (
                    raw.get("translation_ru") and raw.get("definition_en") and raw.get("example")
                ):
                    rejected[old_id] = "missing_required_learner_data"
                    continue
                item = create_item(
                    kind="word",
                    term=raw["lemma"],
                    pos=raw.get("part_of_speech") or "other",
                    primary=None,
                    translation=raw["translation_ru"],
                    definition=raw["definition_en"],
                    ipa=None,
                    usage=None,
                    frequency=None,
                    academic=False,
                    examples=[
                        {
                            "text": raw["example"],
                            "source": "alua_legacy",
                            "source_id": old_id,
                            "license": "Alua authored content",
                            "attribution": "Alua",
                        }
                    ],
                    provenance=[legacy_provenance(old_id)],
                    source_tags=["alua_legacy"],
                )
                items.append(item)
                by_term[term].append(item)
                id_map[old_id] = item.id
                kept += 1
    report = {
        "legacy_count": len(seen_legacy),
        "matched": matched,
        "merged": merged,
        "kept_unique": kept,
        "rejected": len(rejected),
        "rejections": rejected,
        "missing_canonical_match": kept + len(rejected),
        "missing_translation": sum(
            reason == "missing_required_learner_data" for reason in rejected.values()
        ),
    }
    return items, id_map, report


def legacy_provenance(old_id: str) -> dict[str, str]:
    return {
        "source": "alua_legacy",
        "source_id": old_id,
        "license": "Alua authored content",
        "attribution": "Alua",
    }


def make_manifest(
    records: list[dict[str, Any]],
    relations: list[dict[str, Any]],
    counts: dict[str, int],
    source: dict[str, Any],
) -> dict[str, Any]:
    coverage = {
        "seed_headwords": source["counts"]["seed_headwords"],
        "enriched_definition": sum(bool(value["definition_en"]) for value in records),
        "enriched_ru_translation": sum(bool(value["translation_ru"]) for value in records),
        "enriched_examples": sum(bool(value["examples"]) for value in records),
        "learner_ready": sum(bool(value["learner_ready"]) for value in records),
        "missing_ru_translation": sum(not value["translation_ru"] for value in records),
        "with_ipa": sum(bool(value["ipa"]) for value in records),
    }
    return {
        "schema_version": 2,
        "dataset_version": "lexicon-v2-2026-09",
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "total_items": len(records),
        "counts": {
            kind: counts.get(kind, 0)
            for kind in ("word", "synonym_upgrade", "phrase", "collocation")
        },
        "coverage": coverage,
        "source_counts": {
            name: sum(name in value["source_tags"] for value in records)
            for name in (
                "ngsl",
                "nawl",
                "wordnet",
                "wiktionary",
                "tatoeba",
                "alua_curated",
                "alua_legacy",
            )
        },
        "source_manifest": source,
        "relation_counts": {
            relation_type: sum(value["relation_type"] == relation_type for value in relations)
            for relation_type in (
                "synonym",
                "upgrade_of",
                "phrase_contains",
                "related",
                "collocation_of",
            )
        },
        "validation": {
            "duplicates": 0,
            "broken_relations": 0,
            "learner_ready_incomplete": 0,
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--staging", type=Path, default=Path("data/lexicon_staging"))
    parser.add_argument("--output", type=Path, default=Path("app/data/lexicon"))
    parser.add_argument("--legacy", type=Path, default=Path("app/content/vocabulary"))
    args = parser.parse_args()
    build(args.staging, args.output, args.legacy)
