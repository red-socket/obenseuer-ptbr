#!/usr/bin/env python3
"""Build the before/after review page for a batch of redrawn textures.

    python review.py 01        -> review/textures/batch-01.html (gitignored)
    python review.py 01 4 7    -> review/textures/batch-01-redo.html, only textures #4 and #7
    python review.py any 4 77  -> review/textures/batch-any-redo.html, by number across batches

Every texture is shown next to the original (colour, and the gloss map when the spec redraws it),
with the English and Portuguese text, where the game uses it, and the open questions. The page
collects a decision per texture (approve / redo / keep the original) and turns them into a short
text to paste back.
"""
import base64
import html
import io
import os
import subprocess
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import copy  # noqa: E402
from render import GAME, OUT, render  # noqa: E402
from specs import BATCHES, NUMBERS, SPECS  # noqa: E402

ASSETS = os.path.dirname(GAME)


def guid(meta):
    with open(meta) as f:
        for line in f:
            if line.startswith("guid:"):
                return line.split()[1]


def where(name):
    """Scenes and prefabs that use the texture, through its materials."""
    tex = guid(os.path.join(GAME, name + ".png.meta"))
    mats = subprocess.run(["grep", "-lF", tex, "-r", os.path.join(ASSETS, "Material")],
                          capture_output=True, text=True).stdout.split()
    scenes, prefabs = set(), set()
    for m in mats:
        g = guid(m + ".meta")
        hits = subprocess.run(["grep", "-rlF", g, os.path.join(ASSETS, "Scenes"), os.path.join(ASSETS, "GameObject")],
                              capture_output=True, text=True).stdout.splitlines()
        for h in hits:
            (scenes if h.endswith(".unity") else prefabs).add(os.path.splitext(os.path.basename(h))[0])
    out = sorted(scenes)
    if len(prefabs) > 3:
        out.append(f"{len(prefabs)} prefabs, e.g. {', '.join(sorted(prefabs)[:2])}")
    else:
        out += [f"prefab {p}" for p in sorted(prefabs)]
    return out


def data_uri(img):
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def main():
    batch = sys.argv[1]
    # "any": textures from any batch, picked by number (python review.py any 77 82 -> batch-any-redo.html)
    names = sorted(NUMBERS, key=NUMBERS.get) if batch == "any" else BATCHES[batch]
    key = batch
    only = {int(a) for a in sys.argv[2:]}
    if only:
        names = [n for n in names if NUMBERS[n] in only]
        batch += "-redo"
    key = batch + "".join(f"-{n}" for n in sorted(only))   # a new set of textures starts a fresh page state
    cards, blank = [], []
    for i, n in enumerate(names, 1):
        spec = SPECS[n]
        num = NUMBERS[n]
        blank.append(f"#{num} {n}: ")
        a = Image.open(os.path.join(GAME, spec.get("source", n) + ".png")).convert("RGBA")
        b = Image.open(os.path.join(OUT, n + ".png")).convert("RGBA")
        scale = max(1, min(6, 384 // a.width))
        w = a.width * scale
        main = "Português (main version)" if spec.get("alts") else "Português"
        pics = [("Original", a.convert("RGB")), (main, b.convert("RGB"))]
        if spec.get("cutout") or any(t.get("alpha_only") for t in spec["text"]):   # cutout sign: the alpha is the shape, show what the game draws
            def cut(im):
                bg = Image.new("RGB", im.size, (40, 40, 40))
                return Image.composite(im.convert("RGB"), bg, im.getchannel("A").point(lambda v: 255 if v >= 77 else 0))
            pics += [("Original in game (cut out)", cut(a)), ("Portuguese in game (cut out)", cut(b))]
        elif spec.get("alpha") or spec.get("derive"):
            pics += [("Original gloss", a.getchannel("A")), ("Portuguese gloss", b.getchannel("A"))]
        # "alts": {label: overrides for the first text line} shows other candidates (e.g. fonts) to choose from;
        # with "all": True the overrides go to every line (the same word on several panels).
        for label, over in spec.get("alts", {}).items():
            alt = copy.deepcopy(spec)
            for t in alt["text"] if over.get("all") else alt["text"][:1]:
                t.update({k: v for k, v in over.items() if k != "all"})
            pics.append((f"Option: {label}", render(n, alt, save=False).convert("RGB")))
        imgs = "".join(f'<figure><img src="{data_uri(p)}" width="{w}"><figcaption>{c}</figcaption></figure>'
                       for c, p in pics)
        pt = " / ".join(t["text"].replace("\n", " ") for t in spec["text"])
        used = where(n)
        note = f'<p class="note">{html.escape(spec["note"])}</p>' if spec.get("note") else ""
        cards.append(f'''
<section class="card" data-id="#{num}" data-old="{i:02d}" data-name="{html.escape(n)}">
  <h2><span class="num">#{num}</span> {html.escape(n)} <small>{a.width}×{a.height}</small></h2>
  <p class="where">{html.escape("; ".join(used) or "no scene reference found")}</p>
  <p class="text"><b>EN</b> {html.escape(spec.get("en", ""))}<br><b>PT</b> {html.escape(pt)}</p>
  {note}
  <div class="pics">{imgs}</div>
  <div class="decide">
    <label><input type="radio" name="d{i}" value="approve"> Approve</label>
    <label><input type="radio" name="d{i}" value="redo"> Redo</label>
    <label><input type="radio" name="d{i}" value="keep"> Keep original</label>
    <input type="text" class="comment" placeholder="Comment (optional)">
  </div>
</section>''')
    page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Texture review {batch}</title>
<style>
:root {{ --bg:#f6f5f2; --card:#fff; --ink:#1d1d1b; --muted:#6b6a66; --line:#dddbd5; --accent:#2f6f4f; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#1b1b1a; --card:#252523; --ink:#ecebe7; --muted:#a3a19b; --line:#3a3936; --accent:#7cc3a0; }} }}
body {{ background:var(--bg); color:var(--ink); font:15px/1.45 system-ui, sans-serif; margin:0 auto; padding:16px; max-width:1100px; }}
header p {{ color:var(--muted); max-width:70ch; }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:8px; padding:14px 16px; margin:16px 0; }}
.card.approve {{ border-color:var(--accent); }} .card.redo {{ border-color:#c0803a; }} .card.keep {{ border-color:#888; }}
h2 {{ font-size:17px; margin:0 0 4px; }} h2 small {{ color:var(--muted); font-weight:400; }}
.num {{ display:inline-block; min-width:2.6em; color:var(--accent); }}
.where {{ color:var(--muted); font-size:13px; margin:0 0 6px; }}
.text {{ margin:6px 0; }} .note {{ margin:6px 0; padding:6px 10px; border-left:3px solid #c0803a; }}
.pics {{ display:flex; flex-wrap:wrap; gap:16px; margin:10px 0; }}
figure {{ margin:0; }} figcaption {{ font-size:12px; color:var(--muted); }}
img {{ image-rendering:pixelated; display:block; height:auto; max-width:100%; background:#000; }}
body.smooth img {{ image-rendering:auto; }}
.decide {{ display:flex; flex-wrap:wrap; gap:14px; align-items:center; }}
.comment {{ flex:1; min-width:200px; padding:5px 8px; border:1px solid var(--line); border-radius:4px; background:var(--bg); color:var(--ink); }}
#out {{ width:100%; height:12em; font:13px ui-monospace, monospace; background:var(--card); color:var(--ink); border:1px solid var(--line); }}
.bar {{ position:sticky; top:0; background:var(--bg); padding:8px 0; display:flex; gap:12px; align-items:center; z-index:1; }}
button {{ padding:6px 12px; border-radius:4px; border:1px solid var(--line); background:var(--card); color:var(--ink); cursor:pointer; }}
</style></head><body>
<header><h1>Texture review, batch {batch}</h1>
<p>Each texture next to the game's original, enlarged with hard pixels so every change shows. "Smooth" switches to
filtered scaling, closer to what the game draws at a distance. Pick a decision per texture; the summary at the bottom
is what to send back. If picking a decision doesn't update the summary box (scripts
blocked in this viewer), type approve / redo / keep after each line of the box instead.</p></header>
<div class="bar"><label><input type="checkbox" id="smooth"> Smooth</label><span id="count"></span></div>
{"".join(cards)}
<h2>Decisions</h2>
<textarea id="out">{html.escape(chr(10).join([f"Texture review {batch}"] + blank))}</textarea>
<p><button id="copy">Copy</button></p>
<script>
const key = "texture-review-{key}";
const cards = [...document.querySelectorAll(".card")];
let saved = {{}};
try {{ saved = JSON.parse(localStorage.getItem(key) || "{{}}"); }} catch (e) {{}}
function update() {{
  const lines = []; let done = 0; const state = {{}};
  for (const c of cards) {{
    const r = c.querySelector("input[type=radio]:checked"), t = c.querySelector(".comment").value.trim();
    c.classList.remove("approve", "redo", "keep");
    if (r) {{ c.classList.add(r.value); done++; }}
    state[c.dataset.id] = {{ d: r ? r.value : "", t }};
    lines.push(`${{c.dataset.id}} ${{c.dataset.name}}: ${{r ? r.value : "(no decision)"}}${{t ? " - " + t : ""}}`);
  }}
  document.getElementById("out").value = "Texture review {batch}\\n" + lines.join("\\n");
  document.getElementById("count").textContent = `${{done}} of ${{cards.length}} decided`;
  try {{ localStorage.setItem(key, JSON.stringify(state)); }} catch (e) {{}}
}}
for (const c of cards) {{
  const s = saved[c.dataset.id] || saved[c.dataset.old];
  if (s) {{
    const r = c.querySelector(`input[value="${{s.d}}"]`); if (r) r.checked = true;
    c.querySelector(".comment").value = s.t || "";
  }}
  c.addEventListener("input", update); c.addEventListener("change", update);
}}
document.getElementById("smooth").addEventListener("change", e => document.body.classList.toggle("smooth", e.target.checked));
document.getElementById("copy").addEventListener("click", () => {{
  const o = document.getElementById("out"); o.select();
  (navigator.clipboard ? navigator.clipboard.writeText(o.value) : Promise.reject()).catch(() => document.execCommand("copy"));
}});
update();
</script></body></html>'''
    dest = os.path.join(ROOT, "review", "textures")
    os.makedirs(dest, exist_ok=True)
    path = os.path.join(dest, f"batch-{batch}.html")
    with open(path, "w") as f:
        f.write(page)
    print(os.path.relpath(path, ROOT))


if __name__ == "__main__":
    main()
