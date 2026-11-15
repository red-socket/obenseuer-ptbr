# Art sources

Where every piece of the Nexus art comes from. Game paths are relative to the AssetRipper export of Obenseuer 0.5.19 (`../obenseuer/AssetRipper/` on the author's machine). That export is never committed or shipped. The scripts read raw game files at render time and never copy them into `art/`.

The layout, palette, fonts and textures follow the red-socket house style v1 (`art/` in [red-socket/obenseuer-mods](https://github.com/red-socket/obenseuer-mods)). The templates, textures and `render.py` here are copies of that kit, with the changes listed below.

## Outputs (`nexus/`)

| File | Size | Made from |
|---|---|---|
| `header.jpg` | 1300×372, ≤ 400 KB | `templates/header.svg` over `shots/janitor-sign.webp`, with `textures/concrete.png`, `textures/tenement-elevation.png`, `textures/dust.png`, the red-socket logo and the two game fonts |
| `thumbnail.jpg` | 1920×1080 | `templates/thumbnail.svg` over `shots/janitor-sign.webp`, with `textures/flag-br-worn.png` and the same textures, logo and fonts |
| `gallery-01.jpg` … `gallery-05.jpg` | 1920×1080 | `templates/gallery.svg` around `shots/floor-plan.webp`, `skills.webp`, `janitor-sign.webp`, `loading-tip.webp`, `pause-menu.webp` |

## Screenshots (`shots/`)

The author took these in game with the translation running (game 0.5.19, 2026-11-14), at 2560×1440. They are stored as WebP at quality 94.

| File | Shows |
|---|---|
| `floor-plan.webp` | Building panel, floor view: apartments, "Renda", "Despejar o morador" |
| `skills.webp` | Character panel, skill list |
| `blueprint-overview.webp` | Building panel, blueprint overview (not used in the current set) |
| `janitor-sign.webp` | Street sign "SERVIÇOS DE ZELADORIA" |
| `loading-tip.webp` | Loading screen tip and "CARREGANDO" |
| `pause-menu.webp` | Pause menu |
| `main-menu.webp` | Main menu (not used: it shows the OBENSEUER logo, which house style keeps off our images) |

## Worn Brazilian flag (`flag/`, `textures/flag-br-worn.png`)

The game has no Brazilian flag. Its own flags (`Texture2D/flag_001_*.png`) are clean 128 px atlas textures, so this one is drawn from scratch and weathered with game textures.

| Step | Source | What was done |
|---|---|---|
| Shape | `flag/flag-br.svg` | Drawn from the official geometry (Lei 5.700/1971, 20×14 modules), without the stars and motto |
| Fading | none | Saturation 42 %, levels squeezed to 24 to 82 % |
| Creases | `ExportedProject/Assets/Texture2D/tarp_001.png` | Greyscale, 2× tile, overlay |
| Grime and bleaching | `ExportedProject/Assets/Texture2D/concrete_009_dirty.png` | Greyscale, 3× tile; darks multiplied in, lights screened in at 60 % |
| Worn-through holes | `ExportedProject/Assets/Texture2D/plasterwall_012.png` (alpha channel, top 370 px) | Blurred and levelled into the flag's alpha, times a feathered edge |

`flag/make-flag.sh` runs these steps. The flag's green, yellow and blue are outside the house palette on purpose. It appears on the thumbnail only.

## Copied from the house-style kit

| File here | Kit file | Changes |
|---|---|---|
| `textures/concrete.png`, `tenement-elevation.png`, `dust.png` | same names | none (they derive from `concrete_002.png`, `blueprint_front.png`, `LoadingScreenBg_effect.png`; see the kit's SOURCES.md) |
| `brand/red-socket-logo.svg` | `brand/red-socket-logo.svg` | none |
| `templates/header.svg` | `templates/header.svg` | Resized from 1400×400 to 1300×372 (the size Nexus stores); safe area x 280 to 1020, y 0 to 220 |
| `templates/thumbnail.svg` | `templates/thumbnail.svg` | Title on two lines, kicker filled from `--kicker`, worn flag on the right |
| `templates/gallery.svg` | `templates/gallery.svg` | none apart from the default screenshot path |
| `render.py` | `render.py` | Fonts read from `../obenseuer/AssetRipper` (or `$OBENSEUER_ASSETRIPPER`), WebP screenshots, `--kicker`, output to `art/nexus/` |

## Fonts (read at render time)

| Font | Game file | Use |
|---|---|---|
| Erika Ormig | `ExportedAssets/Assets/Font/Erika Ormig.ttf` | Title, tagline, captions, wordmark |
| Perfect DOS VGA 437 | `ExportedAssets/Assets/Font/PerfectDOSVGA437.ttf` | Thumbnail kicker |

Both fonts have problems with Portuguese text. The wording works around them:

- Erika Ormig draws the tilde on ã, õ, Ã and Õ as a vertical squiggle that collides with the letter (the game shows the same thing in "Visão" and "Opções"). The image text has no ã or õ. ç, é, ê and á render cleanly.
- Perfect DOS VGA 437 maps U+0080 to U+00FF to code page 437 glyphs by byte value, so "Ç" comes out as "╟". Text in this font stays ASCII.
