import SwiftUI

struct LearnView: View {
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: AluaSpacing.lg) {
                AluaSectionHeader(
                    title: "Choose your focus",
                    subtitle: "Build durable English skills at your own pace."
                )
                learningCard(
                    title: "Vocabulary",
                    description: "Build active IELTS vocabulary",
                    systemImage: "character.book.closed"
                )
                learningCard(
                    title: "Grammar",
                    description: "Master English structures",
                    systemImage: "textformat"
                )
                learningCard(
                    title: "Review",
                    description: "Strengthen learned material",
                    systemImage: "arrow.triangle.2.circlepath"
                )
            }
            .padding(AluaSpacing.md)
        }
        .background(AluaColors.groupedBackground)
        .navigationTitle("Learn")
    }

    private func learningCard(title: String, description: String, systemImage: String) -> some View {
        AluaCard {
            HStack(spacing: AluaSpacing.md) {
                Image(systemName: systemImage)
                    .font(.title2)
                    .foregroundStyle(AluaColors.accent)
                    .frame(width: 36, height: 44)
                VStack(alignment: .leading, spacing: AluaSpacing.xs) {
                    Text(title).font(AluaTypography.headline)
                    Text(description)
                        .font(AluaTypography.subheadline)
                        .foregroundStyle(AluaColors.secondaryText)
                }
                Spacer()
            }
        }
        .accessibilityElement(children: .combine)
    }
}

#Preview {
    NavigationStack { LearnView() }
}
