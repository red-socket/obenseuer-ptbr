#!/usr/bin/env bash
# Weather the clean flag (flag-br.svg) into textures/flag-br-worn.png with the game's own textures:
#   tarp_001          fabric creases (overlay)
#   concrete_009_dirty  grime and sun-bleached blotches (multiply / screen)
#   plasterwall_012   worn-through holes (its alpha channel), plus a feathered edge
# Raw game textures are read from the AssetRipper export and never copied into art/.
set -euo pipefail
cd "$(dirname "$0")"
T="${OBENSEUER_ASSETRIPPER:-../../../obenseuer/AssetRipper}/ExportedProject/Assets/Texture2D"
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
W=1000 H=700

rsvg-convert flag-br.svg -w $W -h $H -o "$tmp/flag.png"

# Sun-faded print: less than half the saturation, darks lifted a lot, whites dulled.
magick "$tmp/flag.png" -modulate 100,42 +level 24%,82% "$tmp/faded.png"

# Creases: the tarp tiled at 2x, centred on mid-grey so overlay only adds folds.
magick -size ${W}x${H} tile:<(magick "$T/tarp_001.png" -resize 200% -colorspace gray png:-) \
  -auto-level +level 32%,68% "$tmp/creases.png"
# Grime: concrete blotches, darks to dirt (multiply), lights to bleaching (screen).
magick -size ${W}x${H} tile:<(magick "$T/concrete_009_dirty.png" -resize 300% -colorspace gray png:-) \
  -auto-level "$tmp/grime.png"
magick "$tmp/grime.png" +level 55%,100% "$tmp/dirt.png"         # light grey, darker specks
magick "$tmp/grime.png" -negate -level 55%,100% "$tmp/bleach.png" # mostly black, light blotches

magick "$tmp/faded.png" \
  \( "$tmp/creases.png" \) -compose Overlay -composite \
  \( "$tmp/dirt.png" \) -compose Multiply -composite \
  \( "$tmp/bleach.png" -evaluate multiply .6 \) -compose Screen -composite \
  "$tmp/worn.png"

# Alpha: peeling plaster for worn-through holes, times a feathered edge.
# The plaster's own alpha marks where it has peeled; keep only the larger gaps.
magick "$T/plasterwall_012.png" -crop 512x370+0+0 +repage -alpha extract -resize ${W}x${H}! \
  -blur 0x3 -level 0%,22% "$tmp/holes.png"
magick -size ${W}x${H} xc:black -fill white -draw "rectangle 30,30 $((W-30)),$((H-30))" \
  -blur 0x22 "$tmp/edge.png"
magick "$tmp/holes.png" "$tmp/edge.png" -compose Multiply -composite "$tmp/alpha.png"

magick "$tmp/worn.png" "$tmp/alpha.png" -alpha off -compose CopyOpacity -composite \
  -strip ../textures/flag-br-worn.png
echo "wrote art/textures/flag-br-worn.png"
