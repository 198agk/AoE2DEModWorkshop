# -*- coding: utf-8 -*-
"""PE-parse AoE2DE_s.exe; find the pointer array that references the font-name strings."""
import os, io, struct, json

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\hud_render"
data = open(EXE, "rb").read()
rep = io.StringIO()

# ---- PE headers ----
pe_off = struct.unpack_from("<I", data, 0x3C)[0]
assert data[pe_off:pe_off+4] == b"PE\0\0", "not PE"
machine, nsec = struct.unpack_from("<HH", data, pe_off + 4)
opt_size = struct.unpack_from("<H", data, pe_off + 20)[0]
opt_off = pe_off + 24
magic = struct.unpack_from("<H", data, opt_off)[0]
image_base = struct.unpack_from("<Q", data, opt_off + 24)[0] if magic == 0x20B else struct.unpack_from("<I", data, opt_off + 28)[0]
rep.write("PE off=0x%X machine=0x%X nsec=%d magic=0x%X image_base=0x%X\n"
          % (pe_off, machine, nsec, magic, image_base))

sec_off = opt_off + opt_size
secs = []
for i in range(nsec):
    o = sec_off + i * 40
    name = data[o:o+8].rstrip(b"\0").decode("ascii", "replace")
    vsize, va, rawsize, rawptr = struct.unpack_from("<IIII", data, o + 8)
    secs.append(dict(name=name, va=va, vsize=vsize, raw=rawptr, rawsize=rawsize))
    rep.write("  SEC %-10s VA=0x%08X VSize=0x%08X RawPtr=0x%08X RawSize=0x%08X\n"
              % (name, va, vsize, rawptr, rawsize))

def off2rva(off):
    for s in secs:
        if s["raw"] <= off < s["raw"] + s["rawsize"]:
            return s["va"] + (off - s["raw"])
    return None

def rva2off(rva):
    for s in secs:
        if s["va"] <= rva < s["va"] + max(s["vsize"], s["rawsize"]):
            return s["raw"] + (rva - s["va"])
    return None

# ---- strings found earlier ----
FONT_STRS = {}
for nm, off in [("combined", 0x032E6D90), ("basic_bold_16", 0x032E6DA0),
                ("combined_sansserif", 0x032E6DB0), ("TimeLineTexture", 0x032E6D70),
                ("MapViewTexture", 0x032E6D80)]:
    rva = off2rva(off)
    FONT_STRS[nm] = dict(off=off, rva=rva, va=image_base + rva)
    rep.write("STR %-20s fileoff=0x%08X rva=0x%08X va=0x%016X\n" % (nm, off, rva, FONT_STRS[nm]["va"]))

# ---- search for 8-byte pointers to these VAs, contiguous = an array ----
rep.write("\n=== pointer search (8-byte LE, pointing at the string VAs) ===\n")
for nm, d in FONT_STRS.items():
    pat = struct.pack("<Q", d["va"])
    hits = []
    st = 0
    while True:
        i = data.find(pat, st)
        if i < 0: break
        hits.append(i); st = i + 1
    rep.write("  %-20s va=0x%X  pointer hits=%d : %s\n" % (nm, d["va"], len(hits),
              ["0x%08X" % h for h in hits[:10]]))

# also try 4-byte RVA refs
rep.write("\n=== pointer search (4-byte LE RVA) ===\n")
for nm, d in FONT_STRS.items():
    pat = struct.pack("<I", d["rva"])
    hits = []
    st = 0
    while True:
        i = data.find(pat, st)
        if i < 0: break
        hits.append(i); st = i + 1
    rep.write("  %-20s rva=0x%X  hits=%d : %s\n" % (nm, d["rva"], len(hits),
              ["0x%08X" % h for h in hits[:10]]))

# ---- look at the surrounding "font" init region for an array of {name, something} ----
rep.write("\n=== hexdump 0x032E6D88..0x032E6DD0 (the three names in place) ===\n")
for i in range(0x032E6D88, 0x032E6DD0, 16):
    ch = data[i:i+16]
    rep.write("  %08X  %-47s  %s\n" % (i, " ".join("%02X" % c for c in ch),
              "".join(chr(c) if 32 <= c < 127 else "." for c in ch)))

# ---- search for any run of consecutive pointers into the font filename strings ----
rep.write("\n=== scan whole .rdata for >=3 consecutive 8-byte pointers into 0x032E6D00..0x032E6E00 ===\n")
lo, hi = off2rva(0x032E6D00), off2rva(0x032E6E00)
lo_va, hi_va = image_base + lo, image_base + hi
rdata = next((s for s in secs if s["name"] in (".rdata",)), None)
rep.write("target VA window: 0x%X..0x%X\n" % (lo_va, hi_va))
if rdata:
    base = rdata["raw"]; size = rdata["rawsize"]
    found = []
    i = base
    while i + 16 <= base + size:
        v, = struct.unpack_from("<Q", data, i)
        if lo_va <= v < hi_va:
            # count run
            n = 0; j = i
            while j + 8 <= base + size:
                w, = struct.unpack_from("<Q", data, j)
                if lo_va <= w < hi_va:
                    n += 1; j += 8
                else:
                    break
            if n >= 3:
                arr = []
                for k in range(n):
                    w, = struct.unpack_from("<Q", data, i + k*8)
                    o2 = rva2off(w - image_base)
                    arr.append(data[o2:data.index(b"\0", o2)].decode("utf-8", "replace") if o2 else "?")
                found.append((i, n, arr))
                i = j
                continue
        i += 1
    for i, n, arr in found[:20]:
        rep.write("  @0x%08X (rva 0x%X) n=%d -> %s\n" % (i, off2rva(i), n, arr))
    if not found:
        rep.write("  none\n")

open(os.path.join(OUT, "pe_font_table.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())
