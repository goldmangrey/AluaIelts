import FirebaseCore
import Foundation

enum FirebaseBootstrap {
    static func configureIfAvailable() -> Bool {
        if FirebaseApp.app() != nil {
            return true
        }
        guard
            let path = Bundle.main.path(forResource: "GoogleService-Info", ofType: "plist"),
            let options = FirebaseOptions(contentsOfFile: path)
        else {
            return false
        }
        FirebaseApp.configure(options: options)
        return true
    }
}
