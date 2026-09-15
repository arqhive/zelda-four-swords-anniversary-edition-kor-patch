"""Locate screenshot graphics in language-specific tile data.

For every 8x8 block of a 1x screenshot (all 8x8 grid alignments), the colour layout is normalised
(colours renumbered by first appearance) and looked up among all tiles (with h/v flips) of:
  subtask_us_en.cmp NCGR 0-4 (4bpp) and zeldat_us_en.bin entries (4bpp and 8bpp views).
Blocks with fewer than 3 colours are ignored (too ambiguous).

Output: extract/gfx/match/<shot>_hits.png (hits outlined, colour per source) + hits.json
"""
import glob, json, os, struct, sys
from collections import defaultdict
from PIL import Image, ImageDraw
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # tools/ (lz, ndsrom)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# local work data (extracted graphics, screenshots) - not part of the repository
BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "work")
GFX = os.path.join(BASE, "extract", "gfx")
OUT = os.path.join(GFX, "match")
os.makedirs(OUT, exist_ok=True)


def norm(pix):
    m, out = {}, []
    for v in pix:
        if v not in m:
            m[v] = len(m)
        out.append(m[v])
    return tuple(out), len(m)


def tiles_from_4bpp(data):
    px = [v for b in data for v in (b & 15, b >> 4)]
    return [px[i * 64:(i + 1) * 64] for i in range(len(px) // 64)]


def tiles_from_8bpp(data):
    return [list(data[i * 64:(i + 1) * 64]) for i in range(len(data) // 64)]


def flips(t):
    rows = [t[y * 8:(y + 1) * 8] for y in range(8)]
    h = [v for r in rows for v in r[::-1]]
    v = [x for r in rows[::-1] for x in r]
    hv = [x for r in rows[::-1] for x in r[::-1]]
    return {"": t, "h": h, "v": v, "hv": hv}


def load_sources(base=None):
    """Tile sources from the extracted originals, or from patched files in `base`
    (subtask_us_en.cmp + zeldat_us_en.bin as written by gfx_patch.py)."""
    src = {}
    if base:
        import lz
        dec = lz.decompress(open(os.path.join(base, "subtask_us_en.cmp"), "rb").read())
        n = struct.unpack_from("<I", dec, 0)[0] // 4
        offs = struct.unpack_from("<%dI" % n, dec, 0)
        for k in range(5):
            o = offs[k]
            dsize = struct.unpack_from("<I", dec, o + 0x28)[0]
            src["sub%02d" % k] = tiles_from_4bpp(dec[o + 0x30:o + 0x30 + dsize])
        z = open(os.path.join(base, "zeldat_us_en.bin"), "rb").read()
        n = struct.unpack_from("<I", z, 0)[0] // 8
        for i in range(n):
            off, size = struct.unpack_from("<II", z, i * 8)
            blob = z[off:off + (size & 0x7FFFFFFF)]
            data = lz.decompress(blob) if size & 0x80000000 else blob
            src["zel%02d_4" % i] = tiles_from_4bpp(data)
            src["zel%02d_8" % i] = tiles_from_8bpp(data)
    else:
        for k in range(5):
            b = open(os.path.join(GFX, "subtask_us_en", "%02d_RGCN.bin" % k), "rb").read()
            dsize = struct.unpack_from("<I", b, 0x28)[0]
            src["sub%02d" % k] = tiles_from_4bpp(b[0x30:0x30 + dsize])
        for f in sorted(glob.glob(os.path.join(GFX, "zeldat_us_en", "*.bin"))):
            i = os.path.basename(f)[:2]
            data = open(f, "rb").read()
            src["zel%s_4" % i] = tiles_from_4bpp(data)
            src["zel%s_8" % i] = tiles_from_8bpp(data)
    index = defaultdict(list)
    for name, tiles in src.items():
        for ti, t in enumerate(tiles):
            for fl, ft in flips(t).items():
                key, ncol = norm(ft)
                if ncol >= 3:
                    index[key].append((name, ti, fl))
    return src, index


def main():
    src, index = load_sources()
    print("tile index built:", sum(len(v) for v in index.values()), "entries")
    palette = {}
    results = {}
    for shot in sorted(glob.glob(os.path.join(BASE, "screens", "*.png"))):
        im = Image.open(shot).convert("RGB")
        W, H = im.size
        px = im.load()
        hits = []
        for oy in range(8):
            for ox in range(8):
                for by in range(oy, H - 7, 8):
                    for bx in range(ox, W - 7, 8):
                        block = [px[bx + x, by + y] for y in range(8) for x in range(8)]
                        key, ncol = norm(block)
                        if ncol < 3 or key not in index:
                            continue
                        cands = index[key]
                        names = {c[0] for c in cands}
                        if len(cands) > 6:  # generic pattern, skip
                            continue
                        hits.append({"x": bx, "y": by, "cands": cands})
        results[os.path.basename(shot)] = hits
        vis = im.resize((W * 3, H * 3), Image.NEAREST)
        dr = ImageDraw.Draw(vis)
        for h in hits:
            name = h["cands"][0][0]
            col = palette.setdefault(name[:5], [(255, 0, 0), (0, 255, 0), (0, 128, 255), (255, 0, 255),
                                               (255, 160, 0), (0, 255, 255), (255, 255, 0)][len(palette) % 7])
            dr.rectangle([h["x"] * 3, h["y"] * 3, (h["x"] + 8) * 3 - 1, (h["y"] + 8) * 3 - 1], outline=col)
        tag = "shot%02d" % len(results)
        vis.save(os.path.join(OUT, tag + "_hits.png"))
        by_src = defaultdict(int)
        for h in hits:
            for n in {c[0] for c in h["cands"]}:
                by_src[n] += 1
        print("%s %-32s hits %4d  by source %s" % (tag, os.path.basename(shot), len(hits), dict(sorted(by_src.items(), key=lambda x: -x[1]))))
    json.dump(results, open(os.path.join(OUT, "hits.json"), "w"), ensure_ascii=False)
    print("legend:", {k: v for k, v in palette.items()})


if __name__ == "__main__":
    main()
