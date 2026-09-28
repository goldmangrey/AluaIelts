enum AppTab: Hashable {
    case today
    case learn
    case progress
    case partner

    var title: String {
        switch self {
        case .today: "Today"
        case .learn: "Learn"
        case .progress: "Progress"
        case .partner: "Partner"
        }
    }

    var systemImage: String {
        switch self {
        case .today: "sun.max"
        case .learn: "book.closed"
        case .progress: "chart.line.uptrend.xyaxis"
        case .partner: "person.2"
        }
    }
}
