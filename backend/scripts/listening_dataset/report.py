# ruff: noqa: E501
"""Generate the Stage 1 report and an audit row for every expected position.
QA CSV rows are not public question objects and are never counted as questions.
Markdown prose stays in full paragraphs for editing and deterministic output.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path

from importer import DEFAULT_OUTPUT, ROOT, dump


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def ranges(numbers):
    values = sorted(set(numbers))
    runs = []
    for n in values:
        if runs and runs[-1][-1] + 1 == n:
            runs[-1].append(n)
        else:
            runs.append([n])
    return ", ".join(str(r[0]) if len(r) == 1 else f"{r[0]}–{r[-1]}" for r in runs) or "—"


def position_audit(root):
    stream = io.StringIO()
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(
        [
            "exam_id",
            "book",
            "printed_test_number",
            "local_ordinal",
            "part_number",
            "question_number",
            "parsed",
            "renderable",
            "source_verified",
            "key_present",
            "key_verified",
            "status",
            "task_source",
            "source_line",
            "pdf_pages",
            "problems",
        ]
    )
    for row in read(root / "manifest.json")["exams"]:
        doc = read(root / "exams" / f"{row['exam_id']}.json")
        key = read(root / "keys" / f"{row['exam_id']}.json")
        qa = read(root / "qa/exams" / f"{row['exam_id']}.json")
        question_map = {
            q["question_number"]: (q, g)
            for p in doc["parts"]
            for g in p["groups"]
            for q in g["questions"]
        }
        answer_map = {a["question_number"]: a for a in key["answers"]}
        for number in range(1, 41):
            item = question_map.get(number)
            q, g = item if item else (None, None)
            a = answer_map.get(number)
            source = (
                g["source_reference"] if g else doc["parts"][(number - 1) // 10]["source_reference"]
            )
            issues = (
                q["issues"]
                if q
                else [
                    i["reason"]
                    for i in qa["issues"]
                    if i.get("question_number") == number and not i["code"].startswith("key")
                ]
            )
            status = q["verification"]["status"] if q else "source_required"
            writer.writerow(
                [
                    doc["exam_id"],
                    doc["book"],
                    doc["printed_test_number"],
                    doc["local_ordinal"],
                    (number - 1) // 10 + 1,
                    number,
                    int(q is not None),
                    int(bool(q and q["renderable"])),
                    int(bool(q and q["verification"]["status"] == "source_verified")),
                    int(a is not None),
                    int(bool(a and a["verification"]["status"] == "key_verified")),
                    status,
                    source["file"],
                    q["blank_references"][0]["line"] if q else "",
                    ",".join(map(str, source["pdf_pages"])),
                    "; ".join(issues),
                ]
            )
    (root / "qa/positions.csv").write_text(stream.getvalue(), encoding="utf-8")


def document(root, output, checks=None):
    manifest = read(root / "manifest.json")
    tot = manifest["totals"]
    inventory = read(root / "qa/input_inventory.json")
    assets = read(root / "qa/assets.json")["assets"]
    native_tables = sum(
        bool(g["structured_layout"])
        for e in manifest["exams"]
        for p in read(root / "exams" / f"{e['exam_id']}.json")["parts"]
        for g in p["groups"]
    )
    files = sum(len(b["files"]) for b in inventory)
    duplicate_sets = sum(
        len(f["copies"]) - 1 for b in inventory for f in b["canonical_files"].values()
    )
    ready = [e["exam_id"] for e in manifest["exams"] if e["ready_for_stage2"]]
    lines = [
        "# Listening Dataset — Stage 1",
        "",
        "Подготовлен вопросный датасет из новых материалов ListTest. Охват всех книг не означает независимую сверку всего текста. Stage 2 не реализован.",
        "",
        "| Метрика | Фактический результат |",
        "|---|---:|",
        f"| Books processed | {tot['books_processed']}/18 |",
        f"| Exams processed | {tot['exams_processed']}/72 |",
        f"| Parts processed | {tot['parts_processed']}/288 |",
        f"| Question positions found | {tot['parsed_questions']}/2880 |",
        f"| Interactive questions | {tot['interactive_questions']}/2880 |",
        f"| Source-verified questions | {tot['source_verified_questions']}/2880 |",
        f"| Answer keys present | {tot['keys_present']}/2880 |",
        f"| Verified answer keys | {tot['key_verified_positions']}/2880 |",
        f"| Exams with complete question content | {tot['complete_question_content']}/72 |",
        f"| Exams with complete verified keys | {tot['complete_verified_keys']}/72 |",
        f"| Exams ready for Stage 2 content integration | {tot['ready_for_stage2']}/72 |",
        f"| Missing questions | {tot['missing_questions']} |",
        f"| Parsed but blocked questions | {tot['blocked_questions']} |",
        f"| Critical issues | {tot['critical_issues']} |",
        "",
        "Critical issues — 160 отсутствующих ключей Cambridge 04 и 16 позиций с дефектами первичного материала. Не проведённая независимая сверка остальных позиций учитывается отдельно как needs_review, без искусственного PASS.",
        "",
        "## Входные материалы",
        "",
        f"Обработаны {files} файлов из 18 каталогов `~/Desktop/ListTest/Cambridge_IELTS_04…21`. Найдены 36 canonical TXT (18 question files и 18 answer files). {duplicate_sets} дополнительных копий TXT распознаны по SHA-256; они не создают дополнительные тесты. Выбран корневой TXT каждой книги; все его копии идентичны. JSON/CSV manifests и README включены в inventory, но их утверждения о проверенности не наследуются.",
        "",
        "Оригинальные 18 PDF найдены в `ieltsbooks/Cambridge-IELTS-04.pdf` … `Cambridge-IELTS-21.pdf`; в inventory записаны реальные SHA-256. Старый extracted/OCR архив и веб-сайты не использовались. Массового OCR не было. PDF визуально использовались для адресной сверки, а одна повреждённая вложенная картинка была восстановлена прямым рендером страницы.",
        "",
        "После отката не было Listening JSON и исходных .py импортёра; остался только игнорируемый `__pycache__`. Изучены Reading manifest и организация `backend/scripts/reading_dataset`. Reading не изменён. Все текущие изменения — новые файлы датасета, pipeline и этот отчёт.",
        "",
        "## Созданные файлы",
        "",
        "- `backend/scripts/listening_dataset/importer.py`: воспроизводимый импорт и атомарная замена результата.",
        "- `schema.py`: закрытые JSON Schema contracts.",
        "- `validator.py`: проверки всех тестов, assets, приватности и готовности.",
        "- `source_reviews.json`: адресные, привязанные к SHA-256 сверки и исправления.",
        "- `test_contract.py`: постоянные регрессии на настоящих заданиях.",
        "- `report.py`, `requirements.txt`, `README.md`: отчёт, окружение и команды воспроизведения.",
        "- `backend/app/content/listening_v1/manifest.json`, `exams/` (72 JSON), `keys/` (72 private JSON, четыре честно пустых для Cambridge 04).",
        "- `schemas/`, `assets/public/`, `assets/private/`, `qa/` (inventory, assets registry, per-exam issues, 2880-row audit CSV, validation, Cambridge 12 mapping, historical revisions).",
        "- `docs/LISTENING_DATASET_STAGE1.md`: этот воспроизводимый отчёт.",
        "",
        "## Canonical contract",
        "",
        "`Exam` содержит stable ID, book, printed_test_number, local_ordinal, четыре Part, public assets и раздельные метрики. IDs Cambridge 12 — `cambridge-12-test-05…08`, ordinal — 1…4; точная таблица хранится в `qa/cambridge12_mapping.json`.",
        "",
        "`Part` содержит диапазон 1–10/11–20/21–30/31–40, порядок, source reference, instructions в группах и `audio_mapping_key`. `Group` содержит точные инструкции, тип, constraints, presentation mode, полный shared answer bank, content blocks и ordered questions. `Question` содержит ID/номер, actual prompt или visual_binding, input_type, options, blank_references с номерами строк и offsets, limits, parsed/renderable и verification.",
        "",
        f"Представлены все 13 требуемых типов и дополнительный `completion_with_word_bank` для настоящего не буквенного банка Cambridge 04. Для {native_tables} явно разделённых таблиц сохранены также typed rows/cells и номера пропусков. Остальные сложные таблицы, формы, карты, планы, диаграммы и flowcharts используют оригинальные изображения. Изображения не считаются вопросами: у каждого вопроса есть отдельный input и привязка.",
        "",
        "У spatial options нет выдуманного текста: label взят из напечатанного диапазона, visual_reference указывает оригинал с соответствующей меткой. Для обычного MCQ каждый A/B/C содержит настоящий текст. Multiple-choice pairs имеют два question_id и два answer slots. Cambridge 04 Test 3 Q40 — отдельно один multi_select с двумя обязательными выборами на один номер.",
        "",
        "В визуально сверенных image-backed группах оригинальная страница является основным представлением, а content blocks содержат изображения и реальные answer fields. Это сохраняет геометрию и исходные опечатки без исправления по смыслу; нет утверждения о посимвольной редактуре всего TXT.",
        "",
        "## Importer и версии",
        "",
        "Импортёр использует state machine Test/Part, collapse повторных PDF headers, parser объявленных диапазонов, inline numbered blanks, source offsets, колонок вариантов и отдельных answer files. Он не создаёт question object для номера, который не удаётся достоверно привязать. Ошибки остаются адресными. Отдельные visual overrides содержат исходные страницы и pinned source hashes: при изменении проверенного источника импорт останавливается для повторной сверки.",
        "",
        "Промежуточный результат строится в соседней временной директории, проходит validator и затем заменяется rename на том же filesystem. При замене изменённых документов сохраняются предыдущие exam/key JSON, схемы, manifest, source inventory и asset registry в `qa/history/<previous-manifest-sha256>/`; старые content-addressed изображения сохраняются. Чужой producer не перезаписывается автоматически. Повторный импорт тех же входов не создаёт новую history revision.",
        "",
        "## Ключи и приватность",
        "",
        "`keys/<exam_id>.json` содержит official_answer, исходную source_notation, явно указанные slash forms, информацию об optional parentheses, source line, private evidence assets, verification и unordered_groups. Словесные/орфографические альтернативы не добавлены по догадке. Сложная official notation сохранена для дальнейшей реализации grading; посимвольное раскрытие всех скобок и составных ответов не объявлено готовым grading engine.",
        "",
        "Cambridge 09 Test 1 Q33 требует два компонента внутри одного ответа (оба за один балл); source notation сохранена вместе с typed within_position_rules/all_components_required; она не превращена в два номера. Пара текстовых ответов Cambridge 06 Q26–27 также хранит два самостоятельных слота с общим unordered keyset. Unordered sets для отдельных answer slots хранят список номеров и expected_units приватно; в public JSON остаются только cardinality/order, без правильных букв.",
        "",
        "В public exam нет ключей, expected units, правильных ответов, private images или абсолютных Mac paths. Валидатор проверяет закрытую схему и запрет приватных полей рекурсивно. `keys`, `qa`, `assets/private` нельзя монтировать как статический public каталог. Наличие файла внутри backend само по себе не создаёт endpoint; API здесь не разрабатывался.",
        "",
        "## Assets",
        "",
        f"Реестр содержит {len(assets)} уникальных изображений: {sum(a['visibility'] == 'public' for a in assets)} public task/source assets и {sum(a['visibility'] == 'private' for a in assets)} private key evidence assets. Сохранены реальные bytes, размеры, SHA-256, исходные relative files, роли и Book/Test/Part associations. Дедупликация — по содержимому, не по имени или регистру каталога. Изображения не перерисовывались.",
        "",
        "Единственный сломанный input asset: Cambridge 13 `Listening_Complete/images/PDF_036.png`, 0 bytes. Он восстановлен из локального PDF page 36 (PyMuPDF 2x, без OCR); `qa/assets.json` содержит оригинальный путь, причину, PDF hash и страницу. Desktop inputs не менялись.",
        "",
        "## Ограничения и конкретные блокировки",
        "",
        "- Cambridge 04 Test 1 Part 4 Q34: PDF p.8 и TXT печатают `43` вместо ожидаемого номера. Q34 object не придуман; нужна чистая подтверждающая публикация.",
        "- Cambridge 04 Tests 1–4: все 160 официальных ключей отсутствуют в комплекте. В PDF 128 страниц, поиск по text layer не обнаружил answer-key section; последняя страница — Speaking. Вложения официальных ключей отсутствуют.",
        "- Cambridge 06 Test 2 Part 1 Q6–10: PDF p.35 и supplied table crop имеют нечитаемые заголовки колонок. Пять полей разобраны, исходное изображение сохранено, но renderable=false для полного задания.",
        "- Cambridge 14 Test 3 Part 1 Q1–10: PDF p.53 визуально почти пуст. TXT реконструирован из hidden text layer; эти десять полей parsed, source_required и blocked.",
        "- Cambridge 16 Test 2 Part 2 Q11: `Baprivate home.` восстановлено в `B. a private home.` строго по PDF p.35, A также сверено. Cambridge 13 Test 1 Part 3 Q26–30: банк A–H в две строки восстановлен общим parser колонок по PDF p.15.",
        "- Cambridge 20: оригинальные опечатки/encoding damage не исправлены по смыслу. Для просмотренных групп сохранено оригинальное визуальное представление; `va (1)` и дублированный префикс суммы в Q2 не скрыты.",
        "",
        "В остальных строках таблицы ниже blockers могут отсутствовать, но остаётся независимая visual review конкретных вопросов и/или официальных ключей. Их полный список — `qa/exams/<exam_id>.json` и `qa/positions.csv`. Это отдельная работа, а не структурная ошибка или отсутствие аудио.",
        "",
        "## Validator и фактические проверки",
        "",
        "Default validator проверяет consistency: schema/UTF-8, 72 IDs, четыре Part, ranges, unique IDs, source anchors, options/банки, ограничения, assets и их hashes/dimensions, key alignment, unordered slots, public/private isolation, корректность всех счётчиков и обязательную адресную QA запись для каждого missing/blocked номера. Он отдельно возвращает `all_question_positions_present=false`, `all_official_keys_present=false`, `stage1_all_ready=false`.",
        "",
        "`--require-ready` требует полной готовности всех 72 экзаменов и возвращает exit 1 на текущем датасете. Это ожидаемый честный результат. Успешный consistency check не означает, что все экзамены готовы.",
        "",
    ]
    if checks:
        lines.extend(
            [
                "Проверки текущей версии:",
                "",
                *[f"- {item['name']}: {item['result']}" for item in checks["checks"]],
                "",
            ]
        )
    else:
        lines.extend(
            [
                "Результаты выполненных команд фиксируются финальным запуском `report.py --checks <checks.json>`. Отсутствие такого файла не считается PASS.",
                "",
            ]
        )
    lines.extend(
        [
            "Browser E2E, frontend builds, API, Firebase и audio tests не выполнялись: они не входят в Stage 1. Никаких SSH, миграций, deploy, commit/push, production .env или изменений Reading не было.",
            "",
            "## Stage 2",
            "",
            "Для будущего аудио каждый Part уже имеет identity key `{book, printed_test_number, local_ordinal, part_number}`. Путей, durations, SHA-256 MP3 и timestamps здесь нет. На Stage 2 Oracle inventory должен привязываться к этим ключам с сохранением Cambridge 12 Test 5–8. Отсутствие аудио не участвует в текущей готовности.",
            "",
            "Полностью source/key verified для content integration: "
            + ", ".join(f"`{eid}`" for eid in ready)
            + ". Это готовность содержания и полей, без реализации приложения, backend grading или проверки audio.",
            "",
            "Перед подключением остальных экзаменов нужны: официальные Cambridge 04 keys, читаемые источники для 16 проблемных позиций, независимая сверка оставшихся вопросов/ключей и интерпретация сложной official notation для grading. Не включать needs_review тесты как verified.",
            "",
            "## Все 72 теста",
            "",
            "Parsed/Interactive/Source — позиции из 40. Keys — present / source-verified. Missing/blocked — номера, а не количество изображений. `needs_review` не означает ready.",
            "",
            "| Cambridge | Printed Test (ordinal) | Parsed | Interactive | Source | Keys | Missing / blocked | Status | Problems |",
            "|---|---|---:|---:|---:|---:|---|---|---|",
        ]
    )
    for e in manifest["exams"]:
        qa = read(root / "qa/exams" / f"{e['exam_id']}.json")
        reasons = []
        if e["book"] == 4:
            reasons.append("Официальный ключ Q1–40 отсутствует")
        for finding in qa["source_findings"]:
            if finding.get("status") == "source_required":
                reasons.append(
                    f"Part {finding['part']}, Q{finding.get('question', ranges(finding.get('questions', [])))}; PDF {finding['pdf_page']}: {finding['finding']}"
                )
        pending = qa["editorial_review_pending"]
        if pending["question_numbers"]:
            reasons.append("Не сверены вопросы Q" + ranges(pending["question_numbers"]))
        if pending["key_numbers"]:
            reasons.append("Не сверены ключи Q" + ranges(pending["key_numbers"]))
        status = (
            "ready_for_stage2"
            if e["ready_for_stage2"]
            else "source_required"
            if e["missing_positions"] or e["blocked_positions"] or e["book"] == 4
            else "needs_review"
        )
        text = "; ".join(reasons) or "Содержание и ключи проверены; аудио вне Stage 1"
        lines.append(
            f"| {e['book']:02} | {e['printed_test_number']} ({e['local_ordinal']}) | {e['parsed_questions']} | {e['interactive_questions']} | {e['source_verified_questions']} | {e['keys_present']} / {e['key_verified_positions']} | {ranges(e['missing_positions'])} / {ranges(e['blocked_positions'])} | {status} | {text.replace('|', '/')} |"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--output", type=Path, default=ROOT / "docs/LISTENING_DATASET_STAGE1.md")
    ap.add_argument("--checks", type=Path)
    args = ap.parse_args()
    position_audit(args.dataset)
    checks = read(args.checks) if args.checks else None
    if checks:
        dump(args.dataset / "qa/checks.json", checks)
    document(args.dataset, args.output, checks)
    print(args.output)


if __name__ == "__main__":
    main()
