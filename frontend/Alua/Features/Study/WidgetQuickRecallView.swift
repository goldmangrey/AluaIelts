import SwiftUI

struct WidgetRecallResolver {
    static func card(itemID: String, learnerID: String, generationID: String, expiresAt: Date,
                     activeLearner: String, source: GlanceWidgetSnapshot?, snapshot: StudySnapshot?,
                     pending: [StudyAnswer], now: Date = .now) -> StudyCard? {
        guard activeLearner == learnerID, expiresAt > now,
              let source, source.isCurrent(at: now), !source.isLocal,
              source.learnerID == learnerID, UUID(uuidString: generationID) != nil,
              source.cardID == itemID,
              expiresAt <= source.validUntil.addingTimeInterval(1),
              !pending.contains(where: { $0.item_id == itemID }),
              let card = snapshot?.book.first(where: { $0.id == itemID }),
              card.status == "review_due", card.term == source.term else { return nil }
        return card
    }
}
struct WidgetQuickRecallView: View {
    let store: StudyStore
    let itemID: String
    let learnerID: String
    let generationID: String
    let expiresAt: Date
    @State private var loaded = false
    @State private var card: StudyCard?
    var body: some View {
        Group {
            if loaded {
                StudyReviews(store: store, single: card, showsCloseButton: false)
            } else { SwiftUI.ProgressView("Проверяем карточку…") }
        }.task {
            // Capture the exact widget generation before refreshing Today, which may publish a new one.
            let source = WidgetSnapshotStorage().read()?.glance
            while store.syncing {
                do { try await Task.sleep(for: .milliseconds(100)) } catch { return }
            }
            guard !Task.isCancelled else { return }
            await store.sync()
            if store.error == nil {
                card = WidgetRecallResolver.card(itemID: itemID, learnerID: learnerID,
                    generationID: generationID, expiresAt: expiresAt, activeLearner: store.uid,
                    source: source, snapshot: store.disk.snapshot, pending: store.disk.queue)
            }
            // nil deliberately opens the ordinary due queue. Opening never records a response.
            loaded = true
        }
    }
}
