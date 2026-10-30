import SwiftUI
import WidgetKit

enum WidgetStyle {
    static let accent = Color.accentColor
}

struct WidgetEmptyView: View {
    let title: String
    let message: String
    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title.uppercased()).font(.caption.weight(.semibold)).foregroundStyle(.secondary)
            Spacer(minLength: 2)
            Text(message).font(.headline)
            Text("to continue").font(.caption).foregroundStyle(.secondary)
        }.containerBackground(.background, for: .widget)
    }
}

struct WidgetStaleView: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("ALUA").font(.caption.weight(.semibold)).foregroundStyle(.secondary)
            Spacer()
            Text("Open Alua to refresh").font(.headline)
            Text("Last updated over a day ago").font(.caption).foregroundStyle(.secondary)
        }.containerBackground(.background, for: .widget)
    }
}

func makeWidgetURL(_ value: String) -> URL? { URL(string: value) }
