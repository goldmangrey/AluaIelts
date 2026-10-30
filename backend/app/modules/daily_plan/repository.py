from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ExternalServiceError
from app.db.database import Database
from app.db.models import DailyPlanRow
from app.db.serialization import document
from app.modules.daily_plan.models import DailyPlan, DailyPlanItemState, DailyPlanStatus


class DailyPlanRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def get(self, uid: str, local_date: date) -> DailyPlan | None:
        try:
            with self._database.session() as session:
                row = session.get(DailyPlanRow, (uid, local_date))
                return DailyPlan.model_validate(row.payload) if row else None
        except Exception as exc:
            raise self._error() from exc

    def create(self, uid: str, plan: DailyPlan) -> DailyPlan:
        try:
            with self._database.session() as session:
                session.add(self._row(uid, plan))
            return plan
        except IntegrityError:
            existing = self.get(uid, plan.local_date)
            if existing is not None:
                return existing
            raise self._error()
        except Exception as exc:
            raise self._error() from exc

    def replace(self, uid: str, plan: DailyPlan) -> DailyPlan:
        try:
            with self._database.session() as session:
                row = session.get(DailyPlanRow, (uid, plan.local_date), with_for_update=True)
                if row is None:
                    session.add(self._row(uid, plan))
                else:
                    row.status = plan.status.value
                    row.updated_at = plan.updated_at
                    row.payload = document(plan)
            return plan
        except Exception as exc:
            raise self._error() from exc

    def list_between(self, uid: str, start_date: date, end_date: date) -> list[DailyPlan]:
        try:
            with self._database.session() as session:
                rows = session.scalars(
                    select(DailyPlanRow)
                    .where(
                        DailyPlanRow.learner_id == uid,
                        DailyPlanRow.local_date.between(start_date, end_date),
                    )
                    .order_by(DailyPlanRow.local_date)
                ).all()
                return [DailyPlan.model_validate(row.payload) for row in rows]
        except Exception as exc:
            raise self._error() from exc

    def complete_item(self, uid: str, local_date: date, item_id: str) -> DailyPlan:
        try:
            with self._database.session() as session:
                row = session.get(DailyPlanRow, (uid, local_date), with_for_update=True)
                if row is None:
                    raise ValueError("Daily plan does not exist.")
                plan = DailyPlan.model_validate(row.payload)
                if not any(item.item_id == item_id for item in plan.items):
                    raise ValueError("Daily plan item does not exist.")
                items = tuple(
                    item.model_copy(update={"state": DailyPlanItemState.COMPLETED})
                    if item.item_id == item_id
                    else item
                    for item in plan.items
                )
                status = (
                    DailyPlanStatus.COMPLETED
                    if all(item.state == DailyPlanItemState.COMPLETED for item in items)
                    else DailyPlanStatus.READY
                )
                updated = plan.model_copy(
                    update={"items": items, "status": status, "updated_at": datetime.now(UTC)}
                )
                row.status = updated.status.value
                row.updated_at = updated.updated_at
                row.payload = document(updated)
                return updated
        except Exception as exc:
            raise self._error() from exc

    @staticmethod
    def _row(uid: str, plan: DailyPlan) -> DailyPlanRow:
        return DailyPlanRow(
            learner_id=uid,
            local_date=plan.local_date,
            status=plan.status.value,
            updated_at=plan.updated_at,
            payload=document(plan),
        )

    @staticmethod
    def _error() -> ExternalServiceError:
        return ExternalServiceError(
            message="Daily plan data is temporarily unavailable.",
            code="daily_plan_persistence_error",
        )
