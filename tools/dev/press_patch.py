# -*- coding: utf-8 -*-
"""시작 화면 PRESS + A 버튼 -> 「Ⓐ 누르기」.

A 기호(실측 x=94~109, y=16~31)를 왼쪽으로 옮기고 그 오른쪽 4px 떨어진 자리에 글자를 둔다.
둘을 한 덩어리로 원본 PRESS+기호 범위(x=35~110)의 가운데에 놓는다.
글자 속은 원본 PRESS 와 같은 세로 그라데이션, 테두리는 1번.
"""
import os
from PIL import Image, ImageDraw, ImageFont

TEXT_X, TEXT_Y = (35, 90), (18, 31)
ICON_X, ICON_Y = (94, 110), (16, 32)
FULL = (35, 110)
GRAD = {19: 11, 20: 11, 21: 11, 22: 10, 23: 10, 24: 9, 25: 9,
        26: 8, 27: 8, 28: 7, 29: 7, 30: 1}
EDGE = 1
GAP = 4


def glyph(text, path, size, sp=0):
    f = ImageFont.truetype(path, size)
    pts, pen = set(), 0
    for ch in text:
        l, t, r, b = f.getbbox(ch)
        im = Image.new('1', (r + 4, b + 4))
        d = ImageDraw.Draw(im)
        d.fontmode = '1'
        d.text((2, 2), ch, font=f, fill=1)
        p = im.load()
        for y in range(im.height):
            for x in range(im.width):
                if p[x, y]:
                    pts.add((pen + x, y))
        pen += int(f.getlength(ch)) + sp
    x0 = min(q[0] for q in pts); y0 = min(q[1] for q in pts)
    w = max(q[0] for q in pts) - x0 + 1
    h = max(q[1] for q in pts) - y0 + 1
    return {(x - x0, y - y0) for x, y in pts}, w, h


def apply(cells, font_path, text="누르기", size=16, gap=GAP, cy=24):
    """시트 0의 셀 딕셔너리를 제자리에서 고친다."""
    icon = {(x - ICON_X[0], y - ICON_Y[0]): cells[(x, y)]
            for y in range(*ICON_Y) for x in range(*ICON_X)}
    for y in range(TEXT_Y[0], TEXT_Y[1] + 1):
        for x in range(TEXT_X[0], TEXT_X[1] + 1):
            cells[(x, y)] = 0
    for y in range(*ICON_Y):
        for x in range(*ICON_X):
            cells[(x, y)] = 0
    iw = ICON_X[1] - ICON_X[0]
    pts, w, h = glyph(text, font_path, size)
    left = FULL[0] + (FULL[1] - FULL[0] + 1 - (iw + gap + w)) // 2
    for (dx, dy), v in icon.items():
        k = (left + dx, ICON_Y[0] + dy)
        if k in cells and v:
            cells[k] = v
    ox, oy = left + iw + gap, cy - h // 2
    placed = {(x + ox, y + oy) for x, y in pts}
    for x, y in placed:
        for ddx in (-1, 0, 1):
            for ddy in (-1, 0, 1):
                k = (x + ddx, y + ddy)
                if k in cells and k not in placed and TEXT_Y[0] <= k[1] <= TEXT_Y[1]:
                    cells[k] = EDGE
    for k in placed:
        if k in cells:
            cells[k] = GRAD.get(k[1], 9)
    return "글자 %d×%dpx · 기호 x=%d~%d · 글자 x=%d~%d" % (w, h, left, left + iw - 1, ox, ox + w - 1)
