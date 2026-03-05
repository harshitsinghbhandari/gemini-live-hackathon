import SwiftUI

struct ActionCard: Identifiable, Codable, Equatable {
    let id: String
    let timestamp: Date
    let action: String
    let tier: TierLevel
    let tool: String?
    let toolkit: String?
    let reason: String
    let upgraded: Bool
    let speak: String
    let authUsed: Bool
    let blocked: Bool
    let success: Bool
    let durationMs: Int

    enum TierLevel: String, Codable {
        case green  = "GREEN"
        case yellow = "YELLOW"
        case red    = "RED"

        var color: Color {
            switch self {
            case .green:  return Color(hex: "16a34a")
            case .yellow: return Color(hex: "ca8a04")
            case .red:    return Color(hex: "dc2626")
            }
        }

        var icon: String {
            switch self {
            case .green:  return "checkmark.circle.fill"
            case .yellow: return "exclamationmark.circle.fill"
            case .red:    return "lock.shield.fill"
            }
        }
    }

    enum CodingKeys: String, CodingKey {
        case id, timestamp, action, tier, tool, toolkit, reason, upgraded, speak
        case authUsed = "auth_used"
        case blocked, success
        case durationMs = "duration_ms"
    }
}
