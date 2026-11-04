import Foundation

func runCharacterPersonalityTests() {
    func expect(_ condition: @autoclosure () -> Bool, _ message: String) {
        if !condition() { fatalError(message) }
    }
    for persona in [CharacterPersonality.inosuke, .tanjiro, .nezuko, .bill, .amit] {
        for text in ["Olá!", "", "```swift\nprint(\"oi\")\n```", "[Estilo de conversa]\nTexto do usuário"] {
            expect(persona.visibleMessage(persona.messageForSession(text)) == text,
                   "Reopening chat must preserve the exact user input without leaking the persona prefix")
            expect(persona.visibleMessage(text) == text, "Unwrapped history must not be changed")
        }
    }
    expect(SpecialTravel.progress(time: 1.9, start: 2, duration: 3) == 0, "Charge must wait for anticipation")
    expect(SpecialTravel.progress(time: 3.5, start: 2, duration: 3) == 0.5, "Charge travels continuously")
    expect(SpecialTravel.progress(time: 9, start: 2, duration: 3) == 1, "Charge must stop at its endpoint")
    expect(SpecialTravel.progress(time: 1.9, start: 2, duration: 0) == 0, "Thunder must wait for its dash")
    expect(SpecialTravel.progress(time: 2, start: 2, duration: 0) == 1, "Thunder retains its instantaneous dash")
    expect(CompanionApproach.destination(start: 100, target: 600, separation: 70, bounds: 50...750) == 530,
           "Run approaches the friend from the left with space between bodies")
    expect(CompanionApproach.destination(start: 600, target: 100, separation: 70, bounds: 50...750) == 170,
           "Run approaches the friend from the right")
    expect(CompanionApproach.destination(start: 550, target: 600, separation: 70, bounds: 50...750) == 550,
           "Already nearby companions should not run away from one another")
    expect(CompanionApproach.destination(start: 100, target: 900, separation: 70, bounds: 50...750) == 750,
           "Resizing or changing displays cannot send the runner beyond the Dock")
    expect(CompanionApproach.destination(start: 0, target: 300, separation: 70, bounds: 50...50) == 50,
           "Zero-width travel remains well-defined")
    print("CharacterPersonality tests passed (history round-trip and attack timing)")
}
