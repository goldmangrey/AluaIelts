import SwiftUI

struct AluaPrimaryStyle: ButtonStyle {
    @Environment(\.isEnabled) private var enabled
    func makeBody(configuration: Configuration) -> some View {
        configuration.label.font(.headline).multilineTextAlignment(.center)
            .frame(maxWidth: .infinity, minHeight: 24).padding(.vertical, 16).padding(.horizontal, 20)
            .foregroundStyle(AluaColors.background)
            .background(AluaColors.primaryText.opacity(enabled ? (configuration.isPressed ? 0.75 : 1) : 0.35), in: RoundedRectangle(cornerRadius: 16))
    }
}
struct AluaPage<Content: View>: View {
    let content: Content
    let resetKey: String?
    init(resetKey: String? = nil, @ViewBuilder content: () -> Content) {
        self.resetKey = resetKey; self.content = content()
    }
    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                VStack(alignment: .leading, spacing: 28) {
                    Color.clear.frame(height: 0).id("page-top").accessibilityHidden(true)
                    content
                }.frame(maxWidth: 640, alignment: .leading).padding(.horizontal, 24)
                    .padding(.bottom, 24).frame(maxWidth: .infinity)
            }.background(AluaColors.background).scrollDismissesKeyboard(.interactively)
                .onChange(of: resetKey) { _, _ in proxy.scrollTo("page-top", anchor: .top) }
        }
    }
}

struct AluaRouteRow: View {
    let title: String
    var subtitle: String? = nil
    var symbol: String? = nil
    var body: some View {
        HStack(alignment: .center, spacing: 16) {
            if let symbol { Image(systemName: symbol).font(.title3).frame(width: 26).accessibilityHidden(true) }
            VStack(alignment: .leading, spacing: 6) {
                Text(title).font(.headline).foregroundStyle(AluaColors.primaryText)
                if let subtitle { Text(subtitle).font(.subheadline).foregroundStyle(AluaColors.secondaryText) }
            }.frame(maxWidth: .infinity, alignment: .leading)
            Image(systemName: "chevron.right").font(.caption.weight(.semibold)).foregroundStyle(AluaColors.secondaryText).accessibilityHidden(true)
        }.padding(.vertical, 12).frame(minHeight: 52).contentShape(Rectangle())
    }
}
struct AluaCloseButton: View {
    var action: (() -> Void)? = nil
    @Environment(\.dismiss) private var dismiss
    var body: some View {
        Button { if let action { action() } else { dismiss() } } label: {
            Image(systemName: "xmark").font(.body.weight(.medium)).frame(width: 44, height: 44)
        }.accessibilityLabel("Закрыть").accessibilityHint("Сохранённые ответы останутся в приложении")
    }
}
struct StudySyncNotice: View {
    let store: StudyStore
    var body: some View {
        if store.error != nil || !store.disk.queue.isEmpty {
            VStack(alignment: .leading, spacing: 8) {
                Label(store.disk.queue.isEmpty ? "Не удалось обновить данные" : "Ответы сохранены на iPhone: \(store.disk.queue.count)", systemImage: "icloud.slash")
                    .font(.subheadline.weight(.medium))
                Text(store.storageReadable ? "При подключении ответы отправятся автоматически. До отправки не удаляйте приложение." : "Не удалось прочитать сохранённые ответы. Хранилище не изменено.")
                    .font(.footnote).foregroundStyle(AluaColors.secondaryText)
                if store.error != nil {
                    Button("Повторить отправку") { Task { await store.sync() } }.frame(minHeight: 44)
                }
            }.padding(16).frame(maxWidth: .infinity, alignment: .leading)
                .background(AluaColors.cardBackground, in: RoundedRectangle(cornerRadius: 12))
                .accessibilityElement(children: .contain)
        }
    }
}
struct StudyLoading: View {
    let store: StudyStore?
    var body: some View {
        if let store, store.error != nil {
            ContentUnavailableView {
                Label("Не удалось открыть учебник", systemImage: "wifi.slash")
            } description: { Text("Проверьте соединение. Сохранённый прогресс останется с вами.") }
            actions: { Button("Попробовать снова") { Task { await store.sync() } }.buttonStyle(AluaPrimaryStyle()) }
        } else { SwiftUI.ProgressView("Открываем учебник…").frame(maxWidth: .infinity, minHeight: 240) }
    }
}
struct StudyChoice: View {
    let text: String
    let selected: Bool
    let action: () -> Void
    var body: some View {
        Button(action: action) {
            HStack(spacing: 16) {
                Text(text).multilineTextAlignment(.leading).frame(maxWidth: .infinity, alignment: .leading)
                Image(systemName: selected ? "checkmark.circle.fill" : "circle").accessibilityHidden(true)
            }.font(.body).foregroundStyle(AluaColors.primaryText).padding(18).frame(minHeight: 56)
                .background(selected ? AluaColors.progressTrack : AluaColors.cardBackground, in: RoundedRectangle(cornerRadius: 14))
                .overlay(RoundedRectangle(cornerRadius: 14).strokeBorder(selected ? Color.primary : .clear, lineWidth: 1))
        }.buttonStyle(.plain).accessibilityAddTraits(selected ? .isSelected : [])
    }
}
