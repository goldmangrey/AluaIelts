"""Test-only export: validated public projections, never answer keys. No DB/auth calls."""
import os
import json
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

repo = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo / "backend"))
from app.modules.reading.catalog import ReadingCatalog  # noqa: E402

catalog = ReadingCatalog()
exams = [catalog.public_exam(exam) for eid, exam in catalog.exams.items()
         if catalog.entries[eid]["enabled_for_private_practice"]]
groups = [(exam, g) for exam in exams for p in exam["passages"] for g in p["question_groups"]]
counts = Counter(g["type"] for _, g in groups)
all_counts = Counter(g["type"] for exam in catalog.exams.values() for p in exam["passages"] for g in p["question_groups"])
samples = {t: next(e["id"] for e, g in groups if g["type"] == t) for t in counts}
now = datetime.now(timezone.utc)
output = {"exams": exams, "assets": {aid: str(catalog.path(asset["path"])) for aid, asset in catalog.assets.items()},
          "now": now.isoformat(), "deadline": (now + timedelta(hours=1)).isoformat(),
          "counts": dict(counts), "all_counts": dict(all_counts), "samples": samples,
          "enabled": len(exams), "extracted": len(catalog.entries)}
if os.environ.get("ALUA_RELEASE_TEST"):
    from app.modules.reading.grading import result_for
    eid = "cambridge-18-test-01"
    snapshot = {"exam": catalog.exams[eid], "key": catalog.keys[eid], "metadata": catalog.entries[eid]}
    qs = [q for p in snapshot["exam"]["passages"] for g in p["question_groups"] for q in g["questions"]]
    output["release_results"] = []
    for answers in ({}, {qs[0]["id"]: "lettuce", qs[1]["id"]: "tomato"}):
        result = result_for(snapshot, answers, "full_exam", None, 120, {})
        output["release_results"].append({"answers": answers, "result": result})
    output["release_hash"] = snapshot["metadata"]["content_hash"]
Path(sys.argv[1]).write_text(json.dumps(output))
print(f"Reading public test projections: {len(exams)} enabled exams; {len(counts)} question types; {len(groups)} groups")
