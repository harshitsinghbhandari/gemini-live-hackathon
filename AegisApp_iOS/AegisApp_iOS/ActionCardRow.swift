import SwiftUI

struct ActionCardRow: View {
    let action: ActionCard
    
    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            // Leading icon with circle background
            ZStack {
                Circle()
                    .fill(action.tier.color.opacity(0.15))
                    .frame(width: 40, height: 40)
                Image(systemName: action.tier.icon)
                    .font(.system(size: 20, weight: .semibold))
                    .foregroundColor(action.tier.color)
            }
            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text(action.action)
                        .font(.headline)
                        .fontWeight(.semibold)
                        .foregroundColor(.white)
                        .lineLimit(1)
                    Spacer()
                    Text(formattedRelativeTime(from: action.timestamp))
                        .font(.caption)
                        .foregroundColor(.white.opacity(0.6))
                        .lineLimit(1)
                }
                Text(action.reason)
                    .font(.subheadline)
                    .foregroundColor(.gray)
                    .lineLimit(1)
                if let tool = action.tool, !tool.isEmpty || (action.toolkit?.isEmpty == false) {
                    HStack(spacing: 4) {
                        if let tool = action.tool, !tool.isEmpty {
                            Text("Tool: \(tool)")
                        }
                        if let toolkit = action.toolkit, !toolkit.isEmpty {
                            if (action.tool != nil && !(action.tool ?? "").isEmpty) {
                                Text("•")
                            }
                            Text("Toolkit: \(toolkit)")
                        }
                    }
                    .font(.caption2)
                    .foregroundColor(.gray)
                    .lineLimit(1)
                }
            }
            Spacer()
            VStack {
                Spacer()
                Text(statusText)
                    .font(.caption2)
                    .fontWeight(.semibold)
                    .foregroundColor(.white)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 3)
                    .background(statusColor)
                    .clipShape(Capsule())
            }
        }
        .padding(12)
        .background(Color.white.opacity(0.03))
        .cornerRadius(12)
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(action.action), \(statusText) status")
    }
    
    private var statusText: String {
        if action.blocked {
            return "Blocked"
        } else if action.success {
            return "Success"
        } else {
            return "Failed"
        }
    }
    
    private var statusColor: Color {
        if action.blocked {
            return .red
        } else if action.success {
            return .green
        } else {
            return .yellow
        }
    }
    
    private func formattedRelativeTime(from date: Date) -> String {
        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .short
        let now = Date()
        let relativeString = formatter.localizedString(for: date, relativeTo: now)
        // If relative time string is too verbose or equals to date, fallback to short time
        if relativeString == "0s ago" || relativeString.isEmpty {
            let timeFormatter = DateFormatter()
            timeFormatter.timeStyle = .short
            return timeFormatter.string(from: date)
        }
        return relativeString
    }
}

#if DEBUG

struct ActionCardRow_Previews: PreviewProvider {
    static var previews: some View {
        Group {
            ActionCardRow(action: sampleActionCardSuccess)
                .preferredColorScheme(.dark)
                .previewLayout(.sizeThatFits)
                .padding()
            ActionCardRow(action: sampleActionCardBlocked)
                .preferredColorScheme(.dark)
                .previewLayout(.sizeThatFits)
                .padding()
            ActionCardRow(action: sampleActionCardFailed)
                .preferredColorScheme(.dark)
                .previewLayout(.sizeThatFits)
                .padding()
        }
        .background(Color.black)
    }

    static var sampleActionCardSuccess: ActionCard {
        ActionCard(
            id: UUID().uuidString,
            timestamp: Date().addingTimeInterval(-125),
            action: "Upload Backup",
            tier: .green,
            tool: "BackupToolX",
            toolkit: "ToolkitA",
            reason: "User initiated backup",
            upgraded: false,
            speak: "",
            authUsed: false,
            blocked: false,
            success: true,
            durationMs: 0
        )
    }

    static var sampleActionCardBlocked: ActionCard {
        ActionCard(
            id: UUID().uuidString,
            timestamp: Date().addingTimeInterval(-3600),
            action: "Delete File",
            tier: .red,
            tool: "",
            toolkit: "AdminToolkit",
            reason: "Permission denied",
            upgraded: false,
            speak: "",
            authUsed: false,
            blocked: true,
            success: false,
            durationMs: 0
        )
    }

    static var sampleActionCardFailed: ActionCard {
        ActionCard(
            id: UUID().uuidString,
            timestamp: Date().addingTimeInterval(-45),
            action: "Sync Data",
            tier: .yellow,
            tool: "SyncTool",
            toolkit: "",
            reason: "Network error",
            upgraded: false,
            speak: "",
            authUsed: false,
            blocked: false,
            success: false,
            durationMs: 0
        )
    }
}
#endif

