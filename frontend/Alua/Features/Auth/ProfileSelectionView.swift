import SwiftUI

struct ProfileSelectionView: View {
    let authSession: AuthSession
    @State private var code = ""
    @FocusState private var codeFocused: Bool
    var body: some View {
        NavigationStack {
            AluaPage {
                Text("alua.").font(.largeTitle.weight(.bold)).padding(.top, 32)
                VStack(alignment: .leading, spacing: 16) {
                    Text("Ваш английский.\nКаждый день.").font(.largeTitle.weight(.semibold))
                    Text("1 500 слов и выражений. Один учебник, к которому всегда можно вернуться.")
                        .font(.title3).foregroundStyle(AluaColors.secondaryText)
                }
                VStack(alignment: .leading, spacing: 14) {
                    Text("Подключите этот iPhone").font(.headline)
                    Text("Введите одноразовый код от владельца. В следующий раз приложение войдёт автоматически.").foregroundStyle(AluaColors.secondaryText)
                    SecureField("Одноразовый код", text: $code)
                        .textContentType(.oneTimeCode).textInputAutocapitalization(.characters).autocorrectionDisabled()
                        .padding(18).background(AluaColors.cardBackground, in: RoundedRectangle(cornerRadius: 14))
                        .focused($codeFocused).submitLabel(.go).onSubmit(enroll).accessibilityLabel("Одноразовый код устройства")
                    Button(authSession.isSelectingProfile ? "Подключаем…" : "Продолжить", action: enroll)
                        .buttonStyle(AluaPrimaryStyle()).disabled(code.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || authSession.isSelectingProfile)
                    if authSession.isSelectingProfile { SwiftUI.ProgressView("Проверяем код") }
                    if let error = authSession.selectionError { Label(error, systemImage: "exclamationmark.circle").font(.subheadline).foregroundStyle(.red) }
                }
                Text("Ваш прогресс связан с профилем и сохраняется после каждого ответа.").font(.footnote).foregroundStyle(AluaColors.secondaryText)
            }.preferredColorScheme(.light)
        }
    }
    private func enroll() {
        guard !code.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty, !authSession.isSelectingProfile else { return }
        let submittedCode = code; code = ""; codeFocused = false
        Task { await authSession.enroll(code: submittedCode) }
    }
}
