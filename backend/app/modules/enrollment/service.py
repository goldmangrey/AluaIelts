import secrets
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import AluaError, ConflictError, UnauthorizedError
from app.db.database import Database
from app.db.models import DeviceEnrollmentRow, EnrollmentCodeRow, LearnerProfileRow
from app.modules.enrollment.bootstrap import household_lock
from app.modules.enrollment.repository import hash_secret
from app.modules.enrollment.schemas import EnrollDeviceResponse
from app.modules.users.models import UserProfile


def normalize_enrollment_code(code: str) -> str:
    return "".join(character for character in code.upper() if character.isalnum())


class DeviceEnrollmentService:
    def __init__(self, database: Database) -> None:
        self._database = database

    def enroll(self, code: str, device_name: str | None) -> EnrollDeviceResponse:
        code_hash = hash_secret(normalize_enrollment_code(code))
        enrollment_id = str(uuid4())
        token = f"alua_dev_{secrets.token_urlsafe(32)}"
        try:
            with self._database.session() as session:
                # Cluster-wide throttle: at most one code check per second, across workers.
                # Try-lock rejects concurrent requests immediately; no new table or IP trust.
                if not session.scalar(text("SELECT pg_try_advisory_xact_lock(19770429, 3)")):
                    raise AluaError(
                        "Повторите попытку через несколько секунд.", "enrollment_throttled", 429
                    )
                session.execute(text("SELECT pg_sleep(1)"))
                household_lock(session)
                pairing = session.get(EnrollmentCodeRow, code_hash, with_for_update=True)
                now = datetime.now(UTC)
                if pairing is None or pairing.redeemed_at is not None:
                    raise UnauthorizedError(
                        message="The enrollment code is invalid or has already been used.",
                        code="enrollment_code_invalid",
                    )
                expires_at = pairing.expires_at
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=UTC)
                if expires_at <= now:
                    raise UnauthorizedError(
                        message="The enrollment code has expired.",
                        code="enrollment_code_expired",
                    )
                if not pairing.learner_id:
                    raise UnauthorizedError(
                        "Код не привязан к существующему профилю.", "enrollment_code_invalid"
                    )
                learner_id = pairing.learner_id
                existing = session.get(LearnerProfileRow, learner_id)
                if existing is None:
                    raise ConflictError("Learner not found.", "enrollment_learner_missing")
                profile = UserProfile.model_validate(existing.payload)
                session.add(
                    DeviceEnrollmentRow(
                        enrollment_id=enrollment_id,
                        learner_id=learner_id,
                        token_hash=hash_secret(token),
                        device_name=device_name,
                        created_at=now,
                    )
                )
                pairing.redeemed_at = now
                pairing.learner_id = learner_id
            return EnrollDeviceResponse(
                token=token,
                enrollment_id=enrollment_id,
                profile=profile,
            )
        except (ConflictError, UnauthorizedError):
            raise
        except IntegrityError as exc:
            raise ConflictError(
                message="The enrollment code was already used.", code="enrollment_code_conflict"
            ) from exc
