import SwiftUI

struct DiagnosticView: View {
    let service: LearningQualityService
    @State private var placement: Placement?
    @State private var selected: Int?
    @State private var busy = false
    @State private var error: String?
    var body: some View {
        AluaPage(resetKey: placement?.question.map { String($0.id) }) {
            if let placement {
                if let question = placement.question {
                    VStack(alignment: .leading, spacing: 14) {
                        Text("Вопрос \(placement.answered + 1) из \(placement.total)").font(.subheadline).foregroundStyle(AluaColors.secondaryText)
                        AluaProgressBar(value: Double(placement.answered) / Double(placement.total))
                    }
                    Text(question.prompt).font(.title2.weight(.semibold))
                    VStack(spacing: 12) {
                        ForEach(question.options.indices, id: \.self) { index in
                            StudyChoice(text: question.options[index], selected: selected == index) { selected = index }.disabled(busy)
                        }
                    }
                    Button(busy ? "Сохраняем…" : "Дальше") { Task { await answer(question.id, selected) } }
                        .buttonStyle(AluaPrimaryStyle()).disabled(busy || selected == nil)
                    Button("Не знаю") { Task { await answer(question.id, nil) } }.frame(maxWidth: .infinity, minHeight: 44).disabled(busy)
                    Text("Можно остановиться и вернуться позже. Ответы сохраняются после отправки.").font(.footnote).foregroundStyle(AluaColors.secondaryText)
                } else if let result = placement.result {
                    Text("Отправная точка").font(.largeTitle.weight(.semibold))
                    Text(result.difficulty).font(.largeTitle.weight(.bold))
                    Text(result.notice).font(.title3).foregroundStyle(AluaColors.secondaryText)
                    Text("Результат определяет стартовую сложность до начала курса. Уже начатая программа сохраняется.").foregroundStyle(AluaColors.secondaryText)
                    if !result.gaps.isEmpty {
                        Divider()
                        Text("Темы для практики").font(.headline)
                        ForEach(result.gaps, id: \.self) { Text(topicTitle($0)).font(.body) }
                    }
                }
            } else if error == nil { SwiftUI.ProgressView("Загружаем вопросы…") }
            if let error {
                Label(error, systemImage: "wifi.slash").foregroundStyle(AluaColors.secondaryText)
                Button("Повторить загрузку") { Task { await load() } }.frame(minHeight: 44)
            }
        }.navigationTitle("Стартовая проверка").navigationBarTitleDisplayMode(.inline).task { await load() }
    }
    private func topicTitle(_ id: String) -> String {
        ["vocabulary_daily": "Повседневная лексика", "present_simple": "Present Simple",
         "past_simple": "Past Simple", "vocabulary_context": "Лексика в контексте",
         "present_perfect": "Present Perfect", "conditionals": "Условные предложения",
         "reading_detail": "Детали текста", "vocabulary_collocation": "Сочетания слов",
         "past_perfect": "Past Perfect", "reading_inference": "Выводы из текста",
         "inversion": "Инверсия", "vocabulary_nuance": "Оттенки значений"][id] ?? "Дополнительная практика"
    }
    private func load() async {
        do { placement = try await service.placement(); error = nil }
        catch { self.error = "Не удалось загрузить. Проверьте соединение." }
    }
    private func answer(_ id: Int, _ choice: Int?) async {
        guard !busy else { return }; busy = true; defer { busy = false }
        do { placement = try await service.answer(id: id, choice: choice); selected = nil; error = nil }
        catch { self.error = "Ответ не подтверждён. Повторите отправку или загрузите сохранённое состояние." }
    }
}
