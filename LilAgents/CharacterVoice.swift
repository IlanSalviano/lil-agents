import AppKit
import AVFoundation

/// A separate preference for each companion; identifiers distinguish quality variants.
final class CharacterVoice: NSObject, NSMenuDelegate {
    let characterName: String
    let defaultLanguage: String
    private let defaults: UserDefaults
    private let availableVoices: () -> [AVSpeechSynthesisVoice]
    var stopCharacterSpeech: (() -> Void)?
    private static var previewSpeech: AVSpeechSynthesizer?
    static var isPreviewSpeaking: Bool { previewSpeech?.isSpeaking ?? false }

    init(characterName: String, defaultLanguage: String,
         defaults: UserDefaults = .standard,
         availableVoices: @escaping () -> [AVSpeechSynthesisVoice] = AVSpeechSynthesisVoice.speechVoices) {
        self.characterName = characterName
        self.defaultLanguage = defaultLanguage
        self.defaults = defaults
        self.availableVoices = availableVoices
        super.init()
    }

    var selectedIdentifier: String? {
        get { defaults.string(forKey: "\(characterName)VoiceIdentifier") }
        set {
            if let newValue {
                defaults.set(newValue, forKey: "\(characterName)VoiceIdentifier")
            } else {
                defaults.removeObject(forKey: "\(characterName)VoiceIdentifier")
            }
        }
    }

    static func qualityName(_ quality: AVSpeechSynthesisVoiceQuality) -> String {
        switch quality {
        case .premium: return "Premium"
        case .enhanced: return "Enhanced"
        case .default: return "Standard"
        @unknown default: return "Standard"
        }
    }

    static func label(for voice: AVSpeechSynthesisVoice) -> String {
        let quality = qualityName(voice.quality)
        let suffix = " (\(quality))"
        let name = voice.name.hasSuffix(suffix) ? String(voice.name.dropLast(suffix.count)) : voice.name
        return "\(name) — \(quality)"
    }

    func resolvedVoice(in voices: [AVSpeechSynthesisVoice]) -> AVSpeechSynthesisVoice? {
        if let identifier = selectedIdentifier,
           let selected = voices.first(where: { $0.identifier == identifier }) {
            return selected
        }
        // Prefer quality, then a stable name/identifier order, within the phrase's language.
        let sorted = voices.sorted {
            if $0.quality != $1.quality { return $0.quality.rawValue > $1.quality.rawValue }
            return $0.identifier < $1.identifier
        }
        return sorted.first { $0.language == defaultLanguage }
            ?? sorted.first { $0.language.split(separator: "-").first == defaultLanguage.split(separator: "-").first }
            ?? AVSpeechSynthesisVoice(language: defaultLanguage)
    }

    func utterance(for phrase: String) -> AVSpeechUtterance {
        let utterance = AVSpeechUtterance(string: phrase)
        utterance.voice = resolvedVoice(in: availableVoices())
        utterance.rate = AVSpeechUtteranceDefaultSpeechRate
        utterance.pitchMultiplier = 1
        utterance.volume = 1
        return utterance
    }

    func makeMenu() -> NSMenu {
        let menu = NSMenu(title: "Voice")
        menu.autoenablesItems = false
        menu.delegate = self
        populate(menu)
        return menu
    }

    func menuNeedsUpdate(_ menu: NSMenu) {
        // Refresh on opening so newly downloaded voices and changes in the other menu appear.
        populate(menu)
    }

    private func populate(_ menu: NSMenu) {
        menu.removeAllItems()
        let voices = availableVoices()
        let selected = selectedIdentifier
        let automatic = NSMenuItem(title: "Automatic", action: #selector(selectVoice(_:)), keyEquivalent: "")
        automatic.target = self
        automatic.state = selected == nil ? .on : .off
        menu.addItem(automatic)

        if let selected, !voices.contains(where: { $0.identifier == selected }) {
            let missing = NSMenuItem(title: "Saved voice unavailable — using Automatic", action: nil, keyEquivalent: "")
            missing.isEnabled = false
            missing.state = .on
            menu.addItem(missing)
        }

        let preview = NSMenuItem(title: "Test Voice", action: #selector(testVoice), keyEquivalent: "")
        preview.target = self
        preview.isEnabled = resolvedVoice(in: voices) != nil
        menu.addItem(preview)
        let stop = NSMenuItem(title: "Stop Preview", action: #selector(stopPreviewFromMenu), keyEquivalent: "")
        stop.target = self
        stop.isEnabled = Self.isPreviewSpeaking
        menu.addItem(stop)
        menu.addItem(.separator())

        let groups = Dictionary(grouping: voices, by: \.language)
        for language in groups.keys.sorted() {
            let languageName = Locale.current.localizedString(forIdentifier: language) ?? language
            let group = NSMenuItem(title: "\(languageName) (\(language))", action: nil, keyEquivalent: "")
            let submenu = NSMenu(title: languageName)
            submenu.autoenablesItems = false
            for voice in groups[language, default: []].sorted(by: {
                if $0.quality != $1.quality { return $0.quality.rawValue > $1.quality.rawValue }
                if $0.name != $1.name { return $0.name.localizedStandardCompare($1.name) == .orderedAscending }
                return $0.identifier < $1.identifier
            }) {
                let item = NSMenuItem(title: Self.label(for: voice), action: #selector(selectVoice(_:)), keyEquivalent: "")
                item.target = self
                item.representedObject = voice.identifier
                item.state = voice.identifier == selected ? .on : .off
                if item.state == .on { group.state = .on }
                submenu.addItem(item)
            }
            group.submenu = submenu
            menu.addItem(group)
        }
        if voices.isEmpty {
            let empty = NSMenuItem(title: "No installed voices found", action: nil, keyEquivalent: "")
            empty.isEnabled = false
            menu.addItem(empty)
        }
        menu.addItem(.separator())
        let help = NSMenuItem(title: "How to Download Enhanced / Premium Voices…",
                              action: #selector(showDownloadHelp), keyEquivalent: "")
        help.target = self
        menu.addItem(help)
    }

    @objc func selectVoice(_ sender: NSMenuItem) {
        selectedIdentifier = sender.representedObject as? String
        Self.stopPreview()
        stopCharacterSpeech?()
    }

    @objc func testVoice() {
        Self.stopPreview()
        stopCharacterSpeech?()
        let voice = resolvedVoice(in: availableVoices())
        let phrase: String
        switch voice?.language.split(separator: "-").first {
        case "pt": phrase = "Olá! Eu sou \(characterName). Esta é a minha voz."
        case "es": phrase = "¡Hola! Soy \(characterName). Esta es mi voz."
        case "fr": phrase = "Bonjour ! Je suis \(characterName). Voici ma voix."
        case "de": phrase = "Hallo! Ich bin \(characterName). Das ist meine Stimme."
        case "ja": phrase = "こんにちは！私は\(characterName)です。これが私の声です。"
        default: phrase = "Hello! I'm \(characterName). This is my voice."
        }
        let speech = Self.previewSpeech ?? AVSpeechSynthesizer()
        Self.previewSpeech = speech
        // Explicit previews work even when automatic character sounds are disabled.
        speech.speak(utterance(for: phrase))
    }

    static func stopPreview() {
        previewSpeech?.stopSpeaking(at: .immediate)
    }

    @objc private func stopPreviewFromMenu() { Self.stopPreview() }

    @objc private func showDownloadHelp() {
        NSWorkspace.shared.open(URL(string: "https://support.apple.com/guide/mac-help/mchlp2290/mac")!)
    }
}
