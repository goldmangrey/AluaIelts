import SwiftUI

struct AluaProgressBar: View {
    let value: Double

    private var normalizedValue: Double {
        min(max(value, 0), 1)
    }

    var body: some View {
        GeometryReader { geometry in
            ZStack(alignment: .leading) {
                Capsule().fill(AluaColors.progressTrack)
                Capsule()
                    .fill(AluaColors.accent)
                    .frame(width: geometry.size.width * normalizedValue)
            }
        }
        .frame(height: 8)
        .accessibilityElement()
        .accessibilityLabel("Progress")
        .accessibilityValue(Text(normalizedValue, format: .percent))
    }
}

#Preview {
    AluaProgressBar(value: 0.64)
        .padding()
}
