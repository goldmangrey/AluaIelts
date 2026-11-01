import SwiftUI

struct ReadingView: View {
    @Bindable var store: ReadingStore
    @State private var player = false
    var body: some View {
        List {
            Section {
                Text("IELTS Academic").font(.title2.bold())
                Text("Cambridge Practice Tests").foregroundStyle(.secondary)
            }.listRowBackground(Color.clear)
            if let pending = store.disk.pendingStart {
                Section("Восстановить начало") {
                    Button("Продолжить запрос начала экзамена") { Task { player = await store.start(exam: pending.exam_id, mode: pending.mode, passage: pending.selected_passage) } }.disabled(store.busy)
                }
            }
            if let resume = unfinished.first {
                Section("Продолжить") {
                    Button { Task { player = await store.open(resume.id) } } label: {
                        VStack(alignment: .leading, spacing: 8) {
                            Text(title(resume.exam_id)).font(.headline)
                            if let record = store.disk.records[resume.id] {
                                Text("Passage \(record.ui.currentPassage) · \(record.exam.questions.count - record.unanswered) ответов").font(.subheadline).foregroundStyle(.secondary)
                            }
                            Text("Продолжить").font(.subheadline.bold())
                        }.padding(.vertical, 8)
                    }.disabled(store.busy).accessibilityIdentifier("reading.resume")
                }
            }
            Section {
                if store.busy && store.books.isEmpty { SwiftUI.ProgressView("Загружаем библиотеку…") }
                ForEach(store.books) { book in
                    NavigationLink {
                        ReadingBookView(store: store, bookNumber: book.book_number, player: $player)
                    } label: {
                        VStack(alignment: .leading, spacing: 5) {
                            Text("Cambridge IELTS \(book.book_number)").font(.headline)
                            Text("\(book.available.count) теста · завершено \(book.exams.reduce(0) { $0 + $1.completed_attempts })").font(.subheadline).foregroundStyle(.secondary)
                            if let band = book.exams.compactMap(\.best_estimated_band).max() { Text("Best Estimated Band \(band, specifier: "%.1f")").font(.caption) }
                        }.padding(.vertical, 8)
                    }.accessibilityIdentifier("reading.book.\(book.book_number)")
                }
            }
            Section {
                Text("Материалы для личной практики могут содержать ошибки переноса из исходных PDF.").font(.footnote).foregroundStyle(.secondary)
                if let message = store.errorMessage { Text(message).font(.subheadline); Button("Повторить") { Task { await store.loadLibrary() } } }
            }
        }.navigationTitle("Reading").navigationBarTitleDisplayMode(.large)
        .task { await store.loadLibrary() }
        .refreshable { await store.loadLibrary() }
        .fullScreenCover(isPresented: $player, onDismiss: { Task { await store.loadLibrary() } }) {
            ReadingFlow(store: store)
        }

    }
    private var unfinished: [ReadingAttempt] {
        var items = Dictionary(uniqueKeysWithValues: store.disk.history.filter { !$0.terminal }.map { ($0.id, $0) })
        for r in store.disk.records.values {
            if r.server.terminal { items[r.id] = nil } else { items[r.id] = r.server }
        }
        return items.values.sorted { $0.started_at > $1.started_at }
    }
    private func title(_ eid: String) -> String {
        store.disk.books.flatMap(\.exams).first { $0.exam_id == eid }?.title ?? "Reading"
    }
}

struct ReadingBookView: View {
    @Bindable var store: ReadingStore
    let bookNumber: Int
    @Binding var player: Bool
    var body: some View {
        List {
            Section("Academic Reading") {
                ForEach(store.books.first { $0.book_number == bookNumber }?.available ?? []) { exam in
                    NavigationLink {
                        ReadingModeView(store: store, entry: exam, player: $player)
                    } label: {
                        HStack {
                            Text("Test \(exam.source_test_number)")
                            Spacer()
                            if let band = exam.best_estimated_band { Text("Best Band \(band, specifier: "%.1f")").foregroundStyle(.secondary) }
                            else { Text(exam.completed_attempts == 0 ? "Не начат" : "Завершено: \(exam.completed_attempts)").foregroundStyle(.secondary) }
                        }.padding(.vertical, 8)
                    }.accessibilityIdentifier("reading.test.\(exam.source_test_number)")
                }
            }
        }.navigationTitle("Cambridge IELTS \(bookNumber)").navigationBarTitleDisplayMode(.inline)
    }
}
struct ReadingModeView: View {
    @Bindable var store: ReadingStore
    let entry: ReadingCatalogEntry
    @Binding var player: Bool
    @State private var passage = 1
    var body: some View {
        List {
            Section("Полный экзамен") {
                Text("60 минут · 3 passages · 40 вопросов")
                Text("Таймер продолжает идти после закрытия приложения. Ответы, поступившие на сервер после дедлайна, не засчитываются.").font(.footnote).foregroundStyle(.secondary)
                Button("Начать экзамен") { Task { player = await store.start(exam: entry.exam_id, mode: .full_exam, passage: nil) } }
                    .buttonStyle(.borderedProminent).tint(.primary).disabled(store.busy).accessibilityIdentifier("reading.start.full")
            }
            Section("Тренировка") {
                Picker("Passage", selection: $passage) { ForEach(1...3, id: \.self) { Text("Passage \($0)").tag($0) } }.pickerStyle(.segmented)
                Text("Без строгого таймера. Можно проверять ответы по ходу тренировки. IELTS Band не рассчитывается.").font(.footnote).foregroundStyle(.secondary)
                Button("Начать тренировку") { Task { player = await store.start(exam: entry.exam_id, mode: .passage_practice, passage: passage) } }.disabled(store.busy).accessibilityIdentifier("reading.start.practice")
            }
            if store.busy { SwiftUI.ProgressView("Подготавливаем материалы…") }
            if let error = store.errorMessage { Section { Text(error).font(.subheadline) } }
            Section("История попыток") {
                let history = store.disk.history.filter { $0.exam_id == entry.exam_id }
                if history.isEmpty { Text("Здесь появятся твои попытки.").foregroundStyle(.secondary) }
                ForEach(history) { attempt in
                    Button { Task { player = await store.open(attempt.id) } } label: {
                        VStack(alignment: .leading, spacing: 5) {
                            Text(attempt.started_at, style: .date)
                            Text(attempt.mode == .full_exam ? "Полный экзамен" : "Passage \(attempt.selected_passage ?? 1)").font(.subheadline)
                            if let score = attempt.raw_score { Text("\(score) верно" + (attempt.estimated_band.map { String(format: " · Estimated Band %.1f", $0) } ?? "")).font(.subheadline).foregroundStyle(.secondary) }
                            else { Text(attempt.terminal ? "Посмотреть результат" : "Продолжить").font(.subheadline).foregroundStyle(.secondary) }
                        }
                    }.disabled(store.busy)
                }
                if store.hasMoreHistory { Button("Загрузить ещё") { Task { await store.loadHistory(reset: false) } } }
            }
        }.navigationTitle("Test \(entry.source_test_number)").navigationBarTitleDisplayMode(.inline)
    }
}

struct ReadingFlow: View {
    @Bindable var store: ReadingStore
    @Environment(\.dismiss) private var dismiss
    var body: some View {
        NavigationStack {
            if let record = store.active {
                if let result = record.result { ReadingResultsView(store: store, result: result) }
                else if record.server.terminal {
                    ContentUnavailableView {
                        Label("Получаем результат", systemImage: "checkmark.circle")
                    } description: { Text("Ответы завершены на сервере. Подключись к сети, чтобы загрузить результат.") } actions: {
                        Button("Повторить") { Task { await store.refresh() } }
                        Button("В библиотеку") { dismiss() }
                    }
                } else { ReadingPlayerView(store: store) }
            } else { ContentUnavailableView("Попытка недоступна", systemImage: "book.closed").toolbar { Button("Закрыть") { dismiss() } } }
        }.interactiveDismissDisabled()
    }
}

struct ReadingPlayerView: View {
    @Bindable var store: ReadingStore
    @Environment(\.dismiss) private var dismiss
    @Environment(\.scenePhase) private var scenePhase
    @State private var detent: PresentationDetent = .height(134)
    @State private var auxiliary: Panel?
    @State private var confirmation: Confirmation?
    private enum Confirmation { case exit, submit }
    private enum Panel: String, Identifiable { case navigator, settings; var id: String { rawValue } }
    var body: some View {
        GeometryReader { geometry in
            let wide = geometry.size.width >= 650
            VStack(spacing: 0) {
                HStack {
                    Text(store.active?.exam.title ?? "Reading").font(.headline)
                    Spacer()
                    TimelineView(.periodic(from: .now, by: 1)) { _ in
                        Text(timer).font(.system(.headline, design: .monospaced)).monospacedDigit()
                            .foregroundStyle(store.remainingSeconds == 0 ? .red : store.preferences.theme.foreground)
                            .accessibilityLabel("Осталось \(timer)")
                            .onChange(of: store.remainingSeconds) { _, n in if n == 0 { Task { await store.refresh() } } }
                    }
                }.padding(.horizontal).padding(.vertical, 10)
                if let record = store.active {
                    Picker("Reading passage", selection: Binding(get: { record.ui.currentPassage }, set: { store.selectPassage($0) })) {
                        ForEach(record.exam.passages) { p in Text("Passage \(p.number)").tag(p.number) }
                    }.pickerStyle(.segmented).padding(.horizontal).padding(.bottom, 8)
                }
                if store.active?.server.mode == .full_exam && store.remainingSeconds == nil {
                    HStack { Text("Подключись к сети, чтобы подтвердить оставшееся время.").font(.caption); Button("Повторить") { Task { await store.refresh() } } }.padding(.horizontal)
                } else if store.remainingSeconds == 0 {
                    Text("Время экзамена закончилось. Проверяем ответы, сохранённые на сервере.").font(.caption).padding(.horizontal)
                } else if store.active?.queue.isEmpty == false || store.active?.conflict == true || store.diskError {
                    Text(store.syncMessage).font(.caption).foregroundStyle(.secondary).padding(.horizontal).padding(.bottom, 4)
                }
                HStack(spacing: 0) {
                    if let p = store.active?.exam.passages.first(where: { $0.number == store.active?.ui.currentPassage }) {
                        ReadingPassageView(store: store, passage: p).id(p.id)
                    }
                    if wide { Divider(); panel(expanded: true).frame(width: geometry.size.width * 0.46) }
                }
            }
            .background(store.preferences.theme.background).foregroundStyle(store.preferences.theme.foreground)
            .sheet(isPresented: Binding(get: { !wide }, set: { _ in })) {
                NavigationStack {
                    panel(expanded: detent != .height(134))
                        .toolbar(.hidden, for: .navigationBar)
                }
                    .presentationDetents([.height(134), .medium, .large], selection: $detent)
                    .presentationBackgroundInteraction(.enabled(upThrough: .medium))
                    .presentationDragIndicator(.visible).interactiveDismissDisabled()
                    .preferredColorScheme(store.preferences.theme == .dark ? .dark : .light)
                    .onChange(of: detent) { _, value in store.updateUI { $0.detent = value == .large ? "large" : value == .medium ? "medium" : "compact" } }
            }
        }
        .toolbar {
            ToolbarItem(placement: .topBarLeading) { Button("Выйти") { confirmation = .exit } }
            ToolbarItemGroup(placement: .topBarTrailing) {
                Button { auxiliary = .navigator } label: { Image(systemName: "square.grid.3x3") }.accessibilityLabel("Все вопросы")
                Button { auxiliary = .settings } label: { Image(systemName: "textformat.size") }.accessibilityLabel("Настройки чтения")
                Button("Завершить") { confirmation = .submit }.disabled(store.isSubmitting)
            }
        }
        .navigationBarBackButtonHidden().navigationBarTitleDisplayMode(.inline)
        .preferredColorScheme(store.preferences.theme == .dark ? .dark : .light)
        .task {
            detent = store.active?.ui.detent == "large" ? .large : store.active?.ui.detent == "medium" ? .medium : .height(134)
            while !Task.isCancelled {
                do { try await Task.sleep(for: .seconds(15)) } catch { return }
                if scenePhase == .active {
                    if store.active?.queue.isEmpty == false { await store.sync() }
                    else { store.queueState() }
                }
            }
        }
        .onChange(of: scenePhase) { _, phase in if phase == .active { Task { await store.refresh() } } }
        .onChange(of: confirmation) { _, value in if value != nil { detent = .medium } }
    }
    private var timer: String {
        guard store.active?.server.mode == .full_exam else { return "Тренировка" }
        guard let n = store.remainingSeconds else { return "––:––" }
        return String(format: "%02d:%02d", n / 60, n % 60)
    }
    private func panel(expanded: Bool) -> some View {
        VStack(spacing: 0) {
            if let confirmation {
                confirmationContent(confirmation)
            } else {
                if expanded {
                    HStack {
                        Text(store.syncMessage).font(.caption).foregroundStyle(.secondary)
                        Spacer()
                        Button { auxiliary = .navigator } label: { Image(systemName: "square.grid.3x3").frame(width: 44, height: 44) }.accessibilityLabel("Все вопросы")
                        Button { confirmation = .submit } label: { Image(systemName: "checkmark.circle").frame(width: 44, height: 44) }.accessibilityLabel("Завершить Reading").accessibilityIdentifier("reading.finish").disabled(store.isSubmitting)
                        Button { Task { await store.reconnect() } } label: { Image(systemName: "arrow.triangle.2.circlepath").frame(width: 44, height: 44) }.accessibilityLabel("Синхронизировать ответы")
                    }.padding(.horizontal)
                    if store.active?.conflict == true {
                        Text("Есть изменения с другого устройства. Выбери, какие ответы оставить.").font(.subheadline).padding(.horizontal)
                        HStack { Button("Серверные") { store.resolveConflict(keepLocal: false) }; Spacer(); Button("Мои локальные") { store.resolveConflict(keepLocal: true) } }.padding()
                    }
                    if store.diskError { Button("Повторить локальное сохранение") { store.retryLocalSave() } }
                    if let error = store.errorMessage { Text(error).font(.caption).foregroundStyle(.secondary).padding(.horizontal) }
                }
                ReadingQuestionPanel(store: store, expanded: expanded) { detent = detent == .medium ? .large : .medium }
            }
        }
        .sheet(item: $auxiliary) { item in
            NavigationStack {
                Group { if item == .navigator { ReadingNavigator(store: store) { auxiliary = nil; detent = .medium } } else { ReadingSettingsView(store: store) } }
                    .toolbar { Button("Готово") { auxiliary = nil } }
            }
        }
    }
    private func confirmationContent(_ kind: Confirmation) -> some View {
        ScrollView {
        VStack(alignment: .leading, spacing: 20) {
            Text(kind == .exit ? "Выйти из Reading?" : "Завершить Reading?").font(.title2.bold())
            if kind == .exit {
                Text("\(store.syncMessage) Таймер полного экзамена продолжает идти.")
                Button("Выйти и сохранить попытку") { dismiss() }.buttonStyle(.borderedProminent).tint(.primary)
                Button("Продолжить") { confirmation = nil }
            } else {
                Text("\(store.active.map { $0.exam.questions.count - $0.unanswered } ?? 0)/\(store.active?.exam.questions.count ?? 40) отвечено. \(store.active?.unanswered ?? 0) без ответа.")
                Text("Сначала отправим ожидающие изменения. При отсутствии сети результат появится после подтверждения сервера.").font(.subheadline).foregroundStyle(.secondary)
                Button("Завершить и проверить") { store.submit(); confirmation = nil }
                    .buttonStyle(.borderedProminent).tint(.primary).disabled(store.isSubmitting)
                Button("Вернуться к вопросам") { confirmation = nil }
            }
        }.padding(24).frame(maxWidth: .infinity, alignment: .leading)
        }
    }

}

struct ReadingNavigator: View {
    @Bindable var store: ReadingStore
    let select: () -> Void
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                ForEach(store.active?.exam.passages ?? []) { passage in
                    Text("Passage \(passage.number)").font(.headline)
                    LazyVGrid(columns: [GridItem(.adaptive(minimum: 44))], spacing: 10) {
                        ForEach(passage.questions) { q in
                            let answered = store.active?.answers[q.id, default: ""].trimmingCharacters(in: .whitespacesAndNewlines).isEmpty == false
                            let marked = store.active?.ui.bookmarks.contains(q.id) == true
                            Button { store.selectQuestion(q); select() } label: {
                                VStack(spacing: 2) { Text("\(q.number)"); if marked { Image(systemName: "bookmark.fill").font(.caption2) } }
                                    .frame(minWidth: 44, minHeight: 44)
                                    .background(answered ? Color.primary.opacity(0.14) : Color.primary.opacity(0.03), in: RoundedRectangle(cornerRadius: 8))
                                    .overlay(RoundedRectangle(cornerRadius: 8).stroke(store.active?.ui.questionID == q.id ? Color.primary : Color.clear, lineWidth: 2))
                            }.buttonStyle(.plain).accessibilityLabel("Question \(q.number), \(answered ? "с ответом" : "без ответа")\(marked ? ", отмечен" : "")")
                        }
                    }
                }
                Text("Отметки для возврата сохраняются только на этом iPhone.").font(.footnote).foregroundStyle(.secondary)
            }.padding()
        }.navigationTitle("Вопросы").navigationBarTitleDisplayMode(.inline)
    }
}
struct ReadingSettingsView: View {
    @Bindable var store: ReadingStore
    var body: some View {
        Form {
            Picker("Режим чтения", selection: Binding(get: { store.preferences.theme }, set: { store.setPreferences(theme: $0) })) {
                Text("Светлый").tag(ReadingTheme.light); Text("Сепия").tag(ReadingTheme.sepia); Text("Тёмный").tag(ReadingTheme.dark)
            }.pickerStyle(.segmented)
            Stepper("Размер текста: \(Int(store.preferences.fontSize))", value: Binding(get: { store.preferences.fontSize }, set: { store.setPreferences(size: $0) }), in: 16...30, step: 1)
            Text("Выдели текст и выбери маркер в системном меню. Настройки действуют только в Reading.").font(.footnote)
        }.navigationTitle("Чтение").navigationBarTitleDisplayMode(.inline)
    }
}

struct ReadingResultsView: View {
    @Bindable var store: ReadingStore
    let result: ReadingResult
    @Environment(\.dismiss) private var dismiss
    var body: some View {
        List {
            Section {
                Text(store.active?.exam.title ?? "Reading").font(.headline)
                if store.active?.server.mode == .full_exam, let band = result.estimated_band {
                    Text(String(format: "%.1f", band)).font(.system(size: 64, weight: .semibold, design: .rounded)).accessibilityLabel("Примерный IELTS Band \(band)")
                    Text("Estimated IELTS Academic Reading Band").font(.subheadline).foregroundStyle(.secondary)
                }
                Text("\(result.raw_score) / \(result.total_questions) верно").font(.title2.bold())
                if result.estimated_band == nil {
                    Text(store.active?.server.mode == .passage_practice ? "Точность: \(Int(result.accuracy * 100))%. Band для одного passage не рассчитывается." : "Для этого результата опубликованная ориентировочная шкала не определяет Band.").font(.subheadline).foregroundStyle(.secondary)
                }
                Text("Время: \(result.elapsed_seconds / 60) мин \(result.elapsed_seconds % 60) с").font(.subheadline)
                Text("Ошибок: \(result.incorrect_count) · Пропущено: \(result.unanswered_count)").font(.subheadline)
                if store.active?.server.status == "expired" { Text("Время экзамена закончилось. Проверены ответы, сохранённые на сервере до дедлайна.").font(.footnote) }
            }
            if let r = store.active, !r.excludedLocalAnswers.isEmpty {
                Section("Сохранено только на iPhone") {
                    Text("Эти локальные ответы не вошли в серверный результат.").font(.footnote)
                    ForEach(r.excludedLocalAnswers.keys.sorted(), id: \.self) { qid in
                        Text("Question \(r.exam.questions.first { $0.id == qid }?.number ?? 0): \(r.excludedLocalAnswers[qid] ?? "")")
                    }
                }
            }
            Section("По passages") {
                ForEach(result.per_passage.keys.sorted(), id: \.self) { key in
                    if let stat = result.per_passage[key] { HStack { Text("Passage \(key)"); Spacer(); Text("\(stat.correct)/\(stat.total)") } }
                }
            }
            Section("Типы заданий") {
                ForEach(result.weakest_question_types, id: \.self) { key in
                    if let stat = result.per_question_type[key] {
                        HStack { Text(ReadingQuestionType(rawValue: key)?.title ?? key); Spacer(); Text("\(stat.correct)/\(stat.total)") }
                    }
                }
            }
            if let weakest = result.weakest_question_types.first(where: { key in
                guard let stat = result.per_question_type[key] else { return false }
                return stat.correct < stat.total
            }), let stat = result.per_question_type[weakest] {
                Section("Что улучшить") {
                    Text("\(ReadingQuestionType(rawValue: weakest)?.title ?? weakest): \(stat.correct)/\(stat.total) верно")
                    NavigationLink("Разобрать ошибки этого типа") { ReadingReviewView(store: store, result: result, initialType: weakest) }
                }
            }
            Section {
                NavigationLink("Разобрать ответы") { ReadingReviewView(store: store, result: result) }.accessibilityIdentifier("reading.review")
                Button("В библиотеку") { dismiss() }
            }
        }.navigationTitle("Результат").navigationBarTitleDisplayMode(.inline).navigationBarBackButtonHidden()
    }
}
struct ReadingReviewView: View {
    @Bindable var store: ReadingStore
    let result: ReadingResult
    var initialType: String? = nil
    @State private var typeFilter = ""
    @State private var mistakesOnly = true
    @State private var passageFilter = 0
    var body: some View {
        List {
            Section {
                Picker("Показать", selection: $mistakesOnly) { Text("Ошибки").tag(true); Text("Все").tag(false) }.pickerStyle(.segmented)
                Picker("Passage", selection: $passageFilter) {
                    Text("Все passages").tag(0)
                    ForEach(store.active?.exam.passages ?? []) { Text("Passage \($0.number)").tag($0.number) }
                }
                Picker("Тип задания", selection: $typeFilter) {
                    Text("Все типы").tag("")
                    ForEach(result.per_question_type.keys.sorted(), id: \.self) { key in Text(ReadingQuestionType(rawValue: key)?.title ?? key).tag(key) }
                }
                if let stat = result.per_passage[String(passageFilter)] { Text("\(stat.correct)/\(stat.total) верно") }
            }
            ForEach(result.positions.filter { (!mistakesOnly || !$0.is_correct) && (passageFilter == 0 || $0.passage_number == passageFilter) && (typeFilter.isEmpty || $0.question_type.rawValue == typeFilter) }) { p in
                Section("Question \(p.number) · \(p.question_type.title)") {
                    if let q = store.active?.exam.questions.first(where: { $0.id == p.question_id }) { Text(q.prompt).font(.subheadline) }
                    Text("Ваш ответ: \(p.unanswered ? "Пропущен" : p.user_answer)")
                    Label("Правильный ответ: \(p.correct_answer)", systemImage: p.is_correct ? "checkmark.circle" : "xmark.circle")
                    if let group = store.active?.exam.group(for: p.question_id) {
                        DisclosureGroup("Задание и варианты") {
                            if group.usesImage { ForEach(group.assets) { ReadingAssetView(asset: $0, store: store) } }
                            else { ReadingBlocksView(blocks: group.content_blocks, assets: group.assets, store: store) }
                        }
                    }
                    if let evidence = p.evidence?.quote, !evidence.isEmpty { Text(evidence).font(.subheadline).textSelection(.enabled) }
                    if let passage = store.active?.exam.passages.first(where: { $0.number == p.passage_number }) {
                        NavigationLink("Открыть Passage \(p.passage_number)") {
                            ReadingPassageView(store: store, passage: passage, review: true).navigationTitle(passage.title).navigationBarTitleDisplayMode(.inline)
                                .onAppear {
                                    if let quote = p.evidence?.quote, let index = passage.content.firstIndex(where: { $0.text.contains(quote) }) {
                                        store.updateUI { $0.passageAnchors[passage.id] = "\(passage.id)-\(index)" }
                                    }
                                }
                        }
                    }
                }
            }
        }.navigationTitle("Разбор ответов").navigationBarTitleDisplayMode(.inline)
            .onAppear { if let initialType { typeFilter = initialType } }
    }
}
