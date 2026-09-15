"""NFTR (NitroSystem font) 1bpp reader/writer with glyph insertion."""
import struct
from PIL import Image, ImageDraw, ImageFont


class Nftr:
    def __init__(self, data):
        self.hdr = bytearray(data[:0x10])
        self.finf = bytearray(data[0x10:0x30])
        cg = 0x30
        cg_size = struct.unpack_from("<I", data, cg + 4)[0]
        self.cw, self.ch, gsz, self.base, self.maxw, self.bpp = struct.unpack_from("<BBHBBB", data, cg + 8)
        assert self.bpp == 1
        cw_o = cg + cg_size
        first, last = struct.unpack_from("<HH", data, cw_o + 8)
        assert first == 0
        self.widths = [tuple(data[cw_o + 0x10 + i * 3:cw_o + 0x13 + i * 3]) for i in range(last + 1)]
        self.glyphs = []  # list of 2D bool rows; count follows CWDH (CGLP tail is padding)
        for i in range(len(self.widths)):
            g = data[cg + 0x10 + i * gsz:cg + 0x10 + (i + 1) * gsz]
            self.glyphs.append([[bool((g[(y * self.cw + x) // 8] >> (7 - (y * self.cw + x) % 8)) & 1)
                                 for x in range(self.cw)] for y in range(self.ch)])
        # CMAP chain -> code -> glyph index
        self.cmap = {}
        p = cw_o + struct.unpack_from("<I", data, cw_o + 4)[0]
        while p and p < len(data):
            size = struct.unpack_from("<I", data, p + 4)[0]
            lo, hi, typ = struct.unpack_from("<HHH", data, p + 8)
            nxt = struct.unpack_from("<I", data, p + 0x10)[0]
            q = p + 0x14
            if typ == 0:
                idx0 = struct.unpack_from("<H", data, q)[0]
                for c in range(lo, hi + 1):
                    self.cmap[c] = idx0 + c - lo
            elif typ == 1:
                for c in range(lo, hi + 1):
                    idx = struct.unpack_from("<H", data, q + (c - lo) * 2)[0]
                    if idx != 0xFFFF:
                        self.cmap[c] = idx
            else:
                cnt = struct.unpack_from("<H", data, q)[0]
                for i in range(cnt):
                    c, idx = struct.unpack_from("<HH", data, q + 2 + i * 4)
                    self.cmap[c] = idx
            p = nxt - 8 if nxt else 0

    def add_ttf_glyphs(self, chars, ttf, index=0, size=12, yoff=-1, advance=12):
        font = ImageFont.truetype(ttf, size, index=index)
        for c in chars:
            if ord(c) in self.cmap:
                continue
            im = Image.new("1", (self.cw, self.ch), 0)
            ImageDraw.Draw(im).text((0, yoff), c, font=font, fill=1)
            self.glyphs.append([[bool(im.getpixel((x, y))) for x in range(self.cw)] for y in range(self.ch)])
            self.widths.append((0, min(self.cw, advance), advance))
            self.cmap[ord(c)] = len(self.glyphs) - 1

    def resize_cell(self, cw):
        for g in self.glyphs:
            for row in g:
                row.extend([False] * (cw - len(row)))
        self.cw = cw
        self.maxw = max(self.maxw, cw)

    def build(self):
        gsz = (self.cw * self.ch + 7) // 8
        cglp = bytearray(struct.pack("<BBHBBBB", self.cw, self.ch, gsz, self.base, self.maxw, self.bpp, 0))
        for g in self.glyphs:
            buf = bytearray(gsz)
            for y in range(self.ch):
                for x in range(self.cw):
                    if g[y][x]:
                        bit = y * self.cw + x
                        buf[bit // 8] |= 0x80 >> (bit % 8)
            cglp += buf
        cglp = pad4(b"PLGC" + struct.pack("<I", 8 + len(cglp) + (-(8 + len(cglp)) % 4)) + cglp)

        cwdh_body = struct.pack("<HHI", 0, len(self.widths) - 1, 0) + b"".join(bytes(w) for w in self.widths)
        cwdh = pad4(b"HDWC" + struct.pack("<I", 8 + len(cwdh_body) + (-(8 + len(cwdh_body)) % 4)) + cwdh_body)

        cglp_o = 0x30
        cwdh_o = cglp_o + len(cglp)
        cmap_o = cwdh_o + len(cwdh)

        # CMAPs: direct ranges for 0x20-0x7E / 0xA1-0xFF (as original), scan for everything else
        blocks = []
        direct = [(0x20, 0x7E), (0xA1, 0xFF)]
        for lo, hi in direct:
            blocks.append((lo, hi, 0, struct.pack("<H", self.cmap[lo])))
        rest = sorted(c for c in self.cmap if not any(lo <= c <= hi for lo, hi in direct))
        scan = struct.pack("<H", len(rest)) + b"".join(struct.pack("<HH", c, self.cmap[c]) for c in rest)
        blocks.append((0x0000, 0xFFFF, 2, scan))
        cmaps = bytearray()
        offs = []
        pos = cmap_o
        sizes = []
        for lo, hi, typ, body in blocks:
            sz = 0x14 + len(body); sz += -sz % 4
            offs.append(pos); sizes.append(sz); pos += sz
        for i, (lo, hi, typ, body) in enumerate(blocks):
            nxt = offs[i + 1] + 8 if i + 1 < len(blocks) else 0
            blk = b"PAMC" + struct.pack("<IHHHHI", sizes[i], lo, hi, typ, 0, nxt) + body
            cmaps += pad4(blk)

        # FINF (incl. 8-byte section header): pGlyph@0x10 pWidth@0x14 pMap@0x18 height@0x1C width@0x1D
        finf = bytearray(self.finf)
        struct.pack_into("<I", finf, 0x10, cglp_o + 8)
        struct.pack_into("<I", finf, 0x14, cwdh_o + 8)
        struct.pack_into("<I", finf, 0x18, cmap_o + 8)
        finf[0x1D] = max(finf[0x1D], self.maxw)
        body = bytes(finf) + cglp + cwdh + cmaps
        hdr = bytearray(self.hdr)
        struct.pack_into("<I", hdr, 8, 0x10 + len(body))
        struct.pack_into("<H", hdr, 0x0E, 3 + len(blocks))
        return bytes(hdr) + body


def pad4(b):
    return bytes(b) + b"\x00" * (-len(b) % 4)
