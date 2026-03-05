import Foundation
import Combine

class WebSocketClient: NSObject, ObservableObject {
    private var webSocketTask: URLSessionWebSocketTask?
    private let url = URL(string: Config.wsURL)!
    private var reconnectTimer: Timer?

    let statusPublisher = PassthroughSubject<AgentStatus, Never>()
    let actionPublisher = PassthroughSubject<ActionCard, Never>()
    let yellowConfirmPublisher = PassthroughSubject<YellowConfirmRequest, Never>()
    let redAuthStartedPublisher = PassthroughSubject<RedAuthRequest, Never>()
    let redAuthResultPublisher = PassthroughSubject<Bool, Never>()
    let sessionStartedPublisher = PassthroughSubject<Void, Never>()
    let sessionEndedPublisher = PassthroughSubject<Void, Never>()
    let waveformPublisher = PassthroughSubject<[Float], Never>()

    func connect() {
        let session = URLSession(configuration: .default)
        webSocketTask = session.webSocketTask(with: url)
        webSocketTask?.resume()
        receiveMessage()
        reconnectTimer?.invalidate()
    }

    func disconnect() {
        webSocketTask?.cancel(with: .normalClosure, reason: nil)
        reconnectTimer?.invalidate()
    }

    private func receiveMessage() {
        webSocketTask?.receive { [weak self] result in
            switch result {
            case .success(let message):
                switch message {
                case .string(let text):
                    self?.handleMessage(text)
                case .data(let data):
                    if let text = String(data: data, encoding: .utf8) {
                        self?.handleMessage(text)
                    }
                @unknown default:
                    break
                }
                self?.receiveMessage()
            case .failure(let error):
                print("WebSocket error: \(error)")
                self?.scheduleReconnect()
            }
        }
    }

    private func handleMessage(_ text: String) {
        guard let data = text.data(using: .utf8),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let event = json["event"] as? String else { return }

        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601

        DispatchQueue.main.async { [weak self] in
            switch event {
            case "status":
                if let value = json["value"] as? String {
                    switch value {
                    case "idle": self?.statusPublisher.send(.idle)
                    case "listening": self?.statusPublisher.send(.listening)
                    case "executing": self?.statusPublisher.send(.executing)
                    case "auth": self?.statusPublisher.send(.waitingAuth)
                    case "error": self?.statusPublisher.send(.error("Unknown error"))
                    default: break
                    }
                }
            case "action":
                if let dataObj = json["data"] as? [String: Any],
                   let jsonData = try? JSONSerialization.data(withJSONObject: dataObj),
                   let card = try? decoder.decode(ActionCard.self, from: jsonData) {
                    self?.actionPublisher.send(card)
                }
            case "yellow_confirm":
                if let dataObj = json["data"] as? [String: Any],
                   let jsonData = try? JSONSerialization.data(withJSONObject: dataObj),
                   let request = try? decoder.decode(YellowConfirmRequest.self, from: jsonData) {
                    self?.yellowConfirmPublisher.send(request)
                }
            case "red_auth_started":
                if let dataObj = json["data"] as? [String: Any] {
                    var mutableData = dataObj
                    let now = Date()
                    mutableData["requested_at"] = ISO8601DateFormatter().string(from: now)
                    mutableData["expires_at"] = ISO8601DateFormatter().string(from: now.addingTimeInterval(30))

                    if let jsonData = try? JSONSerialization.data(withJSONObject: mutableData),
                       let request = try? decoder.decode(RedAuthRequest.self, from: jsonData) {
                        self?.redAuthStartedPublisher.send(request)
                    }
                }
            case "red_auth_result":
                if let dataObj = json["data"] as? [String: Any],
                   let approved = dataObj["approved"] as? Bool {
                    self?.redAuthResultPublisher.send(approved)
                }
            case "session_started":
                self?.sessionStartedPublisher.send()
            case "session_ended":
                self?.sessionEndedPublisher.send()
            case "waveform":
                if let value = json["value"] as? Float {
                    // ws_server.py sends a single Float (peak)
                    // We use this value to represent the current amplitude
                    // JULES.md says [Float] of bar heights (0.0-1.0, count matches ws_server.py)
                    // Since ws_server.py sends a single value, we treat it as the uniform height for the waveform bars
                    let bars = Array(repeating: value, count: 10)
                    self?.waveformPublisher.send(bars)
                }
            default:
                break
            }
        }
    }

    private func scheduleReconnect() {
        reconnectTimer?.invalidate()
        reconnectTimer = Timer.scheduledTimer(withTimeInterval: 3.0, repeats: false) { [weak self] _ in
            self?.connect()
        }
    }

    func sendYellowResponse(id: String, confirmed: Bool) {
        let message: [String: Any] = [
            "event": "yellow_response",
            "data": [
                "id": id,
                "confirmed": confirmed
            ]
        ]
        if let data = try? JSONSerialization.data(withJSONObject: message),
           let text = String(data: data, encoding: .utf8) {
            webSocketTask?.send(.string(text)) { error in
                if let error = error {
                    print("Error sending yellow_response: \(error)")
                }
            }
        }
    }
}

