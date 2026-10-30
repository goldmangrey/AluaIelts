import Foundation

protocol LearningEventServiceProtocol: Sendable {
    func recordGrammarLessonOpened(id: String, curriculumNodeID: String?) async
    func recordVocabularyTrackOpened(id: String, curriculumNodeID: String?) async
    func recordVocabularyItemOpened(id: String, curriculumNodeID: String?) async
    func getRecentEvents(limit: Int, before: Date?) async throws -> LearningEventsResponse
}

final class LearningEventService: LearningEventServiceProtocol, Sendable {
    private let apiClient: any APIClientProtocol

    init(apiClient: any APIClientProtocol) {
        self.apiClient = apiClient
    }

    func recordGrammarLessonOpened(id: String, curriculumNodeID: String?) async {
        await record(.grammarLessonOpened, contentID: id, curriculumNodeID: curriculumNodeID)
    }

    func recordVocabularyTrackOpened(id: String, curriculumNodeID: String?) async {
        await record(.vocabularyTrackOpened, contentID: id, curriculumNodeID: curriculumNodeID)
    }

    func recordVocabularyItemOpened(id: String, curriculumNodeID: String?) async {
        await record(.vocabularyItemOpened, contentID: id, curriculumNodeID: curriculumNodeID)
    }

    func getRecentEvents(limit: Int = 50, before: Date? = nil) async throws
        -> LearningEventsResponse
    {
        var queryItems = [URLQueryItem(name: "limit", value: String(limit))]
        if let before {
            queryItems.append(
                URLQueryItem(name: "before_server_received_at", value: before.ISO8601Format())
            )
        }
        return try await apiClient.send(
            APIEndpoint(
                path: "/api/v1/learning-events",
                queryItems: queryItems,
                requiresAuthentication: true
            ),
            responseType: LearningEventsResponse.self
        )
    }

    private func record(
        _ type: LearningEventType,
        contentID: String,
        curriculumNodeID: String?
    ) async {
        let eventID = UUID()
        let request = CreateLearningEventRequest(
            eventID: eventID,
            eventType: type,
            contentID: contentID,
            curriculumNodeID: curriculumNodeID,
            clientOccurredAt: Date(),
            timezone: TimeZone.current.identifier,
            sessionID: nil
        )
        do {
            let _: LearningEvent = try await apiClient.send(
                APIEndpoint(
                    path: "/api/v1/learning-events",
                    method: .post,
                    body: request,
                    requiresAuthentication: true
                ),
                responseType: LearningEvent.self
            )
        } catch {
            #if DEBUG
                print("Learning event send failed: \(type.rawValue)/\(eventID)")
            #endif
        }
    }
}
