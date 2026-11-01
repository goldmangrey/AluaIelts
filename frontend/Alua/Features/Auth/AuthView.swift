import SwiftUI

struct AuthView: View {
    let authSession: AuthSession
    @State private var registering = false
    @State private var name = ""
    @State private var email = ""
    @State private var password = ""
    @State private var confirmation = ""
    @State private var showPassword = false
    @State private var showConfirmation = false
    @State private var resetting = false
    @FocusState private var focus: Field?
    private enum Field { case name, email, password, confirmation }

    static func validEmail(_ value: String) -> Bool {
        let value = value.trimmingCharacters(in: .whitespacesAndNewlines)
        return value.count <= 254 && value.range(of: #"^[^\s@]+@[^\s@]+\.[^\s@]+$"#, options: .regularExpression) != nil
    }
    static func validRegistration(name: String, email: String, password: String, confirmation: String) -> Bool {
        let name = name.trimmingCharacters(in: .whitespacesAndNewlines)
        return !name.isEmpty && name.count <= 80 && validEmail(email)
            && (8...128).contains(password.count) && password == confirmation
    }
    private var valid: Bool {
        registering ? Self.validRegistration(name: name, email: email, password: password, confirmation: confirmation)
            : Self.validEmail(email) && !password.isEmpty
    }
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 24) {
                    VStack(spacing: 8) {
                        Text("Alua.").font(.largeTitle.bold())
                        Text("Your English learning companion").font(.subheadline).foregroundStyle(AluaColors.secondaryText)
                    }.padding(.top, 24)
                    VStack(spacing: 8) {
                        Text(registering ? "Создать аккаунт" : "С возвращением").font(.title2.bold())
                        if !registering { Text("Войди, чтобы продолжить обучение.").foregroundStyle(AluaColors.secondaryText) }
                    }
                    VStack(alignment: .leading, spacing: 12) {
                        if registering {
                            Text("Имя").font(.subheadline)
                            TextField("Ваше имя", text: $name).textContentType(.name)
                                .focused($focus, equals: .name).submitLabel(.next)
                                .onSubmit { focus = .email }.accessibilityLabel("Имя")
                                .accessibilityIdentifier("auth.name")
                                .padding().background(AluaColors.cardBackground, in: RoundedRectangle(cornerRadius: 12))
                        }
                        Text("Электронная почта").font(.subheadline)
                        TextField("you@example.com", text: $email)
                            .keyboardType(.emailAddress).textContentType(.username)
                            .textInputAutocapitalization(.never).autocorrectionDisabled()
                            .focused($focus, equals: .email).submitLabel(.next)
                            .onSubmit { focus = .password }
                            .accessibilityLabel("Электронная почта").accessibilityIdentifier("auth.email")
                            .padding().background(AluaColors.cardBackground, in: RoundedRectangle(cornerRadius: 12))
                        passwordField("Пароль", value: $password, visible: $showPassword, field: .password)
                        if registering {
                            Text("От 8 до 128 символов.").font(.footnote).foregroundStyle(AluaColors.secondaryText)
                            passwordField("Повторите пароль", value: $confirmation, visible: $showConfirmation, field: .confirmation)
                            if !confirmation.isEmpty && password != confirmation {
                                Text("Пароли не совпадают.").font(.footnote).foregroundStyle(.red)
                            }
                        }
                        if let error = authSession.selectionError {
                            Text(error).font(.subheadline).foregroundStyle(.red).accessibilityIdentifier("auth.error")
                        }
                        Button(registering ? "Создать аккаунт" : "Войти", action: submit)
                            .buttonStyle(AluaPrimaryStyle()).disabled(!valid || authSession.isSelectingProfile)
                            .accessibilityIdentifier(registering ? "auth.create" : "auth.login")
                        if authSession.isSelectingProfile { SwiftUI.ProgressView(registering ? "Создаём аккаунт…" : "Входим…") }
                    }
                    if !registering {
                        Button("Забыли пароль?") { resetting = true }.frame(minHeight: 44)
                            .accessibilityIdentifier("auth.reset")
                    }
                    Button(registering ? "Уже есть аккаунт? Войти" : "Зарегистрироваться") {
                        registering.toggle(); password = ""; confirmation = ""
                        authSession.selectionError = nil; focus = nil
                    }.frame(minHeight: 44).disabled(authSession.isSelectingProfile)
                        .accessibilityIdentifier("auth.toggleRegistration")
                }.padding(24).frame(maxWidth: 480).frame(maxWidth: .infinity)
            }.scrollDismissesKeyboard(.interactively)
                .sheet(isPresented: $resetting) { PasswordResetView(authSession: authSession, initialEmail: email) }
        }.tint(AluaColors.accent).preferredColorScheme(.light)
    }

    @ViewBuilder
    private func passwordField(_ title: String, value: Binding<String>, visible: Binding<Bool>, field: Field) -> some View {
        Text(title).font(.subheadline)
        HStack {
            Group {
                if visible.wrappedValue { TextField(title, text: value) }
                else { SecureField(title, text: value) }
            }.textContentType(registering ? .newPassword : .password)
                .textInputAutocapitalization(.never).autocorrectionDisabled()
                .focused($focus, equals: field)
                .submitLabel(registering && field == .password ? .next : .go)
                .onSubmit { if registering && field == .password { focus = .confirmation } else { submit() } }
                .accessibilityLabel(title)
                .accessibilityIdentifier(field == .confirmation ? "auth.confirmation" : "auth.password")
            Button(visible.wrappedValue ? "Hide" : "Show") { visible.wrappedValue.toggle() }
                .accessibilityLabel(field == .confirmation
                    ? (visible.wrappedValue ? "Скрыть повтор пароля" : "Показать повтор пароля")
                    : (visible.wrappedValue ? "Скрыть пароль" : "Показать пароль"))
                .accessibilityIdentifier(field == .confirmation ? "auth.confirmationVisibility" : "auth.passwordVisibility")
                .frame(minHeight: 44)
        }.padding(.horizontal).background(AluaColors.cardBackground, in: RoundedRectangle(cornerRadius: 12))
    }
    private func submit() {
        guard valid, !authSession.isSelectingProfile else { return }
        focus = nil
        let secret = password, isSignup = registering
        password = ""; confirmation = ""
        Task {
            if isSignup { await authSession.signUp(name: name, email: email, password: secret) }
            else { await authSession.signIn(email: email, password: secret) }
        }
    }
}

private struct PasswordResetView: View {
    let authSession: AuthSession
    @State private var email: String
    @State private var loading = false
    @State private var message: String?
    @Environment(\.dismiss) private var dismiss
    init(authSession: AuthSession, initialEmail: String) {
        self.authSession = authSession
        _email = State(initialValue: initialEmail)
    }
    var body: some View {
        NavigationStack {
            Form {
                Text("Укажи свой email.")
                TextField("email@example.com", text: $email)
                    .keyboardType(.emailAddress).textContentType(.emailAddress)
                    .textInputAutocapitalization(.never).autocorrectionDisabled()
                    .accessibilityLabel("Электронная почта для восстановления")
                Button("Отправить письмо") {
                    loading = true
                    Task {
                        defer { loading = false }
                        do {
                            try await authSession.resetPassword(email: email)
                            message = "Если для этого адреса доступно восстановление, письмо с инструкциями будет отправлено."
                        } catch { message = "Не удалось отправить запрос. Проверьте соединение и попробуйте позже." }
                    }
                }.disabled(loading || !AuthView.validEmail(email))
                if loading { SwiftUI.ProgressView() }
                if let message { Text(message) }
            }.navigationTitle("Восстановление пароля").navigationBarTitleDisplayMode(.inline)
                .toolbar { ToolbarItem(placement: .cancellationAction) { Button("Закрыть") { dismiss() } } }
        }
    }
}
