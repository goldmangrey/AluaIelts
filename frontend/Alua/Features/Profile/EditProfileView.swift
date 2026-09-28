import SwiftUI

struct EditProfileView: View {
    let authSession: AuthSession
    let profile: UserProfile

    @Environment(\.dismiss) private var dismiss
    @State private var displayName: String
    @State private var level: EnglishLevel
    @State private var targetBand: Double
    @State private var studyMinutes: Int
    @State private var isSaving = false
    @State private var errorMessage: String?

    private let studyOptions = [15, 30, 45, 60, 90]

    init(authSession: AuthSession, profile: UserProfile) {
        self.authSession = authSession
        self.profile = profile
        _displayName = State(initialValue: profile.displayName ?? "")
        _level = State(initialValue: profile.currentLevel ?? .a1)
        _targetBand = State(initialValue: profile.targetIELTSBand ?? 6.5)
        _studyMinutes = State(initialValue: profile.dailyStudyMinutes ?? 30)
    }

    var body: some View {
        Form {
            Section("Profile") {
                TextField("Display Name", text: $displayName)
                    .textContentType(.name)
            }

            Section("Learning Preferences") {
                Picker("Current Level", selection: $level) {
                    ForEach(EnglishLevel.allCases) { level in
                        Text(level.rawValue).tag(level)
                    }
                }
                Picker("Target IELTS", selection: $targetBand) {
                    ForEach(Array(stride(from: 4.0, through: 9.0, by: 0.5)), id: \.self) { band in
                        Text(band.formatted(.number.precision(.fractionLength(1)))).tag(band)
                    }
                }
                Picker("Daily Study", selection: $studyMinutes) {
                    ForEach(studyOptions, id: \.self) { minutes in
                        Text("\(minutes) minutes").tag(minutes)
                    }
                }
            }

            if let errorMessage {
                Section {
                    Label(errorMessage, systemImage: "exclamationmark.circle")
                        .foregroundStyle(.red)
                }
            }
        }
        .navigationTitle("Edit Profile")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .confirmationAction) {
                Button(isSaving ? "Saving…" : "Save") {
                    Task { await save() }
                }
                .disabled(
                    isSaving || displayName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                )
            }
        }
    }

    private func save() async {
        isSaving = true
        errorMessage = nil
        defer { isSaving = false }
        do {
            try await authSession.updateProfile(
                UserProfileUpdate(
                    displayName: displayName.trimmingCharacters(in: .whitespacesAndNewlines),
                    currentLevel: level,
                    targetIELTSBand: targetBand,
                    dailyStudyMinutes: studyMinutes
                )
            )
            dismiss()
        } catch {
            if let localizedError = error as? LocalizedError,
               let message = localizedError.errorDescription
            {
                errorMessage = message
            } else {
                errorMessage = "The profile could not be saved."
            }
        }
    }
}
