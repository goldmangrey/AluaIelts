"""Web safety additions against the existing disposable PostgreSQL fixture only."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

from test_household_bootstrap import bootstrap, headers, postgres_url, system  # noqa: F401

from app.modules.reading.catalog import get_catalog
from app.modules.reading.repository import ReadingRepository
from app.modules.reading.schemas import CreateAttempt
from app.modules.reading.service import ReadingService, utcnow

EID = "cambridge-18-test-01"


def test_reuse_active_cross_device_and_legacy_compatibility(system):  # noqa: F811
    db, client, _ = system
    owner, _ = bootstrap(client, "husband")
    h = headers(owner)
    # Existing HTTP auth setup also proves the new flag is accepted by the router.
    payload = {"event_id": str(uuid4()), "exam_id": EID, "mode": "full_exam", "reuse_active": True}
    first = client.post("/api/v1/reading/attempts", headers=h, json=payload)
    assert first.status_code == 201, first.text
    aid = first.json()["id"]
    # Derive the same learner scope from the authenticated profile, not Firebase UID.
    uid = client.get("/api/v1/me", headers=h).json()["uid"]
    service = ReadingService(ReadingRepository(db), get_catalog())
    def create(_):
        return service.create(uid, CreateAttempt(event_id=uuid4(), exam_id=EID,
                              mode="full_exam", reuse_active=True))["id"]
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert set(pool.map(create, range(8))) == {aid}
    assert client.post("/api/v1/reading/attempts", headers=h, json=payload).json()["id"] == aid
    # Opt-in does not change older clients that intentionally create a new attempt.
    legacy = client.post("/api/v1/reading/attempts", headers=h,
                         json={"event_id": str(uuid4()), "exam_id": EID, "mode": "full_exam"})
    assert legacy.status_code == 201 and legacy.json()["id"] != aid


def test_reuse_expires_old_attempt_and_terminal_results_are_owned(system):  # noqa: F811
    db, client, _ = system
    owner, _ = bootstrap(client, "husband")
    h = headers(owner)
    uid = client.get("/api/v1/me", headers=h).json()["uid"]
    now = utcnow()
    service = ReadingService(ReadingRepository(db), get_catalog(), clock=lambda: now)
    request = CreateAttempt(event_id=uuid4(), exam_id=EID, mode="full_exam", reuse_active=True)
    first = service.create(uid, request)
    now += timedelta(seconds=3601)
    # Deadline is enforced when any lifecycle operation observes it, without React.
    second = service.create(uid, request.model_copy(update={"event_id": uuid4()}))
    assert second["id"] != first["id"]
    ended = service.get(uid, first["id"])
    assert ended["status"] == "expired"
    result = service.result(uid, first["id"])
    assert result["raw_score"] == 0 and result["total_questions"] == 40
    assert service.result(uid, first["id"]) == result
    other, _ = bootstrap(client, "wife")
    response = client.get(f'/api/v1/reading/attempts/{first["id"]}/result', headers=headers(other))
    assert response.status_code == 404
