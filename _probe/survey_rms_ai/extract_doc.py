# -*- coding: utf-8 -*-
"""Minimal OLE2 (CFB) reader + Word97 .doc text extractor. No external deps."""
import struct, sys, os, re

class OLE:
    def __init__(self, data):
        self.d = data
        assert data[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", "not an OLE2 file"
        self.ssz = 1 << struct.unpack_from("<H", data, 30)[0]
        self.sssz = 1 << struct.unpack_from("<H", data, 32)[0]
        self.ndifat = struct.unpack_from("<I", data, 68)[0]
        first_difat = struct.unpack_from("<I", data, 68)[0]
        self.difat_start = struct.unpack_from("<I", data, 68)[0]
        self.nfat = struct.unpack_from("<I", data, 44)[0]
        self.dir_start = struct.unpack_from("<I", data, 48)[0]
        self.mini_cutoff = struct.unpack_from("<I", data, 56)[0]
        self.mini_start = struct.unpack_from("<I", data, 60)[0]
        self.n_minifat = struct.unpack_from("<I", data, 64)[0]
        # DIFAT: first 109 entries in header at 76
        difat = list(struct.unpack_from("<109I", data, 76))[:self.nfat]
        # follow DIFAT chain if needed
        sect = self.difat_start
        while sect not in (0xFFFFFFFE, 0xFFFFFFFF) and len(difat) < self.nfat + 1000:
            off = 512 + sect * self.ssz
            vals = struct.unpack_from("<%dI" % (self.ssz // 4), data, off)
            difat.extend(vals[:-1])
            sect = vals[-1]
        self.fat = []
        for fs in difat:
            if fs in (0xFFFFFFFE, 0xFFFFFFFF): continue
            off = 512 + fs * self.ssz
            if off + self.ssz > len(data): break
            self.fat.extend(struct.unpack_from("<%dI" % (self.ssz // 4), data, off))
        self.minifat = []
        if self.n_minifat:
            mf = self._read_chain_raw(self.mini_start)
            self.minifat = list(struct.unpack_from("<%dI" % (len(mf) // 4), mf, 0))
        self.ministream = self._read_chain_raw(self.dir_start) if False else None
        self.entries = self._read_dir()

    def _chain(self, start, fat):
        out = []
        s = start
        seen = set()
        while s not in (0xFFFFFFFE, 0xFFFFFFFF) and s not in seen and s < len(fat):
            seen.add(s); out.append(s); s = fat[s]
        return out

    def _read_chain_raw(self, start):
        out = bytearray()
        for s in self._chain(start, self.fat):
            off = 512 + s * self.ssz
            out += self.d[off:off + self.ssz]
        return bytes(out)

    def _read_dir(self):
        raw = self._read_chain_raw(self.dir_start)
        ents = []
        for i in range(len(raw) // 128):
            e = raw[i * 128:(i + 1) * 128]
            nlen = struct.unpack_from("<H", e, 64)[0]
            name = e[:max(0, nlen - 2)].decode("utf-16-le", "replace") if nlen >= 2 else ""
            typ = e[66]
            start = struct.unpack_from("<I", e, 116)[0]
            size = struct.unpack_from("<Q", e, 120)[0]
            ents.append({"name": name, "type": typ, "start": start, "size": size})
        # ministream is root entry's stream
        root = next((x for x in ents if x["type"] == 5), None)
        if root:
            self.ministream = self._read_chain_raw(root["start"])[:root["size"]]
        return ents

    def read(self, name):
        e = next((x for x in self.entries if x["name"] == name and x["type"] == 2), None)
        if not e: return None
        if e["size"] < self.mini_cutoff and self.ministream is not None:
            out = bytearray()
            for s in self._chain(e["start"], self.minifat):
                out += self.ministream[s * self.sssz:(s + 1) * self.sssz]
            return bytes(out[:e["size"]])
        return self._read_chain_raw(e["start"])[:e["size"]]


def doc_text(path):
    ole = OLE(open(path, "rb").read())
    wd = ole.read("WordDocument")
    if wd is None:
        return None, [x["name"] for x in ole.entries]
    flags = struct.unpack_from("<H", wd, 10)[0]
    fWhichTblStm = (flags >> 9) & 1
    fcMin = struct.unpack_from("<I", wd, 24)[0]
    fcMac = struct.unpack_from("<I", wd, 28)[0]
    tbl = ole.read("1Table" if fWhichTblStm else "0Table")
    if tbl is None:
        tbl = ole.read("0Table") or ole.read("1Table")
    if tbl is None:
        # Word 6/95 style: text is plain in WordDocument from fcMin..fcMac
        raw = wd[fcMin:fcMac]
        return raw.decode("cp1252", "replace"), [x["name"] for x in ole.entries]
    # find piece table via clx: fcClx at FIB offset 418, lcbClx 422
    fcClx = struct.unpack_from("<I", wd, 418)[0]
    lcbClx = struct.unpack_from("<I", wd, 422)[0]
    if fcClx == 0 or lcbClx == 0 or fcClx >= len(tbl):
        raw = wd[fcMin:fcMac]
        return raw.decode("cp1252", "replace"), [x["name"] for x in ole.entries]
    clx = tbl[fcClx:fcClx + lcbClx]
    # skip prc entries (0x01) then find 0x02
    i = 0
    while i < len(clx) and clx[i] == 1:
        cb = struct.unpack_from("<h", clx, i + 1)[0]
        i += 3 + cb
    if i >= len(clx) or clx[i] != 2:
        # fallback: raw latin1
        return wd[fcMin:fcMac].decode("cp1252", "replace"), [x["name"] for x in ole.entries]
    lcb = struct.unpack_from("<I", clx, i + 1)[0]
    pcdt = clx[i + 5:i + 5 + lcb]
    ncp = (len(pcdt) - 4) // 12
    cps = list(struct.unpack_from("<%dI" % (ncp + 1), pcdt, 0))
    pieces = []
    base = 4 * (ncp + 1)
    for k in range(ncp):
        off = base + k * 8
        fc = struct.unpack_from("<I", pcdt, off + 2)[0]
        compressed = (fc & 0x40000000) != 0
        fcv = fc & 0x3FFFFFFF
        if compressed:
            fcv //= 2
        pieces.append((cps[k], cps[k + 1], fcv, compressed))
    out = []
    for cpstart, cpend, fcv, comp in pieces:
        n = cpend - cpstart
        if comp:
            out.append(wd[fcv:fcv + n].decode("cp1252", "replace"))
        else:
            out.append(wd[fcv:fcv + n * 2].decode("utf-16-le", "replace"))
    return "".join(out), [x["name"] for x in ole.entries]


def clean(t):
    t = t.replace("\r", "\n").replace("\x07", "\t|\t").replace("\x0c", "\n---PAGE---\n")
    t = re.sub(r"\x13[^\x14\x15]*\x14", "", t)
    t = re.sub(r"[\x00-\x08\x0b\x0e-\x1f]", "", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t


if __name__ == "__main__":
    src = sys.argv[1]; dst = sys.argv[2]
    txt, names = doc_text(src)
    if txt is None:
        print("FAILED. streams:", names); sys.exit(1)
    txt = clean(txt)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, "w", encoding="utf-8").write(txt)
    print(f"streams: {names}")
    print(f"chars: {len(txt)}")
    print("---- first 3000 chars ----")
    print(txt[:3000])
