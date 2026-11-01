import XCTest

final class FirebaseLoginUITests: XCTestCase {
    @MainActor
    func testRegistrationFormValidationAndReturnToLogin() {
        let app = XCUIApplication()
        app.launchArguments = ["-AppleLanguages", "(en)", "-AppleLocale", "en_US"]
        app.launch()
        XCTAssertTrue(app.textFields["auth.email"].waitForExistence(timeout: 20))
        app.swipeUp()
        let toggle = app.buttons["auth.toggleRegistration"]
        XCTAssertTrue(toggle.waitForExistence(timeout: 5))
        toggle.press(forDuration: 0.2)
        let name = app.textFields["auth.name"]
        if !name.waitForExistence(timeout: 5), toggle.label == "Зарегистрироваться" {
            // A simulator can drop the initial tap; retry only while still on Login.
            toggle.press(forDuration: 0.2)
        }
        XCTAssertTrue(name.waitForExistence(timeout: 5))
        if !name.isHittable { app.swipeDown() }
        name.tap(); name.typeText("New Learner")
        let email = app.textFields["auth.email"]
        email.tap(); email.typeText("new@example.org")
        app.swipeUp()
        let create = app.buttons["auth.create"]
        XCTAssertTrue(create.waitForExistence(timeout: 5))
        XCTAssertFalse(create.isEnabled)
        XCTAssertTrue(app.secureTextFields["auth.confirmation"].exists)
        app.buttons["auth.confirmationVisibility"].tap()
        XCTAssertTrue(app.textFields["auth.confirmation"].exists)
        // Do not contact Firebase or create a real test account.
        app.swipeUp()
        toggle.press(forDuration: 0.2)
        XCTAssertTrue(app.buttons["auth.login"].waitForExistence(timeout: 5))
        XCTAssertFalse(app.buttons["auth.login"].isEnabled)
    }

    @MainActor
    func testLoginValidationVisibilityAndPasswordResetPresentation() {
        let app = XCUIApplication()
        app.launchArguments = ["-AppleLanguages", "(en)", "-AppleLocale", "en_US"]
        app.launch()
        let email = app.textFields["auth.email"]
        XCTAssertTrue(email.waitForExistence(timeout: 20))
        XCTAssertFalse(app.buttons["auth.login"].isEnabled)
        email.tap()
        email.typeText("invalid")
        XCTAssertFalse(app.buttons["auth.login"].isEnabled)
        app.buttons["Показать пароль"].tap()
        XCTAssertTrue(app.textFields["auth.password"].exists)
        app.buttons["Скрыть пароль"].tap()
        XCTAssertTrue(app.secureTextFields["auth.password"].exists)
        // No real Firebase request or password is used by this rendering test.
        app.swipeUp()
        let reset = app.buttons["auth.reset"]
        XCTAssertTrue(reset.waitForExistence(timeout: 5))
        reset.tap()
        XCTAssertTrue(app.navigationBars["Восстановление пароля"].waitForExistence(timeout: 5))
        XCTAssertFalse(app.buttons["Отправить письмо"].isEnabled)
        app.buttons["Закрыть"].tap()
        XCTAssertTrue(email.waitForExistence(timeout: 5))
    }
}
