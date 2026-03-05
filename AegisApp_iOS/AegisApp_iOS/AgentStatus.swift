import SwiftUI

enum AgentStatus: Equatable {
    case idle
    case listening
    case executing
    case waitingAuth
    case error(String)

    var icon: String {
        switch self {
        case .idle:        return "◈"
        case .listening:   return "◉"
        case .executing:   return "◌"
        case .waitingAuth: return "⊠"
        case .error:       return "⊗"
        }
    }

    var color: Color {
        switch self {
        case .idle:        return .gray
        case .listening:   return Color(hex: "7c3aed")
        case .executing:   return .orange
        case .waitingAuth: return Color(hex: "dc2626")
        case .error:       return Color(hex: "dc2626")
        }
    }
}
