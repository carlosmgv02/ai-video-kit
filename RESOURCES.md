# Recursos fuera del repo

Lo que no se descarga en `vendor/` porque se instala con npm o pip, o porque son bancos de recursos. Revisa la licencia de cada recurso concreto antes de usarlo en un vídeo de cliente.

## Paquetes oficiales de Remotion (npm, misma versión que `remotion`)

El kit usa 4.0.530. Para añadirlos: `npm i` en el proyecto de Remotion con la misma versión.

| Paquete | Para qué |
|---|---|
| `@remotion/transitions` | `TransitionSeries` y `makeHtmlInCanvasPresentation` (shaders WebGL entre escenas, para portar gl-transitions) |
| `@remotion/light-leaks` | Fugas de luz de película generadas, sin archivos de vídeo |
| `@remotion/motion-blur` | Desenfoque de movimiento real (`CameraMotionBlur`, `Trail`) en gráficos rápidos |
| `@remotion/noise` | Ruido Perlin para movimientos orgánicos, temblor de cámara, partículas |
| `@remotion/lottie`, `@remotion/rive` | Animaciones Lottie o Rive (iconos animados, stickers) |
| `@remotion/layout-utils` | `fitText`: texto que encaja en un ancho |
| `@remotion/shapes`, `@remotion/paths` | Formas y trazos SVG animados (dibujar una línea, morph) |
| `@remotion/three` | 3D con Three.js |
| `@remotion/captions` | Formato estándar de subtítulos y páginas tipo TikTok |

## Herramientas de IA para la calidad (pip / brew, locales)

| Herramienta | Para qué | Licencia |
|---|---|---|
| [DeepFilterNet](https://github.com/Rikorose/DeepFilterNet) | Quitar ruido de la voz mucho mejor que `afftdn` | MIT / Apache 2.0 |
| [Demucs](https://github.com/facebookresearch/demucs) | Separar voz de música o ruido de fondo | MIT |
| [WhisperX](https://github.com/m-bain/whisperX) | Tiempos por palabra más precisos que Whisper | BSD-2 |
| [RobustVideoMatting](https://github.com/PeterL1n/RobustVideoMatting) | Recorte de persona estable en el tiempo, alternativa a Apple Vision | GPL-3.0 (no copiar código al repo) |
| [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN) | Subir resolución a vídeos de WhatsApp o fotos pequeñas | BSD-3 |
| [RIFE / Practical-RIFE](https://github.com/hzwer/Practical-RIFE) | Interpolar fotogramas: cámara lenta suave, 60 fps | MIT |
| [PySceneDetect](https://github.com/Breakthrough/PySceneDetect) | Detectar cambios de plano mejor que el umbral de ffmpeg | BSD-3 |
| [auto-editor](https://github.com/WyattBlue/auto-editor) | Corte automático de silencios, para comparar con el nuestro | Unlicense |
| [Manim](https://github.com/ManimCommunity/manim) / [Motion Canvas](https://github.com/motion-canvas/motion-canvas) | Animación matemática / motion graphics por código (alternativas a Remotion) | MIT |

## Bancos de recursos

| Recurso | Qué hay | Licencia (comprobar en cada pieza) |
|---|---|---|
| [Mixkit](https://mixkit.co/free-sound-effects/) | Efectos de sonido, música, vídeo de stock | Licencia Mixkit, uso comercial gratis |
| [Pixabay](https://pixabay.com/sound-effects/) | Efectos, música, vídeo e imágenes | Licencia Pixabay |
| [Freesound](https://freesound.org) | Efectos de sonido; filtra por CC0 | CC0 / CC-BY según el sonido |
| [gl-transitions.com](https://gl-transitions.com) | Galería visual de las 267 transiciones de `vendor/gl-transitions__gl-transitions` | MIT |
| [LottieFiles](https://lottiefiles.com/free-animations) | Animaciones Lottie gratuitas | Lottie Simple License |
| [Google Fonts](https://fonts.google.com) vía `@remotion/google-fonts` | Tipografías | OFL |
| [Lucide](https://lucide.dev) | Iconos SVG | ISC |
| [Remotion resources](https://www.remotion.dev/docs/resources) | Lista oficial de plantillas y librerías | varias |
