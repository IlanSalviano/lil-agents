// Compile with app sources except LilAgentsApp.swift, then run in a review .app.
import AppKit
import AVFoundation

@main
struct VoiceRuntimeReview {
    @MainActor
    static func main() async throws {
        _ = NSApplication.shared
        NSApp.setActivationPolicy(.accessory)
        func expect(_ condition: Bool, _ message: String) {
            precondition(condition, message)
            print("PASS: \(message)")
        }
        let event = NSEvent.mouseEvent(with: .rightMouseDown, location: .zero,
                                      modifierFlags: [], timestamp: 0, windowNumber: 0,
                                      context: nil, eventNumber: 0, clickCount: 1, pressure: 1)!
        for name in ["Bruce", "Jazz", "Zenitsu", "Inosuke", "Tanjiro", "Nezuko", "Bill", "Amit"] {
            let character = WalkerCharacter(videoName: "unused", name: name)
            let view = CharacterContentView()
            view.character = character
            expect(view.menu(for: event)?.items.last?.submenu?.title == "Voice",
                   "\(name) has a voice menu even without special moves")
        }

        let suite = "com.lilagents.voice-runtime.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suite)!
        defer { defaults.removePersistentDomain(forName: suite) }
        let installed = AVSpeechSynthesisVoice.speechVoices()
        let settings = CharacterVoice(characterName: "Review", defaultLanguage: "pt-BR", defaults: defaults)
        settings.selectedIdentifier = installed.first { $0.quality == .enhanced && $0.language == "pt-BR" }?.identifier
        let menu = settings.makeMenu()
        WalkerCharacter.soundsEnabled = false
        menu.performActionForItem(at: menu.items.firstIndex { $0.title == "Test Voice" }!)
        for _ in 0..<50 {
            if CharacterVoice.isPreviewSpeaking { break }
            try await Task.sleep(for: .milliseconds(100))
        }
        expect(CharacterVoice.isPreviewSpeaking, "Test Voice menu starts native synthesis with Sounds off")
        try await Task.sleep(for: .milliseconds(500))
        settings.menuNeedsUpdate(menu)
        let stopIndex = menu.items.firstIndex { $0.title == "Stop Preview" }!
        expect(menu.items[stopIndex].isEnabled, "Stop Preview is enabled during playback")
        menu.performActionForItem(at: stopIndex)
        for _ in 0..<50 {
            if !CharacterVoice.isPreviewSpeaking { break }
            try await Task.sleep(for: .milliseconds(100))
        }
        expect(!CharacterVoice.isPreviewSpeaking, "Stop Preview menu stops native synthesis")

        // Render native audio buffers to verify the selected voices produce real audio.
        var samples = installed.filter { $0.quality != .default }
        if let standard = installed.first(where: { $0.language == "en-US" && $0.quality == .default }) {
            samples.append(standard)
        }
        for voice in samples {
            settings.selectedIdentifier = voice.identifier
            let utterance = settings.utterance(for: voice.language.hasPrefix("pt") ? "Olá, esta é a minha voz." : "Hello, this is my voice.")
            expect(utterance.voice?.identifier == voice.identifier, "Speech uses \(CharacterVoice.label(for: voice))")
            let synthesizer = AVSpeechSynthesizer()
            let result = AudioResult()
            synthesizer.write(utterance) { buffer in
                guard let pcm = buffer as? AVAudioPCMBuffer else { return }
                result.record(pcm.frameLength)
            }
            for _ in 0..<150 {
                if result.finished { break }
                try await Task.sleep(for: .milliseconds(100))
            }
            expect(result.finished && result.frames > 0, "Native audio rendered for \(voice.language) / \(CharacterVoice.label(for: voice))")
        }
        print("Voice runtime checks passed. Premium audio requires an installed Premium voice.")
    }
}

private final class AudioResult: @unchecked Sendable {
    private let lock = NSLock()
    private var frameCount: UInt64 = 0
    private var isFinished = false
    var frames: UInt64 { lock.lock(); defer { lock.unlock() }; return frameCount }
    var finished: Bool { lock.lock(); defer { lock.unlock() }; return isFinished }
    func record(_ frames: AVAudioFrameCount) {
        lock.lock()
        defer { lock.unlock() }
        frameCount += UInt64(frames)
        if frames == 0 { isFinished = true }
    }
}
