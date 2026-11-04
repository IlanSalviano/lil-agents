// Read-only integration check against the REAL Sparkle engine and remote feed.
// Pass an unmodified baseline .app and the expected newer build number.
// The information-only check never downloads or installs an update.
import AppKit
import Sparkle

@main
final class RemoteUpdateReview: NSObject, SPUUpdaterDelegate {
    private var updater: SPUUpdater!
    private var expected = ""

    @MainActor static func main() throws {
        _ = NSApplication.shared
        NSApp.setActivationPolicy(.prohibited)
        guard CommandLine.arguments.count == 3,
              let host = Bundle(path: CommandLine.arguments[1]) else {
            fatalError("Usage: verify-remote-update <baseline.app> <expected build>")
        }
        let review = RemoteUpdateReview()
        review.expected = CommandLine.arguments[2]
        let driver = SPUStandardUserDriver(hostBundle: host, delegate: nil)
        review.updater = SPUUpdater(hostBundle: host, applicationBundle: host,
                                   userDriver: driver, delegate: review)
        // Keep scheduled checks inert in this process without changing saved preferences.
        UserDefaults.standard.setVolatileDomain(["SUEnableAutomaticChecks": false],
                                               forName: UserDefaults.argumentDomain)
        try review.updater.start()
        review.updater.checkForUpdateInformation()
        DispatchQueue.main.asyncAfter(deadline: .now() + 45) {
            fputs("FAIL: remote update check timed out\n", stderr)
            exit(1)
        }
        withExtendedLifetime(review) { NSApp.run() }
    }

    func updater(_ updater: SPUUpdater, didFindValidUpdate item: SUAppcastItem) {
        guard item.versionString == expected else {
            fputs("FAIL: unexpected build \(item.versionString)\n", stderr)
            exit(1)
        }
        print("PASS: Sparkle offered \(item.displayVersionString) (\(item.versionString)) from the remote feed")
        print("Download: \(item.fileURL?.absoluteString ?? "missing")")
        exit(0)
    }

    func updaterDidNotFindUpdate(_ updater: SPUUpdater, error: Error) {
        fputs("FAIL: no newer update: \(error)\n", stderr)
        exit(1)
    }

    func updater(_ updater: SPUUpdater, didAbortWithError error: Error) {
        fputs("FAIL: Sparkle check: \(error)\n", stderr)
        exit(1)
    }
}
