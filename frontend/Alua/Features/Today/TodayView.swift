import SwiftUI

struct TodayView: View {
    let environment: AppEnvironment
    let authSession: AuthSession

    private var greeting: String {
        guard let name = authSession.profile?.displayName, !name.isEmpty else {
            return "Good morning"
        }
        return "Good morning, \(name)"
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: AluaSpacing.lg) {
                VStack(alignment: .leading, spacing: AluaSpacing.xs) {
                    Text(greeting)
                        .font(AluaTypography.largeTitle)
                    Text("A focused session is ready when you are.")
                        .font(AluaTypography.body)
                        .foregroundStyle(AluaColors.secondaryText)
                }

                AluaCard {
                    VStack(alignment: .leading, spacing: AluaSpacing.md) {
                        HStack(alignment: .firstTextBaseline) {
                            Text("Daily progress").font(AluaTypography.headline)
                            Spacer()
                            Text("18 / 42").font(AluaTypography.headline.monospacedDigit())
                        }
                        AluaProgressBar(value: 18.0 / 42.0)
                        VStack(spacing: AluaSpacing.sm) {
                            metricRow("Vocabulary", value: "12 / 20")
                            metricRow("Grammar", value: "4 / 12")
                            metricRow("Review", value: "2 / 10")
                        }
                    }
                }

                PrimaryButton(title: "Continue Learning", systemImage: "arrow.right") {}

                VStack(alignment: .leading, spacing: AluaSpacing.sm) {
                    AluaSectionHeader(title: "Current focus")
                    AluaCard {
                        Label("Present Perfect", systemImage: "text.book.closed")
                            .font(AluaTypography.headline)
                    }
                }
            }
            .padding(AluaSpacing.md)
        }
        .background(AluaColors.groupedBackground)
        .navigationTitle("Today")
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                NavigationLink {
                    SettingsView(environment: environment, authSession: authSession)
                } label: {
                    Image(systemName: "gearshape")
                }
                .accessibilityLabel("Settings")
            }
        }
    }

    private func metricRow(_ title: String, value: String) -> some View {
        HStack {
            Text(title).foregroundStyle(AluaColors.secondaryText)
            Spacer()
            Text(value).monospacedDigit()
        }
        .font(AluaTypography.subheadline)
    }
}
