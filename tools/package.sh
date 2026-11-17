#!/usr/bin/env bash
# Build the release archive releases/ObenseuerPTBR-<version>.zip from an explicit allowlist.
#   tools/package.sh
# Only git-tracked files go in (plus the freshly built DLL), laid out as BepInEx/plugins/ObenseuerPTBR/, so the
# archive extracts straight into the game folder. Refuses to run if the version in Plugin.cs and the latest
# CHANGELOG entry differ, or if the files that ship have uncommitted changes.
set -euo pipefail
cd "$(dirname "$0")/.."

version="$(sed -n 's/.*const string Version = "\([^"]*\)".*/\1/p' mod/ObenseuerPTBR/Plugin.cs)"
changelog="$(sed -n 's/^## \([0-9][^ ]*\).*/\1/p' CHANGELOG.md | head -1)"
[[ -n "$version" ]] || { echo "no Version in Plugin.cs" >&2; exit 1; }
[[ "$version" == "$changelog" ]] || { echo "Plugin.cs says $version, CHANGELOG.md says $changelog" >&2; exit 1; }

shipped=(mod/ObenseuerPTBR translations/pt-BR textures/pt-BR LICENSE CHANGELOG.md README.md)
if [[ -n "$(git status --porcelain -- "${shipped[@]}")" ]]; then
  echo "uncommitted changes in shipped files:" >&2
  git status --short -- "${shipped[@]}" >&2
  exit 1
fi

dotnet build mod/ObenseuerPTBR -c Release -p:Deploy=false -nologo -v:q
dll=mod/ObenseuerPTBR/bin/Release/net472/ObenseuerPTBR.dll
[[ -f "$dll" ]] || { echo "built DLL not found: $dll" >&2; exit 1; }

out="releases/ObenseuerPTBR-$version.zip"
mkdir -p releases
rm -f "$out"
# The allowlist: the DLL, then tracked .po and .png files and the three documents. Nothing else is read.
{
  echo "$dll	ObenseuerPTBR.dll"
  git -c core.quotePath=false ls-files -- 'translations/pt-BR/*.po' | sed 's|^\(.*\)$|\1	\1|'
  git -c core.quotePath=false ls-files -- 'textures/pt-BR/*.png' | sed 's|^\(.*\)$|\1	\1|'
  for f in LICENSE CHANGELOG.md README.md; do echo "$f	$f"; done
} | python3 -I -c '
import sys, zipfile
out = sys.argv[1]
base = "BepInEx/plugins/ObenseuerPTBR/"
n = 0
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for line in sys.stdin:
        src, dst = line.rstrip("\n").split("\t")
        z.write(src, base + dst)
        n += 1
print(f"{out}: {n} files")
' "$out"
