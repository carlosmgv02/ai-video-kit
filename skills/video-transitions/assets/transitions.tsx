import type { CSSProperties, ReactNode } from "react"

/**
 * CapCut-style cut transitions, pure math + one wrapper. No dependencies beyond React.
 *
 * Every transition is a "look" of the picture as a function of u = (t - cut) / dur:
 * u in [-1, 0) is the old shot running into the cut, u in [0, 1] the new shot leaving it. Outside: identity.
 * Use it two ways:
 *   1. One continuous video with jump cuts (talking head):  <CutFx look={cutLook(t, [[3.2, "flash"], [8.1, "whip"]])}>{video}</CutFx>
 *   2. Scenes in a <TransitionSeries>:  <TransitionSeries.Transition presentation={cut("flashZoom")} timing={linearTiming({ durationInFrames: frames("flashZoom", fps) })} />
 */
export type TransitionKind =
  | "flash" // white flash with a small push (CapCut "Flash")
  | "flashZoom" // zoom into the cut, white flash, the new shot settles from zoomed in
  | "zoomIn" // zoom blur through the cut (CapCut "Pull in")
  | "zoomOut" // the new shot pulls back from close with blur (CapCut "Pull out")
  | "punch" // hard cut that lands 12 % zoomed and settles: the classic jump-cut punch
  | "whip" // whip pan sideways with motion blur
  | "whipUp" // whip pan vertical
  | "spin" // rotate + zoom blur
  | "glitch" // RGB split + jitter
  | "shake" // camera shake on landing
  | "blur" // defocus through the cut
  | "dipBlack"
  | "dipWhite"
  | "lightLeak" // warm film light sweeping across
  | "warmFlash" // warm overexposed glow: the picture burns to amber light and comes back

export type Look = {
  x: number // px
  y: number
  scale: number
  rotate: number // deg
  blur: number // px
  brightness: number
  rgb: number // px of RGB channel split
  flash: number // white overlay 0..1
  dark: number // black overlay 0..1
  leak: number // light leak overlay 0..1
  leakX: number // where the leak sits, 0..1 across the frame
  warm: number // warm glow overlay 0..1
}

export const IDENTITY: Look = { x: 0, y: 0, scale: 1, rotate: 0, blur: 0, brightness: 1, rgb: 0, flash: 0, dark: 0, leak: 0, leakX: 0.5, warm: 0 }

/** Half length (s) on each side of the cut. The whole transition lasts 2 x this. */
export const HALF: Record<TransitionKind, number> = {
  flash: 0.16, flashZoom: 0.2, zoomIn: 0.22, zoomOut: 0.24, punch: 0.22, whip: 0.18, whipUp: 0.18, spin: 0.24,
  glitch: 0.18, shake: 0.32, blur: 0.22, dipBlack: 0.28, dipWhite: 0.24, lightLeak: 0.45, warmFlash: 0.26,
}

const c01 = (v: number) => Math.min(1, Math.max(0, v))
// deterministic noise so renders are identical frame to frame
const noise = (n: number) => {
  const s = Math.sin(n * 127.1 + 311.7) * 43758.5453
  return (s - Math.floor(s)) * 2 - 1
}

/** The look at u in [-1, 1]. dir alternates whips/spins (1 or -1). */
export const lookAt = (kind: TransitionKind, u: number, dir = 1): Look => {
  if (u < -1 || u > 1) return IDENTITY
  const pre = u < 0
  const p = pre ? 1 + u : 0 // 0 -> 1 into the cut
  const q = pre ? 0 : 1 - u // 1 -> 0 after the cut
  const e = 1 - Math.abs(u) // peak at the cut
  const L: Look = { ...IDENTITY }
  switch (kind) {
    case "flash":
      L.flash = e ** 3 * 0.95
      L.brightness = 1 + 0.5 * e ** 2
      L.scale = 1 + 0.05 * e
      break
    case "flashZoom":
      L.scale = pre ? 1 + 0.35 * p ** 2 : 1 + 0.25 * q ** 2
      L.blur = 16 * e ** 2
      L.flash = e ** 4 * 0.9
      L.brightness = 1 + 0.4 * e ** 2
      break
    case "zoomIn":
      L.scale = pre ? 1 + 0.5 * p ** 2 : 1 + 0.3 * q ** 2
      L.blur = 22 * e ** 2
      break
    case "zoomOut":
      L.scale = pre ? 1 + 0.06 * p : 1 + 0.6 * q ** 2
      L.blur = 20 * e ** 2
      break
    case "punch":
      L.scale = pre ? 1 : 1 + 0.12 * q ** 3
      break
    case "whip":
    case "whipUp": {
      const k = pre ? p ** 2 : -(q ** 2)
      if (kind === "whip") L.x = dir * k * 340
      else L.y = dir * k * 520
      L.blur = Math.abs(k) * 26
      L.scale = 1 + Math.abs(k) * 0.12
      break
    }
    case "spin":
      L.rotate = dir * (pre ? 16 * p ** 2 : -16 * q ** 2)
      L.scale = 1 + 0.45 * e ** 2
      L.blur = 18 * e ** 2
      break
    case "glitch": {
      const f = Math.floor((u + 1) * 30) // changes ~every frame
      L.rgb = 22 * e
      L.x = noise(f) * 34 * e
      L.y = noise(f + 7) * 10 * e
      L.brightness = 1 + 0.25 * e * (noise(f + 3) > 0.3 ? 1 : 0)
      break
    }
    case "shake":
      if (!pre) {
        const d = q ** 2
        L.x = Math.sin(u * 46) * 26 * d
        L.y = Math.cos(u * 39) * 18 * d
        L.rotate = Math.sin(u * 33) * 1.4 * d
        L.scale = 1 + 0.06 * d
      }
      break
    case "blur":
      L.blur = 30 * e ** 2
      L.brightness = 1 + 0.12 * e
      L.scale = 1 + 0.04 * e
      break
    case "dipBlack":
      L.dark = c01(e * 1.4) ** 1.5
      break
    case "dipWhite":
      L.flash = c01(e * 1.3) ** 1.5
      break
    case "warmFlash":
      L.brightness = 1 + 1.1 * e ** 2
      L.warm = e ** 1.6
      L.scale = 1 + 0.06 * e ** 2
      L.blur = 5 * e ** 3
      break
    case "lightLeak":
      L.leak = e ** 1.5
      L.leakX = (u + 1) / 2
      L.brightness = 1 + 0.25 * e ** 2
      break
  }
  // a rotated frame shows black corners unless it is zoomed enough to cover them (9:16 or 16:9)
  const r = (Math.abs(L.rotate) * Math.PI) / 180
  L.scale = Math.max(L.scale, Math.cos(r) + (16 / 9) * Math.sin(r))
  return L
}

/** Combined look at time t for a list of cuts [time, kind]. The closest active cut wins. */
export const cutLook = (t: number, cuts: readonly (readonly [number, TransitionKind])[]): Look => {
  let best: Look = IDENTITY
  let bestD = Infinity
  cuts.forEach(([c, kind], i) => {
    const d = Math.abs(t - c)
    if (d <= HALF[kind] && d < bestD) {
      bestD = d
      best = lookAt(kind, (t - c) / HALF[kind], i % 2 ? -1 : 1)
    }
  })
  return best
}

/** Frames a <TransitionSeries.Transition> needs for this kind. */
export const frames = (kind: TransitionKind, fps: number) => Math.round(HALF[kind] * 2 * fps)

let uid = 0
/** Applies a look to its children (transform + filter) and draws the flash / dip / leak overlays on top. */
export const CutFx = ({ look: L, children, origin = "50% 50%" }: { look: Look; children: ReactNode; origin?: string }) => {
  const id = `rgb${(uid = (uid + 1) % 1e6)}`
  const filters = [L.blur > 0.3 && `blur(${L.blur.toFixed(1)}px)`, L.brightness !== 1 && `brightness(${L.brightness.toFixed(3)})`, L.rgb > 0.5 && `url(#${id})`].filter(Boolean).join(" ")
  const fill: CSSProperties = { position: "absolute", inset: 0, pointerEvents: "none" }
  return (
    <div style={{ ...fill, overflow: "hidden" }}>
      {L.rgb > 0.5 && (
        <svg width={0} height={0} style={{ position: "absolute" }}>
          <filter id={id} x="-10%" y="-10%" width="120%" height="120%" colorInterpolationFilters="sRGB">
            <feOffset in="SourceGraphic" dx={-L.rgb} result="r0" />
            <feColorMatrix in="r0" type="matrix" values="1 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0" result="r" />
            <feColorMatrix in="SourceGraphic" type="matrix" values="0 0 0 0 0  0 1 0 0 0  0 0 0 0 0  0 0 0 1 0" result="g" />
            <feOffset in="SourceGraphic" dx={L.rgb} result="b0" />
            <feColorMatrix in="b0" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 1 0 0  0 0 0 1 0" result="b" />
            <feBlend in="r" in2="g" mode="screen" result="rg" />
            <feBlend in="rg" in2="b" mode="screen" />
          </filter>
        </svg>
      )}
      <div
        style={{
          ...fill,
          transform: `translate(${L.x.toFixed(1)}px, ${L.y.toFixed(1)}px) rotate(${L.rotate.toFixed(2)}deg) scale(${L.scale.toFixed(4)})`,
          transformOrigin: origin,
          filter: filters || undefined,
        }}
      >
        {children}
      </div>
      {L.leak > 0.01 && (
        <div
          style={{
            ...fill,
            mixBlendMode: "screen",
            opacity: L.leak,
            background: `radial-gradient(60% 45% at ${L.leakX * 120 - 10}% 35%, rgba(255,170,70,0.95), rgba(255,90,40,0.55) 45%, rgba(255,60,30,0) 75%), linear-gradient(100deg, rgba(255,200,120,0) ${L.leakX * 100 - 30}%, rgba(255,220,160,0.6) ${L.leakX * 100}%, rgba(255,200,120,0) ${L.leakX * 100 + 30}%)`,
          }}
        />
      )}
      {L.warm > 0.01 && (
        <div
          style={{
            ...fill,
            mixBlendMode: "screen",
            opacity: L.warm,
            background: "radial-gradient(90% 70% at 50% 42%, rgba(255,240,205,1) 0%, rgba(255,186,96,0.92) 45%, rgba(255,120,40,0.75) 100%)",
          }}
        />
      )}
      {L.flash > 0.01 && <div style={{ ...fill, background: "#fff", opacity: L.flash }} />}
      {L.dark > 0.01 && <div style={{ ...fill, background: "#000", opacity: L.dark }} />}
    </div>
  )
}

/**
 * @remotion/transitions presentation, typed loosely so this file needs no extra package.
 * The cut happens at the middle of the transition: the old scene shows the first half, the new one the second.
 */
export const cut = (kind: TransitionKind, dir = 1) => ({
  component: ({ presentationProgress: p, presentationDirection, children }: { presentationProgress: number; presentationDirection: "entering" | "exiting"; children: ReactNode }) => {
    const exiting = presentationDirection === "exiting"
    if (exiting ? p >= 0.5 : p < 0.5) return null
    return <CutFx look={lookAt(kind, p * 2 - 1, dir)}>{children}</CutFx>
  },
  props: {},
})
