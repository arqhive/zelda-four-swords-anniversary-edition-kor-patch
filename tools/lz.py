"""Nintendo LZ10/LZ11 decompressor."""
import struct


def decompress(src):
    typ = src[0]
    size = src[1] | src[2] << 8 | src[3] << 16
    p = 4
    if size == 0:
        size = struct.unpack_from("<I", src, 4)[0]; p = 8
    out = bytearray()
    while len(out) < size:
        flags = src[p]; p += 1
        for bit in range(8):
            if len(out) >= size:
                break
            if not flags & (0x80 >> bit):
                out.append(src[p]); p += 1
                continue
            if typ == 0x10:
                b1, b2 = src[p], src[p + 1]; p += 2
                n = (b1 >> 4) + 3; disp = ((b1 & 0xF) << 8 | b2) + 1
            else:
                b1 = src[p]; ind = b1 >> 4
                if ind == 0:
                    n = (b1 << 4 | src[p + 1] >> 4) + 0x11
                    disp = ((src[p + 1] & 0xF) << 8 | src[p + 2]) + 1; p += 3
                elif ind == 1:
                    n = ((b1 & 0xF) << 12 | src[p + 1] << 4 | src[p + 2] >> 4) + 0x111
                    disp = ((src[p + 2] & 0xF) << 8 | src[p + 3]) + 1; p += 4
                else:
                    n = ind + 1; disp = ((b1 & 0xF) << 8 | src[p + 1]) + 1; p += 2
            for _ in range(n):
                out.append(out[-disp])
    return bytes(out)


def compress_lz11(data):
    """Greedy LZ11 compressor (hash chains over 3-byte prefixes, window 0x1000).

    Never emits displacement 1: the game's decoder (like the original files) only works with disp >= 2.
    """
    n = len(data)
    out = bytearray([0x11])
    if n < 0x1000000:
        out += bytes([n & 0xFF, n >> 8 & 0xFF, n >> 16 & 0xFF])
    else:
        out += b"\x00\x00\x00" + n.to_bytes(4, "little")
    head = {}
    pos = 0
    while pos < n:
        flag_pos = len(out); out.append(0); flags = 0
        for bit in range(8):
            if pos >= n:
                break
            best_len, best_disp = 0, 0
            if pos + 3 <= n:
                key = data[pos:pos + 3]
                chain = head.get(key, [])
                limit = min(0x10110, n - pos)
                for cand in reversed(chain[-64:]):
                    disp = pos - cand
                    if disp > 0x1000 or disp < 2:
                        continue
                    l = 3
                    while l < limit and data[cand + l] == data[pos + l]:
                        l += 1
                    if l > best_len:
                        best_len, best_disp = l, disp
                        if l == limit:
                            break
            if best_len >= 3:
                flags |= 0x80 >> bit
                d = best_disp - 1
                if best_len <= 0x10:
                    out += bytes([(best_len - 1) << 4 | d >> 8, d & 0xFF])
                elif best_len <= 0x110:
                    l = best_len - 0x11
                    out += bytes([l >> 4, (l & 0xF) << 4 | d >> 8, d & 0xFF])
                else:
                    l = best_len - 0x111
                    out += bytes([0x10 | l >> 12, l >> 4 & 0xFF, (l & 0xF) << 4 | d >> 8, d & 0xFF])
                step = best_len
            else:
                out.append(data[pos])
                step = 1
            for p in range(pos, min(pos + step, n - 2)):
                head.setdefault(data[p:p + 3], []).append(p)
            pos += step
        out[flag_pos] = flags
    while len(out) % 4:
        out.append(0)
    return bytes(out)
