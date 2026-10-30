import SwiftUI
import WidgetKit

struct TodayLearningWidget: Widget {
    let kind = "TodayLearningWidget"
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: AluaWidgetProvider()) { TodayWidgetView(entry: $0) }
            .configurationDisplayName("Today")
            .description("See today's learning plan progress.")
            .supportedFamilies([.systemSmall, .systemMedium, .accessoryInline, .accessoryCircular, .accessoryRectangular])
    }
}

private struct TodayWidgetView: View {
    @Environment(\.widgetFamily) private var family
    let entry: AluaWidgetEntry
    var body: some View {
        if entry.isTodayStale { WidgetStaleView() }
        else if let learner = entry.snapshot?.learner, let today = learner.today {
            content(learner, today).widgetURL(makeWidgetURL("alua://today"))
                .containerBackground(today.isComplete ? WidgetStyle.accent.opacity(0.12) : Color.clear, for: .widget)
                .accessibilityLabel("\(today.completedItems) of \(today.totalItems) activities completed today")
        } else { WidgetEmptyView(title: "Today", message: "Open Alua") .widgetURL(makeWidgetURL("alua://today")) }
    }
    @ViewBuilder private func content(_ learner: LearnerWidgetSnapshot, _ today: WidgetTodaySnapshot) -> some View {
        switch family {
        case .accessoryInline: Text(today.isComplete ? "\(today.completedItems)/\(today.totalItems) done ♡" : "\(today.completedItems)/\(today.totalItems) today")
        case .accessoryCircular:
            Gauge(value: Double(today.completedItems), in: 0...Double(max(today.totalItems, 1))) { Text("Today") }
                .gaugeStyle(.accessoryCircularCapacity).overlay(Text("\(today.completedItems)/\(today.totalItems)").font(.caption2.monospacedDigit()))
        case .accessoryRectangular:
            VStack(alignment: .leading) { Text(today.isComplete ? "DONE" : "TODAY").font(.caption2); Text("\(today.completedItems) of \(today.totalItems)").font(.headline) }
        default:
            VStack(alignment: .leading, spacing: 6) {
                Text(today.isComplete ? "DONE FOR TODAY" : "TODAY").font(.caption.weight(.semibold)).foregroundStyle(.secondary)
                Text("\(today.completedItems) / \(today.totalItems)").font(.system(.title, design: .rounded, weight: .bold)).monospacedDigit()
                if today.isComplete { Text(personalMessage(learner.displayName)).font(.subheadline).lineLimit(2) }
                else if let focus = today.currentFocus { Text(focus).font(.subheadline).lineLimit(2) }
                if family == .systemMedium { Spacer(); Text("Grammar \(today.grammarItems)   Vocabulary \(today.vocabularyItems)   Review \(today.reviewItems)").font(.caption).foregroundStyle(.secondary) }
            }
        }
    }
    private func personalMessage(_ name: String?) -> String {
        guard let name, !name.isEmpty, name.count <= 18 else { return "Proud of you ♡" }
        return "Proud of you, \(name) ♡"
    }
}
