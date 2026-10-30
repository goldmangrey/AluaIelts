import SwiftUI
import WidgetKit

struct AluaGlanceWidget: Widget {
    let kind = "AluaGlanceWidget"
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: AluaWidgetProvider()) { entry in
            AluaGlanceContent(glance: entry.snapshot?.glance, date: entry.date)
                .containerBackground(.clear, for: .widget)
                .widgetURL(entry.snapshot?.glance?.url(at: entry.date) ?? URL(string: "alua://today"))
        }
        .configurationDisplayName("Alua Glance")
        .description("Вспомните изученное слово или продолжите текущий день.")
        .supportedFamilies([.accessoryRectangular])
    }
}
