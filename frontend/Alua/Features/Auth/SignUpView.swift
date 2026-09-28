import SwiftUI

struct SignUpView: View {
    let authSession: AuthSession
    @State private var displayName = ""
    @State private var email = ""
    @State private var password = ""
    @State private var confirmation = ""

    private var validationMessage: String? {
        if !confirmation.isEmpty, password != confirmation {
            return "Passwords do not match."
        }
        return nil
    }

    private var canSubmit: Bool {
        !displayName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            && email.contains("@")
            && password.count >= 6
            && password == confirmation
            && !authSession.isAuthenticating
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: AluaSpacing.lg) {
                AluaSectionHeader(
                    title: "Create your account",
                    subtitle: "Start with a simple learner profile."
                )

                VStack(spacing: AluaSpacing.md) {
                    TextField("Display Name", text: $displayName)
                        .textContentType(.name)
                    TextField("Email", text: $email)
                        .keyboardType(.emailAddress)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .textContentType(.username)
                    SecureField("Password", text: $password)
                        .textContentType(.newPassword)
                    SecureField("Confirm Password", text: $confirmation)
                        .textContentType(.newPassword)
                        .submitLabel(.go)
                        .onSubmit { submitIfPossible() }
                }
                .textFieldStyle(.roundedBorder)

                if let message = validationMessage {
                    Text(message)
                        .font(AluaTypography.subheadline)
                        .foregroundStyle(.red)
                } else if let error = authSession.authenticationError {
                    Text(error)
                        .font(AluaTypography.subheadline)
                        .foregroundStyle(.red)
                }

                PrimaryButton(
                    title: authSession.isAuthenticating ? "Creating Account…" : "Create Account",
                    isDisabled: !canSubmit
                ) {
                    Task {
                        await authSession.signUp(
                            displayName: displayName,
                            email: email,
                            password: password
                        )
                    }
                }
            }
            .padding(AluaSpacing.lg)
        }
        .navigationTitle("Create Account")
        .navigationBarTitleDisplayMode(.inline)
    }

    private func submitIfPossible() {
        guard canSubmit else { return }
        Task {
            await authSession.signUp(
                displayName: displayName,
                email: email,
                password: password
            )
        }
    }
}
