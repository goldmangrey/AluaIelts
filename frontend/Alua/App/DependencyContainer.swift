import Foundation

struct DependencyContainer {
    let environment: AppEnvironment
    let apiClient: any APIClientProtocol
    let authService: any AuthServiceProtocol
    let userService: any UserServiceProtocol

    @MainActor
    static func live(environment: AppEnvironment = .current) -> DependencyContainer {
        let authService = FirebaseAuthService()
        let apiClient = APIClient(
            baseURL: environment.apiBaseURL,
            tokenProvider: authService
        )
        return DependencyContainer(
            environment: environment,
            apiClient: apiClient,
            authService: authService,
            userService: UserService(apiClient: apiClient)
        )
    }
}
