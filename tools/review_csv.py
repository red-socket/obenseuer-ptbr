#!/usr/bin/env python3
"""Review the translation in a spreadsheet: export every entry to one CSV, edit it, import it back.

    python3 -I tools/review_csv.py export            # -> review/pt-BR.csv
    python3 -I tools/review_csv.py import            # review/pt-BR.csv -> translations/pt-BR/*.po

Columns: file, key, english, portuguese, reviewed, note, context.
- Edit "portuguese" to change a translation.
- Put "x" (or sim/yes) in "reviewed" to approve a line; that clears its fuzzy flag. Clearing the
  column marks the line fuzzy (needs review) again.
- "note" is kept as a translator comment in the .po file.
- Rows are matched on file + key + english; rows whose English no longer exists are reported and skipped.
The CSV is UTF-8 with a BOM so Excel and LibreOffice open accents correctly. Open it with every column
typed as text, so values like "+20" or "1/2" are not turned into formulas or dates.
"""
import argparse
import csv
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import po  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COLUMNS = ["file", "key", "english", "portuguese", "reviewed", "note", "context"]
YES = {"x", "sim", "s", "yes", "y", "1", "true", "ok"}
NOTE_PREFIX = "review: "


def po_files(lang):
    return sorted(glob.glob(os.path.join(ROOT, "translations", lang, "*.po")))


def cmd_export(args):
    os.makedirs(os.path.dirname(args.csv), exist_ok=True)
    rows = 0
    with open(args.csv, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(COLUMNS)
        for path in po_files(args.lang):
            name = os.path.basename(path)[:-3]
            for e in po.read(path):
                note = next((c[len(NOTE_PREFIX):] for c in e.comments if c.startswith(NOTE_PREFIX)), "")
                w.writerow([name, e.msgctxt or "", e.msgid, e.msgstr,
                            "" if "fuzzy" in e.flags or not e.msgstr else "x", note, " | ".join(e.refs[:3])])
                rows += 1
    print(f"{rows} rows -> {os.path.relpath(args.csv, ROOT)}")


def cmd_import(args):
    with open(args.csv, encoding="utf-8-sig", newline="") as fh:
        table = {(r["file"], r["key"] or None, r["english"]): r for r in csv.DictReader(fh)}
    used, changed, approved = set(), 0, 0
    for path in po_files(args.lang):
        name = os.path.basename(path)[:-3]
        entries, dirty = po.read(path), False
        for e in entries:
            r = table.get((name, e.msgctxt, e.msgid))
            if r is None:
                continue
            used.add((name, e.msgctxt, e.msgid))
            pt = r["portuguese"]
            reviewed = r["reviewed"].strip().lower() in YES and bool(pt)
            flags = [f for f in e.flags if f != "fuzzy"] + ([] if reviewed or not pt else ["fuzzy"])
            comments = [c for c in e.comments if not c.startswith(NOTE_PREFIX)]
            if r["note"].strip():
                comments.append(NOTE_PREFIX + r["note"].strip().replace("\n", " "))
            if pt != e.msgstr:
                changed += 1
            if reviewed and "fuzzy" in e.flags:
                approved += 1
            if (pt, flags, comments) != (e.msgstr, e.flags, e.comments):
                e.msgstr, e.flags, e.comments, dirty = pt, flags, comments, True
        if dirty:
            po.write(path, entries, lang=args.lang)
    missing = [k for k in table if k not in used]
    for k in missing[:20]:
        print(f"not found (English changed or row edited?): {k[0]} {k[1] or ''} {k[2][:60]!r}", file=sys.stderr)
    print(f"{changed} translations changed, {approved} lines approved, {len(missing)} rows not matched")
    print("Run tools/check.py to verify placeholders and tags.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["export", "import"])
    ap.add_argument("--lang", default="pt-BR")
    ap.add_argument("--csv", help="CSV path (default review/<lang>.csv)")
    args = ap.parse_args()
    args.csv = args.csv or os.path.join(ROOT, "review", f"{args.lang}.csv")
    return cmd_export(args) if args.cmd == "export" else cmd_import(args)


if __name__ == "__main__":
    sys.exit(main())
