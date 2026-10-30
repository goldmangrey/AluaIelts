enum AppTab: Hashable, CaseIterable {
    case today, book, progress
    var title: String {
        switch self { case .today: "Сегодня"; case .book: "Моя книга"; case .progress: "Прогресс" }
    }
    var systemImage: String {
        switch self { case .today: "sun.max"; case .book: "book.closed"; case .progress: "chart.bar" }
    }
}
