import Foundation

struct RedAuthRequest: Codable, Identifiable {
    let id: String
    let action: String
    let reason: String
    let tool: String
    let toolkit: String
    let requestedAt: Date
    var expiresAt: Date

    enum CodingKeys: String, CodingKey {
        case id, action, reason, tool, toolkit
        case requestedAt = "requested_at"
        case expiresAt = "expires_at"
    }
}
