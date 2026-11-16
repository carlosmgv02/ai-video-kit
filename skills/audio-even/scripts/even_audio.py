#!/usr/bin/env python3
"""Make a voice track uniform across clips: per segment, speech loudness and long-term spectrum are pulled
toward a common reference (median of the segments), then the whole file goes to -14 LUFS / -1.5 dBTP.

  even_audio.py <in video|audio> <out> [--segments auto|a-b,c-d] [--level] [--report out.png]
  even_audio.py --selftest

Video stream is copied untouched. Audio comes out at 48 kHz.
"""
import argparse, pathlib, re, subprocess, sys, tempfile
import numpy as np
import soundfile as sf
from scipy import signal

SR = 48000
N = 2048                      # analysis frame (43 ms): speech detection and spectrum
HOP = 512                     # STFT hop for applying the correction
SCENE = 0.25                  # lower than prep.py's 0.42: a cut between two takes of the same person scored 0.31-0.40;
                              # a false split only costs a small correction toward the median
XFADE = 0.03                  # crossfade between segment corrections, s
MAX_EQ, MAX_GAIN = 6.0, 10.0  # dB clamps per band / per segment
MAX_AIR = 3.0                 # max boost above 6 kHz: phone audio has hiss and codec mush up there
MIN_EQ_S, MIN_GAIN_S = 2.0, 0.5  # seconds of speech needed to trust a segment's spectrum / level
MIN_PAUSE = 1.0               # a pause this long splits segments when there are no shot changes
CENTERS = 1000 * 2 ** (np.arange(-10, 11) / 3)  # 1/3-octave bands 100 Hz .. 10 kHz
TP = -1.5
LEVEL = "dynaudnorm=f=250:g=15:m=3:p=0.9:r=0.1"  # --level: slow, phrase-to-phrase leveling, max +9.5 dB
# BS.1770 K-weighting at 48 kHz
KW = [([1.53512485958697, -2.69169618940638, 1.19839281085285], [1, -1.69065929318241, 0.73248077421585]),
      ([1.0, -2.0, 1.0], [1, -1.99004745483398, 0.99007225036621])]

FREQS = np.fft.rfftfreq(N, 1 / SR)
EDGES = CENTERS[:, None] * 2 ** (np.array([-1, 1]) / 6)
BANDS = np.array([(FREQS >= lo) & (FREQS < hi) for lo, hi in EDGES], float).T  # (bins, bands)
BANDS[np.argmin(abs(FREQS - CENTERS[0])), 0] = 1  # lowest band is narrower than a bin: give it its nearest one


def ff(*a):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *map(str, a)], check=True)


def ff_log(*a):
    return subprocess.run(["ffmpeg", "-hide_banner", "-nostats", *map(str, a)], capture_output=True, text=True).stderr


def has_video(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=codec_type",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    return "video" in r.stdout


def shots(path):
    ts = [float(t) for t in re.findall(r"pts_time:([\d.]+)", ff_log("-i", path, "-vf", f"select='gt(scene,{SCENE})',showinfo", "-an", "-f", "null", "-"))]
    out = []
    for t in ts:  # a camera whip gives several in a row: keep the first
        if not out or t - out[-1] > 1.0:
            out.append(t)
    return out


def frames(m):
    k = len(m) // N
    return m[:k * N].reshape(k, N)


def frame_db(m):
    return 10 * np.log10(np.mean(frames(m) ** 2, axis=1) + 1e-12)


def speech_mask(db, segs):
    """Speech frames, thresholded per segment so a quiet room still counts as speech."""
    mk = np.zeros(len(db), bool)
    for a, b in segs:
        i, j = int(a * SR / N), min(int(b * SR / N), len(db))
        d = db[i:j]
        if len(d):
            mk[i:j] = d > max(np.percentile(d, 10) + 8, np.percentile(d, 95) - 25)
    return mk


def pauses(mk):
    """Midpoints of runs of non-speech longer than MIN_PAUSE."""
    out, run = [], 0
    for i, s in enumerate(np.append(mk, True)):
        if not s:
            run += 1
        elif run:
            if run * N / SR >= MIN_PAUSE and run < i:  # skip leading silence
                out.append((i - run / 2) * N / SR)
            run = 0
    return out


def wmedian(v, w):
    o = np.argsort(v)
    c = np.cumsum(np.asarray(w)[o])
    return np.asarray(v)[o][np.searchsorted(c, c[-1] / 2)]


def measure(m, segs, mk):
    """Per segment: speech seconds, speech LUFS (ungated, K-weighted), band shape (dB, mean 0), tilt, centroid."""
    kf = frames(signal.lfilter(*KW[1], signal.lfilter(*KW[0], m)))
    P = np.abs(np.fft.rfft(frames(m) * np.hanning(N), axis=1)) ** 2
    out = []
    for a, b in segs:
        idx = np.flatnonzero(mk[int(a * SR / N):int(b * SR / N)]) + int(a * SR / N)
        if not len(idx):
            out.append(dict(speech=0.0, lufs=np.nan, shape=np.zeros(len(CENTERS)), tilt=np.nan, centroid=np.nan))
            continue
        p = P[idx].mean(0)
        bands = 10 * np.log10(p @ BANDS + 1e-20)
        voice = (FREQS > 80) & (FREQS < 12000)
        out.append(dict(speech=len(idx) * N / SR,
                        lufs=-0.691 + 10 * np.log10(np.mean(kf[idx] ** 2) + 1e-12),
                        shape=bands - bands.mean(),
                        tilt=np.polyfit(np.log2(CENTERS), bands, 1)[0],
                        centroid=(FREQS[voice] * p[voice]).sum() / p[voice].sum()))
    return out


def spread(ms):
    lv = [s["lufs"] for s in ms if s["speech"] >= MIN_GAIN_S]
    return max(lv) - min(lv) if lv else 0.0


def shape_dev(ms):
    """Mean RMS distance (dB) of each trusted segment's spectrum shape to their weighted median."""
    ok = [s for s in ms if s["speech"] >= MIN_EQ_S]
    if len(ok) < 2:
        return 0.0
    ref = np.array([wmedian([s["shape"][k] for s in ok], [s["speech"] for s in ok]) for k in range(len(CENTERS))])
    return float(np.mean([np.sqrt(np.mean((s["shape"] - ref) ** 2)) for s in ok]))


def eq_curves(ms):
    ok = [s for s in ms if s["speech"] >= MIN_EQ_S]
    if len(ok) < 2:
        return [np.zeros(len(CENTERS)) for _ in ms]
    ref = np.array([wmedian([s["shape"][k] for s in ok], [s["speech"] for s in ok]) for k in range(len(CENTERS))])
    kern = np.array([1, 2, 3, 2, 1]) / 9  # smooth across bands: correct the tone, not single phonemes
    out = []
    for s in ms:
        if s["speech"] < MIN_EQ_S:
            out.append(np.zeros(len(CENTERS)))
            continue
        e = np.convolve(np.pad(ref - s["shape"], 2, mode="edge"), kern, mode="valid")
        e = np.clip(e - e.mean(), -MAX_EQ, MAX_EQ)
        out.append(np.where(CENTERS > 6000, np.minimum(e, MAX_AIR), e))
    return out


def apply(y, segs, eqs, gains):
    """STFT gain per (frame, bin): each segment's EQ + gain, linear crossfade of XFADE at boundaries."""
    f, t, Z = signal.stft(y.T, SR, nperseg=N, noverlap=N - HOP)
    G = np.zeros((len(f), len(t)))
    lf = np.log(np.maximum(f, 1))
    for i, ((a, b), e, g) in enumerate(zip(segs, eqs, gains)):
        a = -np.inf if i == 0 else a
        b = np.inf if i == len(segs) - 1 else b
        w = np.clip((t - a) / XFADE + 0.5, 0, 1) * np.clip((b - t) / XFADE + 0.5, 0, 1)
        curve = np.interp(lf, np.log([50, *CENTERS, 16000]), [0, *e, 0]) + g  # taper to 0 outside the voice range
        G += curve[:, None] * w[None, :]
    _, x = signal.istft(Z * 10 ** (G / 20), SR, nperseg=N, noverlap=N - HOP)
    return x.T[:len(y)]


def correct(y, segs, mk):
    """Returns corrected audio, before/after-correction measurements, EQ curves and gains."""
    m = y.mean(1)
    before = measure(m, segs, mk)
    eqs = eq_curves(before)
    mid = measure(apply(y, segs, eqs, [0] * len(segs)).mean(1), segs, mk)
    ok = [s for s in before if s["speech"] >= MIN_GAIN_S]
    ref = wmedian([s["lufs"] for s in ok], [s["speech"] for s in ok]) if ok else 0
    gains = [float(np.clip(ref - s["lufs"], -MAX_GAIN, MAX_GAIN)) if s["speech"] >= MIN_GAIN_S else 0.0 for s in mid]
    return apply(y, segs, eqs, gains), before, eqs, gains


def lufs_tp(path):
    log = ff_log("-i", path, "-af", "ebur128=peak=true", "-f", "null", "-")
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", log)[-1]), float(re.findall(r"Peak:\s+(-?[\d.inf]+) dBFS", log)[-1])


def master(src, dst, level, tmp):
    """Optional phrase leveling, then linear gain to -14 LUFS and an oversampled peak limiter at TP.
    Linear gain + limiter instead of single-pass loudnorm: loudnorm's dynamic mode is an AGC and can pump."""
    pre = pathlib.Path(tmp) / "pre.wav"
    ff("-i", src, "-af", LEVEL if level else "anull", "-c:a", "pcm_f32le", pre)
    i, _ = lufs_tp(pre)
    lim = 10 ** ((TP - 0.3) / 20)  # 0.3 dB margin for the AAC encode
    gain = -14 - i
    for _ in range(2):  # second pass adds back what the limiter took
        ff("-i", pre, "-af", f"volume={gain:.2f}dB,aresample=192000,"
           f"alimiter=limit={lim:.4f}:attack=2:release=80:level=0:latency=1,aresample={SR}", "-c:a", "pcm_f32le", dst)
        gain += -14 - lufs_tp(dst)[0]


def table(segs, before, after, eqs, gains):
    print(f"{'segment':>13} {'speech':>6} {'LUFS antes':>10} {'después':>8} {'tilt antes':>10} {'después':>8} "
          f"{'centr antes':>11} {'después':>8} {'gain':>6}  EQ")
    for (a, b), s, t, e, g in zip(segs, before, after, eqs, gains):
        top = np.argsort(-abs(e))[:3]
        moves = " ".join(f"{e[k]:+.1f}@{CENTERS[k]:.0f}" for k in sorted(top) if abs(e[k]) >= 0.5) or "-"
        print(f"{a:6.2f}-{b:6.2f} {s['speech']:5.1f}s {s['lufs']:10.1f} {t['lufs']:8.1f} {s['tilt']:10.2f} {t['tilt']:8.2f} "
              f"{s['centroid']:11.0f} {t['centroid']:8.0f} {g:+6.1f}  {moves}")


def report(path, segs, before, after):
    from PIL import Image, ImageDraw, ImageFont
    W, H, M = 1400, 560, 50
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    try:  # the bundled default font has no accents
        d.font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 13)
    except OSError:
        d.font = ImageFont.load_default(size=13)
    cols = [(220, 50, 47), (38, 139, 210), (133, 153, 0), (211, 54, 130), (181, 137, 0), (42, 161, 152), (108, 113, 196), (203, 75, 22)]
    pw = (W - 3 * M) // 2
    for p, (title, ms) in enumerate([("antes", before), ("después", after)]):
        x0 = M + p * (pw + M)
        y0, ph = 40, H - 140
        X = lambda f: x0 + pw * (np.log(f / 80) / np.log(12500 / 80))
        Y = lambda db: y0 + ph / 2 - db * ph / 50  # ±25 dB
        d.rectangle([x0, y0, x0 + pw, y0 + ph], outline="black")
        for db in (-20, -10, 0, 10, 20):
            d.line([x0, Y(db), x0 + pw, Y(db)], fill=(225, 225, 225))
            d.text((x0 - 28, Y(db) - 6), f"{db:+d}", fill="black")
        for f in (100, 250, 500, 1000, 2000, 4000, 10000):
            d.line([X(f), y0, X(f), y0 + ph], fill=(225, 225, 225))
            d.text((X(f) - 12, y0 + ph + 4), f"{f // 1000}k" if f >= 1000 else str(f), fill="black")
        d.text((x0, 12), f"{title}: forma del espectro de voz por segmento (dB, media 0)   "
                         f"dispersión {shape_dev(ms):.2f} dB, LUFS spread {spread(ms):.1f} dB", fill="black")
        for i, s in enumerate(ms):
            if s["speech"] < MIN_GAIN_S:
                continue
            c = cols[i % len(cols)]
            d.line([(X(f), Y(v)) for f, v in zip(CENTERS, s["shape"])], fill=c, width=2)
            a, b = segs[i]
            d.text((x0 + (i % 3) * pw // 3, y0 + ph + 24 + (i // 3) * 16), f"{a:.1f}-{b:.1f}s  {s['lufs']:.1f} LUFS", fill=c)
    img.save(path)


def run(inp, out, seg_arg, level, rep):
    inp, out = pathlib.Path(inp).resolve(), pathlib.Path(out).resolve()
    if inp == out:
        sys.exit("out must be a different file from in")
    video = has_video(inp)
    with tempfile.TemporaryDirectory() as tmp:
        ff("-i", inp, "-vn", "-ar", SR, "-c:a", "pcm_f32le", f"{tmp}/in.wav")
        y, _ = sf.read(f"{tmp}/in.wav", dtype="float64", always_2d=True)
        dur = len(y) / SR
        db = frame_db(y.mean(1))
        if seg_arg == "auto":
            sh, pa = shots(inp) if video else [], pauses(speech_mask(db, [(0, dur)]))
            cuts = sorted(sh + [p for p in pa if all(abs(p - s) > 1 for s in sh)])
            how = f"{len(sh)} cambios de plano + {len(cuts) - len(sh)} pausas ≥ {MIN_PAUSE:.0f} s"
        else:
            cuts = sorted({float(x) for r in seg_arg.split(",") for x in r.split("-")})
            how = "segmentos a mano"
        cuts = [c for c in cuts if 0.5 < c < dur - 0.5]
        edges = [0.0, *cuts, dur]
        segs = list(zip(edges[:-1], edges[1:]))
        print(f"{inp.name}: {dur:.1f} s, {len(segs)} segmentos ({how})")
        mk = speech_mask(db, segs)
        ycorr, before, eqs, gains = correct(y, segs, mk)
        sf.write(f"{tmp}/corr.wav", ycorr, SR, subtype="FLOAT")
        final = pathlib.Path(tmp) / "final.wav"
        master(f"{tmp}/corr.wav", final, level, tmp)
        yf, _ = sf.read(final, dtype="float64", always_2d=True)
        yf = np.pad(yf, ((0, max(0, len(y) - len(yf))), (0, 0)))[:len(y)]
        after = measure(yf.mean(1), segs, mk)
        table(segs, before, after, eqs, gains)
        i, tp = lufs_tp(final)
        print(f"LUFS spread entre segmentos: {spread(before):.1f} -> {spread(after):.1f} dB")
        print(f"diferencia de espectro (RMS a la mediana): {shape_dev(before):.2f} -> {shape_dev(after):.2f} dB")
        print(f"salida: {i:.1f} LUFS, true peak {tp:.1f} dBTP (objetivo -14 / {TP})")
        if video:
            ff("-i", inp, "-i", final, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
               "-ar", SR, "-movflags", "+faststart", out)
        else:
            ff("-i", final, *(["-c:a", "pcm_s24le"] if out.suffix == ".wav" else []), out)
        if rep:
            report(rep, segs, before, after)
            print(f"report {pathlib.Path(rep).resolve()}")
    print(f"done {out}")


def selftest():
    """Two noise 'voices' with on/off pauses, different level (10 dB) and tilt (1.5 dB/oct): after correction
    they must match within 1 dB in level and spectrum shape."""
    rng = np.random.default_rng(0)

    def voice(tilt, lvl, sec):
        f = np.fft.rfftfreq(SR * sec, 1 / SR)
        spec = np.fft.rfft(rng.standard_normal(SR * sec)) * 10 ** (tilt * np.log2(np.maximum(f, 20) / 1000) / 20)
        x = np.fft.irfft(spec, SR * sec)
        gate = (np.arange(len(x)) / SR) % 0.6 < 0.4  # 0.4 s on, 0.2 s off
        x = x / np.std(x) * 10 ** (lvl / 20) * gate + 1e-4 * rng.standard_normal(len(x))
        return x

    y = np.concatenate([voice(-3.0, -20, 6), voice(-1.5, -30, 4)])[:, None]
    segs = [(0.0, 6.0), (6.0, 10.0)]
    mk = speech_mask(frame_db(y[:, 0]), segs)
    out, before, eqs, gains = correct(y, segs, mk)
    after = measure(out[:, 0], segs, mk)
    assert spread(before) > 7, spread(before)
    assert shape_dev(before) > 1.2, shape_dev(before)
    assert spread(after) < 1, spread(after)
    assert np.sqrt(np.mean((after[0]["shape"] - after[1]["shape"]) ** 2)) < 1, after
    assert abs(gains[0]) < 0.5 and gains[1] > 6, gains  # the long segment is the reference, the short one moves
    assert pauses(np.array([1] * 10 + [0] * 30 + [1] * 10, bool)) == [25 * N / SR]
    print(f"selftest ok: spread {spread(before):.1f} -> {spread(after):.2f} dB, "
          f"shape {shape_dev(before):.2f} -> {shape_dev(after):.2f} dB, gains {gains[0]:+.1f} / {gains[1]:+.1f}")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
        sys.exit()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inp")
    ap.add_argument("out")
    ap.add_argument("--segments", default="auto", help="auto (shot changes, or long pauses) or a-b,c-d in seconds")
    ap.add_argument("--level", action="store_true", help="also even phrase-to-phrase loudness (gentle dynaudnorm)")
    ap.add_argument("--report", help="PNG with the per-segment spectra before/after")
    a = ap.parse_args()
    run(a.inp, a.out, a.segments, a.level, a.report)
