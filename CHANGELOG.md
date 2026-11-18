# Changelog

## 0.5.1 (2026-11-17)

- Recipe and 3D model pickups are translated ("Receita: Pierogi"). The game builds their names from the recipe name and an English suffix.
- The character creation questions and cards are translated ("Motivo da sua mudança para Obenseuer", "Esta escolha pode ter consequências no futuro"). Before, most of them stayed in English, and "Almost every day" came out as "Almost every dia".
- On the difficulty screen, PRÓXIMO and VOLTAR no longer run into each other.
- Long titles on the character creation cards wrap onto a second line instead of shrinking ("Apreciador de cachaça de cogumelo"). Any label now uses the lines its box has room for before its text is made smaller.
- With SafeTravels or QuestHelper installed, their text is in Portuguese too: the pause menu entries ("Destravar personagem", "Guia de tarefas"), SafeTravels' messages, and the whole Quest Helper window with its quest hints.
- The vertical EXCHANGE sign in the tenement yard now reads CAMBIO. It is built from the game's 3D letters, so the plugin swaps in the game's own letter models. They have no accents, so it can't read CÂMBIO.
- 16 more textures that were still in English: both buses (TRANSPORTE COLETIVO DE STALBURG and the graffiti on the wrecked one), the O Market doors and a shop window, a doormat, the screens of the free-standing ATM and of the closed parcel locker, the soup kitchen sign, the emergency number and dentist posters, the Stalburg wall map, and the cereal, Pekka coffee and cooking oil packaging.

## 0.5.0 (2026-11-17)

First public release. The whole translation is a first draft. Every line is still marked as unreviewed in the `.po` files, and the game shows these drafts by default (the `ShowUnreviewedDrafts` setting). Reviews and corrections will come in later versions.

### What's translated

- Menus, options, key bindings and character creation.
- Every item name and description (1,244 items), all 935 recipes and 908 pieces of furniture.
- Interface labels, tooltips, prompts, notifications, loading-screen tips and the names of things you look at.
- All 48 tasks and their 270 objectives, quest items, blueprints, the 94 notes, the emails and the two books.
- All dialogue: 488 conversations, about 10,500 lines and replies. Lines addressed to your character follow its gender ("Você está cansado/cansada?"), and so do the words the game slips in about your character ("garoto", "senhor").
- Speaker names that are titles rather than names ("Guarda", "Padre"). People's names stay as they are.
- Text the game puts together from pieces: messages like "Encher um tanque com …", renovation tasks ("Prédio: escadaria (surrado)"), item names ("Pote de vidro (vazio)"), the hostel bed menu, the sleep timer, crafting details, crime notifications and the doctor's addiction diagnosis.
- 317 textures with English text: signs, notices, screens, maps, posters, menus, magazine and book covers, and packaging. Signs drawn in pixel lettering keep that style. Brand and place names stay as they are. More posters and packaging will follow.
- With the BetterTenement mod installed, its ledger window, upgrade cards and map tooltips are in Portuguese too. Without it, nothing changes.
- The same goes for other red-socket mods: the opening hours FairMarket adds to shop doors ("(Fechado, abre 8:00)", "Seg-Sex 8-18, Sáb 10-16, Dom fechado") and the storage buttons from TidyInventory, FewerClicks and BetterTenement ("Esvaziar", "Juntar", "Completar", "Guardar").

### How it works

- The plugin applies the translation in memory while the game runs. It doesn't change game files or write anything to your saves, so you can remove it at any time and the game goes back to English.
- The game matches saved tasks and notes by their English titles, so those titles are translated only on screen.
- Translated textures stay translated when you leave a place and come back. The game reloads the original textures on every visit, so the plugin checks them again after each door.
- When a Portuguese label is longer than the English one, the plugin widens it or scales the text down a little to fit.
- The game's typewriter font draws ã and õ with a smudge and puts the accents of capitals like Á on top of the letter. The plugin redraws those letters when the game starts.
- If a game font has no accented letters, the plugin uses one that does.
- Settings are in `BepInEx/config/redsocket.obenseuer.ptbr.cfg`. `Enabled`, `TranslateTextures` and `FixTypewriterAccents` turn each part off. `ShowUnreviewedDrafts` and `CollectUntranslated` are for translators.
