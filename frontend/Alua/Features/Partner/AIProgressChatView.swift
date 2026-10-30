import SwiftUI

struct AIProgressChatView: View {
    let store: AIProgressStore
    @State private var input = ""
    private let starters = [
        "What improved this week?",
        "What should we focus on next?",
        "Which grammar areas cause the most difficulty?",
        "How consistent was the study routine?"
    ]

    var body: some View {
        VStack(spacing: 0) {
            ScrollView {
                LazyVStack(alignment: .leading, spacing: AluaSpacing.sm) {
                    Text("Answers are based only on shared Alua learning data.")
                        .font(AluaTypography.caption).foregroundStyle(AluaColors.secondaryText)
                    if store.messages.isEmpty { suggestions(starters) }
                    ForEach(store.messages) { message in bubble(message) }
                    if !store.suggestedFollowups.isEmpty { suggestions(store.suggestedFollowups) }
                    if let error = store.errorMessage { Text(error).foregroundStyle(.red).font(AluaTypography.caption) }
                }.padding(AluaSpacing.md)
            }
            HStack(spacing: AluaSpacing.sm) {
                TextField("Ask about progress", text: $input, axis: .vertical).textFieldStyle(.roundedBorder)
                Button { submit(input) } label: { Image(systemName: "arrow.up.circle.fill").font(.title2) }
                    .disabled(input.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || store.isSendingMessage || !store.isAvailable)
            }.padding(AluaSpacing.md).background(.bar)
        }.navigationTitle("Ask AI").task { await store.loadConversation() }
    }

    private func bubble(_ message: AIProgressChatMessage) -> some View {
        HStack {
            if message.role == "user" { Spacer(minLength: 48) }
            Text(message.content).padding(AluaSpacing.sm)
                .background(message.role == "user" ? AluaColors.accent : AluaColors.cardBackground)
                .foregroundStyle(message.role == "user" ? Color.white : AluaColors.primaryText)
                .clipShape(RoundedRectangle(cornerRadius: 14))
            if message.role != "user" { Spacer(minLength: 48) }
        }
    }
    private func suggestions(_ values: [String]) -> some View {
        VStack(alignment: .leading, spacing: AluaSpacing.xs) {
            ForEach(values, id: \.self) { value in
                Button(value) { input = value }.buttonStyle(.bordered)
            }
        }
    }
    private func submit(_ value: String) {
        input = ""
        Task { await store.sendMessage(value) }
    }
}
