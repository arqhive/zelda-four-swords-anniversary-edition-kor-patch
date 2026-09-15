"""Tiny pure-Python AES-128 block encryptor (enough for CTR mode)."""

SBOX = [0] * 256
def _init():
    p = q = 1
    while True:
        p = p ^ ((p << 1) & 0xFF) ^ (0x1B if p & 0x80 else 0)
        q ^= q << 1; q ^= q << 2; q ^= q << 4; q &= 0xFF
        if q & 0x80: q ^= 0x09
        x = q ^ (((q << 1) | (q >> 7)) & 0xFF) ^ (((q << 2) | (q >> 6)) & 0xFF) ^ (((q << 3) | (q >> 5)) & 0xFF) ^ (((q << 4) | (q >> 4)) & 0xFF)
        SBOX[p] = (x ^ 0x63) & 0xFF
        if p == 1: break
    SBOX[0] = 0x63
_init()

def _xt(a):
    return ((a << 1) ^ 0x1B) & 0xFF if a & 0x80 else a << 1

def expand(key):
    w = list(key)
    rcon = 1
    while len(w) < 176:
        t = w[-4:]
        if len(w) % 16 == 0:
            t = [SBOX[t[1]] ^ rcon, SBOX[t[2]], SBOX[t[3]], SBOX[t[0]]]
            rcon = _xt(rcon)
        w += [w[-16 + i] ^ t[i] for i in range(4)]
    return w

def encrypt_block(rk, block):
    s = [b ^ rk[i] for i, b in enumerate(block)]
    for rnd in range(1, 11):
        s = [SBOX[b] for b in s]
        s = [s[(i + 4 * (i % 4)) % 16] for i in range(16)]  # ShiftRows (column-major)
        if rnd != 10:
            n = []
            for c in range(4):
                a = s[4 * c:4 * c + 4]
                n += [_xt(a[0]) ^ _xt(a[1]) ^ a[1] ^ a[2] ^ a[3],
                      a[0] ^ _xt(a[1]) ^ _xt(a[2]) ^ a[2] ^ a[3],
                      a[0] ^ a[1] ^ _xt(a[2]) ^ _xt(a[3]) ^ a[3],
                      _xt(a[0]) ^ a[0] ^ a[1] ^ a[2] ^ _xt(a[3])]
            s = n
        s = [b ^ rk[16 * rnd + i] for i, b in enumerate(s)]
    return bytes(s)

if __name__ == "__main__":
    # FIPS-197 C.1 test vector
    k = bytes(range(16)); pt = bytes.fromhex("00112233445566778899aabbccddeeff")
    assert encrypt_block(expand(k), pt).hex() == "69c4e0d86a7b0430d8cdb78070b4c55a"
    print("AES self-test OK")
