import Foundation
import Observation

@MainActor @Observable
final class DeepLinkRouter {
    private(set) var pending: DeepLink?
    func receive(_ url: URL) { if let link = DeepLink(url: url) { pending = link } }
    func consume() -> DeepLink? { defer { pending = nil }; return pending }
}
