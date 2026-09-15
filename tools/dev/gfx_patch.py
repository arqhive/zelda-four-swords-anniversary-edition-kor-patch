"""Replace English image text with Korean by editing the matched tiles.

Usage: python gfx_patch.py preview   -> extract/gfx/patch_preview.png (orig / erased / korean per item)
       python gfx_patch.py apply     -> out/gfx (or $GFX_OUT): subtask_us_en.cmp, zeldat_us_en.bin
Env: GFX_SKIP=name,name  (extra items to leave untouched)   GFX_OUT=dir

Each ITEM: name, screenshot key, source prefix, text rect (x0,y0,x1,y1 inclusive), Korean, bg side, options.
  bg side: 'both' | 'left' | 'right' | 'inside' | 'global' | (r,g,b) - where each row's plate colour is sampled
  options: {'affine': True} fill unmatched blocks from a regular tile-number layout (verified on visible pixels)

Safety rules (learned in-game):
  * blocks whose tile also appears elsewhere on screen (other plates) are left exactly as they are
  * blocks whose tile is reused inside the same item may only be erased (no glyph pixels)
  * a tile may never receive two different contents (within an item or across items) -> item skipped
  * no guessing of flat tiles by neighbour numbers
"""
import os, struct, sys
from collections import Counter, defaultdict
from PIL import Image, ImageDraw, ImageFont
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # tools/ (lz, ndsrom)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lz
from tile_match import load_sources, norm, flips

# local work data (work/screens, work/extract, work/out) - not part of the repository
BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "work")
SHOTS = os.path.join(BASE, "screens")
GFX = os.path.join(BASE, "extract", "gfx")
FONT = "C:/Windows/Fonts/malgunbd.ttf"
ROW = 32  # tiles per row in every 256px-wide sheet

ITEMS = [
    ("Begin",          "064716", "sub01", (100, 243, 170, 262), "시작", "both", {}),
    ("Help",           "064716", "sub01", (105, 305, 170, 326), "도움말", "both", {}),
    ("CHOOSE A FILE",  "064737", "sub02", (112, 189, 214, 206), "파일 선택", "both", {}),
    ("Start",          "064737", "sub02", (98, 276, 156, 295), "시작", "both", {}),
    ("COPY",           "064737", "sub02", (62, 317, 115, 336), "복사", "both", {}),
    ("ERASE",          "064737", "sub02", (146, 319, 200, 334), "삭제", "right", {}),
    ("Multiplayer",    "064745", "sub02", (66, 246, 178, 265), "다 함께 놀기", "both", {}),
    ("Single player",  "064745", "sub02", (66, 303, 193, 322), "혼자 놀기", "both", {}),
    ("Select Color",   "064753", "sub01", (140, 201, 234, 219), "색 선택", "both", {}),
    ("ENTER A NAME",   "072627", "sub02", (128, 3, 238, 17), "이름 입력", "both", {}),
    ("CHOOSE A STAGE", "072700", "zel07", (57, 3, 197, 19), "스테이지 선택", "gapcol", {"affine": True, "max_h": 13}),
    ("CHAMBERS (bar)", "064818", "sub03", (60, 361, 180, 374), "시작의 사당", "both", {}),
    # stage-select map label lives in zeldat_us_en entry 2 (the sub03 match was an identical copy)
    ("CHAMBERS (map)", "072700", "zel02", (77, 160, 179, 172), "시작의 사당", "gapcol", {}),
]
UNSAFE = set(filter(None, os.environ.get("GFX_SKIP", "").split(",")))

# Direct edits on tile sheets whose graphics are stored as a readable image (no screenshot needed).
# name, source, text rect in sheet pixels (x0,y0,x1,y1), Korean, bg sampling columns (left, right)
SHEET_ITEMS = [
    # erase rect = original "OK" pixels; glyph rect = whole button interior (bigger Korean text)
    ("OK button (name entry)", "sub00", (169, 4, 190, 12), "확인", (164, 3, 196, 13)),
]

WRITTEN = {}  # (source, tile) -> pixels written by an earlier item in this run
_screen_cache = {}


def screen_index(img):
    """normalised 8x8 pattern -> screen positions, over all grid alignments (cached per image)."""
    k = id(img)
    if k not in _screen_cache:
        px = img.load()
        W, H = img.size
        idx = defaultdict(list)
        for by in range(0, H - 7):
            for bx in range(0, W - 7):
                idx[norm([px[bx + x, by + y] for y in range(8) for x in range(8)])[0]].append((bx, by))
        _screen_cache[k] = (img, idx)
    return _screen_cache[k][1]


def shot_path(key):
    return next((os.path.join(SHOTS, f) for f in os.listdir(SHOTS) if key in f), None)


def lum(c):
    return c[0] * 0.3 + c[1] * 0.59 + c[2] * 0.11


def match_blocks(img, rect, index, src, prefix):
    """8x8 blocks around rect matched to tiles: {(bx,by): [(src, tile, flip), ...]}."""
    x0, y0, x1, y1 = rect
    px = img.load()
    W, H = img.size
    per_align = []
    for oy in range(8):
        for ox in range(8):
            found = {}
            for by in range((y0 - 8 - oy) // 8 * 8 + oy, y1 + 8, 8):
                for bx in range((x0 - 8 - ox) // 8 * 8 + ox, x1 + 8, 8):
                    if bx < 0 or by < 0 or bx + 8 > W or by + 8 > H:
                        continue
                    key, ncol = norm([px[bx + x, by + y] for y in range(8) for x in range(8)])
                    cands = [c for c in index.get(key, []) if c[0].startswith(prefix)]
                    if ncol >= 3 and cands and len(cands) <= 16:
                        found[(bx, by)] = cands
            per_align.append(found)
    per_align.sort(key=len, reverse=True)
    if not per_align or not per_align[0]:
        return {}
    best = dict(per_align[0])

    def consistent(pos, c):
        bx, by = pos
        s, ti, fl = c
        for (dx, dy), step in (((8, 0), 1), ((-8, 0), -1), ((0, 8), ROW), ((0, -8), -ROW)):
            if fl in ("h", "hv") and dx: step = -step
            if fl in ("v", "hv") and dy: step = -step
            for n in best.get((bx + dx, by + dy), []):
                if n[0] == s and n[1] == ti + step and n[2] == fl:
                    return True
        return False
    for pos in list(best):
        good = [c for c in best[pos] if consistent(pos, c)]
        if good:
            best[pos] = good

    def overlaps(a, b):
        return abs(a[0] - b[0]) < 8 and abs(a[1] - b[1]) < 8
    for found in per_align[1:]:
        if len(found) < 2:
            break
        for pos, cands in found.items():
            if not any(overlaps(pos, q) for q in best):
                best[pos] = cands
    return best


def visible_consistent(get, bx, by, tile):
    """tile index <-> screen colour must be a bijection on the visible pixels."""
    t2c, c2t = {}, {}
    for y in range(8):
        for x in range(8):
            c = get(bx + x, by + y)
            if c is None:
                continue
            v = tile[y * 8 + x]
            if t2c.setdefault(v, c) != c or c2t.setdefault(c, v) != v:
                return False
    return True


def affine_fill(blocks, rect, src, get):
    """Extend matches using a regular layout: tile = base + col + ROW*row (unflipped)."""
    x0, y0, x1, y1 = rect
    X, Y = next(iter(blocks))
    votes = Counter()
    for (bx, by), cands in blocks.items():
        if (bx - X) % 8 or (by - Y) % 8:
            continue
        for s, ti, fl in cands:
            if fl == "":
                votes[(s, ti - (bx - X) // 8 - ROW * ((by - Y) // 8))] += 1
    if not votes or votes.most_common(1)[0][1] < 4:
        return blocks, 0
    (s, base), _ = votes.most_common(1)[0]
    added = 0
    for by in range(Y + (y0 - 8 - Y) // 8 * 8, y1 + 1, 8):
        for bx in range(X + (x0 - 8 - X) // 8 * 8, x1 + 1, 8):
            if (bx, by) in blocks or bx + 8 <= x0 - 4 or bx > x1 + 4:
                continue
            t = base + (bx - X) // 8 + ROW * ((by - Y) // 8)
            if 0 <= t < len(src[s]) and visible_consistent(get, bx, by, src[s][t]):
                blocks[(bx, by)] = [(s, t, "")]
                added += 1
    return blocks, added


def render_korean(text, fill, outline, box_w, box_h):
    for size in range(16, 7, -1):
        font = ImageFont.truetype(FONT, size)
        l, t, r, b = font.getbbox(text)
        w, h = r - l + 2, b - t + 2
        if w <= box_w and h <= box_h:
            break
    mask = Image.new("1", (w, h), 0)
    d = ImageDraw.Draw(mask)
    d.fontmode = "1"
    d.text((1 - l, 1 - t), text, font=font, fill=1)
    m = mask.load()
    out = {}
    for y in range(h):
        for x in range(w):
            if m[x, y]:
                out[(x, y)] = fill
    if outline is not None:
        for y in range(h):
            for x in range(w):
                if not m[x, y] and any(0 <= x + dx < w and 0 <= y + dy < h and m[x + dx, y + dy]
                                       for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    out[(x, y)] = outline
    return out, w, h, size


def process(item, index, src, write):
    name, key, prefix, rect, korean, side, opts = item
    if shot_path(key) is None:
        return "%-15s no screenshot - skipped (kept as in base graphics)" % name, []
    img = Image.open(shot_path(key)).convert("RGB")
    W, H = img.size
    px = img.load()
    get = lambda x, y: px[x, y] if 0 <= x < W and 0 <= y < H else None
    x0, y0, x1, y1 = rect
    blocks = match_blocks(img, rect, index, src, prefix)
    if not blocks:
        return "%-15s NO MATCH - skipped" % name, []
    added = 0
    if opts.get("affine"):
        blocks, added = affine_fill(blocks, rect, src, get)

    def block_of(x, y):
        for (bx, by) in blocks:
            if bx <= x < bx + 8 and by <= y < by + 8:
                return (bx, by)
        return None

    # colour -> palette index (visible pixels of first candidates)
    cmap = {}
    for (bx, by), cands in blocks.items():
        s, ti, fl = cands[0]
        t = flips(src[s][ti])[fl]
        for y in range(8):
            for x in range(8):
                c = get(bx + x, by + y)
                if c is not None:
                    cmap.setdefault(c, t[y * 8 + x])

    # locking
    tile_positions = defaultdict(set)
    for pos, cands in blocks.items():
        for s, ti, fl in cands:
            tile_positions[(s, ti)].add(pos)
    inner_locked = {pos for pos, cands in blocks.items()
                    if any(len(tile_positions[(s, ti)]) > 1 for s, ti, fl in cands)}
    outer_locked = set()
    sidx = screen_index(img)
    for (bx, by) in blocks:
        if bx < 0 or by < 0 or bx + 8 > W or by + 8 > H:
            continue
        k = norm([px[bx + x, by + y] for y in range(8) for x in range(8)])[0]
        for p in sidx.get(k, []):
            if abs(p[0] - bx) < 8 and abs(p[1] - by) < 8:
                continue
            if any(abs(p[0] - q[0]) < 8 and abs(p[1] - q[1]) < 8 for q in blocks):
                continue  # reuse inside this item
            outer_locked.add((bx, by))
            break

    # erase English
    new = img.copy()
    npx = new.load()
    fg = Counter()
    fg_rows = []
    global_bg = Counter(px[x, y] for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)).most_common(1)[0][0]
    gap_col = None
    if side == "gapcol":
        # plate profile from the column with the fewest dark (outline) pixels, preferring the centre
        darkest = min({px[x, y] for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)}, key=lum)
        dark_lum = lum(darkest) + 40
        gap_col = min(range(x0 + 2, x1 - 1),
                      key=lambda x: (sum(1 for y in range(y0, y1 + 1) if lum(px[x, y]) <= dark_lum),
                                     abs(x - (x0 + x1) // 2)))
    for y in range(y0, y1 + 1):
        samples = []
        if side in ("both", "left"):
            samples += [px[x, y] for x in range(max(0, x0 - 4), x0)]
        if side in ("both", "right"):
            samples += [px[x, y] for x in range(x1 + 1, min(W, x1 + 5))]
        if side == "inside":
            samples = [px[x, y] for x in range(x0, x1 + 1)]
        if isinstance(side, tuple):
            bg = side
        elif gap_col is not None:
            bg = px[gap_col, y]
        elif side == "global" or not samples:
            bg = global_bg
        else:
            bg = Counter(samples).most_common(1)[0][0]
        row_fg = 0
        for x in range(x0, x1 + 1):
            if px[x, y] != bg:
                fg[px[x, y]] += 1
                row_fg += 1
            if block_of(x, y) is not None:  # pixels in unmatched blocks cannot be written: keep them
                npx[x, y] = bg
        if row_fg:
            fg_rows.append(y)
    cols = [c for c, _ in fg.most_common(4)]
    fill = max(cols[:2], key=lum) if cols else (255, 255, 255)
    outline = min(cols, key=lum) if len(cols) > 1 else None
    # outer-locked blocks keep their original pixels
    for (bx, by) in outer_locked:
        for y in range(8):
            for x in range(8):
                if 0 <= bx + x < W and 0 <= by + y < H:
                    npx[bx + x, by + y] = px[bx + x, by + y]
    erased = new.copy()

    # place Korean where every glyph pixel lands in a writable, non-locked block
    text_h = (fg_rows[-1] - fg_rows[0] + 1) if fg_rows else (y1 - y0 + 1)
    box_h = min(text_h + 1, y1 - y0 + 1, opts.get("max_h", 99))
    glyph, w, h, size = render_korean(korean, fill, outline, x1 - x0 + 1, box_h)

    def bad(x, y):
        b = block_of(x, y)
        return b is None or b in inner_locked or b in outer_locked
    cx = x0 + (x1 - x0 + 1 - w) // 2
    cy = y0 + (y1 - y0 + 1 - h) // 2
    best_pos = None
    for dy in range(-2, 3):
        for dx in range(-10, 11):
            ox_, oy_ = cx + dx, cy + dy
            if ox_ < x0 or oy_ < y0 or ox_ + w - 1 > x1 or oy_ + h - 1 > y1:
                continue
            miss = sum(1 for gx, gy in glyph if bad(ox_ + gx, oy_ + gy))
            score = (miss, abs(dx) + abs(dy))
            if best_pos is None or score < best_pos[0]:
                best_pos = (score, ox_, oy_)
    (glyph_miss, _), ox, oy = best_pos if best_pos else ((len(glyph), 0), cx, cy)
    for (gx, gy), c in glyph.items():
        if not bad(ox + gx, oy + gy):
            npx[ox + gx, oy + gy] = c

    changed = [(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1) if npx[x, y] != px[x, y]]
    uncovered = sum(1 for x, y in changed if block_of(x, y) is None)
    report = "%-15s blocks %3d (+%d affine) locked in/out %d/%d font %dpx glyph px dropped %d uncovered px %d" % (
        name, len(blocks), added, len(inner_locked), len(outer_locked), size, glyph_miss, uncovered)

    if write:
        if name in UNSAFE:
            report += " SKIPPED (marked unsafe)"
        elif uncovered > 80:
            report += " SKIPPED (too many uncovered pixels)"
        elif glyph_miss > 12:
            report += " SKIPPED (glyph does not fit writable tiles)"
        else:
            pending, conflict = {}, []
            for (bx, by), cands in blocks.items():
                if (bx, by) in outer_locked:
                    continue
                if all(get(bx + x, by + y) is None or npx[bx + x, by + y] == px[bx + x, by + y]
                       for y in range(8) for x in range(8)):
                    continue
                for s, ti, fl in cands:
                    t = flips(src[s][ti])[fl]
                    local = {}
                    for y in range(8):
                        for x in range(8):
                            c = get(bx + x, by + y)
                            if c is not None:
                                local.setdefault(c, t[y * 8 + x])
                    merged = dict(cmap); merged.update(local)
                    pix = []
                    for y in range(8):
                        for x in range(8):
                            if get(bx + x, by + y) is None:
                                pix.append(t[y * 8 + x])  # off-screen rows keep original data
                                continue
                            c = npx[bx + x, by + y]
                            if c not in merged:
                                c = min(merged, key=lambda m: sum((a - b) ** 2 for a, b in zip(m, c)))
                            pix.append(merged[c])
                    unflipped = flips(pix)[fl]
                    if (s, ti) in pending and pending[(s, ti)] != unflipped:
                        conflict.append((s, ti))
                    pending[(s, ti)] = unflipped
            clash = [k for k, t in pending.items() if k in WRITTEN and WRITTEN[k] != t]
            if conflict:
                report += " SKIPPED (tile conflict %s)" % conflict[:3]
            elif clash:
                report += " SKIPPED (clash with earlier item %s)" % clash[:3]
            else:
                for k, t in pending.items():
                    src[k[0]][k[1]] = t
                    WRITTEN[k] = t
                report += " tiles written %d" % len(pending)
    pad = 6
    box = (max(0, x0 - pad), max(0, y0 - pad), min(W, x1 + pad + 1), min(H, y1 + pad + 1))
    return report, [img.crop(box), erased.crop(box), new.crop(box)]


def sheet_edit(item, src, write):
    """Edit text drawn directly in a tile sheet (256px wide, 8x8 tiles) in palette-index space."""
    name, sname, (x0, y0, x1, y1), korean = item[:4]
    gx0, gy0, gx1, gy1 = item[4] if len(item) > 4 else (x0, y0, x1, y1)
    tiles = src[sname]
    get = lambda x, y: tiles[(y // 8) * ROW + x // 8][(y % 8) * 8 + x % 8]
    sheet = {}
    for y in range(max(0, min(y0, gy0) - 4), max(y1, gy1) + 5):
        for x in range(max(0, min(x0, gx0) - 6), min(256, max(x1, gx1) + 7)):
            sheet[(x, y)] = get(x, y)
    new = dict(sheet)
    fg = Counter()
    for y in range(y0, y1 + 1):
        samples = [sheet[(x, y)] for x in list(range(x0 - 4, x0)) + list(range(x1 + 1, x1 + 5)) if (x, y) in sheet]
        bg = Counter(samples).most_common(1)[0][0]
        for x in range(x0, x1 + 1):
            if sheet[(x, y)] != bg:
                fg[sheet[(x, y)]] += 1
            new[(x, y)] = bg
    fill = fg.most_common(1)[0][0] if fg else 1
    glyph, w, h, size = render_korean(korean, fill, None, gx1 - gx0 + 1, gy1 - gy0 + 1)
    ox = gx0 + (gx1 - gx0 + 1 - w) // 2
    oy = gy0 + (gy1 - gy0 + 1 - h) // 2
    for (gx, gy), c in glyph.items():
        new[(ox + gx, oy + gy)] = c
    touched = {((x // 8) + (y // 8) * ROW) for (x, y), v in new.items() if v != sheet[(x, y)]}
    report = "%-22s sheet edit %s font %dpx fill idx %d tiles %d" % (name, sname, size, fill, len(touched))
    if write and name not in UNSAFE:
        pending = {}
        for ti in touched:
            t = list(tiles[ti])
            for (x, y), v in new.items():
                if (x // 8) + (y // 8) * ROW == ti:
                    t[(y % 8) * 8 + x % 8] = v
            pending[(sname, ti)] = t
        clash = [k for k, t in pending.items() if k in WRITTEN and WRITTEN[k] != t]
        if clash:
            report += " SKIPPED (clash)"
        else:
            for k, t in pending.items():
                tiles[k[1]] = t
                WRITTEN[k] = t
            report += " written"
    # preview crops as greyscale index images
    def to_img(d):
        xs = [p[0] for p in d]; ys = [p[1] for p in d]
        im = Image.new("RGB", (max(xs) - min(xs) + 1, max(ys) - min(ys) + 1))
        for (x, y), v in d.items():
            im.putpixel((x - min(xs), y - min(ys)), (v * 17,) * 3)
        return im
    return report, [to_img(sheet), to_img(new)]


# ---------------------------------------------------------------- guessed stage-name plates (no screenshots)
# Bottom-bar names drawn as readable plates in the sub03 sheet: (name, text rect in sheet px, Korean)
BAR_NAMES = [
    ("bar TALUS CAVE",        (27, 50, 106, 61), "바위산 동굴"),
    ("bar SEA OF TREES",      (149, 50, 245, 61), "돌아올 수 없는 숲"),
    ("bar VAATI'S PALACE",    (17, 66, 121, 77), "바람의 궁전"),
    ("bar DEATH MOUNTAIN",    (145, 66, 251, 77), "데스마운틴"),
    ("bar HERO'S TRIAL",      (22, 81, 111, 93), "수련장"),
    ("bar REALM OF MEMORIES", (142, 81, 252, 93), "추억의 대지"),
]
# Map labels: zeldat_us_en entries share the CHAMBERS (entry 2) tile layout -> (name, entry, rect in label px, Korean)
MAP_NAMES = [
    ("map TALUS CAVE",        3, (20, 2, 98, 13), "바위산 동굴"),
    ("map SEA OF TREES",      4, (15, 2, 107, 13), "돌아올 수 없는 숲"),
    ("map VAATI'S PALACE",    5, (8, 2, 113, 13), "바람의 궁전"),
    ("map DEATH MOUNTAIN",    6, (7, 2, 118, 13), "데스마운틴"),
    ("map REALM OF MEMORIES", 8, (5, 2, 115, 13), "추억의 대지"),
    ("map HERO'S TRIAL",      9, (15, 2, 100, 13), "수련장"),
    # redo the CHAMBERS label (R6 version picked up stray plate lines); its tiles are exclusive -> override
    ("map CHAMBERS OF INSIGHT", 2, (5, 2, 118, 13), "시작의 사당", "override"),
]


def plain_profile(get, x0, x1, y0, y1):
    """Most common column (top..bottom) in a region with sparse text = the plate background column."""
    return list(Counter(tuple(get(x, y) for y in range(y0, y1 + 1)) for x in range(x0, x1 + 1)).most_common(1)[0][0])


def index_edit(get, rect, korean, lum, bg_row=None):
    """Erase + draw Korean in palette-index space. get(x,y)->index; bg_row(y)->plate index for that row.
    Returns {(x,y): new index}, font size."""
    x0, y0, x1, y1 = rect
    if bg_row is None:
        profile = plain_profile(get, x0, x1, y0, y1)
        bg_row = lambda y: profile[y - y0]
    new, fg, rows = {}, Counter(), []
    for y in range(y0, y1 + 1):
        bg = bg_row(y)
        hit = False
        for x in range(x0, x1 + 1):
            if get(x, y) != bg:
                fg[get(x, y)] += 1
                hit = True
            new[(x, y)] = bg
        if hit:
            rows.append(y)
    cols = [c for c, _ in fg.most_common(4)]
    fill = max(cols[:2], key=lum) if cols else 1
    outline = min(cols, key=lum) if len(cols) > 1 else None
    text_h = rows[-1] - rows[0] + 1 if rows else y1 - y0 + 1
    glyph, w, h, size = render_korean(korean, fill, outline, x1 - x0 + 1, min(text_h + 1, y1 - y0 + 1))
    ox = x0 + (x1 - x0 + 1 - w) // 2
    oy = y0 + (y1 - y0 + 1 - h) // 2
    for (gx, gy), c in glyph.items():
        new[(ox + gx, oy + gy)] = c
    return {k: v for k, v in new.items() if v != get(*k)}, size


def commit(pending, report):
    clash = [k for k, t in pending.items() if k in WRITTEN and WRITTEN[k] != t]
    if clash:
        return report + " SKIPPED (clash %s)" % clash[:3], False
    for k, t in pending.items():
        WRITTEN[k] = t
    return report + " tiles %d" % len(pending), True


def guessed_plates(src, index, write):
    rows = []
    # bottom bar names (sub03 sheet); palette unknown -> indices are roughly ordered dark..light
    tiles = src["sub03"]
    get = lambda x, y: tiles[(y // 8) * ROW + x // 8][(y % 8) * 8 + x % 8]
    lum_idx = lambda v: 255 if v == 0 else v * 16
    orig, oidx = load_sources()
    # plate background column (rows 0..15 of a 16px bar plate) from the ORIGINAL "TALUS CAVE" bar (wide word gaps)
    o3 = orig["sub03"]
    oget = lambda x, y: o3[(y // 8) * ROW + x // 8][(y % 8) * 8 + x % 8]
    bar_profile = plain_profile(oget, 27, 106, 48, 63)
    print("bar plate profile (from original TALUS CAVE bar):", "".join("%X" % v for v in bar_profile))
    for name, rect, korean in BAR_NAMES:
        plate_top = rect[1] // 16 * 16
        changes, size = index_edit(get, rect, korean, lum_idx, bg_row=lambda y, t=plate_top: bar_profile[y - t])
        pending = {}
        for (x, y), v in changes.items():
            ti = (y // 8) * ROW + x // 8
            t = pending.setdefault(("sub03", ti), list(tiles[ti]))
            t[(y % 8) * 8 + x % 8] = v
        report = "%-24s %dpx" % (name, size)
        if write and name not in UNSAFE:
            report, ok = commit(pending, report)
            if ok:
                for (s, ti), t in pending.items():
                    tiles[ti] = t
        rows.append(report)
        print(report)
    # map labels: layout + palette from the CHAMBERS label in the stage-select screenshot
    path = shot_path("072700")
    if path is None:
        print("map labels skipped: stage-select screenshot missing")
        return
    img = Image.open(path).convert("RGB")
    px = img.load()
    blocks = match_blocks(img, (56, 150, 200, 180), oidx, orig, "zel02")
    layout = {pos: (c[0][1], c[0][2]) for pos, c in blocks.items()}
    X0 = min(p[0] for p in layout); Y0 = min(p[1] for p in layout)
    pal = {}
    for (bx, by), (ti, fl) in layout.items():
        t = flips(orig["zel02_4"][ti])[fl]
        for y in range(8):
            for x in range(8):
                pal.setdefault(t[y * 8 + x], px[bx + x, by + y])
    lum_pal = lambda v: lum(pal.get(v, (v * 17,) * 3))
    cell = {}  # label px -> (tile, flip, tile-local x, y)
    for (bx, by), (ti, fl) in layout.items():
        for y in range(8):
            for x in range(8):
                cell[(bx - X0 + x, by - Y0 + y)] = (ti, fl, x, y)
    # label background column from the ORIGINAL "TALUS CAVE" map label (entry 3, wide word gaps)
    def cget(x, y, tiles=orig["zel03_4"]):
        ti, fl, lx, ly = cell[(x, y)]
        return flips(tiles[ti])[fl][ly * 8 + lx]
    xs = [x for x in range(20, 99) if all((x, y) in cell for y in range(16))]
    map_profile = plain_profile(cget, min(xs), max(xs), 0, 15)
    print("map label profile (from original TALUS CAVE label):", "".join("%X" % v for v in map_profile))
    for name, entry, rect, korean, *flags in MAP_NAMES:
        tiles = src["zel%02d_4" % entry]
        base_tiles = orig["zel%02d_4" % entry] if "override" in flags else tiles
        if "override" in flags:
            tiles[:] = [list(t) for t in base_tiles]  # restart from the original English label
            for k in [k for k in WRITTEN if k[0] == "zel%02d_4" % entry]:
                del WRITTEN[k]

        def lget(x, y, tiles=tiles):
            ti, fl, lx, ly = cell[(x, y)]
            return flips(tiles[ti])[fl][ly * 8 + lx]
        # shrink the rect horizontally until it lies inside the known layout
        x0, y0, x1, y1 = rect
        inside = lambda a, b: all((x, y) in cell for y in range(y0, y1 + 1) for x in range(a, b + 1))
        while x0 < x1 and not inside(x0, x0):
            x0 += 1
        while x1 > x0 and not inside(x1, x1):
            x1 -= 1
        if not inside(x0, x1):
            print("%-24s SKIPPED (rect has holes in layout)" % name)
            continue
        rect = (x0, y0, x1, y1)
        changes, size = index_edit(lget, rect, korean, lum_pal, bg_row=lambda y: map_profile[y])
        work = {}
        for (x, y), v in changes.items():
            ti, fl, lx, ly = cell[(x, y)]
            flipped = work.setdefault((ti, fl), list(flips(tiles[ti])[fl]))
            flipped[ly * 8 + lx] = v
        pending = {("zel%02d_4" % entry, ti): flips(t)[fl] for (ti, fl), t in work.items()}
        report = "%-24s %dpx" % (name, size)
        if write and name not in UNSAFE:
            report, ok = commit(pending, report)
            if ok:
                for (s, ti), t in pending.items():
                    tiles[ti] = t
        print(report)


def render_guess_preview(src):
    """sub03 sheet (greyscale) + map labels of entries 3-9 using the CHAMBERS layout, after edits."""
    tiles = src["sub03"]
    sheet = Image.new("L", (256, 104))
    p = sheet.load()
    for y in range(104):
        for x in range(256):
            p[x, y] = tiles[(y // 8) * ROW + x // 8][(y % 8) * 8 + x % 8] * 17
    sheet = sheet.resize((768, 312), Image.NEAREST).convert("RGB")
    out = Image.new("RGB", (768, 312 + 7 * 52), (30, 30, 30))
    out.paste(sheet, (0, 0))
    path = shot_path("072700")
    if path:
        orig, oidx = load_sources()
        img = Image.open(path).convert("RGB")
        px = img.load()
        blocks = match_blocks(img, (56, 150, 200, 180), oidx, orig, "zel02")
        layout = {pos: (c[0][1], c[0][2]) for pos, c in blocks.items()}
        X0 = min(q[0] for q in layout); Y0 = min(q[1] for q in layout)
        pal = {}
        for (bx, by), (ti, fl) in layout.items():
            t = flips(orig["zel02_4"][ti])[fl]
            for y in range(8):
                for x in range(8):
                    pal.setdefault(t[y * 8 + x], px[bx + x, by + y])
        for k, e in enumerate((3, 4, 5, 6, 8, 9, 2)):
            lab = Image.new("RGB", (128, 16), (255, 0, 255))
            lp = lab.load()
            for (bx, by), (ti, fl) in layout.items():
                t = flips(src["zel%02d_4" % e][ti])[fl]
                for y in range(8):
                    for x in range(8):
                        v = t[y * 8 + x]
                        lp[bx - X0 + x, by - Y0 + y] = pal.get(v, (v * 17,) * 3)
            out.paste(lab.resize((384, 48), Image.NEAREST), (0, 312 + k * 52))
    out.save(os.path.join(GFX, "guess_preview.png"))


def pack4(tiles):
    px = [v for t in tiles for v in t]
    return bytes(px[i] | px[i + 1] << 4 for i in range(0, len(px), 2))


def write_files(src):
    out_dir = os.environ.get("GFX_OUT", os.path.join(BASE, "out", "gfx"))
    os.makedirs(out_dir, exist_ok=True)
    dec = bytearray(open(os.path.join(GFX, "..", "subtask_us_en.cmp.dec"), "rb").read())
    n = struct.unpack_from("<I", dec, 0)[0] // 4
    offs = struct.unpack_from("<%dI" % n, dec, 0)
    for k in range(5):
        o = offs[k]
        dsize = struct.unpack_from("<I", dec, o + 0x28)[0]
        data = pack4(src["sub%02d" % k])
        assert len(data) == dsize
        dec[o + 0x30:o + 0x30 + dsize] = data
    open(os.path.join(out_dir, "subtask_us_en.cmp"), "wb").write(lz.compress_lz11(bytes(dec)))
    z = open(os.path.join(GFX, "..", "zeldat_us_en.bin"), "rb").read()
    n = struct.unpack_from("<I", z, 0)[0] // 8
    entries = []
    for i in range(n):
        off, size = struct.unpack_from("<II", z, i * 8)
        comp = bool(size & 0x80000000)
        blob = z[off:off + (size & 0x7FFFFFFF)]
        raw = lz.decompress(blob) if comp else blob
        packed = pack4(src["zel%02d_4" % i])
        new_raw = packed[:len(raw)] + raw[len(packed):]
        if new_raw != raw:
            blob = lz.compress_lz11(new_raw) if comp else new_raw
        entries.append((blob, comp))
    table, body = bytearray(), bytearray()
    for blob, comp in entries:
        table += struct.pack("<II", n * 8 + len(body), len(blob) | (0x80000000 if comp else 0))
        body += blob
    open(os.path.join(out_dir, "zeldat_us_en.bin"), "wb").write(bytes(table + body))
    print("wrote", out_dir)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "preview"
    base = os.environ.get("GFX_BASE")  # dir with previously patched subtask_us_en.cmp / zeldat_us_en.bin
    src, index = load_sources(base)
    if base:
        orig, _ = load_sources()
        for s, tiles in src.items():
            for ti, t in enumerate(tiles):
                if t != orig[s][ti]:
                    WRITTEN[(s, ti)] = t  # protect earlier Korean edits
        print("base graphics:", base, "- protected tiles:", len(WRITTEN))
    rows = []
    for item in ITEMS:
        report, crops = process(item, index, src, mode == "apply")
        print(report)
        if crops:
            rows.append((item[0], crops))
    for item in SHEET_ITEMS:
        report, crops = sheet_edit(item, src, mode == "apply")
        print(report)
        rows.append((item[0], crops))
    if os.environ.get("GFX_GUESS"):
        guessed_plates(src, index, mode == "apply")
        render_guess_preview(src)
    S = 3
    W = max(sum(c.width for c in crops) * S + 30 for _, crops in rows)
    H = sum(max(c.height for c in crops) * S + 16 for _, crops in rows)
    sheet = Image.new("RGB", (W, H), (30, 30, 30))
    d = ImageDraw.Draw(sheet)
    y = 0
    for name, crops in rows:
        d.text((2, y), name, fill=(255, 255, 0))
        x = 0
        for c in crops:
            sheet.paste(c.resize((c.width * S, c.height * S), Image.NEAREST), (x, y + 12))
            x += c.width * S + 10
        y += max(c.height for c in crops) * S + 16
    sheet.save(os.path.join(GFX, "patch_preview.png"))
    if mode == "apply":
        write_files(src)


if __name__ == "__main__":
    main()
