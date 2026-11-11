"""Confirmed V1 defects only. Integration uses an ephemeral local PostgreSQL cluster."""

# ruff: noqa: F811
import copy
import hashlib
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest
import uvicorn
from sqlalchemy import select
from test_household_bootstrap import bootstrap, headers, postgres_url, system  # noqa: F401
from test_reading import event, perfect, start

from app.modules.exam_integrity import answers_checksum
from app.modules.reading.catalog import ReadingCatalog, get_catalog, questions
from app.modules.reading.models import ReadingAttemptRow

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "backend/scripts/reading_dataset"
sys.path.insert(0, str(TOOLS))
from confirmed_hotfixes import apply_confirmed_hotfixes, records  # noqa: E402
from engine import options, parse_book, rich_text  # noqa: E402
from enrich import enrich_exam  # noqa: E402
from repairs import fingerprint  # noqa: E402

V1 = json.loads((ROOT / "docs/reading-content-fidelity-v1/report.json").read_text())
ISSUES = [f for f in V1["confirmed_findings"] if f["verification_status"] == "CORRUPTED"]
CONFIG = records()
EXAMS = sorted({r["exam_id"] for r in CONFIG["repairs"]})


@pytest.fixture(scope="module")
def catalog():
    return ReadingCatalog()


@pytest.mark.parametrize("issue", ISSUES, ids=lambda f: f["issue_id"])
def test_each_original_issue_has_applied_source_bound_repair(issue, catalog):
    row = next(r for r in CONFIG["repairs"] if issue["issue_id"] in r["issue_ids"])
    exam = catalog.exams[row["exam_id"]]
    target = next(
        value
        for p in exam["passages"]
        for value in [p, *p["question_groups"]]
        if value["id"] == row["target_id"]
    )
    value = target["content"] if row["kind"] == "passage" else target
    assert fingerprint(value) == row["after_sha256"]
    assert row["evidence"]
    assert hashlib.sha256((ROOT / row["pdf_file"]).read_bytes()).hexdigest() == row["pdf_sha256"]
    assert catalog.entries[row["exam_id"]]["enabled_for_private_practice"]


def test_registry_exactly_41_no_ambiguity_or_candidate_repairs():
    ids = [i for row in CONFIG["repairs"] for i in row["issue_ids"]]
    assert len(ids) == len(set(ids)) == 41
    assert set(ids) == {issue["issue_id"] for issue in ISSUES}
    assert len(EXAMS) == 6


@pytest.mark.parametrize(
    "sentence",
    [
        "A team of archaeologists have been working in the mountains in Oppland in Norway",
        "A major reason for improving ventilation in 19th-century hospitals was the demand",
    ],
)
def test_prose_a_is_not_an_option_bank(sentence):
    assert options(sentence) == []


def test_column_options_and_roman_labels_remain_distinct():
    bank = options(
        "A solution B _ partnership C_ destruction\nD exaggeration E cleanliness\n"
        "F regulations G illness H nutrition"
    )
    assert [o["label"] for o in bank] == list("ABCDEFGH")
    assert bank[1]["text"] == "partnership" and bank[2]["text"] == "destruction"
    roman = options("i First\nii Second\niii Third\niv Fourth\nv Environmental effects", True)
    assert [o["label"] for o in roman] == ["i", "ii", "iii", "iv", "v"]


def test_original_numbered_dotted_and_underscore_blanks():
    segments = rich_text(
        "pain from a 6 ........ arm; perceiving 7 ........; "
        "the 8 ______ of the seabed; finding 9 ........ .",
        [6, 7, 8, 9],
    )
    assert [s["number"] for s in segments if s["type"] == "blank"] == [6, 7, 8, 9]
    assert segments[0]["text"] == "pain from a "
    assert segments[-1]["text"] == " ."


@pytest.mark.parametrize(
    "eid,first,letters,count",
    [
        ("cambridge-06-test-01", 23, "ABCDEFGHIJK", 4),
        ("cambridge-07-test-01", 6, "", 4),
        ("cambridge-07-test-01", 37, "ABCDEFGHIJK", 4),
        ("cambridge-07-test-04", 30, "ABCDEFGHIJ", 5),
        ("cambridge-14-test-02", 19, "", 8),
        ("cambridge-16-test-02", 17, "ABCDEFGH", 4),
        ("cambridge-16-test-03", 20, "", 3),
    ],
)
def test_source_summary_slots_banks_and_input_types(catalog, eid, first, letters, count):
    group = next(
        g
        for p in catalog.exams[eid]["passages"]
        for g in p["question_groups"]
        if g["question_numbers"][0] == first
    )
    assert [o["label"] for o in group["options"]] == list(letters)
    assert group["constraints"]["allowed_values"] == list(letters)
    slots = [
        s["number"]
        for b in group["content_blocks"]
        if b["type"] == "rich_text"
        for s in b["segments"]
        if s["type"] == "blank"
    ]
    assert slots == list(range(first, first + count))
    for q in group["questions"]:
        assert q["answer_input_type"] == ("single_select" if letters else "text")
        assert q["constraints"]["max_words"] == (None if letters else 1)
        assert q["constraints"]["allowed_values"] == list(letters)
    if first == 30:
        assert group["constraints"]["reuse_allowed"]


def test_specific_source_wording_and_paragraph_structure(catalog):
    exam = catalog.exams["cambridge-07-test-01"]
    p1, p2, p3 = exam["passages"]
    assert [b["label"] for b in p1["content"] if b.get("label")] == list("ABCDE")
    assert len(p1["content"]) == 8 and len(p3["content"]) == 9
    assert "immensely brighter" in p1["content"][5]["text"]
    assert "itself. However" in p1["content"][5]["text"]
    assert "It is sonar. But" in p1["content"][7]["text"]
    assert "learn several hundred" in p3["content"][5]["text"]
    assert p2["content"][-1]["text"] == "* 1 gallon: 4.546 litres"
    assert p2["content"][0]["type"] == "heading"
    qmap = questions(exam)
    assert qmap[exam["id"] + "-q-19"][2]["prompt"] == "Paragraph G"
    assert qmap[exam["id"] + "-q-20"][2]["prompt"] == "Paragraph H"
    assert "seven paragraphs, A-H" in p2["question_groups"][0]["instructions"]
    assert "a particular" in qmap[exam["id"] + "-q-27"][2]["options"][1]["text"]
    assert "we can" in qmap[exam["id"] + "-q-29"][2]["options"][3]["text"]
    assert qmap[exam["id"] + "-q-34"][2]["prompt"].startswith("As an")


def test_q16_original_key_now_selectable_and_original_asset_retained(catalog):
    eid = "cambridge-07-test-01"
    group = catalog.exams[eid]["passages"][1]["question_groups"][0]
    assert next(o["text"] for o in group["options"] if o["label"] == "v") == "Environmental effects"
    assert group["assets"][0]["crop_box"][3] > 620.4
    old = CONFIG["retained_assets"][0]
    assert old["id"] != group["assets"][0]["id"]
    assert catalog.assets[old["id"]] == old
    assert hashlib.sha256(catalog.path(old["path"]).read_bytes()).hexdigest() == old["sha256"]


def test_crop_refuses_to_clip_a_last_question_below_footer_guess(monkeypatch, tmp_path):
    import pdf_support

    data = {
        "width": 507,
        "height": 654,
        "lines": [
            {"text": "Questions 14-20", "bbox": [35, 100, 300, 115]},
            {"text": "19 Paragraph G", "bbox": [35, 590, 300, 605]},
            {"text": "20", "bbox": [35, 615, 50, 625]},
            {"text": "Paragraph H", "bbox": [65, 615, 300, 625]},
        ],
    }
    monkeypatch.setattr(pdf_support, "page_lines", lambda *args: data)
    with pytest.raises(ValueError, match="below automatic crop"):
        pdf_support.crop_group(
            ROOT / "ieltsbooks/Cambridge-IELTS-07.pdf",
            [26],
            list(range(14, 21)),
            tmp_path,
            "cambridge-07-test-99-p-1-g-14-20",
        )


@pytest.mark.parametrize("eid", EXAMS)
def test_hash_guards_and_idempotent_application(catalog, tmp_path, eid):
    exam = copy.deepcopy(catalog.exams[eid])
    apply_confirmed_hotfixes(exam, tmp_path)
    assert exam == catalog.exams[eid]
    row = next(r for r in CONFIG["repairs"] if r["exam_id"] == eid)
    target = next(
        v
        for p in exam["passages"]
        for v in [p, *p["question_groups"]]
        if v["id"] == row["target_id"]
    )
    if row["kind"] == "passage":
        target["content"][0]["text"] += " STALE"
    else:
        target["instructions"] += " STALE"
    with pytest.raises(ValueError, match="target changed"):
        apply_confirmed_hotfixes(exam, tmp_path)


def test_next_import_replays_only_six_targets_without_publishing(tmp_path, catalog):
    seen = set()
    for book in [6, 7, 14, 16]:
        source = next((ROOT / "ieltsReading").glob(f"*IELTS_{book:02}_*.txt"))
        for exam, key, _ in parse_book(source):
            if exam["id"] not in EXAMS:
                continue
            enrich_exam(exam, key, tmp_path)
            for row in CONFIG["repairs"]:
                if row["exam_id"] != exam["id"]:
                    continue
                target = next(
                    v
                    for p in exam["passages"]
                    for v in [p, *p["question_groups"]]
                    if v["id"] == row["target_id"]
                )
                value = target["content"] if row["kind"] == "passage" else target
                assert fingerprint(value) == row["after_sha256"]
            seen.add(exam["id"])
    assert seen == set(EXAMS)


@pytest.mark.parametrize("eid", EXAMS)
def test_restored_answers_atomic_submit_and_read_only_review(system, eid):
    db, client, _ = system
    owner, _ = bootstrap(client, "husband")
    h = headers(owner)
    attempt, _ = start(client, h, eid=eid)
    catalog = get_catalog()
    answers = perfect(catalog.keys[eid])
    selected = questions(catalog.exams[eid])
    request = event(
        attempt["version"],
        answers=answers,
        answers_checksum=answers_checksum(answers, selected),
        local_revision=1,
    )
    response = client.post(
        f"/api/v1/reading/attempts/{attempt['id']}/submit", headers=h, json=request
    )
    assert response.status_code == 200, response.text
    submitted = response.json()
    assert submitted["final_snapshot_accepted"] and submitted["result"]["raw_score"] == 40
    assert (
        client.post(
            f"/api/v1/reading/attempts/{attempt['id']}/submit", headers=h, json=request
        ).json()
        == submitted
    )
    terminal = client.get(f"/api/v1/reading/attempts/{attempt['id']}", headers=h).json()
    assert terminal["answers"] == answers and terminal["status"] == "submitted"
    result = client.get(f"/api/v1/reading/attempts/{attempt['id']}/result", headers=h)
    assert result.status_code == 200 and result.json()["raw_score"] == 40
    denied = client.put(
        f"/api/v1/reading/attempts/{attempt['id']}/answers/{next(iter(answers))}",
        headers=h,
        json=event(terminal["version"], answer="changed"),
    )
    assert denied.status_code == 409
    with db.session() as session:
        row = session.get(ReadingAttemptRow, attempt["id"])
        assert row.snapshot["key"] == catalog.keys[eid] and row.answers == answers


@pytest.mark.parametrize("eid", EXAMS)
def test_historical_attempt_snapshot_answers_result_and_asset_unchanged(system, eid):
    db, client, _ = system
    owner, _ = bootstrap(client, "husband")
    h = headers(owner)
    catalog = get_catalog()
    old_exam = copy.deepcopy(catalog.exams[eid])
    # Reconstruct the immutable historical shape whose canonical file was hotfixed.
    for row in CONFIG["repairs"]:
        if row["exam_id"] != eid or row["kind"] != "group":
            continue
        group = next(
            g
            for p in old_exam["passages"]
            for g in p["question_groups"]
            if g["id"] == row["target_id"]
        )
        if row["input_type_transitions"]:
            previous = row["input_type_transitions"][0][0]
            for question in group["questions"]:
                question["answer_input_type"] = previous
            if previous == "single_select":
                group["options"] = [{"label": "A", "text": "team of archaeologists"}]
                group["constraints"]["allowed_values"] = ["A"]
        if group["id"] == "cambridge-07-test-01-p-2-g-14-20":
            group["assets"] = copy.deepcopy(CONFIG["retained_assets"])
            group["options"] = [o for o in group["options"] if o["label"] != "v"]
    historical, _ = start(client, h, eid=eid)
    with db.session() as session:
        row = session.get(ReadingAttemptRow, historical["id"])
        row.snapshot = {
            **row.snapshot,
            "exam": old_exam,
            "metadata": {**row.snapshot["metadata"], "content_hash": "1" * 64},
        }
        row.content_hash = "1" * 64
        row.answers = {eid + "-q-20": "A"}
    before = client.get(f"/api/v1/reading/attempts/{historical['id']}", headers=h).json()
    current, _ = start(client, h, eid=eid)
    assert current["id"] != historical["id"]
    after = client.get(f"/api/v1/reading/attempts/{historical['id']}", headers=h).json()
    for field in ["answers", "exam", "content_hash", "version", "status"]:
        assert after[field] == before[field]
    asset = CONFIG["retained_assets"][0]
    response = client.get("/api/v1/reading/assets/" + asset["id"], headers=h)
    assert response.status_code == 200
    assert hashlib.sha256(response.content).hexdigest() == asset["sha256"]
    submit = client.post(
        f"/api/v1/reading/attempts/{historical['id']}/submit",
        headers=h,
        json=event(after["version"]),
    )
    assert submit.status_code == 200
    result = submit.json()["result"]
    assert result["content_hash"] == "1" * 64
    old_result = copy.deepcopy(result)
    client.get(f"/api/v1/reading/attempts/{current['id']}", headers=h)
    assert (
        client.get(f"/api/v1/reading/attempts/{historical['id']}/result", headers=h).json()
        == old_result
    )
    with db.session() as session:
        row = session.scalar(
            select(ReadingAttemptRow).where(ReadingAttemptRow.id == historical["id"])
        )
        assert row.snapshot["exam"] == old_exam and row.answers == {eid + "-q-20": "A"}


@pytest.mark.skipif(
    os.environ.get("ALUA_RUN_READING_HOTFIX_BROWSER") != "1",
    reason="Opt-in real frontend/HTTP test with disposable PostgreSQL",
)
def test_confirmed_hotfix_browser_exam_finish_review(system, tmp_path):
    _, client, _ = system
    owner, _ = bootstrap(client, "husband")
    data = {
        eid: {
            "answers": perfect(get_catalog().keys[eid]),
            "groups": [
                r["target_id"]
                for r in CONFIG["repairs"]
                if r["exam_id"] == eid and r["kind"] == "group"
            ],
        }
        for eid in EXAMS
    }
    fixture = tmp_path / "hotfix-browser.json"
    fixture.write_text(json.dumps(data))
    server = uvicorn.Server(
        uvicorn.Config(client.app, host="127.0.0.1", port=3402, log_level="warning", lifespan="off")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert server.started
        env = dict(os.environ, ALUA_HOTFIX_TOKEN=owner["token"], ALUA_HOTFIX_FIXTURE=str(fixture))
        subprocess.run(
            ["node", "scripts/test-reading-confirmed-hotfix.mjs"],
            cwd=ROOT / "web",
            env=env,
            check=True,
            timeout=600,
        )
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        assert not thread.is_alive()
