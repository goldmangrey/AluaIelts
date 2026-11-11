# ALUA IELTS Writing Task 2 — Dataset V2 Quality Repair

**Cutoff:** 2026-11-11. **Version:** 2. **Input:** 326 stable V1 records, 36 URLs, 446 reported source appearances. No V1 files were modified.

## Evidence and publication rule

All 326 records contain **independently drafted IELTS-style practice prompts**. These are **not original exam questions**. Their topics come from V1 editorial synopses, which themselves may have provenance errors. The main `writing-task2-v2.json` is an editorial workspace, **NOT a ready-to-publish bank of 326 verified recent exam questions**.

Only 32 records have been individually matched against a visible Task 2 on a newly opened source page and pass the rule-based practice task checks. They are exported separately as `alua-ready-practice-only.json`, and must always be labelled **Alua editorial practice task based on a third-party recall**. Not official Cambridge/IELTS text.

288 records have drafts but **need individual original-source content checking**. These are `PENDING_INDIVIDUAL_SOURCE_REVIEW` (or `MERGED_ALIAS` where applicable), and must not be marketed as verified IELTS exam questions or imported into the public app as such. Source pages were reachable, but simply reaching the page does NOT count as checking a particular question.

## Metrics

| Metric | V1 | V2 |
|---|---:|---:|
| Original records | 326 | 326 preserved |
| Ready practice questions (source item matched, non-alias) | 0 | 32 |
| Complete independently written practice prompts | 0 | 326 |
| Individual question matched to retrieved source | Not established | 38 |
| Essay types manually cross-checked against actual published task | Not established | 38 |
| Confirmed alias merges | 0 in V2 | 6 |
| Rejected records | 0 | 0 |
| Records pending item-level source review | — | 288 |
| Historical source URLs retained | 36 | 36 |
| Historical appearances retained | 446 | 446 |
| Original full texts with established reproduction rights | 0 | 0 |
| Editorial adaptations | 0 | 326 |
| Alias records (preserved, not published as separate tasks) | — | 6 |
| Structural/data validation issues | — | 0 |

### Source review interpretation

All **36/36 source pages** were opened through public web research as of 2026-11-11. The corpus still comes from **only two publisher domains**, neither of which establishes a candidate's identity or an official exam sitting. 38 selected V1 records were checked against the visible topic and task directive, not against the original IELTS exam paper. The list and line hints appear in `source-review.json` and each V2 item's `source_review_evidence`.

**NO official IELTS verification:** Zero independent multi-candidate confirmation; zero original wording licences. The authenticity field retains the V1 reported status; it is not increased to `MULTI_SOURCE_REPORTED`.

### Specific duplicate decisions

Confirmed editorial sameness in six pairs (the second ID is an alias, never removed):

- `000006` ← `000007`: advertising economic/social impacts.
- `000018` ← `000019`: animal use and animal rights.
- `000020` ← `000021`: artistic ability and natural talent.
- `000092` ← `000094`: family values versus school learning.
- `000280` ← `000283`: technology reducing versus enabling crime.
- `000295` ← `000296`: TV content versus viewing time for children.

These are *task-equivalence editorial merges*, not proof of independent test administrations. The previous 446 appearance entries and original 326 V1 IDs remain intact. Extra suspicious pairs were **kept distinct** and queued for examination in `duplicate-decisions.json` / `near-duplicate-review-queue.json`.

### Essay classification

The old category distribution was preserved unless a source shows an unequivocal reason to change it. No bulk rebalancing. For original `other` entries, the specific standalone question is preserved as an editorial instruction. No claims about a fixed official nine-type taxonomy.

### Review limitations and next steps

1. Run per-question verification for the 288 still-pending entries. `source-review.json` lists each source and its unverified V1 questions. The next queue should prioritise 2026, then 2025, then 2024, and then near-duplicates.
2. Ask a qualified IELTS content editor to read each adaptation in context. This version ran a structural/English editorial pass and required-directive checks, but **no independent native-speaking examiner signed off**.
3. Verify Academic status independently where possible. V1 classifies it from archive context; no exam operator verified particular sessions.
4. Complete rights/publishing review before production use. Only original Alua drafts are proposed for display; third-party full texts remain unlicensed and are not reproduced.
5. Avoid sorting by exact exam date where date fields are merely V1 candidate-reported or source-listed; publication date and exam date must not be conflated.
6. Keep all original V1 assets archived unmodified; aliases should resolve via `canonical_id_v2` without deleting their historical appearances.

### Technical quality report

- V1 record count unchanged; original field values byte-for-byte-equivalent at JSON value level.
- All V2 stable IDs preserved; source and appearance references intact.
- All 326 independently authored draft practice questions contain answerable directives appropriate to their recorded essay type; each Two-Part has at least two explicit questions.
- JSON Schema check: **PASS**; rule-based QA issues: **0**.
- CSV UTF-8 BOM and JSON parity: **PASS**.
- No original unlicensed full task text stored in `question_text` or `original_question_text`.
- This QA **does not** guarantee that 326 source topics have been matched or that adaptations match exact unretrieved subquestions.

### For developers

Import **`alua-ready-practice-only.json`** into an explicitly labelled *editorial IELTS-style practice* collection. Keep `writing-task2-v2.json` as archival/master curation data, including source/audit status. Never present a draft with `content_quality_status != READY` as an authenticated historical IELTS exam question.

### Continued review queue and topic tables

- `remaining-review-queue.json` lists all 288 item-level pending checks in descending year order, with near-duplicate flags and exact source links.
- `curation-batches.json` divides them into batches of at most 40 records; the batch status is *PENDING*, not completed.
- `topics-v2.json` and `essay-types-v2.json` add the READY and canonical counts without modifying the V1 taxonomy files.
- Editorially unique canonical count after six aliases: **320**. This is NOT a claim that all other pairs were proved unique.
