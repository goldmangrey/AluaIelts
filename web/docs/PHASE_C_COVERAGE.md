# Reading question coverage — Phase C

Counts are question groups (not scored positions). Public schema projections were used for tests; answer keys stay server-side.

| Backend type | All 72 | Enabled 63 | Scored positions (enabled) | Renderer | Verification sample |
|---|---:|---:|---:|---|---|
| `diagram_labelling` | 8 | 8 | 42 | Typed blocks + Field / AssetImage | `cambridge-05-test-02-p-2-g-21-23` |
| `flow_chart_completion` | 4 | 4 | 17 | Typed blocks + Field / AssetImage | `cambridge-05-test-02-p-1-g-04-08` |
| `matching_features` | 48 | 43 | 201 | Field select (Matching) | `cambridge-04-test-01-p-3-g-30-32` |
| `matching_headings` | 35 | 27 | 151 | Field select (Matching) | `cambridge-04-test-03-p-2-g-14-17` |
| `matching_information` | 57 | 51 | 250 | Field select (Matching) | `cambridge-04-test-02-p-3-g-27-32` |
| `matching_sentence_endings` | 21 | 15 | 64 | Field select (Matching) | `cambridge-05-test-02-p-2-g-24-27` |
| `multiple_choice_multiple` | 39 | 37 | 86 | MultiChoice / source inputs | `cambridge-04-test-02-p-3-g-33-35` |
| `multiple_choice_single` | 72 | 63 | 211 | RadioQuestion | `cambridge-04-test-01-p-1-g-14-14` |
| `note_completion` | 36 | 32 | 204 | Typed blocks + Field / AssetImage | `cambridge-08-test-03-p-3-g-33-36` |
| `sentence_completion` | 24 | 19 | 88 | Typed blocks + Field / AssetImage | `cambridge-04-test-04-p-1-g-07-10` |
| `short_answer` | 10 | 9 | 36 | Typed blocks + Field / AssetImage | `cambridge-04-test-01-p-1-g-09-13` |
| `summary_completion` | 91 | 83 | 390 | Typed blocks + Field / AssetImage | `cambridge-04-test-01-p-3-g-33-39` |
| `table_completion` | 19 | 18 | 96 | Typed blocks + Field / AssetImage | `cambridge-04-test-01-p-2-g-15-21` |
| `true_false_not_given` | 90 | 78 | 442 | RadioQuestion | `cambridge-04-test-01-p-1-g-01-08` |
| `yes_no_not_given` | 59 | 51 | 242 | RadioQuestion | `cambridge-04-test-02-p-1-g-10-13` |

All 15 types are rendered and have a browser-tested real-content sample. All 538 enabled groups additionally pass parser + server-render checks. Source image variants retain the source artwork and have numbered controls; they are not relabelled as semantic HTML reconstructions.

## Actual representations

- 491 enabled groups: `structured_text`; 47: `source_image_with_inputs`.
- All 18 table-completion groups, 4 flow-chart groups and 8 diagram groups use original source images. There are no actual `table` blocks in the enabled dataset. The renderer supports declared typed table blocks with HTML table/cell inputs; no layout is fabricated from OCR.
- `summary_completion`: 217 text positions and 173 single-select positions. The text variant may contain a plain-text word bank. Both preserve the provided context; no invented choices.
- `note_completion`: 193 text + 11 single-select; `short_answer`: 31 text + 5 single-select.
- Multiple-choice multiple: 37 groups / 86 positions. Typed groups use one checkbox collection mapped to separate question IDs, matching iOS and grading contracts.
- Specific source-only choices: Cambridge 07 Test 3 q26 (single) and q34–39 (multiple). q34–39 is declared structured but has no typed options and does have a registered source asset. The renderer explicitly uses that asset and numbered letter-entry fields, never guesses A–J options from OCR.
- Paragraph content consists of `heading` and `paragraph` blocks. Group blocks observed: `rich_text`, `image`, `list`; declared table/heading blocks are supported without unsafe HTML.

## Content limitations

All enabled tests remain not fully proofread. Backend-enabled is private-practice availability, not a content accuracy certification. Diagrams/source-only tasks cannot offer richer screen-reader semantics than the provided source text/alt metadata; source text is available in an expandable transcript. Semantic tables/flow nodes require verified content blocks from the existing content pipeline; no backend or dataset changes were made.

No known format among enabled tests is silently skipped. Unknown future types/representations, missing fields and missing required asset references fail explicitly. Actual PNG rendering was checked in browser tests, with an explicit 404/retry failure scenario.
