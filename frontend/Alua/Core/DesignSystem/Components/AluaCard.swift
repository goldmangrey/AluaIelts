import SwiftUI

struct AluaCard<Content: View>: View {
    private let content: Content

    init(@ViewBuilder content: () -> Content) {
        self.content = content()
    }

    var body: some View {
        content
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(AluaSpacing.md)
            .background(AluaColors.cardBackground)
            .clipShape(RoundedRectangle(cornerRadius: AluaRadius.medium, style: .continuous))
    }
}

#Preview {
    AluaCard {
        Text("Focused learning, one step at a time.")
    }
    .padding()
}
