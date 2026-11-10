"""On-demand, read-only Reading tutor over the exact frozen attempt. No grading writes."""

import hashlib
import json
import os
import re
import tempfile
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings
from app.core.exceptions import AluaError, ConflictError, ExternalServiceError, NotFoundError
from app.modules.reading.catalog import CRITICAL_ISSUES, questions

VERSION = "reading-review-v1.1"
FIELDS = {
    "why_user_answer_wrong",
    "why_correct_answer_works",
    "ielts_tip",
    "evidence",
    "evidence_status",
}
_guard = threading.Lock()
_usage = {}
_context_usage = {}
_flights = {}


def digest(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()


def unavailable(reason):
    return {
        "why_user_answer_wrong": (
            "Не удалось надёжно подтвердить фрагмент текста для этого вопроса."
        ),
        "why_correct_answer_works": (
            "Сравните сохранённый ответ с ключом. "
            "Подтверждённого объяснения по доступному тексту сейчас нет."
        ),
        "ielts_tip": "Сопоставьте условие задания с полным контекстом соответствующего абзаца.",
        "evidence_status": "unavailable",
        "evidence": [],
        "reason": reason,
    }


def words(text):
    return set(re.findall(r"[a-z]{3,}", text.lower())) - {
        "the",
        "and",
        "that",
        "this",
        "with",
        "from",
        "which",
        "for",
        "are",
        "was",
        "were",
        "has",
        "have",
        "not",
        "given",
        "paragraph",
    }


def focus_terms(group, question):
    lists = []
    for block in group["content_blocks"]:
        if block["type"] == "rich_text":
            lists.append(block["segments"])
        elif block["type"] == "table":
            lists.extend(cell["segments"] for row in block["rows"] for cell in row)
        elif block["type"] == "list":
            lists.extend(block["items"])
    focus = question["prompt"]
    for segments in lists:
        for i, segment in enumerate(segments):
            if segment["type"] == "blank" and segment["number"] == question["number"]:
                before = segments[i - 1].get("text", "") if i else ""
                after = segments[i + 1].get("text", "") if i + 1 < len(segments) else ""
                focus = (
                    re.split(r"[.!?]\s*", before)[-1][-250:]
                    + " "
                    + re.split(r"[.!?]\s*", after)[0][:250]
                )
    generic = {
        "ability",
        "actually",
        "comes",
        "through",
        "which",
        "means",
        "they",
        "their",
        "them",
        "there",
        "these",
        "those",
        "this",
        "that",
        "what",
        "how",
        "why",
        "only",
        "one",
        "word",
        "words",
        "answer",
        "answers",
        "question",
        "questions",
        "choose",
        "write",
        "each",
        "below",
        "following",
        "been",
        "might",
        "would",
        "could",
        "should",
        "than",
        "such",
        "some",
        "more",
        "also",
    }
    return sorted(words(focus) - generic)


def validate(context, raw):
    """Exact anchors first; conservative key linkage second. Return UTF-16 offsets."""
    if not isinstance(raw, dict) or set(raw) != FIELDS:
        raise ValueError("schema")
    for field in FIELDS - {"evidence", "evidence_status"}:
        text = raw[field]
        if (
            not isinstance(text, str)
            or not 1 <= len(text) <= 900
            or not re.search("[А-Яа-яЁё]", text)
            or re.search(r"[<>\x00-\x08]|https?://", text)
        ):
            raise ValueError("prose")
        if re.search(
            r"(?:ты|вы|ученик)\b[^.!?]{0,70}"
            r"(?:невнимател|не замет|подум|перепут|не уч[её]л|не понял)",
            text,
            re.I,
        ):
            raise ValueError("mind_reading")
    evidence = raw["evidence"]
    if not isinstance(evidence, list) or len(evidence) > 3:
        raise ValueError("evidence")
    if raw["evidence_status"] == "unavailable" and not evidence:
        return unavailable("evidence_not_found")
    if raw["evidence_status"] != "found" or not evidence or context["unavailable_reason"]:
        raise ValueError("status")
    anchors = []
    for item in evidence:
        if not isinstance(item, dict) or set(item) != {"block_index", "quote", "kind"}:
            raise ValueError("anchor_schema")
        index, quote, kind = item["block_index"], item["quote"], item["kind"]
        if type(index) is not int or not 0 <= index < len(context["blocks"]):
            raise ValueError("block")
        block = context["blocks"][index]
        if (
            block["type"] != "paragraph"
            or not isinstance(quote, str)
            or not 8 <= len(quote) <= 1200
            or kind not in {"support", "contradiction", "relevant_context"}
        ):
            raise ValueError("quote")
        text = block["text"]
        at = text.find(quote)
        if (
            at < 0
            or text.find(quote, at + 1) >= 0
            or any(quote in b["text"] for n, b in enumerate(context["blocks"]) if n != index)
        ):
            raise ValueError("ambiguous_or_missing_quote")
        if context["not_given"] and kind != "relevant_context":
            raise ValueError("not_given_is_not_proof")
        if (
            not context["not_given"]
            and context["correct_answer"] in {"FALSE", "NO"}
            and kind == "support"
        ):
            raise ValueError("contradiction_required")
        if anchors and (
            index < anchors[-1]["block_index"]
            or index == anchors[-1]["block_index"]
            and at < anchors[-1]["end_codepoint"]
        ):
            raise ValueError("overlapping_or_unordered")
        anchors.append(
            {
                "passage_id": context["passage_id"],
                "block_index": index,
                "quote": quote,
                "kind": kind,
                "start": len(text[:at].encode("utf-16-le")) // 2,
                "end": len(text[: at + len(quote)].encode("utf-16-le")) // 2,
                "end_codepoint": at + len(quote),
            }
        )
    labels = {str(context["blocks"][a["block_index"]].get("label", "")).upper() for a in anchors}
    prose = " ".join(
        raw[k] for k in ("why_user_answer_wrong", "why_correct_answer_works", "ielts_tip")
    )
    references = re.findall(r"(?:paragraph|абзац(?:е|а)?)\s+([A-Z])\b", prose, re.I)
    if any(label.upper() not in labels for label in references):
        raise ValueError("unsupported_paragraph_reference")
    combined = " ".join(a["quote"] for a in anchors)
    grounding = context["grounding"]
    if grounding["mode"] == "text":
        if not any(
            re.search(r"(?<!\w)" + re.escape(t) + r"(?!\w)", combined, re.I)
            for t in grounding["targets"]
        ):
            raise ValueError("key_not_grounded")
        focus = grounding.get("focus")
        if focus is not None and not (words(combined) & set(focus)):
            raise ValueError("blank_context_not_grounded")
    elif grounding["mode"] == "paragraph":
        if not any(
            context["blocks"][a["block_index"]].get("label") in grounding["targets"]
            for a in anchors
        ):
            raise ValueError("wrong_paragraph")
    elif grounding["mode"] == "heading":
        if grounding["targets"] and any(
            context["blocks"][a["block_index"]].get("label") not in grounding["targets"]
            for a in anchors
        ):
            raise ValueError("wrong_heading_paragraph")
        if not all(
            len(a["quote"]) >= 0.6 * len(context["blocks"][a["block_index"]]["text"])
            for a in anchors
        ):
            raise ValueError("heading_needs_main_idea")
    else:
        # A literal answer/option occurrence or shared source concepts is a necessary
        # check, not a claim that lexical overlap proves semantic entailment.
        targets = " ".join(grounding["targets"])
        if len(words(combined) & words(targets)) < min(2, len(words(targets))) or not words(
            targets
        ):
            raise ValueError("key_context_not_grounded")
    for a in anchors:
        a.pop("end_codepoint")
    result = dict(raw, evidence=anchors, reason=None)
    if context["not_given"]:
        result["why_correct_answer_works"] = (
            "Ключ: NOT GIVEN. Цитата показывает только релевантный контекст; "
            "одна цитата не доказывает отсутствие информации во всём passage. "
        ) + raw["why_correct_answer_works"][:600]
    if context["is_correct"]:
        result["why_user_answer_wrong"] = (
            "Сохранённый ответ засчитан верным. Ниже — контекст для сравнения с ключом."
        )
    elif not context["user_answer"].strip():
        result["why_user_answer_wrong"] = (
            "Ответ не был указан. Ниже показан контекст, который нужно сопоставить с заданием."
        )
    return result


@contextmanager
def flight(key):
    # Never occupy the threadpool waiting for an identical in-flight request:
    # the Worker callback also needs an origin thread to re-authorize context.
    with _guard:
        if key in _flights or len(_flights) >= 100:
            raise AluaError(
                "Review is already running. Retry shortly.", "reading_ai_rate_limited", 429
            )
        _flights[key] = True
    try:
        yield
    finally:
        with _guard:
            _flights.pop(key, None)


@contextmanager
def allowance(uid):
    now = time.monotonic()
    with _guard:
        for key in list(_usage):
            if _usage[key]["until"] < now and not _usage[key]["busy"]:
                del _usage[key]
        if uid not in _usage and len(_usage) >= 1000:
            raise AluaError("Please retry shortly.", "reading_ai_rate_limited", 429)
        entry = _usage.setdefault(uid, {"until": now + 60, "count": 0, "busy": False})
        if entry["busy"] or entry["count"] >= 6:
            raise AluaError("Please retry shortly.", "reading_ai_rate_limited", 429)
        entry["busy"] = True
        entry["count"] += 1
    try:
        yield
    finally:
        with _guard:
            entry["busy"] = False


def context_quota(uid):
    """Also limit direct Worker explain requests: they must reauthorize at this API."""
    now = time.monotonic()
    with _guard:
        for key in list(_context_usage):
            if _context_usage[key]["until"] <= now:
                del _context_usage[key]
        if uid not in _context_usage and len(_context_usage) >= 1000:
            raise AluaError("Please retry shortly.", "reading_ai_rate_limited", 429)
        entry = _context_usage.setdefault(uid, {"until": now + 60, "count": 0})
        if entry["count"] >= 6:
            raise AluaError("Please retry shortly.", "reading_ai_rate_limited", 429)
        entry["count"] += 1


class ReadingAIReview:
    def __init__(self, service):
        self.service = service

    def context(self, uid, aid, qid):
        try:
            return self._context(uid, aid, qid)
        except (KeyError, TypeError, ValueError, IndexError):
            raise ExternalServiceError(
                "Saved source is unavailable.", "reading_ai_source_unavailable"
            ) from None

    def _context(self, uid, aid, qid):
        if not get_settings().reading_ai_enabled:
            raise ExternalServiceError("Reading AI is unavailable.", "reading_ai_unavailable")
        with self.service.repo.transaction(uid) as session:
            row = self.service.repo.attempt(session, uid, aid)
            if row.status not in {"submitted", "expired"} or row.result is None:
                raise ConflictError("Finish the attempt first.", "reading_ai_not_completed")
            triple = questions(row.snapshot["exam"]).get(qid)
            saved = next((r for r in row.result["positions"] if r["question_id"] == qid), None)
            if not triple or not saved:
                raise NotFoundError("Question not found.", "reading_ai_question_not_found")
            passage, group, question = triple
            key = next((k for k in row.snapshot["key"]["answers"] if k["question_id"] == qid), None)
            reason = None
            if not key or key["canonical_answer"] != saved["correct_answer"]:
                raise ExternalServiceError(
                    "Saved key is unavailable.", "reading_ai_source_unavailable"
                )
            metadata = row.snapshot["metadata"]
            fingerprint = digest([VERSION, uid, aid, row.snapshot, row.result, row.answers, qid])
            members = [
                r
                for r in row.result["positions"]
                if r.get("grading_group") and r["grading_group"] == saved.get("grading_group")
            ]
            targets = list(key["accepted_answers"])
            mode = "text" if question["answer_input_type"] == "text" else "concepts"
            if question["type"] == "matching_information":
                mode = "paragraph"
            if question["type"] == "matching_headings":
                mode = "heading"
                target = re.search(r"\bparagraph\s+([A-Z])\b", question["prompt"], re.I)
                targets = [target[1].upper()] if target else []
                if not targets:
                    reason = "heading_context_unavailable"
            options = question["options"] or group["options"]
            if options and mode == "concepts":
                expected = set(targets)
                if members:
                    expected = {a for r in members for a in r["accepted_answers"]}
                targets = [o["text"] for o in options if o["label"] in expected]
            elif mode == "concepts":
                targets = [question["prompt"]]
            labels = [o["label"] for o in options]
            if options and (
                len(set(labels)) != len(labels)
                or any(o["text"].strip() == o["label"] for o in options)
                or not all(a in labels for a in key["accepted_answers"])
            ):
                reason = "incomplete_options"
            if (
                not question["prompt"].strip()
                or not group["instructions"].strip()
                or not passage["content"]
                or any("\ufffd" in b["text"] or "\x00" in b["text"] for b in passage["content"])
            ):
                reason = "source_integrity"
            if (
                group["representation"] == "source_image_with_inputs"
                and (
                    re.fullmatch(r"(?:Answer|Question)\s*\d+", question["prompt"], re.I)
                    or question["answer_input_type"] in {"single_select", "multi_select"}
                    and not options
                )
                or question["type"] == "diagram_labelling"
                or question["type"] == "flow_chart_completion"
                and (group["assets"] or group["representation"] == "source_image_with_inputs")
            ):
                reason = "visual_context_unavailable"
            for warning in metadata.get("warnings", []):
                if (
                    warning.get("code") in CRITICAL_ISSUES
                    and warning.get("question_id", qid) == qid
                    and warning.get("group_id", group["id"]) == group["id"]
                ):
                    reason = "source_integrity"
            context = {
                "learner_id": uid,
                "attempt_id": aid,
                "question_id": qid,
                "question_number": question["number"],
                "fingerprint": fingerprint,
                "version": VERSION,
                "passage_id": passage["id"],
                "passage_title": passage["title"],
                "blocks": passage["content"],
                "question_type": question["type"],
                "question": question["prompt"],
                "instructions": group["instructions"],
                "group_content": group["content_blocks"],
                "options": options,
                "constraints": question["constraints"],
                "user_answer": saved["user_answer"],
                "correct_answer": saved["correct_answer"],
                "accepted_answers": key["accepted_answers"],
                "is_correct": saved["is_correct"],
                "group_answers": [
                    {
                        k: r[k]
                        for k in ("question_id", "user_answer", "correct_answer", "is_correct")
                    }
                    for r in members
                ],
                "not_given": saved["correct_answer"].upper() == "NOT GIVEN",
                "grounding": {
                    "mode": mode,
                    "targets": targets,
                    "focus": focus_terms(group, question) if mode == "text" else None,
                },
                "source_status": metadata["content_status"],
                "unavailable_reason": reason,
            }
            if len(json.dumps(context).encode()) > 80_000:
                context["unavailable_reason"] = "context_budget_exceeded"
                context["blocks"] = []
            return context

    def explain(self, uid, aid, qid, authorization):
        context = self.context(uid, aid, qid)
        root = Path(get_settings().reading_ai_cache_root)
        path = root / (digest([uid, aid, qid, context["fingerprint"]]) + ".json")

        def cached():
            try:
                if path.stat().st_size > 20_000 or path.stat().st_mtime < time.time() - 30 * 86400:
                    return None
                data = json.loads(path.read_text())
                if data["fingerprint"] == context["fingerprint"]:
                    return validate(context, data["raw"])
            except (OSError, ValueError, KeyError, TypeError):
                pass
            return None

        with flight(str(path)):
            result = cached()
            if result is not None:
                return {
                    "question_id": qid,
                    "fingerprint": context["fingerprint"],
                    "review": result,
                    "cached": True,
                    "source_status": context["source_status"],
                }
            with allowance(uid):
                if context["unavailable_reason"]:
                    return {
                        "question_id": qid,
                        "fingerprint": context["fingerprint"],
                        "review": unavailable(context["unavailable_reason"]),
                        "cached": False,
                        "source_status": context["source_status"],
                    }
                url = get_settings().reading_ai_worker_url
                parsed = urlparse(url)
                local = (
                    get_settings().environment in {"local", "development"}
                    and parsed.scheme == "http"
                    and parsed.hostname in {"localhost", "127.0.0.1"}
                )
                if (
                    parsed.username
                    or parsed.password
                    or parsed.query
                    or parsed.fragment
                    or parsed.path != "/api/reading/explain"
                    or not (local or parsed.scheme == "https" and parsed.netloc == "alua.study")
                ):
                    raise ExternalServiceError(
                        "Reading AI is unavailable.", "reading_ai_unavailable"
                    )
                try:
                    # Streaming bounds the response; timeout covers body reads as well.
                    with httpx.stream(
                        "POST",
                        url,
                        headers={"Authorization": authorization},
                        json={"attempt_id": aid, "question_id": qid},
                        timeout=50,
                        follow_redirects=False,
                    ) as response:
                        if response.status_code != 200:
                            raise ValueError("provider")
                        body = bytearray()
                        for chunk in response.iter_bytes():
                            body.extend(chunk)
                            if len(body) > 20_000:
                                raise ValueError("payload")
                        data = json.loads(body)
                    if data["fingerprint"] != context["fingerprint"]:
                        raise ValueError("snapshot_changed")
                    raw = data["review"]
                    result = validate(context, raw)
                except (httpx.HTTPError, ValueError, KeyError, TypeError):
                    raise ExternalServiceError(
                        "Reading AI is temporarily unavailable.", "reading_ai_unavailable"
                    ) from None
                try:
                    root.mkdir(parents=True, exist_ok=True, mode=0o700)
                    files = sorted(
                        root.glob("[0-9a-f]" * 64 + ".json"), key=lambda p: p.stat().st_mtime
                    )
                    for old in files[: max(0, len(files) - 999)]:
                        old.unlink(missing_ok=True)
                    fd, temporary = tempfile.mkstemp(dir=root, suffix=".tmp")
                    try:
                        with os.fdopen(fd, "w") as file:
                            json.dump(
                                {"fingerprint": context["fingerprint"], "raw": raw},
                                file,
                                ensure_ascii=False,
                            )
                        os.replace(temporary, path)
                    finally:
                        Path(temporary).unlink(missing_ok=True)
                except OSError:
                    raise ExternalServiceError(
                        "Reading AI cache is unavailable.", "reading_ai_unavailable"
                    ) from None
                return {
                    "question_id": qid,
                    "fingerprint": context["fingerprint"],
                    "review": result,
                    "cached": False,
                    "source_status": context["source_status"],
                }
