"""Canonical final-answer integrity, independent of grading/normalization."""

import hashlib
import json

from app.core.exceptions import ValidationError


def canonical_answers(answers, ids):
    return {qid: answers.get(qid, "") for qid in sorted(ids)}


def answers_checksum(answers, ids):
    pairs = sorted(canonical_answers(answers, ids).items())
    encoded = json.dumps(pairs, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def validate_final(request, ids):
    if set(request.answers) != set(ids):
        raise ValidationError("Final snapshot must contain exactly this attempt's questions.")
    if answers_checksum(request.answers, ids) != request.answers_checksum:
        raise ValidationError("Final answer checksum mismatch.")
    return canonical_answers(request.answers, ids)
