"""Per-texture redraw specs for render.py.

Each entry is keyed by the game texture name (the replacement must keep that name and size):
  erase: rectangles [x0, y0, x1, y1] whose old letters are inpainted ("bg" = background colour,
         "thresh" = how far from it a pixel must be to count as a letter), or flat-filled ("color").
  en / note: the English on the texture and any doubt for the reviewer (review sheet only).
  alpha: {"erase": [...], "letters": gloss value} also redraws the letters in the alpha (gloss) channel.
  text:  lines drawn after erasing. box = area the text is fitted into (centred), "\n" separates lines,
         font = key in FONTS, size = cap in px, squeeze/vsqueeze = horizontal/vertical scale,
         stretch = fill the box exactly, rotate = degrees counter-clockwise.
Coordinates are pixels from the top-left of the game texture.
"""
import os

_G = os.path.expanduser("~/.local/share/fonts/google")
FONTS = {
    "sans": "/usr/share/fonts/liberation/LiberationSans-Regular.ttf",
    "sans-bold": "/usr/share/fonts/liberation/LiberationSans-Bold.ttf",
    "dejavu-cond-bold": "/usr/share/fonts/TTF/DejaVuSansCondensed-Bold.ttf",
    "noto-black": "/usr/share/fonts/noto/NotoSans-Black.ttf",
    "roboto-cond-bold": f"{_G}/robotocondensed/RobotoCondensed-Bold.ttf",
    "roboto-cond": f"{_G}/robotocondensed/RobotoCondensed-Medium.ttf",
    "barlow-cond-bold": f"{_G}/barlowcondensed/BarlowCondensed-Bold.ttf",
    "barlow-cond-semibold": f"{_G}/barlowcondensed/BarlowCondensed-SemiBold.ttf",
    "oswald-bold": f"{_G}/oswald/Oswald-Bold.ttf",
    "anton": f"{_G}/anton/Anton-Regular.ttf",
    "hand": f"{_G}/patrickhand/PatrickHand-Regular.ttf",
    "reenie": f"{_G}/reeniebeanie/ReenieBeanie.ttf",
    "gochi": f"{_G}/gochihand/GochiHand-Regular.ttf",
    "gloria": f"{_G}/gloriahallelujah/GloriaHallelujah.ttf",
    "caveat": f"{_G}/caveat/Caveat[wght].ttf",
    "typewriter": f"{_G}/specialelite/SpecialElite-Regular.ttf",
    "narrow": "/usr/share/fonts/gsfonts/NimbusSansNarrow-Regular.otf",
    "serif": "/usr/share/fonts/liberation/LiberationSerif-Regular.ttf",
    "kalam": f"{_G}/kalam/Kalam-Bold.ttf",
    "lato-black": f"{_G}/lato/Lato-Black.ttf",
    "covered": f"{_G}/coveredbyyourgrace/CoveredByYourGrace.ttf",
    "indie": f"{_G}/indieflower/IndieFlower-Regular.ttf",
    "marker": f"{_G}/permanentmarker/PermanentMarker-Regular.ttf",
    "label": "/usr/share/fonts/TTF/DejaVuSans.ttf",
}

SPECS = {
    # Bazaar shop shelf: "Due to high demand, this item is temporarily out of stock. We apologize for any inconvenience."
    "sign_004_out_of_stock": {
        "en": 'Due to high demand, this item is temporarily out of stock. We apologize for any inconvenience.',
        "note": 'Set in the sign\'s own pixel font (letters copied from the texture; q, á and à drawn to match).',
        "erase": [{"rect": [4, 4, 124, 124], "color": "#e2e3e2"}],
        "text": [{"pixel": "oos", "box": [4, 0, 124, 0], "baselines": [21, 40, 58, 77, 95, 114], "space": 4, "color": "#000000",
                  "text": "Devido à alta\nprocura, este item\nestá esgotado\npor enquanto.\nDesculpe o\ntranstorno."}],
    },
    # Bazaar gate: "NOTICE / Only personnel with a valid passport"
    "sign_004_trespass_bazaar": {
        "en": 'NOTICE / Only personnel with a valid passport',
        "note": 'Literal would be "Somente pessoal com passaporte válido"; I went with the more natural "Entrada só com passaporte válido".',
        "erase": [{"rect": [4, 4, 77, 17], "mode": "dark", "thresh": 20, "k": 7},
                  {"rect": [2, 19, 79, 58], "mode": "dark", "thresh": 25, "k": 7}],
        "text": [{"box": [8, 5, 72, 16], "font": "sans-bold", "color": "#262222", "text": "AVISO"},
                 {"box": [3, 21, 77, 56], "font": "sans-bold", "color": "#2a2a2a", "leading": 0.25, "stroke": 0.2,
                  "text": "Entrada só com\npassaporte\nválido"}],
    },
    # "I'm under repair / Sorry for the inconvenience"
    "sign_004_repaired": {
        "en": "I'm under repair / Sorry for the inconvenience",
        "erase": [{"rect": [3, 2, 78, 29], "mode": "dark", "thresh": 25, "k": 7},
                  {"rect": [3, 32, 78, 58], "mode": "dark", "thresh": 25, "k": 7}],
        "text": [{"box": [10, 4, 70, 28], "font": "sans-bold", "color": "#2a2a2a", "leading": 0.2, "text": "Estou em\nconserto"},
                 {"box": [5, 34, 75, 57], "font": "sans-bold", "color": "#1c1c1c", "leading": 0.2, "text": "Desculpe o\ntranstorno"}],
    },
    # Vertical "PRIVATE PROPERTY" next to a no-entry pictogram
    "sign_004_trespass_0": {
        "en": 'PRIVATE PROPERTY',
        "note": 'Vertical text; PROPRIEDADE is longer than PROPERTY, so its letters are narrower.',
        "erase": [{"rect": [1, 1, 25, 59], "bg": "#b8b8b8", "thresh": 70}],   # circle starts at x 26
        "text": [{"box": [15, 3, 25, 57], "font": "sans-bold", "color": "#141414", "rotate": 270, "stretch": True, "text": "PROPRIEDADE"},
                 {"box": [3, 3, 13, 57], "font": "sans-bold", "color": "#141414", "rotate": 270, "stretch": True, "text": "PRIVADA"}],
    },
    # Red band under a camera pictogram: "VIDEO SURVEILLANCE"
    "sign_004_camera": {
        "en": 'VIDEO SURVEILLANCE',
        "note": 'Alternative: the classic Brazilian "SORRIA, VOCÊ ESTÁ SENDO FILMADO", but the letters would have to be much smaller.',
        "erase": [{"rect": [5, 54, 124, 90], "mode": "light", "thresh": 20, "k": 7}],
        "text": [{"box": [34, 56, 94, 69], "font": "sans-bold", "color": "#b9a7a7", "text": "ÁREA"},
                 {"box": [9, 72, 119, 86], "font": "sans-bold", "color": "#b9a7a7", "text": "MONITORADA"}],
    },
    # Tiny border-post plate: "BORDER / NO TRESPASSING". "FRONTEIRA" doesn't fit in 43 px; "DIVISA" has
    # the same six letters as BORDER.
    "sign_004_border": {
        "en": 'BORDER / NO TRESPASSING',
        "note": '"FRONTEIRA" (9 letters) doesn\'t fit 43 px in this lettering, so "DIVISA" (6, like BORDER). Each line uses the original\'s pixel lettering, redrawn letter by letter.',
        "erase": [{"rect": [2, 2, 41, 12], "mode": "light", "thresh": 20, "k": 5, "isolate": True},
                  {"rect": [12, 14, 32, 23], "mode": "dark", "thresh": 25, "k": 5, "isolate": True},
                  {"rect": [2, 23, 41, 30], "mode": "dark", "thresh": 25, "k": 5}],
        "alpha": {"erase": [{"rect": [2, 2, 41, 12], "mode": "light", "thresh": 40, "k": 5, "isolate": True},
                            {"rect": [12, 14, 32, 23], "mode": "dark", "thresh": 40, "k": 5, "isolate": True},
                            {"rect": [2, 23, 41, 30], "mode": "dark", "thresh": 40, "k": 5}], "letters": 0},
        "text": [{"pixel": "border-top", "box": [1, 0, 42, 0], "baselines": [11], "gap": 2, "color": "#a5a49f",
                  "shade": [-28, 22], "mottle": 16, "alpha": 200, "text": "DIVISA"},
                 {"pixel": "border-mid", "box": [1, 0, 42, 0], "baselines": [22], "color": "#1f1f1e", "mottle": 4,
                  "text": "NÃO"},
                 {"pixel": "border-low", "box": [1, 0, 42, 0], "baselines": [28], "color": "#1c1c1b", "mottle": 4,
                  "text": "ULTRAPASSE"}],
    },
    # Bergmann tunnels (place name, kept): "MAINTENANCE TUNNEL". The gloss map holds an unrelated
    # "DANGER / KEEP OUT" from the base sign; it only changes shininess and is left alone.
    "sign_004_bergmann": {
        "en": 'BERGMANN / MAINTENANCE TUNNEL',
        "note": 'Bergmann is kept (place name, "Túneis Bergmann" in the item texts). Set in the sign\'s own worn pixel capitals; D, O, G and the accents drawn to match.',
        "erase": [{"rect": [3, 19, 61, 43], "mode": "dark", "thresh": 25, "k": 5, "isolate": True}],
        "text": [{"pixel": "bergmann", "box": [2, 0, 62, 0], "baselines": [29, 40], "color": "#1e1e1c", "fade": 0.2,
                  "text": "TÚNEL DE\nMANUTENÇÃO"}],
    },
    # "WATER TUNNEL"
    "sign_004_bergmann_2": {
        "en": 'BERGMANN / WATER TUNNEL',
        "erase": [{"rect": [3, 19, 60, 43], "mode": "dark", "thresh": 25, "k": 5}],
        "text": [{"pixel": "bergmann", "box": [2, 0, 62, 0], "baselines": [29, 40], "color": "#1e1e1c", "fade": 0.2,
                  "text": "TÚNEL\nDE ÁGUA"}],
    },
    # Yellow hazard plate: "DANGER! / CONTAMINATED / AREA"
    "sign_004_bio2": {
        "en": 'DANGER! / CONTAMINATED / AREA',
        "note": 'Portuguese word order swaps the long and short lines (ÁREA / CONTAMINADA).',
        "erase": [{"rect": [4, 3, 76, 55], "mode": "dark", "thresh": 25, "k": 11, "isolate": True}],
        "text": [{"box": [7, 4, 73, 20], "font": "oswald-bold", "color": "#0c0a04", "stretch": True, "text": "PERIGO!"},
                 {"box": [24, 23, 56, 38], "font": "oswald-bold", "color": "#0c0a04", "stretch": True, "text": "ÁREA"},
                 {"box": [6, 40, 74, 54], "font": "oswald-bold", "color": "#0c0a04", "stretch": True, "text": "CONTAMINADA"}],
    },
    # Orange site hoarding: "UNDER CONSTRUCTION"
    "sign_004_construction": {
        "en": 'UNDER CONSTRUCTION',
        "note": 'Alternative: "EM OBRAS".',
        "erase": [{"rect": [2, 20, 126, 73], "mode": "dark", "thresh": 30, "k": 13}],
        "alpha": {"erase": [{"rect": [2, 20, 126, 73], "mode": "dark", "thresh": 40, "k": 13}], "letters": 0},
        "text": [{"box": [48, 23, 80, 47], "font": "anton", "color": "#161616", "stretch": True, "text": "EM"},
                 {"box": [4, 50, 124, 72], "font": "anton", "color": "#161616", "stretch": True, "text": "CONSTRUÇÃO"}],
    },
    # Enamel plate: "WARNING / HIGH VOLTAGE" (lightning bolt kept)
    "sign_009": {
        "en": 'WARNING / HIGH VOLTAGE',
        "note": 'WARNING is "CUIDADO" on all the enamel plates, as on Brazilian safety signs.',
        "erase": [{"rect": [24, 11, 106, 29], "mode": "light", "thresh": 20, "k": 7},
                  {"rect": [17, 33, 88, 67], "mode": "dark", "thresh": 25, "k": 7}],
        "alpha": {"erase": [{"rect": [17, 33, 88, 67], "mode": "dark", "thresh": 40, "k": 7}], "letters": 0},
        "text": [{"box": [26, 13, 104, 28], "font": "sans", "color": "#a0a19f", "text": "CUIDADO", "alpha": 0},
                 {"box": [20, 34, 86, 49], "font": "sans", "color": "#1e1f1e", "text": "ALTA", "size": 15},
                 {"box": [18, 51, 88, 66], "font": "sans", "color": "#1e1f1e", "text": "TENSÃO", "size": 15}],
    },
    # "DANGER / RADIOACTIVE AREA" under a trefoil
    "sign_009_radioactive": {
        "en": 'DANGER / RADIOACTIVE AREA',
        "erase": [{"rect": [12, 45, 117, 68], "mode": "dark", "thresh": 25, "k": 9}],
        "alpha": {"erase": [{"rect": [12, 45, 117, 68], "mode": "dark", "thresh": 40, "k": 9}], "letters": 0},
        "text": [{"box": [30, 46, 98, 58], "font": "sans-bold", "color": "#392808", "stretch": True, "text": "PERIGO"},
                 {"box": [13, 59, 116, 66], "font": "sans-bold", "color": "#392808", "stretch": True, "text": "ÁREA RADIOATIVA"}],
    },
    # "WARNING / AUTHORIZED PERSONNEL ONLY"
    "sign_009_authorized_only": {
        "en": 'WARNING / AUTHORIZED PERSONNEL ONLY',
        "erase": [{"rect": [24, 11, 106, 29], "mode": "light", "thresh": 20, "k": 7},
                  {"rect": [24, 33, 102, 75], "mode": "dark", "thresh": 25, "k": 7}],
        "alpha": {"erase": [{"rect": [24, 11, 106, 29], "mode": "light", "thresh": 40, "k": 7},
                            {"rect": [24, 33, 102, 75], "mode": "dark", "thresh": 40, "k": 7}], "letters": 0},
        "text": [{"box": [26, 13, 104, 28], "font": "sans", "color": "#9a9a98", "text": "CUIDADO", "alpha": 192},
                 {"box": [25, 35, 101, 73], "font": "sans", "color": "#141414", "leading": 0.3, "stroke": 0.25, "text": "SOMENTE\nPESSOAL\nAUTORIZADO"}],
    },
    # Small no-entry plate: "PRIVATE PROPERTY"
    "Sign Private Property_0": {
        "en": 'PRIVATE PROPERTY',
        "note": 'Texture of the placeable "Private property" sign.',
        "erase": [{"rect": [9, 44, 55, 63], "bg": "#bababa", "thresh": 45, "isolate": True}],   # circle ends at row 42
        "text": [{"box": [10, 44, 53, 52], "font": "sans", "color": "#262626", "stretch": True, "stroke": 0.15, "text": "PROPRIEDADE"},
                 {"box": [14, 53, 49, 61], "font": "sans", "color": "#262626", "stretch": True, "stroke": 0.15, "text": "PRIVADA"}],
    },
    # Road sign: "POLICE / CHECKPOINT"
    "sign_police_checkpoint": {
        "en": 'POLICE / CHECKPOINT',
        "note": '"Barreira policial" is the usual term. Alternative: "BLITZ".',
        "erase": [{"rect": [13, 14, 53, 29], "mode": "dark", "thresh": 25, "k": 7, "grain": 5},
                  {"rect": [10, 35, 56, 48], "mode": "dark", "thresh": 25, "k": 7, "grain": 5}],
        "text": [{"box": [14, 15, 51, 28], "font": "sans-bold", "color": "#1a120a", "stretch": True, "stroke": 0.2, "text": "POLÍCIA"},
                 {"box": [14, 39, 51, 44], "font": "sans-bold", "color": "#1a120a", "stretch": True, "text": "BARREIRA"}],
    },
    # Hand-written cardboard: "Bricks are not welcome here"
    "sign_004_no_bricks": {
        "en": 'Bricks are not welcome here',
        "note": 'Hand-written, in Gochi Hand with worn, uneven ink.',
        "erase": [{"rect": [18, 6, 112, 90], "mode": "dark", "thresh": 20, "k": 9}],
        "text": [{"box": [22, 8, 108, 88], "font": "gochi", "color": "#1e1e1e", "leading": 0.05,
                  "wear": 0.75, "mottle": 10, "text": "Tijolos\nnão são\nbem-vindos\naqui"}],
    },

    # ---- Batch 02: screens, exit signs, notices ----
    # Ticket machine (passport check) screens: bold sans ~7 px caps on a lighter panel (x 18-107, rows 88-118).
    # The original lettering is narrower than Liberation Sans Bold, hence the squeeze.
    "ticket_machine_002_screen_default_1": {
        "en": 'PUT THE PASSPORT INTO THE SLOT (arrows point at the slot)',
        "note": '"INSIRA O PASSAPORTE NA ABERTURA" doesn\'t fit two lines at this size, so it drops "into the slot"; the arrows still point at it.',
        "erase": [{"rect": [17, 89, 110, 118], "thresh": 60, "isolate": True, "grain": 3}],
        "text": [{"box": [18, 89, 107, 103], "font": "sans-bold", "size": 10, "squeeze": 0.87, "baseline": 102,
                  "color": "#2d3f48", "text": "INSIRA O"},
                 {"box": [18, 103, 107, 118], "font": "sans-bold", "size": 10, "squeeze": 0.87, "baseline": 112,
                  "color": "#2d3f48", "text": "PASSAPORTE"}],
    },
    "ticket_machine_002_screen_default_2": {
        "en": 'PUT THE PASSPORT INTO THE SLOT (arrows point at the slot)',
        "note": 'Second animation frame of the screen before (arrows moved).',
        "erase": [{"rect": [17, 89, 110, 118], "thresh": 60, "isolate": True, "grain": 3}],
        "text": [{"box": [18, 89, 107, 103], "font": "sans-bold", "size": 10, "squeeze": 0.87, "baseline": 102,
                  "color": "#2d3f48", "text": "INSIRA O"},
                 {"box": [18, 103, 107, 118], "font": "sans-bold", "size": 10, "squeeze": 0.87, "baseline": 112,
                  "color": "#2d3f48", "text": "PASSAPORTE"}],
    },
    "ticket_machine_002_screen_valid": {
        "en": 'PASSPORT IS VALID!',
        "erase": [{"rect": [17, 89, 110, 118], "thresh": 60, "isolate": True, "grain": 3}],
        "text": [{"box": [18, 89, 107, 103], "font": "sans-bold", "size": 10, "squeeze": 0.87, "baseline": 102,
                  "color": "#314e4a", "text": "PASSAPORTE"},
                 {"box": [18, 103, 107, 118], "font": "sans-bold", "size": 10, "squeeze": 0.87, "baseline": 112,
                  "color": "#314e4a", "text": "VÁLIDO!"}],
    },
    "ticket_machine_002_screen_not_valid_1": {
        "en": 'PASSPORT IS NOT VALID!',
        "erase": [{"rect": [17, 89, 110, 118], "thresh": 60, "isolate": True, "grain": 3}],
        "text": [{"box": [18, 89, 107, 103], "font": "sans-bold", "size": 10, "squeeze": 0.87, "baseline": 102,
                  "color": "#2e3f47", "text": "PASSAPORTE"},
                 {"box": [18, 103, 107, 118], "font": "sans-bold", "size": 10, "squeeze": 0.87, "baseline": 112,
                  "color": "#2e3f47", "text": "INVÁLIDO!"}],
    },
    "ticket_machine_002_screen_wait_1": {
        "en": 'PLEASE WAIT',
        "note": 'The four frames animate the dots; the word stays put (left-aligned) like the original.',
        "erase": [{"rect": [17, 89, 110, 118], "thresh": 60, "isolate": True, "grain": 3}],
        "text": [{"box": [37, 95, 107, 110], "font": "sans-bold", "size": 10, "squeeze": 0.87, "baseline": 107,
                  "align": "left", "color": "#2d3f48", "text": "AGUARDE"}],
    },
    "ticket_machine_002_screen_wait_2": {
        "en": 'PLEASE WAIT.',
        "erase": [{"rect": [17, 89, 110, 118], "thresh": 60, "isolate": True, "grain": 3}],
        "text": [{"box": [37, 95, 107, 110], "font": "sans-bold", "size": 10, "squeeze": 0.87, "baseline": 107,
                  "align": "left", "color": "#2d3f48", "text": "AGUARDE."}],
    },
    "ticket_machine_002_screen_wait_3": {
        "en": 'PLEASE WAIT..',
        "erase": [{"rect": [17, 89, 110, 118], "thresh": 60, "isolate": True, "grain": 3}],
        "text": [{"box": [37, 95, 107, 110], "font": "sans-bold", "size": 10, "squeeze": 0.87, "baseline": 107,
                  "align": "left", "color": "#2d3f48", "text": "AGUARDE.."}],
    },
    "ticket_machine_002_screen_wait_4": {
        "en": 'PLEASE WAIT...',
        "erase": [{"rect": [17, 89, 110, 118], "thresh": 60, "isolate": True, "grain": 3}],
        "text": [{"box": [37, 95, 107, 110], "font": "sans-bold", "size": 10, "squeeze": 0.87, "baseline": 107,
                  "align": "left", "color": "#2d3f48", "text": "AGUARDE..."}],
    },
    # ATM screens (bank SBB, flags = language buttons, both kept). Smooth gradient, so no grain needed.
    "ATM_screen_001": {
        "en": 'WELCOME (vertical)',
        "note": '"BEM-VINDO" is what Brazilian ATMs say. Gender-neutral alternative: "BOAS-VINDAS".',
        "erase": [{"rect": [53, 29, 70, 100], "mode": "light", "thresh": 25, "k": 9}],
        "text": [{"box": [53, 20, 70, 108], "font": "sans", "rotate": 90, "color": "#ecf6f7", "stroke": 0.3,
                  "text": "BEM-VINDO"}],
    },
    "ATM_screen_001_out_of_order": {
        "en": 'OUT OF ORDER (vertical, in a red frame)',
        "erase": [{"rect": [56, 30, 68, 99], "mode": "light", "thresh": 40, "k": 7, "isolate": True}],
        "text": [{"box": [56, 32, 68, 98], "font": "roboto-cond", "rotate": 90, "color": "#ffffff", "text": "FORA DE SERVIÇO"}],
    },
    # Tiny green exit light, 20x20 pixel lettering.
    "exit_sign_001_e": {
        "en": 'EXIT',
        "note": 'Pixel letters drawn to match EXIT, one row shorter so the accent fits above them (a single pixel read as a lowercase i).',
        "erase": [{"rect": [0, 0, 20, 10], "color": "#000000"}],
        "text": [{"pixel": "exit", "box": [0, 0, 20, 0], "baselines": [8], "color": "#228322", "text": "SAÍDA"}],
    },
    # Mall corridor signs: wide-tracked caps (12 px) on a light band (rows 213-247), arrow kept.
    "sign_002_exit_mallment_left": {
        "en": 'EXIT TO BAZAAR (arrow left)',
        "note": 'Set in the sign\'s own sharp pixel capitals (S, D, P and the accent drawn to match). The full phrase needs tighter letter spacing; the shorter option keeps the original spacing. Bazaar is "Bazar" in the game text.',
        "erase": [{"rect": [44, 215, 246, 246], "color": "#d1d1d1"}],
        "text": [{"pixel": "mall", "box": [46, 0, 245, 0], "baselines": [236], "gap": 2, "space": 6, "color": "#000000",
                  "text": "SAÍDA PARA O BAZAR"}],
        "alts": {"SAÍDA – BAZAR": {"text": "SAÍDA – BAZAR", "gap": 5, "space": 10}},
    },
    "sign_002_exit_mallment_left_corner": {
        "en": 'EXIT TO BAZAAR (arrow up-left)',
        "erase": [{"rect": [50, 215, 246, 246], "color": "#d1d1d1"}],
        "text": [{"pixel": "mall", "box": [51, 0, 246, 0], "baselines": [236], "gap": 2, "space": 6, "color": "#000000",
                  "text": "SAÍDA PARA O BAZAR"}],
        "alts": {"SAÍDA – BAZAR": {"text": "SAÍDA – BAZAR", "gap": 5, "space": 10}},
    },
    "sign_002_exit_mallment_down": {
        "en": 'EXIT TO BAZAAR (arrow down)',
        "erase": [{"rect": [10, 215, 209, 246], "color": "#d1d1d1"}],
        "text": [{"pixel": "mall", "box": [10, 0, 208, 0], "baselines": [236], "gap": 2, "space": 6, "color": "#000000",
                  "text": "SAÍDA PARA O BAZAR"}],
        "alts": {"SAÍDA – BAZAR": {"text": "SAÍDA – BAZAR", "gap": 5, "space": 10}},
    },
    # Apartment building plate: light bold caps on a dark grainy panel.
    "apartment_sign_001_guard": {
        "en": 'CALL THE GUARD',
        "note": '"Guarda" as in the dialogue speaker names.',
        "erase": [{"rect": [4, 62, 124, 104], "mode": "light", "thresh": 30, "k": 9, "grain": 3}],
        "text": [{"box": [4, 60, 124, 80], "font": "sans-bold", "size": 19.5, "baseline": 79, "color": "#c7c7ca",
                  "mottle": 8, "text": "CHAME"},
                 {"box": [4, 83, 124, 103], "font": "sans-bold", "size": 19.5, "baseline": 102, "color": "#c7c7ca",
                  "mottle": 8, "text": "O GUARDA"}],
    },
    # Water tank plate: CAUTION in yellow on a black box, HOT WATER in black on yellow; both speckled with grime,
    # so the new letters take their colour from the sign's own paint (ink_from).
    "tank_modular_sign_001": {
        "en": 'CAUTION / HOT WATER',
        "note": 'CAUTION is "CUIDADO", as WARNING on the batch 01 plates.',
        "erase": [{"rect": [27, 13, 100, 28], "mode": "light", "thresh": 40, "k": 7, "grain": 3},
                  {"rect": [24, 34, 104, 49], "mode": "dark", "thresh": 40, "k": 7, "grain": 3}],
        "text": [{"box": [28, 14, 99, 27], "font": "roboto-cond-bold", "stretch": True, "color": "#b09050",
                  "ink_from": [0, 21], "text": "CUIDADO"},
                 {"box": [26, 31, 102, 48], "font": "roboto-cond-bold", "stretch": True, "color": "#101010",
                  "ink_from": [0, -21], "text": "ÁGUA QUENTE"}],
    },

    # ---- Batch 03: shop alarm signs, desk notes, hostel decals, alarm label, mine floors ----
    "theft_alarm_001_sign_electronics": {
        "en": 'ELSTRöM ELECTRONICS (x7)',
        "note": 'Elström is the shop name (kept, with its lowercase ö); only ELECTRONICS changes, in the sign\'s own letters (ô drawn like the ö).',
        "erase": [{"rect": [47, 5, 111, 15], "thresh": 100, "isolate": True}, {"rect": [47, 23, 111, 33], "thresh": 100, "isolate": True}, {"rect": [47, 41, 111, 51], "thresh": 100, "isolate": True}, {"rect": [47, 59, 111, 69], "thresh": 100, "isolate": True}, {"rect": [47, 77, 111, 87], "thresh": 100, "isolate": True}, {"rect": [47, 95, 111, 105], "thresh": 100, "isolate": True}, {"rect": [47, 113, 111, 123], "thresh": 100, "isolate": True}],
        "text": [{"pixel": "elstrom", "box": [49, 0, 128, 0], "align": "left", "baselines": [13, 31, 49, 67, 85, 103, 121], "gap": 1,
                  "color": "#03b6ef", "text": "ELETRôNICOS\nELETRôNICOS\nELETRôNICOS\nELETRôNICOS\nELETRôNICOS\nELETRôNICOS\nELETRôNICOS"}],
    },
    "theft_alarm_001_sign_electronics_e": {
        "en": 'ELSTRöM ELECTRONICS (x7)',
        "note": 'Glow (emission) map of the sign before; letters take the old letters\' dimmed colour.',
        "mask_source": "theft_alarm_001_sign_electronics",
        "erase": [{"rect": [47, 5, 111, 15], "thresh": 100, "isolate": True}, {"rect": [47, 23, 111, 33], "thresh": 100, "isolate": True}, {"rect": [47, 41, 111, 51], "thresh": 100, "isolate": True}, {"rect": [47, 59, 111, 69], "thresh": 100, "isolate": True}, {"rect": [47, 77, 111, 87], "thresh": 100, "isolate": True}, {"rect": [47, 95, 111, 105], "thresh": 100, "isolate": True}, {"rect": [47, 113, 111, 123], "thresh": 100, "isolate": True}],
        "text": [{"pixel": "elstrom", "box": [49, 0, 128, 0], "align": "left", "baselines": [13, 31, 49, 67, 85, 103, 121], "gap": 1,
                  "ink": "letters", "color": "#03b6ef", "text": "ELETRôNICOS\nELETRôNICOS\nELETRôNICOS\nELETRôNICOS\nELETRôNICOS\nELETRôNICOS\nELETRôNICOS"}],
    },
    "theft_alarm_001_sign_skeida": {
        "en": 'SKEIDA / PHARMACY',
        "note": 'Skeida is kept (shop name, "Farmácia Skeida" in the item texts). Sign\'s own letters; F and the accent drawn.',
        "erase": [{"rect": [4, 104, 110, 121], "thresh": 100, "isolate": True, "grain": 3}],
        "text": [{"pixel": "skeida", "box": [4, 0, 110, 0], "baselines": [118], "gap": 2, "color": "#d6d7d6", "text": "FARMÁCIA"}],
    },
    "theft_alarm_001_sign_skeida_e": {
        "en": 'SKEIDA / PHARMACY',
        "note": 'Glow (emission) map of the sign before; letters take the old letters\' dimmed colour.',
        "mask_source": "theft_alarm_001_sign_skeida",
        "erase": [{"rect": [4, 104, 110, 121], "thresh": 100, "isolate": True, "grain": 3}],
        "text": [{"pixel": "skeida", "box": [4, 0, 110, 0], "baselines": [118], "gap": 2, "ink": "letters", "color": "#d6d7d6", "text": "FARMÁCIA"}],
    },
    "theft_alarm_001_sign_rob-in": {
        "en": 'ROB-IN / BUILD / AND / REPAIR',
        "note": 'Rob-In is kept. "OBRAS E REPAROS" doesn\'t fit the boxes in this lettering (REPAROS is 2 px too wide), so singular OBRA / REPARO.',
        "erase": [{"rect": [41, 51, 82, 62], "bg": "#f2c61b", "thresh": 150, "isolate": True, "grain": 2},
                  {"rect": [36, 64, 78, 75], "bg": "#f2c61b", "thresh": 150, "isolate": True, "grain": 2},
                  {"rect": [36, 77, 80, 88], "bg": "#f2c61b", "thresh": 150, "isolate": True, "grain": 2}],
        "text": [{"pixel": "robin", "box": [41, 0, 82, 0], "baselines": [60], "gap": 2, "color": "#ea0202", "text": "OBRA"},
                 {"pixel": "robin", "box": [44, 0, 74, 0], "baselines": [73], "gap": 2, "color": "#ea0202", "text": "E"},
                 {"pixel": "robin", "box": [36, 0, 81, 0], "baselines": [86], "gap": 1, "color": "#ea0202", "text": "REPARO"}],
    },
    "theft_alarm_001_sign_rob-in_e": {
        "en": 'ROB-IN / BUILD / AND / REPAIR',
        "note": 'Glow (emission) map of the sign before; letters take the old letters\' dimmed colour.',
        "mask_source": "theft_alarm_001_sign_rob-in",
        "erase": [{"rect": [41, 51, 82, 62], "bg": "#f2c61b", "thresh": 150, "isolate": True, "grain": 2},
                  {"rect": [36, 64, 78, 75], "bg": "#f2c61b", "thresh": 150, "isolate": True, "grain": 2},
                  {"rect": [36, 77, 80, 88], "bg": "#f2c61b", "thresh": 150, "isolate": True, "grain": 2}],
        "text": [{"pixel": "robin", "box": [41, 0, 82, 0], "baselines": [60], "gap": 2, "ink": "letters", "color": "#ea0202", "text": "OBRA"},
                 {"pixel": "robin", "box": [44, 0, 74, 0], "baselines": [73], "gap": 2, "ink": "letters", "color": "#ea0202", "text": "E"},
                 {"pixel": "robin", "box": [36, 0, 81, 0], "baselines": [86], "gap": 1, "ink": "letters", "color": "#ea0202", "text": "REPARO"}],
    },
    "theft_alarm_001_sign_taxfree": {
        "en": 'TAX / FREE',
        "note": 'DUTY / FREE, as duty-free shops are usually called; the FREE line is the original paint, untouched.',
        "erase": [{"rect": [36, 45, 80, 62], "thresh": 100, "isolate": True, "grain": 2}],
        "text": [{"pixel": "taxfree", "box": [33, 0, 84, 0], "baselines": [59], "gap": 3, "color": "#000000", "text": "DUTY"}],
    },
    "theft_alarm_001_sign_taxfree_e": {
        "en": 'TAX / FREE',
        "note": 'Glow (emission) map of the sign before.',
        "mask_source": "theft_alarm_001_sign_taxfree",
        "erase": [{"rect": [36, 45, 80, 62], "thresh": 100, "isolate": True, "grain": 2}],
        "text": [{"pixel": "taxfree", "box": [33, 0, 84, 0], "baselines": [59], "gap": 3, "ink": "letters", "color": "#000000", "text": "DUTY"}],
    },
    # Desk notes (gloss map has no letters).
    "desk_sign_001": {
        "en": 'Sit down and ring the bell (arrow to the bell)',
        "note": 'Typewriter text in Special Elite (a free font with the same worn type). Alternative: "toque o sino".',
        "erase": [{"rect": [8, 69, 121, 99], "mode": "dark", "thresh": 25, "k": 7, "grain": 2}],
        "text": [{"box": [13, 66, 120, 84], "font": "typewriter", "size": 12.5, "baseline": 81, "align": "left", "stroke": 0.35,
                  "color": "#3e3e3e", "text": "Sente-se e"},
                 {"box": [13, 80, 120, 98], "font": "typewriter", "size": 12.5, "baseline": 94, "align": "left", "stroke": 0.35,
                  "color": "#3e3e3e", "text": "toque a sineta"}],
    },
    "desk_sign_001_robin_fix_this": {
        "en": 'ROB[IN, scribbled out] FIX THIS! (marker)',
        "note": 'The scribbled name and the big "!" stay; "FIX THIS" becomes "CONSERTA" (informal, as on a note to a coworker).',
        "erase": [{"rect": [15, 95, 109, 121], "mode": "dark", "thresh": 25, "k": 9, "grain": 2}],   # ROBIN ends at row 93
        "text": [{"box": [17, 96, 108, 119], "font": "gochi", "stretch": True, "color": "#505050", "text": "CONSERTA"}],
        "alts": {"Covered By Your Grace": {"font": "covered"}, "Permanent Marker": {"font": "marker"}},
    },
    "desk_sign_001_dishes": {
        "en": 'Dish return (handwritten)',
        "note": 'A place, not an order: "Devolução de louça" (dish return). The other wording is shown as an option.',
        "erase": [{"rect": [24, 74, 106, 113], "mode": "dark", "thresh": 20, "k": 9, "grain": 2}],
        "text": [{"box": [20, 73, 108, 113], "font": "reenie", "stroke": 0.5, "color": "#3a3a35", "leading": 0, "text": "Devolução\nde louça"}],
        "alts": {"Devolva a louça aqui": {"text": "Devolva a\nlouça aqui"}},
    },
    # Hostel shower decals (alpha is the decal outline only).
    "decal_hostel_shower_001": {
        "en": 'Bathroom & Showers / Customers only!',
        "erase": [{"rect": [22, 47, 234, 69], "mode": "light", "thresh": 30, "k": 9, "isolate": True, "grain": 2},
                  {"rect": [22, 188, 234, 225], "mode": "dark", "thresh": 30, "k": 11, "isolate": True, "grain": 2}],
        "text": [{"box": [24, 44, 232, 68], "font": "sans", "baseline": 67, "color": "#d4d7d7", "text": "Banheiros e chuveiros"},
                 {"box": [24, 186, 232, 224], "font": "narrow", "baseline": 216, "color": "#232321", "text": "Só para clientes!"}],
    },
    "decal_hostel_shower_002": {
        "en": 'CAUTION / Do not drink!',
        "note": 'Alternative: "Água não potável" (non-potable water), the usual wording on Brazilian taps.',
        "erase": [{"rect": [30, 21, 98, 35], "mode": "light", "thresh": 30, "k": 7, "isolate": True, "grain": 2},
                  {"rect": [24, 93, 104, 110], "mode": "dark", "thresh": 30, "k": 9, "isolate": True, "grain": 2}],
        "text": [{"box": [30, 20, 98, 34], "font": "sans", "baseline": 34, "color": "#f7f9fa", "text": "CUIDADO"},
                 {"box": [24, 92, 104, 112], "font": "narrow", "baseline": 109, "color": "#1b1b1b", "text": "Não beba!"}],
    },
    # Alarm box label: two vertical lines, read top to bottom (first line on the right).
    "alarm_001": {
        "en": 'SECURITY ALARM (vertical)',
        "erase": [{"rect": [79, 55, 98, 106], "mode": "light", "thresh": 25, "k": 7, "grain": 2}],
        "text": [{"box": [89, 56, 97, 106], "font": "sans-bold", "rotate": 270, "contrast": [0.15, 0.7], "color": "#a6aca5", "text": "ALARME DE"},
                 {"box": [79, 56, 88, 106], "font": "sans-bold", "rotate": 270, "contrast": [0.15, 0.7], "color": "#a6aca5", "text": "SEGURANÇA"}],
    },
    "sign_008_mines_floors": {
        "en": 'FLOOR A / FLOOR B / FLOOR C (painted, worn)',
        "note": 'NÍVEL is the usual word for mine levels; alternative: ANDAR. The paint is chipped and grimy like the original (C the most).',
        "erase": [{"rect": [134, 41, 220, 58], "mode": "light", "thresh": 30, "k": 9, "grain": 3},
                  {"rect": [134, 116, 220, 133], "mode": "light", "thresh": 30, "k": 9, "grain": 3},
                  {"rect": [134, 191, 220, 208], "mode": "light", "thresh": 25, "k": 9, "grain": 6}],
        "text": [{"box": [135, 36, 219, 57], "font": "sans-bold", "baseline": 57, "contrast": [0.2, 0.7], "mottle": 12, "chip": 0.04, "chip_scale": 0.5,
                  "grime": 10, "color": "#b2c6b4", "text": "NÍVEL A"},
                 {"box": [135, 111, 219, 132], "font": "sans-bold", "baseline": 132, "contrast": [0.2, 0.7], "mottle": 12, "chip": 0.04, "chip_scale": 0.5,
                  "grime": 10, "color": "#b2c6b4", "text": "NÍVEL B"},
                 {"box": [135, 186, 219, 207], "font": "sans-bold", "baseline": 207, "contrast": [0.2, 0.7], "mottle": 14, "chip": 0.3, "chip_scale": 0.55,
                  "grime": 8, "color": "#9eb2a0", "text": "NÍVEL C"}],
    },
    "sign_008_mines_floors_b": {
        "en": 'FLOOR A / FLOOR B / FLOOR C (painted, worn)',
        "erase": [{"rect": [134, 41, 220, 58], "mode": "light", "thresh": 30, "k": 9, "grain": 3},
                  {"rect": [134, 116, 220, 133], "mode": "light", "thresh": 30, "k": 9, "grain": 3},
                  {"rect": [134, 191, 220, 208], "mode": "light", "thresh": 25, "k": 9, "grain": 6}],
        "text": [{"box": [135, 36, 219, 57], "font": "sans-bold", "baseline": 57, "contrast": [0.2, 0.7], "mottle": 12, "chip": 0.04, "chip_scale": 0.5,
                  "grime": 10, "color": "#b2c6b4", "text": "NÍVEL A"},
                 {"box": [135, 111, 219, 132], "font": "sans-bold", "baseline": 132, "contrast": [0.2, 0.7], "mottle": 12, "chip": 0.04, "chip_scale": 0.5,
                  "grime": 10, "color": "#b2c6b4", "text": "NÍVEL B"},
                 {"box": [135, 186, 219, 207], "font": "sans-bold", "baseline": 207, "contrast": [0.2, 0.7], "mottle": 14, "chip": 0.3, "chip_scale": 0.55,
                  "grime": 8, "color": "#9eb2a0", "text": "NÍVEL C"}],
    },

    # ---- Batch 04: machines, notices, screens, metro signs, quarantine notice ----
    "ticket_machine_003": {
        "en": 'SHOW / A TICKET / BELOW (embossed)',
        "erase": [{"rect": [11, 25, 51, 55], "mode": "dark", "thresh": 20, "k": 9, "grain": 2}],
        "text": [{"box": [13, 26, 49, 36], "font": "roboto-cond", "baseline": 35, "size": 9, "mottle": 5, "color": "#6c6b62", "text": "MOSTRE"},
                 {"box": [13, 36, 49, 45], "font": "roboto-cond", "baseline": 44, "size": 9, "mottle": 5, "color": "#6c6b62", "text": "O BILHETE"},
                 {"box": [13, 45, 49, 55], "font": "roboto-cond", "baseline": 54, "size": 9, "mottle": 5, "color": "#6c6b62", "text": "ABAIXO"}],
    },
    "ticket_machine_002": {
        "en": 'TICKETS; BUY A TICKET / COIN RETURN buttons; 1.SHOW A PASSPORT 2.PUT 25 OC COINS INTO THE SLOT 3.PRESS BUY A TICKET; ALLOWED TO BUY A TICKET',
        "note": 'The graffiti stays. Buttons: COMPRAR (buy) and DEVOLUÇÃO (coin return).',
        "erase": [{"rect": [234, 17, 387, 47], "mode": "dark", "thresh": 25, "k": 13, "grain": 3},
                  {"rect": [440, 8, 500, 21], "mode": "dark", "thresh": 15, "k": 5, "isolate": True, "grain": 1},
                  {"rect": [440, 33, 500, 46], "mode": "dark", "thresh": 15, "k": 5, "isolate": True, "grain": 1},
                  {"rect": [215, 63, 318, 104], "mode": "dark", "thresh": 15, "k": 5, "isolate": True, "grain": 2},
                  {"rect": [353, 63, 401, 95], "mode": "dark", "thresh": 15, "k": 5, "isolate": True, "grain": 2}],
        "text": [{"box": [236, 19, 385, 46], "font": "kalam", "color": "#1e1a14", "text": "BILHETES"},
                 {"box": [441, 9, 499, 20], "font": "serif", "color": "#6a6a6a", "text": "COMPRAR"},
                 {"box": [441, 34, 499, 45], "font": "serif", "color": "#6a6a6a", "text": "DEVOLUÇÃO"},
                 {"box": [218, 64, 317, 76], "font": "serif", "size": 8.5, "baseline": 74, "align": "left", "color": "#5c5c5c", "text": "1.MOSTRE O PASSAPORTE"},
                 {"box": [218, 75, 317, 85], "font": "serif", "size": 8.5, "baseline": 83, "align": "left", "color": "#5c5c5c", "text": "2.INSIRA 25 MOEDAS OC"},
                 {"box": [218, 84, 317, 94], "font": "serif", "size": 8.5, "baseline": 92, "align": "left", "color": "#5c5c5c", "text": "NA ABERTURA"},
                 {"box": [218, 93, 317, 103], "font": "serif", "size": 8.5, "baseline": 101, "align": "left", "color": "#5c5c5c", "text": "3.APERTE COMPRAR"},
                 {"box": [355, 64, 401, 76], "font": "serif", "size": 8.5, "baseline": 73, "align": "left", "color": "#5c5c5c", "text": "LIBERADO"},
                 {"box": [355, 74, 401, 85], "font": "serif", "size": 8.5, "baseline": 82, "align": "left", "color": "#5c5c5c", "text": "PARA"},
                 {"box": [355, 83, 401, 94], "font": "serif", "size": 8.5, "baseline": 91, "align": "left", "color": "#5c5c5c", "text": "COMPRAR"}],
    },
    "ticket_machine_mine": {
        "en": 'ORE DROP-OFF (vertical, marker on a label); RECEIPT',
        "note": '"Entrega de minério" as in the item texts. MASMO (brand) stays.',
        "erase": [{"rect": [168, 196, 197, 326], "mode": "dark", "thresh": 25, "k": 9, "isolate": True, "grain": 2},
                  {"rect": [155, 146, 190, 158], "mode": "dark", "thresh": 20, "k": 5, "isolate": True, "grain": 1}],
        "text": [{"box": [169, 198, 196, 324], "font": "gochi", "rotate": 270, "leading": 0, "stroke": 0.4, "color": "#e2541c", "text": "ENTREGA DE\nMINÉRIO"},
                 {"box": [156, 147, 189, 157], "font": "serif", "color": "#6e6e6a", "text": "RECIBO"}],
    },
    "number_ticket_dispenser_001": {
        "en": 'PLEASE / TAKE A / NUMBER (on a red arrow)',
        "note": '"Retire sua senha", what Brazilian queue machines say. Pixel letters in the sign\'s style (I and H drawn).',
        "erase": [{"rect": [17, 164, 56, 182], "mode": "light", "thresh": 35, "k": 5, "isolate": True},
                  {"rect": [15, 183, 57, 190], "mode": "light", "thresh": 35, "k": 5, "isolate": True}],
        "text": [{"pixel": "dispenser", "box": [16, 0, 57, 0], "baselines": [171], "gap": 2, "color": "#cecece", "text": "RETIRE"},
                 {"pixel": "dispenser", "box": [16, 0, 57, 0], "baselines": [180, 189], "gap": 3, "color": "#cecece", "text": "SUA\nSENHA"}],
    },
    "military_area_decal2": {
        "en": 'STOP / MILITARY AREA / NO ENTRY WITHOUT / SPECIAL PERMIT',
        "erase": [{"rect": [22, 12, 234, 84], "mode": "dark", "thresh": 25, "k": 25, "grain": 3},
                  {"rect": [28, 86, 228, 108], "mode": "dark", "thresh": 25, "k": 11, "grain": 3},
                  {"rect": [36, 110, 222, 127], "mode": "dark", "thresh": 25, "k": 9, "grain": 3},
                  {"rect": [36, 127, 222, 143], "mode": "dark", "thresh": 25, "k": 9, "grain": 3}],
        "text": [{"box": [37, 22, 218, 72], "font": "noto-black", "stretch": True, "color": "#141210", "text": "PARE"},
                 {"box": [30, 84, 226, 105], "font": "sans-bold", "tracking": 0.12, "baseline": 104, "color": "#1a1610", "text": "ÁREA MILITAR"},
                 {"box": [38, 112, 220, 126], "font": "sans-bold", "tracking": 0.1, "baseline": 125, "color": "#1a1610", "text": "ENTRADA PROIBIDA SEM"},
                 {"box": [38, 128, 220, 142], "font": "sans-bold", "tracking": 0.1, "baseline": 139, "color": "#1a1610", "text": "AUTORIZAÇÃO ESPECIAL"}],
    },
    "switchyard_breaker_mechanism": {
        "en": 'DANGER 400V AC (the label above is Finnish slang, kept)',
        "erase": [{"rect": [127, 112, 176, 121], "mode": "light", "thresh": 25, "k": 5, "isolate": True, "grain": 1}],
        "text": [{"box": [127, 112, 176, 121], "font": "roboto-cond-bold", "color": "#e8d6d6", "text": "PERIGO 400V AC"}],
    },
    "barrel_001_radioactive": {
        "en": 'RADIOACTIVE (hazard label)',
        "erase": [{"rect": [54, 183, 99, 193], "mode": "dark", "thresh": 25, "k": 5, "isolate": True}],
        "text": [{"pixel": "barrel", "box": [57, 0, 98, 0], "baselines": [189], "gap": 1, "color": "#1c1c1c", "text": "RADIOATIVO"}],
    },
    "flashlight_003_backplate": {
        "en": 'Battery Level / Boost Ready',
        "note": '"Turbo" is what Brazilian flashlights call boost mode.',
        "erase": [{"rect": [36, 44, 92, 56], "mode": "light", "thresh": 25, "k": 7, "grain": 2},
                  {"rect": [36, 88, 92, 100], "mode": "light", "thresh": 25, "k": 7, "grain": 2}],
        "text": [{"box": [34, 44, 94, 56], "font": "sans-bold", "baseline": 54, "size": 10.5, "color": "#a9adac", "text": "Nível da bateria"},
                 {"box": [36, 88, 92, 100], "font": "sans-bold", "baseline": 97, "size": 10.5, "color": "#a9adac", "text": "Turbo pronto"}],
    },
    "sign_002_metro_bazaar": {
        "en": 'M | Bazaar (metro station)',
        "erase": [{"rect": [44, 216, 132, 248], "mode": "light", "thresh": 40, "k": 15, "isolate": True}],
        "text": [{"box": [8, 214, 248, 248], "font": "lato-black", "baseline": 239, "size": 22, "color": "#f6f0f0", "text": "Bazar"}],
    },
    "sign_002_metro_tenement": {
        "en": 'M | Trade Road (metro station, weathered)',
        "note": 'The street has no translation in the game text yet; "Rua do Comércio" here, centred on the red band (one size smaller so it clears the M). Keeping "Trade Road" is the other option.',
        "erase": [{"rect": [50, 213, 186, 251], "mode": "light", "thresh": 35, "k": 15, "grain": 4}],
        "text": [{"box": [9, 214, 247, 249], "font": "lato-black", "baseline": 239, "size": 20, "chip": 0.12,
                  "grime": 14, "mottle": 14, "color": "#e6d2d0", "text": "Rua do Comércio"}],
        "alts": {"Trade Road (kept)": {"text": "Trade Road"}},
    },
    "parcel_locker_001_e_open": {
        "en": 'Take Parcels (locker screen, glow map)',
        "erase": [{"rect": [544, 1554, 640, 1574], "mode": "light", "thresh": 30, "k": 9, "isolate": True}],
        "text": [{"box": [538, 1554, 646, 1574], "font": "sans-bold", "baseline": 1568, "color": "#eef4f5", "text": "Retirar encomendas"}],
    },
    "shroom_extract_machine_001_screen": {
        "en": 'Press the start button / to start the extraction; side buttons Extract / RESULT / SETTINGS; Progress',
        "note": 'Side buttons: Extrair, DADOS (results), CONFIG (settings).',
        "erase": [{"rect": [40, 55, 112, 84], "mode": "dark", "thresh": 20, "k": 7, "isolate": True},
                  {"rect": [28, 94, 60, 105], "mode": "dark", "thresh": 20, "k": 7, "isolate": True},
                  {"rect": [1, 66, 25, 78], "mode": "light", "thresh": 30, "k": 7, "isolate": True},
                  {"rect": [1, 92, 25, 103], "mode": "light", "thresh": 30, "k": 7, "isolate": True},
                  {"rect": [1, 115, 25, 126], "mode": "light", "thresh": 30, "k": 7, "isolate": True}],
        "text": [{"box": [41, 56, 111, 74], "font": "sans-bold", "leading": 0.1, "color": "#52565e", "text": "Aperte o botão iniciar\npara começar a extração"},
                 {"box": [29, 95, 70, 104], "font": "sans-bold", "size": 7, "baseline": 102, "align": "left", "color": "#52565e", "text": "Progresso"},
                 {"box": [1, 69, 24, 76], "font": "roboto-cond-bold", "size": 7, "baseline": 75, "color": "#c8ccd2", "text": "Extrair"},
                 {"box": [1, 94, 24, 102], "font": "roboto-cond-bold", "size": 7, "baseline": 101, "color": "#c8ccd2", "text": "DADOS"},
                 {"box": [1, 117, 24, 125], "font": "roboto-cond-bold", "size": 7, "baseline": 124, "color": "#c8ccd2", "text": "CONFIG"}],
    },
    "shroom_extract_machine_001_screen_progress": {
        "en": 'Extraction in progress / Wait...; side buttons Extract / RESULT / SETTINGS; Progress',
        "erase": [{"rect": [40, 55, 112, 84], "mode": "dark", "thresh": 20, "k": 7, "isolate": True},
                  {"rect": [28, 94, 60, 105], "mode": "dark", "thresh": 20, "k": 7, "isolate": True},
                  {"rect": [1, 66, 25, 78], "mode": "light", "thresh": 30, "k": 7, "isolate": True},
                  {"rect": [1, 92, 25, 103], "mode": "light", "thresh": 30, "k": 7, "isolate": True},
                  {"rect": [1, 115, 25, 126], "mode": "light", "thresh": 30, "k": 7, "isolate": True}],
        "text": [{"box": [41, 59, 111, 82], "font": "sans-bold", "leading": 0.5, "color": "#52565e", "text": "Extração em andamento\nAguarde..."},
                 {"box": [29, 95, 70, 104], "font": "sans-bold", "size": 7, "baseline": 102, "align": "left", "color": "#52565e", "text": "Progresso"},
                 {"box": [1, 69, 24, 76], "font": "roboto-cond-bold", "size": 7, "baseline": 75, "color": "#c8ccd2", "text": "Extrair"},
                 {"box": [1, 94, 24, 102], "font": "roboto-cond-bold", "size": 7, "baseline": 101, "color": "#c8ccd2", "text": "DADOS"},
                 {"box": [1, 117, 24, 125], "font": "roboto-cond-bold", "size": 7, "baseline": 124, "color": "#c8ccd2", "text": "CONFIG"}],
    },
    "shroom_extract_machine_001_screen_done": {
        "en": 'Fluid extraction is done; side buttons Extract / RESULT / SETTINGS; Progress',
        "erase": [{"rect": [40, 55, 112, 84], "mode": "dark", "thresh": 20, "k": 7, "isolate": True},
                  {"rect": [28, 94, 60, 105], "mode": "dark", "thresh": 20, "k": 7, "isolate": True},
                  {"rect": [1, 66, 25, 78], "mode": "light", "thresh": 30, "k": 7, "isolate": True},
                  {"rect": [1, 92, 25, 103], "mode": "light", "thresh": 30, "k": 7, "isolate": True},
                  {"rect": [1, 115, 25, 126], "mode": "light", "thresh": 30, "k": 7, "isolate": True}],
        "text": [{"box": [41, 60, 111, 71], "font": "sans-bold", "color": "#52565e", "text": "Extração do fluido concluída"},
                 {"box": [29, 95, 70, 104], "font": "sans-bold", "size": 7, "baseline": 102, "align": "left", "color": "#52565e", "text": "Progresso"},
                 {"box": [1, 69, 24, 76], "font": "roboto-cond-bold", "size": 7, "baseline": 75, "color": "#c8ccd2", "text": "Extrair"},
                 {"box": [1, 94, 24, 102], "font": "roboto-cond-bold", "size": 7, "baseline": 101, "color": "#c8ccd2", "text": "DADOS"},
                 {"box": [1, 117, 24, 125], "font": "roboto-cond-bold", "size": 7, "baseline": 124, "color": "#c8ccd2", "text": "CONFIG"}],
    },
    "sign_010_border": {
        "en": 'QUARANTINE CHECKPOINT / PLEASE HAVE THE FOLLOWING READY WHEN ENTERING: / ID card OR International Passport OR Entry Permit / MYCOPASS / -OR- / Negative mycotest',
        "note": '"Barreira sanitária" is the Brazilian term for a health checkpoint. The documents match the quest text (Identidade, Passaporte Internacional, Autorização de Entrada). MYCOPASS is a name, kept. The gloss map is redrawn to follow the new text.',
        "erase": [{"rect": [22, 7, 150, 44], "mode": "light", "thresh": 30, "k": 11, "isolate": True, "grain": 2},
                  {"rect": [18, 48, 163, 75], "mode": "dark", "thresh": 30, "k": 7, "isolate": True, "grain": 2},   # frame from x 164
                  {"rect": [58, 86, 163, 134], "mode": "dark", "thresh": 30, "k": 11, "isolate": True, "grain": 2},
                  {"rect": [57, 184, 130, 240], "mode": "dark", "thresh": 30, "k": 11, "isolate": True, "grain": 2}],
        "alpha_follow": {"rect": [8, 5, 184, 251], "gain": 0.99},
        "text": [{"box": [24, 6, 148, 23], "font": "roboto-cond-bold", "baseline": 21, "size": 16, "color": "#eef2f6", "text": "BARREIRA"},
                 {"box": [24, 23, 148, 43], "font": "roboto-cond-bold", "baseline": 40, "size": 16, "color": "#eef2f6", "text": "SANITÁRIA"},
                 {"box": [20, 50, 170, 61], "font": "barlow-cond-bold", "baseline": 60, "align": "left", "color": "#151515", "text": "TENHA EM MÃOS"},
                 {"box": [20, 62, 170, 73], "font": "barlow-cond-bold", "baseline": 72, "align": "left", "color": "#151515", "text": "AO ENTRAR:"},
                 {"box": [61, 88, 134, 106], "font": "barlow-cond-bold", "baseline": 104, "size": 20, "align": "left", "color": "#151515", "text": "Identidade"},
                 {"box": [135, 96, 160, 106], "font": "barlow-cond-bold", "baseline": 104, "size": 11, "align": "left", "color": "#151515", "text": "OU"},
                 {"box": [61, 107, 162, 119], "font": "barlow-cond-bold", "baseline": 117, "align": "left", "color": "#151515", "text": "Passaporte Internacional"},
                 {"box": [61, 120, 162, 132], "font": "barlow-cond-bold", "baseline": 130, "align": "left", "color": "#151515", "text": "OU Autorização de Entrada"},
                 {"box": [60, 186, 100, 201], "font": "barlow-cond-bold", "baseline": 199, "align": "left", "color": "#151515", "text": "-OU-"},
                 {"box": [58, 206, 128, 223], "font": "barlow-cond-bold", "baseline": 219, "size": 14, "align": "left", "color": "#151515", "text": "Micoteste"},
                 {"box": [58, 223, 128, 240], "font": "barlow-cond-bold", "baseline": 235, "size": 14, "align": "left", "color": "#151515", "text": "negativo"}],
    },
}

# Review batches: each is checked by the user, texture by texture, against the original.
# Textures are numbered #1, #2, ... in the order they appear here, across batches; the user refers to
# them by number. Append only: never reorder, remove or insert, or every later number shifts.
BATCHES = {
    "01": ["sign_004_out_of_stock", "sign_004_trespass_bazaar", "sign_004_repaired", "sign_004_trespass_0",
           "Sign Private Property_0", "sign_004_camera", "sign_004_border", "sign_004_bergmann",
           "sign_004_bergmann_2", "sign_004_bio2", "sign_004_construction", "sign_009", "sign_009_radioactive",
           "sign_009_authorized_only", "sign_police_checkpoint", "sign_004_no_bricks"],
    "02": ["ticket_machine_002_screen_default_1", "ticket_machine_002_screen_default_2", "ticket_machine_002_screen_valid",
           "ticket_machine_002_screen_not_valid_1", "ticket_machine_002_screen_wait_1", "ticket_machine_002_screen_wait_2",
           "ticket_machine_002_screen_wait_3", "ticket_machine_002_screen_wait_4", "ATM_screen_001",
           "ATM_screen_001_out_of_order", "exit_sign_001_e", "sign_002_exit_mallment_left",
           "sign_002_exit_mallment_left_corner", "sign_002_exit_mallment_down", "apartment_sign_001_guard",
           "tank_modular_sign_001"],
    "03": ["theft_alarm_001_sign_electronics", "theft_alarm_001_sign_electronics_e", "theft_alarm_001_sign_skeida",
           "theft_alarm_001_sign_skeida_e", "theft_alarm_001_sign_rob-in", "theft_alarm_001_sign_rob-in_e",
           "theft_alarm_001_sign_taxfree", "theft_alarm_001_sign_taxfree_e", "desk_sign_001",
           "desk_sign_001_robin_fix_this", "desk_sign_001_dishes", "decal_hostel_shower_001", "decal_hostel_shower_002",
           "alarm_001", "sign_008_mines_floors", "sign_008_mines_floors_b"],
    "04": ["ticket_machine_003", "ticket_machine_002", "ticket_machine_mine", "number_ticket_dispenser_001",
           "military_area_decal2", "switchyard_breaker_mechanism", "barrel_001_radioactive",
           "shroom_extract_machine_001_screen", "shroom_extract_machine_001_screen_progress",
           "shroom_extract_machine_001_screen_done", "flashlight_003_backplate", "sign_002_metro_bazaar",
           "sign_002_metro_tenement", "sign_010_border", "parcel_locker_001_e_open"],
}

NUMBERS = {}
for _names in BATCHES.values():
    for _n in _names:
        assert _n not in NUMBERS, f"{_n} is in two batches"
        NUMBERS[_n] = len(NUMBERS) + 1
