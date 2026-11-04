import Foundation
import CoreGraphics

/// Layout of the body inside a transparent video canvas. Effects and empty margins
/// must not determine either the body's scale or the position of its soles.
struct CharacterAnimationLayout: Decodable {
    let canvasScale: CGFloat
    let sampleRate: Double
    let referenceHeight: CGFloat
    let soleRows: [CGFloat]

    static let standard = CharacterAnimationLayout(
        canvasScale: 1, sampleRate: 24, referenceHeight: 1920, soleRows: [1623]
    )

    private static let bundled: [String: CharacterAnimationLayout] = {
        var result: [String: CharacterAnimationLayout] = [:]
        for resource in ["zenitsu-animation-layouts", "inosuke-animation-layouts", "tanjiro-animation-layouts", "nezuko-animation-layouts", "bill-animation-layouts", "amit-animation-layouts"] {
            guard let url = Bundle.main.url(forResource: resource, withExtension: "json"),
                  let data = try? Data(contentsOf: url),
                  let layouts = try? JSONDecoder().decode([String: CharacterAnimationLayout].self, from: data)
            else { continue }
            result.merge(layouts) { _, new in new }
        }
        return result
    }()

    static func forVideo(_ name: String) -> CharacterAnimationLayout {
        bundled[name] ?? .standard
    }

    func bottomPaddingFraction(at time: Double) -> CGFloat {
        guard !soleRows.isEmpty, referenceHeight > 0, sampleRate > 0 else { return 0 }
        let index = min(max(time.isFinite ? time * sampleRate : 0, 0), Double(soleRows.count - 1))
        let lower = Int(index)
        let upper = min(lower + 1, soleRows.count - 1)
        let mix = CGFloat(index - Double(lower))
        let sole = soleRows[lower] + (soleRows[upper] - soleRows[lower]) * mix
        return 1 - sole / referenceHeight
    }

    func windowOrigin(
        centerX: CGFloat, groundY: CGFloat, canvasSize: CGSize, time: Double
    ) -> CGPoint {
        CGPoint(
            x: centerX - canvasSize.width / 2,
            y: groundY - canvasSize.height * bottomPaddingFraction(at: time)
        )
    }
}
