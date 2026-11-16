#!/bin/sh
# Downloads the third-party video / Remotion skills into vendor/<owner>__<repo>/ (text, code and small assets only:
# demo videos, gifs and big models stay out). Each folder keeps the upstream LICENSE and a SOURCE file with the commit.
# Only permissive licences (MIT, Remotion's own). AGPL and unlicensed repos are listed in README, not copied.
#   scripts/sync-vendor.sh            # all
#   scripts/sync-vendor.sh remotion-dev/skills
set -eu
ROOT=$(cd "$(dirname "$0")/.." && pwd)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

# repo  subpath-to-copy (. = whole repo)  [folder name, when one repo gives two folders]
# cut-as-code: recipes/codrops (213 MB of third-party demos, own licences) and recipes/line-md (icons) are left out.
LIST="
remotion-dev/skills skills
Vibha-Ramprakash/claude-video-effects .
artemnovitckii/claude-editing-skills .
aaksa/facecammaxxing .
Dryxio/effects-skill .
andyhuo520/digital-human-koubo skills
Ashad001/remotion-transitions .
digitalsamba/claude-code-video-toolkit .claude/skills
haidrrrry/claude-remotion-skill remotion-motion-graphics
Liamrjohnston/remotion-motion-graphics-skill skills
RajaskaJanuardani/motion-craft .
AgriciDaniel/claude-shorts .
WhiteTowerAI/cut-as-code skills
zhenwusw/orca-motion-skill .
Remocn/remocn registry Remocn__remocn-registry
Remocn/remocn plugins/remocn/skills Remocn__remocn-skills
av/remotion-bits .
GTKottman/remotion-transitions .
gl-transitions/gl-transitions .
browser-use/video-use .
louisedesadeleer/clipify .
jacksonwuu/awesome-remotion .
"

echo "$LIST" | while read -r repo sub alias; do
  [ -z "$repo" ] && continue
  [ $# -gt 0 ] && [ "$1" != "$repo" ] && continue
  name=$(echo "$repo" | sed 's#/#__#')
  [ -d "$TMP/$name" ] || git clone -q --depth 1 "https://github.com/$repo" "$TMP/$name"
  dst="$ROOT/vendor/${alias:-$name}"
  rm -rf "$dst" && mkdir -p "$dst"
  rsync -a --prune-empty-dirs --max-size=2m \
    --exclude .git --exclude node_modules --exclude .venv --exclude 'recipes/codrops' --exclude 'recipes/line-md' \
    --exclude '*.mp4' --exclude '*.mov' --exclude '*.webm' --exclude '*.gif' --exclude '*.webp' --exclude '*.mp3' --exclude '*.wav' \
    --exclude '*.onnx' --exclude '*.tflite' --exclude '*.glb' --exclude '*.pt' --exclude '*.pth' \
    "$TMP/$name/$sub/" "$dst/"
  for f in LICENSE LICENSE.md LICENSE.txt NOTICE.md THIRD_PARTY.md package.json; do [ -f "$TMP/$name/$f" ] && [ ! -f "$dst/$f" ] && cp "$TMP/$name/$f" "$dst/"; done
  printf 'https://github.com/%s\npath: %s\ncommit: %s\nsynced: %s\n' "$repo" "$sub" "$(git -C "$TMP/$name" rev-parse HEAD)" "$(date +%F)" > "$dst/SOURCE"
  echo "$repo -> vendor/${alias:-$name} ($(du -sh "$dst" | cut -f1))"
done
