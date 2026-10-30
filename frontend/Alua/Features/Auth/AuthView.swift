import SwiftUI

struct AuthView: View {
    let authSession: AuthSession

    var body: some View {
        ProfileSelectionView(authSession: authSession)
        .tint(AluaColors.accent)
    }
}
