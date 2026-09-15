"""Remove modcrypt from a DSi SRL: decrypt ARM9i/ARM7i areas in place and clear header flag bit 1.

Usage: python decrypt_modcrypt.py in.nds out.nds
"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # tools/ (ndsrom)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aes
from ndsrom import crc16

MAGIC = 0xFFFEFB4E295902582A680F5F1A4F3E79
M128 = (1 << 128) - 1

d = bytearray(open(sys.argv[1], "rb").read())
assert d[0x1C] & 2, "not modcrypted"
code = bytes(d[0x0C:0x10])
keyx = int.from_bytes(b"Nintendo" + code + code[::-1], "little")
keyy = int.from_bytes(d[0x350:0x360], "little")
k = ((keyx ^ keyy) + MAGIC) & M128
k = ((k << 42) | (k >> 86)) & M128
rk = aes.expand(k.to_bytes(16, "big"))

for hdr, ivo in ((0x220, 0x300), (0x228, 0x314)):
    off, size = struct.unpack_from("<II", d, hdr)
    ctr = int.from_bytes(d[ivo:ivo + 16], "little")
    for i in range((size + 15) // 16):
        ks = aes.encrypt_block(rk, ((ctr + i) & M128).to_bytes(16, "big"))[::-1]
        p = off + i * 16
        n = min(16, off + size - p)
        d[p:p + n] = bytes(a ^ b for a, b in zip(d[p:p + n], ks[:n]))
    print("decrypted %X+%X" % (off, size))

d[0x1C] &= ~2 & 0xFF
struct.pack_into("<H", d, 0x15E, crc16(d[:0x15E]))
open(sys.argv[2], "wb").write(d)
print("wrote", sys.argv[2])
