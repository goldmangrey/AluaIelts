import hashlib
from datetime import UTC, datetime

from sqlalchemy import select

from app.db.database import Database
from app.db.models import DeviceEnrollmentRow


def hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class DeviceEnrollmentRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def resolve(self, token: str) -> DeviceEnrollmentRow | None:
        token_hash = hash_secret(token)
        with self._database.session() as session:
            row = session.scalar(
                select(DeviceEnrollmentRow).where(
                    DeviceEnrollmentRow.token_hash == token_hash,
                    DeviceEnrollmentRow.revoked_at.is_(None),
                )
            )
            if row is None:
                return None
            row.last_used_at = datetime.now(UTC)
            session.flush()
            session.expunge(row)
            return row

    def list_active(self, learner_id: str) -> list[DeviceEnrollmentRow]:
        with self._database.session() as session:
            rows = session.scalars(
                select(DeviceEnrollmentRow)
                .where(
                    DeviceEnrollmentRow.learner_id == learner_id,
                    DeviceEnrollmentRow.revoked_at.is_(None),
                )
                .order_by(DeviceEnrollmentRow.created_at)
            ).all()
            for row in rows:
                session.expunge(row)
            return list(rows)

    def revoke(self, learner_id: str, enrollment_id: str) -> bool:
        with self._database.session() as session:
            row = session.get(DeviceEnrollmentRow, enrollment_id, with_for_update=True)
            if row is None or row.learner_id != learner_id or row.revoked_at is not None:
                return False
            row.revoked_at = datetime.now(UTC)
            return True
