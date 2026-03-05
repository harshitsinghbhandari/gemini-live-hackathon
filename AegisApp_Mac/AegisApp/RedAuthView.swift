import SwiftUI

struct RedAuthView: View {
    @ObservedObject var vm: AegisMacViewModel
    @State private var progress: Double = 1.0
    let timer = Timer.publish(every: 0.1, on: .main, in: .common).autoconnect()

    var body: some View {
        ZStack {
            Color.black.opacity(0.9)
                .ignoresSafeArea()

            VStack(spacing: 40) {
                Image(systemName: "lock.shield.fill")
                    .font(.system(size: 80))
                    .foregroundColor(Color(hex: "dc2626"))

                VStack(spacing: 12) {
                    Text("Biometric Authentication Required")
                        .font(.title2.bold())

                    Text(vm.pendingRed?.action ?? "High-risk action detected")
                        .font(.body)
                        .multilineTextAlignment(.center)
                        .foregroundColor(.gray)
                }

                VStack(spacing: 8) {
                    Text("Check your iPhone")
                        .font(.headline)
                        .foregroundColor(Color(hex: "7c3aed"))

                    Text("Confirm with Face ID to proceed")
                        .font(.subheadline)
                        .foregroundColor(.gray)
                }

                GeometryReader { geo in
                    ZStack(alignment: .leading) {
                        Rectangle()
                            .fill(Color.white.opacity(0.1))
                            .frame(height: 6)

                        Rectangle()
                            .fill(Color(hex: "dc2626"))
                            .frame(width: geo.size.width * progress, height: 6)
                    }
                    .cornerRadius(3)
                }
                .frame(height: 6)
                .padding(.horizontal, 40)
            }
            .padding(40)
        }
        .onReceive(timer) { _ in
            if let requestedAt = vm.pendingRed?.requestedAt {
                let elapsed = Date().timeIntervalSince(requestedAt)
                progress = max(0, 1.0 - (elapsed / 30.0))
            }
        }
    }
}
