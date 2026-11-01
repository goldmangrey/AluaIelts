import XCTest

/// Runs only in AluaQA against scripts.qa.stage5_server on loopback. Uses the production UI/auth.
final class AluaProductQATests: XCTestCase {
    let app = XCUIApplication()
    override func setUpWithError() throws {
        continueAfterFailure = false
        app.launch()
    }
    func shot(_ name: String) {
        Thread.sleep(forTimeInterval: 1) // Let the native navigation/presentation transition settle.
        let screenshot = app.screenshot()
        try? screenshot.pngRepresentation.write(to: FileManager.default.temporaryDirectory.appendingPathComponent("alua-qa-\(name).png"))
        let attachment = XCTAttachment(screenshot: screenshot)
        attachment.name = name; attachment.lifetime = .keepAlways; add(attachment)
    }
    func tap(_ title: String) {
        let button = app.buttons[title].firstMatch
        var attempts = 0
        while !button.isHittable && attempts < 8 { app.swipeUp(); attempts += 1 }
        XCTAssertTrue(button.waitForExistence(timeout: 12), title)
        button.tap()
    }
    func enroll(_ role: String) {
        let field = app.secureTextFields.firstMatch
        if field.waitForExistence(timeout: 5) {
            field.tap(); field.typeText(String(repeating: role == "HUSBAND" ? "1" : "2", count: 32))
            tap("Продолжить")
        }
        XCTAssertTrue(app.tabBars.buttons["Сегодня"].waitForExistence(timeout: 20))
    }
    func nextCard() {
        let next = app.buttons["lesson.next"]
        var attempts = 0
        while !next.isHittable && attempts < 8 { app.swipeUp(); attempts += 1 }
        XCTAssertTrue(next.waitForExistence(timeout: 10)); next.tap()
        // Wait for a changed question/pause to be laid out before another tap.
        usleep(250_000)
    }
    func testPracticeNavigation() {
        verifyPracticeNavigation()
    }
    func testPracticeNavigationWithAccessibilityType() {
        app.terminate()
        app.launchArguments += ["-UIPreferredContentSizeCategoryName", "UICTContentSizeCategoryAccessibilityXXXL"]
        app.launch()
        verifyPracticeNavigation(accessibilityType: true)
    }
    private func verifyPracticeNavigation(accessibilityType: Bool = false) {
        enroll("HUSBAND")
        XCTAssertEqual(app.tabBars.buttons.count, 3)
        XCTAssertFalse(app.tabBars.buttons["Прогресс"].exists)
        app.tabBars.buttons["Сегодня"].tap()
        XCTAssertTrue(app.buttons["study.start"].waitForExistence(timeout: 10))
        app.tabBars.buttons["Моя книга"].tap()
        XCTAssertTrue(app.navigationBars["Моя книга"].waitForExistence(timeout: 10))
        // Book intentionally uses a menu instead of segments at accessibility sizes.
        if !accessibilityType {
            XCTAssertTrue(app.segmentedControls.buttons["Мои слова"].waitForExistence(timeout: 10))
            app.segmentedControls.buttons["Мои слова"].tap()
        }
        app.tabBars.buttons["Практика"].tap()
        let descriptions = ["Чтение и понимание текстов", "Восприятие английской речи", "Академическое письмо", "Разговорная практика"]
        for (index, title) in ["Reading", "Listening", "Writing", "Speaking"].enumerated() {
            let row = app.buttons["practice.\(title.lowercased())"]
            var attempts = 0
            while !row.isHittable && attempts < 8 { app.swipeUp(); attempts += 1 }
            XCTAssertTrue(row.isHittable)
            XCTAssertEqual(row.label, "\(title), \(descriptions[index])")
            XCTAssertGreaterThanOrEqual(row.frame.height, 44)
            row.tap()
            XCTAssertTrue(app.navigationBars[title].waitForExistence(timeout: 5))
            if title == "Reading" {
                XCTAssertTrue(app.staticTexts["IELTS Academic"].exists)
            } else {
                XCTAssertTrue(app.staticTexts["Скоро здесь появятся задания."].exists)
            }
            // The tab's NavigationStack and the book filter survive switching tabs.
            app.tabBars.buttons["Моя книга"].tap()
            XCTAssertTrue(app.navigationBars["Моя книга"].exists)
            if !accessibilityType { XCTAssertTrue(app.segmentedControls.buttons["Мои слова"].isSelected) }
            app.tabBars.buttons["Практика"].tap()
            XCTAssertTrue(app.navigationBars[title].exists)
            app.navigationBars.buttons.element(boundBy: 0).tap()
            XCTAssertTrue(app.navigationBars["Практика"].waitForExistence(timeout: 5))
        }
        shot("practice-navigation")
        app.tabBars.buttons["Сегодня"].tap()
        tap("today.grammar")
        XCTAssertTrue(app.navigationBars["Грамматика"].waitForExistence(timeout: 10))
        app.navigationBars.buttons.element(boundBy: 0).tap()
        tap("today.diagnostic")
        XCTAssertTrue(app.navigationBars["Стартовая проверка"].waitForExistence(timeout: 10))
    }
    func testFirstDay() {
        enroll("HUSBAND")
        shot("01-today-0-modern")
        tap("today.diagnostic")
        for _ in 0..<12 { tap("Не знаю") }
        XCTAssertTrue(app.staticTexts["Отправная точка"].waitForExistence(timeout: 10))
        shot("02-diagnostic-result")
        app.navigationBars.buttons.element(boundBy: 0).tap()
        tap("study.start")
        for _ in 0..<10 { nextCard() }
        XCTAssertTrue(app.staticTexts["Подход завершён"].waitForExistence(timeout: 8))
        shot("03-lesson-pause-10")
        tap("Закончить пока")
        tap("study.start")
        XCTAssertTrue(app.staticTexts["job"].waitForExistence(timeout: 8))
        for _ in 10..<18 { nextCard() }
        tap("Закрыть")
        shot("04-today-18-modern")
        app.terminate(); app.launch()
        tap("study.start")
        XCTAssertTrue(app.staticTexts["street"].waitForExistence(timeout: 10))
        for _ in 18..<20 { nextCard() }
        shot("05-lesson-pause-20")
        tap("Продолжить")
        for _ in 20..<30 { nextCard() }
        XCTAssertTrue(app.staticTexts["День завершён"].waitForExistence(timeout: 8))
        shot("06-day-completed")
        tap("Открыть в моей книге")
        XCTAssertTrue(app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH %@", "book.card.")).firstMatch.waitForExistence(timeout: 8))
        shot("07-completed-day-book")
        tap("Закрыть")
        app.tabBars.buttons["Моя книга"].tap()
        shot("08-book-days-modern")
        app.segmentedControls.buttons["Мои слова"].tap()
        shot("09-book-words-modern")
        app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH %@", "book.card.")).firstMatch.tap()
        shot("10-card-detail-modern")
        tap("Повторить")
        shot("11-review-modern")
        tap("Не знаю")
        XCTAssertTrue(app.descendants(matching: .any).matching(NSPredicate(format: "label CONTAINS %@", "Повторим ещё раз")).firstMatch.waitForExistence(timeout: 8))
        shot("12-review-feedback")
        tap("Закрыть")
        app.navigationBars.buttons.element(boundBy: 0).tap()
        app.tabBars.buttons["Практика"].tap()
        shot("13-practice-modern")
    }
    func testLongExpressionSmallPhone() {
        enroll("WIFE")
        tap("study.start")
        XCTAssertTrue(app.staticTexts["contribute to development"].waitForExistence(timeout: 10))
        shot("14-long-expression-small")
        for _ in 15..<18 { nextCard() }
        tap("Закрыть")
        shot("15-today-18-small")
        app.tabBars.buttons["Моя книга"].tap()
        shot("16-book-days-small")
        app.segmentedControls.buttons["Мои слова"].tap()
        shot("17-book-words-small")
        let search = app.searchFields.firstMatch
        if !search.isHittable { app.swipeDown() }
        search.tap(); search.typeText("неблагоприятное")
        shot("18-search-russian-keyboard-small")
        XCTAssertTrue(app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH %@", "book.card.")).firstMatch.exists)
        app.terminate(); app.launch()
        app.tabBars.buttons["Моя книга"].tap()
        app.segmentedControls.buttons["Мои слова"].tap()
        app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH %@", "book.card.")).firstMatch.tap()
        shot("22-card-detail-small")
        tap("Повторить")
        shot("23-review-small")
    }

    func testBookAndRecallViews() {
        enroll("HUSBAND")
        app.tabBars.buttons["Моя книга"].tap()
        shot("08-book-days-modern")
        app.segmentedControls.buttons["Мои слова"].tap()
        shot("09-book-words-modern")
        let first = app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH %@", "book.card.")).firstMatch
        XCTAssertTrue(first.waitForExistence(timeout: 10)); first.tap()
        shot("10-card-detail-modern")
        tap("Повторить")
        shot("11-review-modern")
        tap("Не знаю")
        XCTAssertTrue(app.descendants(matching: .any).matching(NSPredicate(format: "label CONTAINS %@", "Повторим ещё раз")).firstMatch.waitForExistence(timeout: 10))
        shot("12-review-feedback")
        tap("Закрыть")
        app.navigationBars.buttons.element(boundBy: 0).tap()
        app.tabBars.buttons["Практика"].tap()
        shot("13-practice-modern")
    }
    func testAccessibilitySmallPhone() {
        enroll("WIFE")
        shot("24-today-accessibility-small")
        tap("study.start")
        shot("25-lesson-accessibility-small")
        app.swipeUp()
        shot("26-lesson-accessibility-small-scrolled")
        tap("Закрыть")
        tap("today.grammar")
        XCTAssertTrue(app.navigationBars["Грамматика"].waitForExistence(timeout: 10))
        shot("28-grammar-accessibility-small")
        app.navigationBars.buttons.element(boundBy: 0).tap()
        tap("today.diagnostic")
        XCTAssertTrue(app.navigationBars["Стартовая проверка"].waitForExistence(timeout: 10))
        shot("29-diagnostic-accessibility-small")
    }
}
