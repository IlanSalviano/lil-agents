import AppKit

@main
struct ReleaseCastReview {
    @MainActor static func main() {
        _ = NSApplication.shared
        NSApp.setActivationPolicy(.accessory)
        UserDefaults.standard.setVolatileDomain(["hasCompletedOnboarding": true],
                                               forName: UserDefaults.argumentDomain)
        WalkerCharacter.soundsEnabled = false
        let controller = LilAgentsController()
        controller.start()
        let expectsAmit = CommandLine.arguments.contains("--with-amit")
        let names = Set(controller.characters.map(\.name))
        var expected: Set<String> = ["Bruce", "Jazz", "Zenitsu", "Inosuke", "Tanjiro", "Nezuko", "Bill"]
        if expectsAmit { expected.insert("Amit") }
        precondition(names == expected, "Unexpected companion set: \(names)")
        if expectsAmit {
            let amit = controller.characters.first { $0.name == "Amit" }!
            precondition(amit.isManuallyVisible && amit.specialMoves.count == 2)
        }
        for character in controller.characters { character.window.orderOut(nil) }
        print("PASS: \(names.count) companions registered; Amit=\(expectsAmit)")
        exit(0)
    }
}
