import SwiftUI
import WidgetKit

struct PartnerProgressWidget: Widget {
    let kind = "PartnerProgressWidget"
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: AluaWidgetProvider()) { PartnerWidgetView(entry: $0) }
            .configurationDisplayName("Partner Progress")
            .description("See a learner's shared progress for today.")
            .supportedFamilies([.systemSmall, .systemMedium, .accessoryInline, .accessoryRectangular])
    }
}

private struct PartnerWidgetView: View {
    @Environment(\.widgetFamily) private var family
    let entry: AluaWidgetEntry
    var body: some View {
        if entry.isTodayStale { WidgetStaleView() }
        else if let partner = entry.snapshot?.partner {
            content(partner).containerBackground(.background, for: .widget).widgetURL(makeWidgetURL("alua://partner"))
        } else { WidgetEmptyView(title: "Partner", message: "Open Alua").widgetURL(makeWidgetURL("alua://partner")) }
    }
    @ViewBuilder private func content(_ partner: PartnerWidgetSnapshot) -> some View {
        if !partner.permissions.dailyActivity {
            VStack(alignment: .leading, spacing: 6) { Text(partner.learnerDisplayName.uppercased()).font(.caption.weight(.semibold)); Text("Progress is not shared").font(.headline) }
        } else if family == .accessoryInline {
            Text("\(partner.learnerDisplayName) · \(partner.completedItems ?? 0)/\(partner.totalItems ?? 0) today")
        } else {
            VStack(alignment: .leading, spacing: 6) {
                Text(family == .accessoryRectangular ? "\(partner.learnerDisplayName) · TODAY" : partner.learnerDisplayName.uppercased()).font(.caption.weight(.semibold)).lineLimit(1)
                Text("\(partner.completedItems ?? 0) / \(partner.totalItems ?? 0)").font(.title2.bold()).monospacedDigit()
                if partner.activeToday == true, family == .systemSmall { Text("Active today").font(.caption).foregroundStyle(.secondary) }
                if let focus = partner.currentFocus { Text(focus).font(.subheadline).lineLimit(1) }
                if family == .systemMedium, let days = partner.activeDays7 { Text("\(days) / 7 active days").font(.caption).foregroundStyle(.secondary) }
            }.accessibilityLabel("\(partner.completedItems ?? 0) of \(partner.totalItems ?? 0) activities completed today by \(partner.learnerDisplayName)")
        }
    }
}
