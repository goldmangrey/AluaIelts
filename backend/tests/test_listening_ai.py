# ruff: noqa: F811
import copy
import json
from pathlib import Path
from uuid import uuid4

import pytest
from test_household_bootstrap import bootstrap, headers, postgres_url, system  # noqa: F401
from test_listening import listening  # noqa: F401

from app.core.config import get_settings
from app.modules.listening import ai_review as ai
from app.modules.listening.ai_review import AIReview, transcript


def test_transcript_coverage_qa_and_source_mapping():
    from app.modules.listening.catalog import ListeningCatalog

    catalog = ListeningCatalog()
    docs = []
    for eid, exam in catalog.exams.items():
        for p in range(1, 5):
            doc = transcript(exam["book"], exam["printed_test_number"], p)
            assert doc and doc["segments"]
            assert (
                Path(catalog.audio[eid][p]["relative_path"]).stem == Path(doc["source_audio"]).stem
            )
            docs.append(doc)
    assert len(docs) == 288 and sum(not d["complete"] for d in docs) == 0
    assert transcript(5, 1, 2)["source_audio"] == "IELTS05-Test 2-Section 1.m4a"
    assert transcript(14, 2, 4)["segments"][-1]["end"] == 511.46
    assert len(transcript(14, 2, 4)["segments"]) == 55
    assert all(transcript(21, t, p)["complete"] for t in range(1, 5) for p in range(1, 5))
    assert transcript(12, 5, 1)["test"] == 5


def sample():
    return {
        "part": 2,
        "duration": 12,
        "segments": [
            {"id": f"seg-{i:04}", "start": i, "end": i + 0.8, "text": t}
            for i, t in enumerate(
                ["The fee is forty pounds.", "Not fourteen pounds.", "That is for students."], 1
            )
        ],
    }


def output():
    return {
        "what_happened": "В записи называют сорок фунтов.",
        "why": "В ответе указана другая сумма.",
        "next_time": "Слушайте окончание числительного.",
        "segment_ids": ["seg-0001", "seg-0002"],
        "quote": "The fee is forty pounds. Not fourteen pounds.",
    }


def test_evidence_is_server_calculated_and_bad_ids_quotes_are_not_evidence():
    c = sample()
    result = AIReview.validate(c, output())
    assert result["evidence"]["clip_start"] == 0
    assert result["evidence"]["clip_end"] == 3.8  # cap to the reviewed transcript boundary
    for patch in [
        {"segment_ids": ["invented"]},
        {"quote": "Invented quote"},
        {"segment_ids": ["seg-0002", "seg-0001"]},
        {"segment_ids": ["seg-0001", "seg-0003"]},
        {"segment_ids": ["seg-0001", "seg-0001"]},
    ]:
        safe = AIReview.validate(c, {**output(), **patch})
        assert not safe["evidence"]["available"] and safe["evidence"]["clip_start"] is None
        assert "сорок" not in safe["what_happened"]
    with pytest.raises(ai.ExternalServiceError):
        AIReview.validate(c, {**output(), "clip_start": 999})
    c["duration"] = 1
    assert not AIReview.validate(c, output())["evidence"]["available"]


def test_completed_ownership_context_cache_rate_and_snapshot_preservation(
    listening,
    monkeypatch,
    tmp_path,  # noqa: F811
):
    service, client, _, _ = listening
    owner, _ = bootstrap(client, "husband")
    other, _ = bootstrap(client, "wife")
    h = headers(owner)
    created = client.post(
        "/api/v1/listening/attempts",
        headers=h,
        json={"event_id": str(uuid4()), "exam_id": "cambridge-04-test-01"},
    ).json()
    aid = created["id"]
    base = f"/api/v1/listening/attempts/{aid}"
    assert client.post(base + "/ai-review/1").status_code == 401
    assert client.get(base + "/ai-review/1/context", headers=headers(other)).status_code == 404
    assert client.get(base + "/ai-review/1/context", headers=h).status_code == 409
    saved = client.post(
        base + "/sync",
        headers=h,
        json={
            "event_id": str(uuid4()),
            "expected_version": 0,
            "answers": {"cambridge-04-test-01-q01": "wrong"},
            "state": created["state"],
        },
    )
    assert saved.status_code == 200
    assert (
        client.post(
            base + "/submit", headers=h, json={"event_id": str(uuid4()), "expected_version": 1}
        ).status_code
        == 200
    )
    before = client.get(base + "/review", headers=h).json()
    original = copy.deepcopy(transcript(4, 1, 1))
    original["segments"] = sample()["segments"]
    original["source_audio"] = Path(
        service.catalog.audio["cambridge-04-test-01"][1]["relative_path"]
    ).name
    monkeypatch.setattr(ai, "transcript", lambda *_: original)
    monkeypatch.setattr(ai, "probe_duration", lambda *_: 12)
    monkeypatch.setattr(get_settings(), "listening_ai_cache_root", str(tmp_path / "cache"))
    ctx = client.get(base + "/ai-review/1/context", headers=h).json()
    assert ctx["correct_answer"] and ctx["user_answer"] == "wrong"
    calls = []

    class Response:
        status_code = 200

        def json(self):
            return {"fingerprint": ctx["fingerprint"], "review": output()}

    def provider(*args, **kwargs):
        calls.append(kwargs)
        return Response()

    monkeypatch.setattr(ai.httpx, "post", provider)
    first = client.post(base + "/ai-review/1", headers=h)
    assert first.status_code == 200, first.text
    assert first.json()["evidence"]["available"]
    assert client.post(base + "/ai-review/1", headers=h).json() == first.json()
    assert len(calls) == 1 and set(calls[0]["json"]) == {"attempt_id", "question_number"}
    assert client.get(base + "/review", headers=h).json() == before
    assert client.post(base + "/ai-review/2", headers=h).status_code == 422
    # A changed QA revision invalidates the cache and does not call AI for incomplete data.
    original["complete"] = False
    incomplete = client.post(base + "/ai-review/1", headers=h).json()
    assert incomplete["evidence"]["reason"] == "transcript_incomplete" and len(calls) == 1
    original["complete"] = True
    original["source_audio"] = "IELTS04-Test 2-Section 1.mp3"
    assert (
        client.post(base + "/ai-review/1", headers=h).json()["evidence"]["reason"]
        == "audio_identity_mismatch"
    )
    # Rate limit is scoped to the verified owner and does not alter attempts.
    uid = ctx["learner_id"]
    ai._usage[uid] = {"until": ai.time.monotonic() + 60, "count": 6, "busy": False}
    original["text"] += " changed"
    assert client.post(base + "/ai-review/1", headers=h).status_code == 429
    assert client.get(base + "/review", headers=h).json() == before


def test_invalid_transcript_never_becomes_evidence(tmp_path, monkeypatch):
    root = tmp_path / "transcripts"
    root.mkdir()
    path = root / "cambridge-04-test-01-part-01.json"
    path.write_text(
        json.dumps(
            {
                "book": 4,
                "test": 1,
                "section": 1,
                "segments": [{"id": "x", "start": -1, "end": 2, "text": "bad"}],
            }
        )
    )
    (root / "manifest.json").write_text(
        json.dumps({"items": [{"file": path.name, "sha256": "bad"}]})
    )
    transcript.cache_clear()
    monkeypatch.setattr(ai, "TRANSCRIPTS", root)
    assert transcript(4, 1, 1) is None
    transcript.cache_clear()


def test_ai_does_not_claim_to_know_student_attention():
    c = sample()
    response = AIReview.validate(
        c, {**output(), "why": "Ученик сфокусировался на fourteen и не учёл отрицание."}
    )
    assert response["evidence"]["available"]
    assert "сфокусировался" not in response["why"]
    assert "не совпадает с ключом" in response["why"]


def test_duration_reader_supports_real_mp3_and_m4a(listening):
    service, _, _, root = listening
    for filename in ("fixture.mp3", "fixture.m4a"):
        path = root / filename
        stat = path.stat()
        duration = ai.probe_duration(str(path), stat.st_size, stat.st_mtime_ns)
        assert duration is not None and 11.5 < duration < 12.5
    # Existing Cambridge 14 files can contain M4A despite their .mp3 suffix.
    disguised = root / "disguised.mp3"
    disguised.write_bytes((root / "fixture.m4a").read_bytes())
    stat = disguised.stat()
    duration = ai.probe_duration(str(disguised), stat.st_size, stat.st_mtime_ns)
    assert duration is not None and 11.5 < duration < 12.5
    corrupt = root / "corrupt.mp3"
    corrupt.write_bytes(b"not an audio file")
    assert (
        ai.probe_duration(str(corrupt), corrupt.stat().st_size, corrupt.stat().st_mtime_ns) is None
    )


def test_legacy_cambridge05_audio_is_not_silently_remapped(listening, monkeypatch, tmp_path):
    from app.modules.listening.models import ListeningAttemptRow

    service, client, _, _ = listening
    owner, _ = bootstrap(client, "husband")
    h = headers(owner)
    created = client.post(
        "/api/v1/listening/attempts",
        headers=h,
        json={"event_id": str(uuid4()), "exam_id": "cambridge-05-test-01"},
    ).json()
    aid = created["id"]
    base = f"/api/v1/listening/attempts/{aid}"
    client.post(
        base + "/sync",
        headers=h,
        json={
            "event_id": str(uuid4()),
            "expected_version": 0,
            "answers": {"cambridge-05-test-01-q11": "wrong"},
            "state": created["state"],
        },
    ).raise_for_status()
    client.post(
        base + "/submit", headers=h, json={"event_id": str(uuid4()), "expected_version": 1}
    ).raise_for_status()
    with service.db.session() as session:
        row = session.get(ListeningAttemptRow, aid)
        legacy = copy.deepcopy(row.snapshot)
        legacy["audio"]["2"]["relative_path"] = "legacy/IELTS05-Test 1-Section 2.m4a"
        row.snapshot = legacy
    before = client.get(base + "/review", headers=h).json()
    monkeypatch.setattr(get_settings(), "listening_ai_cache_root", str(tmp_path / "legacy-cache"))

    def forbidden(*_args, **_kwargs):
        pytest.fail("Misidentified legacy audio must never call AI")

    monkeypatch.setattr(ai.httpx, "post", forbidden)
    response = client.post(base + "/ai-review/11", headers=h)
    assert response.status_code == 200, response.text
    assert response.json()["evidence"]["reason"] == "audio_identity_mismatch"
    assert client.get(base + "/review", headers=h).json() == before
    with service.db.session() as session:
        assert session.get(ListeningAttemptRow, aid).snapshot == legacy
