# Obenseuer PT-BR

An unofficial Brazilian Portuguese (PT-BR) translation of [Obenseuer](https://store.steampowered.com/app/951240/Obenseuer/) by Loiste Interactive, packaged as a BepInEx 5 plugin. Releases go up on [Nexus Mods](https://www.nexusmods.com/games/obeseuer) and on the GitHub releases page.

Status: the first draft is complete and under review. It covers menus, items, recipes, furniture, interface labels, object names, notifications, tasks, notes, quest items, all dialogue and 317 textures with English text (signs, screens, maps, posters and packaging). See the [CHANGELOG](CHANGELOG.md) for details.

The plugin translates the game in memory while it runs. It doesn't change any game files or write anything to your saves, and removing it brings back the English text.

## Installing

1. Install [BepInEx 5.4.23.6](https://github.com/BepInEx/BepInEx/releases/tag/v5.4.23.6) (`BepInEx_win_x64`) into the game folder.
2. On Linux or Steam Deck (Proton), set the Steam launch option `WINEDLLOVERRIDES="winhttp=n,b" %command%`.
3. Extract the release archive into the game folder, so the plugin ends up in `BepInEx/plugins/ObenseuerPTBR/`.

## How it works

| Text | Where it comes from | How the plugin translates it |
|---|---|---|
| Menus and on-screen labels | TextMeshPro labels in scenes and prefabs, and strings set from game code | A TextMeshPro text preprocessor swaps the text at draw time. The label's own text stays English, so game code that reads labels back keeps working. |
| Item names and descriptions | `StreamingAssets/Items.json` | Translated in the in-memory item database after it loads. The few game rules that match items by English name still see the English name. |
| Recipe names | `StreamingAssets/Recipes.json` | Translated in memory, like items. |
| Tasks, notes, quest items, furniture | ScriptableObjects | Translated where they are displayed. Saved titles stay English, because the game matches saved tasks and notes by title. |
| Dialogue | Dialogue System database | Added in memory as the Dialogue System's own Portuguese fields. Lines addressed to your character use `{{masculine\|feminine}}` forms, picked from your character's gender. |
| Signs, screens, posters, packaging | Textures | Each redrawn texture in `textures/pt-BR/` replaces the game's texture of the same name in memory when the game loads it. The sources and the scripts that draw them are in `art/textures/`. |
| Other mods' windows | The mod's own code | With the BetterTenement mod installed, the English text in its windows is replaced at load time with the entries in `mods.po`. |

The translations are gettext `.po` files in `translations/pt-BR/`, one per domain. Each entry has a stable key in `msgctxt` (for example `item.17260.title`), except interface labels, which use their English text as the key. Anything missing or untranslated shows in English.

## For translators

- Edit the `.po` files with [Poedit](https://poedit.net/), Weblate or any text editor.
- Or review in a spreadsheet: `python3 -I tools/review_csv.py export` writes every entry to `review/pt-BR.csv` (columns: file, key, english, portuguese, reviewed, note, context). Edit the Portuguese, put an `x` in `reviewed` to approve a line, then `python3 -I tools/review_csv.py import` and `python3 -I tools/check.py`.
- `tools/extract.py` regenerates the English templates (`.pot`) from a local [AssetRipper](https://github.com/AssetRipper/AssetRipper) export of the game. After a game update, merge them into the translations with `msgmerge`: it marks changed lines fuzzy and adds new lines untranslated.
- Turn on `CollectUntranslated` in `BepInEx/config/redsocket.obenseuer.ptbr.cfg` to log every on-screen English label that has no translation to `untranslated.po`.

## Building

You need the .NET SDK (any version that can target `net472`) and an installed copy of the game, because the project references the game's own assemblies.

```bash
cd mod/ObenseuerPTBR
dotnet build -c Release -p:Deploy=true   # also copies the plugin and translations into the game
```

The build looks for the game in the default Steam library under `~/.local/share/Steam`. Point it elsewhere with `-p:GameDir=/path/to/Obenseuer`.

`tools/package.sh` builds the release archive, `releases/ObenseuerPTBR-<version>.zip`. It contains only the plugin, the translations, the textures, the license and the changelog, laid out as `BepInEx/plugins/ObenseuerPTBR/` so you can extract it straight into the game folder.

## License

Code: [GPL-3.0](LICENSE). Obenseuer and its assets belong to Loiste Interactive. This project is not affiliated with or endorsed by them.
