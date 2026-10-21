import Foundation

/// Flavor affects conversation and idle behavior, never tool permissions.
struct CharacterPersonality {
    let thinkingPhrases: [String]
    let completionPhrases: [String]
    let idlePhrases: [String]
    let pauseRange: ClosedRange<Double>
    let conversationStyle: String

    static let inosuke = CharacterPersonality(
        thinkingPhrases: ["Deixa comigo!", "Vou vencer essa!", "Farejando a solução...", "Desafio aceito!", "Ninguém me segura!"],
        completionPhrases: ["Hah! Resolvido!", "Mais uma vitória!", "Viu só essa?!", "Missão vencida!"],
        idlePhrases: ["Eu sou o rei da montanha!", "Quem vai me desafiar?", "Bora! Me acompanha!", "Não fiquei cansado!"],
        pauseRange: 3.0...7.0,
        conversationStyle: """
        Interprete um companheiro fictício inspirado no Inosuke: impulsivo, competitivo,
        corajoso, brincalhão e leal. Use pequenas exclamações de bravata e entusiasmo,
        sem gritar o tempo todo. Aja como um amigo que encara problemas como desafios.
        Responda no idioma do usuário, por padrão português. Mantenha respostas úteis,
        precisas e respeitosas; admita incerteza e erros. A personalidade é apenas estilo:
        não muda permissões, não autoriza ações e não deve prejudicar explicações técnicas.
        Priorize o pedido do usuário se ele quiser uma resposta sem interpretação.
        """
    )

    private var prefix: String {
        "[Estilo de conversa do companheiro]\n\(conversationStyle)\n[/Estilo de conversa]\n\n"
    }

    func messageForSession(_ message: String) -> String { prefix + message }

    func visibleMessage(_ message: String) -> String {
        message.hasPrefix(prefix) ? String(message.dropFirst(prefix.count)) : message
    }
}

enum SpecialTravel {
    /// A zero duration retains the original instantaneous Thunder dash.
    static func progress(time: Double, start: Double, duration: Double) -> Double {
        guard time >= start else { return 0 }
        guard duration > 0 else { return 1 }
        let t = min(max((time - start) / duration, 0), 1)
        return t * t * (3 - 2 * t)
    }
}
