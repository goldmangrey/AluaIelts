"""Isolated product QA using the real app and a temporary local PostgreSQL cluster.

Run from backend: uv run python -m scripts.qa.stage5_server
Never reads configured production DATABASE_URL. No admin routes are added to the app.
"""

import json
import os
import subprocess
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4


def main():
    with tempfile.TemporaryDirectory(prefix="alua-stage5-qa-", dir="/tmp") as temp:
        data = str(Path(temp) / "pg")
        subprocess.run(
            [
                "initdb",
                "-D",
                data,
                "-A",
                "trust",
                "-U",
                "alua_qa",
                "--no-locale",
                "--encoding=UTF8",
            ],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                "pg_ctl",
                "-D",
                data,
                "-l",
                str(Path(temp) / "pg.log"),
                "-o",
                f"-k {temp} -h ''",
                "-w",
                "start",
            ],
            check=True,
            capture_output=True,
        )
        try:
            os.environ.update(
                DATABASE_URL=f"postgresql+psycopg://alua_qa@/postgres?host={temp}",
                OPENAI_API_KEY="",
                OPENAI_EXERCISE_GENERATION_ENABLED="false",
                OPENAI_PROGRESS_ANALYSIS_ENABLED="false",
            )
            from alembic.config import Config
            from sqlalchemy import select

            from alembic import command
            from app.db.database import get_database
            from app.db.models import (
                CanonicalVocabularyStateRow,
                EnrollmentCodeRow,
                HouseholdProfileRow,
            )
            from app.modules.enrollment.bootstrap import ensure_profiles
            from app.modules.enrollment.repository import hash_secret
            from app.modules.learning_quality.repository import QualityRepository
            from app.modules.study.router import StudyAction
            from app.modules.study.service import StudyService

            command.upgrade(Config("alembic.ini"), "head")
            db = get_database()
            now = datetime.now(UTC)
            with db.session() as session:
                ensure_profiles(session)
                learners = {
                    r.role: r.learner_id for r in session.scalars(select(HouseholdProfileRow))
                }
                for role, uid in learners.items():
                    session.add(
                        EnrollmentCodeRow(
                            code_hash=hash_secret(("1" if role == "husband" else "2") * 32),
                            learner_id=uid,
                            display_name=role,
                            created_at=now,
                            expires_at=now + timedelta(hours=12),
                        )
                    )
            # The second learner has authentic B2 content and 15 prior introductions, not mock UI.
            uid = learners["wife"]
            QualityRepository(db).mutate(
                uid,
                "diagnostic:v1",
                lambda p: p.update(
                    result={
                        "difficulty": "B2",
                        "gaps": [],
                        "notice": "Локальная QA fixture. Не результат диагностики.",
                    }
                ),
            )
            service = StudyService(db)
            initial = service.snapshot(uid, now)
            for item in initial["cards"][:15]:
                service.act(
                    uid, StudyAction(event_id=uuid4(), item_id=item["id"], action="next"), now
                )
            with db.session() as session:
                for state in session.scalars(
                    select(CanonicalVocabularyStateRow).where(
                        CanonicalVocabularyStateRow.learner_id == uid
                    )
                ):
                    payload = dict(state.payload)
                    payload["next_due_at"] = (now - timedelta(hours=1)).isoformat()
                    state.payload = payload
                    state.due_at = now - timedelta(hours=1)
            # Runtime metadata stays in /tmp and contains no bearer token.
            Path("/tmp/alua-stage5-qa.json").write_text(
                json.dumps(
                    {
                        "database_url": os.environ["DATABASE_URL"],
                        "learners": learners,
                        "base_url": "http://127.0.0.1:8765",
                    }
                )
            )
            print(
                "QA only: http://127.0.0.1:8765; codes: 32 ones (husband) / 32 twos (wife)",
                flush=True,
            )
            import uvicorn

            uvicorn.run(
                "app.main:create_app",
                factory=True,
                host="127.0.0.1",
                port=8765,
                log_level="warning",
            )
        finally:
            subprocess.run(
                ["pg_ctl", "-D", data, "-m", "immediate", "-w", "stop"],
                check=True,
                capture_output=True,
            )
            Path("/tmp/alua-stage5-qa.json").unlink(missing_ok=True)


if __name__ == "__main__":
    main()
