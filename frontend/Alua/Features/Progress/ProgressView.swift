import SwiftUI

struct ProgressView: View {
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: AluaSpacing.lg) {
                AluaSectionHeader(
                    title: "Weekly activity",
                    subtitle: "A concise view of your learning momentum."
                )

                AluaCard {
                    VStack(spacing: AluaSpacing.md) {
                        progressRow("Vocabulary", value: "+8%", systemImage: "character.book.closed")
                        Divider()
                        progressRow("Grammar", value: "+4%", systemImage: "textformat")
                        Divider()
                        progressRow("Retention", value: "81%", systemImage: "brain.head.profile")
                    }
                }

                VStack(alignment: .leading, spacing: AluaSpacing.sm) {
                    AluaSectionHeader(title: "Current stage")
                    AluaCard {
                        VStack(alignment: .leading, spacing: AluaSpacing.sm) {
                            Text("Foundation").font(AluaTypography.title)
                            Text("Building consistency across core language skills.")
                                .font(AluaTypography.subheadline)
                                .foregroundStyle(AluaColors.secondaryText)
                            AluaProgressBar(value: 0.36)
                        }
                    }
                }
            }
            .padding(AluaSpacing.md)
        }
        .background(AluaColors.groupedBackground)
        .navigationTitle("Progress")
    }

    private func progressRow(_ title: String, value: String, systemImage: String) -> some View {
        HStack(spacing: AluaSpacing.md) {
            Image(systemName: systemImage)
                .foregroundStyle(AluaColors.accent)
                .frame(width: 28)
            Text(title).font(AluaTypography.body)
            Spacer()
            Text(value).font(AluaTypography.headline.monospacedDigit())
        }
        .accessibilityElement(children: .combine)
    }
}

#Preview {
    NavigationStack { ProgressView() }
}
