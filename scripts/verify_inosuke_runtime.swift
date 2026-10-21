// Compile with the app's Swift sources except LilAgentsApp.swift and place the
// executable in a review .app containing the app's bundled resources.
import AppKit
import AVFoundation

@main
struct InosukeRuntimeReview {
    @MainActor
    static func main() async throws {
        _ = NSApplication.shared
        NSApp.setActivationPolicy(.accessory)
        UserDefaults.standard.setVolatileDomain([
            "hasCompletedOnboarding": true, "InosukeSize": "large"
        ], forName: UserDefaults.argumentDomain)
        let controller = LilAgentsController()
        controller.start()
        for character in controller.characters { character.window.orderOut(nil) }
        let character = controller.characters.first { $0.name == "Inosuke" }!
        character.specialChance = 0
        character.positionProgress = 0.2
        character.update(dockX: 0, dockWidth: 800, dockTopY: 90)
        func expect(_ condition: Bool, _ message: String) {
            guard condition else { fatalError(message) }
            print("PASS: \(message)")
        }
        func seek(_ seconds: Double) async {
            character.queuePlayer.pause()
            await character.queuePlayer.seek(to: CMTime(seconds: seconds, preferredTimescale: 600),
                                             toleranceBefore: .zero, toleranceAfter: .zero)
            character.update(dockX: 0, dockWidth: 800, dockTopY: 90)
        }
        expect(controller.characters.count == 4, "All four characters load")
        expect(character.personality != nil && character.specialMoves.count == 2, "Personality and both attacks registered")
        character.startSpecial(at: 0)
        try await Task.sleep(for: .milliseconds(400))
        let crossPosition = character.walkStartPos
        await seek(3)
        expect(character.isPlayingSpecial && abs(character.positionProgress - crossPosition) < 0.001,
               "Cross slash stays planted on the Dock")
        await seek(6)
        expect(character.isPaused && !character.isPlayingSpecial, "Cross slash finishes and returns to walking layout")
        character.startSpecial(at: 1)
        try await Task.sleep(for: .milliseconds(400))
        await seek(3.3)
        let midpoint = (character.walkStartPos + character.walkEndPos) / 2
        expect(abs(character.positionProgress - midpoint) < 0.01, "Rush moves continuously through its midpoint")
        let timeBeforeHide = character.queuePlayer.currentTime().seconds
        character.hideForEnvironment()
        try await Task.sleep(for: .milliseconds(200))
        expect(abs(character.queuePlayer.currentTime().seconds - timeBeforeHide) < 0.05,
               "Environment hiding freezes the attack playhead")
        character.showForEnvironmentIfNeeded()
        character.window.orderOut(nil)
        await seek(10)
        expect(character.isPaused && !character.isPlayingSpecial, "Rush finishes without getting stuck")
        for size in CharacterSize.allCases {
            character.size = size
            let bounds = character.playerLayer.bounds
            character.goingRight.toggle()
            character.updateFlip()
            expect(character.playerLayer.bounds == bounds, "Mirroring preserves size at \(size.rawValue)")
        }
        print("Inosuke runtime review passed")
        for c in controller.characters { c.window.orderOut(nil); c.session?.terminate() }
    }
}
