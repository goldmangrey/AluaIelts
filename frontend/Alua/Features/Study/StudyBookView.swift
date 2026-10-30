import SwiftUI

enum BookMode: String, CaseIterable, Identifiable {
    case days = "По дням", topics = "По темам", words = "Мои слова"
    var id: Self { self }
}
struct StudyBook: View {
    let store: StudyStore
    @State private var mode = BookMode.days
    @State private var search = ""
    @State private var filter = "all"
    @Environment(\.dynamicTypeSize) private var textSize
    var body: some View {
        Group {
            if let s = store.disk.snapshot {
                List {
                    Section {
                        Text("IELTS Vocabulary · 1 500 единиц").font(.subheadline).foregroundStyle(AluaColors.secondaryText)
                        if textSize.isAccessibilitySize {
                            Picker("Представление", selection: $mode) { modes }.pickerStyle(.menu)
                        } else { Picker("Представление", selection: $mode) { modes }.pickerStyle(.segmented) }
                    }.listRowSeparator(.hidden)
                    if !search.isEmpty || mode == .words {
                        Section {
                            Picker("Показать", selection: $filter) {
                                Text("Все").tag("all"); Text("Нужно повторить").tag("review_due")
                                Text("Закреплены").tag("retained"); Text("Скрытые").tag("hidden")
                            }.frame(minHeight: 44)
                            let words = StudyPresentation.words(s.book, query: search, filter: filter)
                            if words.isEmpty {
                                ContentUnavailableView(search.isEmpty ? "Здесь появятся ваши слова" : "Ничего не найдено", systemImage: search.isEmpty ? "book" : "magnifyingglass", description: Text(search.isEmpty ? "Изучите первые карточки или измените фильтр." : "Попробуйте другое слово или перевод."))
                            }
                            ForEach(words) { card in StudyBookLink(store: store, card: card) }
                        }
                    } else if mode == .days {
                        let p = StudyPresentation(snapshot: s)
                        ForEach(s.days) { day in
                            let count = p.processed(day)
                            NavigationLink { StudyWords(store: store, title: "День \(day.day)", dayID: day.day) } label: {
                                VStack(alignment: .leading, spacing: 8) {
                                    HStack(alignment: .firstTextBaseline) {
                                        Text("День \(day.day)").font(.headline)
                                        Spacer()
                                        Text("\(count)/30").font(.subheadline.monospacedDigit()).foregroundStyle(AluaColors.secondaryText)
                                    }
                                    Text(day.title).font(.body).foregroundStyle(AluaColors.secondaryText)
                                    Text(count == 30 ? "Завершён" : day.day == s.day && s.available ? "Текущий день" : "Ещё не начат")
                                        .font(.footnote).foregroundStyle(AluaColors.secondaryText)
                                }.padding(.vertical, 10).accessibilityElement(children: .combine)
                            }
                        }
                    } else {
                        ForEach(1...50, id: \.self) { topic in
                            let count = s.book.filter { $0.topic_ids.contains(topic) }.count
                            NavigationLink { StudyWords(store: store, title: s.topics[String(topic)] ?? "Тема", topicID: topic) } label: {
                                VStack(alignment: .leading, spacing: 7) {
                                    Text(s.topics[String(topic)] ?? "Тема \(topic)").font(.headline)
                                    Text("В вашей книге: \(count)").font(.subheadline).foregroundStyle(AluaColors.secondaryText)
                                }.padding(.vertical, 10).accessibilityElement(children: .combine)
                            }
                        }
                    }
                    if !store.disk.queue.isEmpty || store.error != nil { StudySyncNotice(store: store).listRowSeparator(.hidden) }
                }.listStyle(.plain).scrollDismissesKeyboard(.interactively)
            } else { StudyLoading(store: store) }
        }
        .navigationTitle("Моя книга")
        .searchable(text: $search, prompt: "Слово или перевод")
        .autocorrectionDisabled().textInputAutocapitalization(.never)
        .refreshable { await store.sync() }
    }
    @ViewBuilder private var modes: some View {
        ForEach(BookMode.allCases) { value in Text(value.rawValue).tag(value) }
    }
}
struct StudyWords: View {
    let store: StudyStore
    var title = "Мои слова"
    var dayID: Int? = nil
    var topicID: Int? = nil
    @State private var search = ""
    private var cards: [StudyCard] {
        guard let s = store.disk.snapshot else { return [] }
        let ids = dayID.flatMap { n in s.days.first { $0.day == n }.map { Set($0.ids) } }
        return StudyPresentation.words(s.book.filter { card in
            (ids == nil || ids!.contains(card.id)) && (topicID == nil || card.topic_ids.contains(topicID!))
        }, query: search)
    }
    var body: some View {
        List {
            if cards.isEmpty {
                ContentUnavailableView(search.isEmpty ? "Пока нет изученных карточек" : "Ничего не найдено", systemImage: "book", description: Text("Слова появятся здесь по мере изучения. Они останутся доступны и после завершения курса."))
            } else {
                Text("Доступно карточек: \(cards.count)").font(.subheadline).foregroundStyle(AluaColors.secondaryText)
                ForEach(cards) { card in StudyBookLink(store: store, card: card) }
            }
        }.listStyle(.plain).navigationTitle(title).navigationBarTitleDisplayMode(.inline)
            .searchable(text: $search, prompt: "Слово или перевод").autocorrectionDisabled()
            .textInputAutocapitalization(.never).scrollDismissesKeyboard(.interactively)
    }
}
struct StudyBookLink: View {
    let store: StudyStore
    let card: StudyCard
    var body: some View {
        NavigationLink { StudyCardDetail(store: store, original: card) } label: {
            VStack(alignment: .leading, spacing: 6) {
                Text(card.term).font(.headline).foregroundStyle(AluaColors.primaryText)
                Text(card.translation_ru).font(.body).foregroundStyle(AluaColors.secondaryText)
                Text(StudyPresentation.status(card.status)).font(.footnote).foregroundStyle(AluaColors.secondaryText)
            }.padding(.vertical, 8).frame(minHeight: 44).accessibilityElement(children: .combine)
        }.accessibilityIdentifier("book.card.\(card.id)")
    }
}
struct StudyCardDetail: View {
    let store: StudyStore
    let original: StudyCard
    @State private var review = false
    private var card: StudyCard { store.disk.snapshot?.book.first { $0.id == original.id } ?? original }
    private var topic: String {
        card.topic_ids.compactMap { store.disk.snapshot?.topics[String($0)] }.joined(separator: " · ")
    }
    var body: some View {
        AluaPage {
            Text(StudyPresentation.status(card.status)).font(.subheadline.weight(.medium)).foregroundStyle(AluaColors.secondaryText)
            StudyDetails(card: card, topic: topic)
            Button("Повторить") { review = true }.buttonStyle(AluaPrimaryStyle())
            if card.status == "hidden" {
                Button("Восстановить") { action("unhide") }.frame(maxWidth: .infinity, minHeight: 44)
            } else {
                Menu { Button("Скрыть", systemImage: "eye.slash") { action("hide") } } label: {
                    Label("Другие действия", systemImage: "ellipsis").frame(minHeight: 44)
                }
            }
            StudyReport(store: store, card: card)
            StudySyncNotice(store: store)
        }.navigationBarTitleDisplayMode(.inline)
            .fullScreenCover(isPresented: $review) { NavigationStack { StudyReviews(store: store, single: card) } }
    }
    private func action(_ value: String) { store.record(card, action: value); Task { await store.sync() } }
}
struct StudyReport: View {
    let store: StudyStore
    let card: StudyCard
    @State private var showing = false
    @State private var comment = ""
    var body: some View {
        Button("Ошибка в карточке") { showing = true }.frame(minHeight: 44)
            .alert("Что исправить?", isPresented: $showing) {
                TextField("Перевод, пример или другое", text: $comment)
                Button("Отправить") { store.record(card, action: "report", comment: comment); comment = ""; Task { await store.sync() } }
                Button("Отмена", role: .cancel) {}
            }
    }
}
