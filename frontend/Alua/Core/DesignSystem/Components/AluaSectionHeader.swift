import SwiftUI

struct AluaSectionHeader: View {
    let title: String
    var subtitle: String?
    var actionTitle: String?
    var action: (() -> Void)?

    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: AluaSpacing.md) {
            VStack(alignment: .leading, spacing: AluaSpacing.xs) {
                Text(title)
                    .font(AluaTypography.title)
                if let subtitle {
                    Text(subtitle)
                        .font(AluaTypography.subheadline)
                        .foregroundStyle(AluaColors.secondaryText)
                }
            }
            Spacer()
            if let actionTitle, let action {
                Button(actionTitle, action: action)
                    .font(AluaTypography.subheadline.weight(.semibold))
            }
        }
    }
}
