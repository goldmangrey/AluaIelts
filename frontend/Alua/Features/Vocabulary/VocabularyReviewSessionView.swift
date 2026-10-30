import AVFoundation
import SwiftUI

/// Legacy review links retain their existing card types and rating contract.
struct VocabularyReviewSessionView: View {
    let sessionID: String
    let store: VocabularyLearningStore
    @Environment(\.dismiss) private var dismiss
    @State private var index = 0
    @State private var revealed = false
    @State private var rating: VocabularyReviewRating?
    @State private var ratings: [VocabularyReviewRating: Int] = [:]
    @State private var eventIDs: [String: UUID] = [:]
    @State private var isSubmitting = false
    private let speech = VocabularySpeechPlayer()
    var body: some View {
        Group {
            if store.isLoading, store.session?.sessionID != sessionID { SwiftUI.ProgressView("Загружаем повторение…") }
            else if let session = store.session, session.sessionID == sessionID {
                if index < session.cards.count { review(session) }
                else {
                    AluaPage {
                        Text("Повторение завершено").font(.largeTitle.weight(.semibold))
                        Text("Отправлено ответов: \(ratings.values.reduce(0, +))").font(.title2)
                        Text("Следующие повторения помогут закрепить изученное.").foregroundStyle(AluaColors.secondaryText)
                        Button("Готово") { dismiss() }.buttonStyle(AluaPrimaryStyle())
                    }
                }
            } else {
                ContentUnavailableView("Повторение недоступно", systemImage: "wifi.slash", description: Text(store.errorMessage ?? "Подключитесь к сети, чтобы загрузить вопросы."))
            }
        }.navigationTitle("Повторение").navigationBarTitleDisplayMode(.inline)
        .task { if store.session?.sessionID != sessionID { await store.loadSession(id: sessionID) } }
        .onDisappear { speech.stop() }
    }
    private func review(_ session: VocabularyReviewSession) -> some View {
        let card = session.cards[index]
        return AluaPage(resetKey: card.id) {
            Text("\(index + 1) из \(session.cards.count)").font(.subheadline).foregroundStyle(AluaColors.secondaryText)
            AluaProgressBar(value: Double(index) / Double(max(session.cards.count, 1)))
            Text(card.prompt).font(.subheadline).foregroundStyle(AluaColors.secondaryText)
            Text(card.frontTerm).font(.largeTitle.weight(.semibold))
            if revealed {
                Divider()
                Text(card.item.term).font(.title2.weight(.semibold))
                Text(card.item.translationRU).font(.title2)
                if let definition = card.item.definitionEN { Text(definition).foregroundStyle(AluaColors.secondaryText) }
                ForEach(Array(card.item.examples.prefix(2)), id: \.self) { Text($0).font(.body) }
                if let usage = card.item.usageRU { Text(usage).foregroundStyle(AluaColors.secondaryText) }
                Button { speech.speak(card.item.term) } label: { Label("Произнести", systemImage: "speaker.wave.2").frame(minHeight: 44) }
                Text("Как удалось вспомнить?").font(.headline)
                VStack(spacing: 12) {
                    StudyChoice(text: "Не знаю", selected: rating == .again) { rating = .again }
                    StudyChoice(text: "С трудом", selected: rating == .hard) { rating = .hard }
                    StudyChoice(text: "Помню", selected: rating == .good) { rating = .good }
                }.disabled(isSubmitting)
                Button(isSubmitting ? "Сохраняем…" : "Дальше") { if let rating { Task { await submit(rating, card) } } }
                    .buttonStyle(AluaPrimaryStyle()).disabled(rating == nil || isSubmitting)
            } else {
                Text("Вспомните ответ, затем проверьте себя.").foregroundStyle(AluaColors.secondaryText)
                Button("Проверить") { revealed = true }.buttonStyle(AluaPrimaryStyle())
                Button("Не знаю") { rating = .again; revealed = true }.frame(maxWidth: .infinity, minHeight: 44)
            }
            if let error = store.errorMessage { Label(error, systemImage: "exclamationmark.circle").foregroundStyle(.red) }
        }
    }
    private func submit(_ rating: VocabularyReviewRating, _ card: VocabularyReviewCard) async {
        guard !isSubmitting else { return }
        isSubmitting = true
        let eventID = eventIDs[card.id] ?? UUID(); eventIDs[card.id] = eventID
        if await store.submit(card: card, rating: rating, eventID: eventID) {
            ratings[rating, default: 0] += 1; index += 1; revealed = false; self.rating = nil
        }
        isSubmitting = false
    }
}
private final class VocabularySpeechPlayer {
    private let synthesizer = AVSpeechSynthesizer()
    func speak(_ value: String) { stop(); let utterance = AVSpeechUtterance(string: value); utterance.voice = AVSpeechSynthesisVoice(language: "en-US"); synthesizer.speak(utterance) }
    func stop() { synthesizer.stopSpeaking(at: .immediate) }
}
