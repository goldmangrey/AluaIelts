import csv
import gzip
import hashlib
import io
import json
import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, TextIO

VALID_KINDS = {"word", "synonym_upgrade", "phrase", "collocation"}
VALID_RELATIONS = {"synonym", "upgrade_of", "phrase_contains", "related", "collocation_of"}
WORD_RE = re.compile(r"^[A-Za-z][A-Za-z' -]*$")
URL_RE = re.compile(r"https?://|www\.", re.IGNORECASE)
MARKUP_RE = re.compile(r"<[^>]+>|\{\{|\}\}|\[\[")


def normalized(value: str) -> str:
    return " ".join(value.casefold().replace("’", "'").split())


def tokens(value: str) -> set[str]:
    return {part for part in re.findall(r"[a-z]+", normalized(value)) if len(part) > 2}


def stable_id(term: str, part_of_speech: str) -> str:
    key = f"{normalized(term)}|{part_of_speech}"
    return f"lex_{hashlib.sha256(key.encode()).hexdigest()[:20]}"


def raw_sense_id(term: str, part_of_speech: str, source: str, source_sense_id: str) -> str:
    key = f"{normalized(term)}|{part_of_speech}|{source}|{source_sense_id}"
    return f"sense_{hashlib.sha256(key.encode()).hexdigest()[:24]}"


@dataclass(frozen=True)
class Provenance:
    source: str
    source_id: str
    license: str
    attribution: str


@dataclass
class RawLexicalSense:
    raw_sense_id: str
    term: str
    normalized_term: str
    part_of_speech: str
    source: str
    source_sense_id: str
    source_order: int
    definition_en: str
    translation_ru: str | None
    ipa: str | None
    tags: tuple[str, ...]
    synonyms: tuple[str, ...]
    provenance: tuple[Provenance, ...]

    def json(self) -> dict[str, Any]:
        value = asdict(self)
        value["provenance"] = [asdict(item) for item in self.provenance]
        return value

    @classmethod
    def parse(cls, value: dict[str, Any]) -> "RawLexicalSense":
        value = dict(value)
        value["tags"] = tuple(value.get("tags", ()))
        value["synonyms"] = tuple(value.get("synonyms", ()))
        value["provenance"] = tuple(Provenance(**item) for item in value["provenance"])
        return cls(**value)


@dataclass
class SeedHeadword:
    term: str
    source: str
    source_id: str
    rank: int | None
    academic: bool
    license: str
    attribution: str


@dataclass
class CanonicalLexicalItem:
    id: str
    kind: str
    term: str
    normalized_term: str
    lemma: str
    part_of_speech: str
    primary_raw_sense_id: str | None
    translation_ru: str | None
    definition_en: str | None
    ipa: str | None
    usage_ru: str | None
    cefr: str | None
    frequency_rank: int | None
    is_academic: bool
    examples: list[dict[str, str]]
    synonym_ids: list[str] = field(default_factory=list)
    related_item_ids: list[str] = field(default_factory=list)
    phrase_ids: list[str] = field(default_factory=list)
    source_tags: list[str] = field(default_factory=list)
    provenance: list[dict[str, str]] = field(default_factory=list)
    is_active: bool = True
    learner_ready: bool = False
    quality_score: float = 0
    schema_version: int = 2

    def json(self) -> dict[str, Any]:
        return asdict(self)


def open_text(path: Path) -> TextIO:
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open(encoding="utf-8")


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def valid_term(term: str) -> bool:
    if term == "I":
        return True
    if not term or len(term) > 80 or not WORD_RE.fullmatch(term):
        return False
    # Uppercase acronyms and title-cased proper names are excluded; sentence pronoun I is explicit.
    return not term[0].isupper()


def read_ranked_source(path: Path, source: str) -> list[SeedHeadword]:
    values: list[SeedHeadword] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        sample = handle.read(4096)
        handle.seek(0)
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;")
        rows = csv.DictReader(handle, dialect=dialect)
        for fallback_rank, row in enumerate(rows, 1):
            lowered = {normalized(key): (value or "").strip() for key, value in row.items()}
            term = next(
                (lowered[key] for key in ("lemma", "word", "headword") if lowered.get(key)), ""
            )
            if not valid_term(term):
                continue
            rank_value = next(
                (
                    lowered[key]
                    for key in ("rank", "frequency rank", "sfi rank")
                    if lowered.get(key)
                ),
                "",
            )
            rank = int(rank_value) if rank_value.isdigit() else fallback_rank
            attribution = (
                "Browne, Culligan and Phillips, New Academic Word List"
                if source == "nawl"
                else "Browne, Culligan and Phillips, New General Service List"
            )
            values.append(
                SeedHeadword(
                    term,
                    source,
                    term,
                    rank,
                    source == "nawl",
                    "CC BY-SA 4.0",
                    attribution,
                )
            )
    return values


def phrase_candidate_terms(
    curated_path: Path, evidence_path: Path | None, seeds: Iterable[SeedHeadword]
) -> set[str]:
    seed_terms = {normalized(item.term) for item in seeds}
    values = {
        normalized(item["term"])
        for item in json.loads(curated_path.read_text(encoding="utf-8"))
        if " " in normalized(item["term"])
    }
    if evidence_path and evidence_path.exists():
        for line in evidence_path.read_text(encoding="utf-8").splitlines():
            candidate = normalized(line)
            parts = candidate.split()
            if (
                2 <= len(parts) <= 6
                and valid_term(line.strip())
                and any(part in seed_terms for part in parts)
            ):
                values.add(candidate)
    return values


def _translation_for_sense(
    translations: list[dict[str, Any]], gloss: str, sense_count: int
) -> str | None:
    russian = [item for item in translations if item.get("lang_code") == "ru" and item.get("word")]
    if not russian:
        return None
    gloss_tokens = tokens(gloss)
    scored: list[tuple[float, str]] = []
    for item in russian:
        label = str(item.get("sense") or "").strip()
        if not label:
            continue
        label_tokens = tokens(label)
        overlap = len(gloss_tokens & label_tokens) / max(1, len(gloss_tokens | label_tokens))
        if normalized(label) in normalized(gloss) or normalized(gloss) in normalized(label):
            overlap = max(overlap, 0.9)
        if overlap >= 0.35:
            scored.append((overlap, str(item["word"])))
    if scored:
        best_score = max(value[0] for value in scored)
        winners = sorted({word for score, word in scored if score == best_score})
        return winners[0] if len(winners) == 1 else None
    unlabeled = sorted({str(item["word"]) for item in russian if not item.get("sense")})
    if sense_count == 1 and len(unlabeled) == 1:
        return unlabeled[0]
    if len(russian) == 1 and not russian[0].get("sense") and sense_count == 1:
        return str(russian[0]["word"])
    return None


def read_kaikki(
    path: Path, wanted_terms: set[str], phrase_terms: set[str], license_name: str, attribution: str
) -> Iterator[RawLexicalSense]:
    with open_text(path) as handle:
        for line in handle:
            raw = json.loads(line)
            term = str(raw.get("word") or "").strip()
            key = normalized(term)
            if key not in wanted_terms and key not in phrase_terms:
                continue
            if not valid_term(term) or (" " in key and key not in phrase_terms):
                continue
            pos = str(raw.get("pos") or "other")
            senses = raw.get("senses") or []
            translations = raw.get("translations") or []
            ipa = next(
                (str(item["ipa"]) for item in raw.get("sounds", []) if item.get("ipa")), None
            )
            for index, sense in enumerate(senses):
                tags = tuple(sorted(set(sense.get("tags") or ())))
                if set(tags) & {"archaic", "obsolete", "offensive", "vulgar", "rare"}:
                    continue
                glosses = [
                    str(value).strip() for value in sense.get("glosses", []) if str(value).strip()
                ]
                if not glosses:
                    continue
                source_sense = str(sense.get("id") or sense.get("senseid") or f"{pos}:{index}")
                yield RawLexicalSense(
                    raw_sense_id=raw_sense_id(term, pos, "wiktionary", source_sense),
                    term=term,
                    normalized_term=key,
                    part_of_speech=pos,
                    source="wiktionary",
                    source_sense_id=source_sense,
                    source_order=index,
                    definition_en=glosses[0],
                    translation_ru=_translation_for_sense(translations, glosses[0], len(senses)),
                    ipa=ipa,
                    tags=tags,
                    synonyms=tuple(
                        sorted(
                            {
                                str(item)
                                for item in sense.get("synonyms", [])
                                if isinstance(item, str)
                            }
                        )
                    ),
                    provenance=(Provenance("wiktionary", source_sense, license_name, attribution),),
                )


def parse_wordnet_directory(path: Path) -> Iterator[dict[str, Any]]:
    for filename, pos in (
        ("data.noun", "noun"),
        ("data.verb", "verb"),
        ("data.adj", "adjective"),
        ("data.adv", "adverb"),
    ):
        with (path / filename).open(encoding="utf-8") as handle:
            for line in handle:
                if not line or line[0].isspace() or line.startswith("  "):
                    continue
                data, _, definition = line.partition("|")
                fields = data.split()
                if len(fields) < 5 or not definition.strip():
                    continue
                try:
                    count = int(fields[3], 16)
                except ValueError:
                    continue
                lemmas = [fields[4 + index * 2].replace("_", " ") for index in range(count)]
                yield {
                    "synset_id": f"{pos[0]}-{fields[0]}",
                    "lemmas": lemmas,
                    "part_of_speech": pos,
                    "definition": definition.strip(),
                }


def valid_example(text: str) -> bool:
    words = text.split()
    if not 5 <= len(words) <= 20 or URL_RE.search(text) or MARKUP_RE.search(text):
        return False
    internal_capitals = sum(word[:1].isupper() for word in words[1:])
    return internal_capitals <= 2 and text.isprintable()


def exact_term_match(text: str, term: str) -> bool:
    pattern = rf"(?<![A-Za-z']){re.escape(term)}(?![A-Za-z'])"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def read_tatoeba_cc0(path: Path, wanted: set[str]) -> dict[str, list[dict[str, str]]]:
    candidates: dict[str, list[tuple[tuple[int, int, str], dict[str, str]]]] = defaultdict(list)
    with open_text(path) as handle:
        for row in csv.reader(handle, delimiter="\t"):
            if len(row) < 3 or row[1] != "eng" or not valid_example(row[2]):
                continue
            sentence_id, _, text = row[:3]
            words = re.findall(r"[A-Za-z']+", normalized(text))
            present = {
                " ".join(words[start : start + size])
                for size in range(1, min(7, len(words) + 1))
                for start in range(len(words) - size + 1)
            } & wanted
            for term in present:
                if exact_term_match(text, term):
                    word_count = len(text.split())
                    rank = (abs(word_count - 12), word_count, sentence_id)
                    value = {
                        "text": text,
                        "source": "tatoeba",
                        "source_id": sentence_id,
                        "license": "CC0",
                        "attribution": "Tatoeba CC0 sentence export",
                    }
                    candidates[term].append((rank, value))
    return {term: [value for _, value in sorted(values)[:3]] for term, values in candidates.items()}


def choose_primary_sense(senses: list[RawLexicalSense]) -> RawLexicalSense:
    return min(
        senses,
        key=lambda item: (
            item.translation_ru is None,
            item.source != "wiktionary",
            "rare" in item.tags,
            item.source_order,
            item.source_sense_id,
        ),
    )


def definition_similarity(left: str, right: str) -> float:
    left_tokens, right_tokens = tokens(left), tokens(right)
    return len(left_tokens & right_tokens) / max(1, len(left_tokens | right_tokens))


def write_jsonl(path: Path, records: Iterable[dict[str, Any]], compressed: bool = False) -> None:
    if compressed or path.suffix == ".gz":
        binary = path.open("wb")
        archive = gzip.GzipFile(filename="", mode="wb", fileobj=binary, mtime=0)
        handle: TextIO = io.TextIOWrapper(archive, encoding="utf-8")
    else:
        handle = path.open("w", encoding="utf-8")
    with handle:
        for record in records:
            handle.write(
                json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
            )


def validate_records(
    records: list[dict[str, Any]], relations: list[dict[str, Any]]
) -> dict[str, int]:
    ids = [value["id"] for value in records]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate canonical lexical IDs.")
    known = set(ids)
    for value in records:
        if value["kind"] not in VALID_KINDS or not value["term"]:
            raise ValueError(f"Invalid lexical record: {value.get('id')}")
        if not value["provenance"] or any(
            not item.get("source") or not item.get("license") for item in value["provenance"]
        ):
            raise ValueError(f"Malformed provenance: {value['id']}")
        if value["learner_ready"] and not (
            value["translation_ru"] and value["definition_en"] and value["examples"]
        ):
            raise ValueError(f"Learner-ready record is incomplete: {value['id']}")
    for relation in relations:
        if (
            relation["relation_type"] not in VALID_RELATIONS
            or relation["source_id"] not in known
            or relation["target_id"] not in known
            or not relation["evidence"]
        ):
            raise ValueError(f"Invalid lexical relation: {relation}")
    return dict(Counter(value["kind"] for value in records))
