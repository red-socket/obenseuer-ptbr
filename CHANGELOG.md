# Changelog

## 0.4.2 (unreleased)

Fixes from the first full play session:

- Gendered words in dialogue no longer show both forms ("{{Bem-vindo|Bem-vinda}}"). The plugin now resolves them before the game builds the subtitle.
- Notes and emails are translated in the Notes tab. Text you type in your own notebooks is left alone.
- About 650 more interface strings: tooltip lines ("Valor estimado", "Queima por", "Estragando"), interaction prompts ("(Colher) (Segure - Continuar colhendo)"), crafting station names, key names, trader wealth, save slot names, needs warnings ("Sede!") and the controls hint line at the bottom of the menu.
- Renovation tasks read naturally ("Prédio: escadaria (surrado)") and include the courtyard, roof and other targets.
- Item names built from pieces are translated ("Galão plástico com água limpa", "Pote de vidro (vazio)").
- The same English word can now have different translations in different places: the inventory button says "Beber" while the item type stays "Bebida", and the backpack tab says "ABRIR" while the bar sign says "ABERTO".
- Labels that flickered between two sizes (furniture shop) settle on one size, and auto-sized labels can shrink a little further instead of cutting the text off.
- Notes opened from the list are translated too. Before, the title and text of some notes (the bridge toll note, for one) stayed in English.
- The typewriter font used in menus and notes drew ã and õ with a smudge instead of a tilde, and put the accent of capitals like Á and Ô on top of the letter. Those letters are now redrawn when the game starts, from the font's own letters and accents. The `FixTypewriterAccents` setting turns this off.
- More text built by the game from pieces: the hostel bed menu ("Quarto 2, cama 6: 33 OC por noite"), the sleep timer ("Dormindo: Um dia"), the bed comfort prompt, crafting details (process time, fail chance, power), station modifiers, crime notifications ("Furto +505"), the building map tooltips, the mine cart controls and the "Segure - Comer" style prompts for every item action.
- Task descriptions with a second paragraph are translated in full. Before, the last paragraph stayed in English.
- A label that has rich text turned off no longer shows a raw `<size=...>` tag when the Portuguese is longer.
- Labels next to an icon are shrunk instead of widened, so the text no longer slides under the icon ("ancelar" on the sleep screen).
- With the BetterTenement mod installed, its Landlord Ledger window, upgrade cards and map tooltips are in Portuguese too ("Livro-caixa", "Sem efeito no aluguel", "Próximo: …"). Without BetterTenement nothing changes.
- Resident tooltips: "Estado civil" and "Profissão" are translated, and the relationship and job follow the resident's gender ("Noiva", "Professora").
- Deeply nested labels, such as a tooltip line with colour tags and a " · " separator, are translated all the way down ("Próximo: Suja").
- About 100 strings the text extractor had missed: the descriptions in the health and needs tooltips, the card game tutorials, building mode warnings ("Não dá para colocar aqui!"), the effects of the starting choices and the renovation cleanup notice ("4 itens foram embalados...").
- The doctor's addiction diagnosis is now a proper Portuguese sentence ("Você está muito viciado em álcool e nicotina."). The game builds it from English pieces, so the plugin rebuilds it from the same addiction levels.
- Eighty-eight signs, screens and maps with English text are now in Portuguese: warning and notice signs (high voltage, radioactive area, private property, the Bergmann tunnel signs, the "out of stock" notice in shops), the passport ticket machine and ATM screens, the green exit lights, the exit signs in the mall corridors, the "call the guard" plate, the hot water tank sign, the alarm signs at the Elström, Skeida, Rob-In and duty-free shops, the notes on the reception desks, the hostel bathroom signs, the security alarm label, the floor signs by the mine elevator, the metro and mine ticket machines, the number dispenser, the quarantine checkpoint notice, the mushroom extraction machine screens, the flashlight, the parcel locker screen, the military area sign, two metro station signs, a few hazard labels, the Kolhola resident board, the floodgate control panel, the Osrat chalkboard, the teletext news page on the TVs, the metro maps, the street map of the tenement area, the Stalburg Mail inbox, and the first shop signs with opening hours. Signs drawn in pixel lettering keep it. The plugin replaces each sign's texture in memory when the game loads it and leaves the game files alone. Shop fronts, posters and packaging come in later versions.

## 0.4.1 (unreleased)

- Speaker names on subtitles and phone calls are translated when they are titles rather than names ("Guarda", "Padre", "Serviço de emergência"). People's names stay as they are.
- Labels in front of a colon are translated even when the value after it isn't known ("Qualidade: OK").
- The `CollectUntranslated` log skips text that is already in Portuguese and records the scene and object each English label appeared on.

## 0.4.0 (unreleased)

- Draft translation of all dialogue: 488 conversations, about 10,500 lines and response options, using the Dialogue System's own language support. Untranslated lines stay in English.
- Lines addressed to your character, or spoken by them, follow your character's gender ("Você está cansado/cansada?").
- The words the game inserts into dialogue from your character's age and gender ("boy", "sir", "he") are now in Portuguese too.

## 0.3.0 (unreleased)

- Draft translations of every task and objective (48 tasks, 270 objectives), the quest items and blueprints, all 94 notes, the emails and the two books, and 908 furniture names and descriptions.
- Task and note titles are translated only on screen. The game matches saved tasks and notes by their English title, so those stay untouched.
- Renovation tasks that the game builds while you play ("Apt 5 makeshift kitchen") are translated, and so are objective counters and "(Optional)".
- Labels in a different letter case than the English (all caps, lower case inside a sentence) now find their translation.

## 0.2.0 (unreleased)

- Draft translations of every item name and description (1,244 items), all 935 recipe names, the interface labels in scenes and prefabs, object names and prompts you see when you look at things, loading-screen tips, and the notifications and buttons set by the game's code.
- Templates translate messages the game assembles from pieces, such as "Items added (3)!" or "Fill a Tank With Diesel".
- If a game font has no accented characters, the plugin falls back to one that does.
- All drafts are marked "needs review" in the .po files and shown in game by default (`ShowUnreviewedDrafts`).

## 0.1.0 (unreleased)

- Proof of concept: main menu, pause menu, options, key bindings and character creation labels, and 40 items in Brazilian Portuguese.
- Translations are gettext `.po` files; anything untranslated stays in English.
