# ruff: noqa: F811
"""Registration against disposable PostgreSQL; Firebase trust boundary is mocked."""

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from test_household_bootstrap import bootstrap, postgres_url, system  # noqa: F401

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError
from app.db.models import FirebaseIdentityRow, HouseholdProfileRow, LearnerProfileRow
from app.modules.registration import router as registration


def headers(uid):
    return {"Authorization": f"Bearer signed.{uid}.token"}


@pytest.fixture
def signup(system, monkeypatch):
    db, client, _ = system
    get_settings().firebase_auth_enabled = True
    get_settings().self_registration_enabled = True
    registration._verification_times.clear()
    verify = lambda token: token.split(".")[1]  # noqa: E731
    monkeypatch.setattr(registration, "verify_firebase_token", verify)
    monkeypatch.setattr("app.core.auth.verify_firebase_token", verify)
    return db, client


def register(client, uid, name="New learner"):
    return client.post("/api/v1/auth/register", headers=headers(uid), json={"display_name": name})


def test_signup_idempotency_concurrency_and_old_household_unchanged(signup):
    db, client = signup
    bootstrap(client, "husband")
    with db.session() as session:
        old = [(r.learner_id, r.payload) for r in session.scalars(select(LearnerProfileRow))]
        roles = [(r.role, r.learner_id) for r in session.scalars(select(HouseholdProfileRow))]
    with ThreadPoolExecutor(max_workers=8) as pool:
        responses = list(pool.map(lambda _: register(client, "new-A"), range(8)))
    assert all(r.status_code == 200 for r in responses), [r.text for r in responses]
    ids = {r.json()["uid"] for r in responses}
    assert len(ids) == 1
    new_id = ids.pop()
    assert new_id not in {uid for uid, _ in old}
    assert responses[0].headers["cache-control"] == "no-store"
    # A retry is not an update and cannot rename a pre-existing learner.
    assert register(client, "new-A", "Overwrite").json()["display_name"] == "New learner"
    assert client.get("/api/v1/me", headers=headers("new-A")).json()["uid"] == new_id
    with db.session() as session:
        assert session.scalar(select(func.count()).select_from(LearnerProfileRow)) == 3
        assert session.get(FirebaseIdentityRow, "new-A").learner_id == new_id
        assert [
            (r.role, r.learner_id) for r in session.scalars(select(HouseholdProfileRow))
        ] == roles
        for uid, payload in old:
            assert session.get(LearnerProfileRow, uid).payload == payload


def test_recovery_is_atomic_and_retry_creates_once(signup, monkeypatch):
    db, client = signup
    from sqlalchemy.orm import Session

    original = Session.flush

    def failed_mapping(session, *args, **kwargs):
        if any(isinstance(row, FirebaseIdentityRow) for row in session.new):
            raise OperationalError("simulated unavailable DB", {}, Exception("test outage"))
        return original(session, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Session, "flush", failed_mapping)
        assert register(client, "recover").status_code == 503
    with db.session() as session:
        assert session.scalar(select(func.count()).select_from(LearnerProfileRow)) == 0
        assert session.scalar(select(func.count()).select_from(FirebaseIdentityRow)) == 0
    first = register(client, "recover")
    assert first.status_code == 200
    assert register(client, "recover").json() == first.json()


def test_distinct_standalone_learners_and_learning_apis(signup):
    db, client = signup
    a = register(client, "A").json()
    b = register(client, "B").json()
    assert a["uid"] != b["uid"]
    with db.session() as session:
        assert session.scalar(select(func.count()).select_from(HouseholdProfileRow)) == 0
    for uid in ["A", "B"]:
        for path in [
            "/api/v1/me",
            "/api/v1/reading/books",
            "/api/v1/partner/status",
            "/api/v1/vocabulary",
            "/api/v1/grammar",
            "/api/v1/curriculum/me",
            "/api/v1/progress",
            "/api/v1/study/today",
        ]:
            response = client.get(path, headers=headers(uid))
            assert response.status_code == 200, (path, response.text)
    attempt = client.post(
        "/api/v1/reading/attempts",
        headers=headers("A"),
        json={"event_id": str(uuid4()), "exam_id": "cambridge-18-test-01", "mode": "full_exam"},
    )
    assert attempt.status_code in (200, 201), attempt.text
    aid = attempt.json()["id"]
    assert client.get(f"/api/v1/reading/attempts/{aid}", headers=headers("B")).status_code == 404
    assert (
        client.put(
            f"/api/v1/reading/attempts/{aid}/answers/question-1",
            headers=headers("B"),
            json={"event_id": str(uuid4()), "expected_version": 0, "answer": "A"},
        ).status_code
        == 404
    )
    # Vocabulary/SRS study data uses the same authenticated learner boundary.
    assert (
        client.get(
            "/api/v1/study/today", headers=headers("B"), params={"learner_id": a["uid"]}
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/v1/study/actions",
            headers=headers("B"),
            json={
                "learner_id": a["uid"],
                "event_id": str(uuid4()),
                "item_id": "word",
                "action": "known",
            },
        ).status_code
        == 409
    )
    assert client.post("/api/v1/bootstrap", json={}).status_code == 404


def test_reject_identity_injection_invalid_tokens_and_legacy(signup, monkeypatch):
    _, client = signup
    for field in ["learner_id", "firebase_uid", "email", "password", "role"]:
        assert (
            client.post(
                "/api/v1/auth/register",
                headers=headers("A"),
                json={field: "foreign", "display_name": "Name"},
            ).status_code
            == 422
        )
    assert client.post("/api/v1/auth/register", json={}).status_code == 401
    assert (
        client.post(
            "/api/v1/auth/register", headers={"Authorization": "Bearer alua_dev_opaque"}, json={}
        ).status_code
        == 401
    )

    def invalid(_):
        raise UnauthorizedError("Invalid signature")

    monkeypatch.setattr(registration, "verify_firebase_token", invalid)
    assert register(client, "forged").status_code == 401


def test_registration_budgets_and_existing_profile_retry(signup):
    _, client = signup
    get_settings().registration_creations_per_hour = 1
    assert register(client, "A").status_code == 200
    assert register(client, "B").status_code == 429
    assert register(client, "A").status_code == 200
    get_settings().registration_requests_per_minute = 1
    assert register(client, "A").status_code == 429
    get_settings().self_registration_enabled = False
    assert register(client, "C").status_code == 503
    assert client.get("/api/v1/me", headers=headers("A")).status_code == 200
