from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import case, func, literal, select, union_all

from app.core.exceptions import NotFoundError
from app.db.database import get_database
from app.modules.listening.models import ListeningAttemptRow as Listening
from app.modules.practice.models import SavedReviewRow
from app.modules.practice.models import SpeakingAttemptRow as Speaking
from app.modules.reading.models import ReadingAttemptRow as Reading
from app.modules.writing.models import WritingAttemptRow as Writing

ZONE = ZoneInfo("Asia/Almaty")
MODELS = {"listening": Listening, "reading": Reading, "writing": Writing, "speaking": Speaking}


def query(uid, module="all"):
    selects = []
    for name, model in MODELS.items():
        if module not in ("all", name):
            continue
        owner = model.learner_id if name in ("reading", "listening") else model.owner
        completed = model.submitted_at if name in ("reading", "listening") else model.completed_at
        fallback = model.updated_at if name == "writing" else completed
        is_test = (
            literal(False)
            if name == "speaking"
            else (model.mode == "full_exam" if name == "reading" else literal(True))
        )
        stmt = select(
            model.id.label("id"),
            literal(name).label("module"),
            completed.label("completed_at"),
            func.coalesce(completed, fallback).label("sort_at"),
            is_test.label("is_test"),
        ).where(owner == uid)
        if name in ("listening", "reading"):
            stmt = stmt.where(model.result.is_not(None), model.status.in_(["submitted", "expired"]))
        elif name == "writing":
            stmt = stmt.where(model.status == "submitted")
        selects.append(stmt)
    return union_all(*selects).subquery()


def streaks(days, today):
    unique = sorted(set(days))
    longest = run = 0
    previous = None
    for day in unique:
        run = run + 1 if previous and day == previous + timedelta(days=1) else 1
        longest = max(longest, run)
        previous = day
    current = 0
    cursor = today if today in unique else today - timedelta(days=1)
    known = set(unique)
    while cursor in known:
        current += 1
        cursor -= timedelta(days=1)
    return current, longest


class PracticeService:
    def __init__(self, db=None):
        self.db = db or get_database()

    def history(self, uid, module="all", page=1, limit=20, order="desc", day=None):
        table = query(uid, module)
        if day:
            table = (
                select(table)
                .where(
                    func.date(func.timezone("Asia/Almaty", table.c.completed_at))
                    == date.fromisoformat(day)
                )
                .subquery()
            )
        with self.db.session() as s:
            total = s.scalar(select(func.count()).select_from(table))
            page = min(page, max(1, (total + limit - 1) // limit))
            sort = table.c.sort_at.asc() if order == "asc" else table.c.sort_at.desc()
            records = (
                s.execute(
                    select(table)
                    .order_by(sort, table.c.module, table.c.id)
                    .offset((page - 1) * limit)
                    .limit(limit)
                )
                .mappings()
                .all()
            )
            # Bounded bulk reads: no per-attempt ORM/review queries on a history page.
            ids = [r["id"] for r in records]
            rows = {}
            for name in {r["module"] for r in records}:
                model = MODELS[name]
                owner = model.learner_id if name in ("reading", "listening") else model.owner
                rows.update(
                    {
                        (name, r.id): r
                        for r in s.scalars(select(model).where(model.id.in_(ids), owner == uid))
                    }
                )
            counts = {
                (m, aid): n
                for m, aid, n in s.execute(
                    select(SavedReviewRow.module, SavedReviewRow.attempt_id, func.count())
                    .where(SavedReviewRow.owner == uid, SavedReviewRow.attempt_id.in_(ids))
                    .group_by(SavedReviewRow.module, SavedReviewRow.attempt_id)
                )
            }
            items = []
            for record in records:
                name = record["module"]
                r = rows[(name, record["id"])]
                result = getattr(r, "result", None) or {}
                assessment = getattr(r, "assessment", None)
                task = getattr(r, "task_snapshot", None) or {}
                title = (
                    task.get("title")
                    or task.get("prompt")
                    or getattr(r, "exam_id", None)
                    or r.task_id
                )
                if name in ("listening", "reading"):
                    parts = r.exam_id.split("-")
                    if len(parts) == 4 and parts[1].isdigit() and parts[3].isdigit():
                        title = f"Cambridge {int(parts[1])} · {name.title()} Test {int(parts[3])}"
                    if name == "reading" and r.selected_passage:
                        title += f" · Passage {r.selected_passage}"
                if name == "speaking":
                    title = task.get("prompt", r.task_id)
                count = counts.get((name, r.id), 0)
                correct = (
                    result.get("raw_score") if name == "reading" else result.get("correct_count")
                )
                total_questions = result.get("total_questions")
                incorrect = result.get("incorrect_count")
                unanswered = result.get("unanswered_count")
                if incorrect is None and name == "listening":
                    incorrect = sum(
                        q.get("correct") is False and bool(q.get("user_answer", "").strip())
                        for q in result.get("questions", [])
                    )
                    unanswered = sum(
                        not q.get("user_answer", "").strip() for q in result.get("questions", [])
                    )
                if incorrect is None and correct is not None and total_questions is not None:
                    incorrect = total_questions - correct
                items.append(
                    {
                        "id": r.id,
                        "module": name,
                        "title": title,
                        "completed_at": record["completed_at"],
                        "completion_date_known": record["completed_at"] is not None,
                        "correct_count": correct,
                        "incorrect_count": incorrect,
                        "unanswered_count": unanswered,
                        "total_questions": total_questions,
                        "estimated_band": assessment.get("estimated_band")
                        if assessment
                        else result.get("estimated_band"),
                        "ai_status": "saved"
                        if count or assessment
                        else getattr(r, "ai_status", "not_requested")
                        if name != "speaking"
                        else "not_available",
                        "saved_explanations": count,
                        "is_test": record["is_test"],
                    }
                )
            return {"items": items, "total": total, "page": page, "limit": limit}

    def detail(self, uid, aid, include_reviews=True):
        with self.db.session() as s:
            for name, model in MODELS.items():
                owner = model.learner_id if name in ("listening", "reading") else model.owner
                row = s.scalar(select(model).where(model.id == aid, owner == uid))
                if row is None:
                    continue
                if name in ("listening", "reading") and not row.result:
                    continue
                if name == "writing" and row.status != "submitted":
                    continue
                reviews = (
                    s.scalars(
                        select(SavedReviewRow)
                        .where(
                            SavedReviewRow.owner == uid,
                            SavedReviewRow.module == name,
                            SavedReviewRow.attempt_id == aid,
                        )
                        .order_by(SavedReviewRow.created_at)
                    ).all()
                    if include_reviews
                    else []
                )
                return {
                    "id": aid,
                    "module": name,
                    "task": row.task_snapshot if name in ("writing", "speaking") else None,
                    "saved_reviews": [
                        {
                            "question_id": r.question_id,
                            "response": r.response,
                            "created_at": r.created_at,
                            "generation": r.generation,
                        }
                        for r in reviews
                    ],
                    "completed_at": getattr(row, "submitted_at", None)
                    or getattr(row, "completed_at", None),
                }
        raise NotFoundError("Practice attempt not found.")

    def activity(self, uid, now=None):
        today = (now or datetime.now(UTC)).astimezone(ZONE).date()
        table = query(uid)
        with self.db.session() as s:
            totals = s.execute(
                select(
                    func.count(),
                    func.sum(case((table.c.is_test, 1), else_=0)),
                    func.sum(case((table.c.completed_at.is_(None), 1), else_=0)),
                ).select_from(table)
            ).one()
            date = func.date(func.timezone("Asia/Almaty", table.c.completed_at))
            counts = dict(
                s.execute(
                    select(date, func.count())
                    .select_from(table)
                    .where(table.c.completed_at.is_not(None))
                    .group_by(date)
                ).all()
            )
        current, longest = streaks([d for d in counts if d <= today], today)
        days = [
            {
                "date": str(today - timedelta(days=n)),
                "count": counts.get(today - timedelta(days=n), 0),
            }
            for n in range(364, -1, -1)
        ]
        return {
            "timezone": "Asia/Almaty",
            "tests_completed": totals[1] or 0,
            "total_practice_sessions": totals[0],
            "current_streak": current,
            "longest_streak": longest,
            "active_days": sum(d["count"] > 0 for d in days[-30:]),
            "days": days,
            "undated_sessions": totals[2] or 0,
        }
