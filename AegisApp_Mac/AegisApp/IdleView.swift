import SwiftUI

struct IdleView: View {
    @ObservedObject var vm: AegisMacViewModel
    @State private var isAnimating = false

    var body: some View {
        VStack(spacing: 40) {
            Spacer()

            Button(action: {
                vm.startSession()
            }) {
                ZStack {
                    Circle()
                        .fill(Color(hex: "7c3aed"))
                        .frame(width: 100, height: 100)
                        .shadow(color: Color(hex: "7c3aed").opacity(0.6), radius: 20)
                        .scaleEffect(isAnimating ? 1.05 : 1.0)

                    Text("◈")
                        .font(.system(size: 40))
                        .foregroundColor(.white)
                }
            }
            .buttonStyle(.plain)
            .onAppear {
                withAnimation(Animation.easeInOut(duration: 2).repeatForever(autoreverses: true)) {
                    isAnimating = true
                }
            }

            Text("Aegis is idle")
                .font(.system(size: 18, weight: .medium))
                .foregroundColor(.gray)

            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color(hex: "0a0a0f"))
    }
}
