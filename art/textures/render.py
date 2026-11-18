#!/usr/bin/env python3
"""Redraw text on game textures in Portuguese.

    python render.py [NAME ...]            render the specs in specs.py (all, or the named ones)
    python render.py --sheet OUT NAME ...  also write a before/after review sheet

Reads the game texture from the AssetRipper export, erases the English text (or takes a hand-cleaned plate from
art/textures/clean/<name>.png), draws the Portuguese
and writes art/textures/out/pt-BR/<name>.png (same name and size; staging, not shipped). Approved
textures are copied to textures/pt-BR/, which is what the plugin loads.

The alpha channel is kept from the original unless the spec redraws it: on these opaque signs it is
the gloss (smoothness) map, which sometimes repeats the letters.
Needs Pillow, numpy and opencv-python (scikit-image for "thin" text, IOPaint for "lama" erases).
"""
import argparse
import os
import sys
import zlib

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
GAME = os.environ.get("OBENSEUER_TEXTURES",
                      os.path.expanduser("~/Projects/obenseuer/AssetRipper/ExportedProject/Assets/Texture2D"))
OUT = os.path.join(HERE, "out", "pt-BR")
SS = 8   # supersampling for text
LAYERS = {}   # name -> (old letters, text coverage, output colour) of the last render, for "transfer"

sys.path.insert(0, HERE)
from specs import SPECS, FONTS  # noqa: E402
from pixelfonts import PIXEL_FONTS  # noqa: E402


def hexrgb(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def regrain(out, mask, rect, radius, seed, local):
    """Inpainting is smooth; grainy textures show the patch. Give every inpainted pixel the fine detail
    (pixel minus its blurred surroundings) of a random untouched pixel nearby whose blurred colour is close.
    local: work inside rect only (for isolated erases), so a frame or border next to it doesn't leak in."""
    x0, y0, x1, y1 = rect if local else (0, 0, out.shape[1], out.shape[0])
    sub = out[y0:y1, x0:x1].astype(float)
    m = mask[y0:y1, x0:x1]
    base = cv2.GaussianBlur(sub, (0, 0), 1.2, borderType=cv2.BORDER_REFLECT)
    detail = sub - base
    rng = np.random.default_rng(seed)
    h, w = m.shape
    res = sub.copy()
    for y, x in zip(*np.nonzero(m)):
        for _ in range(40):
            sy, sx = y + rng.integers(-radius, radius + 1), x + rng.integers(-radius, radius + 1)
            if 0 <= sy < h and 0 <= sx < w and not m[sy, sx] and np.abs(base[sy, sx] - base[y, x]).sum() < 45:
                res[y, x] = base[y, x] + detail[sy, sx]
                break
    out = out.copy()
    out[y0:y1, x0:x1] = np.clip(res + 0.5, 0, 255).astype(np.uint8)
    return out


IOPAINT = os.environ.get("IOPAINT", os.path.expanduser("~/.local/share/iopaint/venv/bin/iopaint"))
LAMA_CACHE = os.path.join(HERE, "out", "lama-cache")


def lama_inpaint(rgb, mask):
    """Inpaint mask (255 = fill) with LaMa through the IOPaint CLI. Results are cached by input, so re-renders are
    fast and the same on every run."""
    rgb, mask = np.ascontiguousarray(rgb), np.ascontiguousarray(mask)
    key = "%08x" % (zlib.crc32(mask.tobytes(), zlib.crc32(rgb.tobytes())) & 0xffffffff) + "_%dx%d" % rgb.shape[1::-1]
    cached = os.path.join(LAMA_CACHE, key + ".png")
    if not os.path.exists(cached):
        import shutil
        import subprocess
        import tempfile
        if not os.path.exists(IOPAINT):
            sys.exit(f"lama erase needs IOPaint at {IOPAINT} (or set IOPAINT)")
        with tempfile.TemporaryDirectory() as tmp:
            for sub in ("img", "mask", "res"):
                os.mkdir(os.path.join(tmp, sub))
            Image.fromarray(rgb).save(os.path.join(tmp, "img", "a.png"))
            Image.fromarray(mask).save(os.path.join(tmp, "mask", "a.png"))
            subprocess.run([IOPAINT, "run", "--model", "lama", "--device", "cpu", "--image", os.path.join(tmp, "img"),
                            "--mask", os.path.join(tmp, "mask"), "--output", os.path.join(tmp, "res")],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            os.makedirs(LAMA_CACHE, exist_ok=True)
            shutil.move(os.path.join(tmp, "res", "a.png"), cached)
    res = np.array(Image.open(cached).convert("RGB"))
    out = rgb.copy()
    out[mask > 0] = res[mask > 0]   # LaMa may shift untouched pixels slightly; keep them exact
    return out


def erase(rgb, rect, bg=None, thresh=40, grow=1, radius=3, mode="color", k=5, isolate=False, grain=0, detect=None,
          return_mask=False, poly=None, scatter=None, exclude_red=None, sample_min=None, only_red=None, exclude_dark=None,
          lama=False, avoid_thresh=None, avoid_red=None):
    """Inpaint the old letters inside rect.

    mode "color": letters are pixels far from the background colour (flat backgrounds).
    mode "near": letters are pixels close to bg, here the letter colour (crisp one-colour pixel lettering).
    mode "bright": whitish letters on a coloured surface (lowest channel above thresh).
    mode "rows": letters are pixels off their own row's colour (a band shaded in horizontal stripes).
    mode "dark" / "light": letters are thin strokes darker / lighter than their surroundings
    (black-hat / top-hat with a k x k kernel), so grime and stains on worn signs are left alone.
    isolate: fill only from pixels inside rect, so a frame right next to the letters doesn't bleed in.
    grain: put back texture grain sampled within that radius (see regrain).
    detect: find the letters on this image instead (same layout), e.g. the base texture of a dim emission map.
    poly: only erase inside this polygon too (slanted text next to other artwork).
    exclude_red: leave pixels with r - g above this alone (red artwork crossing the letters).
    sample_min: scatter only copies pixels whose darkest channel is above this (plain paper, not ink).
    avoid_thresh: for scatter in dark / light mode, only pixels above this (not thresh) count as ink not to copy,
    so a mottled surface keeps its darker blotches in the fill. avoid_red: never copy pixels with r - g above this.
    scatter: [rx, ry]: instead of inpainting, give each letter pixel the colour of a random untouched pixel within
    rx/ry, for speckled or grimy surfaces where a smooth fill would show.
    lama: fill with the LaMa model (IOPaint) instead of OpenCV; much better on large letters and textured surfaces.
    Use it with a letter mask: on these small textures, filling a whole rect makes up planks and patches.
    """
    x0, y0, x1, y1 = rect
    look = rgb if detect is None else detect
    region = look[y0:y1, x0:x1].astype(int)
    hat = ref = None
    if mode == "bright":   # whitish letters on a coloured surface: all three channels above thresh
        letters = region.min(axis=2) > thresh
    elif mode == "color":
        ref = np.median(region.reshape(-1, 3), axis=0) if bg is None else np.array(hexrgb(bg))
        letters = np.abs(region - ref).sum(axis=2) > thresh
    elif mode == "near":   # crisp letters in one exact colour: pixels within thresh of bg (artwork around is kept)
        ref = np.array(hexrgb(bg))
        letters = np.abs(region - ref).sum(axis=2) <= thresh
    elif mode == "rows":   # a band striped row by row: anything off its row's colour (median of the non-white pixels)
        ref = np.array([np.median(r[r.min(axis=1) < 130], axis=0) if (r.min(axis=1) < 130).any() else np.median(r, axis=0)
                        for r in region])
        letters = np.abs(region - ref[:, None, :]).sum(axis=2) > thresh
    else:
        gray = cv2.cvtColor(np.ascontiguousarray(look), cv2.COLOR_RGB2GRAY)
        op = cv2.MORPH_BLACKHAT if mode == "dark" else cv2.MORPH_TOPHAT
        hat = cv2.morphologyEx(gray, op, cv2.getStructuringElement(cv2.MORPH_RECT, (k, k)))
        letters = hat[y0:y1, x0:x1] > thresh
    mask = np.zeros(rgb.shape[:2], np.uint8)
    mask[y0:y1, x0:x1] = letters.astype(np.uint8) * 255
    if poly is not None:
        keep = np.zeros_like(mask); cv2.fillPoly(keep, [np.array(poly, np.int32)], 255); mask &= keep
    if exclude_red is not None:
        mask[(look[:, :, 0].astype(int) - look[:, :, 1]) > exclude_red] = 0
    if only_red is not None:   # red ink only (keeps black doodles and lines)
        mask[(look[:, :, 0].astype(int) - look[:, :, 1]) <= only_red] = 0
    core = mask > 0   # the letters themselves, before growing the mask into their anti-aliased edges
    if grow:
        mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=grow)
        clip = np.zeros_like(mask); clip[y0:y1, x0:x1] = 255
        if poly is not None:
            clip[:] = 0; cv2.fillPoly(clip, [np.array(poly, np.int32)], 255)
        mask &= clip
        if exclude_red is not None:
            mask[(look[:, :, 0].astype(int) - look[:, :, 1]) > exclude_red] = 0
        if only_red is not None:
            red = (look[:, :, 0].astype(int) - look[:, :, 1]) > only_red
            mask &= (cv2.dilate(red.astype(np.uint8), np.ones((3, 3), np.uint8)) * 255)
        if exclude_dark is not None:   # never touch dark objects next to the letters (a chair drawn over them)
            mask[look.max(axis=2) < exclude_dark] = 0
    if scatter:
        rx, ry = scatter
        m = mask > 0
        avoid = m.copy()   # never sample letter-like pixels, even outside rect (stripes, other text)
        if mode == "bright":
            like = look.min(axis=2) > thresh
        elif mode == "color":
            like = np.abs(look.astype(int) - ref).sum(axis=2) > thresh
        elif mode == "near":
            like = np.abs(look.astype(int) - ref).sum(axis=2) <= thresh
        elif mode == "rows":
            like = np.zeros(m.shape, bool)
        else:
            like = hat > (thresh if avoid_thresh is None else avoid_thresh)
        avoid |= cv2.dilate(like.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
        if sample_min is not None:
            avoid |= look.min(axis=2) < sample_min
        if avoid_red is not None:
            avoid |= (look[:, :, 0].astype(int) - look[:, :, 1]) > avoid_red
        if exclude_dark is not None:
            avoid |= look.max(axis=2) < exclude_dark
        out = cv2.inpaint(rgb, mask, radius, cv2.INPAINT_TELEA)   # fallback where no sample is found
        rng = np.random.default_rng(x0 * 7919 + y0)
        h, w = m.shape
        for y, x in zip(*np.nonzero(m)):
            for _ in range(120):
                sy, sx = y + rng.integers(-ry, ry + 1), x + rng.integers(-rx, rx + 1)
                if 0 <= sy < h and 0 <= sx < w and not avoid[sy, sx] and (not isolate or (x0 <= sx < x1 and y0 <= sy < y1)):
                    out[y, x] = rgb[sy, sx]
                    break
        return (out, core) if return_mask else out
    if lama:   # LaMa needs the surroundings for context; the mask already stays inside rect
        out = lama_inpaint(rgb, mask)
    elif isolate:
        out = rgb.copy()
        out[y0:y1, x0:x1] = cv2.inpaint(np.ascontiguousarray(rgb[y0:y1, x0:x1]),
                                        np.ascontiguousarray(mask[y0:y1, x0:x1]), radius, cv2.INPAINT_TELEA)
    else:
        out = cv2.inpaint(rgb, mask, radius, cv2.INPAINT_TELEA)
    if grain:
        out = regrain(out, mask > 0, rect, grain, x0 * 1000 + y0, isolate)
    return (out, core) if return_mask else out


def fill(rgb, rect, color):
    x0, y0, x1, y1 = rect
    rgb[y0:y1, x0:x1] = hexrgb(color)
    return rgb


def line_bbox(f, line, tr):
    """Ink bbox of a line with tr extra pixels between letters."""
    b = f.getbbox(line)
    if not tr or len(line) < 2:
        return b
    adv = sum(f.getlength(c) for c in line[:-1]) + tr * (len(line) - 1)
    return (f.getbbox(line[0])[0], b[1], int(adv + f.getbbox(line[-1])[2]), b[3])


def text_layer(size, t):
    """Text t (dict) drawn into its box at SS times the resolution; returns a float alpha mask at 1x.
    "tracking" adds that many em between letters. "baseline" puts the first line's baseline on that row
    (the row under the capitals) instead of centring the ink vertically, so accents don't shift the text."""
    w, h = size
    x0, y0, x1, y1 = t["box"]
    rot = t.get("rotate", 0)
    bw, bh = (x1 - x0), (y1 - y0)
    if rot in (90, 270):
        bw, bh = bh, bw
    font_path = FONTS[t.get("font", "sans-bold")]
    lines = t["text"].split("\n")
    gap = t.get("leading", 0.15)

    def measure(px):
        f = ImageFont.truetype(font_path, px)
        if t.get("weight"):   # variable fonts: wght axis
            f.set_variation_by_axes([t["weight"]])
        boxes = [line_bbox(f, l, t.get("tracking", 0) * px) for l in lines]
        hb = f.getbbox("Hgjpy")   # ink height of a line; accents may reach into the gap above
        lh = hb[3] - hb[1]
        width = max(b[2] - b[0] for b in boxes)
        height = lh * len(lines) + int(gap * lh) * (len(lines) - 1)
        return f, width, height, lh

    # Largest size that fits (a "size" in the spec caps it, so lines of one sign can match).
    lo, hi = 4, int(bh * SS * 2) + 8
    cap = t.get("size")
    if cap:
        hi = min(hi, int(cap * SS))
    while lo < hi:
        mid = (lo + hi + 1) // 2
        _, tw, th, _ = measure(mid)
        sx = t.get("squeeze", 1.0)
        if tw * sx <= bw * SS and th * t.get("vsqueeze", 1.0) <= bh * SS:
            lo = mid
        else:
            hi = mid - 1
    f, tw, th, lh = measure(lo)
    tr = t.get("tracking", 0) * lo
    pad = 4 * SS + int(0.5 * lh)   # room for accents above capitals (tilde on big letters)
    canvas = Image.new("L", (tw + 2 * pad, th + 2 * pad), 0)
    d = ImageDraw.Draw(canvas)
    y = pad - f.getbbox("Hgjpy")[1]
    base = y + f.getmetrics()[0]   # baseline of the first line
    for line in lines:
        b = line_bbox(f, line, tr)
        lw = b[2] - b[0]
        align = t.get("align", "center")
        x = pad + (0 if align == "left" else (tw - lw) if align == "right" else (tw - lw) // 2) - b[0]
        for c in (line if tr else [line]):
            d.text((x, y), c, font=f, fill=255, stroke_width=int(t.get("stroke", 0) * SS))
            x += f.getlength(c) + tr
        y += lh + int(gap * lh)
    crop = canvas.getbbox() or (0, 0, 1, 1)
    canvas = canvas.crop(crop)
    base -= crop[1]
    # Optional stretch to the box (signs often use condensed or wide lettering).
    sx = t.get("squeeze", 1.0)
    cw, ch = canvas.size
    if t.get("stretch"):
        nw, nh = bw * SS, bh * SS
    else:
        nw, nh = int(cw * sx), int(ch * t.get("vsqueeze", 1.0))
    base = base * max(1, nh) / ch
    canvas = canvas.resize((max(1, nw), max(1, nh)), Image.LANCZOS)
    if t.get("shear"):   # italic slant: positive leans the tops to the right
        sh = t["shear"]; cw2, ch2 = canvas.size; pad = int(abs(sh) * ch2) + 1
        canvas = canvas.transform((cw2 + pad, ch2), Image.AFFINE, (1, sh, -pad if sh > 0 else 0, 0, 1, 0), Image.BICUBIC)
    if t.get("arch"):   # curved line of text: the ends sit that many px lower than the middle
        arr = np.asarray(canvas); ch2, cw2 = arr.shape; drop = int(t["arch"] * SS)
        off = (drop * ((np.arange(cw2) - cw2 / 2) / (cw2 / 2)) ** 2).astype(int)
        bent = np.zeros((ch2 + drop + 1, cw2), np.uint8)
        for x in range(cw2):
            bent[off[x]:off[x] + ch2, x] = arr[:, x]
        canvas = Image.fromarray(bent)
    if rot:
        canvas = canvas.rotate(rot, expand=True, resample=Image.BICUBIC)
    full = Image.new("L", (w * SS, h * SS), 0)
    cx = x0 * SS + ((x1 - x0) * SS - canvas.width) // 2
    cy = y0 * SS + ((y1 - y0) * SS - canvas.height) // 2
    if t.get("align") == "left" and not rot:
        cx = x0 * SS
    if t.get("anchor") == "right" and not rot:   # right edge of the ink on the box's right edge
        cx = x1 * SS - canvas.width
    if t.get("valign") == "top":
        cy = y0 * SS
    if "baseline" in t and not rot:
        cy = int(t["baseline"] * SS - base)
    full.paste(canvas, (cx, cy))
    small = np.asarray(full.resize((w, h), Image.BOX)).astype(float) / 255.0
    if t.get("pixelate"):   # blocky lettering: draw at 1/n resolution, then scale back up in n x n blocks
        n = t["pixelate"]
        hh, ww = small.shape
        lo = cv2.resize(small, (max(1, ww // n), max(1, hh // n)), interpolation=cv2.INTER_AREA) >= 0.45
        small = cv2.resize(lo.astype(np.uint8), (ww // n * n, hh // n * n), interpolation=cv2.INTER_NEAREST).astype(float)
        small = np.pad(small, ((0, hh - small.shape[0]), (0, ww - small.shape[1])))
    if t.get("mirror"):   # reversed (seen through glass from inside): flip inside the box
        bx0, _, bx1, _ = t["box"]
        small[:, bx0:bx1] = small[:, bx0:bx1][:, ::-1]
    if t.get("crisp"):   # pixel-art lettering: no anti-aliasing
        small = (small >= t["crisp"]).astype(float)
    if t.get("contrast"):   # [lo, hi]: keep anti-aliasing but steepen it, for small, sharp lettering
        lo, hi = t["contrast"]
        small = np.clip((small - lo) / (hi - lo), 0, 1)
    if t.get("thin"):   # 1-px line lettering (chalk script): skeleton of the coverage above that value
        from skimage.morphology import skeletonize   # needs scikit-image
        small = skeletonize(small > t["thin"]).astype(float)
    return small * t.get("opacity", 1.0)


def sideways_layer(size, t):
    """Letters each turned by t["sideways"] degrees (90 = tops to the left) and set one after another along the box,
    for vertical signs whose texture runs sideways. All letters share one cell height before turning, so they line
    up; the row is then stretched to the box."""
    w, h = size
    f = ImageFont.truetype(FONTS[t.get("font", "sans-bold")], 200)
    hb = f.getbbox("HÇÃÕÉ")   # one cell height for every letter, accents and cedillas included
    cells = []
    for ch in t["text"]:
        cw = int(f.getlength(ch)) or 1
        c = Image.new("L", (cw + 20, hb[3] - hb[1] + 20), 0)
        if ch != " ":
            ImageDraw.Draw(c).text((10, 10 - hb[1]), ch, font=f, fill=255, stroke_width=int(t.get("stroke", 0) * 25))
        cells.append(c.rotate(t["sideways"], expand=True))
    gap = int(t.get("tracking", 0) * 200)
    W = sum(c.width for c in cells) + gap * (len(cells) - 1); H = max(c.height for c in cells)
    row = Image.new("L", (W, H), 0); x = 0
    for c in cells:
        row.paste(c, (x, (H - c.height) // 2)); x += c.width + gap
    row = row.crop(row.getbbox() or (0, 0, 1, 1))
    x0, y0, x1, y1 = t["box"]
    full = Image.new("L", (w * SS, h * SS), 0)
    full.paste(row.resize(((x1 - x0) * SS, (y1 - y0) * SS), Image.LANCZOS), (x0 * SS, y0 * SS))
    return np.asarray(full.resize((w, h), Image.BOX)).astype(float) / 255.0 * t.get("opacity", 1.0)


def circle_layer(size, t):
    """Text set around a circle (badges). t["circle"] = {"center": [x, y], "radius": r, "mid": degrees, "outward": bool}.
    Angles run clockwise from the top. outward (top arcs): read clockwise, letter tops point away from the centre,
    baseline on the radius. Otherwise (bottom arcs): read counter-clockwise, tops point to the centre, the radius is
    the letters' outer (baseline) edge. "size" is the font size in px, "tracking" extra em between letters."""
    w, h = size
    c = t["circle"]; cx, cy = c["center"]; r = c["radius"]; out_ = c.get("outward", True)
    f = ImageFont.truetype(FONTS[t.get("font", "sans-bold")], int(t["size"] * SS))
    tr = t.get("tracking", 0) * t["size"] * SS
    xs = t.get("xscale", 1.0)   # wider (or narrower) letters than the font draws them
    adv = [f.getlength(ch) * xs + tr for ch in t["text"]]
    total = sum(adv) - tr
    R = r * SS
    full = Image.new("L", (w * SS, h * SS), 0)
    asc = f.getbbox("H")[1]
    s = -total / 2
    for ch, a_ in zip(t["text"], adv):
        if ch != " ":
            mid = s + (a_ - tr) / 2
            ang = c["mid"] + (1 if out_ else -1) * np.degrees(mid / R)
            g = Image.new("L", (int(a_ + 4 * SS), int(t["size"] * SS * 1.6)), 0)
            gb = f.getbbox(ch)
            ImageDraw.Draw(g).text((2 * SS + tr / 2 * 0, -asc + 2 * SS), ch, font=f, fill=255,
                                   stroke_width=int(t.get("stroke", 0) * SS), stroke_fill=255)   # "stroke": px heavier
            base_y = 2 * SS + (f.getbbox("H")[3] - asc)   # baseline row inside g
            rot = -ang if out_ else -(ang - 180)
            # glyph anchor: horizontal centre, baseline
            gx = 2 * SS + (a_ - tr) / 2
            if xs != 1.0:
                g = g.resize((max(1, int(g.width * xs)), g.height), Image.BICUBIC)
                gx = (2 * SS + f.getlength(ch) / 2) * xs
            gr = g.rotate(rot, expand=True, resample=Image.BICUBIC, center=(gx, base_y))
            # position of the anchor on the circle
            th = np.radians(ang)
            px, py = cx * SS + R * np.sin(th), cy * SS - R * np.cos(th)
            # after rotate(expand), the anchor moves: rotate it the same way around the image centre
            W0, H0 = g.size; W1, H1 = gr.size
            ar = np.radians(rot); dx, dy = gx - W0 / 2, base_y - H0 / 2
            nx = W1 / 2 + dx * np.cos(ar) + dy * np.sin(ar); ny = H1 / 2 - dx * np.sin(ar) + dy * np.cos(ar)
            full.paste(Image.new("L", gr.size, 255), (int(px - nx), int(py - ny)), gr)
        s += a_
    return np.asarray(full.resize((w, h), Image.BOX)).astype(float) / 255.0 * t.get("opacity", 1.0)


def pixel_layer(size, t, name):
    """Text t set in a bitmap font from pixelfonts.py: one line per baseline in t["baselines"], centred in
    the box's x range (or left- or right-aligned), "gap" empty columns between letters and "space" between words.
    "fade" lightens each ink pixel by a random amount up to that fraction, like the worn originals.
    Returns a mask in 0..1."""
    w, h = size
    font = PIXEL_FONTS[t["pixel"]]
    gap, space = t.get("gap", 1), t.get("space", 3)
    mask = np.zeros((h, w))
    x0, _, x1, _ = t["box"]
    for line, base in zip(t["text"].split("\n"), t["baselines"]):
        words = [[font[c] for c in word] for word in line.split(" ")]
        width = sum(sum(len(g[0][0]) for g in wd) + gap * (len(wd) - 1) for wd in words) + space * (len(words) - 1)
        x = x0 if t.get("align") == "left" else x1 - width if t.get("align") == "right" else x0 + (x1 - x0 - width + 1) // 2
        for wd in words:
            for rows, below in wd:
                top = base + below - len(rows) + 1
                for dy, row in enumerate(rows):
                    for dx, c in enumerate(row):
                        if c in "#+" and 0 <= top + dy < h and 0 <= x + dx < w:   # "+": a half-inked edge pixel
                            mask[top + dy, x + dx] = 1 if c == "#" else t.get("half", 0.5)
                x += len(rows[0]) + gap
            x += space - gap
    if t.get("bold"):   # heavier pixel lettering: every stroke one pixel wider to the right
        mask = np.maximum(mask, np.pad(mask, ((0, 0), (1, 0)))[:, :-1])
    if t.get("stretch"):   # blocky lettering: scale the drawn pixels up to fill the box exactly (nearest neighbour)
        bx0, by0, bx1, by1 = t["box"]
        ys, xs = np.nonzero(mask)
        if len(xs):
            glyphs = mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1].astype(np.uint8)
            big = cv2.resize(glyphs, (bx1 - bx0, by1 - by0), interpolation=cv2.INTER_NEAREST)
            mask = np.zeros_like(mask)
            if t.get("mirror"):
                big = big[:, ::-1]
            mask[by0:by1, bx0:bx1] = big
    if t.get("rotate"):   # tilted pixel lettering (degrees, counter-clockwise), nearest neighbour so it stays jagged
        bx0, by0, bx1, by1 = t["box"]
        m = cv2.getRotationMatrix2D(((bx0 + bx1) / 2, (by0 + by1) / 2), t["rotate"], 1.0)
        mask = cv2.warpAffine(mask.astype(np.float32), m, (w, h), flags=cv2.INTER_NEAREST).astype(float)
    if t.get("fade"):
        rng = np.random.default_rng(zlib.crc32(name.encode()))
        mask *= 1 - t["fade"] * rng.random(mask.shape)
    return mask * t.get("opacity", 1.0)


def ink(t, a, name, rgb, orig, old):
    """Per-pixel ink colour (h, w, 3) for text t drawn with mask a. Worn signs don't have flat ink:
    "shade": [top, bottom] brightness added from the top to the bottom row of the text,
    "mottle": strength of blotchy variation (stains),
    "ink_from": [dx, dy] takes the colour from the cleaned texture that far away (e.g. the sign's own paint),
    "ink": "letters" uses the colour of the erased letters nearby (smoothly filled in), so glow falloff and
    vignettes on emission maps carry over."""
    h, w = a.shape
    col = np.zeros((h, w, 3)) + np.array(hexrgb(t.get("color", "#000000")), float)
    if t.get("ink") == "letters" and old.any():
        sigma = t.get("ink_sigma", 4)
        wsum = cv2.GaussianBlur(old.astype(float), (0, 0), sigma)
        csum = cv2.GaussianBlur(orig.astype(float) * old[:, :, None], (0, 0), sigma)
        field = csum / np.maximum(wsum, 1e-6)[:, :, None]
        x0, y0, x1, y1 = t["box"]   # fallback: the old letters around this text, else all of them
        near = np.zeros_like(old)
        near[max(0, y0 - 10):y1 + 10, max(0, x0 - 10):x1 + 10] = True
        mean = orig[old & near].mean(axis=0) if (old & near).any() else orig[old].mean(axis=0)
        trust = np.clip(wsum / 0.05, 0, 1)[:, :, None]   # far from any old letter: their average colour
        col = field * trust + mean * (1 - trust)
    if t.get("ink_from"):
        dx, dy = t["ink_from"]
        ys = np.clip(np.arange(h) + dy, 0, h - 1)
        xs = np.clip(np.arange(w) + dx, 0, w - 1)
        col = rgb[ys][:, xs].astype(float)
    if t.get("ramp"):   # [[x, colour], ...]: ink that changes from left to right (a sheen across a sign)
        px = [p[0] for p in t["ramp"]]; pc = np.array([hexrgb(p[1]) for p in t["ramp"]], float)
        line = np.stack([np.interp(np.arange(w), px, pc[:, i]) for i in range(3)], axis=1)
        col = np.broadcast_to(line[None, :, :], (h, w, 3)).copy()
    rows = np.nonzero(a.any(axis=1))[0]
    if t.get("shade") and len(rows):
        top, bottom = t["shade"]
        ramp = np.interp(np.arange(h), [rows[0], rows[-1]], [top, bottom])
        col += ramp[:, None, None]
    if t.get("mottle"):
        rng = np.random.default_rng(zlib.crc32((name + t.get("text", "")).encode()))
        field = cv2.GaussianBlur(rng.normal(size=(h, w)), (0, 0), 0.8)
        col += (t["mottle"] * field / (field.std() or 1))[:, :, None]
    return np.clip(col, 0, 255)


def render(name, spec, save=True):
    der = spec.get("derive")
    if der:   # {"from": name, "mirror_rgb": bool, "shade": blur}: a copy of another sign, e.g. a poster seen from behind whose
        # colour is mirrored but whose gloss is not; reuse that sign's render instead of redoing it
        res = np.array(render(der["from"], SPECS[der["from"]], save=False).convert("RGBA"))
        if der.get("mirror_rgb"):
            res[:, :, :3] = res[:, ::-1, :3]
        if der.get("shade"):   # a glow map that is the base texture darkened by a smooth vignette: measure the
            # vignette on the two originals and apply it to the new base. The alpha follows the new base when the
            # originals' alphas are the same (a copy of the gloss), otherwise the glow map keeps its own.
            mine = np.array(Image.open(os.path.join(GAME, name + ".png")).convert("RGBA")).astype(float)
            base = np.array(Image.open(os.path.join(GAME, der["from"] + ".png")).convert("RGBA")).astype(float)
            v = cv2.GaussianBlur((mine[:, :, :3].sum(2) + 1) / (base[:, :, :3].sum(2) + 1), (0, 0), der["shade"])
            res[:, :, :3] = np.clip(res[:, :, :3] * v[:, :, None] + 0.5, 0, 255).astype(np.uint8)
            if not np.array_equal(mine[:, :, 3], base[:, :, 3]):
                res[:, :, 3] = mine[:, :, 3].astype(np.uint8)
        img = Image.fromarray(res, "RGBA")
        if save:
            os.makedirs(OUT, exist_ok=True)
            img.save(os.path.join(OUT, name + ".png"))
            if spec.get("game_name"):
                img.save(os.path.join(OUT, spec["game_name"] + ".png"))
        return img
    wf = spec.get("warp_from")
    if wf:   # {"from": name, "src": [x0, y0, x1, y1], "quad": [tl, tr, br, bl]}: a small, tilted picture of another sign
        # (inventory icons of posters). The change made to that sign (new render minus original) is shrunk, warped onto
        # the quad and added to this texture, so the picture keeps its own lighting and blur.
        icon = np.array(Image.open(os.path.join(GAME, name + ".png")).convert("RGBA")).astype(float)
        new = np.array(render(wf["from"], SPECS[wf["from"]], save=False).convert("RGB")).astype(float)
        old = np.array(Image.open(os.path.join(GAME, wf["from"] + ".png")).convert("RGB")).astype(float)
        x0, y0, x1, y1 = wf["src"]
        q = np.float32(wf["quad"])   # fitted to the icon (correlation of the warped original against it)
        qw, qh = int(np.ptp(q[:, 0])) + 1, int(np.ptp(q[:, 1])) + 1

        nearest = wf.get("replace") is not None   # pixel-art sources: keep the letters blocky when enlarging
        # "smooth": the picture is a slightly larger copy of a soft sign (a screen copied into another machine's glow
        # map); area resampling would double pixel rows unevenly there
        interp = cv2.INTER_NEAREST if nearest else cv2.INTER_CUBIC if wf.get("smooth") else cv2.INTER_AREA

        def warp(im):
            small = cv2.resize(np.ascontiguousarray(im[y0:y1, x0:x1]), (qw, qh), interpolation=interp)
            sh, sw = small.shape[:2]
            h = cv2.getPerspectiveTransform(np.float32([[0, 0], [sw, 0], [sw, sh], [0, sh]]), q)
            return cv2.warpPerspective(small, h, (icon.shape[1], icon.shape[0]), flags=cv2.INTER_LINEAR)
        w_new, w_old = warp(new), warp(old)
        # the picture is lit differently from the poster: scale the change by the local brightness ratio
        shade = np.clip(cv2.GaussianBlur(icon[:, :, :3], (0, 0), 3) / (cv2.GaussianBlur(w_old, (0, 0), 3) + 1), 0.3, 1.5)
        if nearest:   # "replace": [x0, y0, x1, y1] on the picture: there its letters are sharper than the shrunk
            # sign, so adding the change leaves them showing; paint the warped new sign there instead, under the
            # picture's own shading
            rx0, ry0, rx1, ry1 = wf["replace"]
            reg = np.zeros(icon.shape[:2], bool); reg[ry0:ry1, rx0:rx1] = True
            wgt = cv2.GaussianBlur(reg.astype(float), (0, 0), 1.0)[:, :, None] * (icon[:, :, 3:] > 0)   # soft seam
            # the picture's local mean (its haze and light) plus the new sign's detail
            paint = cv2.GaussianBlur(icon[:, :, :3], (0, 0), 3) + (w_new - cv2.GaussianBlur(w_old, (0, 0), 3)) * shade
            icon[:, :, :3] = icon[:, :, :3] * (1 - wgt) + np.clip(paint, 0, 255) * wgt
        else:
            icon[:, :, :3] = np.clip(icon[:, :, :3] + (w_new - w_old) * shade * (icon[:, :, 3:] > 0), 0, 255)
        img = Image.fromarray((icon + 0.5).astype(np.uint8), "RGBA")
        if save:
            os.makedirs(OUT, exist_ok=True)
            img.save(os.path.join(OUT, name + ".png"))
        return img
    src = Image.open(os.path.join(GAME, spec.get("source", name) + ".png"))
    if spec.get("rot180"):   # a sheet of covers stored upside down: work on it turned the right way up, turn back at the end
        src = src.convert("RGBA").rotate(180) if src.mode in ("RGBA", "LA", "P") else src.convert("RGB").rotate(180)
    has_alpha = src.mode in ("RGBA", "LA") or "transparency" in src.info
    im = src.convert("RGBA")
    rgb = np.array(im)[:, :, :3].copy()
    orig = rgb.copy()
    alpha = np.array(im)[:, :, 3]
    # "mask_source": detect the old letters on another texture with the same layout (emission maps are too dim).
    detect = None
    if spec.get("mask_source"):
        detect = np.array(Image.open(os.path.join(GAME, spec["mask_source"] + ".png")).convert("RGB"))
    old = np.zeros(rgb.shape[:2], bool)   # the erased letters, for "ink": "letters"
    for op in spec.get("erase", []):
        if op.get("color"):
            rgb = fill(rgb, op["rect"], op["color"])
        else:
            rgb, m = erase(rgb, op["rect"], op.get("bg"), op.get("thresh", 40), op.get("grow", 1), op.get("radius", 3),
                           op.get("mode", "color"), op.get("k", 5), op.get("isolate", False), op.get("grain", 0),
                           detect, return_mask=True, poly=op.get("poly"), scatter=op.get("scatter"),
                           exclude_red=op.get("exclude_red"), sample_min=op.get("sample_min"), only_red=op.get("only_red"), exclude_dark=op.get("exclude_dark"),
                           lama=op.get("lama", False), avoid_thresh=op.get("avoid_thresh"), avoid_red=op.get("avoid_red"))
            old |= m
    # "dotmatrix": LED signs. Clear "clear" to black, then stamp the sign's own lit dot (the pitch x pitch block at
    # "dot") on a grid from "origin", one dot per lit cell of the pixel font text.
    dm = spec.get("dotmatrix")
    if dm:
        x0, y0, x1, y1 = dm["clear"]
        rgb[y0:y1, x0:x1] = 0
        p = dm["pitch"]; sx, sy = dm["dot"]
        sprite = orig[sy:sy + p, sx:sx + p]
        font = PIXEL_FONTS[dm["font"]]; gap = dm.get("gap", 1)
        col = 0
        for c in dm["text"]:
            rows, _ = font[c]
            for dy, row in enumerate(rows):
                for dx, v in enumerate(row):
                    if v == "#":
                        X = dm["origin"][0] + (col + dx) * p; Y = dm["origin"][1] + dy * p
                        rgb[Y:Y + p, X:X + p] = np.maximum(rgb[Y:Y + p, X:X + p], sprite)
            col += len(rows[0]) + gap
    # "copy": [{"from": [x0, y0, x1, y1], "to": [x, y]}]: paste a block of the original texture elsewhere (reuse the
    # sign's own letters when a word only changes a letter or two).
    for cp in spec.get("copy", []):
        x0, y0, x1, y1 = cp["from"]; tx, ty = cp["to"]
        rgb[ty:ty + y1 - y0, tx:tx + x1 - x0] = orig[y0:y1, x0:x1]
    # "transfer": {"from": texture, "rect": [x0, y0, x1, y1]}: this texture contains a scaled copy of another one
    # (e.g. a poster of the metro map). The other texture's old letters, scaled into rect and widened a little, are
    # inpainted here, then its new letters are laid on top at the same scale; the copy keeps its own dirt.
    tr = spec.get("transfer")
    if tr:
        render(tr["from"], SPECS[tr["from"]], save=False)
        sold, scov, sout = LAYERS[tr["from"]]
        x0, y0, x1, y1 = tr["rect"]
        size = (x1 - x0, y1 - y0)
        hole = (cv2.resize(sold.astype(np.float32), size, interpolation=cv2.INTER_AREA) > tr.get("hole", 0.12)).astype(np.uint8)
        full = np.zeros(rgb.shape[:2], np.uint8); full[y0:y1, x0:x1] = hole[:rgb.shape[0] - y0, :rgb.shape[1] - x0] * 255
        full[rgb.max(axis=2).astype(int) - rgb.min(axis=2) > 70] = 0   # never inpaint over coloured lines (tracks)
        rgb = cv2.inpaint(rgb, full, 2, cv2.INPAINT_TELEA)
        cov = cv2.resize(scov.astype(np.float32), size, interpolation=cv2.INTER_AREA)
        col = cv2.resize((sout * scov[:, :, None]).astype(np.float32), size, interpolation=cv2.INTER_AREA)
        col = col / np.maximum(cov, 1e-6)[:, :, None]
        cov = np.clip(cov * tr.get("gain", 1.0), 0, 1)   # copies are usually crisper than a plain downscale
        sub = rgb[y0:y1, x0:x1].astype(float)
        sub = sub * (1 - cov[:, :, None]) + col * cov[:, :, None]
        rgb[y0:y1, x0:x1] = np.clip(sub + 0.5, 0, 255).astype(np.uint8)
    # "repair": put back line art that an erase cut through.
    #   {"vline": [x0, x1], "rows": [y0, y1], "from_row": y}: a straight vertical line, copied from an intact row;
    #   {"curve": poly, "near": px, "color": hex, "thickness": px, "rgb_test": [rmin, gmax]}: a hand-drawn curve
    #   through poly, refitted (ellipse) from its pixels within "near" px outside poly (and inside "fit_rect")
    #   and redrawn inside poly.
    for rp in spec.get("repair", []):
        if "vline" in rp:
            x0, x1 = rp["vline"]; y0, y1 = rp["rows"]
            rgb[y0:y1, x0:x1] = orig[rp["from_row"], x0:x1][None, :, :]
        if "curve" in rp:
            poly = np.array(rp["curve"], np.int32)
            inside = np.zeros(rgb.shape[:2], np.uint8); cv2.fillPoly(inside, [poly], 1)
            near = cv2.dilate(inside, np.ones((2 * rp["near"] + 1, 2 * rp["near"] + 1), np.uint8)) & (1 - inside)
            rmin, gmax = rp["rgb_test"]
            o = orig.astype(int)
            line = (o[:, :, 0] > rmin) & (o[:, :, 1] < gmax) & (o[:, :, 0] - o[:, :, 1] > 40) & (near > 0)
            if rp.get("fit_rect"):   # only the curve's own pixels, not other red art nearby
                fx0, fy0, fx1, fy1 = rp["fit_rect"]
                keep = np.zeros_like(line); keep[fy0:fy1, fx0:fx1] = True; line &= keep
            ys, xs = np.nonzero(line)
            if len(xs) >= 5:
                ell = cv2.fitEllipse(np.column_stack([xs, ys]).astype(np.float32))
                layer = np.zeros(rgb.shape[:2], np.uint8)
                cv2.ellipse(layer, ell, 255, rp.get("thickness", 4), cv2.LINE_AA)
                a = (layer.astype(float) / 255) * inside
                rgb = np.clip(rgb * (1 - a[:, :, None]) + np.array(hexrgb(rp["color"]), float) * a[:, :, None] + 0.5,
                              0, 255).astype(np.uint8)
    # A hand-cleaned plate (text removed in an image editor) replaces the automatic erase: art/textures/clean/<name>.png,
    # same size as the game texture. The erase ops above still run so new text can take its colour from the old letters.
    clean = os.path.join(HERE, "clean", name + ".png")
    if os.path.exists(clean):
        plate = np.array(Image.open(clean).convert("RGB"))
        if plate.shape == rgb.shape:
            rgb = plate.copy()
        else:
            print(f"warning: {clean} is {plate.shape[1]}x{plate.shape[0]}, expected {rgb.shape[1]}x{rgb.shape[0]}; ignored")
    # The same for the gloss (the alpha channel, saved as a grey image): art/textures/clean/<name>_gloss.png.
    gclean = os.path.join(HERE, "clean", name + "_gloss.png")
    if os.path.exists(gclean):
        gplate = np.array(Image.open(gclean).convert("L"))
        if gplate.shape == alpha.shape:
            alpha = gplate.copy()
        else:
            print(f"warning: {gclean} is {gplate.shape[1]}x{gplate.shape[0]}, expected {alpha.shape[1]}x{alpha.shape[0]}; ignored")
    if spec.get("noise"):
        # Inpainting leaves flat patches; a little grain makes them match the print.
        rng = np.random.default_rng(len(name))
        rgb = np.clip(rgb.astype(int) + rng.normal(0, spec["noise"], rgb.shape[:2])[:, :, None], 0, 255).astype(np.uint8)
    # "pattern": a background made of repeated words (CORRUPTION STOP behind a silhouette). Inside rect, the original's
    # coloured ground (pixels near "ground") is kept, everything else that is not a big dark shape (found by opening the
    # dark pixels with a "big" kernel) is filled from it, and new lines of "text" are tiled every "pitch" px from
    # baseline "y", each line shifted by "shift" px, drawn only on the ground (behind the big shapes); "keep" rects
    # are left alone.
    pt = spec.get("pattern")
    if pt:
        x0, y0, x1, y1 = pt["rect"]
        inside = np.zeros(rgb.shape[:2], np.uint8); inside[y0:y1, x0:x1] = 1
        dark = (orig.max(axis=2) < pt.get("dark", 70)).astype(np.uint8)
        k = pt.get("big", 11)
        big = cv2.dilate(cv2.morphologyEx(dark, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))),
                         np.ones((3, 3), np.uint8))
        ground = np.abs(orig.astype(int) - hexrgb(pt["ground"])).sum(axis=2) <= pt.get("ground_t", 90)
        area = inside & (1 - big)
        for kx0, ky0, kx1, ky1 in pt.get("keep", []):   # artwork inside rect that is neither ground nor dark (a collar)
            area[ky0:ky1, kx0:kx1] = 0
        hole = (area & ~ground).astype(np.uint8)
        rgb = cv2.inpaint(np.ascontiguousarray(rgb), hole * 255, 4, cv2.INPAINT_TELEA)
        rgb = regrain(rgb, hole > 0, (x0, y0, x1, y1), 4, zlib.crc32(name.encode()), False)
        f = ImageFont.truetype(FONTS[pt["font"]], pt["size"])
        canvas = Image.new("L", (rgb.shape[1], rgb.shape[0]), 0)
        d = ImageDraw.Draw(canvas)
        period = f.getlength(pt["text"])
        y, i = pt["y"], 0
        while y < y1 + pt["size"]:
            x = x0 - ((i * pt["shift"]) % period)
            d.text((x, y), pt["text"] * (int((x1 - x) / period) + 2), font=f, fill=255, anchor="ls")
            y += pt["pitch"]; i += 1
        m = (np.asarray(canvas, float) / 255) * area
        rgb = np.clip(rgb * (1 - m[:, :, None]) + np.array(hexrgb(pt["color"]), float) * m[:, :, None] + 0.5, 0, 255).astype(np.uint8)
    # The alpha channel is the gloss map on most signs (Standard shader, smoothness from albedo alpha)
    # and often carries the letters too. "alpha": {"erase": [...], "letters": value} redraws them there;
    # "outline": value gives text outlines their own gloss.
    aspec = spec.get("alpha")
    if aspec:
        a3 = np.dstack([alpha] * 3)
        for op in aspec.get("erase", []):
            if op.get("noise"):   # {"base", "dark": [frac, lo, hi], "grey": [frac, lo, hi]}: a flat gloss value with sharp
                nz = op["noise"]   # random specks, for plain gloss areas where any fill would smear (beer, drinks bands)
                x0, y0, x1, y1 = op["rect"]; rng = np.random.default_rng(zlib.crc32((name + "noise").encode()))
                v = np.full((y1 - y0, x1 - x0), float(nz["base"]))
                for key in ("grey", "dark"):
                    if key in nz:
                        frac, lo, hi = nz[key]; hit = rng.random(v.shape) < frac
                        v[hit] = rng.uniform(lo, hi, v.shape)[hit]
                if nz.get("blur"):   # soften the specks a little, like the original's
                    v = cv2.GaussianBlur(v, (0, 0), nz["blur"])
                a3[y0:y1, x0:x1] = np.clip(v, 0, 255).astype(np.uint8)[:, :, None]
                continue
            a3 = fill(a3, op["rect"], op["color"]) if op.get("color") else erase(
                a3, op["rect"], op.get("bg"), op.get("thresh", 40), op.get("grow", 1), op.get("radius", 3),
                op.get("mode", "color"), op.get("k", 5), op.get("isolate", False), op.get("grain", 0),
                poly=op.get("poly"), scatter=op.get("scatter"),
                detect=orig if op.get("detect_rgb") else None)   # find the letters on the colour image
        alpha = a3[:, :, 0]
        if aspec.get("copy_alpha"):   # the "copy" blocks carry their gloss too (re-used letters keep their shine)
            a0 = np.array(im)[:, :, 3]
            for cp in spec.get("copy", []):
                x0, y0, x1, y1 = cp["from"]; tx, ty = cp["to"]
                alpha[ty:ty + y1 - y0, tx:tx + x1 - x0] = a0[y0:y1, x0:x1]
    out = rgb.astype(float)
    aout = alpha.astype(float)
    cov = np.zeros(rgb.shape[:2])
    for t in spec["text"]:
        a = pixel_layer(im.size, t, name) if t.get("pixel") else circle_layer(im.size, t) if t.get("circle") else sideways_layer(im.size, t) if t.get("sideways") else text_layer(im.size, t)
        if t.get("quad"):   # [tl, tr, br, bl]: the box warped onto these corners (text on a cover seen at an angle)
            bx0, by0, bx1, by1 = t["box"]
            m = cv2.getPerspectiveTransform(np.float32([[bx0, by0], [bx1, by0], [bx1, by1], [bx0, by1]]), np.float32(t["quad"]))
            a = cv2.warpPerspective(a.astype(np.float32), m, (a.shape[1], a.shape[0]), flags=cv2.INTER_LINEAR).astype(float)
            if t.get("quad_crisp"):   # [lo, hi]: re-sharpen after the warp (hard-edged originals)
                lo, hi = t["quad_crisp"]
                a = np.clip((a - lo) / (hi - lo), 0, 1)
        if t.get("flip"):   # upside-down lettering: the drawn line turned 180 degrees inside its box
            fx0, fy0, fx1, fy1 = t["box"]
            a[fy0:fy1, fx0:fx1] = a[fy0:fy1, fx0:fx1][::-1, ::-1].copy()
        if t.get("behind_dark"):   # stay behind dark objects in the original (a chair drawn over the text)
            a = a * (orig.max(axis=2) > t["behind_dark"])
        if t.get("under"):   # stay under reddish artwork (e.g. hatching drawn over a street name): r - g above this
            a = a * ((orig[:, :, 0].astype(int) - orig[:, :, 1]) <= t["under"])
        if t.get("only_on"):   # [[colours], t]: draw only where the original is within t of one of these colours
            cols, tol = t["only_on"]   # (the old letters and their plain ground), so a photo in front stays in front
            near = np.zeros(a.shape, bool)
            for c in cols:
                near |= np.abs(orig.astype(int) - np.array(hexrgb(c))).sum(axis=2) <= tol
            a = a * near
        if t.get("clip"):   # [x0, y0, x1, y1]: draw only inside (text partly hidden behind something)
            cx0, cy0, cx1, cy1 = t["clip"]
            keep = np.zeros_like(a); keep[cy0:cy1, cx0:cx1] = 1
            a = a * keep
        if t.get("hide"):   # polygon the letters go under (tape or a tear over the old lettering)
            cover = np.zeros(a.shape, np.uint8); cv2.fillPoly(cover, [np.array(t["hide"], np.int32)], 1)
            a = a * (1 - cover)
        if t.get("wear"):   # worn ink: fade the mask in uneven patches, up to that fraction
            rng = np.random.default_rng(zlib.crc32((name + "wear" + t.get("text", "")).encode()))
            u = cv2.GaussianBlur(rng.random(a.shape), (0, 0), 1.2)
            u = (u - u.min()) / (np.ptp(u) or 1)
            a = a * (1 - t["wear"] * u ** 2)   # squared: mostly intact, a few patches worn away
        if t.get("speckle"):   # [fraction, depth]: worn paint, that fraction of the letter pixels partly see-through
            rng = np.random.default_rng(zlib.crc32((name + "speckle" + t.get("text", "")).encode()))
            frac, depth = t["speckle"]   # (each by a random amount up to depth), single pixels like on pixel-art signs
            hit = rng.random(a.shape) < frac
            a = a * np.where(hit, 1 - depth * rng.random(a.shape), 1)
        if t.get("chip"):   # chipped paint: that fraction of the letter pixels gone entirely, in small clusters
            rng = np.random.default_rng(zlib.crc32((name + "chip" + t.get("text", "")).encode()))
            u = cv2.GaussianBlur(rng.random(a.shape), (0, 0), t.get("chip_scale", 0.7))
            inside = a > 0.3
            if inside.any():
                a = a * (u >= np.quantile(u[inside], t["chip"]))
        if t.get("grime"):   # dark specks on the surface stay on top of the paint
            lum = rgb.mean(axis=2)
            a = a * ((cv2.GaussianBlur(lum, (0, 0), 2) - lum) <= t["grime"])
        if t.get("soften"):   # brush-painted edges
            a = cv2.GaussianBlur(a, (0, 0), t["soften"])
        if t.get("outline"):   # [px, colour]: an outline around the letters, drawn first
            px, oc = t["outline"]
            if t.get("outline_vary"):   # [min px, blur(, soft)]: hand-inked outline, its width wanders between min
                lo, sig = t["outline_vary"][:2]   # and px; soft widens its fading outer edge
                soft = t["outline_vary"][2] if len(t["outline_vary"]) > 2 else 1.0
                rng = np.random.default_rng(zlib.crc32((name + "outline" + t.get("text", "")).encode()))
                u = cv2.GaussianBlur(rng.random(a.shape), (0, 0), sig)
                u = (u - u.min()) / (np.ptp(u) or 1)
                d = cv2.distanceTransform((a < 0.5).astype(np.uint8), cv2.DIST_L2, 5)
                ring = np.clip((lo + (px - lo) * u - d) / soft + 0.5, 0, 1) * (1 - a)
            else:
                ring = cv2.dilate(a.astype(np.float32), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * px + 1, 2 * px + 1)))
                ring = np.clip(ring - a, 0, 1)
            out = out * (1 - ring[:, :, None]) + np.array(hexrgb(oc), float) * ring[:, :, None]
            if aspec and "outline" in aspec:   # outlines with their own gloss (matte paint on a glossy board)
                aout = aout * (1 - ring) + aspec["outline"] * ring
        if t.get("shadow"):   # [dx, dy, colour]: a drop shadow, the same mask shifted, drawn first
            dx, dy, sc = t["shadow"]
            sh = np.zeros_like(a)
            sh[max(0, dy):a.shape[0] + min(0, dy), max(0, dx):a.shape[1] + min(0, dx)] = \
                a[max(0, -dy):a.shape[0] - max(0, dy), max(0, -dx):a.shape[1] - max(0, dx)]
            sh = sh * (1 - a)
            out = out * (1 - sh[:, :, None]) + np.array(hexrgb(sc), float) * sh[:, :, None]
        if t.get("halo"):   # [blur, colour, strength, dx, dy]: a soft dark glow under the letters (print drop shadow)
            hb, hc, hs, hdx, hdy = t["halo"]
            hm = np.roll(np.roll(a, hdy, axis=0), hdx, axis=1)
            hm = np.clip(cv2.GaussianBlur(hm.astype(np.float32), (0, 0), hb) * hs, 0, 1) * (1 - a)
            out = out * (1 - hm[:, :, None]) + np.array(hexrgb(hc), float) * hm[:, :, None]
        col = ink(t, a, name, rgb, orig, old)
        if t.get("ink_texture"):   # paint takes on the surface's texture: add its fine detail (pixel minus blur)
            base = rgb.astype(float)
            col = np.clip(col + t["ink_texture"] * (base - cv2.GaussianBlur(base, (0, 0), 1.5)), 0, 255)
        if not t.get("alpha_only"):   # alpha_only: the letters exist only in the alpha (cutout signs, colour left as is)
            out = out * (1 - a[:, :, None]) + col * a[:, :, None]
            if t.get("outline") and t.get("outline_inset"):   # px: the outline also covers the letters' outer edge
                din = cv2.distanceTransform((a >= 0.5).astype(np.uint8), cv2.DIST_L2, 5)
                inner = np.clip(t["outline_inset"] - din + 0.5, 0, 1) * a
                out = out * (1 - inner[:, :, None]) + np.array(hexrgb(t["outline"][1]), float) * inner[:, :, None]
        cov = 1 - (1 - cov) * (1 - a)
        gl = t.get("alpha", aspec.get("letters")) if aspec else None   # this line's gloss value (none: gloss untouched)
        if gl is not None:
            aout = aout * (1 - a) + gl * a
    # "alpha_follow": {"rect", "gain"}: on textures whose gloss map is a greyscale copy of the artwork, move the
    # gloss by the same amount the brightness changed (keeps the original's fine gloss detail).
    # "alpha_follow": {"rect", "gain"}: on textures whose gloss map is a greyscale copy of the artwork, the gloss under
    # the old letters is filled in from around them, then the new letters change it as much as they change brightness.
    af = spec.get("alpha_follow")
    if af:
        x0, y0, x1, y1 = af["rect"]
        hole = cv2.dilate(old.astype(np.uint8), np.ones((5, 5), np.uint8))
        base = cv2.inpaint(np.ascontiguousarray(alpha), hole, 3, cv2.INPAINT_TELEA).astype(float)
        dl = out.mean(axis=2) - rgb.astype(float).mean(axis=2)
        aout[y0:y1, x0:x1] = (base + af.get("gain", 1.0) * dl)[y0:y1, x0:x1]
    LAYERS[name] = (old, cov, out)
    res = np.dstack([np.clip(out + 0.5, 0, 255).astype(np.uint8), np.clip(aout + 0.5, 0, 255).astype(np.uint8)])
    mode = "RGBA" if has_alpha else "RGB"
    img = Image.fromarray(res, "RGBA").convert(mode)
    if spec.get("rot180"):
        img = img.rotate(180)
    if save:
        os.makedirs(OUT, exist_ok=True)
        img.save(os.path.join(OUT, name + ".png"))
        if spec.get("game_name"):   # AssetRipper's "_0" export name; the game calls the texture this
            img.save(os.path.join(OUT, spec["game_name"] + ".png"))
    return img


def sheet(path, names, width=360):
    """Original (left) and Portuguese (right) per row, nearest-neighbour upscaled, colour only."""
    font = ImageFont.truetype(FONTS["label"], 18)
    rows = []
    for i, n in enumerate(names, 1):
        spec = SPECS[n]
        a = Image.open(os.path.join(GAME, spec.get("source", n) + ".png")).convert("RGB")
        b = Image.open(os.path.join(OUT, n + ".png")).convert("RGB")
        k = max(1, width // a.width)
        a, b = (x.resize((x.width * k, x.height * k), Image.NEAREST) for x in (a, b))
        row = Image.new("RGB", (a.width * 2 + 30, a.height + 34), "white")
        ImageDraw.Draw(row).text((4, 4), f"{i:02d}  {n}  ({a.width // k}x{a.height // k})", fill="black", font=font)
        row.paste(a, (0, 30)); row.paste(b, (a.width + 30, 30))
        rows.append(row)
    W = max(r.width for r in rows); H = sum(r.height + 16 for r in rows)
    s = Image.new("RGB", (W, H), "white"); y = 0
    for r in rows:
        s.paste(r, (0, y)); y += r.height + 16
    s.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*")
    ap.add_argument("--sheet")
    args = ap.parse_args()
    names = args.names or list(SPECS)
    for n in names:
        render(n, SPECS[n])
    if args.sheet:
        sheet(args.sheet, names)
    print(f"{len(names)} textures -> {os.path.relpath(OUT, ROOT)}")


if __name__ == "__main__":
    main()
