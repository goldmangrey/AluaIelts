"""Validated editorial practice only. Archive is never routed to HTTP."""

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from sqlalchemy import select

from app.modules.writing.models import WritingTaskRow

ROOT = Path(__file__).resolve().parents[2] / "content/writing_v2"


def validate_dataset():
    master = json.loads((ROOT / "archive/alua-writing-v2.json").read_text())
    ready = json.loads((ROOT / "alua-writing-v2-ready.json").read_text())
    rows = list(csv.DictReader((ROOT / "archive/alua-writing-v2.csv").open(encoding="utf-8-sig")))
    counts = Counter(r["content_quality_status"] for r in master)
    assert len(master) == len(rows) == 326
    assert counts == {"READY": 32, "PENDING_INDIVIDUAL_SOURCE_REVIEW": 288, "MERGED_ALIAS": 6}
    lookup = {r["id"]: r for r in master}
    assert len(lookup) == 326 and len({r["id"] for r in rows}) == 326
    assert len(ready) == len({r["id"] for r in ready}) == 32
    assert {r["id"] for r in ready} == {
        r["id"] for r in master if r["content_quality_status"] == "READY"
    }
    prompts = set()
    for r in ready:
        m = lookup[r["id"]]
        assert m["record_relation_v2"] == "CANONICAL" and m["alua_publication_ready"]
        for key in ("practice_prompt", "topic_id", "essay_type", "task_requirements"):
            assert r[key] and r[key] == m[key]
        assert r["canonical_id_v2"] == r["id"]
        assert len(r["practice_prompt"].split()) >= 20
        assert "\n\n" in r["practice_prompt"] and r["practice_prompt"].endswith((".", "?"))
        assert r["practice_prompt"] not in prompts
        prompts.add(r["practice_prompt"])
    for r in rows:
        m = lookup[r["id"]]
        for key, value in r.items():
            expected = m[key]
            if isinstance(expected, (list, dict)):
                assert json.loads(value) == expected, (r["id"], key)
            elif isinstance(expected, bool):
                assert value.lower() == str(expected).lower(), (r["id"], key)
            else:
                assert value == ("" if expected is None else str(expected)), (r["id"], key)
    return master, ready, dict(counts)


def import_tasks(db):
    from app.modules.writing.bridge import initialize_local_bridge

    initialize_local_bridge()
    master, ready, counts = validate_dataset()
    lookup = {r["id"]: r for r in master}
    with db.session() as session:
        existing = {r.id: r for r in session.scalars(select(WritingTaskRow))}
        for r in ready:
            value = {
                k: r[k]
                for k in ("id", "topic_id", "essay_type", "practice_prompt", "task_requirements")
            }
            value.update(
                title=lookup[r["id"]]["question_summary"],
                dataset_version="writing-v2",
                publication_status="READY",
            )
            # Stable IDs are immutable; changed prompts require an explicit version migration.
            if r["id"] in existing:
                assert existing[r["id"]].payload == value, "Immutable Writing task changed"
            else:
                session.add(WritingTaskRow(id=r["id"], payload=value))
    return counts


if __name__ == "__main__":
    from app.db.database import get_database

    print(import_tasks(get_database()))
    print(
        {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in ROOT.rglob("*")
            if p.is_file()
        }
    )
