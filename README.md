# ai-video-kit

Skills para que un agente (Claude Code, Codex) edite vídeos y haga motion graphics con Remotion: de un vídeo de móvil a un reel acabado, o un vídeo animado desde cero.

## Cómo usarlo

Instala las skills (abajo) y pídeselo a Claude Code desde cualquier carpeta:

- «Pon "AHORRO" detrás de la persona en este vídeo» → `person-cutout`.
- «Añade un flash cálido en el segundo 12», «más dinámico en los cortes» → `video-transitions`.
- «Iguala la luz entre clips», «la voz suena distinta en esta parte» → `light-even`, `audio-even`.
- «Hazme un vídeo animado explicando X» → `motion-graphics`.

Si tienes un kit de reels propio con la marca de un cliente, guárdalo fuera de este repo y llama desde él a estas skills por su ruta.

## Instalar

Como plugin de Claude Code (instala las skills de `skills/`):
```
/plugin marketplace add carlosmgv02/ai-video-kit
/plugin install ai-video-kit@ai-video-kit
```
Las skills del plugin llevan el prefijo `ai-video-kit:` (por ejemplo `/ai-video-kit:video-transitions`).

Para trabajar en el kit (editas el repo y se nota al momento), enlaza las carpetas en lugar de instalar el plugin; no hagas las dos cosas a la vez:
```sh
./install.sh                    # enlaza skills/* y las skills oficiales de Remotion en ~/.claude/skills
./install.sh ~/.agents/skills   # lo mismo para Codex
scripts/sync-vendor.sh          # vuelve a descargar las skills de terceros (vendor/)
```
Requisitos: macOS (Apple Vision para caras y recortes), Node 22, ffmpeg, Python 3.11 con numpy, scipy y soundfile.

## Skills propias (`skills/`)

| Skill | Qué hace |
|---|---|
| `motion-graphics` | Entrada: qué skill y qué componente usar para cada cosa. |
| `video-transitions` | 14 transiciones estilo CapCut (flash, flash con zoom, zoom in/out, punch, whip, spin, glitch, shake, blur, fundidos, light leak) para cortes de un vídeo continuo o `TransitionSeries`. |
| `person-cutout` | Recorta a la persona en vídeo (Apple Vision) para poner texto detrás de la cabeza. Recorte de fotos de producto. |
| `light-even` | Iguala exposición y balance de blancos entre planos y quita el parpadeo de exposición. |
| `audio-even` | Iguala volumen y tono de la voz entre planos o salas (espectro por tramos, EQ y ganancia). |

## Skills de terceros (`vendor/`, no instaladas)

Copiadas tal cual con su LICENSE y un archivo SOURCE (repo, commit, fecha). Sin vídeos de demo ni modelos pesados.

| Carpeta | Para qué sirve | Licencia |
|---|---|---|
| `remotion-dev__skills` | Skills oficiales de Remotion (buenas prácticas, captions, render, 3D, mapas...). `install.sh` sí las instala. | Licencia de Remotion (gratis hasta 3 personas) |
| `Vibha-Ramprakash__claude-video-effects` | 51 efectos face-cam, capas detrás de la cabeza (MediaPipe) | MIT |
| `artemnovitckii__claude-editing-skills` | Plantillas de reels: behind the person, split screen, ranking, explainer (RobustVideoMatting) | MIT |
| `aaksa__facecammaxxing` | Efectos face-cam con Remotion + GSAP + Three.js, texto detrás (MediaPipe / RVM) | MIT |
| `Dryxio__effects-skill` | 36 efectos face-cam, recorte BiRefNet | MIT |
| `andyhuo520__digital-human-koubo` | Talking head con 48 componentes, TextBehind con Apple Vision | MIT |
| `Ashad001__remotion-transitions` | Transiciones custom (Striped Slam, Zoom Punch, Glitch Slam) | MIT |
| `RajaskaJanuardani__motion-craft` | Motion graphics nivel After Effects, cámara, transiciones | MIT |
| `Liamrjohnston__remotion-motion-graphics-skill` | Motion graphics, cámara cinematográfica, inserts | MIT |
| `zhenwusw__orca-motion-skill` | Motion graphics con formas abstractas y tokens | MIT |
| `digitalsamba__claude-code-video-toolkit` | Toolkit de vídeo: ffmpeg, moviepy, ElevenLabs, Remotion | MIT |
| `haidrrrry__claude-remotion-skill` | Motion graphics con Remotion desde un prompt | MIT |
| `AgriciDaniel__claude-shorts` | Vídeo largo a shorts con subtítulos animados | MIT |
| `WhiteTowerAI__cut-as-code` | Edición como código: cortes, captions, b-roll, color, motion graphics | MIT |
| `Remocn__remocn-registry` / `Remocn__remocn-skills` | Unos 300 componentes de Remotion para copiar: transiciones, shaders, fondos, textos, escenas | MIT |
| `av__remotion-bits` | Componentes listos: gráficos, transiciones, revelado de texto, partículas | MIT |
| `GTKottman__remotion-transitions` | 50 transiciones ordenadas por familia (corte, wipe, motion, distorsión, morph, luz) | MIT |
| `gl-transitions__gl-transitions` | 267 transiciones en shader GLSL (film burn, zoom blur, glitch...). Se portan con `makeHtmlInCanvasPresentation` de `@remotion/transitions` | MIT |
| `browser-use__video-use` | Edición por conversación con ffmpeg: reglas de corte, audio sin chasquidos, subtítulos al final, color | MIT |
| `louisedesadeleer__clipify` | Vídeo largo de conversación a clips 9:16 con seguimiento de cara | MIT |
| `jacksonwuu__awesome-remotion` | Lista de recursos de Remotion | CC0 |

Mirados y no copiados: [OpenChatCut](https://github.com/0xsline/OpenChatCut) y [OpenMontage](https://github.com/calesthio/OpenMontage) (AGPL), [opencode-skills](https://github.com/composio-community/opencode-skills) (enmascarado en Remotion), [video-edit-skill](https://github.com/yerinsabraham/video-edit-skill) y [hypr-video-skills](https://github.com/superyhee/hypr-video-skills) (sin licencia). Lista completa: [awesome-claude-video-skills](https://github.com/zhuyansen/awesome-claude-video-skills).

Herramientas, paquetes y bancos de recursos fuera del repo: [RESOURCES.md](RESOURCES.md).
