import Foundation

struct YellowConfirmRequest: Codable, Identifiable {
    let id: String
    let action: String
    let question: String
    let tool: String
    let toolkit: String
}
