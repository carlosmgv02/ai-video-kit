#!/usr/bin/env python3
"""Cuts the person out of a video: transparent video for "text behind the person" layers.

  matte.py <in.mp4> <out.webm|out.mov> [--mode person|subject] [--from S] [--to S]
           [--smooth 3] [--shrink 2] [--grow 0] [--feather 1.5]

- Apple Vision per frame (macOS only). person = people with hair detail; subject = people plus what they hold.
- --smooth N averages N neighbour masks (kills edge flicker); --shrink/--grow move the edge in/out by pixels;
  --feather blurs the edge. Grey halo around him: --shrink 3. Hair eaten: --shrink 0 --grow 1.
- .webm = VP9 with alpha (small; Remotion <OffthreadVideo transparent>). .mov = ProRes 4444 (big, exact).
- Also writes <out>_mask.mp4 (grey mask) to inspect, and warns when the person fills the frame
  (then text behind him has nowhere to show).
"""
import json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BIN = HERE / "bin/personmask"


def build():
    src = HERE / "personmask.swift"
    if BIN.exists() and BIN.stat().st_mtime > src.stat().st_mtime:
        return
    BIN.parent.mkdir(exist_ok=True)
    subprocess.run(["swiftc", "-O", str(src), "-o", str(BIN)], check=True)


def main(a):
    if len(a) < 2 or a[0].startswith("-"):
        sys.exit(__doc__)
    src, dst = Path(a[0]), Path(a[1])
    opt = lambda k, d: type(d)(a[a.index(k) + 1]) if k in a else d
    mode, t0, t1 = opt("--mode", "person"), opt("--from", 0.0), opt("--to", 0.0)
    smooth, shrink, grow, feather = opt("--smooth", 3), opt("--shrink", 2), opt("--grow", 0), opt("--feather", 1.5)
    assert mode in ("person", "subject"), "--mode person|subject"
    build()
    seek = (["-ss", f"{t0:.3f}"] if t0 > 0 else []) + (["-to", f"{t1:.3f}"] if t1 > 0 else [])
    s = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate", "-of", "json", str(src)], capture_output=True, text=True, check=True).stdout)["streams"][0]
    W, H, fps = s["width"], s["height"], s["r_frame_rate"]
    mask = dst.with_name(dst.stem + "_mask.mp4")

    # 1) frames -> Vision -> grey masks -> temporal smooth, edge in/out, feather -> mask.mp4
    dec = subprocess.Popen(["ffmpeg", "-v", "error", *seek, "-i", str(src), "-f", "rawvideo", "-pix_fmt", "bgra", "-"], stdout=subprocess.PIPE)
    pm = subprocess.Popen([str(BIN), str(W), str(H), mode], stdin=dec.stdout, stdout=subprocess.PIPE)
    dec.stdout.close()
    vf = ",".join(f for f in [f"tmix=frames={smooth}" if smooth > 1 else "", *["dilation"] * grow, *["erosion"] * shrink, f"gblur=sigma={feather}" if feather > 0 else "", "format=gray"] if f)
    enc = subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{W}x{H}", "-r", fps, "-i", "-", "-vf", vf, "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", str(mask)], stdin=pm.stdout)
    pm.stdout.close()
    if dec.wait() or pm.wait() or enc.returncode:
        sys.exit("mask failed")

    # 2) video + mask -> alpha video
    codec = (["-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "28", "-deadline", "realtime", "-cpu-used", "8", "-row-mt", "1", "-auto-alt-ref", "0"]
             if dst.suffix == ".webm" else ["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le"])
    subprocess.run(["ffmpeg", "-v", "error", "-y", *seek, "-i", str(src), "-i", str(mask), "-filter_complex",
                    f"[1:v]format=gray,scale={W}:{H}[m];[0:v][m]alphamerge", "-an", *codec, str(dst)], check=True)

    # 3) how much of the frame is him: text behind needs background around the head
    cov = subprocess.run(["ffmpeg", "-v", "error", "-i", str(mask), "-vf", "fps=1,scale=64:-2,format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
    frac = sum(b > 128 for b in cov) / max(1, len(cov))
    print(f"ok {dst} ({W}x{H}, person ≈ {frac:.0%} of the frame)  mask: {mask}")
    if frac > 0.6:
        print("warning: the person fills most of the frame; text behind will be hidden. Use a wider shot or put the text above the head.")


if __name__ == "__main__":
    main(sys.argv[1:])
