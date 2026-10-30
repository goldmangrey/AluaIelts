import SwiftUI
import WidgetKit

struct VocabularyWidget: Widget {
    let kind = "VocabularyWidget"
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: AluaWidgetProvider()) { VocabularyWidgetView(entry: $0) }
            .configurationDisplayName("Vocabulary")
            .description("See one relevant word from today's plan.")
            .supportedFamilies([.systemSmall, .systemMedium, .accessoryRectangular])
    }
}

private struct VocabularyWidgetView: View {
    @Environment(\.widgetFamily) private var family
    let entry: AluaWidgetEntry
    var body: some View {
        if family == .accessoryRectangular {
            AluaGlanceContent(glance: entry.snapshot?.glance, date: entry.date)
                .containerBackground(.clear, for: .widget)
                .widgetURL(entry.snapshot?.glance?.url(at: entry.date) ?? URL(string: "alua://today"))
        }
        else if entry.isTodayStale { WidgetStaleView() }
        else if let card = entry.vocabularyCard {
            VStack(alignment: .leading, spacing: 6) {
                if family != .accessoryRectangular { Text("VOCABULARY").font(.caption.weight(.semibold)).foregroundStyle(.secondary) }
                Text(card.term.uppercased()).font(family == .systemSmall ? .title2.weight(.bold) : .headline).lineLimit(1).minimumScaleFactor(0.75)
                Text(card.translationRU).font(.subheadline).foregroundStyle(.secondary).lineLimit(2)
                if family == .systemMedium, let metadata = metadata(for: card) {
                    Text(metadata).font(.caption).foregroundStyle(.tertiary).lineLimit(1)
                }
            }.containerBackground(.background, for: .widget).widgetURL(makeWidgetURL("alua://today"))
        } else { WidgetEmptyView(title: "Vocabulary", message: "Open Alua to refresh").widgetURL(makeWidgetURL("alua://today")) }
    }

    private func metadata(for card: WidgetVocabularySnapshot) -> String? {
        [card.ipa, card.cefr].compactMap { value in
            guard let value, !value.isEmpty else { return nil }
            return value
        }.joined(separator: "  ·  ").nilIfEmpty
    }
}

private extension String {
    var nilIfEmpty: String? { isEmpty ? nil : self }
}
