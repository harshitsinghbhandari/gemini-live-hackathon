import SwiftUI

struct YellowPauseView: View {
    @ObservedObject var vm: AegisMacViewModel
    @State private var pulse = 1.0

    var body: some View {
        ZStack {
            Color.black.opacity(0.7)
                .ignoresSafeArea()

            VStack(spacing: 24) {
                Image(systemName: "exclamationmark.circle.fill")
                    .font(.system(size: 60))
                    .foregroundColor(Color(hex: "ca8a04"))
                    .scaleEffect(pulse)

                Text("Confirm Action")
                    .font(.title2.bold())

                Text(vm.pendingYellow?.question ?? "Shall I proceed?")
                    .font(.body)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal)

                HStack(spacing: 20) {
                    Button(action: {
                        vm.respondToYellow(confirmed: false)
                    }) {
                        Text("Skip")
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(Color.white.opacity(0.1))
                            .cornerRadius(12)
                    }
                    .buttonStyle(.plain)

                    Button(action: {
                        vm.respondToYellow(confirmed: true)
                    }) {
                        Text("Proceed")
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(Color(hex: "ca8a04"))
                            .cornerRadius(12)
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(30)
            .background(Color(hex: "1c1c1e"))
            .cornerRadius(24)
            .padding(40)
            .onAppear {
                withAnimation(.easeInOut(duration: 1.2).repeatForever(autoreverses: true)) {
                    pulse = 1.05
                }
            }
        }
    }
}
