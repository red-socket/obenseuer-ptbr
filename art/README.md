# Nexus art

The images for the Obenseuer PT-BR mod page: header, thumbnail and five gallery frames, in `nexus/`. They follow the red-socket house style. [SOURCES.md](SOURCES.md) lists where each piece comes from.

## Re-render

```bash
art/build.sh
```

This writes everything in `nexus/` and prints each file's size. It exits non-zero if an image breaks a Nexus limit or a line of text does not fit. `build.sh` holds the wording and the list of screenshots.

If the flag changes, rebuild its texture first:

```bash
art/flag/make-flag.sh
```

You need `uv`, `rsvg-convert` (librsvg), ImageMagick 7 (`magick`) and an AssetRipper export of the game for the fonts and textures. The scripts look for it in `../obenseuer/AssetRipper`; set `OBENSEUER_ASSETRIPPER` to use another path.

## Rules for new text and screenshots

- Avoid ã and õ in image text. The game's typewriter font draws that tilde badly.
- Keep the thumbnail kicker ASCII. The DOS font turns accented letters into box-drawing characters.
- Take screenshots at 16:9 with the translation running, and add them to `shots/` and SOURCES.md.

## Uploading

| File | Nexus slot |
|---|---|
| `nexus/header.jpg` | Header image |
| `nexus/thumbnail.jpg` | Thumbnail (primary image) |
| `nexus/gallery-01.jpg` … `gallery-05.jpg` | Gallery, in order |
