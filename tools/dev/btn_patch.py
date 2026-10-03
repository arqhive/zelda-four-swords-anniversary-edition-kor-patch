# -*- coding: utf-8 -*-
"""버튼·안내 문구를 한글로 다시 그린다.

영역(x0,x1,y0,y1)은 배경 세로 프로파일을 재는 범위이고,
실제로 지우고 그리는 곳은 opts 의 ex/ey(원본 글자가 있던 칸)로만 한정한다.
영역 전체를 덮으면 그 안의 아이콘·버튼 모서리·옆 판까지 지워진다.
"""
from collections import Counter
from PIL import Image, ImageDraw, ImageFont

import os
FONTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts")
GALMURI9 = os.path.join(FONTS, "Galmuri9.ttf")
GALMURI11 = os.path.join(FONTS, "Galmuri11.ttf")

# 이름, 글자, 영역 x, 영역 y, 글꼴(None=Neo둥근모), 크기, opts
#   ex/ey = 지우고 그릴 범위(끝 포함). 없으면 영역 전체.
#   edge  = 테두리 색 강제(False=테두리 없음, None=자동)
BUTTONS = [
    ("첫 화면 시작", "시작", (52, 118), (66, 94), None, 16, dict(ex=(63, 111))),
    ("첫 화면 도움말", "도움말", (52, 120), (96, 128), None, 16, dict(ex=(69, 107), edge=False)),
    ("작은 시작 버튼", "시작", (203, 243), (3, 19), None, 16, dict(ex=(205, 240))),
    ("작은 확인 버튼", "확인", (203, 243), (31, 50), None, 16, dict(ex=(205, 240), ey=(37, 47), edge=False)),
    ("색 선택 제목", "색 선택", (28, 124), (124, 148), None, 16, dict(ex=(36, 119), cy=136, edge=False)),
    ("색 선택 작은 변형", "색 선택", (0, 76), (156, 180), None, 16, dict(ex=(3, 74), edge=6)),
    # x97~110 은 마름모 아이콘(오른쪽이 ▶ 모양으로 뾰족하다). 글자 S 는 x113 부터다.
    # 세로는 원본이 y176~186(11px) 이지만 화면 띠는 더 아래까지 보이므로
    # 기존 한글패치와 같은 자리(중심 183)에 두면 둥근모 13px 도 위로 삐지지 않는다.
    ("색 선택 큰 변형", "색 선택", (108, 204), (170, 192), None, 16,
     dict(ex=(113, 198), ey=(176, 186), cy=183, edge=5)),
    ("통신 대기", "기다려 주세요", (100, 228), (148, 172), None, 16, dict(ex=(110, 223))),
    # Back 은 테두리 10 + 속 14. 글자 자리는 y20~31 뿐이고 그 위 y8~19 는 B 버튼 기호다.
    ("뒤로 (친구 모집 화면)", "뒤로", (100, 142), (20, 32), GALMURI9, 10, dict(ex=(104, 135), ey=(20, 31))),
    ("친구 모집", "친구 모집", (28, 148), (32, 50), None, 16, dict(ex=(36, 135), edge=False)),
]

# 이름 입력 화면 OK 버튼 — 흰 바탕에 파란 글자, 글자 자리는 y4~12(9px)뿐이다
SUB00 = [
    ("확인 버튼 (이름 입력)", "확인", (165, 198), (2, 15), GALMURI9, 10,
     dict(ex=(170, 191), ey=(4, 12), ink=8, edge=False)),
]

SUB02 = [
    # ex 오른쪽 끝을 판 안쪽으로 — x152~159 는 판 바깥 모서리다
    ("파일 선택", "파일 선택", (0, 160), (64, 80), None, 16, dict(ex=(29, 125), cy=72)),
    ("복사 안내", "어디에 복사할까요?", (0, 160), (80, 96), None, 16, dict(ex=(27, 137), ey=(82, 95))),
    ("삭제 확인", "정말 삭제할까요?", (0, 160), (96, 112), None, 16, dict(ex=(1, 159), ey=(98, 111))),
    ("통신 대기 (사본)", "기다려 주세요", (0, 160), (112, 128), None, 16, dict(ex=(30, 143), ey=(112, 126))),
    # x112~ 는 옆 판의 비스듬한 모서리
    ("그룹 만들기", "그룹 만들기", (0, 118), (128, 144), None, 16, dict(ex=(1, 111))),
    ("그룹 참가", "그룹 참가", (0, 118), (144, 160), None, 16, dict(ex=(2, 111))),
    # x128~159 는 버튼 안의 DS 본체 아이콘 — 건드리면 안 된다
    ("다 함께 놀기", "다 함께 놀기", (0, 160), (160, 176), None, 16, dict(ex=(8, 108))),
    # y132~134 는 버튼 윗면 광택, x124~126 은 왼쪽 꼭지
    ("삭제 버튼", "삭제", (124, 180), (130, 154), None, 16, dict(ex=(127, 179), cx=150, ey=(138, 150))),
    ("복사 버튼", "복사", (199, 246), (130, 154), None, 16, dict(ex=(202, 243), ey=(138, 150))),
    ("그룹 선택", "그룹 선택", (4, 118), (184, 200), None, 16, dict(ex=(14, 113), ey=(185, 199))),
    ("이름 입력", "이름 입력", (4, 118), (200, 216), None, 16, dict(ex=(13, 110), ey=(202, 214))),
    # y190 은 버튼 윗선
    ("시작 버튼", "시작", (183, 232), (190, 210), None, 16, dict(ex=(186, 231), ey=(194, 205))),
    # 버튼 평평한 속은 x197~247 까지 있다 — 영역이 좁아 글자가 테두리로 삐져나갔다
    ("나가기 버튼", "나가기", (183, 250), (214, 234), None, 16, dict(ex=(199, 245), ey=(218, 230))),
    ("뒤로 (파일 메뉴)", "뒤로", (76, 118), (228, 240), GALMURI9, 10, dict(ex=(80, 111), ey=(228, 239))),
    # x124~127 은 버튼 왼쪽 모서리
    ("혼자 놀기", "혼자 놀기", (124, 252), (240, 256), None, 16, dict(ex=(128, 245), ey=(241, 255))),
]


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


def ink_edge(orig, gset, palette, ex, ey):
    """원본 글자가 속+테두리 두 색인지 가린다.

    바깥 한 겹의 색을 테두리 후보로 보되, 본체를 실제로 둘러싸고 있어야 테두리로 친다.
    흰 글자 가장자리의 옅은 보정색(10~30%)을 테두리로 오인하면 글자마다
    외곽 효과가 제각각이 된다.
    """
    if not gset:
        return None, None
    rim = [p for p in gset
           if any((p[0] + dx, p[1] + dy) not in gset for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    core = [p for p in gset if p not in set(rim)]
    edge = Counter(orig[p] for p in rim).most_common(1)[0][0] if rim else None
    ink = Counter(orig[p] for p in core).most_common(1)[0][0] if core else edge
    if edge == ink:
        return ink, None
    bright = lambda i: sum(palette.get(i, (i * 17,) * 3))
    if edge is not None and bright(ink) < bright(edge):
        # 속이 더 어두우면 원본은 「윤곽선만 보이는」 가는 획 (PLEASE WAIT)
        return edge, None
    if edge is None:
        return ink, None
    body = {p for p in gset if orig[p] == ink}
    nb = set()
    for px, py in body:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                q = (px + dx, py + dy)
                if q not in body and ex[0] <= q[0] <= ex[1] and ey[0] <= q[1] <= ey[1]:
                    nb.add(q)
    same = sum(1 for q in nb if orig[q] == edge)
    if not nb or same * 2 < len(nb):
        return ink, None
    return ink, edge


RESTORE_PAD = 8


def apply(orig, cells, font_path, size=16, palette=None, buttons=None):
    """orig = 원본 시트 셀(글자 위치·색을 재는 기준), cells = 고칠 셀."""
    palette = palette or {}
    out = []
    items = list(buttons or BUTTONS)
    # 1단계: 손댈 자리를 통째로 원본으로 되돌린다.
    # 여기 들어오는 cells 에는 이미 기존 한글패치(v1.1)의 글자가 들어 있고,
    # 그 글자는 우리가 지우려는 범위보다 넓게 퍼져 있을 수 있다.
    # 원본으로 되돌려 두면 아이콘·모서리는 살아남고 옛 글자만 사라진다.
    # (되돌리기를 모두 끝낸 뒤에 그려야 이웃한 항목끼리 서로 지우지 않는다.)
    for item in items:
        (x0, x1), (y0, y1) = item[2], item[3]
        for y in range(y0 - RESTORE_PAD, y1 + RESTORE_PAD):
            for x in range(x0 - RESTORE_PAD, x1 + RESTORE_PAD):
                if (x, y) in cells and (x, y) in orig:
                    cells[(x, y)] = orig[(x, y)]
    for item in items:
        name, text, (x0, x1), (y0, y1), fpath, fsize = item[:6]
        opts = item[6] if len(item) > 6 else {}
        path = fpath or font_path
        ex = opts.get("ex", (x0, x1 - 1))
        ey = opts.get("ey", (y0, y1 - 1))
        cols = Counter(tuple(orig[(x, y)] for y in range(y0, y1)) for x in range(x0, x1))
        prof = cols.most_common(1)[0][0]
        g = [(x, y) for y in range(ey[0], ey[1] + 1) for x in range(ex[0], ex[1] + 1)
             if orig[(x, y)] != prof[y - y0]]
        cx = opts.get("cx", (ex[0] + ex[1]) // 2)
        cy = opts.get("cy", (ey[0] + ey[1]) // 2)
        for y in range(ey[0], ey[1] + 1):
            for x in range(ex[0], ex[1] + 1):
                cells[(x, y)] = prof[y - y0]
        ink, edge = ink_edge(orig, set(g), palette, ex, ey)
        if "ink" in opts:
            ink = opts["ink"]
        if "edge" in opts:
            edge = None if opts["edge"] is False else opts["edge"]
        pts, w, h = glyph(text, path, size if fsize is None else fsize)
        ox, oy = cx - w // 2, cy - h // 2
        placed = {(x + ox, y + oy) for x, y in pts}
        # 글자는 영역 안이면 어디든 그려도 된다. 원본 글자는 ex/ey 안에만 있으므로
        # 그 바깥은 깨끗한 배경이고, 지우지 않아도 잔재가 남지 않는다.
        pad = 1 if edge is not None else 0
        clip = [ox - pad < x0, ox + w - 1 + pad >= x1,
                oy - pad < y0, oy + h - 1 + pad >= y1]
        inside = lambda k: x0 <= k[0] < x1 and y0 <= k[1] < y1
        if edge is not None:
            for x, y in placed:
                for ddx in (-1, 0, 1):
                    for ddy in (-1, 0, 1):
                        k = (x + ddx, y + ddy)
                        if k in cells and k not in placed and inside(k):
                            cells[k] = edge
        for k in placed:
            if k in cells and inside(k):
                cells[k] = ink
        out.append("  %s -> 「%s」 %s %dpt · %d×%dpx · 중심 x=%d y=%d · 글자색 %s%s" %
                   (name, text, "갈무리" if fpath else "Neo둥근모", fsize, w, h, cx, cy,
                    "%d번" % ink if edge is None else "%d번(속)+%d번(테두리)" % (ink, edge),
                    "  ※잘림 " + "".join(c for c, e in zip("←→↑↓", clip) if e) if any(clip) else ""))
    return out
