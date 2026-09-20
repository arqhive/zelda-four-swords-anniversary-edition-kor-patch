"""Encode the runtime title OBJ graphics, not just the subtask background.

pat.bin group 181 frames 0/1 reference tiles 0..447 in both localized
zeldat entries 12 and 13. The remaining tiles belong to animated effects.
Index zero is transparent; OBJ tiles are packed in 1D within each object.
"""
import hashlib
import struct

from PIL import Image

from polish_graphics import zentries, rawentry, zpack, lz

SHAPES = (
    ((8, 8), (16, 16), (32, 32), (64, 64)),
    ((16, 8), (32, 8), (32, 16), (64, 32)),
    ((8, 16), (8, 32), (16, 32), (32, 64)),
)
SPRITE_ENTRIES = (12, 13)
TITLE_BYTES = 448 * 64


def title_patterns(pat):
    count = struct.unpack_from('<I', pat)[0] // 4
    assert count == 183
    offsets = struct.unpack_from('<183I', pat)
    pointers = struct.unpack_from('<20I', pat, offsets[181])
    frames = []
    for p in pointers:
        objects = []
        for j in range(pat[p]):
            x, y, flags, low, extra = struct.unpack_from('<bbBBB', pat, p+1+j*5)
            assert extra == 0
            w, h = SHAPES[flags >> 6][flags >> 4 & 3]
            objects.append((x+128, y+96, w, h, low+(flags & 3)*256,
                            bool(flags & 4), bool(flags & 8)))
        frames.append(objects)
    assert frames[0] == [(32+64*x, 16+64*y, 64, 64, (y*3+x)*64, False, False)
                         for y in range(2) for x in range(3)]
    assert frames[1] == [(104, 102, 64, 32, 384, False, False),
                         (168, 102, 64, 32, 416, False, False)]
    assert min(o[4] for frame in frames[2:] for o in frame) == 448
    return frames


def object_pixels(obj):
    x, y, w, h, tile, flip_x, flip_y = obj
    for yy in range(h):
        for xx in range(w):
            off = (tile+yy//8*(w//8)+xx//8)*64+yy%8*8+xx%8
            yield x+(w-1-xx if flip_x else xx), y+(h-1-yy if flip_y else yy), off


def sprite_indices(raw, frames, selected=(0, 1)):
    result = Image.new('L', (256, 192))
    for f in selected:
        for obj in frames[f]:
            for x, y, off in object_pixels(obj):
                if 0 <= x < 256 and 0 <= y < 192 and raw[off]:
                    result.putpixel((x, y), raw[off])
    return result


def sprite_palette(rom):
    # The 8192-byte extended palette has sixteen banks; title uses bank zero.
    raw = rawentry(zentries(rom.read('zeldat.bin'))[62])
    assert len(raw) == 8192
    return [((v & 31)*255//31, ((v >> 5) & 31)*255//31, ((v >> 10) & 31)*255//31)
            for v in struct.unpack('<256H', raw[:512])]


def render_title_sprite(rom, entry=12):
    raw = rawentry(zentries(rom.read('zeldat_us_en.bin'))[entry])
    indices = sprite_indices(raw, title_patterns(rom.read('pat.bin')))
    palette = sprite_palette(rom)
    result = Image.new('RGBA', indices.size)
    result.putdata([(*palette[v], 255 if v else 0) for v in indices.getdata()])
    return result


def compile_sprite_logo(rom, artwork):
    frames = title_patterns(rom.read('pat.bin'))
    palette = sprite_palette(rom)
    source = Image.open(artwork)
    assert source.mode == 'RGBA', 'The sprite artwork must have genuine alpha.'
    alpha = source.getchannel('A')
    assert alpha.getextrema() == (0, 255)
    # Ignore near-transparent extraction noise when determining the logo bounds.
    bounds = alpha.point(lambda a: 255 if a >= 128 else 0).getbbox()
    assert bounds
    native = Image.new('RGBA', (256, 192))
    native.paste(source.crop(bounds).resize((188, 126), Image.Resampling.LANCZOS), (34, 17))
    indexed = Image.new('L', native.size)
    nearest = {}
    for y in range(17, 132):
        for x in range(34, 222):
            r, g, b, a = native.getpixel((x, y))
            if a < 128:
                continue
            color = (r, g, b)
            if color not in nearest:
                # Zero is reserved, even if it is the closest RGB color.
                nearest[color] = min(range(1, 256), key=lambda i:
                    sum((c-p)**2 for c, p in zip(color, palette[i])))
            indexed.putpixel((x, y), nearest[color])
    entries = zentries(rom.read('zeldat_us_en.bin'))
    original_entries = list(entries)
    changed = []
    for n in SPRITE_ENTRIES:
        before = rawentry(entries[n])
        assert len(before) == 51200
        after = bytearray(before)
        for f in (0, 1):
            for obj in frames[f]:
                for x, y, off in object_pixels(obj):
                    if f == 0 and y >= 132:
                        continue  # Original jewels, including their exact indices.
                    subtitle = 104 <= x < 232 and 102 <= y < 132
                    after[off] = indexed.getpixel((x, y)) if (subtitle == (f == 1) and y < 132) else 0
        assert after != before
        assert after[TITLE_BYTES:] == before[TITLE_BYTES:]
        for obj in frames[0]:
            for x, y, off in object_pixels(obj):
                if y >= 132:
                    assert after[off] == before[off]
        decoded = sprite_indices(after, frames)
        # Prove the 1D packing reconstructs the intended indexed title exactly.
        assert decoded.crop((32, 16, 232, 132)).tobytes() == indexed.crop((32, 16, 232, 132)).tobytes()
        compressed = lz.compress_lz11(bytes(after))
        assert lz.decompress(compressed) == bytes(after)
        entries[n] = (compressed, True)
        changed.append({'entry': n, 'changed_bytes': sum(a != b for a, b in zip(before, after)),
                        'sha256': hashlib.sha256(after).hexdigest()})
    assert all(a == b for n, (a, b) in enumerate(zip(original_entries, entries)) if n not in SPRITE_ENTRIES)
    return zpack(entries), {
        'sprite_artwork_sha256': hashlib.sha256(artwork.read_bytes()).hexdigest(),
        'sprite_source_alpha_bounds': bounds, 'sprite_entries': changed,
        'pattern_group': 181, 'pattern_frames': [0, 1],
        'palette_entry': 62, 'palette_bank': 0,
        'transparent_index': 0, 'effect_tiles_448_onward_preserved': True,
        'jewel_rows_132_onward_preserved': True,
        'other_localized_entries_preserved': True,
    }
