import Foundation
import Combine
import SwiftUI
import LocalAuthentication

@MainActor
final class AegisIOSViewModel: ObservableObject {
    @Published var actions: [ActionCard] = []
    @Published var isSessionActive: Bool = false
    @Published var pendingRedAuth: RedAuthRequest? = nil
    @Published var lastAuthResult: AuthResult? = nil

    enum AuthResult { case approved, denied }

    private var firestoreClient = FirestoreClient()
    private var cancellables = Set<AnyCancellable>()
    private let baseURL = "https://guardian-backend-1090554066699.us-central1.run.app"

    init() {
        setupHandlers()
        firestoreClient.startListening()
    }

    private func setupHandlers() {
        firestoreClient.actionPublisher
            .sink { [weak self] actions in self?.actions = actions }
            .store(in: &cancellables)

        firestoreClient.sessionActivePublisher
            .sink { [weak self] isActive in self?.isSessionActive = isActive }
            .store(in: &cancellables)

        firestoreClient.redAuthPublisher
            .sink { [weak self] request in self?.pendingRedAuth = request }
            .store(in: &cancellables)
    }

    func stopSession() {
        guard let url = URL(string: "\(baseURL)/session/stop") else { return }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"

        URLSession.shared.dataTask(with: request) { _, _, _ in }.resume()
    }

    func approveRedAuth(id: String) {
        let context = LAContext()
        var error: NSError?

        if context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &error) {
            context.evaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, localizedReason: "Approve high-risk action") { success, _ in
                DispatchQueue.main.async {
                    if success {
                        self.sendAuthResponse(id: id, approved: true)
                        self.lastAuthResult = .approved
                    } else {
                        self.sendAuthResponse(id: id, approved: false)
                        self.lastAuthResult = .denied
                    }
                    self.pendingRedAuth = nil
                }
            }
        } else {
            // Fallback to passcode or deny
            self.sendAuthResponse(id: id, approved: false)
            self.lastAuthResult = .denied
            self.pendingRedAuth = nil
        }
    }

    func denyRedAuth(id: String) {
        sendAuthResponse(id: id, approved: false)
        self.lastAuthResult = .denied
        self.pendingRedAuth = nil
    }

    private func sendAuthResponse(id: String, approved: Bool) {
        guard let url = URL(string: "\(baseURL)/auth/approve/\(id)") else { return }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let body = ["approved": approved]
        request.httpBody = try? JSONEncoder().encode(body)

        URLSession.shared.dataTask(with: request) { _, _, _ in }.resume()
    }

    func clearAuthResult() {
        lastAuthResult = nil
    }
}
