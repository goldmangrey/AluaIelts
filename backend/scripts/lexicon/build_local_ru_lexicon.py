"""Build the production Vocabulary V2 corpus from checked-in ``*_RU`` sources.

The translated files are the learner-facing contract.  Their untranslated siblings
are retained only as provenance/reference snapshots and are never read here.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

KINDS = {"word", "phrase", "collocation", "phrasal_verb", "synonym_upgrade"}
POS_MAP = {
    "n": "noun",
    "v": "verb",
    "adj": "adjective",
    "adv": "adverb",
    "prep": "preposition",
    "pron": "pronoun",
    "conj": "conjunction",
    "det": "determiner",
    "exclam": "interjection",
    "modal v": "modal_verb",
    "number": "number",
}
CEFR_RE = re.compile(r"\b(A1|A2|B1|B2|C1|C2)\b", re.I)
POS_RE = re.compile(r"\b(n|v|adj|adv|prep|pron|conj|det|exclam|number|modal v)\.(?=\s|,|$)", re.I)
RANKED_RE = re.compile(r"^\s*(\d+)\.\s+(.+)$")
PEARSON_RE = re.compile(r"^\s*(\d+)\s+(.+?)\s*(?:\([^)]*\)\s*)+$")
META_TERMS = {
    "speech",
    "writing",
    "raw freq",
    "freq per million",
    "ftw",
    "integrated",
    "rank",
    "appendices",
}


def normalized(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = value.replace("’", "'").replace("‘", "'").replace("`", "'")
    return " ".join(value.casefold().strip().split())


def clean_ipa(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value if value.startswith("[") and value.endswith("]") else None


def clean_translation(value: str) -> str | None:
    value = " ".join(value.strip().split())
    if not value or not re.search("[А-Яа-яЁё]", value):
        return None
    return value


def clean_term(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).replace("\u00a0", " ").strip()
    value = re.sub(r"^\d+\.\s*", "", value)
    value = CEFR_RE.sub("", value)
    value = POS_RE.sub("", value)
    value = re.sub(r"\s+", " ", value).strip(" ,;:–—")
    return value


def valid_term(term: str, *, multiword: bool | None = None) -> bool:
    key = normalized(term)
    words = key.split()
    if not key or key in META_TERMS or len(key) > 100 or len(words) > 12:
        return False
    if multiword is True and len(words) < 2:
        return False
    if multiword is False and len(words) != 1:
        return False
    if any(marker in key for marker in ("©", "http", "www.", "appendix", "sublist")):
        return False
    if re.search(r"[.!?]$", term) or not re.search(r"[A-Za-z]", term):
        return False
    return bool(re.fullmatch(r"[A-Za-z][A-Za-z'’/() -]*", term))


def infer_pos(raw: str) -> str:
    match = POS_RE.search(raw)
    return POS_MAP.get(match.group(1).casefold(), "other") if match else "other"


@dataclass
class SourceRecord:
    term: str
    translation_ru: str
    ipa: str | None
    kind: str
    source: str
    source_row: int
    lemma: str | None = None
    part_of_speech: str = "other"
    cefr: str | None = None
    definition_en: str | None = None
    forms: tuple[str, ...] = ()


@dataclass
class Canonical:
    id: str
    kind: str
    term: str
    lemma: str
    translation_ru: str
    ipa: str | None = None
    part_of_speech: str = "other"
    definition_en: str | None = None
    usage_ru: str | None = None
    examples: list[str] = field(default_factory=list)
    synonyms: list[str] = field(default_factory=list)
    related_ids: list[str] = field(default_factory=list)
    source_tags: list[str] = field(default_factory=list)
    cefr: str | None = None
    provenance: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__


def _triples(row: list[str]) -> list[tuple[str, str, str]]:
    return [(row[index], row[index + 1], row[index + 2]) for index in range(0, len(row) - 2, 3)]


def parse_csv(path: Path) -> list[SourceRecord]:
    source = source_tag(path)
    with path.open(encoding="utf-8-sig", newline="", errors="replace") as stream:
        rows = list(csv.reader(stream))
    records: list[SourceRecord] = []
    name = path.name
    if "stats_RU" in name:
        for number, row in enumerate(rows[1:], 2):
            add_record(records, row[0], row[2], row[1], "word", source, number)
    elif "NGSL-GR" in name:
        for number, row in enumerate(rows[1:], 2):
            add_record(records, row[3], row[5], row[4], "word", source, number)
    elif "with_English_definitions" in name:
        for number, row in enumerate(rows[1:], 2):
            pos = POS_MAP.get(row[6].casefold(), "other")
            add_record(
                records,
                row[0],
                row[2],
                row[1],
                "word",
                source,
                number,
                part_of_speech=pos,
                definition_en=row[3].strip() or None,
            )
    else:
        # Teaching files encode one headword followed by explicit inflected forms.
        # Only the first triple becomes learnable; remaining triples are aliases.
        start = next(
            (
                index
                for index, row in enumerate(rows)
                if row and not row[0].startswith("##") and clean_translation(row[2])
            ),
            len(rows),
        )
        for number, row in enumerate(rows[start:], start + 1):
            groups = _triples(row)
            if not groups:
                continue
            headword, ipa, translation = groups[0]
            forms = tuple(clean_term(group[0]) for group in groups[1:] if group[0].strip())
            add_record(
                records,
                headword,
                translation,
                ipa,
                "word",
                source,
                number,
                forms=forms,
            )
    return records


def parse_txt(path: Path) -> list[SourceRecord]:
    rows = [line.split("\t") for line in path.read_text(encoding="utf-8-sig").splitlines()]
    name = path.name
    source = source_tag(path)
    if "Pearson" in name:
        return parse_pearson(rows, source)
    if "PHRASE_List_505" in name:
        return parse_ranked_table(rows, source, "phrase")
    if "AFL_607" in name:
        return parse_ranked_table(rows, source, "phrase")
    if "PHaVE" in name:
        records: list[SourceRecord] = []
        for number, row in enumerate(rows, 1):
            if len(row) >= 3 and RANKED_RE.match(row[0]):
                add_record(records, row[0], row[2], row[1], "phrasal_verb", source, number)
        return records

    phrase_source = "phrases" in name.casefold() or "Phrase_List" in name
    records = []
    for number, row in enumerate(rows, 1):
        if len(row) < 3 or not clean_ipa(row[1]):
            continue
        raw = row[0]
        term = clean_term(raw)
        is_multiword = len(normalized(term).split()) > 1
        if phrase_source and not is_multiword:
            continue
        kind = "phrase" if phrase_source else "word"
        add_record(
            records,
            raw,
            row[2],
            row[1],
            kind,
            source,
            number,
            part_of_speech=infer_pos(raw),
            cefr=(match.group(1).upper() if (match := CEFR_RE.search(raw)) else None),
        )
    return records


def parse_ranked_table(rows: list[list[str]], source: str, kind: str) -> list[SourceRecord]:
    records: list[SourceRecord] = []
    previous_was_rank = False
    for number, row in enumerate(rows, 1):
        value = row[0].strip() if row else ""
        if value.isdigit():
            previous_was_rank = True
            continue
        if previous_was_rank and len(row) >= 3 and clean_ipa(row[1]):
            add_record(records, value, row[2], row[1], kind, source, number)
        previous_was_rank = False
    return records


def parse_pearson(rows: list[list[str]], source: str) -> list[SourceRecord]:
    """Reconstruct the list's head + continuation layout into collocations."""
    records: list[SourceRecord] = []
    head: tuple[str, str, str, int] | None = None
    for number, row in enumerate(rows, 1):
        if len(row) < 3 or not clean_ipa(row[1]) or not clean_translation(row[2]):
            head = None
            continue
        raw = row[0].strip()
        match = PEARSON_RE.match(raw)
        if match:
            head = (_pearson_fragment(match.group(2)), row[1], row[2], number)
            continue
        fragment = _pearson_fragment(raw)
        if head and valid_term(fragment, multiword=False):
            left = head[0]
            right = fragment
            add_record(
                records,
                f"{left} {right}",
                f"{head[2]}; {row[2]}",
                None,
                "collocation",
                source,
                number,
            )
    return records


def _pearson_fragment(value: str) -> str:
    """Remove the ACL's grammatical placeholders, not lexical material."""
    value = re.sub(r"\s*\((?:a|an|the|of|to)\)\s*", " ", value, flags=re.I)
    value = re.sub(r"\s*\((?:adj|adv|n|v|vpp)\)\s*$", "", value, flags=re.I)
    return clean_term(value)


def add_record(
    records: list[SourceRecord],
    raw_term: str,
    raw_translation: str,
    raw_ipa: str | None,
    kind: str,
    source: str,
    row: int,
    *,
    part_of_speech: str = "other",
    cefr: str | None = None,
    definition_en: str | None = None,
    forms: tuple[str, ...] = (),
) -> None:
    term = clean_term(raw_term)
    translation = clean_translation(raw_translation)
    multiword = kind != "word"
    if translation and valid_term(term, multiword=multiword):
        records.append(
            SourceRecord(
                term=term,
                lemma=term,
                translation_ru=translation,
                ipa=clean_ipa(raw_ipa),
                kind=kind,
                source=source,
                source_row=row,
                part_of_speech=part_of_speech,
                cefr=cefr,
                definition_en=definition_en,
                forms=forms,
            )
        )


def source_tag(path: Path) -> str:
    name = path.name.split("_RU", 1)[0]
    return re.sub(r"[^A-Za-z0-9.-]+", "_", name).strip("_")


def stable_id(kind: str, term: str, pos: str) -> str:
    identity = f"{kind}:{normalized(term)}:{pos}"
    digest = hashlib.sha256(identity.encode()).hexdigest()[:12]
    slug = re.sub(r"[^a-z0-9]+", "_", normalized(term)).strip("_")[:42]
    return f"lex_{slug}_{digest}"


def load_legacy(directory: Path) -> list[Canonical]:
    manifest = json.loads((directory / "manifest.json").read_text())
    records: list[Canonical] = []
    for filename in manifest["content_files"]:
        for track in json.loads((directory / filename).read_text()):
            for item in track["items"]:
                term = item["lemma"]
                pos = item.get("part_of_speech", "other")
                kind = (
                    "phrasal_verb" if pos == "phrasal_verb" else "phrase" if " " in term else "word"
                )
                records.append(
                    Canonical(
                        id=item["id"],
                        kind=kind,
                        term=term,
                        lemma=term,
                        translation_ru=item["translation_ru"],
                        part_of_speech=pos,
                        definition_en=item.get("definition_en"),
                        examples=[item["example"]] if item.get("example") else [],
                        synonyms=item.get("synonyms", []),
                        source_tags=["alua_legacy_v1"],
                        cefr=track.get("cefr_level"),
                        provenance=[{"source": "alua_legacy_v1", "source_id": item["id"]}],
                    )
                )
    supplement = directory / "lexical_supplement.json"
    for item in json.loads(supplement.read_text()):
        records.append(
            Canonical(
                id=item["id"],
                kind=item["kind"],
                term=item["term"],
                lemma=item["term"],
                translation_ru=item["translation_ru"],
                ipa=item.get("ipa"),
                definition_en=item.get("definition_en"),
                usage_ru=item.get("usage_ru"),
                examples=item.get("examples", []),
                synonyms=item.get("synonyms", []),
                related_ids=item.get("related_item_ids", []),
                source_tags=["alua_legacy_v1"],
                cefr=item.get("cefr"),
                provenance=[{"source": "alua_legacy_v1", "source_id": item["id"]}],
            )
        )
    return records


def compatible_key(
    items: dict[tuple[str, str, str], Canonical], record: SourceRecord
) -> tuple[str, str, str]:
    key_kind = record.kind
    term = normalized(record.lemma or record.term)
    if key_kind != "word":
        return key_kind, term, "other"
    exact = (key_kind, term, record.part_of_speech)
    if exact in items:
        return exact
    other = (key_kind, term, "other")
    if record.part_of_speech != "other" and other in items:
        # Upgrade an unresolved record to the first explicit POS. A later, different
        # explicit POS receives its own canonical item instead of being collapsed.
        item = items.pop(other)
        item.part_of_speech = record.part_of_speech
        items[exact] = item
        return exact
    if record.part_of_speech == "other":
        explicit = next(
            (key for key in items if key[0] == key_kind and key[1] == term),
            None,
        )
        return other if other in items else explicit or other
    return exact


def build(source_dir: Path, legacy_dir: Path, output: Path) -> dict[str, Any]:
    source_files = sorted((*source_dir.rglob("*_RU.csv"), *source_dir.rglob("*_RU.txt")))
    parsed: list[SourceRecord] = []
    inventory = []
    contributions: Counter[str] = Counter()
    inflections = 0
    for path in source_files:
        records = parse_csv(path) if path.suffix == ".csv" else parse_txt(path)
        parsed.extend(records)
        contributions[source_tag(path)] += len(records)
        inflections += sum(len(record.forms) for record in records)
        inventory.append(
            {
                "file": str(path.relative_to(source_dir)),
                "format": path.suffix.removeprefix("."),
                "physical_rows": sum(1 for _ in path.open(encoding="utf-8-sig")),
                "lexical_records": len(records),
                "learner_input": True,
                "content_type": "phrase"
                if any(record.kind != "word" for record in records)
                else "word",
            }
        )

    canonical: dict[tuple[str, str, str], Canonical] = {}
    duplicate_count = 0
    for record in parsed:
        key = compatible_key(canonical, record)
        item = canonical.get(key)
        if item is None:
            item = Canonical(
                id=stable_id(record.kind, record.lemma or record.term, record.part_of_speech),
                kind=record.kind,
                term=record.term,
                lemma=record.lemma or record.term,
                translation_ru=record.translation_ru,
                ipa=record.ipa,
                part_of_speech=record.part_of_speech,
                definition_en=record.definition_en,
                cefr=record.cefr,
            )
            canonical[key] = item
        else:
            duplicate_count += 1
            item.ipa = item.ipa or record.ipa
            item.definition_en = item.definition_en or record.definition_en
            item.cefr = item.cefr or record.cefr
        if record.source not in item.source_tags:
            item.source_tags.append(record.source)
        item.provenance.append({"source": record.source, "source_row": record.source_row})

    legacy = load_legacy(legacy_dir)
    legacy_map: dict[str, str] = {}
    legacy_merged = 0
    legacy_unique = 0
    for old in legacy:
        pseudo = SourceRecord(
            term=old.term,
            lemma=old.lemma,
            translation_ru=old.translation_ru,
            ipa=old.ipa,
            kind=old.kind,
            source="alua_legacy_v1",
            source_row=0,
            part_of_speech=old.part_of_speech,
        )
        key = compatible_key(canonical, pseudo)
        current = canonical.get(key)
        if current is None:
            canonical[key] = old
            current = old
            legacy_unique += 1
        else:
            legacy_merged += 1
            current.definition_en = old.definition_en or current.definition_en
            current.usage_ru = old.usage_ru or current.usage_ru
            current.examples = old.examples or current.examples
            current.synonyms = old.synonyms or current.synonyms
            current.cefr = old.cefr or current.cefr
            current.ipa = current.ipa or old.ipa
            if "alua_legacy_v1" not in current.source_tags:
                current.source_tags.append("alua_legacy_v1")
            current.provenance.extend(old.provenance)
        legacy_map[old.id] = current.id

    values = sorted(
        canonical.values(), key=lambda item: (item.kind, normalized(item.term), item.id)
    )
    ids = {item.id for item in values}
    if len(ids) != len(values) or any(item.kind not in KINDS for item in values):
        raise RuntimeError("Canonical ID/kind validation failed")
    if any(not item.term or not item.translation_ru for item in values):
        raise RuntimeError("Learner-ready term/translation validation failed")
    output.mkdir(parents=True, exist_ok=True)
    (output / "lexicon.jsonl").write_text(
        "".join(
            json.dumps(item.as_dict(), ensure_ascii=False, sort_keys=True) + "\n" for item in values
        )
    )
    (output / "legacy_id_map.json").write_text(
        json.dumps(legacy_map, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    counts = Counter(item.kind for item in values)
    source_coverage = Counter(tag for item in values for tag in item.source_tags)
    manifest = {
        "schema_version": 2,
        "dataset_version": "vocabulary-v2-local-ru-2026-09",
        "input_policy": "Only files whose filename contains _RU",
        "raw_records": len(parsed),
        "unique_canonical_items": len(values),
        "counts": dict(sorted(counts.items())),
        "duplicates_merged": duplicate_count,
        "inflected_forms_collapsed": inflections,
        "items_with_ru_translation": sum(bool(item.translation_ru) for item in values),
        "items_with_ipa": sum(bool(item.ipa) for item in values),
        "legacy_records": len(legacy),
        "legacy_merged": legacy_merged,
        "legacy_unique_preserved": legacy_unique,
        "source_contributions_raw": dict(sorted(contributions.items())),
        "source_coverage_unique": dict(sorted(source_coverage.items())),
        "inventory": inventory,
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", type=Path, default=Path("data/lexicon_sources"))
    parser.add_argument("--legacy", type=Path, default=Path("app/content/vocabulary"))
    parser.add_argument("--output", type=Path, default=Path("app/content/vocabulary_v2"))
    args = parser.parse_args()
    print(json.dumps(build(args.sources, args.legacy, args.output), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
