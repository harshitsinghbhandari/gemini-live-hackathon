import SwiftUI

struct ContentView: View {
    @StateObject var vm = AegisIOSViewModel()

    var body: some View {
        ZStack {
            MirrorView(vm: vm)

            if let request = vm.pendingRedAuth {
                RedAuthRequestView(vm: vm, request: request)
                    .transition(.move(edge: .bottom))
                    .zIndex(1)
            }

            if let result = vm.lastAuthResult {
                PostAuthView(result: result)
                    .transition(.opacity)
                    .zIndex(2)
                    .onDisappear {
                        vm.clearAuthResult()
                    }
            }
        }
        .preferredColorScheme(.dark)
    }
}
