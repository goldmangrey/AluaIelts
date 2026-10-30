import SwiftUI

struct CardActionsView: View {
    let itemID: String
    let service: LearningQualityService
    var onSaved: () async -> Void = {}
    @State private var message: String?
    @State private var busy = false
    @State private var reporting = false
    @State private var comment = ""
    @State private var type = "translation"
    @State private var reportID = UUID()
    var body: some View {
        VStack(alignment: .leading) {
            HStack {
                Button("Уже знаю") { Task { await act("known") } }
                Button("Скрыть") { Task { await act("hide") } }
                Button("Ошибка в карточке") { reporting = true }
            }.font(.caption).disabled(busy)
            if let message { Text(message).font(.caption) }
        }.sheet(isPresented: $reporting) {
            NavigationStack {
                Form {
                    Picker("Тип ошибки", selection: $type) {
                        Text("Перевод").tag("translation"); Text("Пример").tag("example")
                        Text("Грамматика").tag("grammar"); Text("Другое").tag("other")
                    }
                    TextField("Комментарий (необязательно)", text: $comment, axis: .vertical)
                    Button("Отправить") { Task { await act("report") } }.disabled(busy || comment.count > 1000)
                    if let message { Text(message) }
                }.navigationTitle("Ошибка в карточке")
                    .toolbar { Button("Закрыть") { reporting = false } }
            }
        }
    }
    private func act(_ action: String) async {
        guard !busy else { return }; busy = true; defer { busy = false }
        do {
            try await service.action(itemID: itemID, action: action, eventID: action == "report" ? reportID : UUID(), type: type, comment: comment)
            message = action == "known" ? "Добавлено в очередь проверки. Освоение не засчитано." : action == "hide" ? "Карточка скрыта. История сохранена." : "Сообщение сохранено."
            if action == "report" { reporting = false; reportID = UUID(); comment = "" }
            await onSaved()
        } catch { message = "Не сохранено. Проверьте соединение и повторите." }
    }
}
