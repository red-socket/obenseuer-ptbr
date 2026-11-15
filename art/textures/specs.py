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
    "label": "/usr/share/fonts/TTF/DejaVuSans.ttf",
}

SPECS = {
    # Bazaar shop shelf: "Due to high demand, this item is temporarily out of stock. We apologize for any inconvenience."
    "sign_004_out_of_stock": {
        "en": 'Due to high demand, this item is temporarily out of stock. We apologize for any inconvenience.',
        "note": 'The original lettering is a narrow pixel font; this uses a condensed sans stretched to the same block.',
        "erase": [{"rect": [6, 6, 122, 122], "color": "#dcdcdc"}],
        "text": [{"box": [9, 9, 119, 119], "font": "roboto-cond-bold", "color": "#000000", "leading": 0.2, "stretch": True,
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
        "erase": [{"rect": [1, 1, 28, 59], "bg": "#b8b8b8", "thresh": 70}],
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
        "note": '"FRONTEIRA" (9 letters) is unreadable at 43 px wide, so "DIVISA" (6, like BORDER). The original hollow letters became solid ones.',
        "erase": [{"rect": [1, 1, 42, 11], "mode": "light", "thresh": 20, "k": 5},
                  {"rect": [1, 14, 42, 31], "mode": "dark", "thresh": 25, "k": 5}],
        "alpha": {"erase": [{"rect": [0, 0, 43, 31], "mode": "dark", "thresh": 40, "k": 5}], "letters": 0},
        "text": [{"box": [1, 1, 42, 11], "font": "sans-bold", "color": "#c9b48a", "stretch": True, "crisp": 0.5, "text": "DIVISA"},
                 {"box": [14, 13, 29, 21], "font": "sans-bold", "color": "#1a1a1a", "stretch": True, "crisp": 0.5, "text": "NÃO"},
                 {"box": [1, 22, 42, 30], "font": "sans-bold", "color": "#1a1a1a", "stretch": True, "crisp": 0.5, "text": "ULTRAPASSE"}],
    },
    # Bergmann tunnels (place name, kept): "MAINTENANCE TUNNEL". The gloss map holds an unrelated
    # "DANGER / KEEP OUT" from the base sign; it only changes shininess and is left alone.
    "sign_004_bergmann": {
        "en": 'BERGMANN / MAINTENANCE TUNNEL',
        "note": 'Bergmann is kept (place name, "Túneis Bergmann" in the item texts).',
        "erase": [{"rect": [3, 19, 61, 41], "mode": "dark", "thresh": 25, "k": 5, "isolate": True}],
        "text": [{"box": [3, 20, 60, 40], "font": "sans-bold", "color": "#262624", "leading": 0.2, "crisp": 0.45, "text": "TÚNEL DE\nMANUTENÇÃO"}],
    },
    # "WATER TUNNEL"
    "sign_004_bergmann_2": {
        "en": 'BERGMANN / WATER TUNNEL',
        "erase": [{"rect": [3, 19, 60, 41], "mode": "dark", "thresh": 25, "k": 5}],
        "text": [{"box": [10, 20, 54, 40], "font": "sans-bold", "color": "#262624", "leading": 0.2, "crisp": 0.45, "text": "TÚNEL\nDE ÁGUA"}],
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
        "erase": [{"rect": [9, 42, 55, 63], "bg": "#bababa", "thresh": 45, "isolate": True}],
        "text": [{"box": [10, 44, 53, 52], "font": "sans", "color": "#262626", "stretch": True, "stroke": 0.15, "text": "PROPRIEDADE"},
                 {"box": [14, 53, 49, 61], "font": "sans", "color": "#262626", "stretch": True, "stroke": 0.15, "text": "PRIVADA"}],
    },
    # Road sign: "POLICE / CHECKPOINT"
    "sign_police_checkpoint": {
        "en": 'POLICE / CHECKPOINT',
        "note": '"Barreira policial" is the usual term. Alternative: "BLITZ".',
        "erase": [{"rect": [13, 15, 53, 29], "bg": "#8a6c14", "thresh": 70, "grow": 1, "isolate": True},
                  {"rect": [11, 37, 55, 47], "bg": "#8a6c14", "thresh": 70, "grow": 1, "isolate": True}],
        "text": [{"box": [12, 16, 54, 29], "font": "sans-bold", "color": "#211810", "stretch": True, "text": "POLÍCIA"},
                 {"box": [12, 38, 54, 45], "font": "sans-bold", "color": "#211810", "stretch": True, "text": "BARREIRA"}],
    },
    # Hand-written cardboard: "Bricks are not welcome here"
    "sign_004_no_bricks": {
        "en": 'Bricks are not welcome here',
        "note": 'Hand-written; the font is neater than the original scrawl.',
        "erase": [{"rect": [18, 6, 112, 90], "mode": "dark", "thresh": 20, "k": 9}],
        "text": [{"box": [22, 8, 108, 88], "font": "hand", "color": "#262626", "leading": 0.05, "text": "Tijolos\nnão são\nbem-vindos\naqui"}],
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
}

NUMBERS = {}
for _names in BATCHES.values():
    for _n in _names:
        assert _n not in NUMBERS, f"{_n} is in two batches"
        NUMBERS[_n] = len(NUMBERS) + 1
