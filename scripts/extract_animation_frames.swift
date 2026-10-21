// swiftc -parse-as-library scripts/extract_animation_frames.swift -o /tmp/extract-animation-frames
// /tmp/extract-animation-frames LilAgents build/animation-review/all-frames
import AVFoundation
import AppKit

@main
struct ExtractAnimationFrames {
    static func main() async throws {
        guard CommandLine.arguments.count >= 3 else {
            fatalError("Usage: extract-animation-frames <movies-directory> <frames-directory> [--full-resolution] [movie names]")
        }
        let root = URL(fileURLWithPath: CommandLine.arguments[1])
        let output = URL(fileURLWithPath: CommandLine.arguments[2])
        let options = Array(CommandLine.arguments.dropFirst(3))
        let requestedNames = options.filter { !$0.hasPrefix("--") }
        let names = requestedNames.isEmpty ? ["walk-zenitsu-01", "special-zenitsu-thunder-01", "special-zenitsu-flame-01"] : requestedNames
        for name in names {
            let asset = AVURLAsset(url: root.appendingPathComponent(name + ".mov"))
            let duration = try await asset.load(.duration).seconds
            let generator = AVAssetImageGenerator(asset: asset)
            generator.appliesPreferredTrackTransform = true
            generator.requestedTimeToleranceBefore = .zero
            generator.requestedTimeToleranceAfter = .zero
            if !options.contains("--full-resolution") {
                generator.maximumSize = CGSize(width: 540, height: 960)
            }
            let directory = output.appendingPathComponent(name)
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
            for frame in 0..<Int((duration * 24).rounded()) {
                let time = CMTime(value: Int64(frame), timescale: 24)
                let (cgImage, _) = try await generator.image(at: time)
                let bitmap = NSBitmapImageRep(cgImage: cgImage)
                guard let data = bitmap.representation(using: .png, properties: [:]) else {
                    fatalError("PNG encoding failed for \(name), frame \(frame)")
                }
                try data.write(to: directory.appendingPathComponent(String(format: "%06.3f.png", time.seconds)))
            }
            print("Extracted \(name) at 24 fps with alpha")
        }
    }
}
