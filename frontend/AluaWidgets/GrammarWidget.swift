import SwiftUI
import WidgetKit

struct GrammarWidget: Widget {
    let kind = "GrammarWidget"
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: AluaWidgetProvider()) { GrammarWidgetView(entry: $0) }
            .configurationDisplayName("Grammar")
            .description("See today's current grammar structure.")
            .supportedFamilies([.systemSmall, .systemMedium, .accessoryRectangular])
    }
}

private struct GrammarWidgetView: View {
    @Environment(\.widgetFamily) private var family
    let entry: AluaWidgetEntry
    var body: some View {
        if entry.isExpired { WidgetStaleView() }
        else if let grammar = entry.grammarCard {
            VStack(alignment: .leading, spacing: 7) {
                if family != .accessoryRectangular { Text("GRAMMAR").font(.caption.weight(.semibold)).foregroundStyle(.secondary) }
                Text(grammar.shortTitle).font(.headline).lineLimit(1).minimumScaleFactor(0.85)
                Text(grammar.formula).font(.subheadline.monospaced().weight(.semibold)).lineLimit(2)
                if let support = grammar.supportRU { Text(support).font(.caption).foregroundStyle(.secondary).lineLimit(1) }
                if family == .systemMedium, let example = grammar.example { Text(example).font(.caption).lineLimit(1) }
            }.containerBackground(.background, for: .widget).widgetURL(makeWidgetURL("alua://grammar/\(grammar.contentID)"))
        } else { WidgetEmptyView(title: "Grammar", message: "Open Alua").widgetURL(makeWidgetURL("alua://today")) }
    }
}
