import copy
import hashlib
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select

from app.core.exceptions import ConflictError, ValidationError
from app.modules.reading.catalog import ReadingCatalog, questions
from app.modules.reading.grading import result_for
from app.modules.reading.models import ReadingAttemptRow, ReadingMutationRow
from app.modules.reading.repository import ReadingRepository


def utcnow():
    return datetime.now(UTC)


class ReadingService:
    def __init__(self, repository: ReadingRepository, catalog: ReadingCatalog, clock=utcnow):
        self.repo, self.catalog, self.clock = repository, catalog, clock

    @staticmethod
    def mutation_hash(operation, aid, payload):
        return hashlib.sha256(
            json.dumps(
                {"operation": operation, "attempt_id": aid, "payload": payload},
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode()
        ).hexdigest()

    @staticmethod
    def replay(session, uid, event_id, fingerprint):
        event = session.get(ReadingMutationRow, (uid, str(event_id)))
        if event:
            if event.mutation_hash != fingerprint:
                raise ConflictError(
                    "Event UUID was already used with a different payload.",
                    "reading_event_conflict",
                )
            return copy.deepcopy(event.response)
        return None

    @staticmethod
    def record(session, uid, event_id, aid, fingerprint, response, now):
        session.add(
            ReadingMutationRow(
                learner_id=uid,
                event_id=str(event_id),
                attempt_id=aid,
                mutation_hash=fingerprint,
                response=response,
                created_at=now,
            )
        )

    def create(self, uid, request):
        payload = request.model_dump(mode="json")
        fingerprint = self.mutation_hash("create", None, payload)
        with self.repo.transaction(uid) as session:
            replay = self.replay(session, uid, request.event_id, fingerprint)
            if replay is not None:
                return replay
            entry = self.catalog.enabled(request.exam_id)
            now = self.clock()
            selected = request.selected_passage or 1
            snapshot = {
                "exam": self.catalog.exams[request.exam_id],
                "key": self.catalog.keys[request.exam_id],
                "metadata": entry,
            }
            row = ReadingAttemptRow(
                id=str(uuid4()),
                learner_id=uid,
                exam_id=request.exam_id,
                dataset_version=entry["dataset_version"],
                content_hash=entry["content_hash"],
                content_revision=entry["content_revision"],
                mode=request.mode,
                selected_passage=request.selected_passage,
                status="in_progress",
                version=0,
                started_at=now,
                deadline_at=now + timedelta(seconds=3600) if request.mode == "full_exam" else None,
                submitted_at=None,
                created_at=now,
                updated_at=now,
                snapshot=copy.deepcopy(snapshot),
                answers={},
                state={
                    "current_passage": selected,
                    "annotations": [],
                    "crossed_options": [],
                    "checked_question_ids": [],
                    "reported_active_seconds": {},
                },
                result=None,
            )
            session.add(row)
            session.flush()
            response = self.view(row, now)
            self.record(session, uid, request.event_id, row.id, fingerprint, response, now)
            return response

    @staticmethod
    def selected_questions(row):
        return {
            qid: triple
            for qid, triple in questions(row.snapshot["exam"]).items()
            if row.selected_passage is None or triple[0]["number"] == row.selected_passage
        }

    @staticmethod
    def elapsed(row, now):
        elapsed = max(0, int((now - row.started_at).total_seconds()))
        return min(elapsed, 3600) if row.mode == "full_exam" else elapsed

    def finish(self, row, now, *, expired=False):
        row.status = "expired" if expired else "submitted"
        row.submitted_at = row.deadline_at if expired else now
        row.updated_at = now
        row.version += 1
        row.result = result_for(
            row.snapshot,
            row.answers,
            row.mode,
            row.selected_passage,
            self.elapsed(row, row.submitted_at),
            row.state["reported_active_seconds"],
        )
        row.result = {
            "attempt_id": row.id,
            **row.result,
            "completion_reason": "deadline" if expired else "submitted",
        }

    def expire(self, row, now):
        if row.status == "in_progress" and row.deadline_at and now >= row.deadline_at:
            self.finish(row, now, expired=True)

    def view(self, row, now, *, include_exam=False):
        result = {
            "id": row.id,
            "exam_id": row.exam_id,
            "dataset_version": row.dataset_version,
            "content_hash": row.content_hash,
            "content_revision": row.content_revision,
            "mode": row.mode,
            "selected_passage": row.selected_passage,
            "status": row.status,
            "version": row.version,
            "started_at": row.started_at.astimezone(UTC).isoformat(),
            "deadline_at": row.deadline_at.astimezone(UTC).isoformat() if row.deadline_at else None,
            "submitted_at": row.submitted_at.astimezone(UTC).isoformat()
            if row.submitted_at
            else None,
            "server_now": now.isoformat(),
            "remaining_seconds": max(0, int((row.deadline_at - now).total_seconds()))
            if row.deadline_at and row.status == "in_progress"
            else 0
            if row.deadline_at
            else None,
            "elapsed_seconds": self.elapsed(row, row.submitted_at or now),
            "answers": copy.deepcopy(row.answers),
            "state": copy.deepcopy(row.state),
            "content_status": row.snapshot["metadata"]["content_status"],
            "not_fully_proofread": row.snapshot["metadata"]["not_fully_proofread"],
            "timing_status": "server_deadline_enforced"
            if row.mode == "full_exam"
            else "untimed_practice",
        }
        if include_exam and row.mode == "passage_practice" and row.state["checked_question_ids"]:
            result["checked_result"] = result_for(
                row.snapshot,
                row.answers,
                row.mode,
                row.selected_passage,
                self.elapsed(row, row.submitted_at or now),
                row.state["reported_active_seconds"],
                only=set(row.state["checked_question_ids"]),
            )
        if include_exam:
            result["exam"] = self.catalog.public_exam(row.snapshot["exam"])
            if row.selected_passage is not None:
                result["exam"]["passages"] = [
                    p for p in result["exam"]["passages"] if p["number"] == row.selected_passage
                ]
                result["exam"]["question_count"] = len(self.selected_questions(row))
        return result

    def get(self, uid, aid):
        with self.repo.transaction(uid) as session:
            row = self.repo.attempt(session, uid, aid)
            now = self.clock()
            self.expire(row, now)
            return self.view(row, now, include_exam=True)

    def list(self, uid, limit=50, offset=0):
        with self.repo.transaction(uid) as session:
            rows = session.scalars(
                select(ReadingAttemptRow)
                .where(ReadingAttemptRow.learner_id == uid)
                .order_by(ReadingAttemptRow.started_at.desc(), ReadingAttemptRow.id)
                .limit(limit)
                .offset(offset)
                .with_for_update()
            ).all()
            now = self.clock()
            items = []
            for row in rows:
                self.expire(row, now)
                view = self.view(row, now)
                view.pop("answers")
                view.pop("state")
                view["raw_score"] = row.result["raw_score"] if row.result else None
                view["estimated_band"] = row.result["estimated_band"] if row.result else None
                items.append(view)
            return {"items": items, "limit": limit, "offset": offset}

    def library(self, uid, book=None):
        with self.repo.transaction(uid) as session:
            rows = session.scalars(
                select(ReadingAttemptRow)
                .where(ReadingAttemptRow.learner_id == uid)
                .order_by(ReadingAttemptRow.started_at.desc())
                .with_for_update()
            ).all()
            now = self.clock()
            for row in rows:
                self.expire(row, now)
            items = []
            for eid, entry in self.catalog.entries.items():
                if book is not None and entry["source_book"] != book:
                    continue
                attempts = [r for r in rows if r.exam_id == eid]
                done = [r for r in attempts if r.status != "in_progress"]
                active = [r for r in attempts if r.status == "in_progress"]
                bands = [
                    r.result["estimated_band"]
                    for r in done
                    if r.result and r.result["estimated_band"] is not None
                ]
                items.append(
                    {k: copy.deepcopy(v) for k, v in entry.items() if k != "answer_key_hash"}
                    | {
                        "completed_attempts": len(done),
                        "in_progress_attempt_ids": [r.id for r in active],
                        "best_estimated_band": max(bands) if bands else None,
                    }
                )
            return {
                "items": items,
                "dataset_version": self.catalog.manifest["dataset_version"],
                "practice_policy_version": "private-practice-v1",
            }

    def mutate(self, uid, aid, operation, request, *, question_id=None):
        payload = request.model_dump(mode="json")
        fingerprint = self.mutation_hash(operation, aid, {**payload, "question_id": question_id})
        with self.repo.transaction(uid) as session:
            row = self.repo.attempt(session, uid, aid)
            now = self.clock()
            # Deadline authority always uses receipt time AFTER acquiring the transaction lock.
            self.expire(row, now)
            replay = self.replay(session, uid, request.event_id, fingerprint)
            if replay is not None:
                return replay
            if row.status != "in_progress":
                if operation == "submit":
                    response = self.view(row, now) | {"result": row.result}
                elif row.status == "expired":
                    response = self.view(row, now) | {
                        "mutation_applied": False,
                        "rejection_reason": "deadline_passed",
                    }
                else:
                    raise ConflictError(
                        "Completed attempts cannot be modified.", "reading_attempt_completed"
                    )
                self.record(session, uid, request.event_id, aid, fingerprint, response, now)
                return response
            if request.expected_version != row.version:
                raise ConflictError(
                    f"Version conflict; fetch attempt. Current version: {row.version}.",
                    "reading_version_conflict",
                )
            selected = self.selected_questions(row)
            if operation in {"answer", "batch"}:
                changes = (
                    {question_id: request.answer} if operation == "answer" else request.answers
                )
                if set(changes) - set(selected):
                    raise ValidationError(
                        "Question is outside this attempt.", "reading_question_scope"
                    )
                if set(changes) & set(row.state["checked_question_ids"]):
                    raise ConflictError(
                        "Checked practice answers are frozen.", "reading_answer_checked"
                    )
                row.answers = {**row.answers, **changes}
            elif operation == "state":
                self.update_state(row, request, now)
            elif operation == "check":
                if row.mode != "passage_practice":
                    raise ConflictError(
                        "Checks are only available in passage practice.",
                        "reading_check_not_allowed",
                    )
                checking = set(request.question_ids)
                if checking - set(selected):
                    raise ValidationError(
                        "Question is outside this attempt.", "reading_question_scope"
                    )
                # A linked unordered group is an atomic check; revealing one unit reveals the group.
                for key in row.snapshot["key"]["answers"]:
                    if key["question_id"] in checking and key["grading_group"]:
                        group = key["grading_group"]
                        checking.update(
                            k["question_id"]
                            for k in row.snapshot["key"]["answers"]
                            if k["grading_group"] and k["grading_group"]["id"] == group["id"]
                        )
                row.state = {
                    **row.state,
                    "checked_question_ids": sorted(
                        set(row.state["checked_question_ids"]) | checking
                    ),
                }
            elif operation == "submit":
                self.finish(row, now)
            else:
                raise ValueError("Unknown Reading mutation")
            if operation != "submit":
                row.version += 1
                row.updated_at = now
            response = self.view(row, now) | {"mutation_applied": True}
            if operation == "submit":
                response["result"] = row.result
            elif operation == "check":
                response["checked_result"] = result_for(
                    row.snapshot,
                    row.answers,
                    row.mode,
                    row.selected_passage,
                    self.elapsed(row, now),
                    row.state["reported_active_seconds"],
                    only=checking,
                )
            self.record(session, uid, request.event_id, aid, fingerprint, response, now)
            return response

    def update_state(self, row, request, now):
        passages = {
            p["id"]: p
            for p in row.snapshot["exam"]["passages"]
            if row.selected_passage is None or p["number"] == row.selected_passage
        }
        if request.current_passage not in {p["number"] for p in passages.values()}:
            raise ValidationError("Passage is outside this attempt.")
        state = copy.deepcopy(row.state)
        if request.annotations is not None:
            if len({a.id for a in request.annotations}) != len(request.annotations):
                raise ValidationError("Annotation IDs must be unique.")
            for a in request.annotations:
                p = passages.get(a.passage_id)
                if (
                    a.content_hash != row.content_hash
                    or p is None
                    or a.block_index >= len(p["content"])
                ):
                    raise ValidationError("Annotation content version or passage is invalid.")
                text = p["content"][a.block_index]["text"]
                if not (a.start < a.end <= len(text)) or text[a.start : a.end] != a.quote:
                    raise ValidationError(
                        "Annotation quote must match its Unicode codepoint range."
                    )
            state["annotations"] = [a.model_dump(mode="json") for a in request.annotations]
        if request.crossed_options is not None:
            qs = self.selected_questions(row)
            for crossed in request.crossed_options:
                if crossed.question_id not in qs:
                    raise ValidationError("Crossed option is outside this attempt.")
                _, g, q = qs[crossed.question_id]
                allowed = {o["label"] for o in q["options"] + g["options"]}
                allowed.update(q["constraints"]["allowed_values"])
                if crossed.option_label not in allowed:
                    raise ValidationError("Unknown option label.")
            state["crossed_options"] = [c.model_dump() for c in request.crossed_options]
        # Only short server-observed heartbeat intervals count as reported activity.
        # These are NOT proof of attention; closed-app gaps never inflate passage times.
        interval = min(30, max(0, int((now - row.updated_at).total_seconds())))
        times = state["reported_active_seconds"]
        prior = str(state["current_passage"])
        times[prior] = times.get(prior, 0) + interval
        state["current_passage"] = request.current_passage
        row.state = state

    def result(self, uid, aid):
        with self.repo.transaction(uid) as session:
            row = self.repo.attempt(session, uid, aid)
            self.expire(row, self.clock())
            if row.result is None:
                raise ConflictError(
                    "Submit the attempt before accessing its result.", "reading_result_unavailable"
                )
            return copy.deepcopy(row.result)
