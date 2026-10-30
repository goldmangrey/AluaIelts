from copy import deepcopy

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.db.database import get_database
from app.db.models import LearningQualityRow


class QualityRepository:
    def __init__(self, database=None):
        self.database = database or get_database()

    def get(self, uid, key):
        with self.database.session() as session:
            row = session.get(LearningQualityRow, (uid, key))
            return deepcopy(row.payload) if row else {}

    def mutate(self, uid, key, change):
        with self.database.session() as session:
            session.execute(
                insert(LearningQualityRow)
                .values(learner_id=uid, key=key, payload={})
                .on_conflict_do_nothing()
            )
            row = session.scalar(
                select(LearningQualityRow)
                .where(LearningQualityRow.learner_id == uid, LearningQualityRow.key == key)
                .with_for_update()
            )
            payload = deepcopy(row.payload)
            change(payload)
            row.payload = payload
            return deepcopy(payload)

    def preferences(self, uid):
        with self.database.session() as session:
            rows = session.scalars(
                select(LearningQualityRow).where(
                    LearningQualityRow.learner_id == uid, LearningQualityRow.key.startswith("item:")
                )
            )
            return {row.key[5:]: row.payload for row in rows}
