import XCTest

/// Production UI with real local Stage 2 API. Runner provisions a disposable device/DB.
final class ReadingUITests: XCTestCase {
    func testPracticeFromLibraryThroughResultsAndReview() throws {
        continueAfterFailure = false
        let file = URL(fileURLWithPath: "/tmp/alua-reading-stage3-contract.json")
        guard let data = try? Data(contentsOf: file) else { throw XCTSkip("Use frontend/scripts/check_reading.py") }
        let config = try JSONSerialization.jsonObject(with: data) as! [String: String]
        let app = XCUIApplication()
        app.launchArguments = ["-AppleLanguages", "(en)", "-AppleLocale", "en_US"]
        app.launch()
        // Keep presses long enough for the headless simulator to deliver both touch phases.
        let code = app.secureTextFields.firstMatch
        if code.waitForExistence(timeout: 10) {
            focus(code, in: app)
            // A numeric 32-character hex code is valid under the unchanged enrollment schema.
            // Fresh simulator OTP keyboards drop synthetic A-F key events.
            code.typeText(config["ui_code"]! + "\n") // native onSubmit avoids keyboard scroll/tap races
        }
        XCTAssertTrue(app.tabBars.buttons["Практика"].waitForExistence(timeout: 30))
        XCTAssertEqual(app.tabBars.buttons.count, 3)
        app.tabBars.buttons["Практика"].press(forDuration: 0.15)
        let book = app.buttons["reading.book.18"]
        navigate(app.buttons["practice.reading"], to: book, timeout: 60)
        for _ in 0..<5 where !book.isHittable { app.swipeUp() }
        let test = app.buttons["reading.test.1"]
        navigate(book, to: test)
        let practice = app.buttons["reading.start.practice"]
        navigate(test, to: practice)
        practice.press(forDuration: 0.15)
        let expand = app.buttons["reading.question.expand"]
        XCTAssertTrue(expand.waitForExistence(timeout: 30))
        XCTAssertFalse(app.tabBars.buttons["Практика"].isHittable)
        expand.press(forDuration: 0.15); expand.press(forDuration: 0.15) // native medium, then expanded
        let answer = app.descendants(matching: .any)["reading.answer.1"].firstMatch
        XCTAssertTrue(answer.waitForExistence(timeout: 10)); focus(answer, in: app); answer.typeText("lettuces")
        let done = app.buttons["Готово"].firstMatch
        XCTAssertTrue(done.waitForExistence(timeout: 10)); done.press(forDuration: 0.15)
        let finish = app.buttons["reading.finish"]
        XCTAssertTrue(finish.waitForExistence(timeout: 10)); finish.press(forDuration: 0.15)
        let submit = app.buttons["Завершить и проверить"]
        XCTAssertTrue(submit.waitForExistence(timeout: 10)); submit.press(forDuration: 0.15)
        XCTAssertTrue(app.navigationBars["Результат"].waitForExistence(timeout: 30))
        XCTAssertTrue(app.staticTexts["1 / 13 верно"].exists)
        reveal(app.buttons["reading.review"], in: app)
        app.buttons["reading.review"].press(forDuration: 0.15)
        XCTAssertTrue(app.navigationBars["Разбор ответов"].waitForExistence(timeout: 10))
        app.segmentedControls.buttons["Все"].press(forDuration: 0.15)
        XCTAssertTrue(app.staticTexts["Ваш ответ: lettuces"].waitForExistence(timeout: 10))
        reveal(app.buttons["Открыть Passage 1"].firstMatch, in: app)
        app.buttons["Открыть Passage 1"].firstMatch.press(forDuration: 0.15)
        XCTAssertTrue(app.navigationBars["Urban farming"].waitForExistence(timeout: 10))
    }
    private func reveal(_ element: XCUIElement, in app: XCUIApplication) {
        for _ in 0..<8 {
            if element.exists && element.isHittable { return }
            app.swipeUp()
        }
        XCTAssertTrue(element.exists && element.isHittable)
    }
    private func focus(_ field: XCUIElement, in app: XCUIApplication) {
        field.tap()
        if !app.keyboards.firstMatch.waitForExistence(timeout: 5) { field.tap() }
        XCTAssertTrue(app.keyboards.firstMatch.waitForExistence(timeout: 10))
    }
    private func navigate(_ link: XCUIElement, to destination: XCUIElement, timeout: TimeInterval = 15) {
        XCTAssertTrue(link.waitForExistence(timeout: 10))
        link.press(forDuration: 0.2)
        if destination.waitForExistence(timeout: timeout) { return }
        // Retry only navigation, only while the original link is still visible.
        // Never replay a start, answer, check or submit action this way.
        if link.exists && link.isHittable { link.press(forDuration: 0.2) }
        XCTAssertTrue(destination.waitForExistence(timeout: timeout))
    }
}
