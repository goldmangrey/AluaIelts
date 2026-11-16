"""Persistent per-input results with PostgreSQL cross-worker single flight.

The lock spans the existing generation call. Failures roll back; only validated
success is committed. Prompt/model changes do not invalidate a stored explanation.
"""

import hashlib
import json
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select, text

from app.core.exceptions import ConflictError, NotFoundError
from app.modules.listening.models import ListeningAttemptRow
from app.modules.practice.models import SavedReviewRow
from app.modules.reading.models import ReadingAttemptRow


def fingerprint(row):
    return hashlib.sha256(
        json.dumps(
            {"snapshot": row.snapshot, "answers": row.answers, "result": row.result},
            sort_keys=True,
            ensure_ascii=False,
        ).encode()
    ).hexdigest()


def saved_review(service, module, uid, aid, question, generate, prompt_version):
    db = service.db if module == "listening" else service.repo.database
    model = ListeningAttemptRow if module == "listening" else ReadingAttemptRow
    with db.session() as session:
        row = session.scalar(select(model).where(model.id == aid, model.learner_id == uid))
        if row is None:
            raise NotFoundError("Attempt not found.")
        if row.status not in {"submitted", "expired"} or not row.result:
            raise ConflictError("Finish the attempt before review.")
        inputs = fingerprint(row)
        key = f"{uid}:{module}:{aid}:{question}:{inputs}"
        session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 7459))"), {"key": key}
        )
        previous = session.scalar(
            select(SavedReviewRow).where(
                SavedReviewRow.owner == uid,
                SavedReviewRow.module == module,
                SavedReviewRow.attempt_id == aid,
                SavedReviewRow.question_id == str(question),
                SavedReviewRow.input_hash == inputs,
            )
        )
        if previous:
            return {**previous.response, "cached": True, "saved_review_id": previous.id}
        response = generate()
        value = response.get("review", response)
        success = (
            value.get("evidence_status") == "found"
            if module == "reading"
            else value.get("evidence", {}).get("available") is True
        )
        if not success:
            return response
        rid = str(uuid4())
        session.add(
            SavedReviewRow(
                id=rid,
                owner=uid,
                module=module,
                attempt_id=aid,
                question_id=str(question),
                input_hash=inputs,
                response=response,
                generation={
                    **response.get("generation", {}),
                    "prompt_version": prompt_version,
                    "legacy_cache": bool(response.get("cached")),
                },
                created_at=datetime.now(UTC),
            )
        )
        return {**response, "saved_review_id": rid}


def read_saved_reviews(module, uid, aid, question=None):
    """Read-only lookup, never an AI call; exactly the same immutable input key."""
    from app.db.database import get_database

    model = ListeningAttemptRow if module == "listening" else ReadingAttemptRow
    with get_database().session() as session:
        row = session.scalar(select(model).where(model.id == aid, model.learner_id == uid))
        if row is None or row.status not in {"submitted", "expired"} or not row.result:
            raise NotFoundError("Completed attempt not found.")
        stmt = select(SavedReviewRow).where(
            SavedReviewRow.owner == uid,
            SavedReviewRow.module == module,
            SavedReviewRow.attempt_id == aid,
            SavedReviewRow.input_hash == fingerprint(row),
        )
        if question is not None:
            stored = session.scalar(stmt.where(SavedReviewRow.question_id == question))
            return {"response": {**stored.response, "cached": True} if stored else None}
        return {
            "questions": list(session.scalars(stmt.with_only_columns(SavedReviewRow.question_id)))
        }
