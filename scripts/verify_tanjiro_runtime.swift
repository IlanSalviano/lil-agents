// Compile with the app sources except LilAgentsApp.swift; run in an isolated
// review .app containing the production resources and a separate bundle ID.
import AppKit
import AVFoundation

@main
struct TanjiroRuntimeReview {
    @MainActor
    static func main() async throws {
        _ = NSApplication.shared
        NSApp.setActivationPolicy(.accessory)
        UserDefaults.standard.setVolatileDomain([
            "hasCompletedOnboarding": true, "TanjiroSize": "large",
            "InosukeSize": "large", "TanjiroProvider": "codex", "InosukeProvider": "codex"
        ], forName: UserDefaults.argumentDomain)
        let controller = LilAgentsController()
        controller.start()
        for character in controller.characters {
            character.window.orderOut(nil)
            character.specialChance = 0
            character.pauseEndTime = CACurrentMediaTime() + 3600
        }
        let character = controller.characters.first { $0.name == "Tanjiro" }!
        character.positionProgress = 0.5
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
        expect(Set(controller.characters.map(\.name)) == ["Bruce", "Jazz", "Zenitsu", "Inosuke", "Tanjiro", "Nezuko", "Bill", "Amit"],
               "All eight companions load")
        expect(character.isManuallyVisible && character.personality != nil && character.specialMoves.count == 2,
               "Tanjiro launches visible with personality and both attacks")
        for index in character.specialMoves.indices {
            character.startSpecial(at: index)
            try await Task.sleep(for: .milliseconds(400))
            let startPosition = character.walkStartPos
            await seek(3)
            expect(character.isPlayingSpecial && abs(character.positionProgress - startPosition) < 0.001,
                   "Attack \(index) stays planted on the Dock")
            let timeBeforeHide = character.queuePlayer.currentTime().seconds
            character.hideForEnvironment()
            try await Task.sleep(for: .milliseconds(200))
            expect(abs(character.queuePlayer.currentTime().seconds - timeBeforeHide) < 0.05,
                   "Hiding freezes attack \(index)")
            character.showForEnvironmentIfNeeded()
            character.window.orderOut(nil)
            await seek(10)
            expect(character.isPaused && !character.isPlayingSpecial,
                   "Attack \(index) recovers to walking layout")
        }
        for size in CharacterSize.allCases {
            character.size = size
            let bounds = character.playerLayer.bounds
            character.goingRight.toggle()
            character.updateFlip()
            expect(character.playerLayer.bounds == bounds, "Mirroring preserves \(size.rawValue) size")
        }
        character.startWalk()
        try await Task.sleep(for: .milliseconds(400))
        await seek(4.5)
        expect(character.isWalking && abs(character.positionProgress - character.walkStartPos) > 0.01,
               "Walking advances along the Dock")
        await seek(10)
        expect(character.isPaused && !character.isWalking, "Walk finishes and pauses")
        for c in controller.characters { c.window.orderOut(nil); c.session?.terminate() }
        print("Tanjiro runtime review passed")
    }
}
