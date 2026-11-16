#!/usr/bin/env python3
"""Even out light and colour across the shots of a phone video.

1. finds shots with ffmpeg scene detection
2. per shot: mid-tone luma median and R/G/B medians of near-grey pixels (sampled at 2 fps, downscaled)
3. picks a reference shot and computes a gamma + R/G/B gains per shot, clamped
4. applies everything in one ffmpeg pass (timeline `enable=` per shot) + a centred per-frame deflicker
5. re-measures the output and prints a before/after table

usage: even_light.py <in.mp4> <out.mp4> [--ref auto|<seconds>] [--report out.png]
       even_light.py --selftest
"""
import argparse
import json
import math
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

# Lower than prep.py's 0.42: real clip joins on phone reels score 0.23-0.34, camera moves stay under 0.07.
SCENE = 0.2
MIN_SHOT = 1.0          # cuts closer than this (camera whip) count as one
SAMPLE_FPS = 2
LO, HI = 0.06, 0.94     # mid-tone window: ignores black shadows and blown white walls
NEUTRAL = 0.2          # saturation (relative to the cast) under this counts as grey for white balance
GAMMA_LIM = (0.75, 1.35)
GAIN_LIM = (0.88, 1.12)
PUMP_WIN = 1.0         # s: luma swings faster than this inside a shot are pumping and get flattened
PUMP_LIM = (0.93, 1.07)  # per-frame gamma limits (about +-4 % luma): gentle, never hides a real change
W709 = np.array([0.2126, 0.7152, 0.0722])


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,r_frame_rate,color_range,color_space,color_transfer,color_primaries:format=duration",
                        "-of", "json", path], capture_output=True, text=True, check=True)
    j = json.loads(r.stdout)
    s = j["streams"][0]
    num, den = s["r_frame_rate"].split("/")
    s["fps"] = float(num) / float(den)
    s["duration"] = float(j["format"]["duration"])
    return s


def find_shots(path, dur):
    r = subprocess.run(["ffmpeg", "-i", path, "-vf", f"select='gt(scene,{SCENE})',showinfo", "-an", "-f", "null", "-"],
                       capture_output=True, text=True)
    cuts = []
    for t in (float(m) for m in re.findall(r"pts_time:([\d.]+)", r.stderr)):
        if t > MIN_SHOT and dur - t > MIN_SHOT and (not cuts or t - cuts[-1] > MIN_SHOT):
            cuts.append(t)
    edges = [0.0, *cuts, dur]
    return list(zip(edges[:-1], edges[1:]))


def sample(path, info):
    """Frames at SAMPLE_FPS, downscaled to 64 px wide, RGB 0..1, shape (frames, pixels, 3)."""
    w, h = 64, max(2, round(64 * info["height"] / info["width"] / 2) * 2)
    rng = "pc" if info.get("color_range") == "pc" else "tv"
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-an", "-vf",
                          f"fps={SAMPLE_FPS},scale={w}:{h}:flags=area:in_color_matrix=bt709:in_range={rng},format=rgb24",
                          "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h * w, 3) / 255.0


def masks(frames):
    """Per frame: mid-tone pixels (for luma) and near-grey mid-tones (for white balance).
    Taken from the source and reused on the output, so before/after compare the same pixels."""
    out = []
    for px in frames:
        y = px @ W709
        mid = (y > LO) & (y < HI)
        if mid.sum() < 0.05 * len(px):  # almost all black or blown: use everything rather than nothing
            mid[:] = True
        # WB from near-grey pixels (walls, ceiling, grey clothes): their cast is the light, not the blue cabinets.
        # The grey test follows the cast estimate, so a strong uniform cast does not push the greys out.
        cast, wb = np.ones(3), mid
        for _ in range(3):
            n = px / cast
            grey = mid & ((n.max(1) - n.min(1)) / (n.max(1) + 1e-6) < NEUTRAL)
            if grey.sum() < 0.03 * len(px):
                break
            wb = grey
            cast = px[wb].mean(0) / (px[wb].mean(0) @ W709)
        out.append((mid, wb))
    return out


def measure(frames, ms):
    """Per frame: (t, median mid-tone luma, median R, G, B of the grey pixels). Medians commute with
    per-channel curves, so the output reads exactly what the correction did."""
    return np.array([(i / SAMPLE_FPS, np.median(px[mid] @ W709), *np.median(px[wb], axis=0))
                     for i, (px, (mid, wb)) in enumerate(zip(frames, ms))])


def per_shot(rows, shots):
    out = []
    for a, b in shots:
        r = rows[(rows[:, 0] >= a) & (rows[:, 0] < b)]
        if not len(r):  # shot shorter than the sample step
            r = rows[[np.argmin(abs(rows[:, 0] - (a + b) / 2))]]
        out.append({"luma": float(np.median(r[:, 1])), "rgb": np.median(r[:, 2:5], axis=0)})
    return out


def frame_luma(path, info):
    """Mean Y of every frame as eq sees it (code value / 255): the series where pumping shows."""
    h = max(2, round(32 * info["height"] / info["width"] / 2) * 2)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-an", "-vf", f"scale=32:{h}:flags=area,format=gray",
                          "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, 32 * h).mean(1) / 255


def shot_spans(n, fps, shots):
    t = np.arange(n) / fps  # shortcut: assumes constant frame rate (phones and WhatsApp give 30/1), use pts if VFR
    return [(t >= a) & (t < b) for a, b in shots]


def pump_gammas(y, fps, shots):
    """Per-frame eq gamma that pulls each frame to its centred PUMP_WIN average, never across a cut.
    ffmpeg's deflicker made camera-move shots worse on real footage (luma std 0.026 -> 0.032 at size 31),
    most likely because its window is not centred."""
    y = np.clip(y, 0.02, 0.98)
    out = np.ones(len(y))
    k = np.ones(max(3, round(PUMP_WIN * fps) | 1))
    for m in shot_spans(len(y), fps, shots):
        seg = y[m]
        if len(seg) < 3:
            continue
        smooth = np.convolve(seg, k, "same") / np.convolve(np.ones(len(seg)), k, "same")
        out[m] = np.clip(np.log(seg) / np.log(smooth), *PUMP_LIM)
    return out


def correction(stat, ref):
    """gamma (out = in^(1/gamma), >1 brightens) and R/G/B gains that keep luma."""
    gamma = math.log(stat["luma"]) / math.log(ref["luma"])
    gamma = min(max(gamma, GAMMA_LIM[0]), GAMMA_LIM[1])
    # chroma ratios land on the reference's after the per-channel power: (ratio * g)^(1/gamma) = ref ratio
    g = (ref["rgb"] / ref["rgb"][1]) ** gamma / (stat["rgb"] / stat["rgb"][1])
    g = np.clip(g / (g @ W709), *GAIN_LIM)
    return gamma, g / (g @ W709)  # renormalise after clipping so WB never shifts exposure


def pick_ref(stats, shots, ref):
    if ref == "auto":  # median-brightness shot
        return int(np.argsort([s["luma"] for s in stats])[len(stats) // 2])
    t = float(ref)
    return next((i for i, (a, b) in enumerate(shots) if a <= t < b), len(shots) - 1)


def build_filter(shots, corr, info, cmds):
    """One lutrgb per shot (gain then gamma, per channel), enabled only inside its shot, then per-frame eq."""
    rng = "pc" if info.get("color_range") == "pc" else "tv"
    luts = [f"lutrgb=" + ":".join(f"{c}='maxval*pow(clip(val/maxval*{g[k]:.4f},0,1),{1 / gm:.4f})'"
                                  for k, c in enumerate("rgb")) + f":enable='gte(t,{a:.3f})*lt(t,{b:.3f})'"
            for (a, b), (gm, g) in zip(shots, corr) if abs(gm - 1) > 0.004 or np.abs(g - 1).max() > 0.004]
    vf = []
    if luts:  # 16-bit RGB with explicit bt709 both ways: the round trip never shifts colour or bands
        vf = [f"scale=in_color_matrix=bt709:in_range={rng}:out_range=pc,format=gbrp16le", *luts,
              f"scale=out_color_matrix=bt709:in_range=pc:out_range={rng},format=yuv420p"]
    vf += [f"sendcmd=f='{cmds}'", "eq@pump=gamma=1"]
    return ",".join(vf)


def render(src, dst, vf, info):
    meta = []
    for opt, key in (("-color_range", "color_range"), ("-colorspace", "color_space"),
                     ("-color_trc", "color_transfer"), ("-color_primaries", "color_primaries")):
        if info.get(key) and info[key] != "unknown":
            meta += [opt, info[key]]
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-map", "0:v:0", "-map", "0:a?", "-vf", vf,
                    "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", *meta,
                    "-c:a", "copy", "-movflags", "+faststart", dst], check=True)


def report(src, dst, shots, fps, png):
    """Top row: one frame per shot before. Bottom row: the same frames after. No labels (no drawtext here)."""
    sel = "+".join(f"eq(n,{round((a + b) / 2 * fps)})" for a, b in shots)
    strip = f"select='{sel}',scale=270:-2,tile={len(shots)}x1:padding=6:color=white"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-i", dst, "-filter_complex",
                    f"[0:v]{strip}[a];[1:v]{strip}[b];[a][b]vstack", "-fps_mode", "passthrough",
                    "-frames:v", "1", png], check=True)


def selftest():
    ref = {"luma": 0.45, "rgb": np.array([0.45, 0.45, 0.45])}
    # same shot: no correction
    gm, g = correction(ref, ref)
    assert abs(gm - 1) < 1e-9 and np.allclose(g, 1)
    # darker shot: gamma > 1 and it lands exactly on the reference
    dark = {"luma": 0.35, "rgb": np.array([0.35, 0.35, 0.35])}
    gm, _ = correction(dark, ref)
    assert gm > 1 and abs(0.35 ** (1 / gm) - 0.45) < 1e-9
    # very dark shot: clamped, never more than the limit
    gm, _ = correction({"luma": 0.05, "rgb": np.array([0.05] * 3)}, ref)
    assert gm == GAMMA_LIM[1]
    # warm shot: red down, blue up, gains keep luma and stay in limits
    warm = {"luma": 0.45, "rgb": np.array([0.48, 0.45, 0.42])}
    _, g = correction(warm, ref)
    assert g[0] < 1 < g[2] and abs(g @ W709 - 1) < 1e-9
    assert GAIN_LIM[0] - 0.02 < g.min() and g.max() < GAIN_LIM[1] + 0.02
    # warm shot after gains has the reference's chroma ratios
    fixed = warm["rgb"] * g
    assert np.allclose(fixed / fixed[1], [1, 1, 1], atol=0.01)
    # dark warm shot vs a warm reference: ratios still land after gain + gamma
    wref = {"luma": 0.45, "rgb": np.array([0.47, 0.45, 0.43])}
    dw = {"luma": 0.35, "rgb": np.array([0.36, 0.35, 0.35])}
    gm, g = correction(dw, wref)
    out = (dw["rgb"] * g) ** (1 / gm)
    assert np.allclose(out / out[1], wref["rgb"] / wref["rgb"][1], atol=0.005)
    # reference picking
    stats = [{"luma": v} for v in (0.3, 0.5, 0.4)]
    shots = [(0, 5), (5, 9), (9, 12)]
    assert pick_ref(stats, shots, "auto") == 2 and pick_ref(stats, shots, "6") == 1
    # pumping: a 1 s wobble gets flatter, a steady shot is untouched, a cut is never smoothed over
    fps, t = 30, np.arange(300) / 30
    y = 0.5 + 0.03 * np.sin(2 * np.pi * t / 0.8)
    fixed = np.clip(y, 0.02, 0.98) ** (1 / pump_gammas(y, fps, [(0, 10)]))
    assert fixed.std() < 0.5 * y.std()
    step = np.where(t < 5, 0.3, 0.6)
    assert np.allclose(pump_gammas(step, fps, [(0, 5), (5, 10)]), 1)
    assert np.all(pump_gammas(step, fps, [(0, 10)]) <= PUMP_LIM[1])
    print("selftest ok")


def main():
    if "--selftest" in sys.argv:
        return selftest()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--ref", default="auto", help="auto (median shot) or a second inside the reference shot")
    ap.add_argument("--report", help="png: one frame per shot, before (top) and after (bottom)")
    a = ap.parse_args()

    info = probe(a.src)
    if info.get("color_transfer") in ("arib-std-b67", "smpte2084"):
        sys.exit("HDR video: convert it to SDR first (avconvert or ffmpeg tonemap)")
    shots = find_shots(a.src, info["duration"])
    src = sample(a.src, info)
    ms = masks(src)
    before = per_shot(measure(src, ms), shots)
    y0 = frame_luma(a.src, info)
    ri = pick_ref(before, shots, a.ref)
    corr = [correction(s, before[ri]) for s in before]
    with tempfile.TemporaryDirectory() as tmp:
        cmds, last = Path(tmp) / "pump.txt", None
        with open(cmds, "w") as f:
            for i, g in enumerate(pump_gammas(y0, info["fps"], shots)):
                if last is None or abs(g - last) > 0.0005:
                    f.write(f"{max(0, i / info['fps'] - 0.005):.4f} eq@pump gamma {g:.4f};\n")
                    last = g
        render(a.src, a.dst, build_filter(shots, corr, info, cmds), info)
    out = sample(a.dst, info)
    n = min(len(src), len(out))
    after = per_shot(measure(out[:n], ms[:n]), shots)
    y1 = frame_luma(a.dst, info)
    for st, y in ((before, y0), (after, y1)):  # pump = std of per-frame luma inside the shot
        for x, m in zip(st, shot_spans(len(y), info["fps"], shots)):
            x["pump"] = float(y[m].std()) if m.any() else 0.0

    rb = lambda x: f"{x['rgb'][0] / x['rgb'][1]:.3f}/{x['rgb'][2] / x['rgb'][1]:.3f}"
    print(f"{'shot':>4}  {'start-end':>13}  {'luma before':>11}  {'after':>5}  {'pump before':>11}  {'after':>5}"
          f"  {'R/G,B/G before':>14}  {'after':>11}  {'gamma':>5}  WB gains R/G/B")
    for i, ((s, e), b, f, (gm, g)) in enumerate(zip(shots, before, after, corr)):
        mark = "  ref" if i == ri else ""
        print(f"{i + 1:>4}  {s:6.2f}-{e:6.2f}  {b['luma']:11.3f}  {f['luma']:5.3f}  {b['pump']:11.3f}  {f['pump']:5.3f}"
              f"  {rb(b):>14}  {rb(f):>11}  {gm:5.3f}  {g[0]:.3f}/{g[1]:.3f}/{g[2]:.3f}{mark}")
    spread = lambda st, k: max(map(k, st)) - min(map(k, st))
    for name, k in (("luma", lambda x: x["luma"]), ("R/G", lambda x: x["rgb"][0] / x["rgb"][1]),
                    ("B/G", lambda x: x["rgb"][2] / x["rgb"][1])):
        print(f"{name} spread between shots: {spread(before, k):.3f} -> {spread(after, k):.3f}")
    if a.report:
        report(a.src, a.dst, shots, info["fps"], a.report)
        print(f"report: {a.report}")


if __name__ == "__main__":
    main()
