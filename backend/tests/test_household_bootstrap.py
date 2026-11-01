"""Real PostgreSQL integration tests; an isolated temporary cluster, never the configured DB."""

import logging
import re
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from alembic import command


@pytest.fixture(scope="module")
def postgres_url():
    initdb, pg_ctl = shutil.which("initdb"), shutil.which("pg_ctl")
    if not initdb or not pg_ctl:
        pytest.skip("Local PostgreSQL binaries required (no external database is used)")
    with tempfile.TemporaryDirectory(prefix="alua-pg-", dir="/tmp") as temp:
        data = str(Path(temp) / "data")
        subprocess.run(
            [
                initdb,
                "-D",
                data,
                "-A",
                "trust",
                "-U",
                "alua_test",
                "--no-locale",
                "--encoding=UTF8",
            ],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                pg_ctl,
                "-D",
                data,
                "-l",
                str(Path(temp) / "server.log"),
                "-o",
                f"-k {temp} -h ''",
                "-w",
                "start",
            ],
            check=True,
            capture_output=True,
        )
        try:
            yield f"postgresql+psycopg://alua_test@/postgres?host={temp}"
        finally:
            subprocess.run(
                [pg_ctl, "-D", data, "-m", "immediate", "-w", "stop"],
                check=True,
                capture_output=True,
            )


@pytest.fixture
def system(postgres_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("OPENAI_EXERCISE_GENERATION_ENABLED", "false")
    monkeypatch.setenv("OPENAI_PROGRESS_ANALYSIS_ENABLED", "false")
    from app.core.config import get_settings
    from app.db.database import get_database

    get_settings.cache_clear()
    get_database.cache_clear()
    db = get_database()
    with db.engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    cfg.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "alembic"))
    command.upgrade(cfg, "head")
    from app.main import create_app

    logging.getLogger("httpx2").setLevel(logging.WARNING)
    with TestClient(create_app()) as client:
        yield db, client, cfg
    db.engine.dispose()
    get_database.cache_clear()
    get_settings.cache_clear()


def bootstrap(client, role, secret=None):
    # Test-only provisioning of existing learners, never the removed HTTP bootstrap.
    from datetime import timedelta

    from app.db.database import get_database
    from app.db.models import EnrollmentCodeRow, HouseholdProfileRow
    from app.modules.enrollment.bootstrap import ensure_profiles, household_lock
    from app.modules.enrollment.repository import hash_secret

    code = uuid4().hex.upper()
    now = datetime.now(UTC)
    with get_database().session() as session:
        household_lock(session)
        ensure_profiles(session)
        uid = session.get(HouseholdProfileRow, role).learner_id
        session.add(
            EnrollmentCodeRow(
                code_hash=hash_secret(code),
                learner_id=uid,
                display_name=role,
                created_at=now,
                expires_at=now + timedelta(minutes=15),
            )
        )
    payload = {"code": code}
    response = client.post("/api/v1/enrollment", json=payload)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    return response.json(), payload


def headers(device):
    return {"Authorization": "Bearer " + device["token"]}


def test_concurrent_retries_and_constraints(system):
    db, client, _ = system
    from app.db.models import DeviceEnrollmentRow, HouseholdProfileRow, LearnerProfileRow
    from app.modules.enrollment.bootstrap import household_lock

    husband, payload = bootstrap(client, "husband")
    with ThreadPoolExecutor(max_workers=6) as pool:
        statuses = list(
            pool.map(
                lambda _: client.post("/api/v1/enrollment", json=payload).status_code, range(6)
            )
        )
    assert all(status in (401, 429) for status in statuses)
    assert 429 in statuses
    with db.session() as session:
        household_lock(session)
        assert session.scalar(select(func.count()).select_from(DeviceEnrollmentRow)) == 1
        assert session.scalar(select(func.count()).select_from(LearnerProfileRow)) == 2
        assert session.scalar(select(func.count()).select_from(HouseholdProfileRow)) == 2
    with pytest.raises(IntegrityError), db.session() as session:
        session.add(HouseholdProfileRow(role="third", learner_id=husband["profile"]["uid"]))
    with pytest.raises(IntegrityError), db.session() as session:
        session.add(HouseholdProfileRow(role="husband", learner_id=husband["profile"]["uid"]))
    assert (
        client.post(
            "/api/v1/bootstrap", json={"role": "wife", "device_secret": "a" * 64}
        ).status_code
        == 404
    )
    h = headers(husband)
    assert client.get("/api/v1/me", headers=h).status_code == 200
    assert client.delete("/api/v1/device", headers=h).status_code == 200
    assert client.get("/api/v1/me", headers=h).status_code == 401
    assert client.post("/api/v1/enrollment", json=payload).status_code == 401


def test_authorization_and_existing_features(system):
    db, client, _ = system
    husband, _ = bootstrap(client, "husband")
    wife, _ = bootstrap(client, "wife")
    paths = client.get("/openapi.json").json()["paths"]
    count = 0
    for path, operations in paths.items():
        if path in ["/", "/api/v1/health", "/api/v1/enrollment"]:
            continue
        for method in operations:
            if method not in {"get", "post", "patch", "delete", "put"}:
                continue
            url = re.sub(r"\{[^}]+\}", str(uuid4()), path)
            response = client.request(method, url, json={})
            assert response.status_code == 401, (method, path, response.text)
            count += 1
    assert count == 69  # Existing 68 endpoints plus authenticated Firebase registration.
    assert client.post("/api/v1/enrollment", json={"code": "0" * 32}).status_code == 401
    assert (
        client.post(
            "/api/v1/bootstrap", json={"role": "admin", "device_secret": "a" * 64}
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/v1/bootstrap", json={"role": "wife", "device_secret": "short"}
        ).status_code
        == 404
    )
    assert client.get("/api/v1/me", headers={"Authorization": "Bearer invalid"}).status_code == 401
    for me, other in [(husband, wife), (wife, husband)]:
        h = headers(me)
        assert (
            client.get("/api/v1/me", headers=h, params={"uid": other["profile"]["uid"]}).json()[
                "uid"
            ]
            == me["profile"]["uid"]
        )
        assert (
            client.delete("/api/v1/devices/" + other["enrollment_id"], headers=h).status_code == 404
        )
        assert client.get("/api/v1/partner/dashboard", headers=h).status_code == 401
    assert (
        client.patch(
            "/api/v1/me",
            headers=headers(husband),
            json={"uid": wife["profile"]["uid"], "display_name": "H"},
        ).status_code
        == 200
    )
    assert client.get("/api/v1/me", headers=headers(wife)).json()["display_name"] == "Жена"
    # Exercise the real content, planning, SRS and widget pipeline, no mocked repositories.
    for path in [
        "/curriculum/me",
        "/grammar",
        "/vocabulary/tracks",
        "/vocabulary-learning/today",
        "/vocabulary-learning/weekly",
        "/progress",
        "/student-model",
        "/partner/status",
    ]:
        response = client.get("/api/v1" + path, headers=headers(husband))
        assert response.status_code == 200, (path, response.text)
    plan = client.post(
        "/api/v1/daily-plans/today", headers=headers(husband), json={"timezone": "Asia/Almaty"}
    )
    assert plan.status_code == 200, plan.text
    snapshot = client.get("/api/v1/widgets/snapshot", headers=headers(husband))
    assert snapshot.status_code == 200, snapshot.text
    assert snapshot.json()["schema_version"] == 5
    today = client.get("/api/v1/vocabulary-learning/today", headers=headers(husband)).json()
    # Read session identifiers from the response contract, then check foreign ownership.
    for key in ["midday_session", "evening_session"]:
        session_id = today[key]["session_id"]
        assert (
            client.get(
                f"/api/v1/vocabulary-learning/review-sessions/{session_id}", headers=headers(wife)
            ).status_code
            == 404
        )

    session_id = today["midday_session"]["session_id"]
    cards = client.get(
        f"/api/v1/vocabulary-learning/review-sessions/{session_id}", headers=headers(husband)
    ).json()["cards"]
    assert cards
    submission = {
        "event_id": str(uuid4()),
        "lexical_item_id": cards[0]["lexical_item_id"],
        "rating": "good",
    }
    route = f"/api/v1/vocabulary-learning/review-sessions/{session_id}/responses"
    assert client.post(route, headers=headers(wife), json=submission).status_code == 422
    first = client.post(route, headers=headers(husband), json=submission)
    assert first.status_code == 200, first.text
    repeat = client.post(route, headers=headers(husband), json=submission)
    assert repeat.status_code == 200, repeat.text
    assert repeat.json() == first.json()
    invite = client.post("/api/v1/partner/invitations", headers=headers(husband))
    assert invite.status_code == 200, invite.text
    accepted = client.post(
        "/api/v1/partner/invitations/accept",
        headers=headers(wife),
        json={"code": invite.json()["code"]},
    )
    assert accepted.status_code == 200, accepted.text
    assert client.get("/api/v1/partner/dashboard", headers=headers(wife)).status_code == 200
    assert (
        client.post("/api/v1/partner/relationship/revoke", headers=headers(husband)).status_code
        == 200
    )
    assert client.get("/api/v1/partner/dashboard", headers=headers(wife)).status_code == 401


def test_existing_database_upgrade_and_explicit_binding(system):
    db, client, cfg = system
    from app.core.exceptions import ConflictError
    from app.db.models import HouseholdProfileRow, LearnerProfileRow, LearningEventRow
    from app.db.serialization import document
    from app.modules.enrollment.bootstrap import bind_existing, household_lock
    from app.modules.users.models import UserProfile, UserRole

    # Recreate the pre-feature shape with real legacy rows and an existing progress record.
    command.downgrade(cfg, "20261028_0001")
    now = datetime.now(UTC)
    ids = [str(uuid4()), str(uuid4())]
    event_id = str(uuid4())
    with db.session() as session:
        for uid in ids:
            profile = UserProfile(
                uid=uid,
                display_name="Legacy",
                role=UserRole.LEARNER,
                created_at=now,
                updated_at=now,
            )
            session.add(
                LearnerProfileRow(
                    learner_id=uid,
                    display_name="Legacy",
                    created_at=now,
                    updated_at=now,
                    payload=document(profile),
                )
            )
        session.flush()
        session.add(
            LearningEventRow(
                learner_id=ids[0],
                event_id=event_id,
                server_received_at=now,
                event_type="grammar_lesson_opened",
                payload={"sentinel": "preserved"},
            )
        )
    command.upgrade(cfg, "head")
    command.upgrade(cfg, "head")
    for _ in range(2):
        with db.session() as session:
            household_lock(session)
            bind_existing(session, "husband", ids[0])
            bind_existing(session, "wife", ids[1])
    with pytest.raises(ConflictError), db.session() as session:
        household_lock(session)
        bind_existing(session, "wife", ids[0])
    husband, _ = bootstrap(client, "husband")
    assert husband["profile"]["uid"] == ids[0]
    with db.session() as session:
        assert session.get(LearningEventRow, (ids[0], event_id)).payload == {
            "sentinel": "preserved"
        }
        assert len(session.scalars(select(LearnerProfileRow)).all()) == 2
        assert len(session.scalars(select(HouseholdProfileRow)).all()) == 2
    assert (
        client.get(
            f"/api/v1/learning-events/{event_id}", headers=headers(bootstrap(client, "wife")[0])
        ).status_code
        == 404
    )
