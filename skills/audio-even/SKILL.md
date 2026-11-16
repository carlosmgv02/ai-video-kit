---
name: audio-even
description: Deja uniforme la voz de un vídeo de móvil hecho de varios clips, en volumen y en tono. Mide el espectro de la voz en cada parte y lo iguala a una referencia común, después normaliza a -14 LUFS. Úsala siempre que el usuario diga "audio uniforme", "la voz suena distinta entre clips", "en esta parte suena más alto / más bajo / con eco / a lata", "igualar volumen", "igualar tono", "espectro", "espectrometría", "ecualizar la voz", o cuando un vídeo junte tomas de sitios distintos, aunque no nombre la skill.
---

# Voz uniforme entre clips

Rutas: relativas a la carpeta de esta skill (la "Base directory" que muestra Claude al cargarla). `../<otra-skill>/` es una skill hermana de este mismo kit.

`loudnorm` mide el archivo entero, así que no arregla que un clip suene más fuerte, más grave o más fino que otro. Este script parte el audio en segmentos, mide cada uno solo donde hay voz y corrige cada segmento hacia la mediana de todos.

```bash
python3 -I scripts/even_audio.py <entrada> <salida> [--segments auto|a-b,c-d] [--level] [--report out.png]
python3 -I scripts/even_audio.py --selftest
```

- Entrada: vídeo o audio. Con vídeo, la imagen se copia sin tocar y el audio sale en AAC 48 kHz. Con `.wav` de salida, PCM 24 bits.
- `--segments auto` (por defecto): corta en los cambios de plano (escena > 0,25) y en las pausas de 1 s o más. En un audio suelto solo hay pausas. Si sabes dónde cambia la toma, dilo: `--segments 0-8.2,8.2-16,16-23.5` (segundos).
- `--level`: además iguala frase a frase con un `dynaudnorm` lento (ventana de unos 4 s, como mucho +9,5 dB). Sube un poco la diferencia entre segmentos, úsalo solo si dentro de una toma hay frases que se pierden.
- `--report`: PNG con la forma del espectro de cada segmento antes y después. Las curvas deben quedar juntas.

## Cuándo

- Antes de cortar y montar, sobre el vídeo en bruto, cuando el vídeo sean varios clips (WhatsApp unidos, otra habitación, más cerca del móvil). Después monta a partir de la salida como si fuera el original.
- Con cualquier pista de voz suelta.
- No hace falta en una sola toma en el mismo sitio: el script lo dirá con correcciones casi nulas.

## Qué hace

1. Por segmento: LUFS solo de los tramos con voz y espectro medio en 21 bandas de tercio de octava (100 Hz a 10 kHz).
2. Referencia: mediana de los segmentos, pesada por segundos de voz. El clip más largo manda.
3. Corrección: ganancia (máx. ±10 dB) y una curva de EQ suave (máx. ±6 dB por banda, +3 dB por encima de 6 kHz para no subir el siseo), con fundido de 30 ms entre segmentos.
4. Master: ganancia lineal a -14 LUFS y limitador con sobremuestreo a -1,8 dBTP. Sin AGC, así no bombea.

## Cómo leer la tabla

- `LUFS antes/después` por segmento y la línea `LUFS spread`: diferencia entre el segmento más fuerte y el más flojo. Bien si queda por debajo de 1 dB.
- `tilt` (dB por octava) y `centr` (centroide, Hz): más negativo o más bajo es más grave o apagado; más alto, más fino o metálico. Deben acercarse entre segmentos.
- `diferencia de espectro`: distancia media de cada segmento a la mediana. Por debajo de 1 dB no se nota; de 1 a 1,5 dB es que alguno pedía más de ±6 dB.
- `EQ`: los tres movimientos mayores, p. ej. `-6.0@125` es quitar 6 dB a 125 Hz (bola de graves de una habitación).
- `true peak` debe quedar en -1,5 o por debajo.

## Relación con finish.sh

`finish.sh` mezcla voz, efectos y música y masteriza el total a -14 LUFS, pero no toca la voz por partes. Esta skill va antes: deja la voz pareja para que prep.py y finish.sh trabajen sobre una pista uniforme. prep.py vuelve a limpiar y normalizar, no pasa nada por normalizar dos veces.

## Límites

- No quita la reverberación: una sala con eco sonará algo menos a lata, pero con eco.
- Una toma que pide más de ±6 dB (un móvil que corta graves, por ejemplo) se queda a medias.
- Sin cambio de plano ni pausa, no sabe dónde cambia la toma: dale `--segments`.
- Con menos de 2 s de voz en un segmento solo se ajusta el volumen; con menos de 0,5 s, nada.
- Con dos segmentos, la referencia es el más largo, no un promedio.
