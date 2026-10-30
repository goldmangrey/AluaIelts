"""Import an offline, read-only JSON document export into PostgreSQL.

The input is either ``{"documents": [{"path": "users/...", "data": {...}}]}``
or a JSON object mapping document paths to document data. This script never connects
to or modifies the remote source. Dry-run validation is the default; pass ``--apply``
only after reviewing the report.
"""

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.db.database import get_database
from app.db.models import (
    AIConversationRow,
    AIMessageRow,
    CanonicalVocabularyStateRow,
    CurriculumStateRow,
    DailyPlanRow,
    ExerciseAnswerRow,
    ExerciseSessionRow,
    LearnerProfileRow,
    LearningEventRow,
    MasteryEvidenceRow,
    MasteryStateRow,
    PartnerInvitationRow,
    PartnerPermissionRow,
    PartnerRelationshipRow,
    ReviewResponseRow,
    ReviewSessionRow,
    VocabularyPackRow,
)
from app.modules.ai_progress.models import AIProgressChatMessage, AIProgressConversation
from app.modules.curriculum.models import UserCurriculumState
from app.modules.daily_plan.models import DailyPlan
from app.modules.exercises.models import ExerciseAttempt, ExerciseSession
from app.modules.learning_events.models import LearningEvent
from app.modules.mastery.models import MasteryState
from app.modules.partner.models import PartnerInvitation, PartnerRelationship
from app.modules.users.models import UserProfile
from app.modules.vocabulary_review.models import (
    DailyLexicalPack,
    VocabularyReviewEvent,
    VocabularyReviewSession,
    VocabularyReviewState,
)


def load_documents(path: Path) -> list[tuple[str, dict[str, Any]]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and isinstance(raw.get("documents"), list):
        return [(str(item["path"]).strip("/"), item["data"]) for item in raw["documents"]]
    if isinstance(raw, dict) and all(isinstance(value, dict) for value in raw.values()):
        return [(str(key).strip("/"), value) for key, value in raw.items()]
    raise ValueError("Expected a document-path map or an object with a documents list.")


def normalize(value: Any) -> Any:
    """Normalize common extended-JSON timestamp wrappers without cloud SDKs."""
    if isinstance(value, list):
        return [normalize(item) for item in value]
    if isinstance(value, dict):
        if set(value) == {"__time__"}:
            return value["__time__"]
        if set(value) == {"timestampValue"}:
            return value["timestampValue"]
        return {key: normalize(item) for key, item in value.items()}
    return value


def as_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise ValueError("Expected an ISO-8601 timestamp")


def add(session: Session | None, row: Any, counts: Counter[str]) -> None:
    counts[row.__tablename__] += 1
    if session is not None:
        session.merge(row)


def import_documents(
    documents: list[tuple[str, dict[str, Any]]], session: Session | None
) -> tuple[Counter[str], list[str]]:
    counts: Counter[str] = Counter()
    unsupported: list[str] = []
    value: Any
    for path, raw_data in sorted(documents, key=lambda item: item[0].count("/")):
        data = normalize(raw_data)
        parts = path.split("/")
        try:
            if len(parts) == 2 and parts[0] == "users":
                uid = parts[1]
                profile = UserProfile.model_validate({**data, "uid": data.get("uid", uid)})
                add(
                    session,
                    LearnerProfileRow(
                        learner_id=uid,
                        display_name=profile.display_name or "Learner",
                        created_at=profile.created_at,
                        updated_at=profile.updated_at,
                        legacy_identity_key=uid,
                        payload=profile.model_dump(mode="json"),
                    ),
                    counts,
                )
            elif len(parts) >= 4 and parts[0] == "users":
                uid, collection, document_id = parts[1], parts[2], parts[3]
                import_user_document(
                    session, counts, unsupported, path, uid, collection, document_id, data
                )
            elif len(parts) == 2 and parts[0] == "partnerRelationships":
                value = PartnerRelationship.model_validate(data)
                add(
                    session,
                    PartnerRelationshipRow(
                        relationship_id=value.relationship_id,
                        learner_id=value.learner_uid,
                        partner_id=value.partner_uid,
                        status=value.status.value,
                        payload=value.model_dump(mode="json"),
                    ),
                    counts,
                )
                settings = value.sharing_settings
                add(
                    session,
                    PartnerPermissionRow(
                        relationship_id=value.relationship_id,
                        daily_activity=settings.share_daily_activity,
                        progress_analytics=settings.share_progress_analytics,
                        ai_analysis=settings.allow_ai_progress_analysis,
                        updated_at=value.updated_at,
                    ),
                    counts,
                )
            elif len(parts) == 2 and parts[0] == "partnerInvites":
                value = PartnerInvitation.model_validate(data)
                add(
                    session,
                    PartnerInvitationRow(
                        code_hash=value.code_hash,
                        learner_id=value.learner_uid,
                        status=value.status.value,
                        expires_at=value.expires_at,
                        payload=value.model_dump(mode="json"),
                    ),
                    counts,
                )
            elif len(parts) >= 4 and parts[0] == "partnerRelationships":
                relationship_id = parts[1]
                if parts[2] == "aiConversations" and len(parts) == 4:
                    conversation = AIProgressConversation.model_validate(data)
                    add(
                        session,
                        AIConversationRow(
                            conversation_id=conversation.conversation_id,
                            relationship_id=relationship_id,
                            created_by_partner_id=conversation.created_by_partner_uid,
                            updated_at=conversation.updated_at,
                            payload=conversation.model_dump(mode="json"),
                        ),
                        counts,
                    )
                elif parts[2] == "aiConversations" and len(parts) == 6 and parts[4] == "messages":
                    message = AIProgressChatMessage.model_validate(data)
                    add(
                        session,
                        AIMessageRow(
                            message_id=message.message_id,
                            conversation_id=parts[3],
                            created_at=message.created_at,
                            role=message.role.value,
                            content=message.content,
                            payload=message.model_dump(mode="json"),
                        ),
                        counts,
                    )
                else:
                    unsupported.append(path)
            elif parts[0] not in {"partnerRelationshipOwners", "partnerInviteOwners"}:
                unsupported.append(path)
        except Exception as exc:
            raise ValueError(f"Invalid document {path}: {exc}") from exc
    return counts, unsupported


def import_user_document(
    session: Session | None,
    counts: Counter[str],
    unsupported: list[str],
    path: str,
    uid: str,
    collection: str,
    document_id: str,
    data: dict[str, Any],
) -> None:
    payload = data
    value: Any
    if collection == "dailyPlans":
        value = DailyPlan.model_validate(payload)
        add(
            session,
            DailyPlanRow(
                learner_id=uid,
                local_date=value.local_date,
                status=value.status.value,
                updated_at=value.updated_at,
                payload=value.model_dump(mode="json"),
            ),
            counts,
        )
    elif collection == "vocabularyDailyPacks":
        value = DailyLexicalPack.model_validate(payload)
        add(
            session,
            VocabularyPackRow(
                learner_id=uid,
                pack_id=value.pack_id,
                local_date=value.local_date,
                schema_version=value.schema_version,
                payload=value.model_dump(mode="json"),
            ),
            counts,
        )
    elif collection == "vocabularyReviewStates":
        value = VocabularyReviewState.model_validate(payload)
        add(
            session,
            CanonicalVocabularyStateRow(
                learner_id=uid,
                lexical_item_id=value.lexical_item_id,
                review_count=value.review_count,
                due_at=value.next_due_at,
                schema_version=value.schema_version,
                payload=value.model_dump(mode="json"),
            ),
            counts,
        )
    elif collection == "vocabularyReviewSessions":
        value = VocabularyReviewSession.model_validate(payload)
        add(
            session,
            ReviewSessionRow(
                learner_id=uid,
                session_id=value.session_id,
                session_type=value.kind.value,
                payload=value.model_dump(mode="json"),
            ),
            counts,
        )
    elif collection == "vocabularyReviewEvents":
        value = VocabularyReviewEvent.model_validate(payload)
        add(
            session,
            ReviewResponseRow(
                learner_id=uid,
                event_id=value.event_id,
                session_id=value.session_id,
                lexical_item_id=value.lexical_item_id,
                rating=value.rating.value,
                occurred_at=value.reviewed_at,
                payload=value.model_dump(mode="json"),
            ),
            counts,
        )
    elif collection == "learningEvents":
        value = LearningEvent.model_validate(payload)
        add(
            session,
            LearningEventRow(
                learner_id=uid,
                event_id=str(value.event_id),
                server_received_at=value.server_received_at,
                event_type=value.event_type.value,
                payload=value.model_dump(mode="json"),
            ),
            counts,
        )
    elif collection == "exerciseSessions" and len(path.split("/")) == 4:
        value = ExerciseSession.model_validate(payload)
        add(
            session,
            ExerciseSessionRow(
                learner_id=uid,
                session_id=value.session_id,
                daily_plan_date=value.daily_plan_date,
                payload=value.model_dump(mode="json"),
            ),
            counts,
        )
    elif (
        collection == "exerciseSessions"
        and len(path.split("/")) == 6
        and path.split("/")[4] == "attempts"
    ):
        value = ExerciseAttempt.model_validate(payload)
        add(
            session,
            ExerciseAnswerRow(
                learner_id=uid,
                session_id=value.session_id,
                exercise_id=value.exercise_id,
                attempt_id=str(value.attempt_id),
                payload=value.model_dump(mode="json"),
            ),
            counts,
        )
    elif collection == "masteryStates":
        value = MasteryState.model_validate(payload)
        add(
            session,
            MasteryStateRow(
                learner_id=uid,
                state_id=value.state_id,
                updated_at=value.updated_at,
                payload=value.model_dump(mode="json"),
            ),
            counts,
        )
    elif collection == "masteryAppliedEvents":
        add(
            session,
            MasteryEvidenceRow(
                application_id=document_id,
                learner_id=uid,
                event_id=str(payload["event_id"]),
                state_id=str(payload["state_id"]),
                applied_at=as_datetime(payload.get("applied_at", datetime.now(UTC))),
                engine_version=str(payload.get("engine_version", 1)),
            ),
            counts,
        )
    elif collection == "curriculum" and document_id == "current":
        value = UserCurriculumState.model_validate(payload)
        add(
            session,
            CurriculumStateRow(
                learner_id=uid, updated_at=value.updated_at, payload=value.model_dump(mode="json")
            ),
            counts,
        )
    else:
        unsupported.append(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export", type=Path)
    parser.add_argument("--apply", action="store_true", help="Write validated documents")
    parser.add_argument("--report", type=Path, help="Optional JSON report output")
    arguments = parser.parse_args()
    documents = load_documents(arguments.export)
    if arguments.apply:
        with get_database().session() as session:
            counts, unsupported = import_documents(documents, session)
    else:
        counts, unsupported = import_documents(documents, None)
    report = {
        "mode": "applied" if arguments.apply else "dry-run",
        "source_documents": len(documents),
        "rows_by_table": dict(sorted(counts.items())),
        "unsupported_paths": unsupported,
    }
    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if arguments.report:
        arguments.report.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
