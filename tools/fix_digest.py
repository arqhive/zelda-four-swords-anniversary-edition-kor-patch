"""Recompute DSi SRL digest tables (NTR sector hashes -> block hashes -> master hash @0x328).

Usage: python fix_digest.py in.nds out.nds
TWL region sectors are left untouched (they hash modcrypt-decrypted data and are unchanged by our edits).
"""
import hashlib, hmac, struct, sys

HMAC_KEY = bytes.fromhex(
    "2106C0DEBA98CE3FA692E39D46F2ED0176E3CC08562363FACAD4ECDF9A6278348F6D633CFE22CA92208897"
    "23D2CFAEC232678DFECA836498ACFD3E3787465824")


def h(b):
    return hmac.new(HMAC_KEY, b, hashlib.sha1).digest()


def fix(d):
    ntr_o, ntr_s, twl_o, twl_s, sht_o, sht_s, bht_o, bht_s, sec_size, blk_count = struct.unpack_from("<10I", d, 0x1E0)
    changed = 0
    for i, off in enumerate(range(ntr_o, ntr_o + ntr_s, sec_size)):
        new = h(d[off:off + sec_size])
        p = sht_o + i * 20
        if d[p:p + 20] != new:
            d[p:p + 20] = new
            changed += 1
    for b in range(bht_s // 20):
        d[bht_o + b * 20:bht_o + b * 20 + 20] = h(d[sht_o + b * blk_count * 20:sht_o + (b + 1) * blk_count * 20])
    old_master = bytes(d[0x328:0x33C])
    d[0x328:0x33C] = h(d[bht_o:bht_o + bht_s])
    return changed, old_master != bytes(d[0x328:0x33C])


if __name__ == "__main__":
    data = bytearray(open(sys.argv[1], "rb").read())
    n, master_changed = fix(data)
    open(sys.argv[2], "wb").write(data)
    print("%s: %d sector hashes updated, master changed: %s -> %s" % (sys.argv[1], n, master_changed, sys.argv[2]))
