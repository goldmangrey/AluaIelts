# Фаза 10 — виджеты

Найдено пять виджетов. App Group `group.com.alua.app` одинаков в shared constant и обоих entitlements (`AluaShared/AppGroup.swift:3-5`, оба entitlements:3). Виджеты сеть не вызывают; читают App Group snapshot.

AUD-10-01 (VERIFIED, S2): storage делает stage→decode→active, что защищает от битого JSON, но UserDefaults не даёт документированной атомарной multi-key транзакции между процессами (`WidgetSnapshotStorage.swift:15-24`). Старый active остаётся при сбое — приемлемый fallback.

AUD-10-02 (VERIFIED, S1): snapshot принимается только если generatedAt моложе 24 ч и learner.localDate равен текущей дате (`WidgetSnapshotStorage.swift:7-12,40-46`). После полуночи старый snapshot немедленно исчезает; если app не открыт/сеть недоступна, все learner widgets пусты вместо stale-state UI.

AUD-10-03 (VERIFIED, S2): timeline создаёт запись каждые 30 минут до суток — до 49 entries для каждого из пяти видов (`WidgetTimelineProvider.swift:41-49`), хотя vocabulary меняется раз в час, grammar раз в 4 часа. Это лишняя работа/память; reloadAllTimelines вызывается при каждом успешном sync (`WidgetSyncService.swift:17-26`).

Schema 5 и pack schema 2 проверяются жёстко; другие версии дают nil, явной migration/fallback UI нет. Snapshot содержит до 30 lexical items, поэтому статически далёк от 30 MiB, но фактический peak не измерялся. При revoke backend прекращает выдавать partner data, однако уже записанный snapshot очищается только при следующем sync/sign-out; push очистки нет.
