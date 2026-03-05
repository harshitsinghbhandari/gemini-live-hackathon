import SwiftUI

struct MirrorView: View {
    @ObservedObject var vm: AegisIOSViewModel

    var body: some View {
        VStack(spacing: 0) {
            header

            if !vm.isSessionActive {
                emptyState
            } else {
                actionList
            }

            stopButton
        }
        .background(Color(hex: "0a0a0f"))
    }

    private var header: some View {
        HStack {
            Text("Aegis Mirror")
                .font(.system(size: 24, weight: .bold))
                .foregroundColor(.white)
            Spacer()
            Circle()
                .fill(vm.isSessionActive ? Color.green : Color.gray)
                .frame(width: 10, height: 10)
        }
        .padding()
    }

    private var emptyState: some View {
        VStack(spacing: 20) {
            Spacer()
            Image(systemName: "desktopcomputer")
                .font(.system(size: 60))
                .foregroundColor(.white.opacity(0.1))
            Text("No active session")
                .font(.headline)
                .foregroundColor(.gray)
            Spacer()
        }
        .frame(maxWidth: .infinity)
    }

    private var actionList: some View {
        ScrollView {
            LazyVStack(spacing: 16) {
                ForEach(vm.actions) { action in
                    ActionCardRow(action: action)
                }
            }
            .padding()
        }
    }

    private var stopButton: some View {
        Button(action: {
            vm.stopSession()
        }) {
            Text("STOP SESSION")
                .font(.system(size: 14, weight: .bold))
                .foregroundColor(.white)
                .padding()
                .frame(maxWidth: .infinity)
                .background(Color.red)
                .cornerRadius(12)
        }
        .padding()
    }
}
