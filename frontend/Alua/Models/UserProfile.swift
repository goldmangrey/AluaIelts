import Foundation

enum UserRole: String, Codable, Sendable {
    case learner
    case partner
}

enum EnglishLevel: String, CaseIterable, Codable, Sendable, Identifiable {
    case a1 = "A1"
    case a2 = "A2"
    case b1 = "B1"
    case b2 = "B2"
    case c1 = "C1"
    case c2 = "C2"

    var id: String { rawValue }
}

struct UserProfile: Codable, Sendable, Equatable {
    let uid: String
    let email: String?
    var displayName: String?
    let role: UserRole
    var currentLevel: EnglishLevel?
    var targetIELTSBand: Double?
    var dailyStudyMinutes: Int?
    let createdAt: Date
    var updatedAt: Date

    enum CodingKeys: String, CodingKey {
        case uid, email, role
        case displayName = "display_name"
        case currentLevel = "current_level"
        case targetIELTSBand = "target_ielts_band"
        case dailyStudyMinutes = "daily_study_minutes"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}

struct UserProfileUpdate: Encodable, Sendable {
    let displayName: String?
    let currentLevel: EnglishLevel?
    let targetIELTSBand: Double?
    let dailyStudyMinutes: Int?

    enum CodingKeys: String, CodingKey {
        case displayName = "display_name"
        case currentLevel = "current_level"
        case targetIELTSBand = "target_ielts_band"
        case dailyStudyMinutes = "daily_study_minutes"
    }
}
