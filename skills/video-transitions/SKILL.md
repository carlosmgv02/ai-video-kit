---
name: video-transitions
description: Transiciones de vídeo estilo CapCut para Remotion: flash de luz, flash con zoom, zoom in y zoom out con desenfoque, golpe de zoom, barrido (whip), giro, glitch RGB, temblor, desenfoque, fundido a negro o blanco y luz de película. Úsala cuando pidan transiciones, "que sea más fluido", "como CapCut", "flash", "zoom en el corte", "glitch", "cortes más dinámicos", o al montar escenas con TransitionSeries, aunque no digan "skill".
---

# Transiciones

Un solo archivo sin dependencias: `assets/transitions.tsx`. El kit de reels lo enlaza en `src/brand/transitions.tsx`, así que cualquier mejora llega a todos los proyectos con `prep.py --update-brand`.

Cada transición es un "look" (posición, zoom, giro, desenfoque, brillo, separación RGB, flash blanco, negro, luz) en función de `u = (t - corte) / duración`: de -1 a 0 es el plano que se va, de 0 a 1 el que llega. Así se usa igual con un vídeo continuo con cortes de salto o con escenas separadas.

## Catálogo

| kind | Qué es | Cuándo |
|---|---|---|
| `flash` | flash blanco con un empujón leve | cambio de tema, revelación |
| `flashZoom` | zoom hacia el corte, flash, el nuevo plano llega acercado | el más "CapCut": inicio de bloque, gancho |
| `zoomIn` | zoom con desenfoque a través del corte | avanzar, "vamos a ver" |
| `zoomOut` | el plano nuevo llega desde cerca y se aleja | conclusión, plano general |
| `punch` | corte seco que llega con 12 % de zoom | cortes de salto con energía |
| `whip` / `whipUp` | barrido lateral / vertical con desenfoque | capítulos, "lo segundo" (ya automático en `chapter`) |
| `spin` | giro con zoom | humor, giro de guion, una vez por vídeo |
| `glitch` | separación RGB y temblor | error, "mentira", tecnología |
| `shake` | temblor al aterrizar | golpe, cifra fuerte, multa |
| `blur` | desenfoque y vuelta | paso de tiempo suave |
| `dipBlack` / `dipWhite` | fundido a negro / blanco | final, salto de tiempo largo |
| `lightLeak` | luz cálida de película que cruza | tono emocional, viajes |
| `warmFlash` | la imagen se quema en luz cálida (ámbar) y vuelve | flash "de calor", cambio de tema con buen rollo |

Duraciones en `HALF` (segundos a cada lado del corte, de 0,16 a 0,45).

## En el kit de reels

En `src/edit.tsx`, con el segundo del corte (mira `segments` en `src/data.json` o `transcript.txt`):
```ts
transitions: [[20.72, "flash"], [31.32, "flashZoom"], [53.95, "lightLeak"]],
```
Los `chapter` ya llevan `whip`. Ponlas en cortes reales (inicio de un segmento) para que el salto quede escondido. Un vídeo profesional lleva pocas: 3 a 6 en un reel de 60 s, cada una con intención. Los cortes de salto normales van sin efecto (el kit ya alterna el encuadre).

Sonido: añade el efecto en `sfx` del edit (`whoosh` para whip/zoom, `impact` o `boom` para flash/shake, `swish` para spin).

## En una composición con escenas

```tsx
import { TransitionSeries, linearTiming } from "@remotion/transitions"
import { cut, frames } from "./transitions"

<TransitionSeries>
  <TransitionSeries.Sequence durationInFrames={90}><SceneA /></TransitionSeries.Sequence>
  <TransitionSeries.Transition presentation={cut("flashZoom")} timing={linearTiming({ durationInFrames: frames("flashZoom", 30) })} />
  <TransitionSeries.Sequence durationInFrames={90}><SceneB /></TransitionSeries.Sequence>
</TransitionSeries>
```
El cambio de escena ocurre en la mitad de la transición. Para un vídeo continuo: `<CutFx look={cutLook(t, cuts)}>{video}</CutFx>`.

## Añadir una transición

1. Nuevo nombre en `TransitionKind`, su duración en `HALF` y un `case` en `lookAt` usando `p` (0→1 hacia el corte), `q` (1→0 después) y `e` (pico en el corte).
2. Revisa unos fotogramas alrededor del corte (`npx remotion render ... --sequence --frames=a-b --scale=0.4`) y que en `u = ±1` el look sea la identidad (sin saltos).
3. Añádela a la tabla.

Más ideas y código: `vendor/Ashad001__remotion-transitions` (Striped Slam, Glitch Slam...), `vendor/RajaskaJanuardani__motion-craft`, `vendor/zhenwusw__orca-motion-skill` y la skill oficial `vendor/remotion-dev__skills/remotion-best-practices`.
