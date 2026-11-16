---
name: motion-graphics
description: Punto de entrada para crear vídeos de motion graphics con Remotion (animaciones, explicativos, anuncios, intros, textos cinéticos, gráficos de datos, vídeos sin persona) y para añadir motion graphics encima de un vídeo grabado. Dice qué skill y qué componente usar en cada caso. Úsala siempre que pidan "motion graphics", "animación", "vídeo animado", "explainer", "intro", "texto animado", "kinetic typography", "haz un vídeo con Remotion", o efectos encima de un vídeo, aunque no digan "skill".
---

# Motion graphics

Todo se hace en Remotion (React, 30 fps). Esta skill reparte el trabajo:

| Necesitas | Ve a |
|---|---|
| Reglas base de Remotion (animar con `useCurrentFrame`, `spring`, `interpolate`, `Sequence`, assets, fuentes, render) | `remotion-best-practices` (oficial, enlaza al resto de `remotion-*`) |
| Editar un vídeo grabado (reel con persona hablando) | Tu kit de reels de marca si tienes uno; si no, `remotion-best-practices` + `remotion-captions` y las skills de abajo |
| Transiciones (flash, zoom, whip, glitch...) | `video-transitions` |
| Texto o gráficos detrás de la persona | `person-cutout` |
| Luz y color iguales entre planos | `light-even` |
| Voz con el mismo volumen y tono entre planos | `audio-even` |
| Subtítulos | `remotion-captions` |

## Vídeo desde cero (sin grabación)

1. Proyecto: `npx create-video@latest --blank`.
2. Guion por escenas de 2 a 4 s. Cada escena, una idea. Escríbelas como componentes y encadénalas con `<TransitionSeries>` y `cut(kind)` de `video-transitions`.
3. Define antes los tokens de la marca (colores, fuentes, curvas, duraciones) en un `tokens.ts` y úsalos en todo en lugar de inventar estilos por escena.
4. Movimiento profesional: curvas ease-out y ease-in-out, entradas de 0,3 a 0,5 s, escalonadas 60 a 90 ms, nada que rebote salvo un `pop` puntual. Una cosa se mueve cada vez.
5. Revisa con stills a mitad de cada escena y un render `--scale=0.5` antes del final.

## Encima de un vídeo grabado

Detecta la cara (Apple Vision, `VNDetectFaceRectanglesRequest`) y coloca los gráficos donde no la tapan; centra los zooms en ella; mezcla a -14 LUFS. Iguala antes luz y voz entre planos (`light-even`, `audio-even`).

## Lo que se nota "hecho por IA" (evitar)

- Pastillas de texto que resumen lo que dice ("PRECIO: CLARO Y SIN SORPRESAS"). Usa gráficos visuales con una o dos palabras suyas.
- Efectos sintetizados. Usa grabaciones reales (Mixkit, ver `RESOURCES.md`).
- Transiciones en todos los cortes. Pocas y con intención.
- Emoji, amarillo CapCut, rebotes y rotaciones gratuitas.

## Referencias de terceros (vendor/, no instaladas)

Antes de diseñar un componente desde cero, busca uno parecido en `~/Documents/WebDev/ai-video-kit/vendor/` y adáptalo a los tokens de la marca: componentes (`Remocn__remocn-registry`, unos 300; `av__remotion-bits`), transiciones (`GTKottman__remotion-transitions`, 50; `gl-transitions__gl-transitions`, 267 shaders portables con `makeHtmlInCanvasPresentation`). Paquetes oficiales útiles (light-leaks, motion-blur, noise, lottie) y herramientas de IA en `RESOURCES.md`. Más, en `README.md` del repo: efectos face-cam (`Vibha-Ramprakash__claude-video-effects`, `aaksa__facecammaxxing`, `Dryxio__effects-skill`), plantillas de reels (`artemnovitckii__claude-editing-skills`), cámara cinematográfica y gráficos (`Liamrjohnston__remotion-motion-graphics-skill`, `RajaskaJanuardani__motion-craft`), shorts desde vídeo largo (`AgriciDaniel__claude-shorts`, `WhiteTowerAI__cut-as-code`), talking head con 48 componentes (`andyhuo520__digital-human-koubo`).
