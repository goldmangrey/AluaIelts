import argparse
import json
from pathlib import Path

from pipeline import validate_records

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "path", type=Path, nargs="?", default=Path("app/data/lexicon/lexicon.jsonl")
    )
    parser.add_argument(
        "--relations",
        type=Path,
        default=Path("app/data/lexicon/lexical_relations.jsonl"),
    )
    args = parser.parse_args()
    records = [json.loads(line) for line in args.path.read_text().splitlines() if line]
    relations = [json.loads(line) for line in args.relations.read_text().splitlines() if line]
    print(
        json.dumps(
            {
                "total": len(records),
                "counts": validate_records(records, relations),
                "relations": len(relations),
            },
            sort_keys=True,
        )
    )
