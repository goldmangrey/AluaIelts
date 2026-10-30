import SwiftUI

/// The real accessory widget content, also available to rendering/accessibility tests.
struct AluaGlanceContent: View {
    let glance: GlanceWidgetSnapshot?
    var date = Date.now
    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            if let glance, glance.isCurrent(at: date),
               !(glance.day == 1 && glance.processed == 0 && glance.cardID == nil) {
                if let term = glance.term, glance.cardID != nil, !glance.isLocal {
                    Text("ВСПОМНИ").font(.caption2.weight(.semibold))
                    Text(term).font(.headline).lineLimit(2).fixedSize(horizontal: false, vertical: true)
                    Text("Помнишь значение?").font(.caption)
                } else {
                    Text("ALUA").font(.caption2.weight(.semibold))
                    Text(glance.finished ? "50 дней пройдены" : "День \(glance.day) · \(glance.processed)/30").font(.headline)
                    Text(glance.isLocal ? "На iPhone · ждёт отправки" : "Продолжить в Alua").font(.caption)
                }
            } else {
                Text("ALUA").font(.caption2.weight(.semibold))
                Text("Время для английского").font(.headline).lineLimit(2)
                Text("Откройте свой учебник").font(.caption)
            }
        }.frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .leading)
            .accessibilityElement(children: .combine)
    }
}
