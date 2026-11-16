---
name: person-cutout
description: Recorta a la persona de un vídeo (vídeo con transparencia) para poner texto, gráficos o fotos DETRÁS de ella, el efecto "texto detrás de la cabeza" de los reels. También recorta productos de fotos. Úsala siempre que pidan "texto detrás de mí / de la persona", "palabra gigante detrás", "efecto profundidad", "recortar a la persona", "quitar el fondo del vídeo", "rotoscopia", "matte", o quitar el fondo a fotos de producto, aunque no digan "skill".
---

# Recortar a la persona (texto detrás)

Rutas: relativas a la carpeta de esta skill (la "Base directory" que muestra Claude al cargarla). `../<otra-skill>/` es una skill hermana de este mismo kit.

Tres capas: vídeo original, texto encima, y la persona recortada encima del texto. El recorte es un vídeo con transparencia alineado fotograma a fotograma con el original.

## Recortar

```bash
python3 -I scripts/matte.py <in.mp4> <out.webm> [--mode person|subject] [--from S --to S]
```
- Apple Vision, solo macOS. La primera vez compila `personmask.swift` (unos segundos).
- `--mode person` (por defecto): personas, con detalle de pelo. `--mode subject`: la persona y lo que sostiene (un producto en la mano).
- Velocidad: unos 8 fotogramas por segundo en 1080x1920 (un reel de 70 s tarda unos 5 min). Si solo hace falta un tramo, `--from/--to` y luego cuadra el tiempo de inicio en Remotion.
- Bordes: por defecto `--shrink 2`. Halo claro alrededor, `--shrink 3`. Pelo comido, `--shrink 0 --grow 1`. Parpadeo del borde, `--smooth 5`.
- Salida `.webm` (VP9 con alfa, ligera) o `.mov` (ProRes 4444, exacta y pesada). Deja también `<out>_mask.mp4` para revisar.
- Avisa si la persona ocupa más del 60 % del cuadro: entonces el texto de detrás no se ve. Pide un plano más abierto o pon el texto por encima de la cabeza.

## Uso

1. `matte.py cut.mp4 person.webm` sobre el vídeo ya cortado (otra vez si cambias el corte).
2. Pon el texto entre el vídeo y el recorte (abajo). Que siga los mismos zooms y transiciones que el vídeo: mételos en el mismo contenedor.
3. Revisa con un still en el centro del tramo: la palabra tiene que leerse alrededor de la cabeza.

Criterio: una o dos palabras suyas (el tema, un número, un lugar), de 2 a 4 veces por vídeo. Nada de frases.

## En cualquier composición de Remotion

```tsx
<OffthreadVideo src={staticFile("cut.mp4")} muted />
<div style={{ position: "absolute", top: 300, fontSize: 320, fontWeight: 900 }}>AHORRO</div>
<OffthreadVideo src={staticFile("person.webm")} transparent muted />
```
`transparent` es obligatorio en el recorte (si no, sale fondo negro). Monta el recorte solo mientras haga falta: decodificar dos vídeos es más lento.

## Otras opciones (vendor/)

- RobustVideoMatting (`vendor/artemnovitckii__claude-editing-skills`, `vendor/aaksa__facecammaxxing`): más estable en el tiempo, multiplataforma, necesita PyTorch y descargar el modelo.
- MediaPipe selfie segmentation (`vendor/Vibha-Ramprakash__claude-video-effects`): rápido, bordes peores.
- BiRefNet con rembg (`vendor/Dryxio__effects-skill`): muy buen borde por foto, lento y parpadea en vídeo.
