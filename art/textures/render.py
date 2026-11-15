#!/usr/bin/env python3
"""Redraw text on game textures in Portuguese.

    python render.py [NAME ...]            render the specs in specs.py (all, or the named ones)
    python render.py --sheet OUT NAME ...  also write a before/after review sheet

Reads the game texture from the AssetRipper export, erases the English text, draws the Portuguese
and writes art/textures/out/pt-BR/<name>.png (same name and size; staging, not shipped). Approved
textures are copied to textures/pt-BR/, which is what the plugin loads.

The alpha channel is kept from the original unless the spec redraws it: on these opaque signs it is
the gloss (smoothness) map, which sometimes repeats the letters.
Needs Pillow, numpy and opencv-python.
"""
import argparse
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
GAME = os.environ.get("OBENSEUER_TEXTURES",
                      os.path.expanduser("~/Projects/obenseuer/AssetRipper/ExportedProject/Assets/Texture2D"))
OUT = os.path.join(HERE, "out", "pt-BR")
SS = 8   # supersampling for text

sys.path.insert(0, HERE)
from specs import SPECS, FONTS  # noqa: E402


def hexrgb(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def erase(rgb, rect, bg=None, thresh=40, grow=1, radius=3, mode="color", k=5, isolate=False):
    """Inpaint the old letters inside rect.

    mode "color": letters are pixels far from the background colour (flat backgrounds).
    mode "dark" / "light": letters are thin strokes darker / lighter than their surroundings
    (black-hat / top-hat with a k x k kernel), so grime and stains on worn signs are left alone.
    isolate: fill only from pixels inside rect, so a frame right next to the letters doesn't bleed in.
    """
    x0, y0, x1, y1 = rect
    region = rgb[y0:y1, x0:x1].astype(int)
    if mode == "color":
        ref = np.median(region.reshape(-1, 3), axis=0) if bg is None else np.array(hexrgb(bg))
        letters = np.abs(region - ref).sum(axis=2) > thresh
    else:
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        op = cv2.MORPH_BLACKHAT if mode == "dark" else cv2.MORPH_TOPHAT
        hat = cv2.morphologyEx(gray, op, cv2.getStructuringElement(cv2.MORPH_RECT, (k, k)))
        letters = hat[y0:y1, x0:x1] > thresh
    mask = np.zeros(rgb.shape[:2], np.uint8)
    mask[y0:y1, x0:x1] = letters.astype(np.uint8) * 255
    if grow:
        mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=grow)
        clip = np.zeros_like(mask); clip[y0:y1, x0:x1] = 255
        mask &= clip
    if isolate:
        out = rgb.copy()
        out[y0:y1, x0:x1] = cv2.inpaint(np.ascontiguousarray(rgb[y0:y1, x0:x1]),
                                        np.ascontiguousarray(mask[y0:y1, x0:x1]), radius, cv2.INPAINT_TELEA)
        return out
    return cv2.inpaint(rgb, mask, radius, cv2.INPAINT_TELEA)


def fill(rgb, rect, color):
    x0, y0, x1, y1 = rect
    rgb[y0:y1, x0:x1] = hexrgb(color)
    return rgb


def text_layer(size, t):
    """Text t (dict) drawn into its box at SS times the resolution; returns a float alpha mask at 1x."""
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
        boxes = [f.getbbox(l) for l in lines]
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
    canvas = Image.new("L", (tw + 8 * SS, th + 8 * SS), 0)
    d = ImageDraw.Draw(canvas)
    y = 4 * SS - f.getbbox("Hgjpy")[1]
    for line in lines:
        b = f.getbbox(line)
        lw = b[2] - b[0]
        align = t.get("align", "center")
        x = 4 * SS + (0 if align == "left" else (tw - lw) if align == "right" else (tw - lw) // 2) - b[0]
        d.text((x, y), line, font=f, fill=255,
               stroke_width=int(t.get("stroke", 0) * SS))
        y += lh + int(gap * lh)
    canvas = canvas.crop(canvas.getbbox() or (0, 0, 1, 1))
    # Optional stretch to the box (signs often use condensed or wide lettering).
    sx = t.get("squeeze", 1.0)
    cw, ch = canvas.size
    if t.get("stretch"):
        nw, nh = bw * SS, bh * SS
    else:
        nw, nh = int(cw * sx), int(ch * t.get("vsqueeze", 1.0))
    canvas = canvas.resize((max(1, nw), max(1, nh)), Image.LANCZOS)
    if rot:
        canvas = canvas.rotate(rot, expand=True, resample=Image.BICUBIC)
    full = Image.new("L", (w * SS, h * SS), 0)
    cx = x0 * SS + ((x1 - x0) * SS - canvas.width) // 2
    cy = y0 * SS + ((y1 - y0) * SS - canvas.height) // 2
    if t.get("align") == "left" and not rot:
        cx = x0 * SS
    if t.get("valign") == "top":
        cy = y0 * SS
    full.paste(canvas, (cx, cy))
    small = np.asarray(full.resize((w, h), Image.BOX)).astype(float) / 255.0
    if t.get("crisp"):   # pixel-art lettering: no anti-aliasing
        small = (small >= t["crisp"]).astype(float)
    return small * t.get("opacity", 1.0)


def render(name, spec):
    src = Image.open(os.path.join(GAME, spec.get("source", name) + ".png"))
    has_alpha = src.mode in ("RGBA", "LA") or "transparency" in src.info
    im = src.convert("RGBA")
    rgb = np.array(im)[:, :, :3].copy()
    alpha = np.array(im)[:, :, 3]
    for op in spec.get("erase", []):
        if op.get("color"):
            rgb = fill(rgb, op["rect"], op["color"])
        else:
            rgb = erase(rgb, op["rect"], op.get("bg"), op.get("thresh", 40), op.get("grow", 1), op.get("radius", 3),
                        op.get("mode", "color"), op.get("k", 5), op.get("isolate", False))
    if spec.get("noise"):
        # Inpainting leaves flat patches; a little grain makes them match the print.
        rng = np.random.default_rng(len(name))
        rgb = np.clip(rgb.astype(int) + rng.normal(0, spec["noise"], rgb.shape[:2])[:, :, None], 0, 255).astype(np.uint8)
    # The alpha channel is the gloss map on most signs (Standard shader, smoothness from albedo alpha)
    # and often carries the letters too. "alpha": {"erase": [...], "letters": value} redraws them there.
    aspec = spec.get("alpha")
    if aspec:
        a3 = np.dstack([alpha] * 3)
        for op in aspec.get("erase", []):
            a3 = fill(a3, op["rect"], op["color"]) if op.get("color") else erase(
                a3, op["rect"], op.get("bg"), op.get("thresh", 40), op.get("grow", 1), op.get("radius", 3),
                op.get("mode", "color"), op.get("k", 5), op.get("isolate", False))
        alpha = a3[:, :, 0]
    out = rgb.astype(float)
    aout = alpha.astype(float)
    for t in spec["text"]:
        a = text_layer(im.size, t)
        out = out * (1 - a[:, :, None]) + np.array(hexrgb(t["color"]), float) * a[:, :, None]
        if aspec and "letters" in aspec:
            aout = aout * (1 - a) + t.get("alpha", aspec["letters"]) * a
    res = np.dstack([np.clip(out + 0.5, 0, 255).astype(np.uint8), np.clip(aout + 0.5, 0, 255).astype(np.uint8)])
    mode = "RGBA" if has_alpha else "RGB"
    img = Image.fromarray(res, "RGBA").convert(mode)
    os.makedirs(OUT, exist_ok=True)
    img.save(os.path.join(OUT, name + ".png"))
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
