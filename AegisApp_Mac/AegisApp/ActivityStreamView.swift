import SwiftUI

struct ActivityStreamView: View {
    @ObservedObject var vm: AegisMacViewModel

    var body: some View {
        ZStack(alignment: .bottom) {
            ScrollView {
                LazyVStack(spacing: 16) {
                    ForEach(Array(vm.actions.enumerated()), id: \.element.id) { index, action in
                        ActionCardRow(action: action)
                            .opacity(index >= 5 ? 0.6 : 1.0)
                    }
                }
                .padding()
                .padding(.bottom, 80)
            }

            Button(action: {
                vm.stopSession()
            }) {
                HStack {
                    Image(systemName: "stop.fill")
                    Text("STOP SESSION")
                }
                .font(.system(size: 14, weight: .bold))
                .foregroundColor(.white)
                .padding()
                .frame(maxWidth: .infinity)
                .background(Color.red)
                .cornerRadius(12)
            }
            .buttonStyle(.plain)
            .padding()
        }
        .background(Color(hex: "0a0a0f"))
    }
}

struct ActionCardRow: View {
    let action: ActionCard
    @State private var showDetail = false

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(action.action)
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundColor(.white)

                Spacer()

                Image(systemName: action.tier.icon)
                    .foregroundColor(action.tier.color)
            }

            HStack {
                Text(action.tool ?? "Manual")
                    .font(.system(size: 12))
                    .foregroundColor(.gray)

                Spacer()

                Text("\(action.durationMs)ms")
                    .font(.system(size: 12))
                    .foregroundColor(.gray)
            }
        }
        .padding()
        .background(Color.white.opacity(0.05))
        .cornerRadius(12)
        .overlay(
            Rectangle()
                .fill(action.tier.color)
                .frame(width: 4)
                .padding(.vertical, 8),
            alignment: .leading
        )
        .onTapGesture {
            showDetail = true
        }
        .sheet(isPresented: $showDetail) {
            ActionDetailView(action: action)
        }
    }
}

struct ActionDetailView: View {
    let action: ActionCard
    @Environment(\.dismiss) var dismiss

    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            HStack {
                Text("Action Details")
                    .font(.title2.bold())
                Spacer()
                Button("Done") { dismiss() }
            }

            Divider()

            DetailRow(label: "Command", value: action.action)
            DetailRow(label: "Reason", value: action.reason)
            DetailRow(label: "Tier", value: action.tier.rawValue)
            DetailRow(label: "Tool", value: action.tool ?? "None")
            DetailRow(label: "Status", value: action.success ? "Success" : "Failed")

            Spacer()
        }
        .padding()
        .preferredColorScheme(.dark)
    }
}

struct DetailRow: View {
    let label: String
    let value: String
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label.uppercased())
                .font(.caption.bold())
                .foregroundColor(.gray)
            Text(value)
                .font(.body)
                .foregroundColor(.white)
        }
    }
}
