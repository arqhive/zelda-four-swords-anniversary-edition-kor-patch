# -*- coding: utf-8 -*-
"""UI 그래픽을 한글로 바꾼 롬을 만든다.

v1.1 그래픽 패치 위에 지도 이름판·하단 바·제목판(make_plates)과
버튼·안내 문구(btn_patch, press_patch)를 다시 그리고, 대사 글꼴을 바꾼다.

  python tools/dev/build_ui_rom.py --rom 원본.nds --font gulim --out 결과.nds
  (선택) --redo 재작업PNG폴더 --src 원본PNG폴더
"""
import argparse, json, os, re, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "tools"))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8")
from ndsrom import Rom
from kmsg import Kmsg, from_markup
from nftr import Nftr
import bps, lz, fix_digest
import make_plates as mp

EN = 1
GFX = ("subtask_us_en.cmp", "zeldat_us_en.bin", "subtask.cmp")

FONTDIR = os.path.join(REPO, "tools", "fonts")
FONTS = {
    "galmuri11": dict(ttf=os.path.join(FONTDIR, "Galmuri11.ttf"),
                      size=11, cell_w=12, advance=11, yoff=0),
    "condensed": dict(ttf=os.path.join(FONTDIR, "Galmuri11-Condensed.ttf"),
                      size=11, cell_w=10, advance=8, yoff=0),
    "gulim": dict(ttf="C:/Windows/Fonts/gulim.ttc", size=11, cell_w=10, advance=10, yoff=0, index=0),
}


def line_widths(toks, width_of):
    widths, cur = [], 0
    for t in toks:
        if isinstance(t, str):
            cur += sum(width_of(c) for c in t)
        elif t[0] == 1:
            widths.append(cur); cur = 0
    widths.append(cur)
    return widths


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rom", required=True)
    ap.add_argument("--font", required=True, choices=sorted(FONTS))
    ap.add_argument("--out", required=True)
    ap.add_argument("--redo", help="사용자가 다시 그린 PNG 폴더")
    ap.add_argument("--src", help="추출한 원본 PNG 폴더 (--redo 와 짝)")
    args = ap.parse_args()
    spec = FONTS[args.font]

    rom = Rom(args.rom)
    original = {n: rom.read(n) for n in GFX}

    # 1. v1.1 그래픽 패치
    gfx = {n: bps.apply(original[n], open(os.path.join(REPO, "patches", "gfx", n + ".bps"), "rb").read())
           for n in GFX}

    # 2. 확정한 01 이름판 · 03 제목판 (zeldat) / 02 하단 바 (subtask_us_en 3번 시트)
    gfx["zeldat_us_en.bin"] = mp.build_plates(gfx["zeldat_us_en.bin"])
    data = bytearray(lz.decompress(gfx["subtask_us_en.cmp"]))
    count = struct.unpack_from("<I", data)[0] // 4
    offsets = struct.unpack_from("<%dI" % count, data)
    off = offsets[3]
    size = struct.unpack_from("<I", data, off + 0x28)[0]
    raw = bytes(data[off + 0x30:off + 0x30 + size])
    packed = mp.sheet_pack(raw, mp.build_bars(mp.sheet_cells(raw)))
    data[off + 0x30:off + 0x30 + size] = packed
    blob = lz.compress_lz11(bytes(data))
    assert lz.decompress(blob) == bytes(data)
    # 2-b. 사용자가 다시 그린 PNG 되돌려 넣기
    import apply_png
    pals = {int(k): {int(i): tuple(c) for i, c in v.items()}
            for k, v in json.load(open(os.path.join(HERE, "pal_sub.json"), encoding="utf-8")).items()}
    data = bytearray(lz.decompress(blob))
    offsets = struct.unpack_from("<%dI" % (struct.unpack_from("<I", data)[0] // 4), data)
    sheets, meta = {}, {}
    for k in range(5):
        o = offsets[k]
        sz = struct.unpack_from("<I", data, o + 0x28)[0]
        raw2 = bytes(data[o + 0x30:o + 0x30 + sz])
        sheets[k] = mp.sheet_cells(raw2)
        meta[k] = (o, sz, raw2)
    report = []
    import press_patch
    NEO = os.path.join(FONTDIR, "neodgm.ttf")
    report.append("  시작 화면 PRESS -> 「Ⓐ 누르기」 · " + press_patch.apply(sheets[0], NEO))
    n = 1
    if args.redo and args.src:
        n += apply_png.apply_pngs(sheets, args.redo, args.src, pals, report)
    # 첫 화면 시작·도움말은 Neo둥근모(볼드 없음)로 다시 그린다 — 재작업 PNG 위에 덮어쓴다
    import btn_patch
    odata = lz.decompress(original["subtask_us_en.cmp"])
    ooffs = struct.unpack_from("<%dI" % (struct.unpack_from("<I", odata)[0] // 4), odata)
    oo = ooffs[1]
    osz = struct.unpack_from("<I", odata, oo + 0x28)[0]
    orig_sheet1 = mp.sheet_cells(bytes(odata[oo + 0x30:oo + 0x30 + osz]))
    oo0 = ooffs[0]
    osz0 = struct.unpack_from("<I", odata, oo0 + 0x28)[0]
    orig_sheet0 = mp.sheet_cells(bytes(odata[oo0 + 0x30:oo0 + 0x30 + osz0]))
    report += btn_patch.apply(orig_sheet0, sheets[0], NEO, palette=pals.get(0, {}),
                              buttons=btn_patch.SUB00)
    report += btn_patch.apply(orig_sheet1, sheets[1], NEO, palette=pals.get(1, {}))
    oo2 = ooffs[2]
    osz2 = struct.unpack_from("<I", odata, oo2 + 0x28)[0]
    orig_sheet2 = mp.sheet_cells(bytes(odata[oo2 + 0x30:oo2 + 0x30 + osz2]))
    report += btn_patch.apply(orig_sheet2, sheets[2], NEO, palette=pals.get(2, {}),
                              buttons=btn_patch.SUB02)
    if n:
        print("재작업 PNG %d개 반영" % n)
        for line in report:
            print(line)
        for k, (o, sz, raw2) in meta.items():
            data[o + 0x30:o + 0x30 + sz] = mp.sheet_pack(raw2, sheets[k])
        blob = lz.compress_lz11(bytes(data))
        assert lz.decompress(blob) == bytes(data)
    gfx["subtask_us_en.cmp"] = blob

    # 3. 대사 폰트
    font = Nftr(rom.read("font_ltn.nftr"))
    if spec["cell_w"] > font.cw:
        font.resize_cell(spec["cell_w"])
    km = Kmsg(rom.read("us.kmsg"))
    ko = json.load(open(os.path.join(REPO, "translation", "ko.json"), encoding="utf-8"))
    need = set()
    for sid, markup in ko.items():
        markup = re.sub(r"\{ruby:([^|}]*)\|[^}]*\}", r"\1", markup)
        toks = from_markup(markup)
        km.entries[int(sid)][1][EN] = toks
        need |= {ord(c) for t in toks if isinstance(t, str) for c in t}
    missing = sorted(c for c in need if c not in font.cmap)
    kw = {"index": spec["index"]} if "index" in spec else {}
    font.add_ttf_glyphs([chr(c) for c in missing], spec["ttf"], size=spec["size"],
                        yoff=spec["yoff"], advance=spec["advance"], **kw)

    def width_of(c):
        i = font.cmap.get(ord(c))
        return font.widths[i][2] if i is not None else font.cw
    limit = 232
    over = [(int(sid), n, w) for sid in sorted(ko, key=int)
            for n, w in enumerate(line_widths(km.entries[int(sid)][1][EN], width_of)) if w > limit]

    fb, kb = font.build(), km.build()
    rom.remove("all.kmsg")
    rom.replace("font_ltn.nftr", fb)
    rom.replace("us.kmsg", kb)
    for n, b in gfx.items():
        rom.replace(n, b)
    assert all(e <= rom.data_limit() for s, e in rom.fat), "파일 자료가 다이제스트 영역을 침범"
    out = bytearray(rom.data)
    fix_digest.fix(out)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    if os.path.exists(args.out):          # 직전 빌드를 _prev 로 남겨 3단 비교에 쓴다
        import shutil
        shutil.copy(args.out, os.path.splitext(args.out)[0] + "_prev.nds")
    open(args.out, "wb").write(out)
    chk = Rom(args.out)
    assert chk.read("font_ltn.nftr") == fb and chk.read("us.kmsg") == kb
    for n, b in gfx.items():
        assert chk.read(n) == b, n
    print("%s: 글리프 %d개 추가 · 셀 %d×%d · advance %d · 폰트 %d바이트" %
          (args.font, len(missing), font.cw, font.ch, spec["advance"], len(fb)))
    print("  232px 넘는 줄: %d개" % len(over))
    for sid, n, w in over[:10]:
        print("    항목 %d 줄 %d: %dpx" % (sid, n, w))
    print("  ->", args.out)


if __name__ == "__main__":
    main()
