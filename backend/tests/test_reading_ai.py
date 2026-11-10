"""Frozen-source tutor regression; ephemeral PostgreSQL, synthetic model responses."""

# ruff: noqa: F811
import copy
import json
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path

import pytest
from test_household_bootstrap import bootstrap, headers, postgres_url, system  # noqa: F401
from test_reading import event, start

from app.core.config import get_settings
from app.modules.exam_integrity import answers_checksum
from app.modules.reading import ai_review as ai
from app.modules.reading.ai_review import ReadingAIReview, validate
from app.modules.reading.catalog import get_catalog, questions
from app.modules.reading.router import get_reading_service

FIXTURE = json.loads(
    (Path(__file__).resolve().parents[2] / "web/tests/fixtures/reading-ai-cases.json").read_text()
)


def test_exact_anchors_are_utf16_not_python_codepoints():
    value = validate(FIXTURE["context"], FIXTURE["raw"])
    anchor = value["evidence"][0]
    assert anchor["start"] == 3  # emoji is two UTF-16 units, then a space
    assert anchor["end"] == 36
    assert anchor["passage_id"] == "p1"


@pytest.mark.parametrize(
    "patch",
    [
        {"evidence": [{"block_index": 99, "quote": "Bats use sounds", "kind": "support"}]},
        {"evidence": [{"block_index": 0, "quote": "Bats use vision", "kind": "support"}]},
        {"evidence": [{"block_index": 0, "quote": "Bats use sounds", "kind": "none"}]},
        {"evidence": [{"block_index": 0, "quote": "find obstacles", "kind": "support"}]},
        {
            "evidence": [
                {"block_index": 0, "quote": "Bats use sounds", "kind": "support", "start": 1}
            ]
        },
        {"why_user_answer_wrong": "Вы невнимательно читали текст."},
        {"why_correct_answer_works": "<script>Русский</script>"},
        {"extra": "fabricated"},
        {"why_correct_answer_works": "Это подтверждено в абзаце Z."},
    ],
)
def test_invalid_evidence_and_prose_rejected(patch):
    with pytest.raises(ValueError):
        validate(FIXTURE["context"], FIXTURE["raw"] | patch)


def test_duplicate_quote_order_heading_and_ng_rules():
    ctx, raw = copy.deepcopy(FIXTURE["context"]), copy.deepcopy(FIXTURE["raw"])
    ctx["blocks"][0]["text"] += " " + raw["evidence"][0]["quote"]
    with pytest.raises(ValueError):
        validate(ctx, raw)
    ctx = copy.deepcopy(FIXTURE["context"])
    raw["evidence"] *= 2
    with pytest.raises(ValueError):
        validate(ctx, raw)
    raw = copy.deepcopy(FIXTURE["raw"])
    ctx["not_given"] = True
    ctx["correct_answer"] = "NOT GIVEN"
    ctx["grounding"] = {"mode": "concepts", "targets": ["Bats use sounds"]}
    with pytest.raises(ValueError):
        validate(ctx, raw)
    raw["evidence"][0]["kind"] = "relevant_context"
    assert "одна цитата не доказывает" in validate(ctx, raw)["why_correct_answer_works"]
    ctx["grounding"] = {"mode": "heading", "targets": []}
    raw["evidence"][0]["quote"] = "Bats use sounds"
    with pytest.raises(ValueError):
        validate(ctx, raw)


def model_for(context):
    for i, block in enumerate(context["blocks"]):
        if block["type"] != "paragraph":
            continue
        for target in context["grounding"]["targets"]:
            at = block["text"].lower().find(target.lower())
            if at >= 0:
                left = block["text"].rfind(".", 0, max(0, at - 160)) + 1
                right = block["text"].find(".", at + len(target) + 80)
                quote = block["text"][
                    left : right + 1 if right >= 0 else len(block["text"])
                ].strip()
                if block["text"].count(quote) == 1:
                    raw = copy.deepcopy(FIXTURE["raw"])
                    raw["evidence"] = [{"block_index": i, "quote": quote, "kind": "support"}]
                    try:
                        validate(context, raw)
                    except ValueError:
                        continue
                    return raw
    raise AssertionError("Fixture needs a source answer")


@contextmanager
def fake_stream(context, raw, calls, *args, **kwargs):
    calls.append(kwargs)

    class Response:
        status_code = 200

        def iter_bytes(self):
            yield json.dumps({"fingerprint": context["fingerprint"], "review": raw}).encode()

    yield Response()


def submit_payload(attempt, answers):
    ids = questions(get_catalog().exams[attempt["exam_id"]])
    full = {qid: answers.get(qid, "") for qid in ids}
    return event(
        attempt["version"],
        answers=full,
        answers_checksum=answers_checksum(full, ids),
        local_revision=1,
    )


def test_completed_ownership_snapshot_cache_and_no_mutation(system, monkeypatch, tmp_path):
    db, client, _ = system
    owner, _ = bootstrap(client, "husband")
    other, _ = bootstrap(client, "wife")
    h = headers(owner)
    attempt, _ = start(client, h, eid="cambridge-07-test-01")
    aid = attempt["id"]
    qid = "cambridge-07-test-01-q-07"
    base = f"/api/v1/reading/attempts/{aid}"
    endpoint = base + f"/ai-review/{qid}"
    assert client.post(endpoint, headers=h).status_code == 409
    assert client.get(endpoint + "/context", headers=headers(other)).status_code == 404
    assert client.get(endpoint + "/context").status_code == 401
    submit = client.post(base + "/submit", headers=h, json=submit_payload(attempt, {qid: "touch"}))
    assert submit.status_code == 200, submit.text
    before = client.get(base, headers=h).json()
    before_result = client.get(base + "/result", headers=h).json()
    settings = get_settings()
    monkeypatch.setattr(settings, "reading_ai_cache_root", str(tmp_path))
    ctx = client.get(endpoint + "/context", headers=h).json()
    assert ctx["correct_answer"] == "echoes/obstacles" and ctx["user_answer"] == "touch"
    assert ctx["unavailable_reason"] is None
    raw, calls = model_for(ctx), []
    monkeypatch.setattr(ai.httpx, "stream", lambda *a, **kw: fake_stream(ctx, raw, calls, *a, **kw))
    response = client.post(endpoint, headers=h)
    assert response.status_code == 200, response.text
    assert response.json()["review"]["evidence_status"] == "found"
    assert client.post(endpoint, headers=h).json()["cached"] is True
    assert len(calls) == 1 and set(calls[0]["json"]) == {"attempt_id", "question_id"}
    assert client.post(base + "/ai-review/unknown", headers=h).status_code == 404
    after = client.get(base, headers=h).json()
    for field in ["answers", "version", "status", "exam", "content_hash"]:
        assert after[field] == before[field]
    assert client.get(base + "/result", headers=h).json() == before_result
    # Canonical edits do not replace the frozen passage.
    catalog = get_reading_service().catalog
    canonical = catalog.exams["cambridge-07-test-01"]["passages"][0]["content"][3]
    old = canonical["text"]
    canonical["text"] = "Changed canonical source"
    try:
        assert client.get(endpoint + "/context", headers=h).json() == ctx
    finally:
        canonical["text"] = old


def test_singleflight_same_key_and_rate_limit(monkeypatch, tmp_path):
    context = copy.deepcopy(FIXTURE["context"])
    context["source_status"] = "needs_review"
    service = ReadingAIReview(None)
    monkeypatch.setattr(service, "context", lambda *a: context)
    monkeypatch.setattr(get_settings(), "reading_ai_cache_root", str(tmp_path))
    calls = []

    @contextmanager
    def provider(*a, **kw):
        time.sleep(0.05)
        with fake_stream(context, FIXTURE["raw"], calls, *a, **kw) as response:
            yield response

    monkeypatch.setattr(ai.httpx, "stream", provider)

    def run(_):
        try:
            return service.explain("singleflight", "a", "q", "Bearer synthetic")
        except ai.AluaError as error:
            return error.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, range(2)))
    assert len(calls) == 1 and 429 in results
    assert service.explain("singleflight", "a", "q", "Bearer synthetic")["cached"] is True
    ai._usage["limited"] = {"until": time.monotonic() + 60, "count": 6, "busy": False}
    with pytest.raises(ai.AluaError) as error:
        service.explain("limited", "a", "q", "Bearer synthetic")
    assert error.value.status_code == 429


def test_reading_ai_browser_real_endpoints(system, monkeypatch, tmp_path):
    import os
    import subprocess
    import threading

    import uvicorn

    _, client, _ = system
    owner, _ = bootstrap(client, "husband")
    h = headers(owner)
    attempt, _ = start(client, h, eid="cambridge-07-test-01")
    aid = attempt["id"]
    answer = {"cambridge-07-test-01-q-07": "touch", "cambridge-07-test-01-q-08": "wrong"}
    response = client.post(
        f"/api/v1/reading/attempts/{aid}/submit", headers=h, json=submit_payload(attempt, answer)
    )
    assert response.status_code == 200, response.text
    attempt = client.get(f"/api/v1/reading/attempts/{aid}", headers=h).json()
    settings = get_settings()
    monkeypatch.setattr(
        settings, "reading_ai_worker_url", "http://127.0.0.1:3327/api/reading/explain"
    )
    monkeypatch.setattr(settings, "reading_ai_cache_root", str(tmp_path / "cache"))
    fixture = tmp_path / "browser.json"
    ctx = client.get(
        f"/api/v1/reading/attempts/{aid}/ai-review/cambridge-07-test-01-q-07/context", headers=h
    ).json()
    item = model_for(ctx)["evidence"][0]
    text = ctx["blocks"][item["block_index"]]["text"]
    at = text.index(item["quote"])
    highlight = {
        "id": "fixture-highlight",
        "passageId": ctx["passage_id"],
        "block": item["block_index"],
        "start": len(text[:at].encode("utf-16-le")) // 2,
        "end": len(text[: at + len(item["quote"])].encode("utf-16-le")) // 2,
        "quote": item["quote"],
    }
    fixture.write_text(
        json.dumps(
            {
                "token": owner["token"],
                "uid": owner["profile"]["uid"],
                "attempt": attempt,
                "highlight": highlight,
                "target": next(
                    t for t in ctx["grounding"]["targets"] if t.lower() in item["quote"].lower()
                ),
            }
        )
    )
    server = uvicorn.Server(
        uvicorn.Config(client.app, host="127.0.0.1", port=3427, log_level="warning", lifespan="off")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert server.started
        subprocess.run(
            ["node", "scripts/test-reading-ai.mjs"],
            cwd=Path(__file__).resolve().parents[2] / "web",
            env=dict(os.environ, ALUA_READING_AI_FIXTURE=str(fixture)),
            check=True,
            timeout=300,
        )
    finally:
        server.should_exit = True
        thread.join(timeout=10)


def context_service(eid, answers=None, status="submitted"):
    from types import SimpleNamespace

    from app.modules.reading.grading import result_for

    catalog = get_catalog()
    snapshot = copy.deepcopy(
        {"exam": catalog.exams[eid], "key": catalog.keys[eid], "metadata": catalog.entries[eid]}
    )
    result = result_for(snapshot, answers or {}, "full_exam", None, 100, {})
    row = SimpleNamespace(status=status, snapshot=snapshot, answers=answers or {}, result=result)

    class Repo:
        @contextmanager
        def transaction(self, _):
            yield None

        def attempt(self, *_):
            return row

    return ReadingAIReview(SimpleNamespace(repo=Repo())), row


@pytest.mark.parametrize(
    "eid,number",
    [("cambridge-07-test-01", n) for n in [6, 7, 8, 9, 16, 37, 38, 39, 40]]
    + [("cambridge-16-test-03", n) for n in [20, 21, 22]],
)
def test_restored_summary_heading_and_text_contexts(eid, number):
    service, row = context_service(eid)
    qid = f"{eid}-q-{number:02}"
    context = service.context("fixture-context", "a", qid)
    assert context["unavailable_reason"] is None
    assert context["question"] and context["group_content"] and context["blocks"]
    assert context["correct_answer"] == next(
        a["canonical_answer"] for a in row.snapshot["key"]["answers"] if a["question_id"] == qid
    )
    if number == 16:
        assert context["grounding"]["mode"] == "heading" and context["grounding"]["targets"] == [
            "D"
        ]
        assert len(context["options"]) >= 8
    if eid == "cambridge-16-test-03":
        assert context["question_type"] == "summary_completion"
        validate(context, model_for(context))


def test_expired_correct_blank_unordered_and_corrupt_source():
    from test_reading import perfect

    eid = "cambridge-07-test-01"
    answers = perfect(get_catalog().keys[eid])
    service, row = context_service(eid, answers, status="expired")
    qid = eid + "-q-07"
    context = service.context("fixture-context", "a", qid)
    assert (
        context["is_correct"]
        and "засчитан верным" in validate(context, model_for(context))["why_user_answer_wrong"]
    )
    row.snapshot["exam"]["passages"][0]["content"][3]["text"] += "\ufffd"
    assert service.context("fixture-context", "a", qid)["unavailable_reason"] == "source_integrity"
    row.snapshot["key"]["answers"] = []
    with pytest.raises(ai.ExternalServiceError):
        service.context("fixture-context", "a", qid)
    for exam, key in get_catalog().keys.items():
        group = next((k for k in key["answers"] if k.get("grading_group")), None)
        if group:
            answers = perfect(key)
            members = [
                k for k in key["answers"] if k.get("grading_group") == group["grading_group"]
            ]
            values = [answers[k["question_id"]] for k in members][::-1]
            for k, value in zip(members, values, strict=True):
                answers[k["question_id"]] = value
            service, _ = context_service(exam, answers)
            ctx = service.context("fixture-context", "a", group["question_id"])
            assert len(ctx["group_answers"]) == len(members)
            assert all(r["is_correct"] for r in ctx["group_answers"])
            break
    else:
        raise AssertionError("Unordered fixture required")


def test_unavailable_visual_does_not_invoke_provider(monkeypatch, tmp_path):
    context = copy.deepcopy(FIXTURE["context"])
    context.update(source_status="needs_review", unavailable_reason="visual_context_unavailable")
    service = ReadingAIReview(None)
    monkeypatch.setattr(service, "context", lambda *a: context)
    monkeypatch.setattr(get_settings(), "reading_ai_cache_root", str(tmp_path))
    monkeypatch.setattr(
        ai.httpx, "stream", lambda *a, **kw: pytest.fail("No model should be called")
    )
    assert (
        service.explain("visual", "a", "q", "Bearer fixture")["review"]["evidence_status"]
        == "unavailable"
    )


def test_context_endpoint_quota_closes_direct_worker_bypass():
    for _ in range(6):
        ai.context_quota("context-quota-fixture")
    with pytest.raises(ai.AluaError) as error:
        ai.context_quota("context-quota-fixture")
    assert error.value.status_code == 429
