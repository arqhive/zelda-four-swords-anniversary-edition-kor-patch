"""지도 이름판 7종 · 하단 바 7종 · 스테이지 선택 제목을 확정 사양대로 다시 그린다.

확정 사양(2026-10-03):
  공통   글자 속 팔레트 1번, 외곽선 13번(흰색) 8방향 1px
  이름판 바탕 단색 9번, 갈무리9 10pt, 중심 x=59 y=8, 바탕은 x<=117 에만
  하단바 바탕 단색 9번, 갈무리9 10pt, 중심 x=67 y=8, 바탕은 x=6~127 에만
  제목판 원본 그라데이션 복원(x=96~239), Neo둥근모 16pt 자간 2px, 중심 x=168 y=9

원본 롬만 있으면 결과를 그대로 재현한다. 글꼴은 tools/fonts 에 있다.
"""
import argparse
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ndsrom import Rom
import lz
from polish_graphics import unpack4, pack4, zentries, rawentry, zpack, MAP_LAYOUT

FONTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts")
GALMURI9 = os.path.join(FONTS, "Galmuri9.ttf")
NEODGM = os.path.join(FONTS, "neodgm.ttf")
FILL, OUTLINE = 1, 13

PLATE_PROFILE = [12, 13] + [9] * 11 + [11, 3, 4]
# 판 오른쪽 끝은 x=117 에서 그림자(x=118~119)로 넘어간다. 그 전환 열을 단색으로 덮으면
# 판 아래 선이 x=117 에서 뚝 끊겨 보인다. 원본(수련장 판)의 전환 열을 그대로 쓴다.
PLATE_EDGE_X = 117
PLATE_EDGE = [12, 13, 8, 12, 12, 8, 8, 9, 9, 9, 9, 10, 10, 9, 4, 4]
BAR_PROFILE = [12, 13, 8, 8] + [9] * 9 + [11, 2, 4]
TITLE_PROFILE = [7, 7, 7] + [8] * 7 + [11] * 7 + [12, 8, 13, 4, 5, 1, 0]

PLATES = [(2, "시작의 사당"), (3, "바위산 동굴"), (4, "돌아올 수 없는 숲"), (5, "바람의 궁전"),
          (6, "데스마운틴"), (8, "추억의 대지"), (9, "수련장")]
BARS = [(128, 32, "시작의 사당"), (128, 48, "돌아올 수 없는 숲"), (128, 64, "데스마운틴"),
        (128, 80, "추억의 대지"), (0, 48, "바위산 동굴"), (0, 64, "바람의 궁전"), (0, 80, "수련장")]


def glyph(text, path, size, spacing=0):
    """글자 픽셀 좌표 집합과 크기. 안티앨리어싱 없이 글자별로 이어 붙인다."""
    font = ImageFont.truetype(path, size)
    points, pen = set(), 0
    for ch in text:
        left, top, right, bottom = font.getbbox(ch)
        im = Image.new("1", (right + 4, bottom + 4))
        draw = ImageDraw.Draw(im)
        draw.fontmode = "1"
        draw.text((2, 2), ch, font=font, fill=1)
        pixels = im.load()
        for y in range(im.height):
            for x in range(im.width):
                if pixels[x, y]:
                    points.add((pen + x, y))
        pen += int(font.getlength(ch)) + spacing
    x0 = min(p[0] for p in points)
    y0 = min(p[1] for p in points)
    w = max(p[0] for p in points) - x0 + 1
    h = max(p[1] for p in points) - y0 + 1
    return {(x - x0, y - y0) for x, y in points}, w, h


def write_text(cells, text, path, size, spacing, cx, cy, ylimit):
    points, w, h = glyph(text, path, size, spacing)
    ox, oy = cx - w // 2, cy - h // 2
    placed = {(x + ox, y + oy) for x, y in points}
    for x, y in placed:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                key = (x + dx, y + dy)
                if key in cells and ylimit[0] <= key[1] <= ylimit[1] and cells[key] != 0:
                    cells[key] = OUTLINE
    for key in placed:
        if key in cells:
            cells[key] = FILL
    return w, h


def plate_cells(raw):
    pixels = unpack4(raw)
    return {(bx + x, by + y): pixels[t * 64 + y * 8 + x]
            for (bx, by), t in MAP_LAYOUT.items() for y in range(8) for x in range(8)}


def plate_pack(raw, cells):
    pixels = unpack4(raw)
    for (bx, by), t in MAP_LAYOUT.items():
        for y in range(8):
            for x in range(8):
                pixels[t * 64 + y * 8 + x] = cells[(bx + x, by + y)]
    return pack4(pixels)


def sheet_cells(raw, width=256):
    pixels = unpack4(raw)
    cols = width // 8
    return {(t % cols * 8 + j % 8, t // cols * 8 + j // 8): pixels[t * 64 + j]
            for t in range(len(pixels) // 64) for j in range(64)}


def sheet_pack(raw, cells, width=256):
    pixels = unpack4(raw)
    cols = width // 8
    for t in range(len(pixels) // 64):
        for j in range(64):
            pixels[t * 64 + j] = cells[(t % cols * 8 + j % 8, t // cols * 8 + j // 8)]
    return pack4(pixels)


def build_plates(zeldat):
    """zeldat_us_en.bin 의 지도 이름판 7종과 제목판을 다시 그린 blob 을 돌려준다."""
    entries = zentries(zeldat)
    for index, text in PLATES:
        raw = rawentry(entries[index])
        cells = plate_cells(raw)
        for key in cells:
            if key[0] <= PLATE_EDGE_X:
                cells[key] = PLATE_PROFILE[key[1]]
        write_text(cells, text, GALMURI9, 10, 0, 59, 8, (1, 13))
        blob = lz.compress_lz11(plate_pack(raw, cells))
        assert lz.decompress(blob) == plate_pack(raw, cells)
        entries[index] = (blob, True)
    # 제목판
    raw = rawentry(entries[7])
    cells = sheet_cells(raw)
    for key in cells:
        if 96 <= key[0] <= 239:
            cells[key] = TITLE_PROFILE[key[1]]
    write_text(cells, "스테이지 선택", NEODGM, 16, 2, 168, 9, (2, 18))
    blob = lz.compress_lz11(sheet_pack(raw, cells))
    assert lz.decompress(blob) == sheet_pack(raw, cells)
    entries[7] = (blob, True)
    return zpack(entries)


def build_bars(cells):
    """subtask_us_en.cmp 3번 시트 셀을 받아 하단 바 7종을 다시 그린다."""
    for bx, by, text in BARS:
        for y in range(16):
            for x in range(128):
                if 6 <= x <= 127 and cells[(bx + x, by + y)] != 0:
                    cells[(bx + x, by + y)] = BAR_PROFILE[y]
        local = {(x, y): cells[(bx + x, by + y)] for y in range(16) for x in range(128)}
        write_text(local, text, GALMURI9, 10, 0, 67, 8, (1, 13))
        for (x, y), v in local.items():
            cells[(bx + x, by + y)] = v
    return cells


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rom", required=True, help="원본 복호화 DSiWare SRL (00000000)")
    ap.add_argument("--out", required=True, help="결과를 넣을 폴더")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    rom = Rom(args.rom)

    zeldat = build_plates(rom.read("zeldat_us_en.bin"))
    open(os.path.join(args.out, "zeldat_us_en.bin"), "wb").write(zeldat)
    print("zeldat_us_en.bin %d bytes (지도 이름판 7종 + 제목판)" % len(zeldat))

    import struct
    data = bytearray(lz.decompress(rom.read("subtask_us_en.cmp")))
    count = struct.unpack_from("<I", data)[0] // 4
    offsets = struct.unpack_from("<%dI" % count, data)
    off = offsets[3]
    size = struct.unpack_from("<I", data, off + 0x28)[0]
    raw = bytes(data[off + 0x30:off + 0x30 + size])
    packed = sheet_pack(raw, build_bars(sheet_cells(raw)))
    data[off + 0x30:off + 0x30 + size] = packed
    blob = lz.compress_lz11(bytes(data))
    assert lz.decompress(blob) == bytes(data)
    open(os.path.join(args.out, "subtask_us_en.cmp"), "wb").write(blob)
    print("subtask_us_en.cmp %d bytes (하단 바 7종)" % len(blob))


if __name__ == "__main__":
    main()
