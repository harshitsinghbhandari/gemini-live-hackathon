import SwiftUI

struct PostAuthView: View {
    let result: AegisIOSViewModel.AuthResult
    @Environment(\.dismiss) var dismiss

    var body: some View {
        VStack(spacing: 30) {
            Image(systemName: result == .approved ? "checkmark.circle.fill" : "xmark.circle.fill")
                .font(.system(size: 120))
                .foregroundColor(result == .approved ? .green : .red)
                .scaleEffect(1.0)
                .transition(.scale)

            Text(result == .approved ? "Approved" : "Denied")
                .font(.largeTitle.bold())
                .foregroundColor(.white)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color(hex: "0a0a0f"))
        .onAppear {
            DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) {
                dismiss()
            }
        }
    }
}
