#!/usr/bin/env python3
"""Extract every player-visible English string from Obenseuer into gettext templates.

Reads the AssetRipper export (scenes, prefabs, ScriptableObjects, decompiled C#) and
the game's StreamingAssets, and writes one .pot file per domain plus a stats table.

    python3 -I tools/extract.py --out source/pot --stats source/stats.md

Every entry gets a stable key in msgctxt (item ID, dialogue entry ID, task ID, ...).
UI labels and C# literals have no stable ID, so their English text is the key.
"""
import argparse
import collections
import json
import multiprocessing
import os
import re
import sys

import yaml

HOME = os.path.expanduser("~")
DEFAULT_RIPPER = f"{HOME}/Projects/obenseuer/AssetRipper"
DEFAULT_GAME = f"{HOME}/.local/share/Steam/steamapps/common/Obenseuer"

TMP_GUID = "67dfb1fdfb2b407222eda8e23ac8b724"  # Unity.TextMeshPro scripts (TextMeshProUGUI, TextMeshPro)

# Display fields of ScriptableObjects and scene components, per class.
# Classes deriving from Interactable get "title" and "m_useMessage" automatically.
FIELDS = {
    "TaskInfo": ["title", "description"],
    "TaskObjective": ["title", "description"],
    "TaskItem": ["itemName", "itemDetails"],
    "TaskItemBlueprint": ["itemName", "itemDetails"],
    "TaskItemMap": ["itemName", "itemDetails"],
    "TaskItemMail": ["itemName", "itemDetails"],
    "TaskItemGroup": ["itemName", "itemDetails"],
    "NoteInfo": ["title", "content"],
    "Email": ["title", "content", "from"],
    "BookInfo": ["title"],
    "Landmark": ["title"],
    "Furniture": ["title", "details"],
    "FurnitureGroup": ["title"],
    "PlayerMailSubscription": ["subscriptionName"],
    "TenementContractor": ["contractorName"],
    "LoadingScreen": ["title", "hintText"],
    "StartSelection": ["title", "question", "description"],
    "PlayerStatUI": ["statName"],
    "Achievements": ["rewardName"],
    "Character": ["Job", "Relationship"],
    "ToolTipInfo": ["toolTipInfoTitle", "toolTipInfoDetails"],
    "PlayerStatsToolTipInfo": ["toolTipInfoTitle", "toolTipInfoDetails"],
    "HintContext": ["title", "header", "lines"],
}

# ScriptableObject classes whose strings get an asset-based key instead of a text key.
SO_DOMAINS = {
    "TaskInfo": "tasks", "TaskObjective": "tasks",
    "TaskItem": "taskitems", "TaskItemBlueprint": "taskitems", "TaskItemMap": "taskitems",
    "TaskItemMail": "taskitems", "TaskItemGroup": "taskitems",
    "NoteInfo": "notes", "Email": "notes", "BookInfo": "notes",
    "Landmark": "world", "PlayerMailSubscription": "world", "Furniture": "furniture",
    "FurnitureGroup": "furniture", "TenementContractor": "tenement",
}

# C# calls whose string literal arguments reach the screen.
UI_SINKS = re.compile(
    r"CreateNotification|ChangeUseText|UseAndHoldText|ShowNotification|UpdateToolTipInfo|"
    r"ToolTip\.instance\.Activate|\.Activate\(|HintContent\(|\.AddText\(|\.AddList\(|KeyCodeInfoToString|"
    r"CreateStatInfoUI|\.text\s*=|\.text\s*\+=|SetText\(|ShowLine\(|Print\(")
NOT_UI = re.compile(r"Debug\.|LogWarning|LogError|Exception\(|Resources\.Load|GetKey|PlayerPrefs|Animator|"
                    r"\.Play\(|SetBool|SetTrigger|Shader\.|Find\(|CompareTag|DialogueLua|Lua\.|GetComponent")
LITERAL = re.compile(r'\$?@?"((?:[^"\\]|\\.)*)"')


class Catalog:
    """Ordered msgctxt -> entry map for one domain."""

    def __init__(self, name, keyed):
        self.name = name
        self.keyed = keyed  # False: the English text is the key (no msgctxt)
        self.entries = collections.OrderedDict()

    def add(self, key, text, ref):
        text = clean(text)
        if not text or not re.search(r"[A-Za-z]", text):
            return
        if not self.keyed and is_noise(text):
            return
        k = key if self.keyed else text
        e = self.entries.get(k)
        if e is None:
            self.entries[k] = e = {"text": text, "refs": []}
        elif e["text"] != text:
            # Same key, different text: keep both visible to the translator.
            alt = f"{k}#{len(self.entries)}"
            self.entries[alt] = e = {"text": text, "refs": []}
        if ref and ref not in e["refs"] and len(e["refs"]) < 6:
            e["refs"].append(ref)

    def words(self):
        return sum(len(re.findall(r"[A-Za-zÀ-ÿ']+", e["text"])) for e in self.entries.values())


NOISE = re.compile(
    r"^\s*(.|(.)\2+|[_\-=.\s]+|.*Lorem [Ii]psum.*|.*Place Holder.*|.*99[./:]99.*|"
    r"(\w\s*\n\s*)+\w?|Info (Text|Title|Details)|BSpace|V\.\d.*|\d+\s*(Hz|dB|-?\d+ dB)|Display \d+|"
    r"\d+ x \d+|-?\d+([.,]\d+)?%?)\s*$", re.S)


def is_noise(text):
    """Layout placeholders and keyboard keys that are never shown as English prose."""
    t = text.replace("\u200b", "").strip()
    return len(t) < 2 or bool(NOISE.match(t))


def clean(text):
    if text is None:
        return ""
    text = str(text)
    return text if text.strip() else ""


# ---------------------------------------------------------------- Unity YAML

FIELD_LINE = re.compile(r"^(\s*)(- )?(\w+): ?(.*)$")


def read_scalar(first, lines, i, indent):
    """Return (python value, next index) for a YAML scalar that may span lines."""
    buf = [first]
    v = first.lstrip()
    if v.startswith('"'):
        body = v[1:]
        while not re.search(r'(?<!\\)(\\\\)*"\s*$', body) and i < len(lines):
            body = lines[i].rstrip("\n")
            buf.append(body)
            i += 1
    elif v.startswith("'"):
        body = v[1:]
        while not re.search(r"(?<!')('')*'\s*$", body) and i < len(lines):
            body = lines[i].rstrip("\n")
            buf.append(body)
            i += 1
    else:
        while i < len(lines):
            nxt = lines[i]
            ind = len(nxt) - len(nxt.lstrip(" "))
            if ind <= indent or FIELD_LINE.match(nxt) or nxt.startswith("---"):
                break
            buf.append(nxt.rstrip("\n"))
            i += 1
    try:
        val = yaml.safe_load("v: " + "\n  ".join(s.strip() if n else s for n, s in enumerate(buf)))["v"]
    except yaml.YAMLError:
        val = " ".join(s.strip() for s in buf).strip("\"'")
    return val, i


def iter_monobehaviours(path, guid2cls):
    """Yield (class name, fileID of the document, [(field, value)]) for every MonoBehaviour."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        lines = fh.readlines()
    i, cls, doc_id, fields, in_mb = 0, None, None, [], False
    while i < len(lines):
        line = lines[i]
        i += 1
        if line.startswith("--- !u!"):
            if in_mb and cls:
                yield cls, doc_id, fields
            in_mb, cls, fields = False, None, []
            doc_id = line.split("&")[-1].split()[0] if "&" in line else None
            continue
        if line.startswith("MonoBehaviour:"):
            in_mb = True
            continue
        if not in_mb:
            continue
        if line.startswith("  m_Script:"):
            m = re.search(r"fileID: (-?\d+), guid: (\w+)", line)
            if m:
                cls = "TMP_Text" if m.group(2) == TMP_GUID else guid2cls.get(m.group(2))
            continue
        if cls is None:
            continue
        m = FIELD_LINE.match(line.rstrip("\n"))
        if not m:
            continue
        indent, name, value = len(m.group(1)), m.group(3), m.group(4)
        if value.startswith(("{", "[")) or value == "":
            continue
        val, i = read_scalar(value, lines, i, indent)
        if isinstance(val, str):
            fields.append((name, val))
    if in_mb and cls:
        yield cls, doc_id, fields


def interactable_classes(src):
    """Every class in SRC that derives (transitively) from Interactable."""
    parent = {}
    for f in os.listdir(src):
        if f.endswith(".cs"):
            with open(os.path.join(src, f), encoding="utf-8", errors="replace") as fh:
                for m in re.finditer(r"\bclass (\w+)\s*:\s*(\w+)", fh.read()):
                    parent[m.group(1)] = m.group(2)
    out = set()
    for c in parent:
        p, seen = c, set()
        while p in parent and p not in seen:
            seen.add(p)
            p = parent[p]
            if p == "Interactable":
                out.add(c)
                break
    out.add("Interactable")
    return out


# ---------------------------------------------------------------- sources

def extract_items(game, cat):
    path = f"{game}/Obenseuer_Data/StreamingAssets/Items.json"
    with open(path, encoding="utf-8-sig") as fh:
        items = json.load(fh)
    for it in items:
        ref = f"Items.json:{it['ID']}"
        cat.add(f"item.{it['ID']}.title", it.get("Title"), ref)
        cat.add(f"item.{it['ID']}.desc", it.get("Description"), ref)
        for n, skin in enumerate((it.get("Appearance") or {}).get("SkinNames") or []):
            cat.add(f"item.{it['ID']}.skin.{n}", skin, ref)
    return len(items)


def extract_recipes(game, cat):
    path = f"{game}/Obenseuer_Data/StreamingAssets/Recipes.json"
    with open(path, encoding="utf-16") as fh:
        recipes = json.load(fh)["Recipes"]
    for r in recipes:
        cat.add(f"recipe.{r['ID']}.name", r.get("Name"), f"Recipes.json:{r['ID']}")


def extract_dialogue(assets, dlg, actors):
    path = f"{assets}/MonoBehaviour/Dialogue Database.asset"
    with open(path, encoding="utf-8") as fh:
        raw = re.sub(r"^--- !u!.*$", "---", fh.read(), flags=re.M)
    raw = re.sub(r"^%TAG.*$", "", raw, flags=re.M)
    db = next(yaml.load_all(raw, Loader=getattr(yaml, "CSafeLoader", yaml.SafeLoader)))["MonoBehaviour"]

    def fields(obj):
        return {f["title"]: f.get("value") for f in obj.get("fields") or []}

    for a in db.get("actors") or []:
        f = fields(a)
        name = f.get("Display Name") or (f.get("Name") or "").split("/")[-1]
        actors.add(f"actor.{a['id']}.name", name, f.get("Name"))
    for c in db.get("conversations") or []:
        title = fields(c).get("Title")
        for e in c.get("dialogueEntries") or []:
            f = fields(e)
            key = f"dlg.{c['id']}.{e['id']}"
            dlg.add(f"{key}.text", f.get("Dialogue Text"), title)
            dlg.add(f"{key}.menu", f.get("Menu Text"), title)
    return len(db.get("conversations") or [])


_WORKER = {}


def _init_worker(guid2cls, inter):
    _WORKER["guid2cls"], _WORKER["inter"] = guid2cls, inter


def _scan_asset(args):
    """Worker: (domain, key or None, text, ref) rows for one scene/prefab/asset file."""
    path, rel = args
    rows, seen = [], set()
    is_asset = path.endswith(".asset")
    for cls, _doc, fields in iter_monobehaviours(path, _WORKER["guid2cls"]):
        want = set(FIELDS.get(cls, []))
        if cls in _WORKER["inter"]:
            want |= {"title", "m_useMessage"}
        if cls == "TMP_Text":
            want = {"m_text"}
        if not want:
            continue
        so_dom = SO_DOMAINS.get(cls) if is_asset else None
        first = {}
        for k, v in fields:
            first.setdefault(k, v)
        ident = first.get("id") or first.get("addressableAssetPath") or rel
        for name, value in fields:
            if name not in want:
                continue
            if so_dom:
                key = f"{cls}.{ident}.{name}"
                if (key, value) not in seen:
                    seen.add((key, value))
                    rows.append((so_dom, key, value, rel))
            elif cls == "TMP_Text":
                rows.append(("ui", None, value, rel))
            else:
                if name == "m_useMessage" and value.strip() and not value.startswith("("):
                    value = f"({value})"  # Interactable.useMessage adds the parentheses before display
                rows.append(("world", None, value, f"{rel} ({cls}.{name})"))
    return rows


def extract_assets(assets, src, cats, guid2cls, jobs):
    """ScriptableObjects (keyed) and scene/prefab components (text-keyed), scanned in parallel."""
    inter = interactable_classes(src)
    paths = []
    for sub in ("Content", "Scenes", "GameObject", "Resources"):
        for root, _, files in os.walk(f"{assets}/{sub}"):
            for fn in sorted(files):
                if fn.endswith((".asset", ".unity", ".prefab")):
                    path = os.path.join(root, fn)
                    paths.append((path, os.path.relpath(path, assets)))
    paths.sort(key=lambda p: -os.path.getsize(p[0]))  # big scenes first for better load balance
    with multiprocessing.Pool(jobs, initializer=_init_worker, initargs=(guid2cls, inter)) as pool:
        results = dict(zip((p[1] for p in paths), pool.map(_scan_asset, paths, chunksize=4)))
    seen_so = set()
    for rel in sorted(results):  # deterministic output order
        for dom, key, value, ref in results[rel]:
            if key is not None:
                if (key, value) in seen_so:
                    continue
                seen_so.add((key, value))
            cats[dom].add(key, value, ref)


def extract_string_tables(assets, cat):
    """Unity Localization tables (unused by the game, but the en column is a handy glossary seed)."""
    base = f"{assets}/Localization/String Tables"
    if not os.path.isdir(base):
        return
    for table in sorted(os.listdir(base)):
        shared = f"{base}/{table}/{table} Shared Data.asset"
        en = f"{base}/{table}/{table}_en.asset"
        if not (os.path.exists(shared) and os.path.exists(en)):
            continue
        ids = dict(re.findall(r"m_Id: (\d+)\n\s+m_Key: (.*)", open(shared, encoding="utf-8").read()))
        body = open(en, encoding="utf-8").read()
        for m in re.finditer(r"m_Id: (\d+)\n\s+m_Localized: (.*)", body):
            if m.group(1) in ids:
                cat.add(f"loc.{table}.{ids[m.group(1)]}", yaml.safe_load("v: " + m.group(2))["v"], table)


STR_LIT = r'\$?@?"(?:[^"\\]|\\.)*"'
_CALL = r'(?:\[[^\[\]]*\]|\([^()]*\))*'
OPERAND = r'(?:' + STR_LIT + r'|[\w.]+' + _CALL + r'(?:\.\w+' + _CALL + r')*)'
CHAIN = re.compile(OPERAND + r'(?:\s*\+\s*' + OPERAND + r')+')


def _unescape(body):
    return bytes(body, "utf-8").decode("unicode_escape", errors="ignore")


def _interpolated(lit):
    """$"Items added ({n})!" -> "Items added ({0})!" (doubled braces kept literal)."""
    body, out, n, i = lit[lit.index('"') + 1:-1], [], 0, 0
    while i < len(body):
        c = body[i]
        if body.startswith("{{", i) or body.startswith("}}", i):
            out.append(c)
            i += 2
            continue
        if c == "{":
            depth, j = 1, i + 1
            while j < len(body) and depth:
                depth += {"{": 1, "}": -1}.get(body[j], 0)
                j += 1
            out.append("{%d}" % n)
            n += 1
            i = j
            continue
        out.append(c)
        i += 1
    return _unescape("".join(out))


def _template(chain):
    """'"Fill a Tank With " + fuel.Item.Title' -> 'Fill a Tank With {0}'; None if no literal text."""
    parts = re.findall(OPERAND, chain)
    out, n, has_text = [], 0, False
    for part in parts:
        if re.fullmatch(STR_LIT, part):
            text = _interpolated(part) if part.startswith("$") else _unescape(part[part.index('"') + 1:-1])
            if part.startswith("$"):
                text = re.sub(r"\{(\d+)\}", lambda m: "{%d}" % (int(m.group(1)) + n), text)
                n += len(re.findall(r"\{\d+\}", text))
            has_text |= bool(re.search(r"[A-Za-z]{2}", re.sub(r"\{\d+\}", "", text)))
            out.append(text)
        else:
            out.append("{%d}" % n)
            n += 1
    return "".join(out) if has_text else None


# Enums whose member names the game shows with ToString(): (file under SRC, enum name or None for all enums in it).
SHOWN_ENUMS = [
    ("UpgradeType.cs", None),                       # tenement upgrade tiers (SRC/TenementUpgrade.cs:193-240)
    ("OS/Items/ItemConsumable.cs", "ConsumableType"),  # item type line (SRC/ToolTip.cs GetType)
    ("OS/Items/ItemEquipable.cs", "EquipableType"),
    ("OS/Items/ItemQualityData.cs", "Quality"),
    ("PlayerStats.cs", "PlayerSkillType"),          # skill names (SRC/PlayerSkillIncreaseUI.cs)
]


def extract_enums(src, cat):
    for rel, name in SHOWN_ENUMS:
        path = os.path.join(src, rel)
        if not os.path.exists(path):
            continue
        body = open(path, encoding="utf-8", errors="replace").read()
        for m in re.finditer(r"enum (\w+)\s*\{([^}]*)\}", body):
            if name and m.group(1) != name:
                continue
            for member in re.findall(r"^\s*(\w+)\s*(?:=\s*-?\d+)?\s*,?\s*$", m.group(2), re.M):
                if member != "None":
                    cat.add(None, member, f"SRC/{rel} enum {m.group(1)}")


def extract_csharp(src, cat):
    """String literals and composed strings passed to UI sinks in the game code (heuristic).

    Composed strings become templates: {0}, {1} ... stand for the non-literal parts, in source order.
    """
    for fn in sorted(os.listdir(src)):
        if not fn.endswith(".cs") or "DeveloperConsole" in fn:
            continue
        with open(os.path.join(src, fn), encoding="utf-8", errors="replace") as fh:
            for n, line in enumerate(fh, 1):
                if not UI_SINKS.search(line) or NOT_UI.search(line):
                    continue
                ref = f"SRC/{fn}:{n}"
                used = []
                for m in CHAIN.finditer(line):
                    if '"' not in m.group(0):
                        continue
                    t = _template(m.group(0))
                    if t:
                        cat.add(None, t, ref)
                    used.append(m.span())
                for m in re.finditer(STR_LIT, line):
                    if any(a <= m.start() < b for a, b in used):
                        continue
                    lit = m.group(0)
                    text = _interpolated(lit) if lit.startswith("$") else _unescape(lit[lit.index('"') + 1:-1])
                    if re.search(r"[A-Za-z]{2}", re.sub(r"\{\d+\}", "", text)) and not re.fullmatch(r"<[^>]*>|[\w/]+\.\w+", text.strip()):
                        cat.add(None, text, ref)


# ---------------------------------------------------------------- output

def po_escape(s):
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n\"\n\"").replace("\t", "\\t")


def write_pot(cat, path):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write('msgid ""\nmsgstr ""\n"Content-Type: text/plain; charset=UTF-8\\n"\n'
                 f'"X-Domain: {cat.name}\\n"\n\n')
        for key, e in cat.entries.items():
            for r in e["refs"]:
                fh.write(f"#: {r}\n")
            if cat.keyed:
                fh.write(f'msgctxt "{po_escape(key)}"\n')
            fh.write(f'msgid "{po_escape(e["text"])}"\nmsgstr ""\n\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ripper", default=DEFAULT_RIPPER, help="AssetRipper output folder")
    ap.add_argument("--game", default=DEFAULT_GAME, help="Obenseuer install folder")
    ap.add_argument("--out", default="source/pot", help="folder for the .pot files")
    ap.add_argument("--stats", default="source/stats.md", help="Markdown table of string and word counts")
    ap.add_argument("--jobs", type=int, default=os.cpu_count(), help="parallel workers for the scene scan")
    ap.add_argument("--only", nargs="*", help="limit to these domains (items, dialogue, ...)")
    args = ap.parse_args()

    assets = f"{args.ripper}/ExportedProject/Assets"
    src = f"{args.ripper}/ExportedAssets/Scripts/Assembly-CSharp"
    guid2cls = {}
    for root, _, files in os.walk(f"{assets}/Scripts"):
        for f in files:
            if f.endswith(".cs.meta"):
                m = re.search(r"guid: (\w+)", open(os.path.join(root, f)).read())
                if m:
                    guid2cls[m.group(1)] = f[:-8]

    keyed = ["items", "recipes", "dialogue", "actors", "tasks", "taskitems", "notes", "furniture", "tenement", "loctables"]
    cats = {n: Catalog(n, n in keyed) for n in keyed + ["world", "ui", "code"]}
    only = set(args.only or cats)

    if "items" in only:
        extract_items(args.game, cats["items"])
    if "recipes" in only:
        extract_recipes(args.game, cats["recipes"])
    if only & {"dialogue", "actors"}:
        extract_dialogue(assets, cats["dialogue"], cats["actors"])
    if only & {"tasks", "taskitems", "notes", "furniture", "tenement", "world", "ui"}:
        extract_assets(assets, src, cats, guid2cls, args.jobs)
    if "loctables" in only:
        extract_string_tables(assets, cats["loctables"])
    if "code" in only:
        extract_csharp(src, cats["code"])
        extract_enums(src, cats["code"])

    os.makedirs(args.out, exist_ok=True)
    rows = []
    for name, cat in cats.items():
        if name not in only or not cat.entries:
            continue
        write_pot(cat, os.path.join(args.out, f"{name}.pot"))
        rows.append((name, len(cat.entries), cat.words()))
    with open(args.stats, "w", encoding="utf-8") as fh:
        fh.write("| Domain | Strings | Words |\n|---|---:|---:|\n")
        for name, n, w in rows:
            fh.write(f"| {name} | {n:,} | {w:,} |\n")
        fh.write(f"| **total** | **{sum(r[1] for r in rows):,}** | **{sum(r[2] for r in rows):,}** |\n")
    print(open(args.stats).read())


if __name__ == "__main__":
    sys.exit(main())
