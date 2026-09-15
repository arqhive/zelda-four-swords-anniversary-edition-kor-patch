"""Minimal BPS patch creator / applier (format used by Floating IPS, beat, Rom Patcher JS).

Usage: python bps.py create source target patch.bps [metadata]
       python bps.py apply  source patch.bps output
"""
import struct, sys, zlib

SOURCE_READ, TARGET_READ, SOURCE_COPY, TARGET_COPY = range(4)


def _num(n):
    out = bytearray()
    while True:
        x = n & 0x7F
        n >>= 7
        if n == 0:
            out.append(0x80 | x)
            return bytes(out)
        out.append(x)
        n -= 1


def _read_num(buf, p):
    data, shift = 0, 1
    while True:
        x = buf[p]; p += 1
        data += (x & 0x7F) * shift
        if x & 0x80:
            return data, p
        shift <<= 7
        data += shift


def create(src, dst, metadata=b""):
    out = bytearray(b"BPS1")
    out += _num(len(src)) + _num(len(dst)) + _num(len(metadata)) + metadata
    n, i = len(dst), 0
    MIN_RUN = 16  # identical run length worth a SourceRead
    while i < n:
        if i < len(src) and src[i] == dst[i]:
            j = i
            while j < n and j < len(src) and src[j] == dst[j]:
                j += 1
            if j - i >= MIN_RUN or j == n:
                out += _num(((j - i - 1) << 2) | SOURCE_READ)
                i = j
                continue
        # literal bytes until the next long identical run
        j = i
        while j < n:
            if j < len(src) and src[j] == dst[j]:
                k = j
                while k < n and k < len(src) and src[k] == dst[k] and k - j < MIN_RUN:
                    k += 1
                if k - j >= MIN_RUN or k == n:
                    break
                j = k
            else:
                j += 1
        out += _num(((j - i - 1) << 2) | TARGET_READ) + dst[i:j]
        i = j
    out += struct.pack("<I", zlib.crc32(src)) + struct.pack("<I", zlib.crc32(dst))
    out += struct.pack("<I", zlib.crc32(bytes(out)))
    return bytes(out)


def apply(src, patch):
    assert patch[:4] == b"BPS1", "not a BPS patch"
    assert zlib.crc32(patch[:-4]) == struct.unpack_from("<I", patch, len(patch) - 4)[0], "patch CRC mismatch"
    src_crc, dst_crc = struct.unpack_from("<II", patch, len(patch) - 12)
    if zlib.crc32(src) != src_crc:
        raise ValueError("source CRC32 mismatch (expected %08X, got %08X)" % (src_crc, zlib.crc32(src)))
    p = 4
    src_size, p = _read_num(patch, p)
    dst_size, p = _read_num(patch, p)
    meta_size, p = _read_num(patch, p)
    p += meta_size
    out = bytearray()
    src_rel = dst_rel = 0
    end = len(patch) - 12
    while p < end:
        data, p = _read_num(patch, p)
        cmd, length = data & 3, (data >> 2) + 1
        if cmd == SOURCE_READ:
            out += src[len(out):len(out) + length]
        elif cmd == TARGET_READ:
            out += patch[p:p + length]; p += length
        else:
            off, p = _read_num(patch, p)
            off = (-1 if off & 1 else 1) * (off >> 1)
            if cmd == SOURCE_COPY:
                src_rel += off
                out += src[src_rel:src_rel + length]; src_rel += length
            else:
                dst_rel += off
                for _ in range(length):
                    out.append(out[dst_rel]); dst_rel += 1
    assert len(out) == dst_size and zlib.crc32(out) == dst_crc, "output CRC mismatch"
    return bytes(out)


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "create":
        src = open(sys.argv[2], "rb").read(); dst = open(sys.argv[3], "rb").read()
        meta = sys.argv[5].encode("utf-8") if len(sys.argv) > 5 else b""
        open(sys.argv[4], "wb").write(create(src, dst, meta))
    else:
        src = open(sys.argv[2], "rb").read(); patch = open(sys.argv[3], "rb").read()
        open(sys.argv[4], "wb").write(apply(src, patch))
