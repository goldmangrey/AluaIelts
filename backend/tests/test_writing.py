"""Writing contracts and real PostgreSQL; never the persistent learner database."""

# ruff: noqa: F811
import hashlib
import hmac
import json
import os
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import pytest
from test_household_bootstrap import bootstrap, headers, postgres_url, system  # noqa: F401

from app.modules.writing.catalog import import_tasks, validate_dataset
from app.modules.writing.contract import CRITERIA, validate_assessment, words

BASE = "/api/v1/writing"
ESSAY = (
    "Adults without literacy skills face serious barriers at work. " * 28
    + "\n\n"
    + "Governments should fund evening classes with childcare and trained teachers. " * 8
)


def assessment(essay=ESSAY):
    quote = essay.split(". ")[0] + "."
    start = len(essay[: essay.index(quote)].encode("utf-16-le")) // 2
    anchor = dict(quote=quote, start=start, end=start + len(quote.encode("utf-16-le")) // 2)
    return dict(
        criteria=[
            dict(
                name=name,
                band=6.0,
                rationale_en="Development is relevant but repetitive.",
                explanation_ru="Аргументы повторяются, развейте примеры.",
                evidence=[anchor],
                improvement="Explain how evening classes remove a specific employment barrier.",
            )
            for name in CRITERIA
        ],
        top_improvements=[
            dict(action=action, quote=quote)
            for action in [
                "Develop one workplace example.",
                "Explain the effect on families.",
                "Connect the proposed support to the barrier.",
            ]
        ],
        issues=[
            anchor
            | dict(
                category="style_suggestion",
                why="A more precise description helps.",
                better="Adults with limited literacy often struggle to secure stable employment.",
                explanation_ru="Уточните характер трудностей.",
                corrected_translation_ru=(
                    "Взрослым с низкой грамотностью часто трудно найти постоянную работу."
                ),
            )
        ],
        uncertainty="Repeated text limits the evidence of independent development.",
    )


def signed(path, h, data, secret="w" * 64):
    body = json.dumps(data)
    stamp = str(int(time.time()))
    signature = hmac.new(
        secret.encode(), f"{stamp}\n{path}\n{body}".encode(), hashlib.sha256
    ).hexdigest()
    return dict(
        headers=h
        | {
            "Content-Type": "application/json",
            "X-Writing-Time": stamp,
            "X-Writing-Signature": signature,
        },
        content=body,
    )


def create(client, h, task="writing-t2-000004"):
    r = client.post(BASE + "/attempts", headers=h, json=dict(task_id=task, event_id=str(uuid4())))
    assert r.status_code == 201, r.text
    return r.json()


def test_dataset():
    master, ready, counts = validate_dataset()
    assert len(master) == 326 and len(ready) == 32 and counts["MERGED_ALIAS"] == 6
    assert words("Don't   re-write... children’s  future!") == 4


@pytest.mark.parametrize(
    "change",
    [
        "schema",
        "missing",
        "score",
        "quote",
        "offset",
        "total",
        "missing_tr",
        "overlap",
        "generic",
        "certainty",
    ],
)
def test_invalid_contract(change):
    r = assessment()
    if change == "generic":
        r["criteria"][2]["improvement"] = "Incorporate even more sophisticated collocations."
    if change == "certainty":
        r["uncertainty"] = "None."
    if change == "schema":
        r["unexpected"] = True
    if change == "missing":
        r["criteria"].pop()
    if change == "score":
        r["criteria"][0]["band"] = 6.3
    if change == "quote":
        r["criteria"][0]["evidence"][0]["quote"] = "This was never written."
    if change == "offset":
        r["issues"][0]["start"] = 1
    if change == "total":
        r["estimated_band"] = 9
    if change == "missing_tr":
        r["criteria"][0]["evidence"] = []
    if change == "overlap":
        r["issues"] *= 2
    with pytest.raises(ValueError):
        validate_assessment(r, ESSAY)


def test_utf16_and_server_total():
    essay = "😀 " + ESSAY
    r = assessment(essay)
    assert validate_assessment(r, essay)["estimated_band"] == 6
    r["criteria"][0]["band"] = 7
    assert validate_assessment(r, essay)["estimated_band"] == 6.5


def test_writing_postgres(system, monkeypatch):
    db, client, _ = system
    monkeypatch.setenv("WRITING_BRIDGE_SECRET", "w" * 64)
    assert import_tasks(db) == import_tasks(db)
    owner, _ = bootstrap(client, "husband")
    other, _ = bootstrap(client, "wife")
    h = headers(owner)
    foreign = headers(other)
    assert client.get(BASE + "/tasks").status_code == 401
    tasks = client.get(BASE + "/tasks", headers=h).json()["items"]
    assert len(tasks) == 32
    assert client.get(BASE + "/tasks/writing-t2-000001", headers=h).status_code == 404
    a = create(client, h)
    aid = a["id"]
    path = BASE + f"/attempts/{aid}"
    assert client.get(path, headers=foreign).status_code == 404
    for body, status in [
        (dict(expected_version=0, essay="short"), 200),
        (dict(expected_version=0, essay="stale"), 409),
        (dict(expected_version=1, essay="word " * 2001), 422),
        (dict(expected_version=1, essay="a" * 16001), 422),
    ]:
        assert client.put(path, headers=h, json=body).status_code == status
    assert client.post(path + "/submit", headers=h, json={"expected_version": 1}).status_code == 422
    assert (
        client.put(path, headers=foreign, json={"expected_version": 1, "essay": ESSAY}).status_code
        == 404
    )
    a = client.put(path, headers=h, json={"expected_version": 1, "essay": ESSAY}).json()
    assert (
        client.put(path, headers=h, json={"expected_version": 1, "essay": ESSAY}).json()["version"]
        == a["version"]
    )
    assert client.get(path, headers=h).json()["essay"] == ESSAY
    for _ in range(2):
        assert (
            client.post(
                path + "/submit", headers=h, json={"expected_version": a["version"]}
            ).status_code
            == 200
        )
    assert (
        client.put(
            path, headers=h, json={"expected_version": a["version"], "essay": "changed"}
        ).status_code
        == 409
    )
    claim = path + "/assessment/claim"
    complete = path + "/assessment/complete"
    assert client.post(claim, headers=h, json={}).status_code == 403
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: client.post(claim, **signed(claim, h, {})), range(2)))
    assert sorted(r.status_code for r in results) == [200, 409]
    lease = next(r.json()["lease"] for r in results if r.status_code == 200)
    bad = assessment()
    bad["issues"][0]["start"] = 2
    assert (
        client.post(complete, **signed(complete, h, {"lease": lease, "review": bad})).status_code
        == 422
    )
    bad_v3 = assessment()
    bad_v3["quality_policy"] = "writing-accuracy-v3"
    assert (
        client.post(complete, **signed(complete, h, {"lease": lease, "review": bad_v3})).status_code
        == 422
    )
    bad_v4 = assessment()
    bad_v4["quality_policy"] = "writing-accuracy-v4"
    assert (
        client.post(complete, **signed(complete, h, {"lease": lease, "review": bad_v4})).status_code
        == 422
    )
    assert client.get(path, headers=h).json()["assessment"] is None
    assert (
        client.post(complete, **signed(complete, h, {"lease": lease})).json()["ai_status"]
        == "AI_UNAVAILABLE"
    )
    lease = client.post(claim, **signed(claim, h, {})).json()["lease"]
    result = client.post(
        complete,
        **signed(
            complete,
            h,
            dict(lease=lease, review=assessment(), provider="cloudflare", model="mock-model"),
        ),
    )
    assert result.status_code == 200, result.text
    assert result.json()["assessment"]["essay_version"] == a["version"]
    cached = client.post(claim, **signed(claim, h, {})).json()
    assert cached["cached"]
    assert cached["attempt"]["assessment"] == result.json()["assessment"]
    assert client.post(complete, **signed(complete, foreign, dict(lease=lease))).status_code == 404
    second = create(client, h)
    assert second["id"] != aid
    assert client.get(path, headers=h).json()["assessment"] == result.json()["assessment"]


@pytest.mark.skipif(
    os.environ.get("ALUA_WRITING_BROWSER") != "1", reason="Explicit browser/live runner only"
)
def test_writing_browser(system, monkeypatch, tmp_path):
    import uvicorn

    db, client, _ = system
    monkeypatch.setenv("WRITING_BRIDGE_SECRET", "w" * 64)
    import_tasks(db)
    owner, _ = bootstrap(client, "husband")
    fixture = tmp_path / "writing.json"
    fixture.write_text(
        json.dumps(
            dict(
                token=owner["token"],
                uid=owner["profile"]["uid"],
                essay=(
                    LIVE_ESSAY
                    if os.environ.get("ALUA_WRITING_LIVE") == "1"
                    else "Adults without literacy skills face serious barriers at work. "
                    + LIVE_ESSAY
                    if os.environ.get("ALUA_WRITING_INCIDENT") == "1"
                    else ESSAY
                ),
                review=assessment(),
            )
        )
    )
    fixture.chmod(0o600)
    server = uvicorn.Server(
        uvicorn.Config(client.app, host="127.0.0.1", port=3439, log_level="warning", lifespan="off")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started and time.monotonic() < deadline:
            time.sleep(0.02)
        assert server.started
        subprocess.run(
            ["node", "scripts/test-writing.mjs", str(fixture)],
            cwd=Path(__file__).resolve().parents[2] / "web",
            check=True,
            env=dict(os.environ, ALUA_LOCAL_STACK="true", WRANGLER_SEND_METRICS="false"),
            timeout=300,
        )
    finally:
        server.should_exit = True
        thread.join(10)


LIVE_ESSAY = """
Although education is widely available, some adults enter employment without being able to
read or write confidently. This limits their choices and can make ordinary
responsibilities stressful. Governments should respond with accessible teaching rather
than assuming that these adults can return to school without help.

The most immediate disadvantage is restricted access to stable work. Many employers
require applicants to complete online forms and read safety instructions. A capable worker
may therefore be rejected before an interview because they cannot understand the
application. Even after finding a job, they may struggle to learn new procedures and
become dependent on colleagues. These difficulties can reduce both income and confidence.

Limited literacy also affects life outside work. Reading a rental agreement, checking
medicine instructions or understanding a letter from a child's school can be difficult.
For example, a parent who cannot read a school message may miss an important meeting and
appear uninterested despite wanting to support their child. The consequences extend beyond
one person's employment prospects.

Government support should combine adult literacy classes with practical assistance.
Evening courses at libraries or community centres would allow employed adults to attend
without losing wages. Free childcare and transport support would remove further barriers.
Teachers should use everyday documents and workplace examples so that learners can apply
their skills immediately. Confidential enrolment could also help adults who feel
embarrassed about returning to education.

In conclusion, poor literacy restricts employment and makes essential daily tasks harder.
Publicly funded, flexible teaching can address these problems, but courses will only be
useful if adults can attend them alongside their existing responsibilities. Success should
be measured by practical improvements in learners' independence, rather than simply
counting course registrations."""

# Keep paragraphs intact while source-formatting this synthetic live sample.
LIVE_ESSAY = "\n\n".join(" ".join(p.split()) for p in LIVE_ESSAY.strip().split("\n\n"))


def test_writing_distinguishes_attempt_and_hourly_caps(system, monkeypatch):
    from datetime import UTC, datetime, timedelta

    from app.modules.writing.models import WritingAttemptRow

    db, client, _ = system
    monkeypatch.setenv("WRITING_BRIDGE_SECRET", "w" * 64)
    import_tasks(db)
    owner, _ = bootstrap(client, "husband")
    h = headers(owner)
    rows = []
    for _ in range(4):
        a = create(client, h)
        path = BASE + "/attempts/" + a["id"]
        client.put(path, headers=h, json={"expected_version": 0, "essay": ESSAY})
        client.post(path + "/submit", headers=h, json={"expected_version": 1})
        rows.append(a["id"])
    now = datetime.now(UTC)
    with db.session() as s:
        for aid, count, age in zip(rows[:3], [3, 2, 1], [10, 20, 30], strict=True):
            a = s.get(WritingAttemptRow, aid)
            a.ai_calls = count
            a.ai_started_at = now - timedelta(minutes=age)
    path = BASE + "/attempts/" + rows[0] + "/assessment/claim"
    limit = client.post(path, **signed(path, h, {}))
    assert limit.status_code == 429
    assert limit.json()["error"]["code"] == "writing_attempt_limit"
    assert limit.json()["error"]["retryable"] is False
    assert "retry-after" not in limit.headers
    path = BASE + "/attempts/" + rows[3] + "/assessment/claim"
    window = client.post(path, **signed(path, h, {}))
    assert window.status_code == 429
    assert window.json()["error"]["code"] == "writing_rate_limited"
    assert 1790 <= int(window.headers["retry-after"]) <= 1800
    with db.session() as s:
        assert s.get(WritingAttemptRow, rows[0]).ai_calls == 3
        assert s.get(WritingAttemptRow, rows[3]).ai_calls == 0
        assert s.get(WritingAttemptRow, rows[0]).essay == ESSAY


def test_writing_persists_typed_failure_without_assessment(system, monkeypatch):
    db, client, _ = system
    monkeypatch.setenv("WRITING_BRIDGE_SECRET", "w" * 64)
    import_tasks(db)
    owner, _ = bootstrap(client, "husband")
    h = headers(owner)
    a = create(client, h)
    path = BASE + "/attempts/" + a["id"]
    client.put(path, headers=h, json={"expected_version": 0, "essay": ESSAY})
    client.post(path + "/submit", headers=h, json={"expected_version": 1})
    claim_path, complete_path = path + "/assessment/claim", path + "/assessment/complete"
    claim = client.post(claim_path, **signed(claim_path, h, {})).json()
    assert claim["failure_protocol"] == 1
    completed = client.post(
        complete_path,
        **signed(complete_path, h, {"lease": claim["lease"], "failure_kind": "invalid_response"}),
    ).json()
    assert completed["ai_status"] == "invalid_response"
    assert completed["assessment"] is None and completed["essay"] == ESSAY
    assert client.get(path, headers=h).json()["ai_status"] == "invalid_response"


# Deterministic contract tests only: these synthetic outputs do not measure LLM quality.
def accuracy_assessment():
    fixture = json.loads(
        (Path(__file__).parents[2] / "web/tests/fixtures/writing-advertising-v2.json").read_text()
    )
    essay = fixture["essay"]
    review = assessment(essay)
    review.update(quality_policy="writing-accuracy-v2", issues=[], top_improvements=[])
    for criterion, band in zip(review["criteria"], (6, 7, 8, 9), strict=True):
        criterion.update(band=band, improvement=None, target=None)
    return essay, review


@pytest.mark.parametrize("count", range(4))
def test_accuracy_empty_issues_and_optional_advice(count):
    essay, review = accuracy_assessment()
    del review["criteria"][0]["improvement"]
    review["top_improvements"] = [
        dict(
            action=f"Develop relevant argument {i}.",
            quote=review["criteria"][0]["evidence"][0]["quote"],
            target=None,
        )
        for i in range(count)
    ]
    out = validate_assessment(review, essay)
    assert out["issues"] == []
    assert len(out["top_improvements"]) == count
    assert [c["band"] for c in out["criteria"]] == [6, 7, 8, 9]
    assert out["task2_mean"] == out["estimated_band"] == 7.5
    assert out["quality_policy"] == "writing-accuracy-v2"
    assert out["feedback_semantics"] == "NOT VERIFIED"


def accuracy_style(essay, original, replacement):
    sentence = next(s.strip() + "." for s in essay.split(".") if original in s)
    start = len(essay[: essay.index(sentence)].encode("utf-16-le")) // 2
    return dict(
        quote=sentence,
        start=start,
        end=start + len(sentence.encode("utf-16-le")) // 2,
        category="style_suggestion",
        why="Optional alternative; the original is acceptable English.",
        better=sentence.replace(original, replacement),
        explanation_ru="Необязательная альтернатива.",
        corrected_translation_ru="Синтетический перевод для проверки контракта.",
        target=dict(original=original, replacement=replacement),
        correction_type="optional",
        necessity="Not necessary: the original is valid; this changes emphasis only.",
    )


@pytest.mark.parametrize(
    "original,replacement",
    [
        ("advertisers frequently manufacture", "advertisers often create"),
        ("the consumer", "consumers"),
        ("relentless marketing", "aggressive marketing campaigns"),
    ],
)
def test_accuracy_style_is_not_a_mandatory_language_error(original, replacement):
    essay, review = accuracy_assessment()
    issue = accuracy_style(essay, original, replacement)
    review["issues"] = [issue]
    assert validate_assessment(review, essay)["issues"][0]["category"] == "style_suggestion"
    for category in ("grammar_error", "lexical_error"):
        issue["category"] = category
        with pytest.raises(ValueError, match="correction_type"):
            validate_assessment(review, essay)


@pytest.mark.parametrize("location", ["issue", "criterion", "top"])
def test_accuracy_rejects_mismatched_expression_evidence(location):
    essay, review = accuracy_assessment()
    target = dict(original="relentless marketing", replacement="aggressive marketing campaigns")
    anchor = review["criteria"][0]["evidence"][0]
    if location == "issue":
        review["issues"] = [
            accuracy_style(
                essay, **dict(original=target["original"], replacement=target["replacement"])
            )
            | anchor
        ]
    elif location == "criterion":
        review["criteria"][2].update(improvement="Optional wording alternative.", target=target)
    else:
        review["top_improvements"] = [
            dict(action="Optional wording alternative.", quote=anchor["quote"], target=target)
        ]
    with pytest.raises(ValueError, match="target_source_mismatch"):
        validate_assessment(review, essay)


@pytest.mark.parametrize(
    "mutation",
    [
        "policy",
        "necessity",
        "replacement",
        "category",
        "too_many",
        "missing_target",
        "nan",
        "reverse",
    ],
)
def test_accuracy_invalid_structures(mutation):
    essay, review = accuracy_assessment()
    issue = accuracy_style(essay, "relentless marketing", "aggressive marketing campaigns")
    review["issues"] = [issue]
    if mutation == "policy":
        review["quality_policy"] = "unrecognised"
    elif mutation == "necessity":
        del issue["necessity"]
    elif mutation == "replacement":
        issue["better"] = "A rewrite without the declared replacement."
    elif mutation == "category":
        issue["category"] = "invented_category"
    elif mutation == "too_many":
        review["top_improvements"] = [
            dict(action=f"Develop argument {i}.", quote=issue["quote"], target=None)
            for i in range(4)
        ]
    elif mutation == "missing_target":
        del review["criteria"][0]["target"]
    elif mutation == "nan":
        review["criteria"][0]["band"] = float("nan")
    else:
        issue["end"] = issue["start"]
    with pytest.raises(ValueError):
        validate_assessment(review, essay)


@pytest.mark.parametrize(
    "bands,mean,estimate",
    [
        ((6, 6, 6, 6), 6, 6),
        ((7, 6, 6, 6), 6.25, 6.5),
        ((7, 7, 7, 6), 6.75, 7),
        ((9, 8, 7, 6), 7.5, 7.5),
        ((0, 0, 0, 0), 0, 0),
    ],
)
def test_accuracy_task2_mean_and_existing_display_convention(bands, mean, estimate):
    essay, review = accuracy_assessment()
    for criterion, band in zip(review["criteria"], bands, strict=True):
        criterion["band"] = band
    out = validate_assessment(review, essay)
    assert out["task2_mean"] == mean
    assert out["estimated_band"] == estimate


def test_accuracy_legacy_half_band_preserved():
    review = assessment()
    review["criteria"][2]["band"] = 6.5
    out = validate_assessment(review, ESSAY)
    assert out["criteria"][2]["band"] == 6.5
    assert "quality_policy" not in out


def test_accuracy_half_band_scale_not_changed_without_official_increment_confirmation():
    essay, review = accuracy_assessment()
    review["criteria"][2]["band"] = 7.5
    assert validate_assessment(review, essay)["criteria"][2]["band"] == 7.5


def v3_assessment():
    essay, review = accuracy_assessment()
    review["quality_policy"] = "writing-accuracy-v3"
    review["task_understanding"] = dict(
        essay_type="discussion and opinion",
        position="Economic benefits coexist with social costs.",
        position_development="Relevant reasons are developed in the body.",
        position_claims=[
            dict(
                claim="Advertising has economic benefits.",
                development="developed",
                basis="The body explains employment effects.",
            )
        ],
        requirements=[
            dict(
                requirement="Discuss both views",
                coverage="addressed",
                explanation="Both sides receive body paragraphs.",
            )
        ],
    )
    for criterion in review["criteria"]:
        criterion.update(
            strengths=["A concrete synthetic strength."],
            limitations=[],
            descriptor_fit="Synthetic descriptor-based justification.",
        )
    return essay, review


@pytest.mark.parametrize(
    "mutation",
    ["valid", "task", "claims", "strengths", "limitations", "fit", "impact", "contradiction"],
)
def test_v3_structured_analysis(mutation):
    essay, review = v3_assessment()
    if mutation == "valid":
        value = validate_assessment(review, essay)
        assert value["quality_policy"] == "writing-accuracy-v3"
        assert value["issues"] == []
        assert value["task_understanding"]["requirements"][0]["coverage"] == "addressed"
        return
    if mutation == "task":
        del review["task_understanding"]
    elif mutation == "claims":
        review["task_understanding"]["position_claims"] = []
    elif mutation == "strengths":
        review["criteria"][0]["strengths"] = []
    elif mutation == "limitations":
        del review["criteria"][0]["limitations"]
    elif mutation == "fit":
        del review["criteria"][0]["descriptor_fit"]
    else:
        review["criteria"][3]["limitations"] = [
            dict(
                description="A concrete loss of control.",
                impact="unknown" if mutation == "impact" else "substantial",
            )
        ]
    with pytest.raises(ValueError):
        validate_assessment(review, essay)


def test_v3_independent_high_grammar_and_lower_task_response():
    essay, review = v3_assessment()
    review["criteria"][0].update(
        band=7,
        limitations=[
            dict(description="A central thesis proposition is not developed.", impact="substantial")
        ],
    )
    assert [c["band"] for c in validate_assessment(review, essay)["criteria"]] == [7, 7, 8, 9]


def v4_assessment():
    essay, old = accuracy_assessment()
    criteria = [
        dict(
            name=c["name"],
            strength="A concrete synthetic strength.",
            limitation=None,
            descriptor_fit="Synthetic descriptor-based justification.",
            evidence=c["evidence"],
            band=c["band"],
            improvement=None,
            improvement_quote=None,
        )
        for c in old["criteria"]
    ]
    return essay, dict(
        quality_policy="writing-accuracy-v4",
        criteria=criteria,
        top_improvements=[],
        issues=[],
        uncertainty="AI estimate, not verified examiner calibration.",
    )


def test_v4_compact_and_legacy_totals():
    essay, raw = v4_assessment()
    result = validate_assessment(raw, essay)
    assert result["task2_mean"] == result["estimated_band"] == 7.5
    assert result["quality_policy"] == "writing-accuracy-v4"
    assert result["top_improvements"] == result["issues"] == []
    for policy in ("writing-accuracy-v2", "writing-accuracy-v3"):
        text, legacy = accuracy_assessment() if policy.endswith("v2") else v3_assessment()
        assert validate_assessment(legacy, text)["quality_policy"] == policy


@pytest.mark.parametrize(
    "mutation", ["quote", "band", "extra", "missing", "style", "top", "unchanged", "overlap"]
)
def test_v4_persistence_contract_rejects_invalid(mutation):
    essay, raw = v4_assessment()
    quote = raw["criteria"][0]["evidence"][0]["quote"]
    raw["issues"] = [
        dict(
            quote=quote,
            start=0,
            end=len(quote),
            category="grammar_error",
            why="Synthetic validation fixture, not a linguistic claim.",
            better="A different synthetic fragment.",
        )
    ]
    if mutation == "quote":
        raw["issues"][0]["quote"] = "Fabricated quotation."
    elif mutation == "band":
        raw["criteria"][0]["band"] = 7.2
    elif mutation == "extra":
        raw["estimated_band"] = 9
    elif mutation == "missing":
        del raw["criteria"][0]["descriptor_fit"]
    elif mutation == "style":
        raw["issues"][0]["category"] = "style_suggestion"
    elif mutation == "top":
        raw["top_improvements"] = [dict(action="Unrelated action.", quote=quote)]
    elif mutation == "unchanged":
        raw["issues"][0]["better"] = quote
    else:
        raw["issues"] *= 2
    with pytest.raises(ValueError):
        validate_assessment(raw, essay)


def test_v4_dataset_reproducible_without_modifying_source(tmp_path):
    import importlib.util

    root = Path(__file__).resolve().parents[2]
    source = root / "web/tests/fixtures/writing-v4/source.txt"
    before = source.read_bytes()
    spec = importlib.util.spec_from_file_location(
        "prepare_writing_v4", root / "web/scripts/prepare-writing-v4.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    output = tmp_path / "dataset"
    module.prepare(source, output)
    expected = json.loads((root / "web/tests/fixtures/writing-v4/dataset.json").read_text())
    assert json.loads((output / "dataset.json").read_text()) == expected
    assert len(expected) == len({r["id"] for r in expected}) == 24
    assert source.read_bytes() == before
    assert len(module.DEV) == 14 and len(module.HOLDOUT) == 10
    assert not module.DEV & module.HOLDOUT


def test_v4_fragment_utf16_offsets():
    _, raw = v4_assessment()
    essay = "😀 People has cars."
    anchor = dict(quote=essay, start=0, end=len(essay.encode("utf-16-le")) // 2)
    for criterion in raw["criteria"]:
        criterion["evidence"] = [anchor]
    raw["issues"] = [
        dict(
            quote="People has",
            start=3,
            end=13,
            category="grammar_error",
            why="The plural subject requires have.",
            better="People have",
        )
    ]
    assert validate_assessment(raw, essay)["issues"][0]["start"] == 3
    raw["issues"][0]["start"] = 2
    with pytest.raises((ValueError, UnicodeError)):
        validate_assessment(raw, essay)


def test_v4_validates_all_evidence_before_display_normalization():
    _, raw = v4_assessment()
    sentences = [f"Source number {i}." for i in range(5)]
    essay = " ".join(sentences)
    evidence = []
    for sentence in sentences:
        start = essay.index(sentence)
        evidence.append(dict(quote=sentence, start=start, end=start + len(sentence)))
    for criterion in raw["criteria"]:
        criterion["evidence"] = evidence.copy()
    criterion = raw["criteria"][0]
    criterion["improvement"] = "Develop this claim."
    criterion["improvement_quote"] = sentences[-1]
    raw["top_improvements"] = [dict(action=criterion["improvement"], quote=sentences[-1])]
    result = validate_assessment(raw, essay)
    assert [a["quote"] for a in result["criteria"][0]["evidence"]] == [
        sentences[0], sentences[1], sentences[-1]
    ]
    assert all(len(c["evidence"]) == 3 for c in result["criteria"])
    for field in ("band", "strength", "limitation", "descriptor_fit", "improvement"):
        assert result["criteria"][0][field] == criterion[field]
    raw["criteria"][0]["evidence"][-1] = dict(quote="Fabricated.", start=0, end=11)
    with pytest.raises(ValueError, match="quote_mismatch"):
        validate_assessment(raw, essay)
