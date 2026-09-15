"""Inspect DSi SRL digest (sector/block hash tables) and verify them.

Usage: python tools/digest_check.py rom.nds
(TWL-region sector mismatches are expected: those hashes cover modcrypt-decrypted data.)
"""
import hashlib, hmac, struct, sys

HMAC_KEY = bytes.fromhex(
    "2106C0DEBA98CE3FA692E39D46F2ED0176E3CC08562363FACAD4ECDF9A6278348F6D633CFE22CA92208897"
    "23D2CFAEC232678DFECA836498ACFD3E3787465824")

if len(sys.argv) < 2:
    sys.exit(__doc__)
path = sys.argv[1]
d = open(path, "rb").read()
ntr_o, ntr_s, twl_o, twl_s, sht_o, sht_s, bht_o, bht_s, sec_size, blk_count = struct.unpack_from("<10I", d, 0x1E0)
print("NTR digest region %X+%X  TWL region %X+%X" % (ntr_o, ntr_s, twl_o, twl_s))
print("sector hashtable %X+%X  block hashtable %X+%X  sector size %X  sectors/block %d" % (sht_o, sht_s, bht_o, bht_s, sec_size, blk_count))
master = d[0x328:0x33C]
print("master (0x328):", master.hex())

def sectors():
    for base, size in ((ntr_o, ntr_s), (twl_o, twl_s)):
        for off in range(base, base + size, sec_size):
            yield off

stored0 = d[sht_o:sht_o + 20]
sec0 = d[ntr_o:ntr_o + sec_size]
for name, fn in (("HMAC-SHA1", lambda b: hmac.new(HMAC_KEY, b, hashlib.sha1).digest()),
                 ("SHA1", lambda b: hashlib.sha1(b).digest())):
    print("%-9s sector0 match: %s" % (name, fn(sec0) == stored0))
    if fn(sec0) == stored0:
        h = fn
        bad = [i for i, off in enumerate(sectors()) if h(d[off:off + sec_size]) != d[sht_o + i * 20:sht_o + i * 20 + 20]]
        print("  sector mismatches:", len(bad), bad[:10])
        blk_bad = []
        nblk = bht_s // 20
        for b in range(nblk):
            chunk = d[sht_o + b * blk_count * 20:sht_o + (b + 1) * blk_count * 20]
            if h(chunk) != d[bht_o + b * 20:bht_o + b * 20 + 20]:
                blk_bad.append(b)
        print("  block mismatches:", len(blk_bad), blk_bad[:10])
        print("  master match:", h(d[bht_o:bht_o + bht_s]) == master)
