---
name: light-even
description: Deja la luz y el color uniformes en un vídeo de móvil hecho de varios clips o planos. Iguala la exposición y el balance de blancos de cada plano a uno de referencia y aplana el parpadeo de exposición (el móvil que sube y baja la luz solo). Úsala siempre que el usuario diga "luz uniforme", "igualar color", "igualar exposición entre clips", "un plano más oscuro que otro", "este clip sale más amarillo / más azul", "parpadeo de exposición", "la luz bombea", o cuando un vídeo junte tomas de sitios o momentos distintos, aunque no nombre la skill.
---

# Luz uniforme entre planos

Rutas: relativas a la carpeta de esta skill (la "Base directory" que muestra Claude al cargarla). `../<otra-skill>/` es una skill hermana de este mismo kit.

Un script, una pasada de ffmpeg. Mide cada plano, elige una referencia y corrige el resto hacia ella.

```bash
python3 -I scripts/even_light.py <in.mp4> <out.mp4> [--ref auto|<segundos>] [--report out.png]
python3 -I scripts/even_light.py --selftest
```

- `--ref auto` (por defecto): el plano de brillo mediano. Con `--ref 3.5` manda el plano que contiene el segundo 3,5. Elige el plano que mejor se ve; si el mediano queda oscuro, todos bajarán a él.
- `--report`: PNG con un fotograma por plano, arriba antes y abajo después.
- El audio se copia tal cual. Resolución y metadatos de color se mantienen. x264 crf 16.

## Cuándo

- Antes de cortar y montar, sobre el vídeo en bruto. Después monta a partir de la salida como si fuera el original; el grade de marca va encima.
- Si también hace falta `audio-even`, encadénalos: el orden da igual, cada uno copia la otra pista.
- Vídeo de iPhone en HDR: conviértelo antes con `avconvert -p PresetHEVCHighestQualitySDR` (o `ffmpeg` con tonemap). El script lo rechaza.

## Qué hace

1. Planos: cambios de escena de ffmpeg por encima de 0,2 (prep.py usa 0,42 y se salta uniones reales, que puntúan 0,23 a 0,34). Cortes a menos de 1 s se juntan.
2. Mide a 2 fps, en miniatura: mediana de luma de los medios tonos (ignora sombras negras y paredes blancas quemadas) y R/G/B de los píxeles casi grises (paredes, techo, ropa gris), que dan el color de la luz y no el de los muebles.
3. Corrige cada plano con una curva por canal (ganancia de blancos y gamma), limitada a gamma 0,75 a 1,35 y ganancias de 0,88 a 1,12 para que nunca se vea roto.
4. Parpadeo: lleva cada fotograma a la media de 1 s centrada en él, dentro de su plano y como mucho un 4 % de luz. Con el `deflicker` de ffmpeg los planos con cámara en movimiento salían peor, por eso no se usa.
5. Vuelve a medir la salida con los mismos píxeles y saca la tabla.

## Cómo comprobarlo

- `luma spread between shots`: diferencia entre el plano más claro y el más oscuro. Bien por debajo de 0,02.
- `R/G spread` y `B/G spread`: lo mismo para el color. Bien por debajo de 0,03. Si un plano no llega, es que pedía más de lo que permiten los límites.
- `pump`: variación de luz dentro del plano. Debe bajar o quedarse igual, nunca subir.
- Lee el PNG del report: los planos de abajo deben parecerse entre sí más que los de arriba, sin cielos ni paredes quemadas y sin tinte. Si algo no convence, prueba otro `--ref`.

## Límites

- Mide el color con lo que hay de gris en el plano. Un plano sin nada neutro (todo madera o todo azul) usa la media de los medios tonos y puede corregir de más hacia el color contrario; los límites lo frenan.
- El parpadeo y un cambio real de luz dentro del mismo plano (pasar de una habitación a otra sin corte) se tratan igual: el cambio no desaparece, se suaviza en 1 s.
- Si la cámara se mueve de una habitación a otra sin corte, es un solo plano con una sola corrección.
- Supone frame rate constante (los móviles y WhatsApp lo dan).
