import SwiftUI

struct SettingsView: View {
    let environment: AppEnvironment
    let authSession: AuthSession
    var studyStore: StudyStore? = nil
    var partnerStore: PartnerStore? = nil
    var aiStore: AIProgressStore? = nil
    @State private var enrollmentID: String?
    @State private var deviceError: String?
    private var appVersion: String { Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "—" }
    var body: some View {
        List {
            if let profile = authSession.profile {
                Section("Ваш профиль") {
                    LabeledContent("Имя", value: profile.displayName ?? "Не указано")
                    NavigationLink("Изменить профиль") { EditProfileView(authSession: authSession, profile: profile) }
                }
            }
            if let studyStore {
                Section("Занятия") {
                    NavigationLink("Стартовая проверка") { DiagnosticView(service: LearningQualityService(apiClient: studyStore.api)) }
                    Text("50 учебных дней · 30 новых единиц в день").foregroundStyle(AluaColors.secondaryText)
                    if !studyStore.disk.queue.isEmpty || studyStore.error != nil { StudySyncNotice(store: studyStore) }
                }
            }
            if let partnerStore, let aiStore {
                Section { NavigationLink("Совместный прогресс") { PartnerView(store: partnerStore, aiStore: aiStore) } }
            }
            Section("О приложении") {
                LabeledContent("Версия", value: appVersion)
                Text("alua. — ваш учебник IELTS Vocabulary").font(.body)
                Text("Редакторский каталог для закрытого использования. Независимая проверка преподавателем ещё не завершена.").font(.footnote).foregroundStyle(AluaColors.secondaryText)
            }
            Section {
                DisclosureGroup("Привязка устройства") {
                    if let uid = authSession.profile?.uid { LabeledContent("Learner ID") { Text(uid).textSelection(.enabled) } }
                    if let enrollmentID { LabeledContent("Устройство") { Text(enrollmentID).textSelection(.enabled) } }
                    if let deviceError { Text(deviceError).foregroundStyle(.red) }
                    Button("Проверить устройство") { Task { await loadDeviceID() } }.frame(minHeight: 44)
                    Text("Для смены профиля нужна доверенная повторная привязка. История обучения остаётся у вашего профиля.").font(.footnote).foregroundStyle(AluaColors.secondaryText)
                }
            }
            #if DEBUG
            Section {
                DisclosureGroup("Диагностика приложения") {
                    LabeledContent("Окружение", value: environment.rawValue)
                    Text(environment.apiBaseURL.absoluteString).textSelection(.enabled)
                }
            }
            #endif
        }.listStyle(.insetGrouped).scrollContentBackground(.hidden).background(AluaColors.cardBackground)
            .navigationTitle("Настройки").navigationBarTitleDisplayMode(.inline)
            .task { await loadDeviceID() }
    }
    private func loadDeviceID() async {
        enrollmentID = nil; deviceError = nil
        do { enrollmentID = try await authSession.currentDeviceID() }
        catch { deviceError = "Не удалось проверить устройство. Повторите при доступной сети." }
    }
}
