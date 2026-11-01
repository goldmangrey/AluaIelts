"""Runtime adapter around the *single* Stage 1 deterministic scorer."""

import collections
import re

from app.modules.reading.catalog import questions
from scripts.reading_dataset.grading import grade_exam, normalize

GRADING_VERSION = "reading-private-v1"
BAND_TABLE_VERSION = "academic-indicative-2026-11-01-v1"
BAND_SOURCE = "https://eslbar.co.uk/wp-content/uploads/2019/10/Ielts-score-conversions-chart.pdf"
BAND_ANCHOR_SOURCE = "https://takeielts.britishcouncil.org/results/how-is-ielts-assessed"
# Published indicative ranges. Below the lowest published interval no band is invented.
BAND_RANGES = (
    (4, 5, 2.5),
    (6, 7, 3.0),
    (8, 9, 3.5),
    (10, 12, 4.0),
    (13, 14, 4.5),
    (15, 18, 5.0),
    (19, 22, 5.5),
    (23, 26, 6.0),
    (27, 29, 6.5),
    (30, 32, 7.0),
    (33, 34, 7.5),
    (35, 36, 8.0),
    (37, 38, 8.5),
    (39, 40, 9.0),
)


def estimated_band(score: int) -> float | None:
    if not 0 <= score <= 40:
        raise ValueError("Reading score must be between 0 and 40")
    return next((band for low, high, band in BAND_RANGES if low <= score <= high), None)


def constrained_answer(answer: str, question: dict) -> str:
    """Over-limit answers score zero; preserve the unmodified answer in persistence/results.

    Hyphenated words count as one. A numerical expression is counted separately when
    instructions explicitly allow a number in addition to the word limit.
    """
    constraints = question["constraints"]
    maximum = constraints["max_words"]
    if maximum is None or question["answer_input_type"] != "text":
        return answer
    tokens = answer.strip().split()
    words = [t for t in tokens if not re.fullmatch(r"[£$€]?\d[\d,.]*(?:%|[a-zA-Z]+)?", t)]
    numbers = len(tokens) - len(words)
    # When a number is allowed, at most one numerical token is additional to max_words.
    if len(words) > maximum or len(tokens) > maximum + int(constraints["allow_number"]):
        return ""
    if numbers and not constraints["allow_number"]:
        return ""
    return answer


def result_for(
    snapshot: dict,
    answers: dict,
    mode: str,
    selected_passage: int | None,
    elapsed_seconds: int,
    passage_seconds: dict,
    *,
    only: set[str] | None = None,
) -> dict:
    exam, key = snapshot["exam"], snapshot["key"]
    qs = questions(exam)
    keyed = {a["question_id"]: a for a in key["answers"]}
    cleaned = {}
    for qid, value in answers.items():
        k = keyed[qid]
        # Explicit official variants take precedence over an inconsistent printed limit
        # (e.g. Cambridge 14 T4 Q1: ONE WORD ONLY, key explicitly accepts four / 4).
        official = normalize(value, k["normalization_rules"]) in {
            normalize(v, k["normalization_rules"]) for v in k["accepted_answers"]
        }
        cleaned[qid] = value if official else constrained_answer(value, qs[qid][2])
    # The private-practice policy was checked by the server when the snapshot was created.
    # This flag is never accepted from an API client.
    scored = grade_exam(exam, key, cleaned, allow_unreleased=True)
    selected = {
        qid
        for qid, (p, _, _) in qs.items()
        if selected_passage is None or p["number"] == selected_passage
    }
    if only is not None:
        selected &= only
    keys = {a["question_id"]: a for a in key["answers"]}
    positions, by_passage, by_type = [], {}, {}
    for qid, (p, _, q) in qs.items():
        if qid not in selected:
            continue
        answer = answers.get(qid, "")
        correct = bool(scored["positions"][qid])
        k = keys[qid]
        positions.append(
            {
                "question_id": qid,
                "number": q["number"],
                "question_type": q["type"],
                "passage_number": p["number"],
                "user_answer": answer,
                "correct_answer": k["canonical_answer"],
                "accepted_answers": k["accepted_answers"],
                "grading_group": k["grading_group"],
                "is_correct": correct,
                "unanswered": not answer.strip(),
                "evidence": k.get("evidence"),
            }
        )
        for mapping, identifier in ((by_passage, str(p["number"])), (by_type, q["type"])):
            row = mapping.setdefault(
                identifier, {"correct": 0, "incorrect": 0, "unanswered": 0, "total": 0}
            )
            row["correct"] += int(correct)
            row["unanswered"] += int(not answer.strip())
            row["incorrect"] += int(bool(answer.strip()) and not correct)
            row["total"] += 1
    for mapping in (by_passage, by_type):
        for row in mapping.values():
            row["accuracy"] = row["correct"] / row["total"]
    for num, row in by_passage.items():
        row["reported_active_seconds"] = passage_seconds.get(num, 0)
        row["time_is_verified"] = False
    counts = collections.Counter(
        "correct" if x["is_correct"] else "unanswered" if x["unanswered"] else "incorrect"
        for x in positions
    )
    score = counts["correct"]
    is_full = mode == "full_exam" and only is None
    band = estimated_band(score) if is_full else None
    return {
        "exam_id": exam["id"],
        "dataset_version": exam["dataset_version"],
        "content_hash": snapshot["metadata"]["content_hash"],
        "content_revision": snapshot["metadata"]["content_revision"],
        "mode": mode,
        "selected_passage": selected_passage,
        "grading_version": GRADING_VERSION,
        "raw_score": score,
        "total_questions": len(positions),
        "accuracy": score / len(positions) if positions else 0,
        "estimated_band": band,
        "band_is_estimate": True,
        "band_label": "Estimated IELTS Academic Reading Band" if is_full else None,
        "band_table_version": BAND_TABLE_VERSION if is_full else None,
        "band_unavailable_reason": "below_published_range" if is_full and band is None else None,
        "elapsed_seconds": elapsed_seconds,
        "timing_status": "server_deadline_enforced" if is_full else "untimed_practice",
        "correct_count": counts["correct"],
        "incorrect_count": counts["incorrect"],
        "unanswered_count": counts["unanswered"],
        "positions": positions,
        "per_passage": by_passage,
        "per_question_type": by_type,
        "weakest_question_types": sorted(by_type, key=lambda t: (by_type[t]["accuracy"], t)),
    }
