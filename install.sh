#!/bin/sh
# Links the kit's skills (and the official Remotion skills from vendor/) into ~/.claude/skills.
# Never overwrites a real folder there: it warns and skips it.
#   ./install.sh [target dir]      # default ~/.claude/skills (Codex: ~/.agents/skills)
set -eu
ROOT=$(cd "$(dirname "$0")" && pwd)
DST=${1:-$HOME/.claude/skills}
mkdir -p "$DST"
for s in "$ROOT"/skills/*/ "$ROOT"/vendor/remotion-dev__skills/remotion-*/; do
  s=${s%/}
  [ -f "$s/SKILL.md" ] || continue
  n=$(basename "$s")
  if [ -e "$DST/$n" ] && [ ! -L "$DST/$n" ]; then echo "skip $n: $DST/$n is a real folder"; continue; fi
  ln -sfn "$s" "$DST/$n"
  echo "linked $n"
done
