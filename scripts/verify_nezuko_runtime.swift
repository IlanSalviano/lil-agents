// Run in an isolated review .app with the production resources and separate ID.
// No AI sessions are started. Preferences are volatile within this test process.
import AppKit
import AVFoundation

@main
struct NezukoRuntimeReview {
    @MainActor
    static func main() async throws {
        _ = NSApplication.shared
        NSApp.setActivationPolicy(.accessory)
        var defaults: [String: Any] = ["hasCompletedOnboarding": true]
        for name in ["Bruce", "Jazz", "Zenitsu", "Inosuke", "Tanjiro", "Nezuko"] {
            defaults[name + "Size"] = "large"
            defaults[name + "Provider"] = "codex"
        }
        UserDefaults.standard.setVolatileDomain(defaults, forName: UserDefaults.argumentDomain)
        let controller = LilAgentsController()
        controller.start()
        for c in controller.characters {
            c.window.orderOut(nil)
            c.specialChance = 0
            c.pauseEndTime = CACurrentMediaTime() + 3600
        }
        let nezuko = controller.characters.first { $0.name == "Nezuko" }!
        let zenitsu = controller.characters.first { $0.name == "Zenitsu" }!
        func expect(_ condition: Bool, _ message: String) {
            guard condition else { fatalError(message) }
            print("PASS: \(message)")
        }
        func place(_ character: WalkerCharacter, _ position: CGFloat, width: CGFloat = 800) {
            character.positionProgress = position
            character.update(dockX: 0, dockWidth: width, dockTopY: 90)
        }
        func seek(_ seconds: Double, width: CGFloat = 800) async {
            nezuko.queuePlayer.pause()
            await nezuko.queuePlayer.seek(to: CMTime(seconds: seconds, preferredTimescale: 600),
                                         toleranceBefore: .zero, toleranceAfter: .zero)
            nezuko.update(dockX: 0, dockWidth: width, dockTopY: 90)
        }
        func begin(_ index: Int) async throws {
            nezuko.startSpecial(at: index)
            try await Task.sleep(for: .milliseconds(300))
        }
        expect(controller.characters.count == 8, "All eight companions load")
        expect(nezuko.isManuallyVisible && nezuko.personality != nil && nezuko.specialMoves.count == 2,
               "Nezuko launches with personality, run and transformation")
        expect(nezuko.displayHeight < zenitsu.displayHeight, "Tiny form is smaller than Zenitsu")
        for (start, target) in [(0.15, 0.8), (0.85, 0.2)] {
            place(zenitsu, target)
            place(nezuko, start)
            try await begin(0)
            expect(nezuko.goingRight == (target > start), "Run faces Zenitsu from either side")
            await seek(2.6)
            let middle = (nezuko.walkStartPos + nezuko.walkEndPos) / 2
            expect(abs(nezuko.positionProgress - middle) < 0.005, "Run moves continuously to the friend")
            await seek(5.3)
            expect(abs(nezuko.window.frame.midX - zenitsu.window.frame.midX) > 45
                   && abs(nezuko.window.frame.midX - zenitsu.window.frame.midX) < 100,
                   "Run stops beside Zenitsu without overlapping")
            await seek(10)
            expect(nezuko.isPaused && !nezuko.isPlayingSpecial, "Run returns to tiny idle")
        }
        place(zenitsu, 0.7)
        place(nezuko, 0.1)
        try await begin(0)
        await seek(1)
        let firstEnd = nezuko.walkEndPos
        place(zenitsu, 0.85)
        await seek(2)
        expect(nezuko.walkEndPos > firstEnd, "Run follows a moving Zenitsu")
        let beforeHide = nezuko.positionProgress
        zenitsu.setManuallyVisible(false)
        await seek(2.1)
        expect(nezuko.isPaused && abs(nezuko.positionProgress - beforeHide) < 0.001,
               "Hiding Zenitsu cancels the run without teleporting")
        try await begin(0)
        expect(nezuko.isPaused && !nezuko.isPlayingSpecial,
               "Explicit run with hidden Zenitsu stays idle")
        zenitsu.setManuallyVisible(true)
        zenitsu.window.orderOut(nil)
        zenitsu.size = .small
        place(zenitsu, 0.8)
        place(nezuko, 0.1)
        try await begin(0)
        await seek(5.3)
        expect(abs(nezuko.window.frame.midX - zenitsu.window.frame.midX) < 100,
               "Approach uses physical centers when companions have different sizes")
        await seek(10)
        place(nezuko, 0.5)
        try await begin(1)
        await seek(1)
        let beforeFreeze = nezuko.queuePlayer.currentTime().seconds
        nezuko.hideForEnvironment()
        try await Task.sleep(for: .milliseconds(200))
        expect(abs(nezuko.queuePlayer.currentTime().seconds - beforeFreeze) < 0.05,
               "Environment hiding freezes the transformation playhead")
        nezuko.showForEnvironmentIfNeeded()
        nezuko.window.orderOut(nil)
        await seek(4)
        expect(nezuko.isPlayingSpecial, "Transformation uses its own animation layout")
        await seek(10)
        expect(nezuko.isPaused && !nezuko.isPlayingSpecial, "Transformation restores tiny idle")
        for size in CharacterSize.allCases {
            nezuko.size = size
            let bounds = nezuko.playerLayer.bounds
            nezuko.goingRight.toggle()
            nezuko.updateFlip()
            expect(nezuko.playerLayer.bounds == bounds, "Mirroring preserves \(size.rawValue) size")
        }
        place(zenitsu, 0.5, width: 20)
        place(nezuko, 0.5, width: 20)
        try await begin(0)
        await seek(2, width: 20)
        expect(nezuko.positionProgress.isFinite && nezuko.window.frame.minX.isFinite,
               "A Dock narrower than the character cannot cause NaN positions")
        await seek(10, width: 20)
        for c in controller.characters { c.window.orderOut(nil) }
        print("Nezuko runtime review passed")
    }
}
