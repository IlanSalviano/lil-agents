import Foundation
import CoreGraphics

func runCharacterAnimationLayoutTests() throws {
    func expect(_ condition: @autoclosure () -> Bool, _ message: String) {
        if !condition() {
            fputs("FAIL: \(message)\n", stderr)
            exit(1)
        }
    }
    let path = CommandLine.arguments.dropFirst().first ?? "LilAgents/zenitsu-animation-layouts.json"
    let data = try Data(contentsOf: URL(fileURLWithPath: path))
    let layouts = try JSONDecoder().decode([String: CharacterAnimationLayout].self, from: data)
    let walk = layouts["walk-zenitsu-01"]!
    let thunder = layouts["special-zenitsu-thunder-01"]!
    let flame = layouts["special-zenitsu-flame-01"]!

    expect(walk.soleRows.count == 241 && thunder.soleRows.count == 145 && flame.soleRows.count == 145,
           "calibration covers every decoded movie frame, including recovery")
    // Body measurements exclude sword, lightning, and dragon. Their standing
    // heights should match the original walk at every menu size.
    for height: CGFloat in [100, 150, 200] {
        let bodyHeight = height * 652 / 960
        expect(abs(height * thunder.canvasScale * 587 / 960 - bodyHeight) < 1,
               "thunder recovery preserves the walking body's size")
        expect(abs(height * flame.canvasScale * 259 / 960 - bodyHeight) < 1,
               "flame recovery preserves the walking body's size")
        for layout in [walk, thunder, flame] {
            let canvas = CGSize(width: height * layout.canvasScale * 1080 / 1920,
                                height: height * layout.canvasScale)
            for (index, sole) in layout.soleRows.enumerated() {
                let time = Double(index) / 24
                for centerX: CGFloat in [-1200, 3600] {
                    let origin = layout.windowOrigin(centerX: centerX, groundY: 90, canvasSize: canvas, time: time)
                    let screenSole = origin.y + canvas.height - sole * canvas.height / 960
                    expect(abs(screenSole - 90) < 0.0001, "soles touch the Dock through the complete action")
                    expect(abs(origin.x + canvas.width / 2 - centerX) < 0.0001,
                           "larger FX canvases preserve the character's horizontal anchor")
                }
            }
        }
    }
    expect(flame.soleRows[0] == 672 && flame.soleRows[120] == 740,
           "flame anchors track sandals rather than the lower fire sword")
    expect(walk.bottomPaddingFraction(at: -.infinity) == walk.bottomPaddingFraction(at: 0),
           "invalid playheads cannot move the character off screen")
    expect(flame.bottomPaddingFraction(at: 100) == flame.bottomPaddingFraction(at: 6),
           "the last frame remains grounded when the player holds at the end")
    print("CharacterAnimationLayout tests passed (all frames, three sizes, both display origins)")
}
