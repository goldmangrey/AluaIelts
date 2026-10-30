from datetime import UTC, date, datetime
from uuid import NAMESPACE_URL, uuid5

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.modules.daily_plan.repository import DailyPlanRepository
from app.modules.daily_plan.service import DailyPlanService
from app.modules.exercises.coordinator import ExerciseGenerationCoordinator
from app.modules.exercises.generator import ENGINE_VERSION
from app.modules.exercises.grader import ExerciseGrader
from app.modules.exercises.models import ExerciseAttempt, ExerciseSession, ExerciseSessionStatus
from app.modules.exercises.repository import ExerciseRepository
from app.modules.exercises.schemas import (
    ExerciseAttemptFeedback,
    ExerciseAttemptResult,
    ExerciseItemState,
    ExercisePublicResponse,
    ExerciseSessionProgress,
    ExerciseSessionResponse,
    SubmitExerciseAttemptRequest,
)
from app.modules.learning_events.models import AssessmentEventPayload
from app.modules.learning_events.service import LearningEventService
from app.modules.mastery.models import MasteryContentType, MasteryEvidence
from app.modules.mastery.repository import MasteryRepository
from app.modules.mastery.service import MasteryService


class ExerciseService:
    def __init__(
        self,
        *,
        repository: ExerciseRepository,
        plans: DailyPlanRepository,
        daily_plan_service: DailyPlanService,
        generator: ExerciseGenerationCoordinator,
        grader: ExerciseGrader,
        events: LearningEventService,
        mastery: MasteryService,
        mastery_repository: MasteryRepository,
    ) -> None:
        self._repository = repository
        self._plans = plans
        self._daily_plans = daily_plan_service
        self._generator = generator
        self._grader = grader
        self._events = events
        self._mastery = mastery
        self._mastery_repository = mastery_repository

    def create_session(self, uid: str, local_date: date, item_id: str) -> ExerciseSessionResponse:
        plan = self._plans.get(uid, local_date)
        if plan is None:
            raise NotFoundError(message="Daily plan not found.", code="exercise_plan_not_found")
        item = next((value for value in plan.items if value.item_id == item_id), None)
        if item is None:
            raise NotFoundError(
                message="Daily plan item not found.", code="exercise_plan_item_not_found"
            )
        session_id = str(
            uuid5(NAMESPACE_URL, f"alua:{uid}:{local_date}:{item_id}:{ENGINE_VERSION}")
        )
        existing = self._repository.get_session(uid, session_id)
        if existing:
            return self._response(uid, existing)
        exercises, generation_mode = self._generator.generate(
            session_id, item, self._mastery_repository.list_states(uid)
        )
        if not exercises:
            raise ValidationError(
                message="No canonical exercise content is available.",
                code="exercise_content_unavailable",
            )
        now = datetime.now(UTC)
        session = ExerciseSession(
            session_id=session_id,
            user_id=uid,
            daily_plan_date=local_date,
            daily_plan_item_id=item_id,
            content_type=item.content_type,
            content_id=item.content_id,
            curriculum_node_id=item.curriculum_node_id,
            plan_item_kind=item.kind,
            exercises=exercises,
            created_at=now,
            updated_at=now,
            total_exercises=len(exercises),
            curriculum_version=plan.curriculum_version,
            vocabulary_version=plan.vocabulary_version,
            grammar_version=plan.grammar_version,
            generation_mode=generation_mode,
            openai_model=(
                next(
                    (
                        exercise.generation_model
                        for exercise in exercises
                        if exercise.generation_model is not None
                    ),
                    None,
                )
            ),
            prompt_version=(
                next(
                    (
                        exercise.generation_template_version
                        for exercise in exercises
                        if exercise.generation_template_version is not None
                    ),
                    None,
                )
            ),
        )
        return self._response(uid, self._repository.create_session(uid, session))

    def get_session(self, uid: str, session_id: str) -> ExerciseSessionResponse:
        session = self._repository.get_session(uid, session_id)
        if session is None:
            raise NotFoundError(
                message="Exercise session not found.", code="exercise_session_not_found"
            )
        return self._response(uid, session)

    def submit_attempt(
        self, uid: str, session_id: str, exercise_id: str, request: SubmitExerciseAttemptRequest
    ) -> ExerciseAttemptResult:
        session = self._repository.get_session(uid, session_id)
        if session is None:
            raise NotFoundError(
                message="Exercise session not found.", code="exercise_session_not_found"
            )
        exercise = next(
            (value for value in session.exercises if value.exercise_id == exercise_id), None
        )
        if exercise is None:
            raise NotFoundError(message="Exercise not found.", code="exercise_not_found")
        attempts = self._repository.list_attempts(uid, session_id)
        answered_ids = {value.exercise_id for value in attempts}
        first_unanswered = next(
            (value for value in session.exercises if value.exercise_id not in answered_ids), None
        )
        existing = next((value for value in attempts if value.exercise_id == exercise_id), None)
        if existing is None and first_unanswered and first_unanswered.exercise_id != exercise_id:
            raise ConflictError(
                message="Exercises must be answered in order.", code="exercise_out_of_order"
            )
        is_correct = False if request.unknown else self._grader.grade(exercise, request.answer)
        proposed = ExerciseAttempt(
            attempt_id=request.attempt_id,
            exercise_id=exercise_id,
            session_id=session_id,
            submitted_answer=request.answer,
            topic_id=exercise.content_id
            if exercise.content_type.value == "grammar_lesson"
            else None,
            exercise_type=exercise.exercise_type,
            answer_status="unknown"
            if request.unknown
            else "correct"
            if is_correct
            else "incorrect",
            is_correct=is_correct,
            outcome=1.0 if is_correct else 0.0,
            client_occurred_at=request.client_occurred_at,
            server_received_at=datetime.now(UTC),
            response_time_ms=request.response_time_ms,
        )
        attempt = self._repository.create_attempt(uid, proposed)
        event_id = uuid5(
            NAMESPACE_URL,
            f"alua:{uid}:{session_id}:{exercise_id}:{attempt.attempt_id}:exercise_answered",
        )
        error_tags = exercise.error_tags if not attempt.is_correct else ()
        assessment = AssessmentEventPayload(
            exercise_id=exercise_id,
            exercise_session_id=session_id,
            daily_plan_item_id=session.daily_plan_item_id,
            exercise_type=exercise.exercise_type.value,
            dimension=exercise.dimension.value,
            evidence_kind=exercise.evidence_kind.value,
            difficulty=exercise.difficulty.value,
            outcome=attempt.outcome,
            is_correct=attempt.is_correct,
            response_time_ms=attempt.response_time_ms,
            error_tags=error_tags,
        )
        event = self._events.record_exercise_answered(
            uid=uid,
            event_id=event_id,
            content_type=exercise.content_type.value,
            content_id=exercise.content_id,
            curriculum_node_id=exercise.curriculum_node_id,
            occurred_at=attempt.client_occurred_at,
            assessment=assessment,
        )
        self._mastery.apply_evidence(
            uid,
            MasteryEvidence(
                event_id=event.event_id,
                content_type=MasteryContentType(exercise.content_type.value),
                content_id=exercise.content_id,
                dimension=exercise.dimension,
                outcome=attempt.outcome,
                occurred_at=event.server_received_at,
                evidence_kind=exercise.evidence_kind,
                difficulty=exercise.difficulty,
                error_tags=error_tags,
            ),
        )
        attempts = self._repository.list_attempts(uid, session_id)
        completed = len(attempts) == session.total_exercises
        updated = session.model_copy(
            update={
                "answered_exercises": len(attempts),
                "correct_exercises": sum(value.is_correct for value in attempts),
                "status": ExerciseSessionStatus.COMPLETED
                if completed
                else ExerciseSessionStatus.ACTIVE,
                "updated_at": datetime.now(UTC),
            }
        )
        updated = self._repository.update_session(uid, updated)
        if completed:
            self._daily_plans.complete_item_from_exercise_session(
                uid, session.daily_plan_date, session.daily_plan_item_id
            )
        feedback = self._feedback(exercise, attempt)
        return ExerciseAttemptResult(
            **feedback.model_dump(),
            session_progress=self._progress(updated),
            session_status=updated.status,
            daily_plan_item_completed=completed,
        )

    def _response(self, uid: str, session: ExerciseSession) -> ExerciseSessionResponse:
        attempts = {
            value.exercise_id: value
            for value in self._repository.list_attempts(uid, session.session_id)
        }
        exercises = [
            ExercisePublicResponse(
                exercise_id=value.exercise_id,
                exercise_type=value.exercise_type,
                content_type=value.content_type,
                content_id=value.content_id,
                curriculum_node_id=value.curriculum_node_id,
                instruction=value.instruction,
                prompt=value.prompt,
                options=list(value.options),
                sequence=value.sequence,
                state=ExerciseItemState.ANSWERED
                if value.exercise_id in attempts
                else ExerciseItemState.UNANSWERED,
                result=self._feedback(value, attempts[value.exercise_id])
                if value.exercise_id in attempts
                else None,
            )
            for value in session.exercises
        ]
        return ExerciseSessionResponse(
            **session.model_dump(
                exclude={
                    "user_id",
                    "exercises",
                    "total_exercises",
                    "answered_exercises",
                    "correct_exercises",
                    "curriculum_version",
                    "vocabulary_version",
                    "grammar_version",
                    "generation_mode",
                    "openai_model",
                    "prompt_version",
                }
            ),
            exercises=exercises,
            progress=self._progress(session),
        )

    @staticmethod
    def _feedback(exercise, attempt: ExerciseAttempt) -> ExerciseAttemptFeedback:  # type: ignore[no-untyped-def]
        return ExerciseAttemptFeedback(
            attempt_id=attempt.attempt_id,
            exercise_id=attempt.exercise_id,
            is_correct=attempt.is_correct,
            outcome=attempt.outcome,
            correct_answer_display=exercise.correct_answer_display,
            explanation=exercise.explanation,
            error_tags=list(exercise.error_tags if not attempt.is_correct else ()),
        )

    @staticmethod
    def _progress(session: ExerciseSession) -> ExerciseSessionProgress:
        return ExerciseSessionProgress(
            answered=session.answered_exercises,
            total=session.total_exercises,
            correct=session.correct_exercises,
        )
