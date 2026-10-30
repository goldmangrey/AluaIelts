import SwiftUI

struct StudyProgressView: View {
    let store: StudyStore
    let quality: LearningQualityService
    @State private var placement: Placement?
    @State private var grammar: [GrammarTopicSummary.Topic] = []
    @State private var qualityError = false
    var body: some View {
        AluaPage {
            if let s = store.disk.snapshot {
                let p = StudyPresentation(snapshot: s)
                VStack(alignment: .leading, spacing: 20) {
                    Text("Ваш путь в учебнике").font(.title2.weight(.semibold))
                    metric("Пройдено дней", "\(p.completedDays) из 50")
                    AluaProgressBar(value: Double(p.completedDays) / 50)
                    metric("Впервые изучено", "\(p.introduced) из 1 500")
                    metric("Закреплено повторениями", "\(p.retained)")
                    metric("Ожидают повторения", "\(p.due)")
                    Text("Пройденная карточка ещё не означает устойчивое знание. Закрепление подтверждается успешными повторениями.")
                        .font(.footnote).foregroundStyle(AluaColors.secondaryText)
                }
                Divider()
                if p.introduced == 0 {
                    Text("Начните с первых 10 карточек. Здесь появится ваш прогресс — без оценок и сравнения с другими.").foregroundStyle(AluaColors.secondaryText)
                }
                VStack(alignment: .leading, spacing: 16) {
                    Text("По темам").font(.title2.weight(.semibold))
                    let studied = (1...50).filter { t in s.book.contains { $0.topic_ids.contains(t) } }
                    if studied.isEmpty { Text("Пока нет изученных тем.").foregroundStyle(AluaColors.secondaryText) }
                    ForEach(studied, id: \.self) { topic in
                        let cards = s.book.filter { $0.topic_ids.contains(topic) }
                        NavigationLink { StudyWords(store: store, title: s.topics[String(topic)] ?? "Тема", topicID: topic) } label: {
                            AluaRouteRow(title: s.topics[String(topic)] ?? "Тема", subtitle: "Впервые изучено: \(cards.count) · закреплено: \(cards.filter { $0.status == "retained" }.count)")
                        }.buttonStyle(.plain)
                    }
                }
                Divider()
                VStack(alignment: .leading, spacing: 16) {
                    Text("Стартовая проверка").font(.title2.weight(.semibold))
                    if let result = placement?.result {
                        Text("Сложность на старте · \(result.difficulty)").font(.headline)
                        Text(result.notice).font(.subheadline).foregroundStyle(AluaColors.secondaryText)
                    } else { Text("Пройдите 12 вопросов, чтобы выбрать стартовую сложность. Диагностика не обязательна для занятий.").foregroundStyle(AluaColors.secondaryText) }
                    NavigationLink(placement?.result == nil ? "Открыть проверку" : "Посмотреть результат") { DiagnosticView(service: quality) }.frame(minHeight: 44)
                }
                VStack(alignment: .leading, spacing: 16) {
                    Text("Где нужна практика").font(.title2.weight(.semibold))
                    let weak = grammar.filter(\.weak)
                    if weak.isEmpty { Text("Пока недостаточно данных для выделения слабых тем. Ожидающее повторение само по себе не означает слабое знание.").foregroundStyle(AluaColors.secondaryText) }
                    ForEach(weak) { topic in
                        Text(topic.title).font(.headline)
                        Text("Ошибок: \(topic.errors) из \(topic.attempts) ответов").foregroundStyle(AluaColors.secondaryText)
                    }
                    if qualityError { Button("Повторить загрузку диагностики") { Task { await loadQuality() } }.frame(minHeight: 44) }
                }
                StudySyncNotice(store: store)
            } else { StudyLoading(store: store) }
        }.navigationTitle("Прогресс").task { await loadQuality() }
            .refreshable { await store.sync(); await loadQuality() }
    }
    private func metric(_ title: String, _ value: String) -> some View {
        ViewThatFits(in: .horizontal) {
            HStack(alignment: .firstTextBaseline) { Text(title).foregroundStyle(AluaColors.secondaryText); Spacer(minLength: 20); Text(value).font(.title2.weight(.semibold)).monospacedDigit() }
            VStack(alignment: .leading, spacing: 6) { Text(title).foregroundStyle(AluaColors.secondaryText); Text(value).font(.title2.weight(.semibold)).monospacedDigit() }
        }.accessibilityElement(children: .combine)
    }
    private func loadQuality() async {
        do { placement = try await quality.placement(); grammar = try await quality.topics().topics; qualityError = false }
        catch { qualityError = true }
    }
}
