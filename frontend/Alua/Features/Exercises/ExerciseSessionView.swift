import SwiftUI

struct ExerciseSessionView: View {
    let planDate: String
    let item: DailyPlanItem
    let dailyPlanStore: DailyPlanStore
    let studentModelStore: StudentModelStore
    @State private var store: ExerciseSessionStore
    @State private var selectedOptionID: String?
    @State private var textAnswer = ""
    @Environment(\.dismiss) private var dismiss

    init(planDate: String, item: DailyPlanItem, service: any ExerciseServiceProtocol, dailyPlanStore: DailyPlanStore, studentModelStore: StudentModelStore) {
        self.planDate = planDate; self.item = item; self.dailyPlanStore = dailyPlanStore; self.studentModelStore = studentModelStore
        _store = State(initialValue: ExerciseSessionStore(service: service))
    }

    var body: some View {
        Group {
            if store.isLoading && store.session == nil { SwiftUI.ProgressView("Готовим практику…") }
            else if let error = store.errorMessage, store.session == nil { errorView(error) }
            else if let session = store.session { sessionContent(session) }
        }
        .navigationTitle("Практика").navigationBarTitleDisplayMode(.inline)
        .task { await store.create(date: planDate, itemID: item.itemID) }
    }

    @ViewBuilder private func sessionContent(_ session: ExerciseSession) -> some View {
        if session.status == .completed && store.lastResult == nil {
            completion(session)
        } else if store.currentExerciseIndex < session.exercises.count {
            let exercise = session.exercises[store.currentExerciseIndex]
            ScrollView {
                VStack(alignment: .leading, spacing: AluaSpacing.lg) {
                    VStack(alignment: .leading, spacing: AluaSpacing.xs) {
                        Text("\(min(session.progress.answered + 1, session.progress.total)) из \(session.progress.total)")
                            .font(AluaTypography.headline)
                        SwiftUI.ProgressView(value: Double(session.progress.answered), total: Double(session.progress.total))
                    }
                    Text(exercise.instruction).font(AluaTypography.subheadline).foregroundStyle(AluaColors.secondaryText)
                    Text(exercise.prompt).font(AluaTypography.title)
                    if exercise.options.isEmpty { typedInput } else { options(exercise) }
                    if let result = store.lastResult { feedback(result) } else {
                        Button("Не знаю") { Task { await store.submitUnknown() } }.disabled(store.isSubmitting)
                        PrimaryButton(title: store.isSubmitting ? "Сохраняем…" : "Проверить", isDisabled: store.isSubmitting || !hasAnswer(exercise)) {
                            Task { if let selectedOptionID { await store.submitChoice(selectedOptionID) } else { await store.submitText(textAnswer) } }
                        }
                    }
                    if let error = store.errorMessage { Text(error).foregroundStyle(.red) }
                }.padding(AluaSpacing.md)
            }.background(AluaColors.groupedBackground)
        }
    }

    private func options(_ exercise: ExercisePublicItem) -> some View {
        VStack(spacing: AluaSpacing.sm) {
            ForEach(exercise.options) { option in
                Button { selectedOptionID = option.id } label: {
                    AluaCard {
                        HStack { Text(option.text).multilineTextAlignment(.leading); Spacer(); Image(systemName: selectedOptionID == option.id ? "checkmark.circle.fill" : "circle") }
                    }
                }.buttonStyle(.plain).disabled(store.lastResult != nil)
            }
        }
    }
    private var typedInput: some View {
        TextField("Ваш ответ", text: $textAnswer).textInputAutocapitalization(.never).autocorrectionDisabled().submitLabel(.done).textFieldStyle(.roundedBorder).frame(minHeight: 44).disabled(store.lastResult != nil)
    }
    private func feedback(_ result: ExerciseAttemptResult) -> some View {
        VStack(alignment: .leading, spacing: AluaSpacing.md) {
            AluaCard {
                VStack(alignment: .leading, spacing: AluaSpacing.sm) {
                    Label(result.isCorrect ? "Верно" : "Попробуем ещё раз", systemImage: result.isCorrect ? "checkmark.circle.fill" : "xmark.circle.fill").font(AluaTypography.title)
                    if !result.isCorrect { Text("Правильный ответ: \(result.correctAnswerDisplay)").font(AluaTypography.headline) }
                    Text(result.explanation).foregroundStyle(AluaColors.secondaryText)
                }
            }
            PrimaryButton(title: result.sessionStatus == .completed ? "Готово" : "Дальше") {
                Task {
                    if result.sessionStatus == .completed { await refreshStores(); dismiss() }
                    else { selectedOptionID = nil; textAnswer = ""; store.advance() }
                }
            }
        }
    }
    private func completion(_ session: ExerciseSession) -> some View {
        ContentUnavailableView {
            Label("Практика завершена", systemImage: "checkmark.circle.fill")
        } description: { Text("\(session.progress.correct) из \(session.progress.total) верно\nЗадание завершено") }
        actions: { Button("Готово") { Task { await refreshStores(); dismiss() } }.buttonStyle(.borderedProminent) }
    }
    private func errorView(_ message: String) -> some View {
        ContentUnavailableView("Практика недоступна", systemImage: "exclamationmark.circle", description: Text(message))
    }
    private func hasAnswer(_ exercise: ExercisePublicItem) -> Bool { exercise.options.isEmpty ? !textAnswer.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty : selectedOptionID != nil }
    private func refreshStores() async { await dailyPlanStore.refresh(); await studentModelStore.refresh() }
}
