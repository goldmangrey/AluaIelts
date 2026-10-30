import SwiftUI
import WidgetKit

struct PracticeWidget: Widget {
    let kind = "PracticeWidget"
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: AluaWidgetProvider()) { PracticeWidgetView(entry: $0) }
            .configurationDisplayName("Review Status")
            .description("See today's review status.")
            .supportedFamilies([.systemSmall, .systemMedium])
    }
}

private struct PracticeWidgetView: View {
    let entry: AluaWidgetEntry
    var body: some View {
        if entry.isTodayStale { WidgetStaleView() }
        else if let today = entry.snapshot?.learner?.today {
            VStack(alignment: .leading, spacing: 6) {
                Text("REVIEW").font(.caption.weight(.semibold)).foregroundStyle(.secondary)
                Text(today.reviewItems == 0 ? "All caught up" : "\(today.reviewItems) items")
                    .font(.title2.bold()).lineLimit(2).minimumScaleFactor(0.75)
                Text(today.reviewItems == 0 ? "Nothing planned" : "Ready in Alua")
                    .font(.subheadline).foregroundStyle(.secondary)
                Spacer(); Text("Open Alua").font(.subheadline.weight(.semibold)).foregroundStyle(WidgetStyle.accent)
            }
                .containerBackground(.background, for: .widget).widgetURL(makeWidgetURL("alua://today"))
        } else { WidgetEmptyView(title: "Review", message: "Open Alua").widgetURL(makeWidgetURL("alua://today")) }
    }
}
