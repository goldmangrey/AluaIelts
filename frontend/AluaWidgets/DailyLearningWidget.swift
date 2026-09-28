import WidgetKit
import SwiftUI

struct LearningEntry: TimelineEntry {
    let date: Date
}

struct LearningProvider: TimelineProvider {
    func placeholder(in context: Context) -> LearningEntry {
        LearningEntry(date: .now)
    }

    func getSnapshot(
        in context: Context,
        completion: @escaping (LearningEntry) -> Void
    ) {
        completion(LearningEntry(date: .now))
    }

    func getTimeline(
        in context: Context,
        completion: @escaping (Timeline<LearningEntry>) -> Void
    ) {
        let entry = LearningEntry(date: .now)

        let nextUpdate = Calendar.current.date(
            byAdding: .hour,
            value: 1,
            to: .now
        ) ?? .now

        completion(
            Timeline(
                entries: [entry],
                policy: .after(nextUpdate)
            )
        )
    }
}

struct DailyLearningWidget: Widget {
    let kind = "DailyLearningWidget"

    var body: some WidgetConfiguration {
        StaticConfiguration(
            kind: kind,
            provider: LearningProvider()
        ) { _ in
            VStack(alignment: .leading, spacing: 6) {
                Text("ALUA")
                    .font(.caption)

                Text("MITIGATE")
                    .font(.headline)

                Text("reduce the severity")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .containerBackground(.fill.tertiary, for: .widget)
        }
        .configurationDisplayName("Daily Learning")
        .description("Vocabulary and grammar practice.")
        .supportedFamilies([
            .systemSmall,
            .systemMedium
        ])
    }
}
