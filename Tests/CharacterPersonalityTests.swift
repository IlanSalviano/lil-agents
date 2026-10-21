import Foundation

func runCharacterPersonalityTests() {
    func expect(_ condition: @autoclosure () -> Bool, _ message: String) {
        if !condition() { fatalError(message) }
    }
    let persona = CharacterPersonality.inosuke
    for text in ["Olá!", "", "```swift\nprint(\"oi\")\n```", "[Estilo de conversa]\nTexto do usuário"] {
        expect(persona.visibleMessage(persona.messageForSession(text)) == text,
               "Reopening chat must preserve the exact user input without leaking the persona prefix")
        expect(persona.visibleMessage(text) == text, "Unwrapped history must not be changed")
    }
    expect(SpecialTravel.progress(time: 1.9, start: 2, duration: 3) == 0, "Charge must wait for anticipation")
    expect(SpecialTravel.progress(time: 3.5, start: 2, duration: 3) == 0.5, "Charge travels continuously")
    expect(SpecialTravel.progress(time: 9, start: 2, duration: 3) == 1, "Charge must stop at its endpoint")
    expect(SpecialTravel.progress(time: 1.9, start: 2, duration: 0) == 0, "Thunder must wait for its dash")
    expect(SpecialTravel.progress(time: 2, start: 2, duration: 0) == 1, "Thunder retains its instantaneous dash")
    print("CharacterPersonality tests passed (history round-trip and attack timing)")
}
