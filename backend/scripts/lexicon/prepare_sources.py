import argparse
import json
from pathlib import Path

from pipeline import (
    checksum,
    normalized,
    parse_wordnet_directory,
    phrase_candidate_terms,
    read_kaikki,
    read_ranked_source,
    read_tatoeba_cc0,
    write_jsonl,
)

NGSL_LICENSE = "CC BY-SA 4.0"
NGSL_ATTRIBUTION = "Browne, Culligan and Phillips, New General Service List"
NAWL_ATTRIBUTION = "Browne, Culligan and Phillips, New Academic Word List"
KAIKKI_LICENSE = "CC BY-SA 3.0 and GFDL"
KAIKKI_ATTRIBUTION = "English Wiktionary contributors; Kaikki/Wiktextract extraction"


def verify_checksums(source: Path) -> dict[str, str]:
    manifest = source / "checksums.sha256"
    if not manifest.exists():
        raise SystemExit(f"Missing checksum manifest: {manifest}")
    expected: dict[str, str] = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        digest, relative = line.split(maxsplit=1)
        expected[relative.lstrip("*").removeprefix("./")] = digest
    for relative, digest in expected.items():
        path = source / relative
        if not path.exists() or checksum(path) != digest:
            raise SystemExit(f"Checksum mismatch or missing source: {relative}")
    return expected


def prepare(source: Path, staging: Path, curated: Path) -> None:
    expected = verify_checksums(source)
    ngsl = source / "ngsl" / "NGSL_1.2_stats.csv"
    nawl = source / "nawl" / "NAWL_1.2_stats.csv"
    kaikki = source / "kaikki" / "kaikki.org-dictionary-English.jsonl.gz"
    wordnet = source / "wordnet" / "dict"
    tatoeba = source / "tatoeba" / "sentences_eng_cc0.tsv.gz"
    required = [
        ngsl,
        source / "ngsl" / "LICENSE.txt",
        nawl,
        source / "nawl" / "LICENSE.txt",
        kaikki,
        source / "kaikki" / "LICENSE.txt",
        tatoeba,
        source / "tatoeba" / "LICENSE.txt",
        source / "wordnet" / "LICENSE.txt",
        *(wordnet / name for name in ("data.noun", "data.verb", "data.adj", "data.adv")),
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit("Missing original source snapshots:\n" + "\n".join(missing))
    unchecked = [
        str(path.relative_to(source))
        for path in required
        if str(path.relative_to(source)) not in expected
    ]
    if unchecked:
        raise SystemExit("Source files missing from checksums.sha256:\n" + "\n".join(unchecked))

    seeds = read_ranked_source(ngsl, "ngsl") + read_ranked_source(nawl, "nawl")
    unique_seeds = {(normalized(item.term), item.source): item for item in seeds}
    seeds = sorted(
        unique_seeds.values(),
        key=lambda item: (item.source, item.rank or 999_999, normalized(item.term)),
    )
    wanted = {normalized(item.term) for item in seeds}
    evidence = source / "phrases" / "phrase_candidates.txt"
    phrase_terms = phrase_candidate_terms(curated, evidence, seeds)

    staging.mkdir(parents=True, exist_ok=True)
    write_jsonl(staging / "headwords.jsonl", [item.__dict__ for item in seeds])
    senses = read_kaikki(kaikki, wanted, phrase_terms, KAIKKI_LICENSE, KAIKKI_ATTRIBUTION)
    write_jsonl(
        staging / "kaikki_senses.jsonl.gz", (item.json() for item in senses), compressed=True
    )

    wordnet_records = []
    for synset in parse_wordnet_directory(wordnet):
        if any(normalized(lemma) in wanted for lemma in synset["lemmas"]):
            wordnet_records.append(synset)
    write_jsonl(
        staging / "wordnet_synsets.jsonl",
        sorted(wordnet_records, key=lambda item: item["synset_id"]),
    )

    examples = read_tatoeba_cc0(tatoeba, wanted | phrase_terms)
    write_jsonl(
        staging / "tatoeba_examples.jsonl",
        (
            {"normalized_term": term, "examples": values}
            for term, values in sorted(examples.items())
        ),
    )
    curated_values = json.loads(curated.read_text(encoding="utf-8"))
    curated_pos = json.loads(
        curated.with_name("curated_lexical_pos.json").read_text(encoding="utf-8")
    )
    for value in curated_values:
        if value["id"] not in curated_pos:
            raise SystemExit(f"Missing curated POS: {value['id']}")
        value["part_of_speech"] = curated_pos[value["id"]]
    write_jsonl(
        staging / "curated_items.jsonl", sorted(curated_values, key=lambda item: item["id"])
    )
    curated_relations = curated.with_name("curated_lexical_relations.json")
    write_jsonl(
        staging / "curated_relations.jsonl",
        sorted(
            json.loads(curated_relations.read_text(encoding="utf-8")),
            key=lambda item: (item["source_term"], item["target_term"]),
        ),
    )
    manifest = {
        "schema_version": 1,
        "source_checksums": expected,
        "licenses": {
            "ngsl": {"license": NGSL_LICENSE, "attribution": NGSL_ATTRIBUTION},
            "nawl": {"license": NGSL_LICENSE, "attribution": NAWL_ATTRIBUTION},
            "wiktionary": {"license": KAIKKI_LICENSE, "attribution": KAIKKI_ATTRIBUTION},
            "wordnet": {
                "license": "Princeton WordNet License",
                "attribution": "Princeton University WordNet",
            },
            "tatoeba": {"license": "CC0", "attribution": "Tatoeba CC0 sentence export"},
            "alua_curated": {"license": "Alua authored content", "attribution": "Alua"},
        },
        "counts": {
            "seed_headwords": len(seeds),
            "phrase_candidate_terms": len(phrase_terms),
            "wordnet_synsets": len(wordnet_records),
            "tatoeba_terms_with_examples": len(examples),
        },
    }
    (staging / "source_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("data/lexicon_sources"))
    parser.add_argument("--staging", type=Path, default=Path("data/lexicon_staging"))
    parser.add_argument(
        "--curated", type=Path, default=Path("app/content/vocabulary/lexical_supplement.json")
    )
    args = parser.parse_args()
    prepare(args.source, args.staging, args.curated)
