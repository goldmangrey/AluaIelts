from app.core.exceptions import ExternalServiceError
from app.db.database import Database
from app.db.models import ProgressAnalyticsRow
from app.db.serialization import document
from app.modules.progress.models import ProgressSnapshot


class ProgressAnalyticsRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def save(self, uid: str, snapshot: ProgressSnapshot) -> None:
        period = snapshot.period
        period_key = f"{period.days}:{period.timezone}:{period.end_date.isoformat()}"
        try:
            with self._database.session() as session:
                row = session.get(ProgressAnalyticsRow, (uid, period_key), with_for_update=True)
                if row is None:
                    session.add(
                        ProgressAnalyticsRow(
                            learner_id=uid,
                            period_key=period_key,
                            generated_at=snapshot.generated_at,
                            payload=document(snapshot),
                        )
                    )
                else:
                    row.generated_at = snapshot.generated_at
                    row.payload = document(snapshot)
        except Exception as exc:
            raise ExternalServiceError(
                message="Progress analytics could not be persisted.",
                code="progress_persistence_error",
            ) from exc
