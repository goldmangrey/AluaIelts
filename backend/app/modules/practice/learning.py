"""Owned read projections over immutable results; only review state is new storage."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import text

from app.core.exceptions import NotFoundError
from app.db.database import get_database

# Keep all graded answers for denominators; unanswered answers are never mistakes.
ANSWERS = """
WITH answers AS (
 SELECT 'listening' AS module, a.id AS attempt_id, a.submitted_at
AS completed_at,
 a.exam_id AS title, q->>'question_id' AS item_key,
q->>'question_number' AS review_key,
 q->>'question_number' AS number,
q->>'user_answer' AS answer,
 q->>'correct_answer' AS correct_answer,
(q->>'correct')::boolean AS correct,
 coalesce(q->>'user_answer','') !~ '[^[:space:]]'
AS unanswered,
 (SELECT g->>'question_type' FROM
jsonb_array_elements(a.snapshot->'exam'->'parts') p,
jsonb_array_elements(p->'groups') g, jsonb_array_elements(g->'questions') meta
 WHERE
meta->>'question_id'=q->>'question_id' LIMIT 1) AS category,
 NULL::jsonb AS feedback
FROM listening_attempts a, jsonb_array_elements(a.result->'questions') q
 WHERE
a.learner_id=:uid AND a.status='submitted' AND a.result IS NOT NULL
 UNION ALL
 SELECT
'reading',a.id,a.submitted_at,a.exam_id,q->>'question_id',q->>'question_id',
q->>'number',q->>'user_answer',q->>'correct_answer',(q->>'is_correct')::boolean,
(q->>'unanswered')::boolean,q->>'question_type',NULL::jsonb
 FROM reading_attempts
a,jsonb_array_elements(a.result->'positions') q
 WHERE a.learner_id=:uid AND a.status
IN ('submitted','expired') AND a.result IS NOT NULL
), mistakes_raw AS (
 SELECT *
FROM answers WHERE correct=false AND unanswered=false
 UNION ALL
 SELECT
'writing',a.id,a.completed_at,coalesce(a.task_snapshot->>'title',a.task_id),
'issue-'||md5(q::text),NULL,NULL,q->>'quote',q->>'better',false,false,
q->>'category',q || jsonb_build_object('assessment_criteria',a.assessment->'criteria')
 FROM writing_attempts
a,jsonb_array_elements(coalesce(a.assessment->'issues','[]'::jsonb)) q
 WHERE
a.owner=:uid AND a.status='submitted'
), mistakes AS (
 SELECT DISTINCT
ON(module,attempt_id,item_key) * FROM mistakes_raw
), marked AS (
 SELECT
m.*,coalesce(s.reviewed,false) AS reviewed FROM mistakes m
 LEFT JOIN
practice_mistake_states s ON s.owner=:uid AND s.module=m.module
 AND
s.attempt_id=m.attempt_id AND s.item_key=m.item_key
)"""


def bounds(period):
    today = datetime.now(ZoneInfo("Asia/Almaty")).date()
    start = (
        datetime.combine(
            today - timedelta(days=int(period) - 1), datetime.min.time(), ZoneInfo("Asia/Almaty")
        )
        if period != "all"
        else None
    )
    end = datetime.combine(today + timedelta(days=1), datetime.min.time(), ZoneInfo("Asia/Almaty"))
    return start, end


def title(value):
    parts = value.split("-")
    if len(parts) == 4 and parts[0] == "cambridge" and parts[1].isdigit() and parts[3].isdigit():
        return f"Cambridge {int(parts[1])} · Test {int(parts[3])}"
    return value


class LearningService:
    def __init__(self, db=None):
        self.db = db or get_database()

    def drafts(self, uid, page=1, limit=20):
        sql = """WITH drafts AS (
        SELECT id,'listening' AS module,exam_id AS
title,updated_at,answers,state,
        NULL::timestamptz AS deadline_at,NULL::integer
AS word_count
        FROM listening_attempts WHERE learner_id=:uid AND
status='in_progress'
        UNION ALL
        SELECT
id,'reading',exam_id,updated_at,answers,state,deadline_at,NULL
        FROM
reading_attempts WHERE learner_id=:uid AND status='in_progress'
        AND
(deadline_at IS NULL OR deadline_at>now())
        UNION ALL
        SELECT
id,'writing',coalesce(task_snapshot->>'title',task_id),updated_at,
'{}'::jsonb,'{}'::jsonb,NULL,word_count FROM writing_attempts
        WHERE owner=:uid
AND status='draft'
        )"""
        args = dict(uid=uid, limit=limit, offset=(page - 1) * limit)
        with self.db.session() as s:
            total = s.scalar(text(sql + "SELECT count(*) FROM drafts"), args)
            rows = (
                s.execute(
                    text(
                        sql + "SELECT * FROM drafts ORDER BY updated_at DESC,id "
                        "LIMIT :limit OFFSET :offset"
                    ),
                    args,
                )
                .mappings()
                .all()
            )
        items = []
        for r in rows:
            state = r["state"]
            module = r["module"]
            answered = sum(bool(str(v).strip()) for v in r["answers"].values())
            position = (
                f"Part {state.get('displayed_part', 1)} · "
                f"Question {state.get('current_question', 1)}"
                if module == "listening"
                else f"Passage {state.get('current_passage', 1)}"
                if module == "reading"
                else f"{r['word_count']} words"
            )
            items.append(
                dict(
                    id=r["id"],
                    module=module,
                    title=title(r["title"]),
                    updated_at=r["updated_at"],
                    answered=answered,
                    position=position,
                    deadline_at=r["deadline_at"],
                    href=f"/{module}/attempts/{r['id']}",
                )
            )
        return dict(items=items, total=total, page=page, limit=limit)

    def mistakes(
        self, uid, module="all", search="", order="newest", page=1, limit=20, include_reviews=True
    ):
        where = """ WHERE (:module='all' OR module=:module) AND (title ILIKE :search OR answer ILIKE
:search OR correct_answer ILIKE :search OR feedback::text ILIKE :search)"""
        sort = {
            "newest": "completed_at DESC NULLS LAST",
            "oldest": "completed_at ASC NULLS LAST",
            "unreviewed": "reviewed ASC,completed_at DESC NULLS LAST",
        }[order]
        args = dict(
            uid=uid,
            module=module,
            search="%" + "%".join(search.split()) + "%",
            limit=limit,
            offset=(page - 1) * limit,
            include_reviews=include_reviews,
        )
        with self.db.session() as s:
            total = s.scalar(text(ANSWERS + "SELECT count(*) FROM marked" + where), args)
            rows = (
                s.execute(
                    text(
                        ANSWERS
                        + """SELECT marked.*, CASE WHEN :include_reviews
THEN rv.response ELSE NULL END
AS saved_review,
rv.response IS NOT NULL AS has_saved_review FROM marked
LEFT JOIN LATERAL (SELECT response FROM practice_saved_reviews
 WHERE owner=:uid AND module=marked.module AND attempt_id=marked.attempt_id
 AND question_id=marked.review_key ORDER BY created_at DESC LIMIT 1) rv ON true"""
                        + where
                        + f" ORDER BY {sort},module,attempt_id,item_key LIMIT :limit OFFSET :offset"
                    ),
                    args,
                )
                .mappings()
                .all()
            )
            items = []
            for row in rows:
                r = dict(row)
                r["title"] = title(r["title"])
                suffix = "results" if r["module"] == "writing" else "review"
                r["href"] = f"/{r['module']}/attempts/{r['attempt_id']}/{suffix}"
                if r["review_key"]:
                    r["href"] += "?question=" + r["review_key"]
                items.append(r)
        return dict(items=items, total=total, page=page, limit=limit)

    def mark(self, uid, module, aid, key, reviewed):
        args = dict(uid=uid, module=module, aid=aid, key=key, reviewed=reviewed)
        with self.db.session() as s:
            exists = s.scalar(
                text(
                    ANSWERS + "SELECT count(*) FROM mistakes WHERE module=:module "
                    "AND attempt_id=:aid AND item_key=:key"
                ),
                args,
            )
            if not exists:
                raise NotFoundError("Mistake not found.")
            s.execute(
                text("""INSERT INTO
practice_mistake_states(owner,module,attempt_id,item_key,reviewed,updated_at)
VALUES(:uid,:module,:aid,:key,:reviewed,now()) ON
CONFLICT(owner,module,attempt_id,item_key)
            DO UPDATE SET
reviewed=EXCLUDED.reviewed,updated_at=EXCLUDED.updated_at"""),
                args,
            )
        return dict(reviewed=reviewed)

    def analytics(self, uid, period="30"):
        start, end = bounds(period)
        args = dict(uid=uid, start=start, end=end)
        from sqlalchemy import func, or_, select

        from app.modules.practice.service import query

        table = query(uid)
        with self.db.session() as s:
            predicate = table.c.completed_at < end
            if start:
                predicate = predicate & (table.c.completed_at >= start)
            else:
                predicate = or_(table.c.completed_at.is_(None), predicate)
            counts = dict(
                s.execute(
                    select(table.c.module, func.count()).where(predicate).group_by(table.c.module)
                ).all()
            )
            summary = (
                s.execute(
                    text(
                        ANSWERS
                        + """SELECT count(*) AS total,count(*) FILTER(WHERE reviewed) AS reviewed
            FROM
marked WHERE (CAST(:start AS timestamptz) IS NULL OR completed_at>=:start)
AND (completed_at<:end OR completed_at IS NULL)"""
                    ),
                    args,
                )
                .mappings()
                .one()
            )
            weak = (
                s.execute(
                    text(
                        ANSWERS
                        + """SELECT module,category,count(DISTINCT attempt_id) AS attempts,
            count(DISTINCT title) AS distinct_tests,
            count(DISTINCT attempt_id) FILTER(WHERE correct=false AND NOT unanswered)
            AS incorrect_attempts,
            count(*) FILTER(WHERE correct IS NULL AND NOT unanswered) AS not_graded,
            count(*)
FILTER(WHERE correct IS NOT NULL AND NOT unanswered) AS answered,
            count(*)
FILTER(WHERE correct=false AND NOT unanswered) AS incorrect,
            count(*)
FILTER(WHERE unanswered) AS unanswered FROM answers
            WHERE category IS NOT
NULL AND (CAST(:start AS timestamptz) IS NULL OR completed_at>=:start)
            AND
completed_at<:end GROUP BY module,category
            HAVING count(*) FILTER(WHERE
correct=false AND NOT unanswered)>0
            ORDER BY count(*) FILTER(WHERE
correct=false AND NOT unanswered) DESC LIMIT 12"""
                    ),
                    args,
                )
                .mappings()
                .all()
            )
            writing = (
                s.execute(
                    text("""
SELECT q->>'name' AS criterion,avg((q->>'band')::numeric) AS band,count(*) AS
assessments
            FROM writing_attempts
a,jsonb_array_elements(coalesce(a.assessment->'criteria','[]'::jsonb)) q
WHERE a.owner=:uid AND a.status='submitted' AND (CAST(:start AS timestamptz) IS NULL
OR a.completed_at>=:start)
            AND (a.completed_at<:end OR a.completed_at IS
NULL) AND q->>'band' IS NOT NULL
            GROUP BY q->>'name' ORDER BY band"""),
                    args,
                )
                .mappings()
                .all()
            )
            charts = {}
            for module, sql in {
                "listening": """
SELECT id,exam_id AS test_key,exam_id AS title,submitted_at AS date,
row_number() OVER(PARTITION BY exam_id ORDER BY submitted_at,id) AS attempt_number,
count(*) OVER(PARTITION BY exam_id) AS attempt_count,
(result->>'correct_count')::numeric AS value FROM
listening_attempts WHERE learner_id=:uid AND status='submitted' AND
(result->>'graded_count')::integer=40 AND (result->>'total_questions')::integer=40""",
                "reading": """
SELECT id,exam_id AS test_key,exam_id AS title,submitted_at AS date,
row_number() OVER(PARTITION BY exam_id ORDER BY submitted_at,id) AS attempt_number,
count(*) OVER(PARTITION BY exam_id) AS attempt_count,
(result->>'raw_score')::numeric AS value FROM
reading_attempts WHERE learner_id=:uid AND status IN ('submitted','expired') AND
(result->>'total_questions')::integer=40""",
                "writing": """
SELECT id,task_id AS test_key,coalesce(task_snapshot->>'title',task_id) AS title,
completed_at AS date,
row_number() OVER(PARTITION BY task_id ORDER BY completed_at,id) AS attempt_number,
count(*) OVER(PARTITION BY task_id) AS attempt_count,
(assessment->>'estimated_band')::numeric AS value FROM
writing_attempts WHERE owner=:uid AND status='submitted' AND
assessment->>'estimated_band' IS NOT NULL""",
            }.items():
                points = (
                    s.execute(
                        text(
                            "SELECT * FROM ("
                            + sql
                            + """
) p WHERE date IS NOT NULL AND value IS NOT NULL AND (CAST(:start AS timestamptz) IS
NULL OR date>=:start) AND date<:end ORDER BY date DESC,id DESC LIMIT 201"""
                        ),
                        args,
                    )
                    .mappings()
                    .all()
                )
                charts[module] = dict(
                    points=[
                        {**dict(p), "title": title(p["title"])} for p in reversed(points[:200])
                    ],
                    truncated=len(points) > 200,
                    scale=9 if module == "writing" else 40,
                )
        return dict(
            period=period,
            counts={m: counts.get(m, 0) for m in ["listening", "reading", "writing", "speaking"]},
            mistakes=dict(summary),
            charts=charts,
            weak_areas=[dict(r) for r in weak],
            writing_criteria=[dict(r) for r in writing],
            speaking_assessment_available=False,
        )
