# Alua IELTS Vocabulary 1500 — редакторский отчёт

**Дата:** 2026-10-29. **Статус:** AI-editorial draft, ожидается независимая человеческая проверка.

**Важное ограничение:** этот набор не является официальным списком слов IELTS; уровни CEFR и приоритеты назначены редакторски.

## Размер и происхождение

- Исходных строк программно прочитано: **11,196**.
- Уникальных исходных английских форм без учёта регистра: **10,708**.
- Исходных записей предварительно рассмотрено автоматическими проверками: **11,196**.
- Редакторских кандидатных строк подготовлено: **1,642**.
- Карточек включено: **1,500**. Целевой объём: 1 500.
- Исходных строк, не вошедших в итоговый файл: **9,696** (это не означает, что все они были индивидуально проверены лексикографом).
- Кандидатов отклонено при построении: **142**.
- Форм English нормализовано (изменение написания в поле `term`): **165**.
- Разные регистровые/одинаковые исходные записи не включались повторно: **488** потенциальных повторов исходного корпуса.
- Типы: `collocation` 607, `fixed_phrase` 117, `phrasal_verb` 141, `word` 635.

## Проверки и ограничения

- Каждая строка JSONL повторно декодирована стандартным JSON-парсером; проверены уникальность ID и нормализованных форм, все поля, допустимые категории, уровни, приоритеты, навыки и фактическая строка источника.
- Проверены непустые значения, минимальная длина примера, конечный знак препинания и отсутствие точных дубликатов английских предложений.
- Начальные три слова примеров автоматически проверены на повторы (совпадение три и более раз) для обнаружения шаблонности.
- Для каждой включённой записи автором подготовлены русское значение, собственная английская дефиниция и отдельная пара примеров; это не является независимой проверкой профессиональным лексикографом.
- Дополнительно редакторски просмотрены случайные 10 карточек каждого CEFR-уровня (50 всего) и по одной случайной карточке из каждой из 50 основных категорий. Это выборочный аудит примеров, а не доказательство идеальной лингвистической точности остальных карточек.
- НЕ проводилось автоматическое доказательство лингвистической безошибочности для каждой карточки; требуется независимый native-speaker/IELTS-teacher review.

## Причины отклонения кандидатных карточек

| Причина | Количество |
|---|---:|
| `duplicate` | 44 |
| `example_short` | 1 |
| `source_missing` | 97 |

Отсутствующие в исходнике выражения отклонены, даже если сами по себе пригодны для IELTS; семантически или технически совпадающие выражения не дублировались.

## Отклонения при импорте редакторского набора

- Строка редакторской заготовки 198: `source_missing` — `numeracy`
- Строка редакторской заготовки 202: `source_missing` — `vocational training`
- Строка редакторской заготовки 206: `source_missing` — `memorise`
- Строка редакторской заготовки 223: `source_missing` — `cybersecurity`
- Строка редакторской заготовки 224: `source_missing` — `online platform`
- Строка редакторской заготовки 226: `source_missing` — `user-friendly`
- Строка редакторской заготовки 228: `source_missing` — `reliable connection`
- Строка редакторской заготовки 232: `source_missing` — `virtual reality`
- Строка редакторской заготовки 236: `source_missing` — `carbon emissions`
- Строка редакторской заготовки 238: `source_missing` — `fossil fuels`
- Строка редакторской заготовки 243: `source_missing` — `deforestation`
- Строка редакторской заготовки 246: `source_missing` — `landfill`
- Строка редакторской заготовки 248: `source_missing` — `extreme weather`
- Строка редакторской заготовки 250: `source_missing` — `energy efficiency`
- Строка редакторской заготовки 251: `source_missing` — `waste management`
- Строка редакторской заготовки 254: `source_missing` — `water scarcity`
- Строка редакторской заготовки 258: `source_missing` — `vaccination`
- Строка редакторской заготовки 264: `source_missing` — `immune system`
- Строка редакторской заготовки 265: `source_missing` — `life expectancy`
- Строка редакторской заготовки 266: `source_missing` — `chronic disease`
- Строка редакторской заготовки 269: `source_missing` — `balanced diet`
- Строка редакторской заготовки 270: `source_missing` — `sedentary lifestyle`
- Строка редакторской заготовки 273: `source_missing` — `side effects`
- Строка редакторской заготовки 275: `source_missing` — `public health`
- Строка редакторской заготовки 279: `source_missing` — `work-life balance`
- Строка редакторской заготовки 286: `source_missing` — `remote work`
- Строка редакторской заготовки 288: `source_missing` — `overtime`
- Строка редакторской заготовки 290: `source_missing` — `workload`
- Строка редакторской заготовки 292: `source_missing` — `flexible working`
- Строка редакторской заготовки 295: `source_missing` — `internship`
- Строка редакторской заготовки 296: `source_missing` — `job satisfaction`
- Строка редакторской заготовки 304: `source_missing` — `public services`
- Строка редакторской заготовки 307: `source_missing` — `sense of belonging`
- Строка редакторской заготовки 311: `source_missing` — `urban community`
- Строка редакторской заготовки 312: `source_missing` — `civic responsibility`
- Строка редакторской заготовки 315: `source_missing` — `social media`
- Строка редакторской заготовки 316: `source_missing` — `misinformation`
- Строка редакторской заготовки 340: `source_missing` — `taxation`
- Строка редакторской заготовки 341: `source_missing` — `public consultation`
- Строка редакторской заготовки 342: `source_missing` — `policy implementation`
- Строка редакторской заготовки 348: `source_missing` — `crime rate`
- Строка редакторской заготовки 349: `source_missing` — `law enforcement`
- Строка редакторской заготовки 359: `source_missing` — `legal rights`
- Строка редакторской заготовки 378: `duplicate` — `neighbourhood`
- Строка редакторской заготовки 463: `duplicate` — `renewable energy`
- Строка редакторской заготовки 515: `duplicate` — `motivation`
- Строка редакторской заготовки 520: `source_missing` — `self-esteem`
- Строка редакторской заготовки 526: `duplicate` — `belief`
- Строка редакторской заготовки 600: `duplicate` — `heritage`
- Строка редакторской заготовки 610: `duplicate` — `audience`
- Строка редакторской заготовки 612: `duplicate` — `competition`
- Строка редакторской заготовки 686: `source_missing` — `hometown`
- Строка редакторской заготовки 694: `source_missing` — `free time`
- Строка редакторской заготовки 696: `duplicate` — `hobby`
- Строка редакторской заготовки 706: `source_missing` — `I don't think so`
- Строка редакторской заготовки 707: `source_missing` — `from my perspective`
- Строка редакторской заготовки 708: `source_missing` — `I would argue that`
- Строка редакторской заготовки 709: `source_missing` — `it seems to me that`
- Строка редакторской заготовки 711: `source_missing` — `I agree`
- Строка редакторской заготовки 712: `source_missing` — `I disagree`
- Строка редакторской заготовки 713: `source_missing` — `I believe`
- Строка редакторской заготовки 714: `source_missing` — `on balance`
- Строка редакторской заготовки 717: `source_missing` — `pessimistic`
- Строка редакторской заготовки 719: `duplicate` — `reliable`
- Строка редакторской заготовки 729: `source_missing` — `considerate`
- Строка редакторской заготовки 731: `source_missing` — `spacious`
- Строка редакторской заготовки 732: `source_missing` — `cosy`
- Строка редакторской заготовки 736: `duplicate` — `modern`
- Строка редакторской заготовки 742: `duplicate` — `historic`
- Строка редакторской заготовки 744: `source_missing` — `natural light`
- Строка редакторской заготовки 747: `source_missing` — `would rather`
- Строка редакторской заготовки 755: `duplicate` — `in the past`
- Строка редакторской заготовки 756: `duplicate` — `usually`
- Строка редакторской заготовки 761: `source_missing` — `to be honest`
- Строка редакторской заготовки 772: `source_missing` — `sounds good`
- Строка редакторской заготовки 776: `source_missing` — `a quarter past`
- Строка редакторской заготовки 777: `source_missing` — `a quarter to`
- Строка редакторской заготовки 781: `source_missing` — `twice a month`
- Строка редакторской заготовки 786: `duplicate` — `approximately`
- Строка редакторской заготовки 787: `source_missing` — `per cent`
- Строка редакторской заготовки 792: `source_missing` — `economical`
- Строка редакторской заготовки 793: `duplicate` — `historic`
- Строка редакторской заготовки 803: `source_missing` — `fewer`
- Строка редакторской заготовки 846: `duplicate` — `research findings`
- Строка редакторской заготовки 854: `duplicate` — `independent variable`
- Строка редакторской заготовки 868: `source_missing` — `make a claim`
- Строка редакторской заготовки 869: `source_missing` — `relevant evidence`
- Строка редакторской заготовки 877: `source_missing` — `in comparison with`
- Строка редакторской заготовки 889: `source_missing` — `principal reason`
- Строка редакторской заготовки 901: `source_missing` — `lack of resources`
- Строка редакторской заготовки 903: `source_missing` — `practical solution`
- Строка редакторской заготовки 904: `source_missing` — `overcome obstacles`
- Строка редакторской заготовки 938: `duplicate` — `roughly equivalent`
- Строка редакторской заготовки 957: `source_missing` — `in addition to`
- Строка редакторской заготовки 958: `source_missing` — `on the contrary`
- Строка редакторской заготовки 966: `source_missing` — `associated with`
- Строка редакторской заготовки 970: `source_missing` — `in light of`
- Строка редакторской заготовки 971: `source_missing` — `in place of`
- Строка редакторской заготовки 1020: `source_missing` — `recycling`
- Строка редакторской заготовки 1021: `source_missing` — `sustainability`
- Строка редакторской заготовки 1022: `source_missing` — `pollutant`
- Строка редакторской заготовки 1066: `source_missing` — `public participation`
- Строка редакторской заготовки 1074: `duplicate` — `neighbour`
- Строка редакторской заготовки 1115: `duplicate` — `civil society`
- Строка редакторской заготовки 1122: `duplicate` — `urban environment`
- Строка редакторской заготовки 1132: `duplicate` — `urban development`
- Строка редакторской заготовки 1145: `duplicate` — `rising cost`
- Строка редакторской заготовки 1149: `source_missing` — `consumer spending`
- Строка редакторской заготовки 1157: `source_missing` — `trade agreement`
- Строка редакторской заготовки 1160: `duplicate` — `outsourcing`
- Строка редакторской заготовки 1165: `duplicate` — `foreign policy`
- Строка редакторской заготовки 1191: `duplicate` — `family member`
- Строка редакторской заготовки 1220: `source_missing` — `energy consumption`
- Строка редакторской заготовки 1229: `duplicate` — `water`
- Строка редакторской заготовки 1232: `source_missing` — `natural habitat`
- Строка редакторской заготовки 1233: `duplicate` — `farming`
- Строка редакторской заготовки 1239: `duplicate` — `physical health`
- Строка редакторской заготовки 1242: `duplicate` — `food`
- Строка редакторской заготовки 1256: `source_missing` — `social behaviour`
- Строка редакторской заготовки 1275: `source_missing` — `walking distance`
- Строка редакторской заготовки 1276: `source_missing` — `means of transport`
- Строка редакторской заготовки 1284: `duplicate` — `younger generation`
- Строка редакторской заготовки 1285: `source_missing` — `urban centre`
- Строка редакторской заготовки 1286: `source_missing` — `urbanisation`
- Строка редакторской заготовки 1287: `source_missing` — `birth rate`
- Строка редакторской заготовки 1288: `source_missing` — `ageing population`
- Строка редакторской заготовки 1289: `source_missing` — `migration pattern`
- Строка редакторской заготовки 1328: `duplicate` — `historical`
- Строка редакторской заготовки 1341: `source_missing` — `recreation`
- Строка редакторской заготовки 1400: `duplicate` — `reach out`
- Строка редакторской заготовки 1413: `duplicate` — `cut off`
- Строка редакторской заготовки 1444: `example_short` — `tea`
- Строка редакторской заготовки 1479: `duplicate` — `on the other hand`
- Строка редакторской заготовки 1480: `duplicate` — `for instance`
- Строка редакторской заготовки 1481: `duplicate` — `in particular`
- Строка редакторской заготовки 1533: `duplicate` — `bright`
- Строка редакторской заготовки 1553: `duplicate` — `in the past`
- Строка редакторской заготовки 1555: `duplicate` — `from time to time`
- Строка редакторской заготовки 1582: `duplicate` — `make a difference`
- Строка редакторской заготовки 1583: `duplicate` — `in other words`
- Строка редакторской заготовки 1587: `duplicate` — `for example`
- Строка редакторской заготовки 1697: `duplicate` — `counter-argument`

## Распределение CEFR

| Уровень | Количество |
|---|---:|
| A1 | 167 |
| A2 | 188 |
| B1 | 378 |
| B2 | 624 |
| C1 | 143 |

## Распределение приоритетов

| Приоритет | Количество |
|---|---:|
| P1 | 1169 |
| P2 | 305 |
| P3 | 26 |

## Основные категории (1–50)

| ID | Категория | Карточки |
|---:|---|---:|
| 1 | Причина и следствие | 33 |
| 2 | Тренды и изменения | 34 |
| 3 | Количество, доли и проценты | 32 |
| 4 | Исследования и доказательства | 35 |
| 5 | Аргументы и мнения | 30 |
| 6 | Сравнение и контраст | 29 |
| 7 | Важность и значимость | 22 |
| 8 | Проблемы и решения | 26 |
| 9 | Процессы и развитие | 25 |
| 10 | Время и последовательность | 26 |
| 11 | Степень, вероятность и уверенность | 24 |
| 12 | Глагольные сочетания | 26 |
| 13 | Связующие слова и логика текста | 25 |
| 14 | Предлоги и устойчивые модели | 21 |
| 15 | Образование и обучение | 38 |
| 16 | Технологии | 34 |
| 17 | Окружающая среда и климат | 25 |
| 18 | Здоровье и медицина | 27 |
| 19 | Работа и карьера | 29 |
| 20 | Общество и сообщество | 24 |
| 21 | СМИ и коммуникация | 27 |
| 22 | Государство и политика | 26 |
| 23 | Закон и преступность | 27 |
| 24 | Города и жильё | 30 |
| 25 | Бизнес и экономика | 31 |
| 26 | Глобализация и торговля | 26 |
| 27 | Культура и традиции | 29 |
| 28 | Семья и детство | 28 |
| 29 | Равенство и права | 24 |
| 30 | Энергия и ресурсы | 25 |
| 31 | Природа, животные и сельское хозяйство | 22 |
| 32 | Образ жизни, питание и психическое здоровье | 28 |
| 33 | Психология и поведение | 24 |
| 34 | Транспорт и туризм | 26 |
| 35 | Население и миграция | 18 |
| 36 | Наука | 27 |
| 37 | Университетская жизнь | 27 |
| 38 | История и перемены | 25 |
| 39 | Искусство, спорт и досуг | 24 |
| 40 | Повседневные phrasal verbs | 65 |
| 41 | Phrasal verbs для мышления и речи | 42 |
| 42 | Phrasal verbs для перемен и отношений | 34 |
| 43 | Повседневные темы Speaking Part 1 | 49 |
| 44 | Выражение мнения | 22 |
| 45 | Характер и чувства | 41 |
| 46 | Описание мест и предметов | 42 |
| 47 | Прошлое, привычки и условия | 29 |
| 48 | Устойчивые разговорные выражения | 34 |
| 49 | Listening: время, частота, даты и числа | 46 |
| 50 | Часто путаемые слова | 37 |

## Типичные проблемы исходного словаря

- Составные выражения переводились суммой отдельных значений: `disposable income — одноразовый; доход` вместо «располагаемый доход».
- `fair treatment` в источнике связывалось с «лечением», хотя для значения «справедливое отношение» это неверно.
- `academic achievement` и `cultural heritage` содержат дословную сегментацию вместо цельной русской единицы.
- Есть повторные варианты разных регистров и записи с `sb/sth`, которые следует осмысленно нормализовать.
- В корпусе есть неполные синтаксические фрагменты (`the difference between the`, `we do not`), неуместные без более широкой грамматики.
- Часть слов имеет несколько неравнозначных частей речи; одну карточку нельзя считать описанием всех значений слова.

## Что осталось проверить человеком

- Правильность выбранного одного значения, русских и английских примеров, естественность British English и уместность присвоенных CEFR и P1–P3.
- Достаточность учебных пояснений для phrasal verbs, моделей управления и многозначных слов.
- Полноту охвата Speaking Part 1 и Listening, а также слои для начинающих A1/A2 (A1/A2 меньше, чем B1/B2).
- Мягкие семантические дубликаты, которые не обнаруживаются сравнением нормализованных строк.
- Редакторские дефиниции независимым специалистом; `human_verified` намеренно не выставляется.

## Повторяющиеся начальные конструкции примеров (для дополнительной оценки)

- `the number of` — 4 раз(а).
- `we need to` — 4 раз(а).
- `the report discusses` — 3 раз(а).
- `the project requires` — 3 раз(а).

## Недопредставленность и дефицит

Корпус имеет большое количество похожих академических коллокаций и отдельных слов, но многие речевые конструкции являются неполными фразами. В нём не нашлось ряда практически полезных терминов (например, `work-life balance`, `vocational training`, `life expectancy`, `misinformation`, `public health`), поэтому они не были искусственно добавлены. Слабо представлены категории «Население и миграция» (18), «Предлоги и устойчивые модели» (21), «Природа, животные и сельское хозяйство» (22) и «Важность и значимость» (22). Основной массив карточек B1/B2; базовые A1/A2 стоит дополнить в следующей версии из других источников. Покрытие по каждому разделу выше отражает фактический редакторский отбор, а не квоту.

## Примеры для ручной проверки (до 20 карточек)

### src-002275 — underlying cause
- Источник: строка 2275; исходная форма: `underlying cause`.
- B2 / P1 / тема 1. Перевод: **первопричина; глубинная причина**.
- Definition: the deeper reason why a problem exists
- EN: Poor planning was the underlying cause of the delay.
- RU: Плохое планирование стало глубинной причиной задержки.

### src-008922 — percentage
- Источник: строка 8922; исходная форма: `percentage`.
- B1 / P1 / тема 3. Перевод: **процентная доля; процент**.
- Definition: an amount expressed as part of one hundred
- EN: The percentage of pupils cycling to school rose to 18%.
- RU: Доля школьников, добирающихся до школы на велосипеде, выросла до 18%.

### src-000634 — empirical evidence
- Источник: строка 634; исходная форма: `empirical evidence`.
- C1 / P2 / тема 4. Перевод: **эмпирические данные; свидетельства, основанные на наблюдениях**.
- Definition: information gathered through observation or experiment
- EN: There is little empirical evidence to support that claim.
- RU: Существует мало эмпирических данных, подтверждающих это утверждение.

### src-000380 — counter-argument
- Источник: строка 380; исходная форма: `counter argument`.
- B2 / P1 / тема 5. Перевод: **контраргумент**.
- Definition: a reason given against a previous argument
- EN: A strong counter-argument is that the plan would be too expensive.
- RU: Сильный контраргумент заключается в том, что план обойдётся слишком дорого.

### src-008001 — knowledge
- Источник: строка 8001; исходная форма: `knowledge`.
- A2 / P1 / тема 15. Перевод: **знания**.
- Definition: information and understanding gained through learning
- EN: Practical experience can deepen your knowledge of a subject.
- RU: Практический опыт может углубить знания по предмету.

### src-003276 — global warming
- Источник: строка 3276; исходная форма: `global warming`.
- B2 / P1 / тема 17. Перевод: **глобальное потепление**.
- Definition: the long-term increase in the Earth's average temperature
- EN: Global warming increases the risk of extreme heat.
- RU: Глобальное потепление повышает риск экстремальной жары.

### src-009252 — promotion
- Источник: строка 9252; исходная форма: `promotion`.
- B1 / P1 / тема 19. Перевод: **повышение по службе**.
- Definition: a move to a more senior position at work
- EN: She received a promotion after two years in the team.
- RU: Через два года работы в команде она получила повышение.

### src-000586 — economic growth
- Источник: строка 586; исходная форма: `economic growth`.
- B2 / P1 / тема 25. Перевод: **экономический рост**.
- Definition: an increase in the goods and services produced by an economy
- EN: Tourism contributed to economic growth in the region.
- RU: Туризм способствовал экономическому росту региона.

### src-008852 — parent
- Источник: строка 8852; исходная форма: `parent`.
- A1 / P1 / тема 28. Перевод: **родитель**.
- Definition: a mother or father
- EN: Every parent wants their child to feel safe.
- RU: Каждый родитель хочет, чтобы его ребёнок чувствовал себя в безопасности.

### src-009072 — population
- Источник: строка 9072; исходная форма: `population`.
- B1 / P1 / тема 35. Перевод: **население; численность населения**.
- Definition: all the people living in a particular area
- EN: The population of the city has grown steadily.
- RU: Население города неуклонно растёт.

### src-003816 — look after
- Источник: строка 3816; исходная форма: `LOOK AFTER`.
- A2 / P1 / тема 40. Перевод: **присматривать за; заботиться о**.
- Definition: to take care of a person, animal or thing
- EN: My aunt looks after our cat when we travel.
- RU: Моя тётя присматривает за нашим котом, когда мы уезжаем.

### src-002431 — figure out
- Источник: строка 2431; исходная форма: `FIGURE OUT`.
- B2 / P1 / тема 41. Перевод: **разобраться; понять**.
- Definition: to understand something by thinking carefully
- EN: I couldn't figure out why the printer kept stopping.
- RU: Я не мог понять, почему принтер постоянно останавливался.

### src-002402 — break up
- Источник: строка 2402; исходная форма: `BREAK UP`.
- B1 / P1 / тема 42. Перевод: **расставаться; прекращать отношения**.
- Definition: to end a romantic relationship
- EN: They broke up after living together for three years.
- RU: Они расстались после трёх лет совместной жизни.

### src-011051 — weekend
- Источник: строка 11051; исходная форма: `weekend`.
- A1 / P1 / тема 43. Перевод: **выходные**.
- Definition: Saturday and Sunday, often days away from work
- EN: I usually visit my parents at the weekend.
- RU: По выходным я обычно навещаю родителей.

### src-003509 — in my opinion
- Источник: строка 3509; исходная форма: `in my opinion`.
- B1 / P1 / тема 44. Перевод: **по моему мнению**.
- Definition: used to introduce a personal view
- EN: In my opinion, parks are essential in large cities.
- RU: По моему мнению, парки необходимы в больших городах.

### src-009936 — shy
- Источник: строка 9936; исходная форма: `shy`.
- A2 / P1 / тема 45. Перевод: **застенчивый**.
- Definition: nervous around unfamiliar people
- EN: I was shy when I first started university.
- RU: Я был застенчивым, когда только поступил в университет.

### src-006186 — crowded
- Источник: строка 6186; исходная форма: `crowded`.
- B1 / P1 / тема 46. Перевод: **переполненный; многолюдный**.
- Definition: containing too many people or things
- EN: The beach gets crowded on sunny weekends.
- RU: В солнечные выходные пляж становится многолюдным.

### src-002571 — a day or two
- Источник: строка 2571; исходная форма: `a day or two`.
- A2 / P1 / тема 47. Перевод: **день-два**.
- Definition: one or two days, approximately
- EN: I'll finish the report in a day or two.
- RU: Я закончу отчёт через день-два.

### src-003331 — half past
- Источник: строка 3331; исходная форма: `HALF PAST`.
- A1 / P1 / тема 49. Перевод: **половина следующего часа**.
- Definition: thirty minutes after a stated hour
- EN: The lecture starts at half past nine.
- RU: Лекция начинается в половине десятого.

### src-005468 — borrow
- Источник: строка 5468; исходная форма: `borrow`.
- A2 / P1 / тема 50. Перевод: **брать взаймы**.
- Definition: to take something temporarily and return it
- EN: Can I borrow your pen for a minute?
- RU: Можно я возьму твою ручку на минуту?

