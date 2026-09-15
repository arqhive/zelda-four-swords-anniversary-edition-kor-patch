"""Build the Korean ROM.

Usage:
  python tools/build_ko.py --rom path/to/00000000 [--out work/KQ9E_ko.nds] [--gfx patches|none|DIR]

Steps: translation/ko.json -> us.kmsg EN slot, missing glyphs added to font_ltn.nftr (gulim 11px in the 10px cell),
Korean graphics applied (patches/gfx/*.bps by default), all.kmsg emptied for space, files placed,
DSi digests recomputed, result verified. Reports lines wider than the widest original English line.

ko.json: {"<id>": "<markup>"} - Korean text with the same tags as the JP/EN markup ({br}, {wait:N}, {c2:N}, ...).
Ruby tags are reduced to their base text. Entries missing from ko.json keep the English text.
"""
import argparse, json, os, re, sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ndsrom import Rom
from kmsg import Kmsg, from_markup
from nftr import Nftr
import bps
import fix_digest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KO = os.path.join(REPO, "translation", "ko.json")
GFX_PATCHES = os.path.join(REPO, "patches", "gfx")
GFX_FILES = ("subtask_us_en.cmp", "zeldat_us_en.bin")
EN = 1
GULIM = os.environ.get("GULIM_TTC", "C:/Windows/Fonts/gulim.ttc")


def line_widths(toks, width_of):
    """Pixel widths of each displayed line (split on {br})."""
    widths, cur = [], 0
    for t in toks:
        if isinstance(t, str):
            cur += sum(width_of(c) for c in t)
        elif t[0] == 1:
            widths.append(cur); cur = 0
    widths.append(cur)
    return widths


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rom", required=True, help="original decrypted DSiWare SRL (NUS content 00000000)")
    ap.add_argument("--out", default=os.path.join(REPO, "work", "KQ9E_ko.nds"))
    ap.add_argument("--gfx", default="patches",
                    help="'patches' = apply patches/gfx/*.bps, 'none' = keep English graphics, or a directory with patched files")
    args = ap.parse_args()

    rom = Rom(args.rom)
    km = Kmsg(rom.read("us.kmsg"))
    ko = json.load(open(KO, encoding="utf-8"))

    font = Nftr(rom.read("font_ltn.nftr"))
    orig_font_chars = set(font.cmap)

    def width_of(c):
        idx = font.cmap.get(ord(c))
        return font.widths[idx][2] if idx is not None else font.cw

    # widest original English line = message box limit
    limit = max(w for _, langs in km.entries if langs[EN] for w in line_widths(langs[EN], width_of))

    needed = set()
    for sid, markup in ko.items():
        markup = re.sub(r"\{ruby:([^|}]*)\|[^}]*\}", r"\1", markup)
        toks = from_markup(markup)
        assert toks and toks[-1] == (0,), "entry %s must end with {end}" % sid
        km.entries[int(sid)][1][EN] = toks
        needed |= {ord(c) for t in toks if isinstance(t, str) for c in t}

    missing = sorted(c for c in needed if c not in orig_font_chars)
    font.add_ttf_glyphs([chr(c) for c in missing], GULIM, size=11, yoff=0, advance=10)

    over = []
    for sid in sorted(ko, key=int):
        for n, w in enumerate(line_widths(km.entries[int(sid)][1][EN], width_of)):
            if w > limit:
                over.append((int(sid), n, w))

    # graphics
    gfx = {}
    for gname in GFX_FILES:
        if args.gfx == "none":
            break
        if args.gfx == "patches":
            gfx[gname] = bps.apply(rom.read(gname), open(os.path.join(GFX_PATCHES, gname + ".bps"), "rb").read())
        else:
            gfx[gname] = open(os.path.join(args.gfx, gname), "rb").read()

    fb, kb = font.build(), km.build()
    rom.remove("all.kmsg")
    rom.replace("font_ltn.nftr", fb)
    rom.replace("us.kmsg", kb)
    placed = {"font_ltn.nftr": fb, "us.kmsg": kb}
    for gname, blob in gfx.items():
        rom.replace(gname, blob)
        placed[gname] = blob
        print("graphics replaced: %s (%d bytes)" % (gname, len(blob)))
    assert all(e <= rom.data_limit() for s, e in rom.fat), "file data overlaps digest tables"

    data = bytearray(rom.data)
    fix_digest.fix(data)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    open(args.out, "wb").write(data)
    chk = Rom(args.out)
    for pname, blob in placed.items():
        assert chk.read(pname) == blob, pname + " corrupted"

    print("translated entries: %d / %d" % (len(ko), len(km.entries)))
    print("glyphs added: %d  font %d bytes  kmsg %d bytes" % (len(missing), len(fb), len(kb)))
    print("line width limit %dpx; lines over limit: %d" % (limit, len(over)))
    for sid, n, w in over[:40]:
        print("  entry %d line %d: %dpx" % (sid, n, w))
    print("wrote", args.out)


if __name__ == "__main__":
    main()
