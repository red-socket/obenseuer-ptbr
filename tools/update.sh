#!/usr/bin/env bash
# Merge freshly extracted English templates (source/pot/*.pot) into the translations.
# Changed English lines become fuzzy (old translation kept for reference), new lines are added
# untranslated, removed lines become obsolete (#~). Prints per-domain statistics.
#   tools/update.sh [lang]     (default pt-BR; run tools/extract.py first)
set -euo pipefail
lang="${1:-pt-BR}"
cd "$(dirname "$0")/.."
mkdir -p "translations/$lang"
for pot in source/pot/*.pot; do
  domain="$(basename "$pot" .pot)"
  po="translations/$lang/$domain.po"
  if [[ -f "$po" ]]; then
    msgmerge --quiet --update --backup=none --previous "$po" "$pot"
  else
    msginit --no-translator --no-wrap --locale="${lang/-/_}" --input="$pot" --output-file="$po" >/dev/null
  fi
  printf '%-12s ' "$domain"; msgfmt --statistics -o /dev/null "$po" 2>&1
done
