// Per-frame subject mask with Apple Vision. Reads raw BGRA frames on stdin, writes 8-bit gray masks
// (same W x H) on stdout. Mode "person" = VNGeneratePersonSegmentationRequest (people only, hair-aware);
// "subject" = VNGenerateForegroundInstanceMaskRequest (people plus what they hold, e.g. a product).
//   personmask <width> <height> [person|subject]
import CoreImage
import CoreVideo
import Foundation
import Vision

let args = CommandLine.arguments
guard args.count >= 3, let W = Int(args[1]), let H = Int(args[2]) else {
    FileHandle.standardError.write("usage: personmask <w> <h> [person|subject]\n".data(using: .utf8)!)
    exit(2)
}
let mode = args.count > 3 ? args[3] : "person"
let frameBytes = W * H * 4
let ctx = CIContext(options: [.workingColorSpace: NSNull()])
let gray = CGColorSpaceCreateDeviceGray()
let seq = VNSequenceRequestHandler() // keeps state between frames: steadier person masks
var buf = [UInt8](repeating: 0, count: frameBytes)
var out = [UInt8](repeating: 0, count: W * H)
let stdin = FileHandle.standardInput
let stdout = FileHandle.standardOutput

func readFrame() -> Bool {
    var got = 0
    while got < frameBytes {
        let d = stdin.readData(ofLength: frameBytes - got)
        if d.isEmpty { return false }
        d.withUnsafeBytes { p in buf.withUnsafeMutableBytes { b in b.baseAddress!.advanced(by: got).copyMemory(from: p.baseAddress!, byteCount: d.count) } }
        got += d.count
    }
    return true
}

while readFrame() {
    var pb: CVPixelBuffer?
    buf.withUnsafeMutableBytes { b in
        _ = CVPixelBufferCreateWithBytes(nil, W, H, kCVPixelFormatType_32BGRA, b.baseAddress!, W * 4, nil, nil, nil, &pb)
    }
    var mask: CIImage?
    if let pb {
        if mode == "subject" {
            let req = VNGenerateForegroundInstanceMaskRequest()
            let h = VNImageRequestHandler(cvPixelBuffer: pb)
            if (try? h.perform([req])) != nil, let r = req.results?.first,
               let m = try? r.generateScaledMaskForImage(forInstances: r.allInstances, from: h) {
                mask = CIImage(cvPixelBuffer: m)
            }
        } else {
            let req = VNGeneratePersonSegmentationRequest()
            req.qualityLevel = .accurate
            req.outputPixelFormat = kCVPixelFormatType_OneComponent8
            if (try? seq.perform([req], on: pb)) != nil, let m = req.results?.first?.pixelBuffer {
                mask = CIImage(cvPixelBuffer: m)
            }
        }
    }
    if let m = mask {
        // Vision masks come smaller than the frame: scale to W x H
        let s = m.transformed(by: CGAffineTransform(scaleX: CGFloat(W) / m.extent.width, y: CGFloat(H) / m.extent.height))
        out.withUnsafeMutableBytes { o in
            ctx.render(s, toBitmap: o.baseAddress!, rowBytes: W, bounds: CGRect(x: 0, y: 0, width: W, height: H), format: .L8, colorSpace: gray)
        }
    } else {
        for i in 0..<out.count { out[i] = 0 }
    }
    stdout.write(Data(out))
}
