"""Nintendo BLZ (bottom/backward LZ, as used by ARM9 binaries and *.blz files) decompressor."""
import struct


def decompress(data):
    if len(data) < 8:
        return data
    inc_len = struct.unpack_from("<I", data, len(data) - 4)[0]
    if inc_len == 0:
        return data[:-4]
    hdr = data[len(data) - 5]
    enc_len = struct.unpack_from("<I", data, len(data) - 8)[0] & 0xFFFFFF
    dec_len = len(data) - enc_len            # untouched prefix
    pak_len = enc_len - hdr                  # compressed payload length
    raw_len = dec_len + enc_len + inc_len
    out = bytearray(raw_len)
    out[:dec_len] = data[:dec_len]
    src = dec_len + pak_len                  # read backwards from here
    dst = raw_len
    src_end = dec_len
    while src > src_end:
        src -= 1
        flags = data[src]
        for _ in range(8):
            if src <= src_end or dst <= dec_len:
                break
            if not flags & 0x80:
                src -= 1; dst -= 1
                out[dst] = data[src]
            else:
                src -= 2
                pair = data[src + 1] << 8 | data[src]
                n = (pair >> 12) + 3
                disp = (pair & 0xFFF) + 3
                for _ in range(n):
                    dst -= 1
                    out[dst] = out[dst + disp]
            flags = (flags << 1) & 0xFF
    return bytes(out)
