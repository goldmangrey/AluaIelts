import Foundation

private struct DeviceEnrollmentRequest: Encodable, Sendable {
    let code: String
    let deviceName: String?
    enum CodingKeys: String, CodingKey { case code; case deviceName = "device_name" }
}

struct LinkedDevice: Decodable, Sendable {
    let enrollmentID: String
    let isCurrent: Bool
    enum CodingKeys: String, CodingKey {
        case enrollmentID = "enrollment_id"
        case isCurrent = "is_current"
    }
}
private struct LinkedDevices: Decodable, Sendable { let devices: [LinkedDevice] }

struct DeviceEnrollmentResponse: Decodable, Sendable {
    let token: String
    let enrollmentID: String
    let profile: UserProfile

    enum CodingKeys: String, CodingKey {
        case token, profile
        case enrollmentID = "enrollment_id"
    }
}

private struct DeviceRevocationResponse: Decodable, Sendable {
    let revoked: Bool
}

protocol EnrollmentServiceProtocol: Sendable {
    func enroll(code: String, deviceName: String?) async throws -> DeviceEnrollmentResponse
    func revokeCurrentDevice() async throws
    func currentDeviceID() async throws -> String
}

final class EnrollmentService: EnrollmentServiceProtocol, Sendable {
    private let apiClient: any APIClientProtocol

    init(apiClient: any APIClientProtocol) {
        self.apiClient = apiClient
    }

    func enroll(code: String, deviceName: String?) async throws -> DeviceEnrollmentResponse {
        try await apiClient.send(
            APIEndpoint(
                path: "/api/v1/enrollment",
                method: .post,
                body: DeviceEnrollmentRequest(code: code, deviceName: deviceName)
            ),
            responseType: DeviceEnrollmentResponse.self
        )
    }

    func currentDeviceID() async throws -> String {
        let result = try await apiClient.send(
            APIEndpoint(path: "/api/v1/devices", requiresAuthentication: true),
            responseType: LinkedDevices.self
        )
        guard let device = result.devices.first(where: { $0.isCurrent }) else { throw APIError.invalidResponse }
        return device.enrollmentID
    }

    func revokeCurrentDevice() async throws {
        let response = try await apiClient.send(
            APIEndpoint(path: "/api/v1/device", method: .delete, requiresAuthentication: true),
            responseType: DeviceRevocationResponse.self
        )
        guard response.revoked else { throw APIError.invalidResponse }
    }
}
