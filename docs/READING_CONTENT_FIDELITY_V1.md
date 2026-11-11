# ALUA READING CONTENT FIDELITY V1 — FORENSIC AUDIT RESULT

**Release decision: NO-GO. Full evidence-based comparison is incomplete.**

This report covers the entire inventory and automated/browser inspection, but does not certify the entire library. Findings below are a confirmed lower bound. Independent OCR disagreements are a review queue, not confirmed corruption. No correctness percentage is inferred.

## Coverage

| Work | Actual result |
|---|---|
| Books / tests inventoried | 18/18 · 72/72 |
| Individual passage / group / question records | 216/216 · 613/613 · 2,880/2,880 |
| Independent recognition | 1,028/1,028 declared Reading physical pages; no recognition errors |
| Browser inspection | 72/72 tests; 2,880 Exam slots and 2,880 Review slots visible in disposable fixtures |
| Complete test comparison against local original-PDF reference | 1/72: Cambridge 7 Test 1 |
| Tests entirely source-verified without defects | 0/72 |
| Passages | 0 VERIFIED · 3 CORRUPTED · 213 NOT_AUDITED |
| Groups | 2 VERIFIED · 12 CORRUPTED · 1 UNRESOLVED · 598 NOT_AUDITED |
| Questions | 17 VERIFIED · 53 CORRUPTED · 5 UNRESOLVED · 2805 NOT_AUDITED · 0 BLOCKED |
| Original key comparison | 44/2,880 KEY_VERIFIED; 2836 KEY_UNVERIFIED |
| Adjudicated findings | 41 confirmed corruption issues + 2 source ambiguities |
| Recognition/detector candidates requiring adjudication | 2343; not confirmed defects |

“Examined 40/40” in the matrix means individual JSON/recognition/browser records were examined. It does **not** mean 40/40 were compared completely with the original page image. A CORRUPTED question may inherit a confirmed defect in required shared group context even when its own sentence is intact.

## Source integrity and provenance

All 18 local PDF hashes and all 18 intermediate TXT hashes match the dataset manifest. Hash equality identifies the generator inputs; it does not establish publisher authenticity or content accuracy. No source was downloaded or replaced.

The attachment named `Cambridge-IELTS-07(1).pdf` is not accessible as a distinct local attachment, so equivalence with it cannot be certified. Project, Desktop and Downloads C07 copies match each other. A different temporary 129-page C07 PDF was identified and excluded. See [attachment provenance](reading-content-fidelity-v1/attachment-provenance.json).

The local C04/C09/C20 files are Word-generated/native-text derivatives or third-party editions; publisher-edition equivalence remains unproven. C09 T3 Q33–37 is UNRESOLVED because the local PDF itself has suspicious wording and extra unnumbered blanks. C07/C08 embedded text is largely watermark text, so embedded text cannot be treated as English source authority. C14 has an ABBYY text layer with recognition artifacts; visible page images take precedence.

Physical PDF pages are 1-based. Printed page numbers are separate and recorded only when established; OCR footer candidates are explicitly unadjudicated. Most corpus page ranges come from existing JSON provenance and still require visual validation. Missing pages, source damage, edition equivalence and exact passage boundaries have **not** been exhaustively cleared across all books.

| Book | PDF pages | SHA-256 | Reading page profile |
|---|---:|---|---|
| 04 | 128 | `c019fb8d269d8df4783443c2351fc2cd5c71cc063c584b9397ef37a165cf2fe1` | {'DIGITAL_TEXT_OR_RETYPE': 73, 'IMAGE_OR_LOW_TEXT_MIXED': 1} |
| 05 | 178 | `7df6a474e84e69a622dd48fc009e69dd7fd711a64b713671bdf492311f5f58cc` | {'SCANNED_WITH_WATERMARK_TEXT_ONLY': 53} |
| 06 | 177 | `a5d4812f970087a7c6dcd7333450c875ed9a401b294a6237c1071ff2629dfc6f` | {'SCANNED_WITH_WATERMARK_TEXT_ONLY': 49} |
| 07 | 180 | `b0d7be939b192c4ea7601b2315049770b7705542f04ae9b87a19e37daac1c971` | {'SCANNED_WITH_WATERMARK_TEXT_ONLY': 36, 'IMAGE_OR_LOW_TEXT_MIXED': 14} |
| 08 | 173 | `2f3cdf0c049ecac93bafafd034c2316ac7ed66b0694bea8a2a7c152042923e23` | {'SCANNED_WITH_WATERMARK_TEXT_ONLY': 50} |
| 09 | 170 | `c3fbc2d06b1b60fe8e7d27936150a09c38714e4bd23e6351a09b93c9555ee890` | {'DIGITAL_TEXT_OR_RETYPE': 69} |
| 10 | 165 | `924bf69326e33aacf54dff62009ff5badf01d17d41340c3e242f86d278b6420d` | {'SCANNED_WITH_WATERMARK_TEXT_ONLY': 50} |
| 11 | 143 | `c0762211a85476475bf6f9b8b678b6863a62302c885d89208e23b9f446de9479` | {'SCANNED_WITH_WATERMARK_TEXT_ONLY': 50} |
| 12 | 136 | `c9b61939ce31049dd9552020dbaf3deb979cbb6244b4cac0ac64f13b3ce049c6` | {'SCANNED_WITH_WATERMARK_TEXT_ONLY': 49} |
| 13 | 143 | `f52f605f6b296954d33f6f7e6b235854ea6c96e4876eb9d5d339dc66292ba994` | {'SCANNED_WITH_WATERMARK_TEXT_ONLY': 51} |
| 14 | 142 | `f0f0d86e7cf93b37154696851b2e61be4f1194b05bd1651c1711e221720018ba` | {'MIXED_SEARCHABLE_SCAN': 50} |
| 15 | 147 | `f3cf750ff166026fb3e52745d53220f3f8ce4b4e1784a7208b92e21205b23e9e` | {'SCANNED_WITH_WATERMARK_TEXT_ONLY': 49, 'MIXED_SEARCHABLE_SCAN': 1} |
| 16 | 144 | `11675fa3dcb124e93afbf44371c174f676a78a260b01ebc190aae5f5fed3912e` | {'SCANNED_WITH_WATERMARK_TEXT_ONLY': 52} |
| 17 | 135 | `73b39f0fb941a647267c9907407af1cc34a81d66864da8a06759aa869d63794d` | {'SCANNED_WITH_WATERMARK_TEXT_ONLY': 50} |
| 18 | 147 | `7f2fdefa5af7b6b75640eec3b0e65c1d49ecb7bd311e1293d53b6377acacbe75` | {'SCANNED_WITH_WATERMARK_TEXT_ONLY': 52} |
| 19 | 138 | `5b460d32f81cba72576e097dba82d8817717f8ae6a261b428916b49dcbdb86c2` | {'SCANNED_WITH_WATERMARK_TEXT_ONLY': 51} |
| 20 | 183 | `1d9f817120206f380b06facfd95c59b71e7bccff2bd974f860a3e3e39dc492bb` | {'DIGITAL_TEXT_OR_RETYPE': 62, 'IMAGE_OR_LOW_TEXT_MIXED': 1} |
| 21 | 146 | `380b27bc658e606a72f1313e8b3375ab878865479e847d9b8598bbc8fa17d661` | {'SCANNED_WITH_WATERMARK_TEXT_ONLY': 51} |

## Confirmed findings

| Category | Distinct confirmed issues |
|---|---:|
| CHANGED_PUNCTUATION | 3 |
| CHANGED_WORDING | 9 |
| INCORRECT_BLANKS | 6 |
| INVENTED_OPTIONS | 1 |
| KEY_OPTION_BINDING | 1 |
| MISSING_CONTENT | 3 |
| OCR_ARTIFACT | 8 |
| STRUCTURAL_RENDERING | 4 |
| WRONG_INPUT_TYPE | 1 |
| WRONG_MISSING_OPTIONS | 5 |

Possible scoring impact: 27 distinct issues. Counts are deduplicated by finding, not by repeated field occurrence. Every affected JSON path is retained in CSV/JSON. Source ambiguities are excluded from confirmed corruption totals.

### Cambridge 7 Test 1 — full reference comparison

All three passages and all Q1–40 were compared, including instructions, paragraph sequence/labels, choices, shared summaries and required answer context, against physical PDF pages 22–33. The original key on physical page 157 (printed 153) was compared for all 40 answers and matches the existing key. Result: all three passages CORRUPTED; 29 questions CORRUPTED and 11 VERIFIED. The source reference remains the hash-bound local PDF, not an authenticated copy of the unavailable named attachment.

- P1 “Let’s Go Bats”: body-title extraction includes graphical rules as punctuation. Paragraph C/E contain meaning-bearing punctuation substitutions; a source paragraph is split at a page boundary. Q1–5 instructions use `Passage |` instead of `Passage 1`.
- Q6–9 “Facial Vision”: leader noise is embedded in the summary, including the fragment around blank 6; four original numbered blanks are not represented as inline answer slots. Full wording, limits and blank locations were visually compared.
- P2: corrupted title and gallon/litre footnote. Q14–20 omit Roman option `v`, merging its text into `iv`; the original Q16 key is `v`, which the UI cannot select. Q19/Q20 prompts are misassigned. The fallback source image itself ends after Q19 and omits Q20 “Paragraph H”.
- Q21–26: original source-image statements are visible, but underlying prompts contain isolated numbers or whole-group fallback text. The original instructions use YES/NO/NOT GIVEN; this is not a TRUE/FALSE defect.
- P3: duplicate title caused by case-sensitive heading suppression; one paragraph is split at the source page break. Q27/Q29/Q34 contain joined words.
- Q37–40: noisy blanks, reordered summary text, lost A–K labels and empty parsed options. Original key correspondence F/H/K/G was verified independently. The report retains short evidence excerpts and the minimum necessary crops.
- The source itself says “seven paragraphs A–H”. This inconsistency is SOURCE_AMBIGUITY, not an importer defect.

### Cambridge 6 Test 1 — Q23–26

Full surrounding group compared on physical page 26 (printed 25), including instructions, four blank positions and A–K options. `FECUCE 26 ...` corresponds to `reduce [26]`; blank 25’s number is lost. Options lose their labels and no inline blank slots are generated. All four questions are CORRUPTED. Original keys G/B/C/A are KEY_VERIFIED from physical page 153. Other C06 passages/questions are not certified.

### Other source-adjudicated cases

- C07 T4 Q30–34: noisy summary blanks and lost A–J labels; all five CORRUPTED. Q35–40 was fully compared and all six are VERIFIED; keys remain unverified.
- C14 T2 Q19–26: broken words such as `comi ng ... patie nts sufferi ng` and missing sentence punctuation; eight questions affected by shared context.
- C16 T2 Q17–20: corrupted summary; option C is merged into B and unavailable. Only blank 20 is inline; blanks 17–19 are detached.
- C16 T3 Q20–22: prose beginning “A team of archaeologists…” is parsed as option A, converting ONE WORD ONLY inputs into single-select controls with only A. All three are CORRUPTED.
- C09 T3 Q33–37: UNRESOLVED local-source wording/blank defects. No guessed replacement is asserted.
- Other books have automated disagreement candidates; they have not been converted into confirmed defects without source adjudication.

## Pipeline and root causes

`Local PDF → earlier OCR/extraction TXT → engine normalization/parsing → repairs/source edits/enrichment → exam JSON → ReadingCatalog/API → React renderer`

Confirmed upstream evidence: the critical OCR fragments already exist in intermediate TXT and persist into JSON. Original OCR engine/run is unavailable, so attribution to a particular OCR model remains suspected, not confirmed. Manifest hashes bind the current files to the generator inputs.

Confirmed transformation behavior, reproduced without invoking dataset generation:

- `backend/scripts/reading_dataset/engine.py`: option detection treats prose starting with “A” as a choice; non-empty parsed options then force single-select input. Broken option labels disappear from parsed options/allowed values.
- `engine.py` rich-text blank recognition relies on underscore-style patterns; corrupted dotted leaders do not become numbered inline slots. Whole-group prompt fallback repeats or misassigns context.
- `backend/scripts/reading_dataset/pdf_support.py`: source-image crop clamps to 93.5% page height; C07 physical page 26 Q20 begins below the resulting crop. Both metadata coordinates and browser image were checked.
- `web/src/features/reading/exam/passage-pane.tsx`: case-sensitive duplicate-heading comparison lets EDUC ATING PSYCHE appear again under its title.
- `question-renderer.tsx` can show generic answer rows when summary slots were not parsed. Image fallback can restore source wording for some groups, but cannot repair missing choices or already clipped source images.

Existing validator gaps: structural 40-question coverage, schema validity, file hashes and grader examples cannot verify original wording, option-label fidelity, negation/limits or image-crop completeness. Current local production statuses are 69 `needs_review`, 3 `blocked`, 0 source-verified; these are reported separately from forensic classifications. Existing hash-bound source edits do not provide corpus-wide content verification.

## Reproducible method and limitations

1. Inventory protected production inputs, SHA-256 PDFs/intermediates, page metadata and declared provenance.
2. Fresh Tesseract recognition of all 1,028 declared Reading pages rendered at 2.5×; embedded text is retained separately. Bounded workers and hash/page checkpoints allow resume. Independent recognition is not proof of source accuracy.
3. Compare all content-bearing fields, including clean-looking text, to recognized source blocks. Normalize harmless whitespace only; retain letters, digits and punctuation. Token operations and normalized offsets are in `checkpoints/diffs-XX.json`. OCR/layout alignment can produce false positives and false negatives.
4. Type-specific automated checks cover all 15 encountered types, including limits, choice labels/reuse, multi-answer grouping and completion slots. Table/flowchart/diagram semantics still require page-image review; generic schema checks do not certify them.
5. Visually adjudicate complete source context, record crop coordinates, source hash, physical/printed pages and every affected field. Only explicit complete, hash-bound review records can set VERIFIED.
6. Inspect unchanged production renderers with disposable Exam/Review fixtures, no DB writes or live user attempts. All 72 tests were inspected in Chromium. This establishes control/context visibility, not full text fidelity or cross-browser equivalence. Full WebKit/mobile source-fidelity validation was not performed.

Evidence crops and excerpts are restricted to defects or disputed context; entire copyrighted books are not bundled in this report. Raw OCR remains in `/tmp/alua-reading-fidelity-work` and can be regenerated from the local PDFs. Checkpoints are deterministic; recognition caches and manual source-review records have separate meanings.

## Full test / passage matrix

V=VERIFIED, C=CORRUPTED, U=UNRESOLVED, N=NOT_AUDITED. Passage status refers to passage content, not a clean bill of health for its question groups. `40/40` is automated/browser record coverage. `Full Q` counts questions whose entire required source context has been compared. Keys are independently source-verified.

| Book/Test | Records | P1 | P2 | P3 | Q V/C/U/N | Full Q | Keys | Groups V/C/U/N | Rendering |
|---|---|---|---|---|---|---:|---|---|---|
| C04 T1 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/9 | Chromium Exam+Review inspected |
| C04 T2 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/9 | Chromium Exam+Review inspected |
| C04 T3 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/10 | Chromium Exam+Review inspected |
| C04 T4 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/10 | Chromium Exam+Review inspected |
| C05 T1 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/9 | Chromium Exam+Review inspected |
| C05 T2 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/10 | Chromium Exam+Review inspected |
| C05 T3 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/9 | Chromium Exam+Review inspected |
| C05 T4 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/8 | Chromium Exam+Review inspected |
| C06 T1 | 40/40 | N | N | N | 0/4/0/36 | 4/40 | 4/40 | 0/1/0/7 | Chromium Exam+Review inspected |
| C06 T2 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/7 | Chromium Exam+Review inspected |
| C06 T3 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/9 | Chromium Exam+Review inspected |
| C06 T4 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/9 | Chromium Exam+Review inspected |
| C07 T1 | 40/40 | C | C | C | 11/29/0/0 | 40/40 | 40/40 | 1/7/0/0 | Chromium Exam+Review inspected |
| C07 T2 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/10 | Chromium Exam+Review inspected |
| C07 T3 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/9 | Chromium Exam+Review inspected |
| C07 T4 | 40/40 | N | N | N | 6/5/0/29 | 11/40 | 0/40 | 1/1/0/5 | Chromium Exam+Review inspected |
| C08 T1 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/7 | Chromium Exam+Review inspected |
| C08 T2 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/8 | Chromium Exam+Review inspected |
| C08 T3 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/9 | Chromium Exam+Review inspected |
| C08 T4 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/9 | Chromium Exam+Review inspected |
| C09 T1 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/9 | Chromium Exam+Review inspected |
| C09 T2 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/10 | Chromium Exam+Review inspected |
| C09 T3 | 40/40 | N | N | N | 0/0/5/35 | 0/40 | 0/40 | 0/0/1/8 | Chromium Exam+Review inspected |
| C09 T4 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/8 | Chromium Exam+Review inspected |
| C10 T1 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/8 | Chromium Exam+Review inspected |
| C10 T2 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/8 | Chromium Exam+Review inspected |
| C10 T3 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/10 | Chromium Exam+Review inspected |
| C10 T4 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/8 | Chromium Exam+Review inspected |
| C11 T1 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/7 | Chromium Exam+Review inspected |
| C11 T2 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/10 | Chromium Exam+Review inspected |
| C11 T3 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/7 | Chromium Exam+Review inspected |
| C11 T4 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/9 | Chromium Exam+Review inspected |
| C12 T5 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/7 | Chromium Exam+Review inspected |
| C12 T6 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/10 | Chromium Exam+Review inspected |
| C12 T7 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/7 | Chromium Exam+Review inspected |
| C12 T8 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/8 | Chromium Exam+Review inspected |
| C13 T1 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/8 | Chromium Exam+Review inspected |
| C13 T2 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/8 | Chromium Exam+Review inspected |
| C13 T3 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/8 | Chromium Exam+Review inspected |
| C13 T4 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/8 | Chromium Exam+Review inspected |
| C14 T1 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/9 | Chromium Exam+Review inspected |
| C14 T2 | 40/40 | N | N | N | 0/8/0/32 | 8/40 | 0/40 | 0/1/0/6 | Chromium Exam+Review inspected |
| C14 T3 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/9 | Chromium Exam+Review inspected |
| C14 T4 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/9 | Chromium Exam+Review inspected |
| C15 T1 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/10 | Chromium Exam+Review inspected |
| C15 T2 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/8 | Chromium Exam+Review inspected |
| C15 T3 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/7 | Chromium Exam+Review inspected |
| C15 T4 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/9 | Chromium Exam+Review inspected |
| C16 T1 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/8 | Chromium Exam+Review inspected |
| C16 T2 | 40/40 | N | N | N | 0/4/0/36 | 4/40 | 0/40 | 0/1/0/7 | Chromium Exam+Review inspected |
| C16 T3 | 40/40 | N | N | N | 0/3/0/37 | 3/40 | 0/40 | 0/1/0/8 | Chromium Exam+Review inspected |
| C16 T4 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/9 | Chromium Exam+Review inspected |
| C17 T1 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/9 | Chromium Exam+Review inspected |
| C17 T2 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/8 | Chromium Exam+Review inspected |
| C17 T3 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/8 | Chromium Exam+Review inspected |
| C17 T4 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/9 | Chromium Exam+Review inspected |
| C18 T1 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/9 | Chromium Exam+Review inspected |
| C18 T2 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/7 | Chromium Exam+Review inspected |
| C18 T3 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/9 | Chromium Exam+Review inspected |
| C18 T4 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/10 | Chromium Exam+Review inspected |
| C19 T1 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/9 | Chromium Exam+Review inspected |
| C19 T2 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/9 | Chromium Exam+Review inspected |
| C19 T3 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/8 | Chromium Exam+Review inspected |
| C19 T4 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/8 | Chromium Exam+Review inspected |
| C20 T1 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/8 | Chromium Exam+Review inspected |
| C20 T2 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/9 | Chromium Exam+Review inspected |
| C20 T3 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/9 | Chromium Exam+Review inspected |
| C20 T4 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/8 | Chromium Exam+Review inspected |
| C21 T1 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/8 | Chromium Exam+Review inspected |
| C21 T2 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/9 | Chromium Exam+Review inspected |
| C21 T3 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/7 | Chromium Exam+Review inspected |
| C21 T4 | 40/40 | N | N | N | 0/0/0/40 | 0/40 | 0/40 | 0/0/0/9 | Chromium Exam+Review inspected |

## Book totals

| Book | Tests | Passages V/C/N | Questions V/C/U/N | Keys verified |
|---|---:|---|---|---:|
| 04 | 4 | 0/0/12 | 0/0/0/160 | 0 |
| 05 | 4 | 0/0/12 | 0/0/0/160 | 0 |
| 06 | 4 | 0/0/12 | 0/4/0/156 | 4 |
| 07 | 4 | 0/3/9 | 17/34/0/109 | 40 |
| 08 | 4 | 0/0/12 | 0/0/0/160 | 0 |
| 09 | 4 | 0/0/12 | 0/0/5/155 | 0 |
| 10 | 4 | 0/0/12 | 0/0/0/160 | 0 |
| 11 | 4 | 0/0/12 | 0/0/0/160 | 0 |
| 12 | 4 | 0/0/12 | 0/0/0/160 | 0 |
| 13 | 4 | 0/0/12 | 0/0/0/160 | 0 |
| 14 | 4 | 0/0/12 | 0/8/0/152 | 0 |
| 15 | 4 | 0/0/12 | 0/0/0/160 | 0 |
| 16 | 4 | 0/0/12 | 0/7/0/153 | 0 |
| 17 | 4 | 0/0/12 | 0/0/0/160 | 0 |
| 18 | 4 | 0/0/12 | 0/0/0/160 | 0 |
| 19 | 4 | 0/0/12 | 0/0/0/160 | 0 |
| 20 | 4 | 0/0/12 | 0/0/0/160 | 0 |
| 21 | 4 | 0/0/12 | 0/0/0/160 | 0 |

## Audit dashboard validation

The offline dashboard was checked separately in Chromium and WebKit at 1366×768 and 390×844: all 72 test entries, item navigation, issue filters, original-source crops, candidate labels and horizontal-overflow checks passed. This validates the report interface only; it does not certify all source text or production UI behavior. See `checkpoints/dashboard-browser-validation.json`.

## Outstanding work / release blockers

- Complete visual source comparison for 213 passages, 598 groups and 2805 questions still NOT_AUDITED. These are overlapping hierarchical work units, not independent defect counts.
- Resolve five C09 questions and the two adjudicated source ambiguities; independently authenticate edition/attachment identity where required.
- Compare 2836 remaining original answer-key entries. A valid existing key never substitutes for question wording verification.
- Adjudicate all 2,343 recognition/detector candidates, inspect all diagrams/tables/flowcharts and relevant footnotes, validate all source page ranges/crops, and inspect actual rendered content against the source for each unreviewed item.
- In a separately authorized repair task, prioritize unavailable correct options / incorrect input types, missing questions or blanks, missing choices and limits, then wording/paragraph/typography defects. Preserve keys, grading and existing attempts unless separately authorized.

## Artifacts and resume

- [Evidence browser](reading-content-fidelity-v1/index.html): all 72 tests, 216 passages, 613 groups and 2,880 questions; filters, stable item anchors, excerpts and crops.
- [Full report](reading-content-fidelity-v1/report.json), [coverage](reading-content-fidelity-v1/coverage.json), [issue inventory](reading-content-fidelity-v1/issues.csv). CSV includes confirmed findings and clearly labeled unconfirmed candidates.
- [Resume queue](reading-content-fidelity-v1/resume-queue.json), [manual reviews](reading-content-fidelity-v1/manual-reviews.json), [source inventory](reading-content-fidelity-v1/source-inventory.json), [browser observations](reading-content-fidelity-v1/browser-observations.json).
- `checkpoints/recognition-all-psm3.json`: page recognition state; `comparison-*.json`: automated comparison state only; `diffs-*.json`: token differences; `pipeline-reproduction.json`: parser reproductions; `safety.json`: protected-file hashes.

Run from project root with an isolated Python environment containing PyMuPDF, Pillow and rapidfuzz, plus local Tesseract:

```sh
python docs/reading-content-fidelity-v1/scripts/recognize.py --help
python docs/reading-content-fidelity-v1/scripts/source_profile.py
python docs/reading-content-fidelity-v1/scripts/record_visual_review.py
python docs/reading-content-fidelity-v1/scripts/audit.py
python docs/reading-content-fidelity-v1/scripts/build_outputs.py
```

The supplied visual-review script reproduces only the recorded adjudications. It does not create new verification for unreviewed material. Regenerate OCR caches if `/tmp` has been cleared; browser fixtures are generated separately by `export_browser.py` / `browser.mjs`. Read their CLI/code before running because their dependencies and temporary paths are explicit.

Protected-file safety: 365 baseline files checked; zero changed during this audit. Production exam content, keys, API, frontend and user results were not edited by this audit. Existing workspace changes from earlier tasks were preserved. No commit, push or deploy.

**NO-GO remains in effect: confirmed scoring-affecting defects exist and most source comparison remains outstanding. A successful script or browser run is not a fidelity PASS.**
