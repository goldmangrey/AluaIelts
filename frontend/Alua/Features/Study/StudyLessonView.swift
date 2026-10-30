import SwiftUI

struct StudyHome: View {
    let store: StudyStore
    var onOpenBook: (() -> Void)? = nil
    @State private var lesson = false
    @State private var review = false
    @ScaledMetric(relativeTo: .largeTitle) private var numberSize = 56
    var body: some View {
        Group {
            if let s = store.disk.snapshot {
                let p = StudyPresentation(snapshot: s, queue: store.disk.queue)
                let count = p.displayDay.map(p.processed) ?? s.processed
                VStack(alignment: .leading, spacing: 28) {
                    VStack(alignment: .leading, spacing: 8) {
                        Text(s.finished ? "Все 50 дней пройдены" : "День \(p.displayDay?.day ?? s.day) из 50").font(.largeTitle.weight(.semibold))
                        Text(p.displayDay?.title ?? s.title).font(.body).foregroundStyle(AluaColors.secondaryText)
                    }
                    VStack(alignment: .leading, spacing: 20) {
                        Text("Сегодняшние слова").font(.headline)
                        Text("\(count) / 30").font(.system(size: numberSize, weight: .semibold)).monospacedDigit()
                            .accessibilityLabel("Обработано \(count) из 30 новых единиц")
                        AluaProgressBar(value: Double(count) / 30)
                        if s.available && !s.cards.isEmpty {
                            Button(count == 0 ? "Начать изучение" : "Продолжить изучение") { lesson = true }
                                .buttonStyle(AluaPrimaryStyle()).accessibilityIdentifier("study.start")
                            Text("Три подхода по 10. Можно остановиться в любой момент.").font(.footnote).foregroundStyle(AluaColors.secondaryText)
                        } else {
                            Text(s.finished ? "Ваш учебник остаётся с вами." : "Сегодняшние 30 слов пройдены").font(.headline)
                            Text(s.finished ? "Возвращайтесь к книге и повторяйте изученное." : "Следующая подборка откроется завтра. Повторения доступны уже сейчас.").foregroundStyle(AluaColors.secondaryText)
                        }
                    }.padding(24).background(AluaColors.cardBackground, in: RoundedRectangle(cornerRadius: 20))
                    VStack(spacing: 0) {
                        Button { review = true } label: {
                            AluaRouteRow(title: "Повторение", subtitle: p.due == 0 ? "Сейчас нет ожидающих карточек" : "Ожидают: \(p.due) · подход до 10 карточек", symbol: "arrow.clockwise")
                        }.buttonStyle(.plain)
                        Divider()
                        if let onOpenBook {
                            Button(action: onOpenBook) { AluaRouteRow(title: "Моя книга", subtitle: "Всё, к чему можно вернуться", symbol: "book.closed") }.buttonStyle(.plain)
                        } else {
                            NavigationLink { StudyBook(store: store) } label: { AluaRouteRow(title: "Моя книга", symbol: "book.closed") }.buttonStyle(.plain)
                        }
                    }
                    StudySyncNotice(store: store)
                }
            } else { StudyLoading(store: store) }
        }
        .fullScreenCover(isPresented: $lesson) { NavigationStack { StudyLesson(store: store) } }
        .fullScreenCover(isPresented: $review) { NavigationStack { StudyReviews(store: store) } }
    }
}

struct StudyDetails: View {
    let card: StudyCard
    let topic: String
    var body: some View {
        VStack(alignment: .leading, spacing: 28) {
            VStack(alignment: .leading, spacing: 12) {
                if !topic.isEmpty { Text(topic).font(.subheadline).foregroundStyle(AluaColors.secondaryText) }
                Text(card.term).font(.largeTitle.weight(.semibold)).fixedSize(horizontal: false, vertical: true)
                    .accessibilityAddTraits(.isHeader).textSelection(.enabled)
                Text(card.translation_ru).font(.title2).fixedSize(horizontal: false, vertical: true)
            }
            if !card.definition_en.isEmpty { Text(card.definition_en).font(.body).foregroundStyle(AluaColors.secondaryText) }
            if !card.example_en.isEmpty {
                VStack(alignment: .leading, spacing: 12) {
                    Text("В контексте").font(.subheadline.weight(.semibold)).foregroundStyle(AluaColors.secondaryText)
                    Text(card.example_en).font(.title3).fixedSize(horizontal: false, vertical: true)
                    if !card.example_ru.isEmpty { Text(card.example_ru).font(.body).foregroundStyle(AluaColors.secondaryText) }
                }.padding(20).frame(maxWidth: .infinity, alignment: .leading)
                    .background(AluaColors.cardBackground, in: RoundedRectangle(cornerRadius: 16))
            }
            if !card.usage_note_ru.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Обратите внимание").font(.subheadline.weight(.semibold))
                    Text(card.usage_note_ru).font(.body).foregroundStyle(AluaColors.secondaryText)
                }
            }
        }
    }
}

struct StudyLesson: View {
    let store: StudyStore
    @Environment(\.dismiss) private var dismiss
    @State private var day: StudyDay?
    @State private var pausedAt: Int?
    @State private var localCount = 0
    @State private var report = false
    @State private var comment = ""
    private var count: Int {
        guard let day, let s = store.disk.snapshot else { return localCount }
        return max(localCount, StudyPresentation(snapshot: s).processed(day))
    }
    var body: some View {
        AluaPage(resetKey: store.disk.snapshot?.cards.first?.id) {
            VStack(alignment: .leading, spacing: 14) {
                Text("День \(day?.day ?? store.disk.snapshot?.day ?? 1) · \(count) из 30")
                    .font(.subheadline).foregroundStyle(AluaColors.secondaryText)
                AluaProgressBar(value: Double(count) / 30)
            }
            if count >= 30 { completion }
            else if let pausedAt { pause(pausedAt) }
            else if let s = store.disk.snapshot, s.available, let card = s.cards.first {
                Text("Подход \(count / 10 + 1) из 3").font(.subheadline).foregroundStyle(AluaColors.secondaryText)
                StudyDetails(card: card, topic: s.topics[String(card.primary_topic_id)] ?? "")
                Button("Дальше") { act(card, "next") }.buttonStyle(AluaPrimaryStyle()).accessibilityIdentifier("lesson.next")
                ViewThatFits(in: .horizontal) {
                    HStack { Button("Уже знаю") { act(card, "known") }; Spacer(); Button("Не знаю") { act(card, "unknown") } }
                    VStack(alignment: .leading) { Button("Уже знаю") { act(card, "known") }; Button("Не знаю") { act(card, "unknown") } }
                }.buttonStyle(.bordered).controlSize(.large)
                Menu {
                    Button("Скрыть", systemImage: "eye.slash") { act(card, "hide") }
                    Button("Ошибка в карточке", systemImage: "flag") { report = true }
                } label: { Label("Другие действия", systemImage: "ellipsis").frame(minHeight: 44) }
                .alert("Ошибка в карточке", isPresented: $report) {
                    TextField("Что нужно исправить?", text: $comment)
                    Button("Отправить") { store.record(card, action: "report", comment: comment); comment = ""; Task { await store.sync() } }
                    Button("Отмена", role: .cancel) {}
                }
            } else { StudyLoading(store: store) }
            StudySyncNotice(store: store)
        }
        .navigationBarTitleDisplayMode(.inline)
        .toolbar { ToolbarItem(placement: .topBarLeading) { AluaCloseButton() } }
        .onAppear {
            if day == nil, let s = store.disk.snapshot {
                day = s.days.first { $0.day == s.day }; localCount = s.processed
            }
        }
    }
    private func pause(_ n: Int) -> some View {
        VStack(alignment: .leading, spacing: 24) {
            Text("Подход завершён").font(.largeTitle.weight(.semibold))
            Text("\(n) из 30 карточек обработано. Можно продолжить сейчас или вернуться позже.").font(.title3).foregroundStyle(AluaColors.secondaryText)
            Button("Продолжить") { pausedAt = nil }.buttonStyle(AluaPrimaryStyle())
            Button("Закончить пока") { dismiss() }.frame(maxWidth: .infinity, minHeight: 44)
            if let s = store.disk.snapshot, let day, day.ids.indices.contains(n - 1),
               let last = s.book.first(where: { $0.id == day.ids[n - 1] }) {
                NavigationLink("Короткая проверка") { StudyReviews(store: store, single: last) }.frame(minHeight: 44)
            }
        }
    }
    private var completion: some View {
        VStack(alignment: .leading, spacing: 24) {
            Text("День завершён").font(.largeTitle.weight(.semibold))
            Text("30 единиц пройдено в сегодняшней подборке.").font(.title2)
            Text("Знакомство — первый шаг. Последующие повторения покажут, что закрепилось.").foregroundStyle(AluaColors.secondaryText)
            if let s = store.disk.snapshot {
                if s.review_due > 0 { Text("Ожидают повторения: \(s.review_due)").font(.headline) }
                if let day {
                    NavigationLink { StudyWords(store: store, title: "День \(day.day)", dayID: day.day) } label: { Text("Открыть в моей книге") }.buttonStyle(AluaPrimaryStyle())
                }
            }
            Button("Закрыть урок") { dismiss() }.frame(maxWidth: .infinity, minHeight: 44)
        }
    }
    private func act(_ card: StudyCard, _ action: String) {
        guard store.disk.snapshot?.cards.first?.id == card.id else { return }
        let before = store.disk.queue.count
        store.record(card, action: action)
        guard store.disk.queue.count > before else { return }
        localCount = store.disk.snapshot?.processed ?? localCount
        if localCount == 10 || localCount == 20 { pausedAt = localCount }
        Task { await store.sync() }
    }
}

struct StudyReviews: View {
    let store: StudyStore
    var single: StudyCard? = nil
    var showsCloseButton = true
    @Environment(\.dismiss) private var dismiss
    @State private var cards: [StudyCard] = []
    @State private var index = 0
    @State private var selected: String?
    @State private var correct: Bool?
    @State private var loaded = false
    var body: some View {
        AluaPage(resetKey: String(index)) {
            if index < cards.count {
                let card = cards[index]
                VStack(alignment: .leading, spacing: 14) {
                    Text("Повторение · \(index + 1) из \(cards.count)").font(.subheadline).foregroundStyle(AluaColors.secondaryText)
                    AluaProgressBar(value: Double(index) / Double(max(1, cards.count)))
                }
                Text("Выберите значение").font(.subheadline).foregroundStyle(AluaColors.secondaryText)
                Text(card.term).font(.largeTitle.weight(.semibold))
                if let correct {
                    VStack(alignment: .leading, spacing: 14) {
                        Label(correct ? "Верно" : "Повторим ещё раз", systemImage: correct ? "checkmark.circle" : "arrow.clockwise")
                            .font(.headline).foregroundStyle(correct ? Color.green : Color.primary)
                        Text(card.translation_ru).font(.title2)
                        if !card.example_en.isEmpty { Text(card.example_en).foregroundStyle(AluaColors.secondaryText) }
                    }.accessibilityElement(children: .combine)
                    Button("Дальше") { index += 1; self.correct = nil; selected = nil }.buttonStyle(AluaPrimaryStyle())
                } else {
                    VStack(spacing: 12) {
                        ForEach(options(card), id: \.self) { option in
                            StudyChoice(text: option, selected: selected == option) { selected = option }
                        }
                    }
                    Button("Проверить") { respond(card, selected) }.buttonStyle(AluaPrimaryStyle()).disabled(selected == nil)
                    Button("Не знаю") { respond(card, nil) }.frame(maxWidth: .infinity, minHeight: 44)
                }
            } else if loaded {
                Text(cards.isEmpty ? "Пока нечего повторять" : "Повторение завершено").font(.largeTitle.weight(.semibold))
                Text(cards.isEmpty ? "Вернитесь позже или откройте любую изученную карточку в книге." : "Ответы сохранены. Расписание следующих повторений учитывает результат.").foregroundStyle(AluaColors.secondaryText)
                if !cards.isEmpty { Text("\(cards.count) карточек в этом подходе").font(.headline) }
                Button("Готово") { dismiss() }.buttonStyle(AluaPrimaryStyle())
            }
            StudySyncNotice(store: store)
        }
        .toolbar { if showsCloseButton { ToolbarItem(placement: .topBarLeading) { AluaCloseButton() } } }
        .navigationBarBackButtonHidden().navigationBarTitleDisplayMode(.inline)
        .onAppear {
            guard !loaded else { return }
            cards = single.map { [$0] } ?? Array((store.disk.snapshot?.book ?? []).filter { card in
                card.status == "review_due" && !store.disk.queue.contains { $0.item_id == card.id }
            }.prefix(10))
            loaded = true
        }
    }
    private func options(_ card: StudyCard) -> [String] {
        let others = ((store.disk.snapshot?.book ?? []) + (store.disk.snapshot?.cards ?? [])).filter { $0.translation_ru != card.translation_ru }.prefix(3).map(\.translation_ru)
        return Array(Set(others + [card.translation_ru])).sorted()
    }
    private func respond(_ card: StudyCard, _ answer: String?) {
        guard correct == nil else { return }
        let before = store.disk.queue.count
        store.record(card, action: "review", answer: answer)
        guard store.disk.queue.count > before else { return }
        correct = answer == card.translation_ru
        Task { await store.sync() }
    }
}
