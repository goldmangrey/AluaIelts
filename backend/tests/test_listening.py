"""Real Stage 1 + disposable PostgreSQL + synthetic audio; never production data/media."""

import copy
import json
import subprocess
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from test_household_bootstrap import bootstrap, headers, postgres_url, system  # noqa: F401

from app.core.exceptions import NotFoundError
from app.modules.listening.catalog import ListeningCatalog, audio_mime, confined, questions
from app.modules.listening.grading import forms, official_limit, result_for
from app.modules.listening.router import get_service
from app.modules.listening.schemas import CreateAttempt
from app.modules.listening.service import ListeningService, utcnow


@pytest.fixture
def listening(system, tmp_path):  # noqa: F811
    db, client, _ = system
    c = ListeningCatalog(audio_root=tmp_path)
    tone = tmp_path / "fixture.mp3"
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=12",
            "-c:a",
            "libmp3lame",
            str(tone),
        ],
        check=True,
    )
    m4a = tmp_path / "fixture.m4a"
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(tone), "-c:a", "aac", str(m4a)],
        check=True,
    )
    # Synthetic test manifest only, injected dependency; production manifest untouched.
    for parts in c.audio.values():
        for a in parts.values():
            media = m4a if a["book"] == 5 else tone
            a["relative_path"] = media.name
            a["byte_size"] = media.stat().st_size
            a["mime_type"] = "audio/mp4" if a["book"] == 5 else "audio/mpeg"
    now = [utcnow()]
    service = ListeningService(db, c, clock=lambda: now[0])
    client.app.dependency_overrides[get_service] = lambda: service
    yield service, client, now, tmp_path
    client.app.dependency_overrides.pop(get_service, None)


def test_catalog_and_all_real_keys():
    c = ListeningCatalog()
    assert Counter(c.mode(e) for e in c.exams) == {
        "verified": 6,
        "preliminary": 66,
    }
    assert (
        sum(
            q["renderable"]
            for e in c.exams.values()
            for p in e["parts"]
            for g in p["groups"]
            for q in g["questions"]
        )
        == 2880
    )
    assert sum(map(len, c.audio.values())) == 288
    cambridge14 = [a for parts in c.audio.values() for a in parts.values() if a["book"] == 14]
    assert len(cambridge14) == 16
    assert all(a["mime_type"] == "audio/mp4" for a in cambridge14)
    assert {c.audio[f"cambridge-12-test-{n:02}"][1]["local_ordinal"] for n in range(5, 9)} == {
        1,
        2,
        3,
        4,
    }
    assert forms("blond(e)") == {"blond", "blonde"}
    assert "17th october" in forms("(the) 17th (of) October")
    assert forms("B") == {"b"}
    for eid in c.exams:
        mode = c.mode(eid)
        if mode == "blocked":
            continue
        snapshot = {"exam": c.exams[eid], "key": c.keys[eid], "mode": mode}
        empty = result_for(snapshot, {})
        assert empty["estimated_band"] is None
        if mode == "ungraded":
            assert empty["correct_count"] is None and all(
                r["correct_answer"] is None for r in empty["questions"]
            )
        if mode == "verified":
            answers = {}
            for k in snapshot["key"]["answers"]:
                if not k["unordered_group"]:
                    answers[k["question_id"]] = sorted(forms(k["official_answer"]))[0]
            for g in snapshot["key"]["unordered_groups"]:
                for n, value in zip(g["question_numbers"], reversed(g["expected_units"])):
                    answers[f"{eid}-q{n:02}"] = value
            scored = result_for(snapshot, answers)
            assert scored["correct_count"] == 40 and scored["estimated_band"] == 9, (eid, scored)
            one = f"{eid}-q01"
            answers[one] = "spellingmistake"
            assert result_for(snapshot, answers)["correct_count"] == 39


def test_owned_lifecycle_snapshots_and_modes(listening):
    service, client, _, _ = listening
    owner, _ = bootstrap(client, "husband")
    other, _ = bootstrap(client, "wife")
    h = headers(owner)
    oh = headers(other)
    assert client.get("/api/v1/listening/exams").status_code == 401
    library = client.get("/api/v1/listening/exams", headers=h).json()
    assert len(library["items"]) == 72
    for eid in ["cambridge-14-test-01", "cambridge-21-test-01", "cambridge-04-test-02"]:
        body = {"event_id": str(uuid4()), "exam_id": eid, "reuse_active": True}
        response = client.post("/api/v1/listening/attempts", headers=h, json=body)
        assert response.status_code == 201, response.text
        started = response.json()
        aid = started["id"]
        base = f"/api/v1/listening/attempts/{aid}"
        assert client.post("/api/v1/listening/attempts", headers=h, json=body).json() == started
        assert "official_answer" not in json.dumps(started) and "relative_path" not in json.dumps(
            {k: v for k, v in started.items() if k != "exam"}
        )
        assert client.get(base, headers=oh).status_code == 404
        assert client.get(base + "/review", headers=h).status_code == 409
        assert client.get(base + "/result", headers=oh).status_code == 404
        uid = client.get("/api/v1/me", headers=h).json()["uid"]

        def same(_):
            return service.create(uid, CreateAttempt(event_id=uuid4(), exam_id=eid)).get("id")

        with ThreadPoolExecutor(max_workers=4) as pool:
            assert set(pool.map(same, range(4))) == {aid}
        qid = eid + "-q01"
        saved_answer = service.catalog.keys[eid]["answers"][0]["explicit_slash_forms"][0]
        event = {
            "event_id": str(uuid4()),
            "expected_version": 0,
            "answers": {qid: saved_answer},
            "state": {
                "displayed_part": 2,
                "current_question": 12,
                "audio_part": 1,
                "playback_seconds": 4.5,
                "marked": [12],
            },
        }
        saved = client.post(base + "/sync", headers=h, json=event)
        assert saved.status_code == 200, saved.text
        assert client.post(base + "/sync", headers=h, json=event).json() == saved.json()
        stale = {**event, "event_id": str(uuid4())}
        assert client.post(base + "/sync", headers=h, json=stale).status_code == 409
        assert (
            client.post(
                base + "/sync", headers=h, json={**event, "answers": {qid: "changed"}}
            ).status_code
            == 409
        )
        resumed = client.get(base, headers=h).json()
        assert (
            resumed["answers"][qid] == saved_answer and resumed["state"]["playback_seconds"] == 4.5
        )
        original = copy.deepcopy(service.catalog.keys[eid])
        service.catalog.keys[eid]["answers"] = []
        finish = {"event_id": str(uuid4()), "expected_version": 1}
        ended = client.post(base + "/submit", headers=h, json=finish)
        assert ended.status_code == 200, ended.text
        service.catalog.keys[eid] = original
        assert client.post(base + "/submit", headers=h, json=finish).json() == ended.json()
        assert (
            client.post(
                base + "/submit", headers=h, json={**finish, "event_id": str(uuid4())}
            ).json()
            == ended.json()
        )
        assert (
            client.post(
                base + "/sync",
                headers=h,
                json={**event, "event_id": str(uuid4()), "expected_version": 2},
            ).status_code
            == 409
        )
        result = client.get(base + "/result", headers=h).json()
        assert result["correct_count"] == 1 and result["graded_count"] == 40
        assert result["label"] == "Listening practice"
        # The existing conversion table starts at 4/40; no lower band is invented.
        assert result["estimated_band"] is None
        assert result["band_table_version"] is not None
        assert client.get(base + "/review", headers=h).json()["exam"]["exam_id"] == eid
        assert client.post(base + "/playback", headers=oh).status_code == 404
    # A new content repair must not weaken the launch gate for broken content.
    broken = service.catalog.exams["cambridge-04-test-01"]["parts"][0]["groups"][0]["questions"][0]
    broken["renderable"] = False
    try:
        blocked = client.post(
            "/api/v1/listening/attempts",
            headers=h,
            json={"exam_id": "cambridge-04-test-01", "event_id": str(uuid4())},
        )
        assert blocked.status_code == 422
    finally:
        broken["renderable"] = True


def test_audio_range_expiry_assets_and_confinement(listening):
    service, client, now, root = listening
    owner, _ = bootstrap(client, "husband")
    h = headers(owner)
    aid = client.post(
        "/api/v1/listening/attempts",
        headers=h,
        json={"event_id": str(uuid4()), "exam_id": "cambridge-14-test-01"},
    ).json()["id"]
    base = f"/api/v1/listening/attempts/{aid}"
    audio = base + "/audio/1"
    assert client.get(audio, headers=h).status_code == 401
    grant = client.post(base + "/playback", headers=h).json()["grant"]
    g = {"X-Playback-Grant": grant}
    response = client.get(audio, headers={**g, "Range": "bytes=10-99"})
    assert response.status_code == 206 and len(response.content) == 90
    assert (
        response.headers["content-range"].startswith("bytes 10-99/")
        and "no-store" in response.headers["cache-control"]
    )
    assert (
        client.head(audio, headers=g).status_code == 200
        and not client.head(audio, headers=g).content
    )
    assert client.get(audio, headers={**g, "Range": "bytes=999999999-"}).status_code == 416
    assert client.get(audio, headers={"X-Playback-Grant": "bad"}).status_code == 401
    assert client.get(base + "/audio/5", headers=g).status_code == 422
    asset = service.get(client.get("/api/v1/me", headers=h).json()["uid"], aid)["exam"]["assets"][
        0
    ]["asset_id"]
    assert client.get(base + "/assets/" + asset, headers=h).status_code == 200
    assert client.get(base + "/assets/asset-private", headers=h).status_code == 404
    m4a = client.post(
        "/api/v1/listening/attempts",
        headers=h,
        json={"exam_id": "cambridge-05-test-01", "event_id": str(uuid4())},
    ).json()
    mbase = f"/api/v1/listening/attempts/{m4a['id']}"
    assert client.get(mbase + "/audio/1", headers=g).status_code == 401
    mg = client.post(mbase + "/playback", headers=h).json()["grant"]
    assert (
        client.head(mbase + "/audio/1", headers={"X-Playback-Grant": mg}).headers["content-type"]
        == "audio/mp4"
    )
    from scripts.listening_media.probe_audio import probe

    record = service.catalog.audio["cambridge-05-test-01"][1]
    technical = probe(root, record)
    assert technical["decode_verified"] and technical["duration"] > 11
    assert not technical["content_mapping_verified"]
    now[0] += timedelta(minutes=16)
    assert client.get(audio, headers=g).status_code == 401
    with pytest.raises(NotFoundError):
        confined(root, "../elsewhere")
    (root / "escape").symlink_to("/etc/hosts")
    with pytest.raises(NotFoundError):
        confined(root, "escape")


@pytest.mark.parametrize(
    ("filename", "source", "stored_mime", "expected_mime"),
    [
        ("fixture.mp3", "fixture.mp3", "audio/mpeg", "audio/mpeg"),
        ("fixture.m4a", "fixture.m4a", "audio/mp4", "audio/mp4"),
        ("mislabeled.mp3", "fixture.m4a", "audio/mpeg", "audio/mp4"),
    ],
)
def test_actual_audio_mime_and_old_snapshot(
    listening, filename, source, stored_mime, expected_mime
):
    from app.modules.listening.models import ListeningAttemptRow

    service, client, _, root = listening
    media = root / filename
    if filename != source:
        media.write_bytes((root / source).read_bytes())
    assert audio_mime(media) == expected_mime
    eid = "cambridge-14-test-01"
    record = service.catalog.audio[eid][1]
    record.update(relative_path=filename, byte_size=media.stat().st_size, mime_type=stored_mime)
    owner, _ = bootstrap(client, "husband")
    h = headers(owner)
    aid = client.post(
        "/api/v1/listening/attempts",
        headers=h,
        json={"event_id": str(uuid4()), "exam_id": eid},
    ).json()["id"]
    # Simulate a catalog correction after an older attempt was persisted.
    record["mime_type"] = expected_mime
    with service.db.session() as session:
        before = copy.deepcopy(session.get(ListeningAttemptRow, aid).snapshot)
    assert before["audio"]["1"]["mime_type"] == stored_mime
    base = f"/api/v1/listening/attempts/{aid}"
    grant = client.post(base + "/playback", headers=h).json()["grant"]
    for method, extra, status in [
        ("GET", {}, 200),
        ("HEAD", {}, 200),
        ("GET", {"Range": "bytes=10-99"}, 206),
        ("HEAD", {"Range": "bytes=10-99"}, 206),
    ]:
        response = client.request(
            method, base + "/audio/1", headers={"X-Playback-Grant": grant, **extra}
        )
        assert response.status_code == status
        assert response.headers["content-type"] == expected_mime
        assert response.headers["accept-ranges"] == "bytes"
        assert "no-store" in response.headers["cache-control"]
        if status == 206:
            assert response.headers["content-range"] == f"bytes 10-99/{media.stat().st_size}"
            assert response.headers["content-length"] == "90"
        assert response.content == (
            b""
            if method == "HEAD"
            else media.read_bytes()[10:100]
            if status == 206
            else media.read_bytes()
        )
    with service.db.session() as session:
        assert session.get(ListeningAttemptRow, aid).snapshot == before


def test_inventory_sniffs_real_containers(listening):
    from scripts.listening_media.import_inventory import parse

    _, _, _, root = listening
    manifest_path = Path(__file__).parents[1] / "app/content/listening_audio_v1/audio_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    lines = []
    for item in manifest["items"]:
        source = root / ("fixture.m4a" if item["book"] in (5, 14) else "fixture.mp3")
        media = root / item["relative_path"]
        media.parent.mkdir(parents=True, exist_ok=True)
        media.symlink_to(source)
        lines.append(f"{item['relative_path']}\t{source.stat().st_size}")
    inventory = root / "inventory.tsv"
    inventory.write_text("\n".join(lines) + "\n")
    imported = parse(inventory, root)
    assert len(imported["items"]) == 288
    for item in imported["items"]:
        assert item["mime_type"] == ("audio/mp4" if item["book"] in (5, 14) else "audio/mpeg")
    # A familiar suffix or an incomplete signature must not become a MIME fallback.
    for content in (b"not mp3", b"ID3\x04\x00\x00\x7f\x7f\x7f\x7f", b"\x00\x00\x00\x20ftypM4A "):
        invalid = root / "invalid.mp3"
        invalid.write_bytes(content)
        with pytest.raises(NotFoundError):
            audio_mime(invalid)


def test_simultaneous_saves_and_grading_rules(listening):
    service, client, _, _ = listening
    owner, _ = bootstrap(client, "husband")
    h = headers(owner)
    row = client.post(
        "/api/v1/listening/attempts",
        headers=h,
        json={"exam_id": "cambridge-14-test-01", "event_id": str(uuid4())},
    ).json()
    base = f"/api/v1/listening/attempts/{row['id']}"

    def edit(value):
        return client.post(
            base + "/sync",
            headers=h,
            json={
                "event_id": str(uuid4()),
                "expected_version": 0,
                "answers": {row["exam_id"] + "-q01": value},
                "state": row["state"],
            },
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(edit, ["first", "second"]))
    assert sorted(r.status_code for r in responses) == [200, 409]
    assert client.get(base, headers=h).json()["version"] == 1
    c = service.catalog
    eid = "cambridge-09-test-01"
    snap = {"exam": c.exams[eid], "key": c.keys[eid], "mode": c.mode(eid)}
    for value, expected in [("plants fish", True), ("fish plants", True), ("plants", False)]:
        result = result_for(snap, {eid + "-q33": value})
        assert (
            next(r for r in result["questions"] if r["question_number"] == 33)["correct"]
            is expected
        )
    eid = "cambridge-20-test-04"
    snap = {"exam": c.exams[eid], "key": c.keys[eid], "mode": c.mode(eid)}
    for value in ["125", "one hundred and twenty-five"]:
        result = result_for(snap, {eid + "-q02": value})
        assert next(r for r in result["questions"] if r["question_number"] == 2)["correct"]
    eid = "cambridge-14-test-01"
    snap = {"exam": c.exams[eid], "key": c.keys[eid], "mode": c.mode(eid)}
    result = result_for(snap, {eid + "-q11": "A", eid + "-q12": "A"})
    assert result["correct_count"] == 1


def test_existing_firebase_identity_access(listening, monkeypatch):
    from app.core.config import get_settings
    from app.firebase_admin_cli import bind_identity

    service, client, _, _ = listening
    owner, _ = bootstrap(client, "husband")
    other, _ = bootstrap(client, "wife")
    get_settings().firebase_auth_enabled = True
    monkeypatch.setattr("app.core.auth.verify_firebase_token", lambda token: token.split(".")[1])
    with service.db.session() as session:
        bind_identity(session, "firebase-listening-A", owner["profile"]["uid"])
        bind_identity(session, "firebase-listening-B", other["profile"]["uid"])
    a = {"Authorization": "Bearer header.firebase-listening-A.signature"}
    b = {"Authorization": "Bearer header.firebase-listening-B.signature"}
    get_settings().legacy_auth_enabled = False
    assert client.get("/api/v1/listening/exams", headers=headers(owner)).status_code == 401
    assert client.get("/api/v1/listening/exams", headers=a).status_code == 200
    created = client.post(
        "/api/v1/listening/attempts",
        headers=a,
        json={"exam_id": "cambridge-14-test-01", "event_id": str(uuid4())},
    )
    assert created.status_code == 201
    base = f"/api/v1/listening/attempts/{created.json()['id']}"
    assert client.get(base, headers=a).status_code == 200
    assert client.get(base, headers=b).status_code == 404
    assert client.post(base + "/playback", headers=b).status_code == 404
    assert client.post(base + "/playback", headers=a).status_code == 200


def test_printed_postcodes_are_single_exact_answer_units():
    catalog = ListeningCatalog()
    for eid, number, correct in [
        ("cambridge-10-test-02", 3, "GT8 2LC"),
        ("cambridge-11-test-02", 3, "PE9 7QT"),
        ("cambridge-12-test-08", 8, "DG7 4PH"),
        ("cambridge-18-test-01", 1, "DW30 7YZ"),
    ]:
        snapshot = {"exam": catalog.exams[eid], "key": catalog.keys[eid], "mode": catalog.mode(eid)}
        qid = f"{eid}-q{number:02}"
        row = next(
            r for r in result_for(snapshot, {qid: correct})["questions"] if r["question_id"] == qid
        )
        assert row["correct"] is True
        row = next(
            r
            for r in result_for(snapshot, {qid: correct + "x"})["questions"]
            if r["question_id"] == qid
        )
        assert row["correct"] is False


def test_all_72_exam_numbers_keys_and_declared_grading_issues():
    catalog = ListeningCatalog()
    issues = {}
    for eid, exam in catalog.exams.items():
        numbers = [
            q["question_number"] for p in exam["parts"] for g in p["groups"] for q in g["questions"]
        ]
        assert sorted(numbers) == list(range(1, 41))
        keys = catalog.keys[eid]["answers"]
        assert sorted(k["question_number"] for k in keys) == list(range(1, 41))
        assert len({k["question_id"] for k in keys}) == 40
        snapshot = {
            "exam": exam,
            "key": catalog.keys[eid],
            "mode": catalog.mode(eid),
            "grading_policy": "practice-v2",
        }
        result = result_for(snapshot, {})
        issues.update(result["grading_issues"])
        qmap = questions(exam)
        sample = {}
        for key in keys:
            if key["unordered_group"] or key["question_id"] in result["grading_issues"]:
                continue
            try:
                accepted = forms(key["official_answer"])
            except ValueError:
                # Explicit multi-component rules are handled below.
                continue
            sample[key["question_id"]] = next(
                form
                for form in accepted
                if official_limit(form, qmap[key["question_id"]][2], accepted)
            )
        for group in catalog.keys[eid]["unordered_groups"]:
            for n, unit in zip(group["question_numbers"], group["expected_units"], strict=True):
                sample[f"{eid}-q{n:02}"] = sorted(forms(unit))[0]
        for rule in catalog.keys[eid]["within_position_rules"]:
            sample[rule["question_id"]] = " ".join(
                component["explicit_slash_forms"][0] for component in rule["components"]
            )
        scored = result_for(snapshot, sample)
        assert scored["correct_count"] == scored["graded_count"], (eid, scored)
        if not scored["grading_issues"]:
            assert scored["graded_count"] == 40 and scored["estimated_band"] == 9
        else:
            assert scored["estimated_band"] is None
        # Editorial metadata cannot change new practice grading, including ungraded.
        for mode in ("verified", "preliminary", "ungraded"):
            assert (
                result_for({**snapshot, "mode": mode}, sample)["correct_count"]
                == scored["correct_count"]
            )
            assert (
                result_for({**snapshot, "mode": mode}, sample)["estimated_band"]
                == scored["estimated_band"]
            )
    assert set(issues) == {
        "cambridge-06-test-01-q07",
        "cambridge-06-test-01-q19",
        "cambridge-11-test-01-q02",
    }


def test_numeric_grouping_is_not_an_ambiguous_answer_list():
    assert forms("1,500 / 1500") == {"1,500", "1500"}
    assert forms("3,000-4,000 / 3000-4000") == {"3,000-4,000", "3000-4000"}
    assert forms("approximately 2,000 / about 2,000") == {"approximately 2,000", "about 2,000"}
    with pytest.raises(ValueError):
        forms("Monday, Thursday")
    with pytest.raises(ValueError):
        forms("10(am), 4.30(pm)")


def test_all_72_start_and_legacy_attempts_remain_unchanged(listening):
    from app.modules.listening.models import ListeningAttemptRow

    service, client, _, _ = listening
    owner, _ = bootstrap(client, "husband")
    h = headers(owner)
    ids = []
    for eid in service.catalog.exams:
        response = client.post(
            "/api/v1/listening/attempts", headers=h, json={"event_id": str(uuid4()), "exam_id": eid}
        )
        assert response.status_code == 201, (eid, response.text)
        ids.append(response.json()["id"])
    assert len(set(ids)) == 72
    # Simulate an existing in-progress preliminary snapshot without the new policy.
    aid = ids[0]
    with service.db.session() as session:
        row = session.get(ListeningAttemptRow, aid)
        snapshot = copy.deepcopy(row.snapshot)
        assert snapshot.pop("grading_policy") == "practice-v2"
        row.snapshot = snapshot
    base = f"/api/v1/listening/attempts/{aid}"
    finished = client.post(
        base + "/submit", headers=h, json={"event_id": str(uuid4()), "expected_version": 0}
    )
    assert finished.status_code == 200
    stored = client.get(base + "/result", headers=h).json()
    assert stored["label"] == "Preliminary result" and stored["band_table_version"] is None
    with service.db.session() as session:
        before = copy.deepcopy(session.get(ListeningAttemptRow, aid).result)
    # Reopening/re-submitting never recalculates a persisted result.
    assert (
        client.post(
            base + "/submit", headers=h, json={"event_id": str(uuid4()), "expected_version": 1}
        ).status_code
        == 200
    )
    assert client.get(base + "/result", headers=h).json() == stored
    assert (
        client.get(base + "/review", headers=h).json()["correct_count"] == stored["correct_count"]
    )
    with service.db.session() as session:
        assert session.get(ListeningAttemptRow, aid).result == before
        assert session.get(ListeningAttemptRow, aid).snapshot == snapshot
