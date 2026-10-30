import SwiftUI

struct PrimaryButton: View {
    let title: String
    var systemImage: String?
    var isDisabled = false
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: AluaSpacing.sm) {
                if let systemImage {
                    Image(systemName: systemImage)
                }
                Text(title)
            }
            .font(AluaTypography.headline)
            .frame(maxWidth: .infinity)

        }
        .buttonStyle(AluaPrimaryStyle())
        .tint(AluaColors.accent)
        .disabled(isDisabled)
    }
}
