import SwiftUI

struct ListeningView: View {
    @ObservedObject var vm: AegisMacViewModel

    var body: some View {
        VStack(spacing: 30) {
            Text(formatDuration(vm.sessionDuration))
                .font(.system(size: 48, weight: .bold, design: .monospaced))
                .foregroundColor(.white)

            HStack(spacing: 4) {
                ForEach(0..<vm.waveformValues.count, id: \.self) { index in
                    RoundedRectangle(cornerRadius: 2)
                        .fill(Color(hex: "7c3aed"))
                        .frame(width: 4, height: max(10, CGFloat(vm.waveformValues[index]) * 100))
                }
            }
            .frame(height: 100)

            Button(action: {
                vm.stopSession()
            }) {
                Image(systemName: "stop.fill")
                    .font(.system(size: 24))
                    .foregroundColor(.white)
                    .frame(width: 60, height: 60)
                    .background(Color.red)
                    .clipShape(Circle())
            }
            .buttonStyle(.plain)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color(hex: "0a0a0f"))
    }

    private func formatDuration(_ seconds: Int) -> String {
        let m = seconds / 60
        let s = seconds % 60
        return String(format: "%d:%02d", m, s)
    }
}
