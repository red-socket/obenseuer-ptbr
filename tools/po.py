"""Minimal gettext .po/.pot reader and writer (no plural forms, which this project doesn't use)."""
import os
import re


class Entry:
    __slots__ = ("msgctxt", "msgid", "msgstr", "flags", "refs", "comments", "extracted")

    def __init__(self):
        self.msgctxt, self.msgid, self.msgstr = None, "", ""
        self.flags, self.refs, self.comments, self.extracted = [], [], [], []

    @property
    def key(self):
        return (self.msgctxt, self.msgid)


def _unquote(s):
    s = s.strip()
    if len(s) < 2 or s[0] != '"' or s[-1] != '"':
        return ""
    out, i, body = [], 0, s[1:-1]
    while i < len(body):
        c = body[i]
        if c == "\\" and i + 1 < len(body):
            n = body[i + 1]
            out.append({"n": "\n", "t": "\t", "r": "\r"}.get(n, n))
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def read(path):
    entries, e, field = [], Entry(), None

    def commit():
        nonlocal e, field
        if field is not None:
            entries.append(e)
        e, field = Entry(), None

    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if not line.strip():
                commit()
                continue
            if line.startswith("#~"):
                continue
            if line.startswith("#"):
                if field == "msgstr":
                    commit()
                if line.startswith("#,"):
                    e.flags += [f.strip() for f in line[2:].split(",") if f.strip()]
                elif line.startswith("#:"):
                    e.refs.append(line[2:].strip())
                elif line.startswith("#."):
                    e.extracted.append(line[2:].strip())
                elif line.startswith("#|"):
                    pass
                else:
                    e.comments.append(line[1:].strip())
                continue
            if line.startswith('"'):
                setattr(e, field, getattr(e, field) + _unquote(line))
                continue
            kw, _, rest = line.partition(" ")
            if kw in ("msgctxt", "msgid") and field == "msgstr":
                commit()
            if kw in ("msgctxt", "msgid", "msgstr"):
                field = kw
                setattr(e, kw, _unquote(rest))
    commit()
    return [x for x in entries if x.msgid != "" or x.msgctxt is not None]


def read_if_exists(path):
    return read(path) if os.path.exists(path) else []


def index(entries):
    return {e.key: e for e in entries}


def _quote(s):
    s = s.replace("\\", "\\\\").replace('"', '\\"').replace("\t", "\\t").replace("\r", "\\r")
    if "\n" not in s:
        return f'"{s}"'
    parts = re.split(r"(?<=\n)", s)
    return '""\n' + "\n".join('"' + p.replace("\n", "\\n") + '"' for p in parts if p)


def write(path, entries, lang="pt-BR"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write('msgid ""\nmsgstr ""\n'
                 '"Project-Id-Version: Obenseuer PT-BR\\n"\n'
                 f'"Language: {lang.replace("-", "_")}\\n"\n'
                 '"MIME-Version: 1.0\\n"\n'
                 '"Content-Type: text/plain; charset=UTF-8\\n"\n'
                 '"Content-Transfer-Encoding: 8bit\\n"\n\n')
        for e in entries:
            for c in e.comments:
                fh.write(f"# {c}\n")
            for c in e.extracted:
                fh.write(f"#. {c}\n")
            for r in e.refs:
                fh.write(f"#: {r}\n")
            if e.flags:
                fh.write("#, " + ", ".join(e.flags) + "\n")
            if e.msgctxt is not None:
                fh.write(f"msgctxt {_quote(e.msgctxt)}\n")
            fh.write(f"msgid {_quote(e.msgid)}\nmsgstr {_quote(e.msgstr)}\n\n")
