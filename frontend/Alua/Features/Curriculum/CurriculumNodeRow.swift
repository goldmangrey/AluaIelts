import SwiftUI

struct CurriculumNodeRow: View {
    let progress: CurriculumNodeProgress

    var body: some View {
        AluaCard {
            HStack(spacing: AluaSpacing.md) {
                Image(systemName: progress.status.systemImage)
                    .foregroundStyle(
                        progress.status == .active || progress.status == .completed
                            ? AluaColors.accent : AluaColors.secondaryText
                    )
                    .frame(width: 24)
                VStack(alignment: .leading, spacing: AluaSpacing.xs) {
                    Text(progress.node.title).font(AluaTypography.headline)
                    Text("\(progress.node.estimatedMinutes) min · \(progress.status.title)")
                        .font(AluaTypography.caption)
                        .foregroundStyle(AluaColors.secondaryText)
                }
                Spacer()
                if progress.isRecommended {
                    Text("Recommended")
                        .font(AluaTypography.caption)
                        .foregroundStyle(AluaColors.accent)
                }
            }
        }
        .opacity(progress.status == .locked ? 0.65 : 1)
        .accessibilityElement(children: .combine)
    }
}
