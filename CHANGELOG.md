# Changelog

## 0.5.0 (unreleased)

First public release. The whole translation is a first draft. Every line is still marked as unreviewed in the `.po` files, and the game shows these drafts by default (the `ShowUnreviewedDrafts` setting). Reviews and corrections will come in later versions.

### What's translated

- Menus, options, key bindings and character creation.
- Every item name and description (1,244 items), all 935 recipes and 908 pieces of furniture.
- Interface labels, tooltips, prompts, notifications, loading-screen tips and the names of things you look at.
- All 48 tasks and their 270 objectives, quest items, blueprints, the 94 notes, the emails and the two books.
- All dialogue: 488 conversations, about 10,500 lines and replies. Lines addressed to your character follow its gender ("Você está cansado/cansada?"), and so do the words the game slips in about your character ("garoto", "senhor").
- Speaker names that are titles rather than names ("Guarda", "Padre"). People's names stay as they are.
- Text the game puts together from pieces: messages like "Encher um tanque com …", renovation tasks ("Prédio: escadaria (surrado)"), item names ("Pote de vidro (vazio)"), the hostel bed menu, the sleep timer, crafting details, crime notifications and the doctor's addiction diagnosis.
- 315 textures with English text: signs, notices, screens, maps, posters, menus, magazine and book covers, and packaging. Signs drawn in pixel lettering keep that style. Brand and place names stay as they are. More posters and packaging will follow.
- With the BetterTenement mod installed, its ledger window, upgrade cards and map tooltips are in Portuguese too. Without it, nothing changes.

### How it works

- The plugin applies the translation in memory while the game runs. It doesn't change game files or write anything to your saves, so you can remove it at any time and the game goes back to English.
- The game matches saved tasks and notes by their English titles, so those titles are translated only on screen.
- When a Portuguese label is longer than the English one, the plugin widens it or scales the text down a little to fit.
- The game's typewriter font draws ã and õ with a smudge and puts the accents of capitals like Á on top of the letter. The plugin redraws those letters when the game starts.
- If a game font has no accented letters, the plugin uses one that does.
- Settings are in `BepInEx/config/redsocket.obenseuer.ptbr.cfg`. `Enabled`, `TranslateTextures` and `FixTypewriterAccents` turn each part off. `ShowUnreviewedDrafts` and `CollectUntranslated` are for translators.
