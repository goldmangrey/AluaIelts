from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.database import get_database
from app.db.models import ExerciseAnswerRow, ExerciseSessionRow
from app.modules.grammar.content_repository import get_grammar_content_repository
from app.modules.learning_quality.questions import QUESTIONS
from app.modules.learning_quality.repository import QualityRepository
from app.modules.vocabulary_review.lexicon_repository import get_canonical_lexicon_repository

router = APIRouter(prefix="/learning-quality", tags=["learning-quality"])
MIN_TOPIC_ATTEMPTS = 3
MIN_TOPIC_ERRORS = 2
WEAK_TOPIC_ERROR_RATE = 0.5

Identity = Annotated[AuthenticatedUser, Depends(get_current_user)]


class Answer(BaseModel):
    question_id: int = Field(ge=0, lt=len(QUESTIONS))
    choice: int | None = Field(default=None, ge=0, le=2)


def presentation(state):
    answers = state.get("answers", {})
    return {
        "version": 1,
        "answered": len(answers),
        "total": len(QUESTIONS),
        "result": state.get("result"),
        "question": (
            {
                "id": len(answers),
                "prompt": QUESTIONS[len(answers)][2],
                "options": QUESTIONS[len(answers)][3],
            }
            if len(answers) < len(QUESTIONS)
            else None
        ),
    }


@router.get("/diagnostic")
def diagnostic(identity: Identity):
    return presentation(QualityRepository().get(identity.uid, "diagnostic:v1"))


@router.post("/diagnostic/answers")
def answer(request: Answer, identity: Identity):
    def change(state):
        answers = state.setdefault("answers", {})
        key = str(request.question_id)
        if key in answers:
            if answers[key] != request.choice:
                raise HTTPException(409, "Answer already saved")
            return
        if request.question_id != len(answers):
            raise HTTPException(409, "Answer the current question")
        answers[key] = request.choice
        if len(answers) == len(QUESTIONS):
            correct = [answers[str(i)] == q[4] for i, q in enumerate(QUESTIONS)]
            # Require foundations before increasing starting difficulty.
            level = "A1"
            for label, end in [("A2", 4), ("B1", 7), ("B2", 10), ("C1", 12)]:
                if sum(correct[:end]) >= end * 0.75:
                    level = label
                else:
                    break
            state["result"] = {
                "difficulty": level,
                "gaps": [q[0] for i, q in enumerate(QUESTIONS) if not correct[i]],
                "completed_at": datetime.now(UTC).isoformat(),
                "notice": "Приблизительная сложность курса, не официальный CEFR или IELTS.",
            }

    return presentation(QualityRepository().mutate(identity.uid, "diagnostic:v1", change))


class Action(BaseModel):
    action: Literal["hide", "unhide", "known", "unknown", "report"]
    event_id: UUID
    error_type: Literal["translation", "example", "grammar", "other"] = "other"
    comment: str = Field(default="", max_length=1000)


@router.post("/items/{item_id}/actions")
def action(item_id: str, request: Action, identity: Identity):
    canonical = get_canonical_lexicon_repository().resolve_id(item_id)
    if canonical is None:
        raise HTTPException(404, "Item not found")
    repo = QualityRepository()
    if request.action == "report":
        payload = {
            "item_id": canonical,
            "error_type": request.error_type,
            "comment": request.comment,
            "created_at": datetime.now(UTC).isoformat(),
        }
        repo.mutate(
            identity.uid,
            f"report:{request.event_id}",
            lambda p: p.update(payload) if not p else None,
        )
    else:

        def change(p):
            if request.action in ("hide", "unhide"):
                p["hidden"] = request.action == "hide"
            else:
                p["verification_pending"] = True
                p["self_assessment"] = request.action
                # A declaration is never evidence of recall or mastery.

        repo.mutate(identity.uid, f"item:{canonical}", change)
    return {"saved": True}


@router.get("/grammar-topics")
def grammar_topics(identity: Identity):
    totals = {}
    with get_database().session() as session:
        rows = session.execute(
            select(ExerciseAnswerRow, ExerciseSessionRow)
            .join(
                ExerciseSessionRow,
                (ExerciseSessionRow.learner_id == ExerciseAnswerRow.learner_id)
                & (ExerciseSessionRow.session_id == ExerciseAnswerRow.session_id),
            )
            .where(ExerciseAnswerRow.learner_id == identity.uid)
        )
        for answer_row, session_row in rows:
            payload = session_row.payload
            if payload.get("content_type") != "grammar_lesson":
                continue
            topic = payload["content_id"]
            value = totals.setdefault(
                topic,
                {
                    "topic_id": topic,
                    "title": get_grammar_content_repository().get_lesson(topic).title,
                    "attempts": 0,
                    "errors": 0,
                    "unknown": 0,
                },
            )
            value["attempts"] += 1
            value["errors"] += not answer_row.payload["is_correct"]
            value["unknown"] += answer_row.payload.get("answer_status") == "unknown"
    return {
        "topics": [
            dict(
                v,
                weak=v["attempts"] >= MIN_TOPIC_ATTEMPTS
                and v["errors"] >= MIN_TOPIC_ERRORS
                and v["errors"] / v["attempts"] >= WEAK_TOPIC_ERROR_RATE,
            )
            for v in totals.values()
        ]
    }
