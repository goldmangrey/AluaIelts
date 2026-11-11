"""On-demand completed-attempt review. Provider output never supplies trusted timestamps."""

import hashlib
import json
import math
import re
import threading
import time
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

import httpx
from mutagen import File as AudioFile
from mutagen import MutagenError
from pydantic import BaseModel, ConfigDict, Field
from pydantic import ValidationError as ModelError

from app.core.config import get_settings
from app.core.exceptions import AluaError, ConflictError, ExternalServiceError, ValidationError
from app.modules import private_ai_cache as cache
from app.modules.listening.catalog import CONTENT, digest, questions

VERSION = "listening-ai-v1"
TRANSCRIPTS = CONTENT / "listening_transcripts_v1"


class ModelReview(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    what_happened: str = Field(min_length=1, max_length=1800)
    why: str = Field(min_length=1, max_length=1800)
    next_time: str = Field(min_length=1, max_length=1000)
    segment_ids: list[str] = Field(max_length=5)
    quote: str = Field(max_length=1800)


@lru_cache(maxsize=288)
def transcript(book, test, part):
    path = TRANSCRIPTS / f"cambridge-{book:02}-test-{test:02}-part-{part:02}.json"
    try:
        doc = json.loads(path.read_text())
        manifest = json.loads((TRANSCRIPTS / "manifest.json").read_text())
        expected = next(r["sha256"] for r in manifest["items"] if r["file"] == path.name)
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected or (
            doc["book"],
            doc["test"],
            doc["section"],
        ) != (book, test, part):
            return None
        previous = -1
        for s in doc["segments"]:
            if (
                not all(
                    isinstance(s[k], (int, float)) and math.isfinite(s[k]) for k in ("start", "end")
                )
                or not 0 <= s["start"] < s["end"]
                or s["start"] < previous
                or not s["text"].strip()
            ):
                return None
            previous = s["start"]
        if len({s["id"] for s in doc["segments"]}) != len(doc["segments"]):
            return None
        return doc
    except (OSError, ValueError, KeyError, StopIteration, TypeError):
        return None


@lru_cache(maxsize=288)
def probe_duration(path, size, mtime):
    # Read only container metadata (including MP3 Xing/VBR and M4A duration).
    # Pure Python: the Oracle host need not install ffprobe/ffmpeg or decode audio.
    try:
        media = AudioFile(path)
        duration = float(media.info.length) if media is not None else 0
        return duration if math.isfinite(duration) and 0 < duration <= 86400 else None
    except (OSError, ValueError, AttributeError, MutagenError):
        return None


def unavailable(part, reason):
    return {
        "what_happened": "Точный фрагмент аудио для этого вопроса сейчас подтвердить нельзя.",
        "why": (
            "Сравните сохранённый ответ с ключом выше. "
            "Без надёжного фрагмента нельзя утверждать, что именно привело к ошибке."
        ),
        "next_time": "Прослушайте эту часть целиком, ориентируясь на вопрос и варианты ответа.",
        "evidence": {
            "available": False,
            "reason": reason,
            "part": part,
            "quote": None,
            "segment_ids": [],
            "clip_start": None,
            "clip_end": None,
        },
    }


_guard = threading.Lock()
_usage = {}


@contextmanager
def allowance(uid):
    now = time.monotonic()
    with _guard:
        for k in list(_usage):
            if _usage[k]["until"] < now and not _usage[k]["busy"]:
                _usage.pop(k)
        e = _usage.setdefault(uid, {"until": now + 60, "count": 0, "busy": False})
        if e["busy"] or e["count"] >= 6:
            raise AluaError("Please try again shortly.", "ai_review_rate_limited", 429)
        e["count"] += 1
        e["busy"] = True
    try:
        yield
    finally:
        with _guard:
            e["busy"] = False


class AIReview:
    def __init__(self, service):
        self.service = service

    def context(self, uid, aid, number):
        with self.service.transaction(uid) as session:
            row = self.service.owned(session, uid, aid)
            if row.status != "submitted":
                raise ConflictError(
                    "Finish the attempt before AI review.", "listening_not_submitted"
                )
            saved = next(
                (q for q in row.result["questions"] if q["question_number"] == number), None
            )
            if (
                not saved
                or saved["correct"] is not False
                or not saved["user_answer"].strip()
                or saved.get("grading_issue")
            ):
                raise ValidationError("AI review is available for scored incorrect answers only.")
            snap = row.snapshot
            part, group, q = questions(snap["exam"])[saved["question_id"]]
            part_number = part["part_number"]
            audio = snap["audio"].get(str(part_number), snap["audio"].get(part_number))
            book, test = snap["exam"]["book"], snap["exam"]["printed_test_number"]
            fingerprint = digest(
                {
                    "version": VERSION,
                    "snapshot": snap["content_hash"],
                    "key": snap["key_hash"],
                    "answer": saved,
                }
            )
        doc = transcript(book, test, part_number)
        reason = None
        duration = None
        if not doc:
            reason = "transcript_unavailable"
        elif not doc["complete"]:
            reason = "transcript_incomplete"
        elif not audio or Path(audio["relative_path"]).stem != Path(doc["source_audio"]).stem:
            reason = "audio_identity_mismatch"
        else:
            try:
                path = self.service.catalog.audio_path(audio)
                stat = path.stat()
                duration = probe_duration(str(path), stat.st_size, stat.st_mtime_ns)
            except AluaError:
                duration = None
            if not duration:
                reason = "audio_duration_unavailable"
            elif doc["segments"][-1]["end"] > duration + 1:
                reason = "transcript_outside_audio"
        data = {
            "learner_id": uid,
            "attempt_id": aid,
            "question_number": number,
            "book": book,
            "test": test,
            "part": part_number,
            "question": q["prompt"],
            "group_context": [
                b["text"] for b in group["content_blocks"] if b["kind"] == "source_line"
            ],
            "constraints": q["constraints"],
            "question_type": group["question_type"],
            "instructions": group["instructions"],
            "options": q["options"] or (group.get("answer_bank") or {}).get("options", []),
            "user_answer": saved["user_answer"],
            "correct_answer": saved["correct_answer"],
            "unavailable_reason": reason,
            "duration": duration,
            "segments": doc["segments"] if doc and not reason else [],
        }
        data["fingerprint"] = digest(
            {"attempt": fingerprint, "transcript": doc, "audio": audio, "duration": duration}
        )
        return data

    @staticmethod
    def validate(context, raw):
        try:
            model = ModelReview.model_validate(raw)
        except ModelError:
            raise ExternalServiceError(
                "AI returned an invalid explanation.", "ai_review_invalid"
            ) from None
        texts = [model.what_happened, model.why, model.next_time]
        if any(not re.search("[А-Яа-яЁё]", t) or re.search(r"[<>\x00-\x08]", t) for t in texts):
            raise ExternalServiceError("AI returned an invalid explanation.", "ai_review_invalid")
        if not model.segment_ids:
            return unavailable(context["part"], "evidence_not_found")
        segments = context["segments"]
        by_id = {s["id"]: s for s in segments}
        ids = model.segment_ids
        if len(set(ids)) != len(ids) or any(i not in by_id for i in ids):
            return unavailable(context["part"], "evidence_not_found")
        chosen = [by_id[i] for i in ids]
        indexes = [segments.index(s) for s in chosen]
        exact = " ".join(s["text"].strip() for s in chosen)
        if (
            indexes != list(range(indexes[0], indexes[0] + len(indexes)))
            or not model.quote.strip()
            or model.quote not in exact
            or chosen[-1]["end"] - chosen[0]["start"] > 60
            or chosen[-1]["end"] > context["duration"]
        ):
            return unavailable(context["part"], "evidence_not_found")
        start = max(0, chosen[0]["start"] - 2.5)
        end = min(context["duration"], segments[-1]["end"], chosen[-1]["end"] + 3)
        if not 0 <= start < end <= context["duration"]:
            return unavailable(context["part"], "evidence_not_found")
        # Do not present guessed attention/thoughts as observed facts. Keep the
        # independently validated clip, replacing that prose with factual comparison.
        prose = model.model_dump(exclude={"quote", "segment_ids"})
        mind = re.compile(
            r"\b(?:ученик|вы|ты)\b[^.!?]{0,65}(?:сфокусир|подум|решил|не\s+уч[её]л|услышал|не\s+понял|не\s+заметил|перепутал|не\s+обратил)",
            re.I,
        )
        safe = {
            "what_happened": "В этом фрагменте есть фраза для сравнения с ключом.",
            "why": "Ответ не совпадает с ключом. Сравните его с цитатой.",
            "next_time": "Прослушайте фрагмент ещё раз и сравните его с вопросом.",
        }
        for field, text in prose.items():
            if mind.search(text):
                prose[field] = safe[field]
        return {
            **prose,
            "evidence": {
                "available": True,
                "reason": None,
                "part": context["part"],
                "quote": model.quote,
                "segment_ids": ids,
                "clip_start": round(start, 3),
                "clip_end": round(end, 3),
            },
        }

    def explain(self, uid, aid, number, authorization):
        context = self.context(uid, aid, number)
        path = (
            Path(get_settings().listening_ai_cache_root)
            / f"{digest([uid, aid, number, context['fingerprint']])}.json"
        )
        try:
            cache.directory(path.parent)
        except OSError:
            raise ExternalServiceError(
                "AI cache is unavailable.", "ai_review_cache_unavailable"
            ) from None
        try:
            cached = cache.load(path)
            if cached and cached["fingerprint"] == context["fingerprint"]:
                if context["unavailable_reason"]:
                    return dict(
                        unavailable(context["part"], context["unavailable_reason"]), cached=True
                    )
                value = cached["review"]
                e = value["evidence"]
                raw = {k: value[k] for k in ("what_happened", "why", "next_time")}
                raw.update(segment_ids=e["segment_ids"], quote=e["quote"] or "")
                validated = self.validate(context, raw)
                return dict(validated, cached=True)
        except (OSError, ValueError, KeyError):
            pass
        with allowance(uid):
            if context["unavailable_reason"]:
                result = unavailable(context["part"], context["unavailable_reason"])
            else:
                url = get_settings().listening_ai_worker_url
                parsed = urlparse(url)
                if not (
                    parsed.scheme == "https"
                    and parsed.hostname == "alua.study"
                    or parsed.scheme == "http"
                    and parsed.hostname in ("localhost", "127.0.0.1")
                ):
                    raise ExternalServiceError(
                        "AI endpoint is not configured.", "ai_review_unavailable"
                    )
                try:
                    response = httpx.post(
                        url,
                        headers={"Authorization": authorization},
                        json={"attempt_id": aid, "question_number": number},
                        timeout=50,
                        follow_redirects=False,
                    )
                    if response.status_code != 200:
                        raise ValueError("Provider unavailable")
                    raw = response.json()
                    # The Worker re-reads context; reject a snapshot/QA change in flight.
                    if raw.get("fingerprint") != context["fingerprint"]:
                        raise ValueError("Context changed")
                    result = self.validate(context, raw["review"])
                except (httpx.HTTPError, ValueError, KeyError):
                    raise ExternalServiceError(
                        "AI review is temporarily unavailable. Please retry.",
                        "ai_review_unavailable",
                    ) from None
            try:
                cache.save(path, {"fingerprint": context["fingerprint"], "review": result})
            except OSError:
                raise ExternalServiceError(
                    "AI review cache is unavailable.", "ai_review_cache_unavailable"
                ) from None
            return dict(result, cached=False)
