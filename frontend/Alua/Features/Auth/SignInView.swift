import SwiftUI

struct SignInView: View {
    let authSession: AuthSession
    @State private var email = ""
    @State private var password = ""
    @FocusState private var focusedField: Field?

    private enum Field {
        case email
        case password
    }

    private var canSubmit: Bool {
        email.contains("@") && !password.isEmpty && !authSession.isAuthenticating
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: AluaSpacing.xl) {
                VStack(alignment: .leading, spacing: AluaSpacing.sm) {
                    Text("Alua").font(AluaTypography.largeTitle)
                    Text("IELTS Learning Companion")
                        .font(AluaTypography.body)
                        .foregroundStyle(AluaColors.secondaryText)
                }

                VStack(spacing: AluaSpacing.md) {
                    TextField("Email", text: $email)
                        .keyboardType(.emailAddress)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .textContentType(.username)
                        .focused($focusedField, equals: .email)
                        .submitLabel(.next)
                        .onSubmit { focusedField = .password }

                    SecureField("Password", text: $password)
                        .textContentType(.password)
                        .focused($focusedField, equals: .password)
                        .submitLabel(.go)
                        .onSubmit { submitIfPossible() }
                }
                .textFieldStyle(.roundedBorder)

                if let error = authSession.authenticationError {
                    Label(error, systemImage: "exclamationmark.circle")
                        .font(AluaTypography.subheadline)
                        .foregroundStyle(.red)
                        .accessibilityLabel("Authentication error: \(error)")
                }

                PrimaryButton(
                    title: authSession.isAuthenticating ? "Signing In…" : "Sign In",
                    isDisabled: !canSubmit
                ) {
                    Task { await authSession.signIn(email: email, password: password) }
                }

                HStack(spacing: AluaSpacing.xs) {
                    Text("Don’t have an account?")
                        .foregroundStyle(AluaColors.secondaryText)
                    NavigationLink("Create Account") {
                        SignUpView(authSession: authSession)
                    }
                    .fontWeight(.semibold)
                }
                .font(AluaTypography.subheadline)
                .frame(maxWidth: .infinity)
            }
            .padding(AluaSpacing.lg)
            .frame(maxWidth: 520)
            .frame(maxWidth: .infinity)
        }
        .background(AluaColors.background)
        .navigationBarTitleDisplayMode(.inline)
    }

    private func submitIfPossible() {
        guard canSubmit else { return }
        Task { await authSession.signIn(email: email, password: password) }
    }
}
