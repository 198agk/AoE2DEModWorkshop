"""p23: find the registration/vtable table that holds absolute VAs of the per-content-mode
functions, and dump it with resolved neighbours. Decisive test for "compiled-in mode table"
vs "directory scan".
Read-only -> p23_out.txt
"""
import os, struct, json

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\modes_overlay"
F = open(os.path.join(OUT, "p23_out.txt"), "w", encoding="utf-8")
def P(*a): print(*a, file=F)

buf = open(EXE, "rb").read()
N = len(buf)
IMGBASE = 0x140000000
e = struct.unpack_from("<I", buf, 0x3c)[0]
nsec = struct.unpack_from("<H", buf, e+6)[0]
optsz = struct.unpack_from("<H", buf, e+20)[0]
sects = []
so = e + 24 + optsz
for i in range(nsec):
    o = so + i*40
    nm = buf[o:o+8].rstrip(b"\0").decode()
    vs, va, rs, ra = struct.unpack_from("<IIII", buf, o+8)
    sects.append((nm, va, vs, ra, rs))
def r2o(rva):
    for nm, va, vs, ra, rs in sects:
        if va <= rva < va + max(vs, rs):
            o = ra + (rva - va); return o if 0 <= o < N else None
    return None
def o2r(o):
    for nm, va, vs, ra, rs in sects:
        if ra <= o < ra + rs: return va + (o - ra)
    return None
def sec(rva):
    for nm, va, vs, ra, rs in sects:
        if va <= rva < va + max(vs, rs): return nm
    return "?"
# pdata lookup
pdo = next(x for x in sects if x[0] == ".pdata")
FN = []
for i in range(pdo[4] // 12):
    st, en, ui = struct.unpack_from("<III", buf, pdo[3] + i*12)
    FN.append((st, en))
FN.sort()
import bisect
fst = [f[0] for f in FN]
def owner(rva):
    i = bisect.bisect_right(fst, rva) - 1
    if i >= 0 and FN[i][0] <= rva < FN[i][1]:
        return FN[i]
    return None
def cstr(rva, ml=200):
    o = r2o(rva)
    if o is None: return None
    q = buf.find(b"\0", o, o+ml)
    return buf[o:q].decode("latin-1") if q > 0 else None

# candidate RVAs: per-content-mode functions (string refs 'Pompeii' etc.) + the modes path fn
CAND = {
    0x0bdcc0: "content-mode fn (Pompeii) #3",
    0x0bc360: "content-mode fn (Pompeii) #1",
    0x0bd320: "content-mode fn (Pompeii) #2",
    0x0bdb50: "modes\\Pompeii\\ path fn",
    0x0bdae0: "UNIQUE_TEMP_FOLDER fn",
    0x0be4f0: "report-list fn",
}
# also siblings for the other 4 mode names, found earlier at +0x120 offsets:
for base, lbl in [(0x0bc360, "Philadelphia?"), (0x0bd320, "Philadelphia#2?"), (0x0bdcc0, "Philadelphia#3?")]:
    pass

P("#"*100)
P("# absolute 8-byte VA occurrences of the candidate functions (anywhere in the image)")
def find_va(va):
    pat = struct.pack("<Q", IMGBASE + va)
    out = []
    s = 0
    while True:
        i = buf.find(pat, s)
        if i < 0: break
        out.append(i); s = i + 1
    return out
allhits = {}
for rva, lbl in CAND.items():
    hs = find_va(rva)
    allhits[rva] = hs
    P(f"  {rva:#08x} ({lbl}): {len(hs)} abs-VA occurrence(s)")
    for fo in hs:
        P(f"      fileoff {fo:#x} rva {o2r(fo):#x} [{sec(o2r(fo))}]")
# also RVA-as-dword occurrences
P("")
P("  RVA-as-dword (4-byte) occurrences:")
for rva, lbl in CAND.items():
    pat = struct.pack("<I", rva)
    hs = []
    s = 0
    while True:
        i = buf.find(pat, s)
        if i < 0: break
        hs.append(i); s = i + 1
    P(f"  {rva:#08x} ({lbl}): {len(hs)} dword occurrence(s) at {[hex(x) for x in hs[:6]]}")

P("")
P("#"*100)
P("# dump of pointer-table neighbourhoods")
seen = set()
for rva, lbl in CAND.items():
    for fo in allhits[rva]:
        if fo in seen: continue
        seen.add(fo)
        start = fo - 0x80
        if start < 0: start = 0
        P(f"  --- around {lbl} @fileoff {fo:#x} (rva {o2r(fo):#x}, {sec(o2r(fo))}) ---")
        p = start
        while p <= fo + 0x80:
            v = struct.unpack_from("<Q", buf, p)[0]
            rv = o2r(p)
            tag = ""
            if IMGBASE <= v < IMGBASE + 0x5000000:
                t = v - IMGBASE
                ow = owner(t)
                s = cstr(t, 40)
                tag = f" -> rva {t:#x} [{sec(t)}]" + (f" fn {ow[0]:#x}-{ow[1]:#x}" if ow else "") + (f" str {s!r}" if s else "")
            P(f"      +{p-start:3d} fo {p:#x} rva {rv if rv else 0:#x}  {v:#018x}{tag}")
            p += 8

P("")
P("#"*100)
P("# content-mode name table 0x31f7460-0x31f7560: strings then pointers")
o = r2o(0x31f7460)
seg = buf[o:o+0x120]
p = 0
while p < len(seg):
    q = seg.find(b"\0", p)
    if q < 0: break
    if q > p:
        s = seg[p:q]
        if len(s) >= 2 and all(32 <= b < 127 for b in s):
            P(f"   {0x31f7460+p:#010x} str {s.decode('latin-1')!r}")
    p = q + 1
P("  --- as 8-byte values ---")
p = 0
while p < len(seg) - 8:
    v = struct.unpack_from("<Q", seg, p)[0]
    if IMGBASE <= v < IMGBASE + 0x5000000:
        t = v - IMGBASE
        ow = owner(t)
        P(f"   {0x31f7460+p:#010x} ptr -> rva {t:#x} [{sec(t)}] fn {ow if ow else None}")
    p += 8

P("")
P("#"*100)
P("# Is there a table of storage-point strings? search .rdata for 8-byte VAs of the registry keys")
for key, rva in [("storage_point_list", 0x325c588), ("replace", 0x325c5a0),
                 ("use_modes_path_for_mods", 0x325c5a8), ("linkedUnits.json", 0x325c5c0),
                 ("morematerials", 0x325c618), ("FULL_STORAGE_SP_DEFAULT_TABLE??", 0x31f8598),
                 ("modes\\Pompeii\\", 0x31f8420), ("Pompeii", 0x31f7480)]:
    hs8 = find_va(rva)
    pat4 = struct.pack("<I", rva)
    hs4 = []
    s = 0
    while True:
        i = buf.find(pat4, s)
        if i < 0: break
        hs4.append(i); s = i + 1
    P(f"  {key!r} rva {rva:#x}: abs8={[hex(x) for x in hs8]} dword={[hex(x) for x in hs4]}")
    for fo in hs8:
        P(f"      ctx: {buf[max(0,fo-24):fo+32]!r}")
F.close()
print("wrote p23_out.txt")
