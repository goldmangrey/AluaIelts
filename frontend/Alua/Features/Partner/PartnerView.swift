import SwiftUI

struct PartnerView: View {
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: AluaSpacing.lg) {
                AluaSectionHeader(
                    title: "Partner progress",
                    subtitle: "A simple overview of today's study plan."
                )

                AluaCard {
                    VStack(alignment: .leading, spacing: AluaSpacing.md) {
                        HStack {
                            Text("Today").font(AluaTypography.headline)
                            Spacer()
                            Text("34 / 42").font(AluaTypography.headline.monospacedDigit())
                        }
                        AluaProgressBar(value: 34.0 / 42.0)
                        partnerRow("Vocabulary", value: "18 / 20")
                        partnerRow("Grammar", value: "10 / 12")
                        partnerRow("Review", value: "6 / 10")
                    }
                }

                AluaCard {
                    VStack(alignment: .leading, spacing: AluaSpacing.xs) {
                        Text("Current focus")
                            .font(AluaTypography.caption)
                            .foregroundStyle(AluaColors.secondaryText)
                        Text("Present Perfect").font(AluaTypography.headline)
                    }
                }

                PrimaryButton(
                    title: "Generate AI Report",
                    systemImage: "doc.text",
                    isDisabled: true
                ) {}
            }
            .padding(AluaSpacing.md)
        }
        .background(AluaColors.groupedBackground)
        .navigationTitle("Partner")
    }

    private func partnerRow(_ title: String, value: String) -> some View {
        HStack {
            Text(title).foregroundStyle(AluaColors.secondaryText)
            Spacer()
            Text(value).monospacedDigit()
        }
        .font(AluaTypography.subheadline)
    }
}

#Preview {
    NavigationStack { PartnerView() }
}
