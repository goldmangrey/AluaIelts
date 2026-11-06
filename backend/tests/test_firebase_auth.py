# ruff: noqa: F811
"""Real temporary PostgreSQL + mocked Firebase verification; never a production identity."""

from uuid import uuid4

import pytest
from firebase_admin import auth
from sqlalchemy import func, select
from test_household_bootstrap import bootstrap, headers, postgres_url, system  # noqa: F401

from app.core.exceptions import ExternalServiceError, UnauthorizedError
from app.db.models import FirebaseIdentityRow, LearnerProfileRow
from app.firebase_admin_cli import bind_identity


def firebase_headers(uid):
    return {"Authorization": f"Bearer header.{uid}.signature"}


def test_mapping_dual_auth_and_isolation(system, monkeypatch):
    db, client, _ = system
    a, _ = bootstrap(client, "husband")
    b, _ = bootstrap(client, "wife")
    from app.core.config import get_settings

    get_settings().firebase_auth_enabled = True
    monkeypatch.setattr("app.core.auth.verify_firebase_token", lambda token: token.split(".")[1])
    with db.session() as session:
        bind_identity(session, "firebaseA", a["profile"]["uid"])
        bind_identity(session, "firebaseA", a["profile"]["uid"])  # idempotent
        bind_identity(session, "firebaseB", b["profile"]["uid"])
    with pytest.raises(ValueError), db.session() as session:
        bind_identity(session, "firebaseA", b["profile"]["uid"])
    with pytest.raises(ValueError), db.session() as session:
        bind_identity(session, "newUID", "missing-learner")
    for uid, device in [("firebaseA", a), ("firebaseB", b)]:
        response = client.get("/api/v1/me", headers=firebase_headers(uid))
        assert response.status_code == 200, response.text
        assert response.json()["uid"] == device["profile"]["uid"]
        assert client.get("/api/v1/me", headers=headers(device)).status_code == 200
    assert client.get("/api/v1/me", headers=firebase_headers("unmapped")).status_code == 403
    assert client.post("/api/v1/bootstrap", json={}).status_code == 404
    started = client.post(
        "/api/v1/reading/attempts",
        headers=firebase_headers("firebaseA"),
        json={"exam_id": "cambridge-18-test-01", "mode": "full_exam", "event_id": str(uuid4())},
    )
    assert started.status_code in (200, 201), started.text
    attempt_id = started.json()["id"]
    assert (
        client.get(
            f"/api/v1/reading/attempts/{attempt_id}", headers=firebase_headers("firebaseB")
        ).status_code
        == 404
    )
    assert (
        client.put(
            f"/api/v1/reading/attempts/{attempt_id}/answers/question-1",
            headers=firebase_headers("firebaseB"),
            json={"event_id": str(uuid4()), "expected_version": 0, "answer": "A"},
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/reading/attempts/{attempt_id}/result",
            headers=firebase_headers("firebaseB"),
        ).status_code
        == 404
    )
    # Same learner can resume their old attempt through either auth provider.
    assert (
        client.get(f"/api/v1/reading/attempts/{attempt_id}", headers=headers(a)).status_code == 200
    )
    get_settings().legacy_auth_enabled = False
    assert client.get("/api/v1/me", headers=headers(a)).status_code == 401
    assert client.get("/api/v1/me", headers=firebase_headers("firebaseA")).status_code == 200
    with db.session() as session:
        assert session.scalar(select(func.count()).select_from(LearnerProfileRow)) == 2
        assert session.scalar(select(func.count()).select_from(FirebaseIdentityRow)) == 2


def test_jwt_never_falls_back_and_feature_default(system, monkeypatch):
    _, client, _ = system
    from app.core.config import get_settings

    def forbidden(*args):
        pytest.fail("JWT must never enter legacy resolver")

    monkeypatch.setattr("app.core.auth.DeviceEnrollmentRepository.resolve", forbidden)
    assert client.get("/api/v1/me", headers=firebase_headers("uid")).status_code == 401
    get_settings().firebase_auth_enabled = True

    def invalid(token):
        raise UnauthorizedError("Invalid credential")

    monkeypatch.setattr("app.core.auth.verify_firebase_token", invalid)
    assert client.get("/api/v1/me", headers=firebase_headers("uid")).status_code == 401
    assert (
        client.get("/api/v1/me", headers={"Authorization": "Bearer alua_dev_x.y"}).status_code
        == 401
    )


@pytest.mark.parametrize(
    "error",
    [
        auth.InvalidIdTokenError("wrong project/signature"),
        auth.ExpiredIdTokenError("expired", cause=None),
        auth.RevokedIdTokenError("revoked"),
        auth.UserDisabledError("disabled"),
        auth.UserNotFoundError("deleted"),
    ],
)
def test_admin_rejections(monkeypatch, error):
    from app.core.firebase_auth import verify_firebase_token

    monkeypatch.setattr("app.core.firebase_auth.firebase_app", lambda: object())

    def verify(token, *, app, check_revoked):
        assert check_revoked is True
        raise error

    monkeypatch.setattr(auth, "verify_id_token", verify)
    with pytest.raises(UnauthorizedError):
        verify_firebase_token("header.payload.signature")


def test_admin_success_and_emulator_block(monkeypatch):
    from app.core.firebase_auth import firebase_app, verify_firebase_token

    with monkeypatch.context() as patch:
        patch.setattr("app.core.firebase_auth.firebase_app", lambda: object())

        def verify(token, *, app, check_revoked):
            assert check_revoked is True
            return {"uid": "verified-uid", "email": "never-used-to-link@example.org"}

        patch.setattr(auth, "verify_id_token", verify)
        assert verify_firebase_token("header.payload.signature") == "verified-uid"
    monkeypatch.setenv("FIREBASE_AUTH_EMULATOR_HOST", "127.0.0.1:9099")
    with pytest.raises(ExternalServiceError):
        firebase_app()


def test_upgrade_from_0005_preserves_learners(system):
    from sqlalchemy import text

    from alembic import command

    db, client, cfg = system
    existing, _ = bootstrap(client, "husband")
    with db.engine.begin() as conn:
        FirebaseIdentityRow.__table__.drop(conn)
        conn.execute(text("UPDATE alembic_version SET version_num='20261101_0005'"))
    command.upgrade(cfg, "head")
    with db.session() as session:
        assert session.get(LearnerProfileRow, existing["profile"]["uid"]) is not None
        assert session.scalar(select(func.count()).select_from(FirebaseIdentityRow)) == 0
        assert (
            session.execute(text("SELECT version_num FROM alembic_version")).scalar()
            == "20261104_0007"
        )
