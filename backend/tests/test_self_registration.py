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
from app.core.firebase_auth import VerifiedFirebaseIdentity
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
    monkeypatch.setattr(
        registration,
        "verify_firebase_identity",
        lambda token: VerifiedFirebaseIdentity(verify(token)),
    )
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

    monkeypatch.setattr(registration, "verify_firebase_identity", invalid)
    assert register(client, "forged").status_code == 401


def test_registration_budgets_and_existing_profile_retry(signup):
    _, client = signup
    get_settings().registration_creations_per_hour = 1
    assert register(client, "A").status_code == 200
    limited = register(client, "B")
    assert limited.status_code == 429
    assert 1 <= int(limited.headers["retry-after"]) <= 3600
    assert limited.headers["cache-control"] == "no-store"
    assert register(client, "A").status_code == 200
    get_settings().registration_requests_per_minute = 1
    assert register(client, "A").status_code == 429
    get_settings().self_registration_enabled = False
    assert register(client, "C").status_code == 503
    assert client.get("/api/v1/me", headers=headers("A")).status_code == 200


def test_verified_google_same_ip_bypasses_only_global_creation_cap(signup, monkeypatch):
    db, client = signup
    settings = get_settings()
    settings.registration_creations_per_hour = 1
    settings.registration_requests_per_minute = 2
    assert register(client, "unverified").status_code == 200
    monkeypatch.setattr(
        registration,
        "verify_firebase_identity",
        lambda token: VerifiedFirebaseIdentity(token.split(".")[1], verified_google=True),
    )
    # TestClient uses one peer for every user. Forged proxy headers cannot affect UID budgets.
    for uid in ["google-A", "google-B", "google-C"]:
        for _ in range(3):
            missing = client.get("/api/v1/me", headers=headers(uid))
            assert missing.status_code == 403
            assert missing.json()["error"]["code"] == "identity_not_allowed"
        first = client.post(
            "/api/v1/auth/register",
            headers={**headers(uid), "X-Forwarded-For": "1.2.3.4", "CF-Connecting-IP": "1.2.3.4"},
            json={},
        )
        assert first.status_code == 200
        assert register(client, uid).json()["uid"] == first.json()["uid"]
        assert client.get("/api/v1/me", headers=headers(uid)).status_code == 200
        abuse = register(client, uid)
        assert abuse.status_code == 429
        assert 1 <= int(abuse.headers["retry-after"]) <= 60
    with db.session() as session:
        assert session.scalar(select(func.count()).select_from(LearnerProfileRow)) == 4


def test_uid_budget_cannot_be_evaded_by_token_rotation(signup, monkeypatch):
    _, client = signup
    get_settings().registration_requests_per_minute = 1
    monkeypatch.setattr(
        registration,
        "verify_firebase_identity",
        lambda _: VerifiedFirebaseIdentity("same-uid", True),
    )
    assert register(client, "token-one").status_code == 200
    assert register(client, "token-two").status_code == 429


def test_token_budget_expires_and_is_bounded(monkeypatch):
    get_settings().registration_requests_per_minute = 1
    registration._verification_times.clear()
    monkeypatch.setattr(registration, "monotonic", lambda: 100)
    registration.consume_verification_budget("token:one")
    with pytest.raises(registration.AluaError) as error:
        registration.consume_verification_budget("token:one")
    assert error.value.headers["Retry-After"] == "60"
    monkeypatch.setattr(registration, "monotonic", lambda: 160)
    registration.consume_verification_budget("token:one")
    for n in range(10001):
        registration.consume_verification_budget(f"uid:{n}")
    assert len(registration._verification_times) == 10000
    registration._verification_times.clear()
    get_settings.cache_clear()


def test_google_multi_uid_creation_flood_still_throttles(signup, monkeypatch):
    db, client = signup
    get_settings().registration_google_creations_per_hour = 3
    monkeypatch.setattr(
        registration,
        "verify_firebase_identity",
        lambda token: VerifiedFirebaseIdentity(token.split(".")[1], True),
    )
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda n: register(client, f"flood-{n}"), range(6)))
    assert sum(r.status_code == 200 for r in results) == 3
    assert sum(r.status_code == 429 for r in results) == 3
    assert all("retry-after" in r.headers for r in results if r.status_code == 429)
    with db.session() as session:
        assert session.scalar(select(func.count()).select_from(FirebaseIdentityRow)) == 3
    # Creation ceiling cannot break retry/recovery of profiles already provisioned.
    winner = next(n for n, r in enumerate(results) if r.status_code == 200)
    assert register(client, f"flood-{winner}").status_code == 200


def test_google_firebase_boundary_to_registration_and_me(signup, monkeypatch):
    """Only the external Firebase SDK is mocked; real verification/routing/DB run."""
    from firebase_admin import auth

    from app.core.firebase_auth import verify_firebase_identity, verify_firebase_token

    db, client = signup
    get_settings().registration_creations_per_hour = 1
    monkeypatch.setattr(registration, "verify_firebase_identity", verify_firebase_identity)
    monkeypatch.setattr("app.core.auth.verify_firebase_token", verify_firebase_token)
    monkeypatch.setattr("app.core.firebase_auth.firebase_app", lambda: object())

    def sdk_verify(token, *, app, check_revoked):
        assert check_revoked is True
        uid = token.split(".")[1]
        if uid == "disabled":
            raise auth.UserDisabledError("disabled")
        if uid == "invalid":
            raise auth.InvalidIdTokenError("invalid signature")
        return {
            "uid": uid,
            "email": f"{uid}@example.org",
            "email_verified": uid != "unverified",
            "firebase": {"sign_in_provider": "google.com"},
        }

    monkeypatch.setattr(auth, "verify_id_token", sdk_verify)
    for uid in ["google-1", "google-2", "google-3"]:
        assert client.get("/api/v1/me", headers=headers(uid)).status_code == 403
        response = register(client, uid)
        assert response.status_code == 200
        assert register(client, uid).json() == response.json()
        # Existing sign-in immediately resolves the same profile, no provisioning.
        for _ in range(2):
            me = client.get("/api/v1/me", headers=headers(uid))
            assert me.status_code == 200
            assert me.json()["uid"] == response.json()["uid"]
    assert register(client, "unverified").status_code == 429
    assert register(client, "disabled").status_code == 401
    assert register(client, "invalid").status_code == 401
    with db.session() as session:
        assert session.scalar(select(func.count()).select_from(LearnerProfileRow)) == 3
        assert session.scalar(select(func.count()).select_from(FirebaseIdentityRow)) == 3
