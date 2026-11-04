// swiftc -parse-as-library LilAgents/CharacterVoice.swift Tests/CharacterVoiceTests.swift -o build/voice-review/voice-tests
import AppKit
import AVFoundation

@main
struct CharacterVoiceTests {
    static func main() {
        _ = NSApplication.shared
        let suite = "com.lilagents.voice-tests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suite)!
        defer { defaults.removePersistentDomain(forName: suite) }
        let installed = AVSpeechSynthesisVoice.speechVoices()
        var catalog = installed
        let bill = CharacterVoice(characterName: "Bill", defaultLanguage: "en-US",
                                  defaults: defaults, availableVoices: { catalog })
        let amit = CharacterVoice(characterName: "Amit", defaultLanguage: "en-US",
                                  defaults: defaults, availableVoices: { catalog })
        func expect(_ condition: Bool, _ message: String) {
            precondition(condition, message)
            print("PASS: \(message)")
        }
        func choices(_ menu: NSMenu) -> [NSMenuItem] {
            menu.items.flatMap { item -> [NSMenuItem] in
                if let submenu = item.submenu { return choices(submenu) }
                return item.representedObject is String ? [item] : []
            }
        }
        let menu = bill.makeMenu()
        expect(bill.selectedIdentifier == nil && menu.items[0].state == .on, "New characters use Automatic")
        expect(choices(menu).count == installed.count, "Menu exposes every installed voice without quality filtering")
        expect(CharacterVoice.qualityName(.enhanced) == "Enhanced"
               && CharacterVoice.qualityName(.premium) == "Premium", "Enhanced and Premium are labeled distinctly")
        expect(menu.items.contains { $0.title == "Test Voice" && $0.target === bill }, "Preview targets the correct character")

        if let voice = installed.first {
            let item = choices(menu).first { ($0.representedObject as? String) == voice.identifier }!
            bill.selectVoice(item)
            let reloaded = CharacterVoice(characterName: "Bill", defaultLanguage: "en-US", defaults: UserDefaults(suiteName: suite)!)
            expect(reloaded.selectedIdentifier == voice.identifier, "Preference survives a new settings instance")
            expect(amit.selectedIdentifier == nil, "Saving Bill does not change Amit")
            expect(bill.utterance(for: "Test").voice?.identifier == voice.identifier, "Actual speech uses the selected identifier")
            bill.menuNeedsUpdate(menu)
            expect(choices(menu).filter { $0.state == .on }.map { $0.representedObject as! String } == [voice.identifier],
                   "Reopening a menu marks exactly the saved variant")

            catalog = installed.filter { $0.identifier != voice.identifier }
            bill.menuNeedsUpdate(menu)
            expect(menu.items.contains { $0.title.contains("Saved voice unavailable") }, "Removed voice shows fallback status")
            expect(bill.selectedIdentifier == voice.identifier, "Missing voice does not erase the preference")
            catalog = installed
            bill.menuNeedsUpdate(menu)
            expect(!menu.items.contains { $0.title.contains("Saved voice unavailable") }
                   && bill.resolvedVoice(in: catalog)?.identifier == voice.identifier, "Reinstalled voice is restored automatically")
        }

        // Every installed variant must resolve exactly, including Enhanced and Premium.
        for voice in installed {
            amit.selectedIdentifier = voice.identifier
            expect(amit.resolvedVoice(in: installed)?.identifier == voice.identifier,
                   "Select \(voice.language) / \(CharacterVoice.label(for: voice))")
        }
        bill.selectVoice(menu.items[0])
        expect(bill.selectedIdentifier == nil, "Automatic clears only this character's preference")
        if let best = installed.filter({ $0.language == "en-US" }).map({ $0.quality.rawValue }).max() {
            expect(bill.resolvedVoice(in: installed)?.quality.rawValue == best, "Automatic picks the highest installed quality in the correct language")
        }
        catalog = []
        bill.menuNeedsUpdate(menu)
        expect(choices(menu).isEmpty && menu.items.contains { $0.title == "No installed voices found" }, "Empty catalog remains usable")
        let counts = Dictionary(grouping: installed, by: { CharacterVoice.qualityName($0.quality) }).mapValues(\.count)
        print("Installed voice coverage: \(counts)")
        print("All character voice tests passed.")
    }
}
