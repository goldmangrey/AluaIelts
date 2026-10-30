import SwiftUI

struct GrammarErrorCard: View {
    let error: GrammarCommonError

    var body: some View {
        AluaCard {
            VStack(alignment: .leading, spacing: AluaSpacing.md) {
                labelledSentence("Incorrect", symbol: "xmark.circle", sentence: error.wrong)
                labelledSentence("Correct", symbol: "checkmark.circle", sentence: error.correct)
                Divider()
                Text(error.explanationEN).font(AluaTypography.body)
                Text(error.explanationRU)
                    .font(AluaTypography.subheadline)
                    .foregroundStyle(AluaColors.secondaryText)
                Text(error.errorTag.replacingOccurrences(of: "_", with: " "))
                    .font(AluaTypography.caption)
                    .foregroundStyle(AluaColors.secondaryText)
            }
        }
    }

    private func labelledSentence(_ label: String, symbol: String, sentence: String) -> some View {
        VStack(alignment: .leading, spacing: AluaSpacing.xs) {
            Label(label, systemImage: symbol).font(AluaTypography.caption.weight(.semibold))
            Text(sentence).font(AluaTypography.body)
        }
    }
}
