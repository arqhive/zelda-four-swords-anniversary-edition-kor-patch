"""Minimal NDS/DSi ROM NitroFS reader/writer."""
import struct

class Rom:
    def __init__(self, path):
        self.data = bytearray(open(path, "rb").read())
        d = self.data
        self.fnt_o, self.fnt_s, self.fat_o, self.fat_s = struct.unpack_from("<IIII", d, 0x40)
        self.fat = [list(struct.unpack_from("<II", d, self.fat_o + i * 8)) for i in range(self.fat_s // 8)]
        self.names = {}
        self._walk(0xF000, "")
        self.data_start = min(s for s, e in self.fat if e > s)

    def _walk(self, did, path):
        d = self.data
        off, first, _ = struct.unpack_from("<IHH", d, self.fnt_o + (did & 0xFFF) * 8)
        p = self.fnt_o + off
        fid = first
        while True:
            l = d[p]; p += 1
            if l == 0:
                break
            n = d[p:p + (l & 0x7F)].decode("latin1"); p += l & 0x7F
            if l & 0x80:
                sub = struct.unpack_from("<H", d, p)[0]; p += 2
                self._walk(sub, path + n + "/")
            else:
                self.names[path + n] = fid
                fid += 1

    def data_limit(self):
        """End of the file data area: the DSi NTR digest region end if present, else the NTR ROM size."""
        if self.data[0x12] & 2:
            ntr_o, ntr_s = struct.unpack_from("<II", self.data, 0x1E0)
            if ntr_s:
                return ntr_o + ntr_s
        return struct.unpack_from("<I", self.data, 0x80)[0]

    def read(self, name):
        s, e = self.fat[self.names[name]]
        return bytes(self.data[s:e])

    def _set(self, fid, s, e):
        self.fat[fid] = [s, e]
        struct.pack_into("<II", self.data, self.fat_o + fid * 8, s, e)

    def remove(self, name):
        """Make a file empty (keeps its FAT slot); its data area becomes free space."""
        fid = self.names[name]
        s, e = self.fat[fid]
        self.data[s:e] = b"\xFF" * (e - s)
        self._set(fid, s, s)

    def _gaps(self, exclude):
        used = sorted((s, e) for i, (s, e) in enumerate(self.fat) if e > s and i != exclude)
        pos = self.data_start
        for s, e in used:
            if s > pos:
                yield pos, s
            pos = max(pos, e)
        if self.data_limit() > pos:
            yield pos, self.data_limit()

    def replace(self, name, blob, align=4):
        """Place blob in the first free gap (its own slot counts as free) inside the data area."""
        fid = self.names[name]
        for lo, hi in self._gaps(fid):
            start = (lo + align - 1) // align * align
            if start + len(blob) <= hi:
                self.data[start:start + len(blob)] = blob
                self._set(fid, start, start + len(blob))
                return start
        raise ValueError("no free gap of %X bytes for %s" % (len(blob), name))

    def save(self, path):
        struct.pack_into("<H", self.data, 0x15E, crc16(self.data[:0x15E]))
        open(path, "wb").write(self.data)


def crc16(buf):
    crc = 0xFFFF
    for b in buf:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc
