import SwiftUI

struct AIProgressReportView: View {
    let response: AIProgressReportResponse

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: AluaSpacing.lg) {
                Text(response.report.headline).font(AluaTypography.title)
                Text("Based on \(response.periodDays) days of shared learning data")
                    .font(AluaTypography.caption).foregroundStyle(AluaColors.secondaryText)
                section("Overview") { Text(response.report.summary) }
                insightSection("Highlights", response.report.highlights)
                insightSection("Areas to Work On", response.report.areasToWorkOn)
                section("Recommended Focus") {
                    ForEach(response.report.recommendations) { item in
                        VStack(alignment: .leading, spacing: AluaSpacing.xs) {
                            Text(item.title).font(AluaTypography.headline)
                            Text(item.recommendation)
                            Text(item.reason).font(AluaTypography.caption).foregroundStyle(AluaColors.secondaryText)
                        }
                    }
                }
                section("Data Limitations") {
                    ForEach(response.report.dataLimitations) { Text($0.statement) }
                }
                Text("AI-generated guidance is advisory and is based only on shared Alua learning data.")
                    .font(AluaTypography.caption).foregroundStyle(AluaColors.secondaryText)
            }.padding(AluaSpacing.md)
        }.background(AluaColors.groupedBackground).navigationTitle("Progress Report")
    }

    private func insightSection(_ title: String, _ values: [AIProgressInsight]) -> some View {
        section(title) {
            if values.isEmpty { Text("No supported conclusion for this period.").foregroundStyle(AluaColors.secondaryText) }
            ForEach(values) { item in
                VStack(alignment: .leading, spacing: AluaSpacing.xs) {
                    Text(item.title).font(AluaTypography.headline)
                    Text(item.statement)
                }
            }
        }
    }
    private func section<Content: View>(_ title: String, @ViewBuilder content: () -> Content) -> some View {
        AluaCard { VStack(alignment: .leading, spacing: AluaSpacing.sm) { Text(title).font(AluaTypography.headline); content() } }
    }
}
