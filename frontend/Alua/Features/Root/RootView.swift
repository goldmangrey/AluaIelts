import SwiftUI

struct RootView: View {
    var body: some View {
        NavigationStack {
            VStack(spacing: 16) {
                Text("Alua")
                    .font(.largeTitle.bold())

                Text("IELTS Learning Companion")
                    .foregroundStyle(.secondary)
            }
            .navigationTitle("Today")
        }
    }
}

#Preview {
    RootView()
}
