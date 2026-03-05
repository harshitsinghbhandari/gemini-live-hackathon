import SwiftUI

struct RedAuthRequestView: View {
    @ObservedObject var vm: AegisIOSViewModel
    let request: RedAuthRequest
    @State private var progress: Double = 1.0
    let timer = Timer.publish(every: 0.1, on: .main, in: .common).autoconnect()

    var body: some View {
        VStack(spacing: 40) {
            Image(systemName: "lock.shield.fill")
                .font(.system(size: 100))
                .foregroundColor(Color(hex: "dc2626"))

            VStack(spacing: 16) {
                Text(request.action)
                    .font(.title2.bold())
                    .multilineTextAlignment(.center)

                Text(request.reason)
                    .font(.body)
                    .multilineTextAlignment(.center)
                    .foregroundColor(.gray)
            }

            VStack(spacing: 20) {
                Button(action: {
                    vm.approveRedAuth(id: request.id)
                }) {
                    HStack {
                        Image(systemName: "faceid")
                        Text("Approve with Face ID")
                    }
                    .font(.headline)
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color(hex: "7c3aed"))
                    .cornerRadius(16)
                }

                Button(action: {
                    vm.denyRedAuth(id: request.id)
                }) {
                    Text("Deny")
                        .font(.headline)
                        .foregroundColor(.red)
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color.white.opacity(0.05))
                        .cornerRadius(16)
                }
            }

            VStack(spacing: 8) {
                GeometryReader { geo in
                    ZStack(alignment: .leading) {
                        Rectangle()
                            .fill(Color.white.opacity(0.1))
                            .frame(height: 8)

                        Rectangle()
                            .fill(Color(hex: "dc2626"))
                            .frame(width: geo.size.width * progress, height: 8)
                    }
                    .cornerRadius(4)
                }
                .frame(height: 8)
            }
            .padding(.top, 20)
        }
        .padding(30)
        .background(Color(hex: "0a0a0f"))
        .onReceive(timer) { _ in
            let elapsed = Date().timeIntervalSince(request.requestedAt)
            progress = max(0, 1.0 - (elapsed / 30.0))
            if progress <= 0 {
                vm.denyRedAuth(id: request.id)
            }
        }
    }
}
