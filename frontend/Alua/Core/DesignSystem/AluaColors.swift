import SwiftUI

enum AluaColors {
    static let background = Color(.systemBackground)
    static let secondaryBackground = Color(.secondarySystemBackground)
    static let groupedBackground = Color(.systemBackground)
    static let cardBackground = Color(uiColor: UIColor { traits in
        traits.userInterfaceStyle == .dark ? .secondarySystemBackground : UIColor(red: 245/255, green: 245/255, blue: 247/255, alpha: 1)
    })
    static let primaryText = Color.primary
    // Slightly darker than #767676 to retain contrast on the secondary surface.
    static let secondaryText = Color(uiColor: UIColor { traits in
        traits.userInterfaceStyle == .dark ? .lightGray : UIColor(white: 0.42, alpha: 1)
    })
    static let accent = Color.primary
    static let progressTrack = Color.primary.opacity(0.09)
}
