import SwiftUI

struct PracticeView: View {
    let readingStore: ReadingStore?
    init(readingStore: ReadingStore? = nil) { self.readingStore = readingStore }
    var body: some View {
        AluaPage {
            Text("Развивай навыки для IELTS.")
                .font(AluaTypography.subheadline)
                .foregroundStyle(AluaColors.secondaryText)

            VStack(spacing: AluaSpacing.sm) {
                // SF Symbols calls the open-book glyph "book"; "book.open" is not available.
                direction("Reading", description: "Чтение и понимание текстов", symbol: "book") {
                    if let readingStore { ReadingView(store: readingStore) }
                    else { ContentUnavailableView("Reading недоступен", systemImage: "book.closed") }
                }
                direction("Listening", description: "Восприятие английской речи", symbol: "headphones") { ListeningView() }
                direction("Writing", description: "Академическое письмо", symbol: "pencil.line") { WritingView() }
                direction("Speaking", description: "Разговорная практика", symbol: "mic") { SpeakingView() }
            }
        }
        .navigationTitle("Практика")
        .navigationBarTitleDisplayMode(.large)
    }

    private func direction<Destination: View>(
        _ title: String, description: String, symbol: String,
        @ViewBuilder destination: () -> Destination
    ) -> some View {
        NavigationLink(destination: destination) {
            AluaRouteRow(title: title, subtitle: description, symbol: symbol)
                .padding(.horizontal, AluaSpacing.md)
                .contentShape(Rectangle())
        }
        .buttonStyle(PracticeRowStyle())
        .accessibilityElement(children: .ignore)
        .accessibilityAddTraits(.isButton)
        .accessibilityLabel("\(title), \(description)")
        .accessibilityHint("Открывает направление \(title)")
        .accessibilityIdentifier("practice.\(title.lowercased())")
    }
}

private struct PracticeRowStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .foregroundStyle(AluaColors.primaryText)
            .background(
                configuration.isPressed ? AluaColors.progressTrack : AluaColors.cardBackground,
                in: RoundedRectangle(cornerRadius: AluaRadius.medium)
            )
    }
}

struct ListeningView: View {
    var body: some View { PracticePlaceholder(title: "Listening", symbol: "headphones") }
}

struct WritingView: View {
    var body: some View { PracticePlaceholder(title: "Writing", symbol: "pencil.line") }
}

struct SpeakingView: View {
    var body: some View { PracticePlaceholder(title: "Speaking", symbol: "mic") }
}

private struct PracticePlaceholder: View {
    let title: String
    let symbol: String

    var body: some View {
        AluaPage {
            VStack(alignment: .leading, spacing: AluaSpacing.md) {
                Image(systemName: symbol)
                    .font(AluaTypography.title)
                    .foregroundStyle(AluaColors.primaryText)
                    .accessibilityHidden(true)
                Text("Скоро здесь появятся задания.")
                    .font(AluaTypography.body)
                    .foregroundStyle(AluaColors.secondaryText)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(AluaSpacing.lg)
            .background(AluaColors.cardBackground, in: RoundedRectangle(cornerRadius: AluaRadius.medium))
        }
        .navigationTitle(title)
        .navigationBarTitleDisplayMode(.large)
    }
}
