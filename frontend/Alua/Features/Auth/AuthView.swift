import SwiftUI

struct AuthView: View {
    let authSession: AuthSession

    var body: some View {
        NavigationStack {
            SignInView(authSession: authSession)
        }
        .tint(AluaColors.accent)
    }
}
