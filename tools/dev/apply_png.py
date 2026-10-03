# -*- coding: utf-8 -*-
"""재작업 PNG 를 시트에 되돌려 넣는다.

팔레트를 스크린샷에서 추정했기 때문에 서로 다른 번호가 같은 색으로 잡힌 자리가 있다
(시트 1의 0·3·9번이 모두 같은 색). 색만 보고 번호를 되돌리면 배경이 망가진다.
그래서 PNG에서는 **흰 글자(251,251,251)의 위치만** 읽고, 배경은 원본에서 복원한다.
작업 기준이 "흰 글자, 외곽선·그림자 없음"이므로 이 방법으로 충분하다.
"""
import os
from collections import Counter
from PIL import Image

WHITE = (251, 251, 251)

ITEMS = {
    "04_버튼_sub01": [("01_첫화면_시작", 1, (52, 66)), ("02_첫화면_도움말", 1, (52, 96)),
                     ("03_작은시작버튼", 1, (196, 0)), ("04_작은확인버튼", 1, (196, 28)),
                     ("05_색선택제목", 1, (28, 124)), ("06_색선택_작은변형", 1, (0, 156)),
                     ("07_색선택_큰변형", 1, (108, 172)), ("08_통신대기", 1, (100, 148)),
                     ("09_친구모집_뒤로", 1, (28, 12))],
    "05_파일메뉴_sub02": [("01_파일선택_복사_삭제안내", 2, (0, 62)), ("02_복사버튼", 2, (196, 132)),
                        ("03_그룹선택_이름입력", 2, (4, 180)), ("04_시작버튼", 2, (180, 188)),
                        ("05_나가기버튼", 2, (196, 212)), ("06_뒤로", 2, (76, 220)),
                        ("07_혼자놀기", 2, (124, 236))],
    "06_이름입력_sub00": [("01_확인버튼", 0, (160, 0)), ("02_PRESS_A버튼", 0, (30, 14)),
                        ("03_글자판전환줄_ABC_abc_백스페이스_OK", 0, (0, 0))],
}

# 글자 색 번호(해당 시트에서 흰색에 해당하는 번호)
WHITE_INDEX = {0: 15, 1: 15, 2: 15}


def background_profile(sheets, k, x0, y0, w, h):
    """항목 영역에서 가장 흔한 세로 배열 = 글자 없는 배경 기둥."""
    cols = Counter(tuple(sheets[k].get((x0 + x, y0 + y), 0) for y in range(h)) for x in range(w))
    prof, n = cols.most_common(1)[0]
    return prof, n


def apply_pngs(sheets, redo_dir, src_dir, pals, report):
    changed = 0
    for folder, items in ITEMS.items():
        d = os.path.join(redo_dir, folder)
        if not os.path.isdir(d):
            continue
        for name, k, (x0, y0) in items:
            p = os.path.join(d, name + ".png")
            q = os.path.join(src_dir, folder, name + ".png")
            if not (os.path.exists(p) and os.path.exists(q)):
                continue
            new = Image.open(p).convert('RGB')
            old = Image.open(q).convert('RGB')
            w, h = old.size
            npx, opx = new.load(), old.load()
            prof, n = background_profile(sheets, k, x0, y0, w, h)
            # 원본 글자가 있던 칸(= 배경 기둥과 다른 칸) 중 사용자가 바꾼 영역을 배경으로 복원
            touched = {(x, y) for y in range(h) for x in range(w) if npx[x, y] != opx[x, y]}
            if not touched:
                continue
            # 사용자가 건드린 영역을 배경 기둥으로 복원한 뒤, 글자(밝은 색)만 다시 찍는다.
            # 추정 팔레트에 같은 색을 가진 번호가 섞여 있어 색→번호 역변환은 쓰지 않는다.
            rev = {}
            for i, v in pals[k].items():
                rev.setdefault(tuple(v), []).append(i)
            ink = {c: idx[0] for c, idx in rev.items() if len(idx) == 1 and sum(c) >= 420}
            xs = [q[0] for q in touched]; ys = [q[1] for q in touched]
            moved = unknown = 0
            for y in range(min(ys), max(ys) + 1):
                for x in range(min(xs), max(xs) + 1):
                    key = (x0 + x, y0 + y)
                    if key in sheets[k] and sheets[k][key] != 0:
                        sheets[k][key] = prof[y]
            for y in range(h):
                for x in range(w):
                    c = npx[x, y]
                    if c not in ink:
                        continue
                    key = (x0 + x, y0 + y)
                    if key in sheets[k] and sheets[k][key] != 0:
                        sheets[k][key] = ink[c]
                        moved += 1
            report.append("  %s/%s.png -> 시트 %d (%d,%d) %dx%d · 옮긴 픽셀 %d%s"
                          % (folder, name, k, x0, y0, w, h, moved,
                             " · 팔레트 밖 %d 건너뜀" % unknown if unknown else ""))
            changed += 1
    return changed
