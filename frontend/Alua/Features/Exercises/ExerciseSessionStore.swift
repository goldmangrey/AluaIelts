import Foundation
import Observation

@MainActor @Observable
final class ExerciseSessionStore {
    private(set) var session: ExerciseSession?
    private(set) var currentExerciseIndex = 0
    private(set) var isLoading = false
    private(set) var isSubmitting = false
    var errorMessage: String?
    private(set) var lastResult: ExerciseAttemptResult?
    @ObservationIgnored private let service: any ExerciseServiceProtocol
    @ObservationIgnored private var attemptIDs: [String: UUID] = [:]

    init(service: any ExerciseServiceProtocol) { self.service = service }

    func create(date: String, itemID: String) async {
        await load { try await service.createSession(date: date, dailyPlanItemID: itemID) }
    }
    func resume(id: String) async { await load { try await service.getSession(id: id) } }
    func submitChoice(_ optionID: String) async { await submit { session, exercise, attemptID in try await service.submitChoiceAnswer(sessionID: session.sessionID, exerciseID: exercise.exerciseID, attemptID: attemptID, optionID: optionID) } }
    func submitText(_ answer: String) async { await submit { session, exercise, attemptID in try await service.submitTextAnswer(sessionID: session.sessionID, exerciseID: exercise.exerciseID, attemptID: attemptID, answer: answer) } }
    func submitUnknown() async { await submit { session, exercise, attemptID in try await service.submitUnknown(sessionID: session.sessionID, exerciseID: exercise.exerciseID, attemptID: attemptID) } }
    func advance() { lastResult = nil; selectCurrentExercise() }

    private func load(_ operation: () async throws -> ExerciseSession) async {
        guard !isLoading else { return }; isLoading = true; errorMessage = nil
        defer { isLoading = false }
        do { session = try await operation(); selectCurrentExercise() } catch { errorMessage = message(error) }
    }
    private func submit(_ operation: (ExerciseSession, ExercisePublicItem, UUID) async throws -> ExerciseAttemptResult) async {
        guard let session, currentExerciseIndex < session.exercises.count, !isSubmitting else { return }
        isSubmitting = true; errorMessage = nil
        defer { isSubmitting = false }
        do {
            let exercise = session.exercises[currentExerciseIndex]
            let attemptID = attemptIDs[exercise.exerciseID] ?? UUID()
            attemptIDs[exercise.exerciseID] = attemptID
            lastResult = try await operation(session, exercise, attemptID)
            self.session = try await service.getSession(id: session.sessionID)
        } catch { errorMessage = message(error) }
    }
    private func selectCurrentExercise() {
        guard let session else { currentExerciseIndex = 0; return }
        currentExerciseIndex = session.exercises.firstIndex { $0.state == .unanswered } ?? max(0, session.exercises.count - 1)
    }
    private func message(_ error: Error) -> String { (error as? LocalizedError)?.errorDescription ?? "Practice is temporarily unavailable." }
}
