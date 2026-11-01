"""Short PostgreSQL transactions, learner scope and per-learner serialization."""

from contextlib import contextmanager

from sqlalchemy import select, text

from app.core.exceptions import NotFoundError
from app.db.database import Database
from app.modules.reading.models import ReadingAttemptRow


class ReadingRepository:
    def __init__(self, database: Database):
        self.database = database

    @contextmanager
    def transaction(self, uid: str):
        with self.database.session() as session:
            # Two private learners: this simple lock also serializes cross-attempt event UUIDs.
            session.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                {"key": "reading:" + uid},
            )
            yield session

    @staticmethod
    def attempt(session, uid: str, aid: str) -> ReadingAttemptRow:
        row = session.scalar(
            select(ReadingAttemptRow)
            .where(ReadingAttemptRow.id == aid, ReadingAttemptRow.learner_id == uid)
            .with_for_update()
        )
        if row is None:
            raise NotFoundError("Reading attempt not found.", "reading_attempt_not_found")
        return row
