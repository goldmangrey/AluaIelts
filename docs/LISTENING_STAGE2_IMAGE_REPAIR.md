# ALUA — Stage 2 Listening Image Repair

Дата: 2026-11-06. Только локальные изменения. **25/26 исходных confirmed восстановлены, 1 BLOCKED. Все 21 подозрения просмотрены: 20 CONFIRMED_DAMAGED и восстановлены, 0 FALSE_POSITIVE, 1 UNCERTAIN.** Итого 45 новых canonical assets в 45 Parts / 29 exams. Stage 1 coverage сохранён. Commit/push/deploy, Oracle и DB migrations не выполнялись.

Это самодостаточный handoff реализации. Не повторять исходный аудит 590 изображений и не запускать общий импорт для применения этих исправлений. Оставшиеся два случая описаны ниже; все новые selections уже применены локально.

## Результат и границы

| Проверка | Результат |
|---|---|
| Исходные confirmed | 25 REPAIRED / 1 BLOCKED из 26 |
| Suspected | 21/21 просмотрено: 20 подтверждены, 1 UNCERTAIN |
| Новые canonical crop | 45 (44 PDF regions, 1 native full-page region) |
| Coverage | 72/72 Tests, 288/288 Parts, 568/568 groups |
| Missing rendered states / problematic Parts | 0 / 0 |
| Known duplicate pairs / order inversions / wrong Part | 0 / 0 / 0 |
| Вновь выбранные повреждённые crop | 0 |
| Старые 47 flagged crop в canonical selections | 0 |
| Оставшееся повреждение исходных пикселей в fallback | 1: C014, строка word limit |
| Dataset validator | technical_integrity=true, errors=[] |
| Crop regression tests / Stage 1 metadata tests | 3/3 PASS / 5/5 PASS |
| Chromium | 26/26 Exam/Review mode cases, 13 Parts; 18 открытий новых crop в image dialog; page_errors=[] |

**Это не утверждение о качестве всех изображений dataset.** Проверены именно 47 crop-кейсов и их источники. В 20 дополнительных подтверждениях учитывались как физически срезанные элементы, так и доказанная неполнота контекста: отсутствующие word limits, варианты ответов, подписи и соседние задания с той же canonical страницы. Ни edge detector, ни OCR не использовались как доказательство повреждения или источник новых пикселей.

## Как восстановлено

1. Каждому finding сопоставлены исходный crop и уже подтверждённая Stage 1 полная страница из `qa/assets.json` / `visual-materials.json`. Диапазоны вопросов и `display_order` не изменялись.
2. Локальные `ieltsbooks/Cambridge-IELTS-NN.pdf` совпали по SHA-256 с исходным PDF provenance во всех затронутых книгах. Физический номер PDF-страницы сохранён в recipes. Перед promotion сравнивались старый crop, полный материал и новый результат.
3. 44 результата — рендер проверенного прямоугольника оригинальной PDF-страницы в 300 DPI, затем белое поле 24 px. Никакого OCR, дорисовки, AI или замены Cambridge текста. Это восстановление потерянного контекста из оригинальных пикселей, а не заявление о появлении новых деталей в исходных сканах.
4. C020 (C07 T3 P3) — native crop из чистой полной страницы dataset, без ресайза. В локальном PDF синий watermark перекрывает схему; чистая подготовленная страница предпочтительнее. Crop сохраняет diagram geometry, Q23–25, заголовок и one-word limit. Тест сравнивает исходные пиксели напрямую.
5. Полные оригиналы и старые crop **не изменены и не удалены**. Новые PNG имеют `asset-<SHA-256>` IDs. Полная прежняя canonical страница стала первой `alternative_asset_ids`, повреждённый crop остался доступен для совместимости, но не выбран canonical.
6. Только 29 затронутых exam JSON обновлены: asset allowlist и image bindings. В write-команде есть deep comparison, запрещающий изменения вопросного содержимого вне visual bindings. Остальные 43 exams не переписаны. Старые snapshots могут продолжить показывать прежние полные страницы из собственных immutable metadata/allowlist.

## Блокировки и неопределённость

### C014 — BLOCKED, C07 Test 4 Part 1, Q1–6

Исходный crop `asset-37bab8fdbaa800a16913c7272389c7f862a9ec962066c147faca1ed8731f1a38`. Чистая полная страница содержит повреждённые пиксели в `AND/OR` строки word limit (часть A/D отсутствует); локальный PDF закрывает эту область синим watermark. Копия `~/Downloads/Cambridge-IELTS-07.pdf` проверена отдельно: она побайтно совпадает с `ieltsbooks` (SHA-256 `b0d7be939b192c4ea7601b2315049770b7705542f04ae9b87a19e37daac1c971`), чистого второго оригинала среди этих двух копий нет. Можно обрезать страницу шире, но нельзя достоверно восстановить каждый символ. Кандидат **не добавлен в dataset и не выбран**. Текущий полный fallback сохранён. Это ограничение качества исходного scan, а не новый UI clipping. Для завершения нужен чистый скан этой конкретной страницы, без watermark/дефекта инструкции. Нельзя восстанавливать буквы по догадке.

[Проверенный крупный фрагмент инструкции](listening-visual-audit/stage2/blocked-C014-instruction.png). Exact fallback ID/path находятся в таблице и manifest.

### C028 — UNCERTAIN, C06 Test 3 Part 3, Q25–30

Исходный crop `asset-1940054e57262c151915fc2810d202ec9cbcf855e5c2ed213210368c926de70b`. Текст Q25–30 и word limit видимы, но верхняя инструкция близка к границе, а нижняя линия рамки не сохранена. Конкретная потеря слова не доказана; нормальным полноценным crop он также не объявлен. **Новый asset не создавался**, полный текущий оригинал оставлен canonical. Для закрытия требуется редакционное решение по полноте рамки/верхней границы или более чистый оригинал. Не включать этот старый crop автоматически.

## Implementation map и воспроизводимость

| File | Изменение |
|---|---|
| `backend/scripts/listening_dataset/image_repairs.json` | 45 небольших hash-pinned recipes: finding, exam/Part, range, old/source/new IDs, source PDF hash/page, rectangle, padding, DPI/source kind. Только утверждённые результаты. |
| `backend/scripts/listening_dataset/image_repairs.py` | `render_crop` проверяет источник, использует original pixels и проверяет ожидаемый output hash; `add_repaired_assets` регистрирует их через существующий `Assets`. |
| `backend/scripts/listening_dataset/importer.py` | После чтения исходных изображений вызывает `add_repaired_assets`; до `apply_visual_materials` включает derived IDs соответствующего exam в public allowlist. Ошибка source/hash останавливает импорт вместо возврата старого crop. |
| `backend/scripts/listening_dataset/repair_images.py` | Точечный `--apply` без общего импорта; меняет только нужные exams/metadata. `check` проверяет hashes/decode/dimensions/padding/allowlists/fallbacks/idempotency. |
| `backend/scripts/listening_dataset/test_image_repairs.py` | 3 regressions: approved selections + blockers, native pixel identity, deterministic PDF rerender + rejection of wrong PDF. |
| `web/src/features/listening/visual-materials.json` | 45 canonical substitutions с сохранением ranges/order и полных альтернатив. |
| `web/scripts/audit-listening-part-coverage.mjs` | `--stage2` добавляет пять mandatory Parts к существующим browser cases и включает настоящую `ListeningPage` для Exam; disposable mocks только на auth/API boundary. |

`visibleSourceMaterial()`, `sourceMaterial()`, `WorkspaceQuestions`, layout/CSS, navigation и остальные runtime UI-файлы в Stage 2 **не менялись**. Все нужные изображения Part остаются слева независимо от active question; questions/inputs справа. Смена фокуса сохраняет IDs и manual source scroll. Чтение metadata через прежний canonical механизм.

Воспроизводимость: все утверждённые PNG сначала созданы кандидатами, затем **повторно отрендерены через тот же helper при применении**; каждый повтор совпал с pinned ID. Importer вызывает этот helper. Дополнительно тест повторяет PDF C003 и native C020. Полный импорт 72 экзаменов не запускался, поскольку не требовался; wiring и actual asset registration проверены при точечном применении. Общий importer validation и legacy metadata tests проходят.

Команды из корня (Pillow/PyMuPDF/jsonschema — существующие pinned requirements; в сессии использован временный `/tmp/alua-stage2-venv`):

```sh
# Проверки без записи контента:
/tmp/alua-stage2-venv/bin/python backend/scripts/listening_dataset/repair_images.py
/tmp/alua-stage2-venv/bin/python -m unittest discover -s backend/scripts/listening_dataset -p 'test_image_repairs.py' -v
/tmp/alua-stage2-venv/bin/python -m unittest discover -s backend/scripts/listening_dataset -p 'test_visual_materials.py' -v
/tmp/alua-stage2-venv/bin/python backend/scripts/listening_dataset/validator.py
node web/scripts/audit-listening-part-coverage.mjs --browser --stage2 --assert-complete
# Из web/:
pnpm exec eslint scripts/audit-listening-part-coverage.mjs --max-warnings=0
pnpm exec tsc --noEmit
```

Уже применённая команда (не запускать повторно без необходимости):

```sh
/tmp/alua-stage2-venv/bin/python backend/scripts/listening_dataset/repair_images.py --apply --pdf-root ieltsbooks
```

Нужны PyMuPDF 1.26.7 и Pillow 13.0.0 из `requirements.txt`; иные renderer bytes должны провалить pinned hash и потребовать просмотра. После правок importer/recipes/checks нужно обновить `manifest.generator_sha256`; это checksum исходников, не DB migration.

## Browser QA: доказательство и ограничения

Chromium 1440×900, локальный disposable Next. Используются **настоящая `ListeningPage` / `Workspace` / `ListeningDraft` / `WorkspaceNavigator` в Exam и настоящая `ListeningReview`**, текущий dataset/resolver/Asset/CSS. Auth и attempt/results/sync API — synthetic in-memory fixture на localhost; реальные пользовательские records не читались и не менялись. Media/AI не вызываются, playback не является предметом PASS. Проверены загрузка каждого изображения, canonical IDs/order, десять одновременно смонтированных вопросов, focus переход между группами, сохранение изображений, независимый scroll и открытие/закрытие новых изображений.

Все шесть обязательных примеров пройдены в Exam и Review: C05 T1 P1 Dreamtime, C05 T4 P2, C11 T3 P3, C18 T3 P1, C19 T1 P2, C21 T2 P3. Также повторены Stage 1 cases/controls C04 T1 P1, C09 T2 P2, C14 T2 P2, C18 T2 P4, C19 T3 P1, C14 T1 P1 и C04 T2 P2. Визуально просмотрены source/new comparisons всех approved случаев и screenshots обязательных браузерных примеров. Большие изображения в enlarge dialog прокручиваются; сам screenshot показывает viewport, не весь файл.

Это **не production/authenticated backend smoke**. WebKit, mobile, audio/AI/Play/Loop, реальные autosave/results и визуальное качество остальных 590 исходных изображений не проверялись. Эти подсистемы не изменены. Полный end-to-end reimport не запускался.

## Артефакты и изменённые файлы

- [Contact sheet всех 47 случаев](listening-visual-audit/stage2/index.html): Before / полный fallback / After, PDF preview, ranges/status/canonical IDs. Все ссылки указывают на реальные assets.
- [Repair manifest](listening-visual-audit/stage2/repair-manifest.json): exact IDs, пути, решения и evidence для всех 47.
- [Dataset validation](listening-visual-audit/stage2/dataset-validation.json), [browser evidence](listening-visual-audit/stage2/browser-evidence.json), screenshots `regression-*` и `repaired-*` в Stage 2.
- Обновлены `stage1/part-coverage.json` и пустой текущий `stage1/regression-findings.csv`; исходные исторические данные Stage 1 сохранены.
- Изменены 29 `backend/app/content/listening_v1/exams/*.json`, `qa/assets.json`, `qa/visual_materials.json`, `manifest.json`, registry и перечисленные выше scripts/tests. Добавлены 45 `assets/public/<hash>.png` (около 37.6 MB), docs и thumbnails. Полный список ниже.
- SHA-256 baseline до Stage 2: **0 изменений старых image files, 0 изменений runtime Listening UI, 0 изменений keys**; только перечисленные metadata/importer/exams. Audio/transcripts, Reading, grading и AI не затрагивались.

## Все 47 решений

IDs в manifest полные. Ссылки в таблице ведут непосредственно к оригинальным/новым файлам; abbreviated labels нужны только для компактности.

| Finding | Cambridge / Test / Part | Range | Decision | Old asset | Source/fallback | New canonical (или сохранённый fallback) |
|---|---|---|---|---|---|---|
| C001 | cambridge-05-test-04 P1 | Q1–10 | REPAIRED | [asset-4002fbffc81c…](../backend/app/content/listening_v1/assets/public/4002fbffc81cbc805614bcb288b918188e11f6fa69bc16fe7b4bf0677345117c.png) | [asset-a7e1ad584d6e…](../backend/app/content/listening_v1/assets/public/a7e1ad584d6ef7f990b9a8860cd974ff07ffb28a4909a0b68865844d3718e2f1.jpg) | [asset-ccded4cd9da9…](../backend/app/content/listening_v1/assets/public/ccded4cd9da9b7518a7dfdf6b08456195262ef3903db99fa483c5261b3e006e3.png) |
| C002 | cambridge-11-test-03 P3 | Q21–26 | REPAIRED | [asset-72599a58ccc7…](../backend/app/content/listening_v1/assets/public/72599a58ccc716931fc93ea6f72889c8b878fab221c39fffe89bfbebfff22f47.jpg) | [asset-4cf0b32b3eca…](../backend/app/content/listening_v1/assets/public/4cf0b32b3eca0553fd6d0b43bd9eb2598fe4b8e4e154a086cc8580cfdd788901.jpg) | [asset-4ddd27548b85…](../backend/app/content/listening_v1/assets/public/4ddd27548b856af0949a8e238054848ca3c9134e8fb7ba30a59dc7b1fb05178d.png) |
| C003 | cambridge-21-test-02 P3 | Q27–30 | REPAIRED | [asset-874e297b9de3…](../backend/app/content/listening_v1/assets/public/874e297b9de36865ad77bda8d0cd34c11ee6f07d9c31855405b5fef7ddb6690f.png) | [asset-74274f69f771…](../backend/app/content/listening_v1/assets/public/74274f69f771eaf1fa66a58faf2b6e0d476f9b75dfa2ed96fba0e75bd2e6bbca.png) | [asset-2deb0b95816a…](../backend/app/content/listening_v1/assets/public/2deb0b95816aec732aafd4bd159c424d971e84f68779372cc4a864e3551c4034.png) |
| C004 | cambridge-05-test-02 P4 | Q31–40 | REPAIRED | [asset-7b451831d806…](../backend/app/content/listening_v1/assets/public/7b451831d806d2d63544db7fd0d057de64ae048edaa5cf32c01946ad0cdb4ee0.png) | [asset-d2a15aa9a375…](../backend/app/content/listening_v1/assets/public/d2a15aa9a3753b49133f068624c2fbf58699494bb6394bed4a407aa04b4fc748.jpg) | [asset-d22b712292c9…](../backend/app/content/listening_v1/assets/public/d22b712292c974736d9c5c011373a051795937d10646aedfe470f2cb356299b5.png) |
| C005 | cambridge-09-test-02 P2 | Q16–20 | REPAIRED | [asset-1e091ce4fe69…](../backend/app/content/listening_v1/assets/public/1e091ce4fe692035a8a5ba9e15a51d2223a33dfd0b4a7569fd6e429119a03c85.png) | [asset-c807b06d0f8e…](../backend/app/content/listening_v1/assets/public/c807b06d0f8e77a0799e466a8b72b9b624a990e702f61bd3868321fd5d7f2156.jpg) | [asset-f1591ff07203…](../backend/app/content/listening_v1/assets/public/f1591ff072031895a45294f72ac60b932d550dc43440abb0ec3be7d0e7dcd578.png) |
| C006 | cambridge-06-test-01 P1 | Q5–10 | REPAIRED | [asset-068423ff9de3…](../backend/app/content/listening_v1/assets/public/068423ff9de3e5b4fecf18d136c02ea752d65589cf78655664fa6c6988e55fa4.jpg) | [asset-151efc63b36d…](../backend/app/content/listening_v1/assets/public/151efc63b36d2e2ddc5d0317ed50c5dd81841931e8b51957686a1469418a0371.jpg) | [asset-d5a182c1d98b…](../backend/app/content/listening_v1/assets/public/d5a182c1d98bded6e0f87a669e455c990d4a8a1580ce417c874bdbd6a85c38f6.png) |
| C007 | cambridge-08-test-03 P1 | Q4–8 | REPAIRED | [asset-4424be7f7f75…](../backend/app/content/listening_v1/assets/public/4424be7f7f752dbf4abc6ac5fc88b3fd57c181b0d874edbe8bb6ca06f520c7bc.png) | [asset-c1a0f801298f…](../backend/app/content/listening_v1/assets/public/c1a0f801298f2422058984c18336096fa41648b81aa927812fb881bb203d6015.png) | [asset-404b99984d62…](../backend/app/content/listening_v1/assets/public/404b99984d628d6a8d053309526b14ce107b5c12bd5624165853f7a489aaa469.png) |
| C008 | cambridge-07-test-03 P1 | Q6–10 | REPAIRED | [asset-b12b2c159811…](../backend/app/content/listening_v1/assets/public/b12b2c159811a045b01a76f3e402661516e6d7e9ff585e9a5cc07c7997ab4620.png) | [asset-5b59329c7a11…](../backend/app/content/listening_v1/assets/public/5b59329c7a11c0e140f1bca31a920b7c8e884ac5d12c72bdaa0c94dee3d59e74.png) | [asset-7e41e8f31827…](../backend/app/content/listening_v1/assets/public/7e41e8f318270fedd36f36bf34a467f96a0b800cdc648426c6f4d784f86e1752.png) |
| C009 | cambridge-14-test-02 P2 | Q16–20 | REPAIRED | [asset-9134a8d2cec1…](../backend/app/content/listening_v1/assets/public/9134a8d2cec1aaf9fc33c1382bbe643511bdd5163c6bd24a9ad4728f037ca527.png) | [asset-104795909c64…](../backend/app/content/listening_v1/assets/public/104795909c64a6f4907769817c8623a06ab48e7effc3d7e1c7bdf53f1a3d6455.png) | [asset-b573f938f791…](../backend/app/content/listening_v1/assets/public/b573f938f7915403ef9fb529d9f966902aa6bccec26100a06a420fe20a37b49d.png) |
| C010 | cambridge-18-test-02 P4 | Q31–40 | REPAIRED | [asset-8a50969c622f…](../backend/app/content/listening_v1/assets/public/8a50969c622f70f7674980f76f6a15427c44fc5dae9954e21bcbcef70ef27d4e.png) | [asset-785b97b4897f…](../backend/app/content/listening_v1/assets/public/785b97b4897fbc821190f0e55a2220f8f3304499f3a23f242db64430e9981a0c.png) | [asset-08b7eb734195…](../backend/app/content/listening_v1/assets/public/08b7eb734195ab6c603fc5141c0cfb4f1d41f7f143488758cfdb32a4a0024f49.png) |
| C011 | cambridge-07-test-04 P2 | Q15–20 | REPAIRED | [asset-f6b3fa610ee8…](../backend/app/content/listening_v1/assets/public/f6b3fa610ee86f405745a579cc7f905d073581cf46cd3bde11484f2f944e89d5.png) | [asset-a7c67992a6b3…](../backend/app/content/listening_v1/assets/public/a7c67992a6b3326150d18cea0d9d508d4740d67ced286623e398bdb260d70a7b.png) | [asset-76e9b8e7fe24…](../backend/app/content/listening_v1/assets/public/76e9b8e7fe24767bef7d47cea74b32b3ad4965465a66818c8afa66c90c7c4d9f.png) |
| C012 | cambridge-11-test-04 P2 | Q17–20 | REPAIRED | [asset-f57229759b63…](../backend/app/content/listening_v1/assets/public/f57229759b6334de8119bf6c088ef2a939b468bba5d754fced1435ecb1811eb4.jpg) | [asset-77de1e8ffb04…](../backend/app/content/listening_v1/assets/public/77de1e8ffb04bd0e4aea475e10f19ac90cd9fa6e40bc7b8972300a42a524e8c2.jpg) | [asset-1692efed4549…](../backend/app/content/listening_v1/assets/public/1692efed454965e33b5e446e5ef5946338fac2117b5f8c0db66339d8ed965a4a.png) |
| C013 | cambridge-12-test-08 P3 | Q21–24 | REPAIRED | [asset-9f8b4b336025…](../backend/app/content/listening_v1/assets/public/9f8b4b336025499ae16dcc701fa48d51a4113a6779b938ad3e05ee5c810c5586.png) | [asset-fb8307db07b8…](../backend/app/content/listening_v1/assets/public/fb8307db07b8d1dbd5a5a7ce629dceecfb525f90d6aa30003d03c2a5b2ca9df2.png) | [asset-ab565d61bccd…](../backend/app/content/listening_v1/assets/public/ab565d61bccdcd94c6825878e177096aabf8c0092a54738c8b19e8b5980642b5.png) |
| C014 | cambridge-07-test-04 P1 | Q1–6 | BLOCKED | [asset-37bab8fdbaa8…](../backend/app/content/listening_v1/assets/public/37bab8fdbaa800a16913c7272389c7f862a9ec962066c147faca1ed8731f1a38.png) | [asset-2d699765d752…](../backend/app/content/listening_v1/assets/public/2d699765d75235aa6ec60a141a5011ed1349bffb7c57443faf06b55459a2f7ec.png) | [asset-2d699765d752…](../backend/app/content/listening_v1/assets/public/2d699765d75235aa6ec60a141a5011ed1349bffb7c57443faf06b55459a2f7ec.png) |
| C015 | cambridge-07-test-02 P1 | Q1–10 | REPAIRED | [asset-0363281b0812…](../backend/app/content/listening_v1/assets/public/0363281b0812c8fcffb714cd47656fcc05290105aca5cfa98923425c40224603.png) | [asset-892dc7776bcb…](../backend/app/content/listening_v1/assets/public/892dc7776bcbc3bcf8b44c140309e0831253ddab5a991b774c401fc26ed7ab49.png) | [asset-ae1755a4b17d…](../backend/app/content/listening_v1/assets/public/ae1755a4b17d84cdf8288221bd4339286a4f4393adc040822493eabe30e8a6e2.png) |
| C016 | cambridge-07-test-01 P1 | Q6–10 | REPAIRED | [asset-bb349f7051ff…](../backend/app/content/listening_v1/assets/public/bb349f7051ff6e02656b82797260bd39dbb602e4f092d73282d576c5dc035e5c.png) | [asset-717877a86b42…](../backend/app/content/listening_v1/assets/public/717877a86b42c5d736524fdbde6cc9a14f6100235b5f7223f436d6987cade147.png) | [asset-8af891bcf535…](../backend/app/content/listening_v1/assets/public/8af891bcf53579e6d9c460c7dd643b771d5f66f552a47351189bfae7cba377f9.png) |
| C017 | cambridge-18-test-03 P1 | Q1–10 | REPAIRED | [asset-c48791329bb8…](../backend/app/content/listening_v1/assets/public/c48791329bb886644a402f27311fd1ce7292e7fc97bf6c35cc1b44b4760f1127.png) | [asset-97d2814c4023…](../backend/app/content/listening_v1/assets/public/97d2814c4023ecdc5b100b54c49c1a445137b32caff617ad01b49a67f9d82373.png) | [asset-c478be2700f4…](../backend/app/content/listening_v1/assets/public/c478be2700f41828eb5cac473d8a26ae5711c09cf6be82a3f4fcf4272e498dad.png) |
| C018 | cambridge-05-test-03 P3 | Q21–30 | REPAIRED | [asset-3adc62150707…](../backend/app/content/listening_v1/assets/public/3adc6215070707f80bbce2a8387e495cfb910cde4ec090cfeff7ba34d886bac1.png) | [asset-5e32f5d1dc2c…](../backend/app/content/listening_v1/assets/public/5e32f5d1dc2c367f36a3de70d05f34a79f4c1aa6939781e11a91e1505f7b9fc7.jpg) | [asset-a788199c75cf…](../backend/app/content/listening_v1/assets/public/a788199c75cf3b11026a79f05b4e37285550a7218b77eae70698cd165c121fa8.png) |
| C019 | cambridge-18-test-04 P1 | Q1–10 | REPAIRED | [asset-58dbce6b29b3…](../backend/app/content/listening_v1/assets/public/58dbce6b29b3208e0d201f7123a158e7861b519596554605982cf7b26e0df93d.png) | [asset-eb7f69cc444a…](../backend/app/content/listening_v1/assets/public/eb7f69cc444afab1c690db44804f116f3d450bd7a07c70bebffe64f1a5464cca.png) | [asset-60e9790ea08e…](../backend/app/content/listening_v1/assets/public/60e9790ea08e11398de5db1ae1bc4a357648518f84973cef35bf5e95801e9d8f.png) |
| C020 | cambridge-07-test-03 P3 | Q23–25 | REPAIRED | [asset-db7e8a9c4dd4…](../backend/app/content/listening_v1/assets/public/db7e8a9c4dd46f4dff41ce78146ca10f7c644ec66899a312dba8b8ae2c5490a3.png) | [asset-9b12f7d7e2bb…](../backend/app/content/listening_v1/assets/public/9b12f7d7e2bb1dec0eb999c79fc6dfd05645eb67f665d07a4d523132699fb707.png) | [asset-8333edd6058b…](../backend/app/content/listening_v1/assets/public/8333edd6058b159fb2fc110827c6f8ab850d494be506ba89a9a13ee1fa267ae3.png) |
| C021 | cambridge-06-test-04 P3 | Q21–27 | REPAIRED | [asset-f9e7ca07f5e1…](../backend/app/content/listening_v1/assets/public/f9e7ca07f5e1d38782b3ab4cae1a23eae834574fdb80130b90926321bf6be429.jpg) | [asset-b723ab26cf04…](../backend/app/content/listening_v1/assets/public/b723ab26cf04d9dc32c6db53c62c568294a8c1681a27f0eb667c0f2563e01c9a.jpg) | [asset-de928e2fdaa4…](../backend/app/content/listening_v1/assets/public/de928e2fdaa4296e3f942b9e39ba905472a4168c421bbc7323a9885ad460d855.png) |
| C022 | cambridge-12-test-08 P2 | Q15–20 | REPAIRED | [asset-72f9a506e959…](../backend/app/content/listening_v1/assets/public/72f9a506e9592069e013a5e9457ee697f840224fa6f1c9568754cfed66e493e8.png) | [asset-ef0a1e3ad794…](../backend/app/content/listening_v1/assets/public/ef0a1e3ad794df809bcdfeafd1e03411e9fb0aea2545cdd9a7308655c42cc144.png) | [asset-ca3c3016c33c…](../backend/app/content/listening_v1/assets/public/ca3c3016c33c5cf48fd161b1358c4038d141b162204baff30d40923587bfb61f.png) |
| C023 | cambridge-05-test-01 P4 | Q31–40 | REPAIRED | [asset-37ce358e0ef8…](../backend/app/content/listening_v1/assets/public/37ce358e0ef8517946a72e80bac80ed89bd9fc500f20fdeb7aa31276d259a3ba.png) | [asset-1032e82bda64…](../backend/app/content/listening_v1/assets/public/1032e82bda643fad6b2ce5b1120cbbec309299c570b1317e800cf8f19dfb4f5f.jpg) | [asset-df79c1253a1e…](../backend/app/content/listening_v1/assets/public/df79c1253a1e7d793503f16d06aa6ec1661dc551a616e8f99241ba12d10fa390.png) |
| C024 | cambridge-06-test-01 P2 | Q17–20 | REPAIRED | [asset-88fb8c0c0b29…](../backend/app/content/listening_v1/assets/public/88fb8c0c0b2903a4bc6af16f8aac1bcb60c12bb1dea075be5462b294e049954f.jpg) | [asset-37fb8b707fd1…](../backend/app/content/listening_v1/assets/public/37fb8b707fd13756db402eb492cdd5df9304a713a49ed705f5f7ef4722cf58ad.jpg) | [asset-5b23e22fc32f…](../backend/app/content/listening_v1/assets/public/5b23e22fc32f137eff3beb533058955cff490fcdb30f466f9b1c5dc220ef8801.png) |
| C025 | cambridge-07-test-02 P2 | Q11–12 | REPAIRED | [asset-78b19ed53628…](../backend/app/content/listening_v1/assets/public/78b19ed53628e3414a1eda16989fc807ee2679af3f9cf2e7b3b37bb6b972f527.png) | [asset-91461cc55d6b…](../backend/app/content/listening_v1/assets/public/91461cc55d6b2e1625c02e4e508a0652df376011bb67c711b7059dd27f5f3e21.png) | [asset-26623107ad08…](../backend/app/content/listening_v1/assets/public/26623107ad08a78b514495da9dd4fefd5d314c6c4262fe3583de3af5c6fb890d.png) |
| C026 | cambridge-18-test-01 P4 | Q31–40 | REPAIRED | [asset-51c19d43da36…](../backend/app/content/listening_v1/assets/public/51c19d43da36195b2be4f2bfb860832f07d963db83b2f9b34a8123aae9c6e4eb.png) | [asset-bf2730943adb…](../backend/app/content/listening_v1/assets/public/bf2730943adb17517feed7f50d77e474b007530461074751bff59b8bc373234c.png) | [asset-aee273fc39fd…](../backend/app/content/listening_v1/assets/public/aee273fc39fd41a2c8ed3b3b0362efd3a2656401b2285acfbd2f0474a0a62dac.png) |
| C027 | cambridge-18-test-04 P4 | Q31–40 | REPAIRED | [asset-c7dec87e12c6…](../backend/app/content/listening_v1/assets/public/c7dec87e12c61cdacb392c4f187e69ae40a13b8df6596b674a1630fe3595eec9.png) | [asset-aa8d64fc0631…](../backend/app/content/listening_v1/assets/public/aa8d64fc06318801eaf3df68806a65f1b6c8cc5ecb34391dfd9d1979f56b526d.png) | [asset-cdd0fe111f45…](../backend/app/content/listening_v1/assets/public/cdd0fe111f450b97946d55a5cc4e4a2e060c8066cefaced6c217cc8e5daf42e9.png) |
| C028 | cambridge-06-test-03 P3 | Q25–30 | UNCERTAIN | [asset-1940054e5726…](../backend/app/content/listening_v1/assets/public/1940054e57262c151915fc2810d202ec9cbcf855e5c2ed213210368c926de70b.jpg) | [asset-a3d806a65c12…](../backend/app/content/listening_v1/assets/public/a3d806a65c12507c335671bba162d72ddfdd1fd91e0e8b0447cef5dcd1979027.jpg) | [asset-a3d806a65c12…](../backend/app/content/listening_v1/assets/public/a3d806a65c12507c335671bba162d72ddfdd1fd91e0e8b0447cef5dcd1979027.jpg) |
| C029 | cambridge-05-test-01 P1 | Q1–6 | REPAIRED | [asset-0fc00612b8aa…](../backend/app/content/listening_v1/assets/public/0fc00612b8aa4c287947961216f1f300c8e542226d6f56329de341c4a0e9daba.png) | [asset-0d7083daf984…](../backend/app/content/listening_v1/assets/public/0d7083daf984f67cc1c9a5c193ee897d7728c4320b6e87138280551eaff169c8.jpg) | [asset-731af3aa2a0e…](../backend/app/content/listening_v1/assets/public/731af3aa2a0eafeca2455a306d556f0efc0db922d32f680e14c2be73652285f6.png) |
| C030 | cambridge-12-test-07 P2 | Q18–20 | REPAIRED | [asset-0972e19261f1…](../backend/app/content/listening_v1/assets/public/0972e19261f1f6da196095e18843aaa95e1f0e247549992ced23fa46a3b9cffd.png) | [asset-361d57e11c87…](../backend/app/content/listening_v1/assets/public/361d57e11c8770ddb8ab6468f78048dd47cb01886240a6cf6ce6040562ce948f.png) | [asset-10b9563cc907…](../backend/app/content/listening_v1/assets/public/10b9563cc907e3e3858adb6a9d09432dfa808c05876aec88a4df6d13c20f1c4e.png) |
| C031 | cambridge-05-test-03 P4 | Q36–40 | REPAIRED | [asset-20005e8a818b…](../backend/app/content/listening_v1/assets/public/20005e8a818b201ac702962fe851c7554719220b80957a08edd4da8cf75cf4b0.png) | [asset-c78cfcc68b5e…](../backend/app/content/listening_v1/assets/public/c78cfcc68b5e42eca2cfd2f88496a16dec48d99b1eab27611ac81d9ac0f6e5a6.jpg) | [asset-2b46b4536e64…](../backend/app/content/listening_v1/assets/public/2b46b4536e64550cdf3155b84aafe4c4c99e3478da4bb374efc013cc776e6c71.png) |
| C032 | cambridge-12-test-06 P3 | Q26–30 | REPAIRED | [asset-b2ae5f0a6c69…](../backend/app/content/listening_v1/assets/public/b2ae5f0a6c698c4d9fdfb9909fe2f54a6cc76fbab56d9515dd332f0fd8b554a9.png) | [asset-ab4043b2394d…](../backend/app/content/listening_v1/assets/public/ab4043b2394de70fab8378271cb9a1450e825e10719c76f012ff646a38f86fe6.png) | [asset-cab0a98b55f6…](../backend/app/content/listening_v1/assets/public/cab0a98b55f627436bc9a7e337bd76aac8398f7a65c33fbcdf4f158f90e49e06.png) |
| C033 | cambridge-06-test-03 P2 | Q14–20 | REPAIRED | [asset-48c750ef1f98…](../backend/app/content/listening_v1/assets/public/48c750ef1f981db16c6f8daead8556be5b72e3a1eed102f3ec560640fa149137.jpg) | [asset-466e2e0c2e5b…](../backend/app/content/listening_v1/assets/public/466e2e0c2e5b3874455fe5fcf48f05dc44dd3f1eb6c688fba080caf9fa093d17.jpg) | [asset-66de2c0cd082…](../backend/app/content/listening_v1/assets/public/66de2c0cd082352b16db66bfe4a931dbd8a3c939c8262dc0563875c83069e7e7.png) |
| C034 | cambridge-05-test-03 P1 | Q1–10 | REPAIRED | [asset-abeeb8f2859a…](../backend/app/content/listening_v1/assets/public/abeeb8f2859a15f534f6c43649e98be6fd338ae8dc9706196d16729c0576700e.png) | [asset-c5aa08b18f41…](../backend/app/content/listening_v1/assets/public/c5aa08b18f413170684b954b19a4163931f02a82a906d425e1f7d1ecbeb52a38.jpg) | [asset-70a5758da2d7…](../backend/app/content/listening_v1/assets/public/70a5758da2d73432c80f73285127ea76f54255a531fd2c807212d5f6a23b3035.png) |
| C035 | cambridge-14-test-04 P4 | Q31–40 | REPAIRED | [asset-c0c567463529…](../backend/app/content/listening_v1/assets/public/c0c5674635297c65275f8ae708a49fac1d4bb6db7886a4850f7590ba67b7c3ff.png) | [asset-22e9ab4e40be…](../backend/app/content/listening_v1/assets/public/22e9ab4e40bee440fd21d453acf2a5bc1cf11af86740fc928753163de9e63ae5.png) | [asset-b82be970064b…](../backend/app/content/listening_v1/assets/public/b82be970064bf57e19b45bf2d68b5e1312ca8a86322f9b43316a7a5efb29ef4c.png) |
| C036 | cambridge-19-test-01 P2 | Q16–20 | REPAIRED | [asset-58b5984e6888…](../backend/app/content/listening_v1/assets/public/58b5984e68886afd388088a3d6f34ef06bae26b1f8d47925f4d9abd5818b4e5f.png) | [asset-82649ba5ba47…](../backend/app/content/listening_v1/assets/public/82649ba5ba479dac088aae18bcd700d7af5a19a373edcfcf168431e2f550bca5.jpg) | [asset-285bb6e3084d…](../backend/app/content/listening_v1/assets/public/285bb6e3084d9f82c4a5c1288f8a0f0cc564d4478a664e08b78658c9c40f0bd6.png) |
| C037 | cambridge-05-test-02 P1 | Q1–10 | REPAIRED | [asset-b9195c6cf1c8…](../backend/app/content/listening_v1/assets/public/b9195c6cf1c8fd4c9706461e7698ac10491768a2b7dc9d39bc060c27eaddb34a.png) | [asset-0128cad01bee…](../backend/app/content/listening_v1/assets/public/0128cad01bee1e04f1ebcf3c7c5cc76e662994aede8d6431b5a013144794fa31.jpg) | [asset-930ddd3ced17…](../backend/app/content/listening_v1/assets/public/930ddd3ced17a04f031a27c383ede9209545468349faff5e2cc9ebb2e0f777de.png) |
| C038 | cambridge-06-test-03 P1 | Q1–10 | REPAIRED | [asset-8e61242c8c5c…](../backend/app/content/listening_v1/assets/public/8e61242c8c5c2490327fa8bd2c2d72c7b1e7a91bb5a80f38bb142323cd8fc1c6.jpg) | [asset-149d9ba1a136…](../backend/app/content/listening_v1/assets/public/149d9ba1a13604a02a9a7ecf979aa224a4b6028140e79f0626e04579561e640d.jpg) | [asset-05032eee328b…](../backend/app/content/listening_v1/assets/public/05032eee328b18c383363931af1543199a3325c9dfb166be79f2e978202866d1.png) |
| C039 | cambridge-19-test-01 P4 | Q31–40 | REPAIRED | [asset-42a67736a48f…](../backend/app/content/listening_v1/assets/public/42a67736a48f1980c295a7eca33705289207b6ea8c10d7f991582b4461dbf36f.png) | [asset-b47d4e1ee524…](../backend/app/content/listening_v1/assets/public/b47d4e1ee5240328e099372ce67ed003d38d1727a4103430b07cf8c1ee14179f.jpg) | [asset-4bf290298712…](../backend/app/content/listening_v1/assets/public/4bf290298712e284a6050a2e0a8580e07752ed77d7871f8fe61776fdfc1ad4e5.png) |
| C040 | cambridge-12-test-07 P3 | Q21–26 | REPAIRED | [asset-fd8c05167adb…](../backend/app/content/listening_v1/assets/public/fd8c05167adba51b9b5ecdd9b5824fd2b674818c3f0d2f332bc7b3c6d87da10b.png) | [asset-976788245acd…](../backend/app/content/listening_v1/assets/public/976788245acd899feb953dd7b78c462a19428da73158c73e598488c1381830a0.png) | [asset-934cec92461e…](../backend/app/content/listening_v1/assets/public/934cec92461ebd5ae3c528ac76d3e96b7a1d3b85bd87f3fcc53c8eb6eb3f6de7.png) |
| C041 | cambridge-14-test-01 P4 | Q31–40 | REPAIRED | [asset-37cc12f86e85…](../backend/app/content/listening_v1/assets/public/37cc12f86e858bc9cdc27c3b7a7c2dcc1424a3ede26b324cb960aa2b63fffcb5.png) | [asset-f43449798fd7…](../backend/app/content/listening_v1/assets/public/f43449798fd7ff37e7ea8255ea612284af75d629d289c943d92929de48f79803.png) | [asset-f3098101a6b9…](../backend/app/content/listening_v1/assets/public/f3098101a6b9c3f21a1129f33b3763601a1fe517017617f65c1e510d3d6d77d0.png) |
| C042 | cambridge-18-test-02 P2 | Q15–20 | REPAIRED | [asset-673730aec49f…](../backend/app/content/listening_v1/assets/public/673730aec49fe2c284c2f0042a5dd4cf8cd3b78a86a20f9a2fa310df87a36780.png) | [asset-59b49f2c5c25…](../backend/app/content/listening_v1/assets/public/59b49f2c5c251250da7bcd6e14851137e5056d63fb06510281137492fe9e68c3.png) | [asset-f64342d5196c…](../backend/app/content/listening_v1/assets/public/f64342d5196c36cdcbbdd403a928527cff20a0e82c59768c9082b5dff3b1ad60.png) |
| C043 | cambridge-05-test-04 P3 | Q21–27 | REPAIRED | [asset-304512a63095…](../backend/app/content/listening_v1/assets/public/304512a63095175dcf3358cf5459387917d45b45825e86aa79d81e0855fc514e.png) | [asset-d8d95abf2072…](../backend/app/content/listening_v1/assets/public/d8d95abf2072e5b22871e6e2349b8abf34e786cb3f720a87e7969842b037c4ce.jpg) | [asset-02d9dd2b1ed3…](../backend/app/content/listening_v1/assets/public/02d9dd2b1ed319b0c8f1725649f547f2d77830f2c80434fade89f6fbf85ecc84.png) |
| C044 | cambridge-11-test-01 P2 | Q15–20 | REPAIRED | [asset-7692e21a7145…](../backend/app/content/listening_v1/assets/public/7692e21a714575a7064a42db592ee6db8ce76c15eb5d6adb28b03b2631f7871d.jpg) | [asset-9d9e46ef41eb…](../backend/app/content/listening_v1/assets/public/9d9e46ef41ebaa602b8b32e54a65a4a2e07ed9a7da879c40e6fcdc2aedab888a.jpg) | [asset-ea1e90ab2d8b…](../backend/app/content/listening_v1/assets/public/ea1e90ab2d8bc567fe57c372d3803a6f3ce0804e0f4453bcdd410107ae500ca5.png) |
| C045 | cambridge-05-test-04 P2 | Q11–17 | REPAIRED | [asset-539e03fed77f…](../backend/app/content/listening_v1/assets/public/539e03fed77f9000e171927b9c2a189bcd2c8ffe3a1369cdcafdb2087523b88f.png) | [asset-836ead9b1ae5…](../backend/app/content/listening_v1/assets/public/836ead9b1ae567c09511b557cd526a4a45539140fb88c722996a3a82da2b1437.jpg) | [asset-6e57cb913691…](../backend/app/content/listening_v1/assets/public/6e57cb9136916a9f512217cef01c2429c89d754cd130b159ccdbfc263b5032a2.png) |
| C046 | cambridge-11-test-02 P2 | Q17–20 | REPAIRED | [asset-09c3cccc820c…](../backend/app/content/listening_v1/assets/public/09c3cccc820cfceb09405b25d771d08f72415b3bd8809a630871e0581b96ac82.jpg) | [asset-0fb33145e891…](../backend/app/content/listening_v1/assets/public/0fb33145e8919e798ae1dfcd515f726db0309ae3972d95745710878b0cebdc47.jpg) | [asset-3b26db6ebef1…](../backend/app/content/listening_v1/assets/public/3b26db6ebef18af8da08d5032f5fb726411cc06077ea68a4b6dd91b05b8d3317.png) |
| C047 | cambridge-14-test-01 P2 | Q11–14 | REPAIRED | [asset-0b961e03b90d…](../backend/app/content/listening_v1/assets/public/0b961e03b90d90b7626aa37b3e4fa8a230bbe9ddbb9dcf63c607df1bc26bedd3.png) | [asset-0c1b7dd10c41…](../backend/app/content/listening_v1/assets/public/0c1b7dd10c41788f338bb76850fbad3bfb6babf70fd553d0fdd7ab6670e52d0a.png) | [asset-ff3406bb9005…](../backend/app/content/listening_v1/assets/public/ff3406bb9005ce6ead351795e6907cb5c2bcd77431acccab132a1e59ed3a3a5c.png) |

## Новые PNG (content hashes)

- `C001` → `assets/public/ccded4cd9da9b7518a7dfdf6b08456195262ef3903db99fa483c5261b3e006e3.png`
- `C002` → `assets/public/4ddd27548b856af0949a8e238054848ca3c9134e8fb7ba30a59dc7b1fb05178d.png`
- `C003` → `assets/public/2deb0b95816aec732aafd4bd159c424d971e84f68779372cc4a864e3551c4034.png`
- `C004` → `assets/public/d22b712292c974736d9c5c011373a051795937d10646aedfe470f2cb356299b5.png`
- `C005` → `assets/public/f1591ff072031895a45294f72ac60b932d550dc43440abb0ec3be7d0e7dcd578.png`
- `C006` → `assets/public/d5a182c1d98bded6e0f87a669e455c990d4a8a1580ce417c874bdbd6a85c38f6.png`
- `C007` → `assets/public/404b99984d628d6a8d053309526b14ce107b5c12bd5624165853f7a489aaa469.png`
- `C008` → `assets/public/7e41e8f318270fedd36f36bf34a467f96a0b800cdc648426c6f4d784f86e1752.png`
- `C009` → `assets/public/b573f938f7915403ef9fb529d9f966902aa6bccec26100a06a420fe20a37b49d.png`
- `C010` → `assets/public/08b7eb734195ab6c603fc5141c0cfb4f1d41f7f143488758cfdb32a4a0024f49.png`
- `C011` → `assets/public/76e9b8e7fe24767bef7d47cea74b32b3ad4965465a66818c8afa66c90c7c4d9f.png`
- `C012` → `assets/public/1692efed454965e33b5e446e5ef5946338fac2117b5f8c0db66339d8ed965a4a.png`
- `C013` → `assets/public/ab565d61bccdcd94c6825878e177096aabf8c0092a54738c8b19e8b5980642b5.png`
- `C015` → `assets/public/ae1755a4b17d84cdf8288221bd4339286a4f4393adc040822493eabe30e8a6e2.png`
- `C016` → `assets/public/8af891bcf53579e6d9c460c7dd643b771d5f66f552a47351189bfae7cba377f9.png`
- `C017` → `assets/public/c478be2700f41828eb5cac473d8a26ae5711c09cf6be82a3f4fcf4272e498dad.png`
- `C018` → `assets/public/a788199c75cf3b11026a79f05b4e37285550a7218b77eae70698cd165c121fa8.png`
- `C019` → `assets/public/60e9790ea08e11398de5db1ae1bc4a357648518f84973cef35bf5e95801e9d8f.png`
- `C020` → `assets/public/8333edd6058b159fb2fc110827c6f8ab850d494be506ba89a9a13ee1fa267ae3.png`
- `C021` → `assets/public/de928e2fdaa4296e3f942b9e39ba905472a4168c421bbc7323a9885ad460d855.png`
- `C022` → `assets/public/ca3c3016c33c5cf48fd161b1358c4038d141b162204baff30d40923587bfb61f.png`
- `C023` → `assets/public/df79c1253a1e7d793503f16d06aa6ec1661dc551a616e8f99241ba12d10fa390.png`
- `C024` → `assets/public/5b23e22fc32f137eff3beb533058955cff490fcdb30f466f9b1c5dc220ef8801.png`
- `C025` → `assets/public/26623107ad08a78b514495da9dd4fefd5d314c6c4262fe3583de3af5c6fb890d.png`
- `C026` → `assets/public/aee273fc39fd41a2c8ed3b3b0362efd3a2656401b2285acfbd2f0474a0a62dac.png`
- `C027` → `assets/public/cdd0fe111f450b97946d55a5cc4e4a2e060c8066cefaced6c217cc8e5daf42e9.png`
- `C029` → `assets/public/731af3aa2a0eafeca2455a306d556f0efc0db922d32f680e14c2be73652285f6.png`
- `C030` → `assets/public/10b9563cc907e3e3858adb6a9d09432dfa808c05876aec88a4df6d13c20f1c4e.png`
- `C031` → `assets/public/2b46b4536e64550cdf3155b84aafe4c4c99e3478da4bb374efc013cc776e6c71.png`
- `C032` → `assets/public/cab0a98b55f627436bc9a7e337bd76aac8398f7a65c33fbcdf4f158f90e49e06.png`
- `C033` → `assets/public/66de2c0cd082352b16db66bfe4a931dbd8a3c939c8262dc0563875c83069e7e7.png`
- `C034` → `assets/public/70a5758da2d73432c80f73285127ea76f54255a531fd2c807212d5f6a23b3035.png`
- `C035` → `assets/public/b82be970064bf57e19b45bf2d68b5e1312ca8a86322f9b43316a7a5efb29ef4c.png`
- `C036` → `assets/public/285bb6e3084d9f82c4a5c1288f8a0f0cc564d4478a664e08b78658c9c40f0bd6.png`
- `C037` → `assets/public/930ddd3ced17a04f031a27c383ede9209545468349faff5e2cc9ebb2e0f777de.png`
- `C038` → `assets/public/05032eee328b18c383363931af1543199a3325c9dfb166be79f2e978202866d1.png`
- `C039` → `assets/public/4bf290298712e284a6050a2e0a8580e07752ed77d7871f8fe61776fdfc1ad4e5.png`
- `C040` → `assets/public/934cec92461ebd5ae3c528ac76d3e96b7a1d3b85bd87f3fcc53c8eb6eb3f6de7.png`
- `C041` → `assets/public/f3098101a6b9c3f21a1129f33b3763601a1fe517017617f65c1e510d3d6d77d0.png`
- `C042` → `assets/public/f64342d5196c36cdcbbdd403a928527cff20a0e82c59768c9082b5dff3b1ad60.png`
- `C043` → `assets/public/02d9dd2b1ed319b0c8f1725649f547f2d77830f2c80434fade89f6fbf85ecc84.png`
- `C044` → `assets/public/ea1e90ab2d8bc567fe57c372d3803a6f3ce0804e0f4453bcdd410107ae500ca5.png`
- `C045` → `assets/public/6e57cb9136916a9f512217cef01c2429c89d754cd130b159ccdbfc263b5032a2.png`
- `C046` → `assets/public/3b26db6ebef18af8da08d5032f5fb726411cc06077ea68a4b6dd91b05b8d3317.png`
- `C047` → `assets/public/ff3406bb9005ce6ead351795e6907cb5c2bcd77431acccab132a1e59ed3a3a5c.png`

## Точно затронутые exams

`cambridge-05-test-01`, `cambridge-05-test-02`, `cambridge-05-test-03`, `cambridge-05-test-04`, `cambridge-06-test-01`, `cambridge-06-test-03`, `cambridge-06-test-04`, `cambridge-07-test-01`, `cambridge-07-test-02`, `cambridge-07-test-03`, `cambridge-07-test-04`, `cambridge-08-test-03`, `cambridge-09-test-02`, `cambridge-11-test-01`, `cambridge-11-test-02`, `cambridge-11-test-03`, `cambridge-11-test-04`, `cambridge-12-test-06`, `cambridge-12-test-07`, `cambridge-12-test-08`, `cambridge-14-test-01`, `cambridge-14-test-02`, `cambridge-14-test-04`, `cambridge-18-test-01`, `cambridge-18-test-02`, `cambridge-18-test-03`, `cambridge-18-test-04`, `cambridge-19-test-01`, `cambridge-21-test-02`.


## Final QA / production release — 2026-11-06

Stage 3 GO; Stage 4 SUCCESS. Full importer reproduction: 72 exam JSON and all 45 PNG hashes identical. Chromium/WebKit/mobile and actual production Exam/Review pass. C014/C028 remain documented exceptions, not repaired. Active backend `listening-visuals-20261106-61433b63`, Cloudflare version `29ce57d8-7263-4957-b3e9-863362890d02`. See [self-contained final release handoff](LISTENING_FINAL_RELEASE.md) for evidence, preservation fingerprints and rollback.
