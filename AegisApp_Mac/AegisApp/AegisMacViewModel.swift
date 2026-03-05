import Foundation
import Combine
import SwiftUI

@MainActor
final class AegisMacViewModel: ObservableObject {
    @Published var status: AgentStatus = .idle
    @Published var actions: [ActionCard] = []
    @Published var sessionDuration: Int = 0
    @Published var waveformValues: [Float] = Array(repeating: 0.0, count: 10)
    @Published var pendingYellow: YellowConfirmRequest? = nil
    @Published var pendingRed: RedAuthRequest? = nil
    @Published var isSessionActive: Bool = false

    private var wsClient = WebSocketClient()
    private var sessionTimer: AnyCancellable?
    private var agentProcess: Process?
    private var cancellables = Set<AnyCancellable>()

    init() {
        setupWebSocketHandlers()
    }

    private func setupWebSocketHandlers() {
        wsClient.statusPublisher
            .sink { [weak self] status in self?.status = status }
            .store(in: &cancellables)

        wsClient.actionPublisher
            .sink { [weak self] card in
                withAnimation(.spring(response: 0.4, dampingFraction: 0.7)) {
                    self?.actions.insert(card, at: 0)
                    if (self?.actions.count ?? 0) > 20 {
                        self?.actions.removeLast()
                    }
                }
            }
            .store(in: &cancellables)

        wsClient.yellowConfirmPublisher
            .sink { [weak self] request in self?.pendingYellow = request }
            .store(in: &cancellables)

        wsClient.redAuthStartedPublisher
            .sink { [weak self] request in
                self?.pendingRed = request
                self?.pollRedAuth(id: request.id)
            }
            .store(in: &cancellables)

        wsClient.redAuthResultPublisher
            .sink { [weak self] approved in
                self?.pendingRed = nil
            }
            .store(in: &cancellables)

        wsClient.sessionStartedPublisher
            .sink { [weak self] in
                self?.actions.removeAll()
                self?.isSessionActive = true
                self?.startTimer()
            }
            .store(in: &cancellables)

        wsClient.sessionEndedPublisher
            .sink { [weak self] in
                self?.isSessionActive = false
                self?.stopTimer()
            }
            .store(in: &cancellables)

        wsClient.waveformPublisher
            .sink { [weak self] values in
                withAnimation(.easeInOut(duration: 0.1)) {
                    self?.waveformValues = values
                }
            }
            .store(in: &cancellables)
    }

    func startSession() {
        guard !isSessionActive else { return }

        do {
            let repoPath = try KeychainHelper.read(key: "aegis_repo_path")

            let process = Process()
            process.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
            process.arguments = ["\(repoPath)/main.py"]

            process.environment = [
                "GOOGLE_API_KEY":    try KeychainHelper.read(key: "google_api_key"),
                "COMPOSIO_API_KEY":  try KeychainHelper.read(key: "composio_api_key"),
                "BACKEND_URL":       Config.backendURL,
                "DEVICE_ID":         Config.deviceID
            ]

            try process.run()
            self.agentProcess = process
            self.isSessionActive = true
            wsClient.connect()
        } catch {
            self.status = .error("Failed to start agent: \(error.localizedDescription)")
        }
    }

    func stopSession() {
        agentProcess?.terminate()
        agentProcess = nil
        wsClient.disconnect()

        isSessionActive = false
        status = .idle
        actions.removeAll()
        waveformValues = Array(repeating: 0.0, count: 10)
        pendingYellow = nil
        pendingRed = nil
        stopTimer()
        sessionDuration = 0
    }

    func respondToYellow(confirmed: Bool) {
        if let id = pendingYellow?.id {
            wsClient.sendYellowResponse(id: id, confirmed: confirmed)
        }
        pendingYellow = nil
    }

    func pollRedAuth(id: String) {
        Timer.scheduledTimer(withTimeInterval: 2.0, repeats: true) { [weak self] timer in
            guard let self = self, self.pendingRed?.id == id else {
                timer.invalidate()
                return
            }

            Task {
                let url = URL(string: "\(Config.backendURL)/auth/status/\(id)")!
                do {
                    let (data, _) = try await URLSession.shared.data(from: url)
                    let statusObj = try JSONDecoder().decode(AuthStatusResponse.self, from: data)

                    if statusObj.status == "approved" {
                        self.pendingRed = nil
                        timer.invalidate()
                    } else if statusObj.status == "denied" {
                        self.pendingRed = nil
                        timer.invalidate()
                    }
                } catch {
                    print("Polling error: \(error)")
                }
            }

            // Auto-deny timeout check (30s)
            if let requestedAt = self.pendingRed?.requestedAt,
               Date().timeIntervalSince(requestedAt) > 30 {
                self.pendingRed = nil
                timer.invalidate()
            }
        }
    }

    private func startTimer() {
        sessionDuration = 0
        sessionTimer = Timer.publish(every: 1, on: .main, in: .common).autoconnect().sink { [weak self] _ in
            self?.sessionDuration += 1
        }
    }

    private func stopTimer() {
        sessionTimer?.cancel()
        sessionTimer = nil
    }
}

struct AuthStatusResponse: Codable {
    let status: String
}
