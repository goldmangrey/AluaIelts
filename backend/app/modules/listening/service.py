import copy
import hashlib
import secrets
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import delete, select, text
from sqlalchemy.orm import load_only

from app.core.exceptions import ConflictError, NotFoundError, UnauthorizedError, ValidationError
from app.modules.listening.catalog import digest, questions
from app.modules.listening.grading import result_for
from app.modules.listening.models import (
    ListeningAttemptRow as Attempt,
)
from app.modules.listening.models import (
    ListeningGrantRow as Grant,
)
from app.modules.listening.models import (
    ListeningMutationRow as Mutation,
)


def utcnow():
    return datetime.now(UTC)


class ListeningService:
    def __init__(self, database, catalog, clock=utcnow):
        self.db, self.catalog, self.clock = database, catalog, clock

    @contextmanager
    def transaction(self, uid):
        with self.db.session() as session:
            session.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
                {"key": "listening:" + uid},
            )
            yield session

    @staticmethod
    def owned(session, uid, aid):
        row = session.scalar(
            select(Attempt).where(Attempt.id == aid, Attempt.learner_id == uid).with_for_update()
        )
        if row is None:
            raise NotFoundError("Listening attempt not found.")
        return row

    @staticmethod
    def replay(session, uid, event, fingerprint):
        row = session.get(Mutation, (uid, str(event)))
        if row:
            if row.mutation_hash != fingerprint:
                raise ConflictError("Event payload differs.", "listening_event_conflict")
            return copy.deepcopy(row.response)

    def record(self, session, uid, event, aid, fingerprint, response):
        session.add(
            Mutation(
                learner_id=uid,
                event_id=str(event),
                attempt_id=aid,
                mutation_hash=fingerprint,
                response=response,
                created_at=self.clock(),
            )
        )

    def view(self, row, include_exam=False):
        result = {
            "id": row.id,
            "exam_id": row.exam_id,
            "status": row.status,
            "version": row.version,
            "mode": row.snapshot["mode"],
            "content_hash": row.snapshot["content_hash"],
            "key_hash": row.snapshot["key_hash"],
            "dataset_version": row.snapshot["dataset_version"],
            "answers": copy.deepcopy(row.answers),
            "state": copy.deepcopy(row.state),
            "started_at": row.started_at.astimezone(UTC).isoformat(),
            "submitted_at": row.submitted_at.astimezone(UTC).isoformat()
            if row.submitted_at
            else None,
        }
        if include_exam:
            result["exam"] = self.catalog.public_exam(row.snapshot["exam"])
        return result

    def library(self, uid):
        with self.transaction(uid) as session:
            rows = session.scalars(
                select(Attempt)
                .options(
                    load_only(
                        Attempt.id,
                        Attempt.exam_id,
                        Attempt.status,
                        Attempt.answers,
                        Attempt.started_at,
                    )
                )
                .where(Attempt.learner_id == uid)
                .order_by(Attempt.started_at.desc())
            ).all()
            entries = []
            for eid in self.catalog.exams:
                entry = self.catalog.entry(eid)
                active = next(
                    (r for r in rows if r.exam_id == eid and r.status == "in_progress"), None
                )
                entry.update(
                    {
                        "active_attempt_id": active.id if active else None,
                        "answered_count": sum(bool(v.strip()) for v in active.answers.values())
                        if active
                        else 0,
                        "completed_count": sum(
                            r.exam_id == eid and r.status == "submitted" for r in rows
                        ),
                    }
                )
                entries.append(entry)
            return {"items": entries, "dataset_version": self.catalog.manifest["schema_version"]}

    def create(self, uid, request):
        fp = digest({"operation": "create", "payload": request.model_dump(mode="json")})
        with self.transaction(uid) as session:
            replay = self.replay(session, uid, request.event_id, fp)
            if replay is not None:
                return replay
            row = None
            if request.reuse_active:
                row = session.scalar(
                    select(Attempt)
                    .where(
                        Attempt.learner_id == uid,
                        Attempt.exam_id == request.exam_id,
                        Attempt.status == "in_progress",
                    )
                    .order_by(Attempt.started_at.desc())
                    .limit(1)
                )
            if row is None:
                now = self.clock()
                snapshot = self.catalog.snapshot(request.exam_id)
                row = Attempt(
                    id=str(uuid4()),
                    learner_id=uid,
                    exam_id=request.exam_id,
                    status="in_progress",
                    version=0,
                    snapshot=snapshot,
                    answers={},
                    state={
                        "displayed_part": 1,
                        "current_question": 1,
                        "audio_part": 1,
                        "playback_seconds": 0,
                        "marked": [],
                    },
                    result=None,
                    started_at=now,
                    updated_at=now,
                    submitted_at=None,
                )
                session.add(row)
                session.flush()
            response = self.view(row, True)
            self.record(session, uid, request.event_id, row.id, fp, response)
            return response

    def get(self, uid, aid):
        with self.transaction(uid) as session:
            return self.view(self.owned(session, uid, aid), True)

    def mutate(self, uid, aid, operation, request):
        fp = digest(
            {"operation": operation, "attempt_id": aid, "payload": request.model_dump(mode="json")}
        )
        with self.transaction(uid) as session:
            row = self.owned(session, uid, aid)
            replay = self.replay(session, uid, request.event_id, fp)
            if replay is not None:
                return replay
            if row.status == "submitted":
                if operation != "submit":
                    raise ConflictError("Finished attempts cannot change.", "listening_terminal")
                response = self.view(row)
                self.record(session, uid, request.event_id, aid, fp, response)
                return response
            if request.expected_version != row.version:
                raise ConflictError(
                    "A newer save exists. Reload and reconcile your draft.",
                    "listening_version_conflict",
                )
            if operation == "sync":
                if not set(request.answers) <= set(questions(row.snapshot["exam"])):
                    raise ValidationError("Unknown answer position.")
                row.answers = copy.deepcopy(request.answers)
                row.state = request.state.model_dump(mode="json")
            else:
                row.result = result_for(row.snapshot, row.answers)
                row.status = "submitted"
                row.submitted_at = self.clock()
            row.version += 1
            row.updated_at = self.clock()
            response = self.view(row)
            self.record(session, uid, request.event_id, aid, fp, response)
            return response

    def result(self, uid, aid, review=False):
        with self.transaction(uid) as session:
            row = self.owned(session, uid, aid)
            if row.status != "submitted":
                raise ConflictError("Finish the attempt before review.", "listening_not_submitted")
            result = copy.deepcopy(row.result)
            if review:
                result["exam"] = self.catalog.public_exam(row.snapshot["exam"])
            result["attempt_id"] = aid
            return result

    def grant(self, uid, aid):
        with self.transaction(uid) as session:
            self.owned(session, uid, aid)
            now = self.clock()
            session.execute(delete(Grant).where(Grant.learner_id == uid, Grant.expires_at <= now))
            token = secrets.token_urlsafe(32)
            expires = now + timedelta(minutes=15)
            session.add(
                Grant(
                    token_hash=hashlib.sha256(token.encode()).hexdigest(),
                    attempt_id=aid,
                    learner_id=uid,
                    expires_at=expires,
                )
            )
            return {"grant": token, "expires_at": expires.isoformat(), "expires_in": 900}

    def playback_record(self, aid, part, token):
        if not token:
            raise UnauthorizedError("Playback authorization required.")
        with self.db.session() as session:
            grant = session.get(Grant, hashlib.sha256(token.encode()).hexdigest())
            if not grant or grant.attempt_id != aid or grant.expires_at <= self.clock():
                raise UnauthorizedError("Playback authorization expired.")
            row = session.get(Attempt, aid)
            if not row or row.learner_id != grant.learner_id:
                raise UnauthorizedError("Invalid playback access.")
            audio = row.snapshot["audio"]
            record = audio.get(str(part), audio.get(part))
            if not record:
                raise NotFoundError("Audio part not found.")
            return copy.deepcopy(record)

    def asset(self, uid, aid, asset):
        with self.transaction(uid) as session:
            row = self.owned(session, uid, aid)
            return self.catalog.asset(row.snapshot["exam"], asset)
