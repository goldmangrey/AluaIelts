import SwiftUI

struct SettingsView: View {
    let environment: AppEnvironment
    let authSession: AuthSession

    private var appVersion: String {
        Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "—"
    }

    var body: some View {
        List {
            if let profile = authSession.profile {
                Section("Account") {
                    LabeledContent("Display Name", value: profile.displayName ?? "—")
                    LabeledContent("Email", value: profile.email ?? "—")
                    NavigationLink("Edit Profile") {
                        EditProfileView(authSession: authSession, profile: profile)
                    }
                }

                Section("Learning") {
                    LabeledContent("Current Level", value: profile.currentLevel?.rawValue ?? "—")
                    LabeledContent(
                        "Target IELTS Band",
                        value: profile.targetIELTSBand.map { $0.formatted(.number.precision(.fractionLength(1))) } ?? "—"
                    )
                    LabeledContent(
                        "Daily Study Goal",
                        value: profile.dailyStudyMinutes.map { "\($0) min" } ?? "—"
                    )
                }
            }

            Section("About") {
                LabeledContent("App version", value: appVersion)
                LabeledContent("Environment", value: environment.rawValue.capitalized)
            }

            #if DEBUG
            Section("Developer") {
                LabeledContent("API base URL") {
                    Text(environment.apiBaseURL.absoluteString)
                        .foregroundStyle(AluaColors.secondaryText)
                        .multilineTextAlignment(.trailing)
                }
            }
            #endif

            Section {
                Button("Sign Out", role: .destructive) {
                    authSession.signOut()
                }
            }
        }
        .navigationTitle("Settings")
        .navigationBarTitleDisplayMode(.inline)
    }
}
