"""ARM9 disassembly helper for KQ9E (decrypted ROM). Usage: python dis.py ADDR COUNT [ADDR COUNT ...]"""
import os, struct, sys
from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM

# decrypted ROM produced by decrypt_modcrypt.py, kept in the untracked work/ folder
ROM = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                   "work", "extract", "KQ9E_decrypted.nds")
d = open(ROM, "rb").read()
REGIONS = [(0x4000, 0x02004000, 0x1235E0), (0xD85400, 0x02400000, 0x4794)]

def ram_bytes(addr, n):
    for o, l, s in REGIONS:
        if l <= addr < l + s:
            return d[o + addr - l:o + addr - l + n]
    raise ValueError("addr %08X not mapped" % addr)

def word(addr):
    return struct.unpack("<I", ram_bytes(addr, 4))[0]

md = Cs(CS_ARCH_ARM, CS_MODE_ARM)

def dis(addr, count):
    code = ram_bytes(addr, count * 4)
    for ins in md.disasm(code, addr):
        note = ""
        if ins.mnemonic.startswith("ldr") and "pc, #" in ins.op_str:
            imm = int(ins.op_str.split("#")[1].rstrip("]"), 16)
            lit = ins.address + 8 + imm
            try:
                note = "  ; =%08X" % word(lit)
            except ValueError:
                pass
        print("%08X  %08X  %-6s %s%s" % (ins.address, struct.unpack("<I", ins.bytes)[0], ins.mnemonic, ins.op_str, note))

if __name__ == "__main__":
    args = sys.argv[1:]
    for i in range(0, len(args), 2):
        print("---- %s" % args[i])
        dis(int(args[i], 16), int(args[i + 1]))
