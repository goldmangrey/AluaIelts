import SwiftUI

struct DailyPlanItemRow: View {
    let item: DailyPlanItem

    var body: some View {
        HStack(alignment: .top, spacing: AluaSpacing.md) {
            Image(systemName: item.state == .completed ? "checkmark.circle.fill" : item.kind.systemImage)
                .foregroundStyle(AluaColors.accent)
                .frame(width: 28, height: 28)
            VStack(alignment: .leading, spacing: AluaSpacing.xs) {
                Text(item.title)
                    .font(AluaTypography.headline)
                    .foregroundStyle(AluaColors.primaryText)
                Text("\(item.kind.title) · \(item.estimatedMinutes) min")
                    .font(AluaTypography.subheadline)
                    .foregroundStyle(AluaColors.secondaryText)
                Text(item.reason.userFacingTitle)
                    .font(AluaTypography.caption)
                    .foregroundStyle(AluaColors.secondaryText)
                if item.state == .completed {
                    Text("Completed").font(AluaTypography.caption.weight(.semibold)).foregroundStyle(AluaColors.accent)
                }
            }
            Spacer()
            Image(systemName: "chevron.right")
                .font(.caption.weight(.semibold))
                .foregroundStyle(AluaColors.secondaryText)
                .padding(.top, AluaSpacing.xs)
        }
        .contentShape(Rectangle())
        .accessibilityElement(children: .combine)
    }
}
