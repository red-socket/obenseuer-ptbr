#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["fonttools>=4.50"]
# ///
"""Render the Nexus images (header, thumbnail, gallery frames) from the red-socket house-style templates.

    uv run art/render.py "Mod Name" "One-line tagline" --kicker "LABEL" \
        --shot a.webp "Caption one" --shot b.png "Caption two"

Copied from the house-style kit in ../obenseuer/art/render.py and adapted: 1300x372 header, a thumbnail
kicker field, WebP screenshots, outputs in art/nexus/. art/build.sh holds the exact command for this mod.
Needs rsvg-convert and ImageMagick (magick) on PATH, and the AssetRipper export for the game fonts
(default ../obenseuer/AssetRipper, override with OBENSEUER_ASSETRIPPER).
"""
import argparse, os, re, shutil, subprocess, sys, tempfile
import xml.etree.ElementTree as ET
from fontTools.ttLib import TTFont

ART = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(ART)
ASSETRIPPER = os.environ.get("OBENSEUER_ASSETRIPPER", os.path.join(ROOT, "../obenseuer/AssetRipper"))
FONT_DIR = os.path.join(ASSETRIPPER, "ExportedAssets/Assets/Font")

# Font family (as written in the templates) -> file in FONT_DIR, used to measure text.
FONT_FILES = {"Erika Ormig": "Erika Ormig.ttf", "Perfect DOS VGA 437": "PerfectDOSVGA437.ttf"}

# Nexus limits checked after export (see art/STYLE.md, "Nexus formats"). Conservative: the upload
# form no longer states its limits, so these are the last published ones (header 400 KB, images 2 MB).
MAX_BYTES = {"header": 400_000, "thumbnail": 2_000_000, "gallery": 2_000_000}

SVG_NS, XLINK_NS = "http://www.w3.org/2000/svg", "http://www.w3.org/1999/xlink"
ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", XLINK_NS)
HREF_KEYS = ("href", f"{{{XLINK_NS}}}href")

_fonts = {}

def text_width(text, family, size):
    font = _fonts.get(family)
    if font is None:
        font = _fonts[family] = TTFont(os.path.join(FONT_DIR, FONT_FILES[family]))
    cmap, hmtx = font.getBestCmap(), font["hmtx"]
    space = cmap.get(32)
    units = sum(hmtx[cmap.get(ord(c), space)][0] for c in text)
    return units * size / font["head"].unitsPerEm

def family_of(el):
    fam = el.get("font-family") or ""
    m = re.search(r"font-family:\s*([^;]+)", el.get("style") or "")
    if m:
        fam = m.group(1)
    return fam.split(",")[0].strip().strip("'\"")

def set_text(el, text, warn):
    """Put text into an element; shrink it to fit data-fit-width, down to data-min-size."""
    el.text = text
    for child in list(el):
        el.remove(child)
    max_w = el.get("data-fit-width")
    if not max_w:
        return
    size = float(el.get("data-max-size") or el.get("font-size"))
    min_size = float(el.get("data-min-size") or size * 0.5)
    w = text_width(text, family_of(el), size)
    if w > float(max_w):
        size = max(min_size, size * float(max_w) / w)
        if text_width(text, family_of(el), size) > float(max_w) + 1:
            warn(f"'{text}' does not fit in {max_w}px even at {min_size:g}px: shorten it")
    el.set("font-size", f"{size:.1f}")

def stage_images(root, base_dir, shot, tmp):
    """librsvg only loads images beside the SVG, so copy every <image> into the render folder."""
    for n, img in enumerate(root.iter(f"{{{SVG_NS}}}image")):
        key = next((k for k in HREF_KEYS if img.get(k)), None)
        if img.get("id") == "screenshot":
            path = shot
        elif key and not img.get(key).startswith("data:"):
            path = os.path.normpath(os.path.join(base_dir, img.get(key)))
        else:
            continue
        ext = os.path.splitext(path)[1].lower()
        if ext in (".png", ".jpg", ".jpeg", ".svg"):
            staged = f"img{n}{ext}"
            shutil.copyfile(path, os.path.join(tmp, staged))
        else:  # librsvg can't read WebP: convert to PNG
            staged = f"img{n}.png"
            subprocess.run(["magick", path, os.path.join(tmp, staged)], check=True)
        for k in HREF_KEYS:
            img.attrib.pop(k, None)
        img.set("href", staged)

def fill(template, values, shot, tmp, warn):
    tree = ET.parse(template)
    root = tree.getroot()
    for el in root.iter():
        field = el.get("data-field")
        if field and field in values:
            if values[field] is None:
                el.set("display", "none")
            else:
                set_text(el, values[field], warn)
    stage_images(root, os.path.dirname(template), shot, tmp)
    return root

def export(root, out_path, kind, tmp, warn):
    w, h = int(float(root.get("width"))), int(float(root.get("height")))
    svg_path = os.path.join(tmp, "page.svg")
    png_path = os.path.join(tmp, "page.png")
    ET.ElementTree(root).write(svg_path, encoding="utf-8", xml_declaration=True)
    subprocess.run(["rsvg-convert", svg_path, "-o", png_path], check=True,
                   env=dict(os.environ, FONTCONFIG_FILE=os.path.join(tmp, "fonts.conf")))
    for quality in (92, 88, 84, 80, 75, 70, 65, 60):
        subprocess.run(["magick", png_path, "-strip", "-sampling-factor", "4:2:0",
                        "-quality", str(quality), out_path], check=True)
        if os.path.getsize(out_path) <= MAX_BYTES[kind]:
            break
    got = subprocess.run(["magick", "identify", "-format", "%wx%h", out_path],
                         check=True, capture_output=True, text=True).stdout
    size = os.path.getsize(out_path)
    if got != f"{w}x{h}":
        warn(f"{out_path}: rendered {got}, expected {w}x{h}")
    if size > MAX_BYTES[kind]:
        warn(f"{out_path}: {size} bytes is over the {MAX_BYTES[kind]} byte limit")
    print(f"{os.path.relpath(out_path, ROOT)}  {got}  {size / 1024:.0f} KiB")

def write_fontconfig(tmp):
    with open(os.path.join(tmp, "fonts.conf"), "w") as f:
        f.write(f"""<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig><include ignore_missing="yes">/etc/fonts/fonts.conf</include>
<dir>{FONT_DIR}</dir><cachedir>{tmp}/fc-cache</cachedir></fontconfig>""")

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name", help="mod name as shown to players, e.g. 'Better Hunger'")
    ap.add_argument("tagline", help="one line saying what the mod does")
    ap.add_argument("--kicker", default="MOD PARA OBENSEUER",
                    help="DOS-font label under the thumbnail title; ASCII only (the font maps accents to CP437 glyphs)")
    ap.add_argument("--shot", nargs=2, action="append", metavar=("IMAGE", "CAPTION"), required=True,
                    help="a screenshot and its caption; repeat for each gallery image (the first also "
                         "backs the header and thumbnail)")
    ap.add_argument("--key-shot", metavar="IMAGE", help="screenshot for header and thumbnail (default: first --shot)")
    ap.add_argument("--out", default=os.path.join(ART, "nexus"), help="output folder (default: art/nexus)")
    args = ap.parse_args()

    if not os.path.isdir(FONT_DIR):
        sys.exit(f"game fonts not found in {FONT_DIR}: set OBENSEUER_ASSETRIPPER to the AssetRipper export")
    out = args.out
    os.makedirs(out, exist_ok=True)
    shots = args.shot
    key_shot = args.key_shot or shots[0][0]
    for path, _ in shots + [(key_shot, "")]:
        if not os.path.isfile(path):
            sys.exit(f"no such image: {path}")

    problems = []
    warn = lambda msg: (problems.append(msg), print("warning:", msg, file=sys.stderr))
    tpl = lambda name: os.path.join(ART, "templates", name)
    with tempfile.TemporaryDirectory(prefix="rs-render-") as tmp:
        write_fontconfig(tmp)
        title1, _, title2 = args.name.rpartition(" ")
        values = {"title": args.name, "title1": title1 or title2, "title2": title2 if title1 else None,
                  "tagline": args.tagline, "kicker": args.kicker}
        export(fill(tpl("header.svg"), values, key_shot, tmp, warn), os.path.join(out, "header.jpg"), "header", tmp, warn)
        export(fill(tpl("thumbnail.svg"), values, key_shot, tmp, warn), os.path.join(out, "thumbnail.jpg"), "thumbnail", tmp, warn)
        for i, (path, caption) in enumerate(shots, 1):
            v = dict(values, caption=caption, index=f"{i:02d}")
            export(fill(tpl("gallery.svg"), v, path, tmp, warn), os.path.join(out, f"gallery-{i:02d}.jpg"), "gallery", tmp, warn)
    sys.exit(1 if problems else 0)

if __name__ == "__main__":
    main()
