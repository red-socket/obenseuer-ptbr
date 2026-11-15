#!/usr/bin/env python3
"""Check translations for broken markup and report progress.

    python3 -I tools/check.py [translations/pt-BR/*.po]

For every translated entry, the Portuguese must keep the English text's {0} placeholders,
rich-text tags (<b>, <color=...>), Dialogue System codes ([var=...], [lua(...)], [em1]),
{key:Action} hint placeholders, line breaks and leading/trailing spaces, and {{m|f}} gender markers
must be well-formed. Typewriter pause codes (\\, \\.) may be moved or dropped. Exits 1 if anything is broken.
"""
import collections
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import po  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKENS = re.compile(r"\{\d+\}|\{key:[^}]+\}|<[^<>]+>|\[(?:var|lua|em\d|/em\d|pic|f|a)[^\]]*\]")
GENDER = re.compile(r"\{\{[^{}|]*\|[^{}|]*\}\}")


def problems(en, pt):
    out = []
    a, b = collections.Counter(TOKENS.findall(en)), collections.Counter(TOKENS.findall(pt))
    if a != b:
        miss, extra = a - b, b - a
        out.append("markup differs" + (f"; missing {sorted(miss)}" if miss else "") + (f"; extra {sorted(extra)}" if extra else ""))
    if pt.count("{{") != len(GENDER.findall(pt)) or pt.count("}}") != len(GENDER.findall(pt)):
        out.append("malformed {{masculine|feminine}} marker")
    if en.count("\n") != pt.count("\n"):
        out.append(f"line breaks {en.count(chr(10))} -> {pt.count(chr(10))}")
    lead = lambda s: s[:len(s) - len(s.lstrip())]
    trail = lambda s: s[len(s.rstrip()):]
    if lead(en) != lead(pt) or trail(en) != trail(pt):
        out.append("leading/trailing whitespace differs")
    return out


def main():
    files = sys.argv[1:] or sorted(glob.glob(os.path.join(ROOT, "translations", "*", "*.po")))
    bad = 0
    print(f"{'file':38s} {'total':>6s} {'done':>6s} {'fuzzy':>6s} {'empty':>6s}")
    for path in files:
        entries = po.read(path)
        total = len(entries)
        fuzzy = sum(1 for e in entries if e.msgstr and "fuzzy" in e.flags)
        done = sum(1 for e in entries if e.msgstr and "fuzzy" not in e.flags)
        for e in entries:
            if not e.msgstr:
                continue
            for p in problems(e.msgid, e.msgstr):
                bad += 1
                key = e.msgctxt or e.msgid[:40]
                print(f"  {os.path.relpath(path, ROOT)}: {key!r}: {p}", file=sys.stderr)
        print(f"{os.path.relpath(path, ROOT):38s} {total:6d} {done:6d} {fuzzy:6d} {total - done - fuzzy:6d}")
    if bad:
        print(f"{bad} problems", file=sys.stderr)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
