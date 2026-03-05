import SwiftUI

struct ContentView: View {
    @StateObject var vm = AegisMacViewModel()

    var body: some View {
        ZStack {
            if !vm.isSessionActive {
                IdleView(vm: vm)
            } else if vm.actions.isEmpty {
                ListeningView(vm: vm)
            } else {
                ActivityStreamView(vm: vm)
            }

            if vm.pendingYellow != nil {
                YellowPauseView(vm: vm)
                    .transition(.opacity)
            }

            if vm.pendingRed != nil {
                RedAuthView(vm: vm)
                    .transition(.move(edge: .bottom))
            }
        }
        .frame(width: 380, height: 680)
        .preferredColorScheme(.dark)
        .background(Color(hex: "0a0a0f").opacity(0.8))
        .background(.ultraThinMaterial)
    }
}
