#!/usr/bin/env bash
# Re-render every Nexus image for Obenseuer PT-BR into art/nexus/. See art/README.md.
# Wording avoids ã/õ (Erika Ormig draws that tilde badly) and keeps the DOS-font kicker ASCII.
set -euo pipefail
cd "$(dirname "$0")"
uv run render.py "Obenseuer PT-BR" "Interface e itens em português do Brasil." \
  --kicker "MOD PARA OBENSEUER" \
  --key-shot shots/janitor-sign.webp \
  --shot shots/floor-plan.webp "A planta de cada andar, com renda, valor e despejo." \
  --shot shots/skills.webp "Habilidades como Arrombamento, Bebedeira e Papelada." \
  --shot shots/janitor-sign.webp "Placas da cidade em português." \
  --shot shots/loading-tip.webp "As dicas da tela de carregamento, em português." \
  --shot shots/pause-menu.webp "O menu de pausa inteiro, em português."
