#!/usr/bin/env python3
"""Move strings between the .pot/.po files and JSONL batches for drafting.

    # unique untranslated English strings of some domains -> JSONL batches of N lines
    python3 -I tools/batch.py export --domains items recipes --size 600 --out /tmp/batches

    # drafted batches ({"id", "pt"} per line) -> translations/pt-BR/<domain>.po, marked fuzzy
    python3 -I tools/batch.py import /tmp/batches/*.out.jsonl

Export de-duplicates by English text within the requested domains, so "Egg" (seven item IDs) is
translated once. Import fills every entry with that English text, keeps translations that already
exist, and marks new ones fuzzy ("needs review" in Poedit). Each batch line carries the English,
the domain, the entry keys and a few source references as context.
"""
import argparse
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import po  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def cmd_export(args):
    os.makedirs(args.out, exist_ok=True)
    groups = {}  # English -> line
    for domain in args.domains:
        pot = po.read(os.path.join(ROOT, "source/pot", f"{domain}.pot"))
        done = po.index(po.read_if_exists(os.path.join(ROOT, "translations", args.lang, f"{domain}.po")))
        for e in pot:
            if not e.msgid or (e.msgctxt, e.msgid) in done:
                continue
            g = groups.setdefault(e.msgid, {"en": e.msgid, "domains": [], "keys": [], "refs": []})
            if domain not in g["domains"]:
                g["domains"].append(domain)
            if e.msgctxt and len(g["keys"]) < 4:
                g["keys"].append(e.msgctxt)
            for r in e.refs:
                if len(g["refs"]) < 3 and r not in g["refs"]:
                    g["refs"].append(r)
    lines = list(groups.values())
    if args.only_keys:
        rx = re.compile(args.only_keys)
        lines = [l for l in lines if any(rx.search(k) for k in l["keys"])]
    if args.exclude_keys:
        rx = re.compile(args.exclude_keys)
        lines = [l for l in lines if not l["keys"] or not all(rx.search(k) for k in l["keys"])]
    if args.sort:
        lines.sort(key=lambda l: l["en"].lower())
    for i, line in enumerate(lines):
        line["id"] = i
    if args.context:
        with open(args.context, encoding="utf-8") as fh:
            ctx = json.load(fh)
        for line in lines:
            for k in line["keys"]:
                c = ctx.get(k.rsplit(".", 1)[0])
                if c:
                    line.update({"speaker": c["speaker"], "to": c["to"]})
                    break
    chunks, cur, words, last = [], [], 0, None
    for line in lines:
        group = line["refs"][0] if line["refs"] else None
        full = len(cur) >= args.size or (args.words and words >= args.words)
        if cur and full and (not args.words or group != last):
            chunks.append(cur)
            cur, words = [], 0
        cur.append(line)
        words += len(line["en"].split())
        last = group
    if cur:
        chunks.append(cur)
    n = 0
    for chunk in chunks:
        n += 1
        path = os.path.join(args.out, f"{args.prefix}{n:02d}.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            for line in chunk:
                fh.write(json.dumps(line, ensure_ascii=False) + "\n")
    with open(os.path.join(args.out, f"{args.prefix}index.json"), "w", encoding="utf-8") as fh:
        json.dump({"domains": args.domains, "lang": args.lang, "count": len(lines)}, fh)
    print(f"{len(lines)} unique strings from {', '.join(args.domains)} -> {n} batches in {args.out}")


def cmd_import(args):
    drafts = {}  # English -> Portuguese
    for pattern in args.files:
        for path in sorted(glob.glob(pattern)):
            src = path.replace(".out.jsonl", ".jsonl")
            english = {}
            with open(src, encoding="utf-8") as fh:
                for raw in fh:
                    line = json.loads(raw)
                    english[line["id"]] = line
            with open(path, encoding="utf-8") as fh:
                for n, raw in enumerate(fh, 1):
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        out = json.loads(raw)
                    except json.JSONDecodeError as e:
                        print(f"{path}:{n}: bad JSON ({e})", file=sys.stderr)
                        continue
                    src_line = english.get(out.get("id"))
                    if src_line is None or not out.get("pt"):
                        continue
                    drafts[src_line["en"]] = out["pt"]
                    for d in src_line["domains"]:
                        domains_seen.add(d)
    for domain in sorted(domains_seen):
        pot = po.read(os.path.join(ROOT, "source/pot", f"{domain}.pot"))
        po_path = os.path.join(ROOT, "translations", args.lang, f"{domain}.po")
        existing = po.index(po.read_if_exists(po_path))
        out, added = [], 0
        for e in pot:
            if not e.msgid:
                continue
            old = existing.get((e.msgctxt, e.msgid))
            if old is not None and old.msgstr:
                e.msgstr, e.flags, e.comments = old.msgstr, old.flags, old.comments
            elif e.msgid in drafts:
                e.msgstr = drafts[e.msgid]
                e.flags = sorted(set(e.flags) | {"fuzzy"})
                added += 1
            out.append(e)
        keys = {e.key for e in out}
        extra = [e for k, e in existing.items() if k not in keys and e.msgstr]  # hand-added entries
        po.write(po_path, out + extra, lang=args.lang)
        print(f"{domain}: {added} drafts added -> {os.path.relpath(po_path, ROOT)}")


domains_seen = set()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    ex = sub.add_parser("export")
    ex.add_argument("--domains", nargs="+", required=True)
    ex.add_argument("--size", type=int, default=100000)
    ex.add_argument("--out", required=True)
    ex.add_argument("--prefix", default="batch")
    ex.add_argument("--lang", default="pt-BR")
    ex.add_argument("--words", type=int, help="cut batches at about this many English words, only between groups (first ref)")
    ex.add_argument("--context", help="dialogue-context.json: adds speaker/to to dialogue lines")
    ex.add_argument("--sort", action="store_true", help="sort by English so similar strings share a batch")
    ex.add_argument("--only-keys", help="regex: keep strings with a key matching it")
    ex.add_argument("--exclude-keys", help="regex: drop strings whose keys all match it")
    im = sub.add_parser("import")
    im.add_argument("files", nargs="+", help="*.out.jsonl files (the source .jsonl must sit next to each)")
    im.add_argument("--lang", default="pt-BR")
    args = ap.parse_args()
    return cmd_export(args) if args.cmd == "export" else cmd_import(args)


if __name__ == "__main__":
    sys.exit(main())
