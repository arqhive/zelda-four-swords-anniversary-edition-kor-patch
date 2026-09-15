"""KMSG (Four Swords AE) text container: parse to tokens, markup conversion, rebuild.

Slots: 0=JP (UTF-16LE), 1..8 = EN/EU languages (UTF-8). us.kmsg uses 1 (EN), 5 (FR), 7 (SP).
Control code: 0x7F, then (UTF-8 only) pad to even offset, then u16 cmd, u16 args.
JP ruby: {0x12} reading 0x0000 base {0x13}
"""
import re
import struct

LANG_SLOTS = 10
UTF16_SLOTS = {0}
# control code -> number of u16 arguments (verified by byte-exact roundtrip)
ARGS = {0: 0, 1: 0, 2: 1, 3: 1, 4: 0, 5: 1, 6: 0, 7: 1, 8: 1, 9: 1, 10: 1, 11: 1, 12: 1, 13: 3, 14: 0, 17: 1, 18: 0, 19: 0}


def parse_string(b, utf16=False):
    """Returns list of tokens: str (text) or tuple (cmd, *args)."""
    toks, text = [], []

    def flush():
        if text:
            toks.append("".join(text) if utf16 else bytes(text).decode("utf-8"))
            text.clear()

    if utf16:
        units = struct.unpack("<%dH" % (len(b) // 2), b[:len(b) // 2 * 2])
        p = 0
        while p < len(units):
            if units[p] == 0x7F:
                flush()
                cmd = units[p + 1]
                n = ARGS[cmd]
                toks.append((cmd,) + tuple(units[p + 2:p + 2 + n]))
                p += 2 + n
                if cmd == 0:
                    break
            else:
                text.append(chr(units[p])); p += 1
    else:
        p = 0
        while p < len(b):
            if b[p] == 0x7F:
                flush()
                q = p + 1
                q += q & 1
                cmd = struct.unpack_from("<H", b, q)[0]
                n = ARGS[cmd]
                toks.append((cmd,) + struct.unpack_from("<%dH" % n, b, q + 2))
                p = q + 2 + 2 * n
                if cmd == 0:
                    break
            else:
                text.append(b[p]); p += 1
    flush()
    return toks


def build_string(toks, utf16=False):
    out = bytearray()
    for t in toks:
        if isinstance(t, str):
            out += t.encode("utf-16le" if utf16 else "utf-8")
        else:
            if utf16:
                out += struct.pack("<%dH" % (len(t) + 1), 0x7F, *t)
            else:
                out.append(0x7F)
                if len(out) & 1:
                    out.append(0)
                out += struct.pack("<%dH" % len(t), *t)
    if len(out) & 1:
        out.append(0)
    return bytes(out)


class Kmsg:
    def __init__(self, data):
        self.header = data[:0x10]
        count = struct.unpack_from("<I", data, 8)[0]
        self.entries = []  # [flag, [tokens or None] * 10]
        for i in range(count):
            base = 0x10 + i * 84
            flag = struct.unpack_from("<I", data, base)[0]
            langs = []
            for j in range(LANG_SLOTS):
                o, s = struct.unpack_from("<II", data, base + 4 + j * 8)
                langs.append(parse_string(data[o:o + s], j in UTF16_SLOTS) if s else None)
            self.entries.append([flag, langs])

    def build(self):
        table = bytearray(self.header)
        body = bytearray()
        start = 0x10 + len(self.entries) * 84
        for flag, langs in self.entries:
            table += struct.pack("<I", flag)
            for j, toks in enumerate(langs):
                if toks is None:
                    table += struct.pack("<II", 0, 0)
                else:
                    s = build_string(toks, j in UTF16_SLOTS)
                    table += struct.pack("<II", start + len(body), len(s))
                    body += s
                    body += b"\x00" * (-len(body) % 4)  # strings are 4-byte aligned; size excludes pad
        return bytes(table + body)


# ---------------------------------------------------------------- markup
# Human-editable form: text with {tags}. Named tags for common codes, {cN:args} for the rest.
NAMES = {1: "br", 3: "wait", 0: "end"}
RUBY_OPEN, RUBY_CLOSE = 18, 19


def to_markup(toks):
    out, i = [], 0
    while i < len(toks):
        t = toks[i]
        if isinstance(t, str):
            out.append(t.replace("{", "{{").replace("}", "}}"))
        elif t[0] == RUBY_OPEN and i + 2 < len(toks) and isinstance(toks[i + 1], str) and toks[i + 2] == (RUBY_CLOSE,) \
                and "\x00" in toks[i + 1]:
            reading, base = toks[i + 1].split("\x00", 1)
            out.append("{ruby:%s|%s}" % (base, reading))
            i += 2
        else:
            name = NAMES.get(t[0], "c%d" % t[0])
            out.append("{%s%s}" % (name, ":" + ",".join(map(str, t[1:])) if len(t) > 1 else ""))
        i += 1
    return "".join(out)


def plain_text(toks):
    """Readable text: ruby -> base only, {br} -> newline, other codes dropped."""
    s = to_markup(toks)
    s = re.sub(r"\{ruby:([^|}]*)\|[^}]*\}", r"\1", s)
    s = s.replace("{br}", "\n")
    s = re.sub(r"(?<!\{)\{[a-z]+\d*(:[0-9,]+)?\}(?!\})", "", s)
    return s.replace("{{", "{").replace("}}", "}")


TAG = re.compile(r"\{\{|\}\}|\{(ruby):([^|}]*)\|([^}]*)\}|\{([a-z]+)(\d*)(?::([0-9,]+))?\}")
REV = {v: k for k, v in NAMES.items()}


def from_markup(s):
    toks, text, pos = [], [], 0

    def flush():
        if text:
            toks.append("".join(text)); text.clear()

    for m in TAG.finditer(s):
        text.append(s[pos:m.start()])
        pos = m.end()
        g = m.group(0)
        if g in ("{{", "}}"):
            text.append(g[0]); continue
        flush()
        if m.group(1):  # ruby (only meaningful for UTF-16 JP slot)
            toks += [(RUBY_OPEN,), m.group(3) + "\x00" + m.group(2), (RUBY_CLOSE,)]
            continue
        name, num, args = m.group(4), m.group(5), m.group(6)
        cmd = int(num) if name == "c" else REV[name]
        a = tuple(int(x) for x in args.split(",")) if args else ()
        assert len(a) == ARGS[cmd], "bad arg count in %s" % g
        toks.append((cmd,) + a)
    text.append(s[pos:])
    flush()
    return [t for t in toks if t != ""]
