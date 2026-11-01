enum AppTab: Hashable, CaseIterable {
    case today, book, practice
    var title: String {
        switch self { case .today: "Сегодня"; case .book: "Моя книга"; case .practice: "Практика" }
    }
    var systemImage: String {
        switch self { case .today: "sun.max"; case .book: "book.closed"; case .practice: "square.grid.2x2" }
    }
}
