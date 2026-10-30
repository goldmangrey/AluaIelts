import SwiftUI

struct VocabularyWordDetailView: View {
    let item: VocabularyItem
    let curriculumNodeID: String?
    let learningEventService: any LearningEventServiceProtocol
    @State private var didRecordOpen = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: AluaSpacing.lg) {
                VStack(alignment: .leading, spacing: AluaSpacing.xs) {
                    Text(item.lemma).font(AluaTypography.largeTitle)
                    Text(item.translationRU).font(AluaTypography.title)
                    Text("\(item.partOfSpeech.title) · \(item.cefrLevel.rawValue) · \(item.register.rawValue.capitalized)")
                        .font(AluaTypography.caption)
                        .foregroundStyle(AluaColors.secondaryText)
                }

                detailSection("Meaning", values: [item.definitionEN])
                detailSection("Examples", values: item.examples)
                if !item.collocations.isEmpty {
                    detailSection("Collocations", values: item.collocations)
                }
                if !item.wordFamily.isEmpty {
                    detailSection(
                        "Word family",
                        values: item.wordFamily.map { "\($0.lemma) · \($0.partOfSpeech.title)" }
                    )
                }
                if !item.synonyms.isEmpty {
                    detailSection("Synonyms", values: item.synonyms)
                }
                if !item.antonyms.isEmpty {
                    detailSection("Antonyms", values: item.antonyms)
                }
                if !item.usageNotes.isEmpty {
                    detailSection("Usage", values: item.usageNotes)
                }
                if !item.commonConfusions.isEmpty {
                    detailSection("Common confusions", values: item.commonConfusions)
                }
            }
            .padding(AluaSpacing.md)
        }
        .background(AluaColors.groupedBackground)
        .navigationTitle(item.lemma)
        .navigationBarTitleDisplayMode(.inline)
        .task {
            guard !didRecordOpen else { return }
            didRecordOpen = true
            await learningEventService.recordVocabularyItemOpened(
                id: item.id,
                curriculumNodeID: curriculumNodeID
            )
        }
    }

    private func detailSection(_ title: String, values: [String]) -> some View {
        VStack(alignment: .leading, spacing: AluaSpacing.sm) {
            AluaSectionHeader(title: title)
            AluaCard {
                VStack(alignment: .leading, spacing: AluaSpacing.sm) {
                    ForEach(values, id: \.self) { value in
                        Text(value).font(AluaTypography.body)
                    }
                }
            }
        }
    }
}
