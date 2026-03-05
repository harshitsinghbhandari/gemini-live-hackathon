import Foundation
import Combine
import FirebaseFirestore

class FirestoreClient: ObservableObject {
    private let db = Firestore.firestore()

    let actionPublisher = PassthroughSubject<[ActionCard], Never>()
    let sessionActivePublisher = PassthroughSubject<Bool, Never>()
    let redAuthPublisher = PassthroughSubject<RedAuthRequest, Never>()

    private var auditListener: ListenerRegistration?
    private var sessionListener: ListenerRegistration?
    private var authListener: ListenerRegistration?

    func startListening() {
        // Audit Logs
        auditListener = db.collection("audit_log")
            .order(by: "timestamp", descending: true)
            .limit(to: 20)
            .addSnapshotListener { [weak self] querySnapshot, error in
                guard let documents = querySnapshot?.documents else { return }

                let actions = documents.compactMap { doc -> ActionCard? in
                    var data = doc.data()
                    data["id"] = doc.documentID

                    // Handle Firestore Timestamp or String to Date conversion for ActionCard
                    if let timestamp = data["timestamp"] {
                        let decoder = JSONDecoder()
                        if let timestampStr = timestamp as? String {
                            decoder.dateDecodingStrategy = .iso8601
                        } else if let firestoreTimestamp = timestamp as? Timestamp {
                            // If it's a Firestore Timestamp, convert it to ISO8601 string for the decoder
                            data["timestamp"] = ISO8601DateFormatter().string(from: firestoreTimestamp.dateValue())
                            decoder.dateDecodingStrategy = .iso8601
                        }

                        if let jsonData = try? JSONSerialization.data(withJSONObject: data) {
                            return try? decoder.decode(ActionCard.self, from: jsonData)
                        }
                    }
                    return nil
                }
                self?.actionPublisher.send(actions)
            }

        // Session Status
        sessionListener = db.collection("app_state").document("session")
            .addSnapshotListener { [weak self] documentSnapshot, error in
                guard let data = documentSnapshot?.data() else { return }
                let isActive = data["is_active"] as? Bool ?? false
                self?.sessionActivePublisher.send(isActive)
            }

        // Pending Auth
        authListener = db.collection("auth_requests")
            .whereField("status", isEqualTo: "pending")
            .addSnapshotListener { [weak self] querySnapshot, error in
                guard let documents = querySnapshot?.documents, let doc = documents.first else { return }

                var data = doc.data()
                data["id"] = doc.documentID

                let isoFormatter = ISO8601DateFormatter()

                // Firestore Timestamp to ISO8601 String for JSONDecoder
                if let requestedAt = data["created_at"] as? Timestamp {
                    data["requested_at"] = isoFormatter.string(from: requestedAt.dateValue())
                    // Expires in 30 seconds
                    data["expires_at"] = isoFormatter.string(from: requestedAt.dateValue().addingTimeInterval(30))
                }

                let decoder = JSONDecoder()
                decoder.dateDecodingStrategy = .iso8601

                if let jsonData = try? JSONSerialization.data(withJSONObject: data) {
                    if let request = try? decoder.decode(RedAuthRequest.self, from: jsonData) {
                        self?.redAuthPublisher.send(request)
                    }
                }
            }
    }

    func stopListening() {
        auditListener?.remove()
        sessionListener?.remove()
        authListener?.remove()
    }
}
