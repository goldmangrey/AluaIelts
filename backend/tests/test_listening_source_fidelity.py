"""Read-only legacy source projection; no real attempts or database needed."""

import copy

import pytest
from test_household_bootstrap import postgres_url, system  # noqa: F401
from test_listening import listening  # noqa: F401

from app.core.exceptions import NotFoundError
from app.modules.listening.catalog import ListeningCatalog
from app.modules.listening.source_materials import enrich_sources, semantic_source


def legacy_exam(catalog):
    old = copy.deepcopy(catalog.exams["cambridge-04-test-03"])
    removed = {m["asset_id"] for m in old["parts"][2]["visual_materials"]}
    part = old["parts"][2]
    part["visual_materials"] = []
    part["supporting_assets"] = []
    for group in part["groups"]:
        group["supporting_assets"] = []
        group["content_blocks"] = [
            b for b in group["content_blocks"] if b["kind"] != "original_source_image"
        ]
        for q in group["questions"]:
            q.pop("visual_binding", None)
    old["assets"] = [a for a in old["assets"] if a["asset_id"] not in removed]
    return old, removed


def test_legacy_sources_added_without_mutating_snapshot_or_question_semantics():
    catalog = ListeningCatalog()
    old, added = legacy_exam(catalog)
    original = copy.deepcopy(old)
    public = catalog.public_exam(old)
    assert old == original
    assert semantic_source(public["parts"]) == semantic_source(old["parts"])
    assert added <= {a["asset_id"] for a in public["assets"]}
    for aid in added:
        assert catalog.asset(old, aid).is_file()
    assert old == original


def test_changed_question_cannot_borrow_current_source_allowlist():
    catalog = ListeningCatalog()
    old, added = legacy_exam(catalog)
    old["parts"][2]["groups"][0]["questions"][0]["prompt"] = "A different historical question"
    assert enrich_sources(old, catalog.exams[old["exam_id"]]) is old
    for aid in added:
        with pytest.raises(NotFoundError):
            catalog.asset(old, aid)


def test_other_exam_or_private_source_is_not_added():
    catalog = ListeningCatalog()
    old, _ = legacy_exam(catalog)
    assert enrich_sources(old, catalog.exams["cambridge-04-test-02"]) is old
    with pytest.raises(NotFoundError):
        catalog.asset(old, "unknown-private-asset")


def test_public_projection_does_not_rewrite_persisted_attempt(listening):  # noqa: F811
    from uuid import uuid4

    from test_household_bootstrap import bootstrap, headers

    service, client, _, _ = listening
    device, _ = bootstrap(client, "husband")
    owner = device["profile"]["uid"]
    response = client.post(
        "/api/v1/listening/attempts",
        headers=headers(device),
        json={"event_id": str(uuid4()), "exam_id": "cambridge-04-test-03", "reuse_active": False},
    )
    assert response.status_code == 201
    aid = response.json()["id"]
    old, added = legacy_exam(service.catalog)
    with service.transaction(owner) as session:
        row = service.owned(session, owner, aid)
        row.snapshot = dict(row.snapshot, exam=old)

    def stored():
        with service.transaction(owner) as session:
            row = service.owned(session, owner, aid)
            return copy.deepcopy(
                (row.snapshot, row.answers, row.state, row.version, row.status, row.result)
            )

    before = stored()
    public = client.get(f"/api/v1/listening/attempts/{aid}", headers=headers(device))
    assert public.status_code == 200
    assert added <= {a["asset_id"] for a in public.json()["exam"]["assets"]}
    for asset in added:
        assert (
            client.get(
                f"/api/v1/listening/attempts/{aid}/assets/{asset}", headers=headers(device)
            ).status_code
            == 200
        )
    assert stored() == before
